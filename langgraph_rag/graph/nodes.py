"""Graph nodes. Each node is a thin wrapper that reads/writes GraphState keys and
delegates to a component built from config. Nodes never import concrete classes
directly beyond the registry, so behavior is config-driven.

A node degrades gracefully: e.g. if `reranked` is absent the generator falls back to
`retrieved`. This is what lets optional nodes be removed without breaking the graph.
"""
from __future__ import annotations

import time

from ..core.config import load_config
from ..core.registry import build
from ..core.state import Chunk, GraphState

# import side effects register components in the registry
from ..retrieval import dense, bm25, hybrid, web  # noqa: F401
from ..rerank import qwen_reranker  # noqa: F401
from ..generate import generator  # noqa: F401
from ..guards.abstention import AbstentionGuard
from ..guards.conversation_rewrite import ConversationRewriter
from ..guards.grounding import GroundingGuard

ABSTAIN_MESSAGE = (
    "I don't have enough information in the Autodesk documentation to answer that "
    "confidently. Could you rephrase, or ask about a specific Autodesk product?"
)


def is_recency_sensitive(query: str, terms: list[str]) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in terms)


def is_in_domain_query(query: str, terms: list[str]) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in terms)


def should_use_web(query: str, top_score: float, n_contexts: int, cfg) -> tuple[bool, str]:
    """Confidence-driven web trigger; keeps obvious out-of-domain questions corpus-only."""
    wc = cfg.get_path("web", {})
    recency_terms = wc.get("recency_terms", [])
    in_domain_terms = wc.get("in_domain_terms", [])
    trigger_score = wc.get("trigger_max_score", 0.35)

    in_domain = is_in_domain_query(query, in_domain_terms)
    recency = is_recency_sensitive(query, recency_terms)
    if recency and in_domain:
        return True, "recency_or_dynamic_in_domain"
    if in_domain and (n_contexts == 0 or top_score < trigger_score):
        return True, "low_corpus_confidence_in_domain"
    return False, "corpus_confident_or_out_of_domain"


class Nodes:
    """Holds the components and exposes node callables for the graph."""

    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        rname = self.cfg.get_path("retrieval.retriever", "hybrid")
        self.retriever = build("retriever", rname)
        rerank_on = self.cfg.get_path("rerank.enabled", True)
        self.reranker = build("reranker", "qwen" if rerank_on else "passthrough")
        self.generator = build("generator", "qwen")
        self.web_enabled = self.cfg.get_path("web.enabled", False)
        self.web_retriever = build("retriever", "web") if self.web_enabled else None
        self.top_k = self.cfg.get_path("retrieval.top_k", 20)
        self.top_n = self.cfg.get_path("rerank.top_n", 5)
        self.web_top_k = self.cfg.get_path("web.top_k", 5)
        # guards (built lazily-ish; cheap constructors)
        self.rewriter = ConversationRewriter(self.cfg)
        self.abstention = AbstentionGuard(self.cfg)
        self.grounding = GroundingGuard(self.cfg)

    # --- nodes ---------------------------------------------------------------
    def rewrite(self, state: GraphState) -> GraphState:
        """Resolve context-dependent follow-ups to a standalone query."""
        rq = self.rewriter.rewrite(state["query"], state.get("chat_history", []))
        trace = dict(state.get("trace", {}))
        trace["rewritten"] = (rq != state["query"])
        return {"rewritten_query": rq, "trace": trace}

    def abstain_gate(self, state: GraphState) -> str:
        """Conditional-edge router: 'abstain' if retrieval confidence too low, else 'answer'."""
        contexts = state.get("reranked") or state.get("retrieved", [])
        top = max((c.get("score", 0.0) for c in contexts), default=0.0)
        if self.abstention.should_abstain(top, len(contexts)):
            return "abstain"
        return "answer"

    def abstain_response(self, state: GraphState) -> GraphState:
        trace = dict(state.get("trace", {}))
        trace["abstain_reason"] = "low_retrieval_confidence"
        return {"answer": ABSTAIN_MESSAGE, "citations": [], "abstained": True, "trace": trace}

    def decide_web(self, state: GraphState) -> GraphState:
        """Record whether web fallback should run."""
        query = state.get("rewritten_query") or state["query"]
        contexts = state.get("reranked") or state.get("retrieved", [])
        top = max((c.get("score", 0.0) for c in contexts), default=0.0)
        use_web, reason = should_use_web(query, top, len(contexts), self.cfg)
        trace = dict(state.get("trace", {}))
        trace["web_triggered"] = use_web
        trace["web_reason"] = reason
        trace["web_corpus_top_score"] = top
        return {"route": "web_augmented" if use_web else "corpus_only", "trace": trace}

    def web_route(self, state: GraphState) -> str:
        return "web" if state.get("route") == "web_augmented" else "answer"

    def web_retrieve(self, state: GraphState) -> GraphState:
        t0 = time.time()
        query = state.get("rewritten_query") or state["query"]
        chunks = self.web_retriever.retrieve(query, self.web_top_k) if self.web_retriever else []
        trace = dict(state.get("trace", {}))
        trace["web_ms"] = round((time.time() - t0) * 1000)
        trace["n_web_results"] = len(chunks)
        return {"web_results": [c.to_dict() for c in chunks], "trace": trace}

    def merge_contexts(self, state: GraphState) -> GraphState:
        """Merge corpus candidates with web results, then rerank final contexts."""
        query = state.get("rewritten_query") or state["query"]
        corpus = [Chunk.from_dict(d) for d in
                  (state.get("reranked") or state.get("contexts") or state.get("retrieved", []))]
        web_chunks = [Chunk.from_dict(d) for d in state.get("web_results", [])]
        trace = dict(state.get("trace", {}))
        if not web_chunks:
            existing_contexts = state.get("contexts") or state.get("reranked") or []
            trace["merged_contexts"] = len(existing_contexts)
            trace["final_context_sources"] = {
                "corpus": sum(1 for c in existing_contexts
                              if Chunk.from_dict(c).source == "corpus"),
                "web": 0,
            }
            trace["web_fallback_failed"] = True
            return {"trace": trace}

        seen: set[str] = set()
        merged: list[Chunk] = []
        for ch in corpus + web_chunks:
            key = ch.url or ch.id
            if key in seen:
                continue
            seen.add(key)
            merged.append(ch)

        ranked = self.reranker.rerank(query, merged, self.top_n) if merged else []
        trace["merged_contexts"] = len(merged)
        trace["final_context_sources"] = {
            "corpus": sum(1 for c in ranked if c.source == "corpus"),
            "web": sum(1 for c in ranked if c.source == "web"),
        }
        trace["top_score"] = ranked[0].score if ranked else 0.0
        return {"reranked": [c.to_dict() for c in ranked],
                "contexts": [c.to_dict() for c in ranked], "trace": trace}

    def finalize_contexts(self, state: GraphState) -> GraphState:
        """No-op join node used by optional graph branches."""
        return {}

    def ground(self, state: GraphState) -> GraphState:
        """Annotate the answer with a groundedness verdict (does not rewrite the answer)."""
        if state.get("abstained"):
            return {"grounding": {"passed": True, "skipped": "abstained"}}
        contexts = [Chunk.from_dict(d) for d in
                    (state.get("contexts") or state.get("reranked") or [])]
        verdict = self.grounding.check(state["query"], state.get("answer", ""), contexts)
        return {"grounding": verdict}

    def retrieve(self, state: GraphState) -> GraphState:
        t0 = time.time()
        query = state.get("rewritten_query") or state["query"]
        chunks = self.retriever.retrieve(query, self.top_k)
        trace = dict(state.get("trace", {}))
        trace["retrieve_ms"] = round((time.time() - t0) * 1000)
        trace["n_retrieved"] = len(chunks)
        return {"retrieved": [c.to_dict() for c in chunks], "trace": trace}

    def rerank(self, state: GraphState) -> GraphState:
        t0 = time.time()
        query = state.get("rewritten_query") or state["query"]
        chunks = [Chunk.from_dict(d) for d in state.get("retrieved", [])]
        ranked = self.reranker.rerank(query, chunks, self.top_n)
        trace = dict(state.get("trace", {}))
        trace["rerank_ms"] = round((time.time() - t0) * 1000)
        trace["top_score"] = ranked[0].score if ranked else 0.0
        return {"reranked": [c.to_dict() for c in ranked],
                "contexts": [c.to_dict() for c in ranked], "trace": trace}

    def generate(self, state: GraphState) -> GraphState:
        t0 = time.time()
        contexts = [Chunk.from_dict(d) for d in
                    (state.get("contexts") or state.get("reranked") or state.get("retrieved", []))]
        result = self.generator.generate(state["query"], contexts, state.get("chat_history", []))
        trace = dict(state.get("trace", {}))
        trace["generate_ms"] = round((time.time() - t0) * 1000)
        return {"answer": result["answer"], "citations": result["citations"],
                "abstained": result["abstained"], "trace": trace}
