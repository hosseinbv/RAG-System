"""Assemble the LangGraph from config. Optional nodes are wired only when enabled,
so toggling a flag in settings.yaml adds/removes a stage without code changes.

Full graph (guards + web on):
  START -> rewrite -> retrieve -> rerank -> decide_web
                                      |-> finalize -> [abstain_gate] -> generate/abstain
                                      |-> web_retrieve -> merge_contexts -> finalize -> ...

Each guard is independent: disable conversation_rewrite / abstention / grounding in config
and the graph re-wires around it. With all guards off it collapses to Phase 2's
retrieve -> rerank -> generate.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ..core.config import load_config
from ..core.state import GraphState
from .nodes import Nodes


def build_pipeline(cfg=None):
    cfg = cfg or load_config()
    nodes = Nodes(cfg)
    g = StateGraph(GraphState)

    rewrite_on = cfg.get_path("guards.conversation_rewrite.enabled", True)
    abstain_on = cfg.get_path("guards.abstention.enabled", True)
    ground_on = cfg.get_path("guards.grounding.enabled", True)
    web_on = cfg.get_path("web.enabled", False)

    # core nodes
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("rerank", nodes.rerank)
    g.add_node("generate", nodes.generate)
    if web_on:
        g.add_node("decide_web", nodes.decide_web)
        g.add_node("web_retrieve", nodes.web_retrieve)
        g.add_node("merge_contexts", nodes.merge_contexts)
        g.add_node("finalize_contexts", nodes.finalize_contexts)
    if rewrite_on:
        g.add_node("rewrite", nodes.rewrite)
    if abstain_on:
        g.add_node("abstain_response", nodes.abstain_response)
    if ground_on:
        g.add_node("ground", nodes.ground)

    # entry
    if rewrite_on:
        g.add_edge(START, "rewrite")
        g.add_edge("rewrite", "retrieve")
    else:
        g.add_edge(START, "retrieve")

    g.add_edge("retrieve", "rerank")

    # tail: where do generate/abstain_response point?
    tail = "ground" if ground_on else END

    def wire_answer_path(source: str) -> None:
        if abstain_on:
            g.add_conditional_edges(source, nodes.abstain_gate,
                                    {"answer": "generate", "abstain": "abstain_response"})
        else:
            g.add_edge(source, "generate")

    # corpus-only path: rerank -> answer path
    # web path: rerank -> decide_web -> web? -> merge -> answer path
    if web_on:
        g.add_edge("rerank", "decide_web")
        g.add_conditional_edges("decide_web", nodes.web_route,
                                {"web": "web_retrieve", "answer": "finalize_contexts"})
        g.add_edge("web_retrieve", "merge_contexts")
        g.add_edge("merge_contexts", "finalize_contexts")
        wire_answer_path("finalize_contexts")
        if abstain_on:
            g.add_edge("abstain_response", tail)
    else:
        wire_answer_path("rerank")
        if abstain_on:
            g.add_edge("abstain_response", tail)

    g.add_edge("generate", tail)
    if ground_on:
        g.add_edge("ground", END)

    return g.compile()


def run_query(query: str, chat_history: list[dict] | None = None, cfg=None) -> dict:
    app = build_pipeline(cfg)
    state = {"query": query, "chat_history": chat_history or []}
    return app.invoke(state)
