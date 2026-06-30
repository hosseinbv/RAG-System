"""Phase 2: retrieval fusion, reranker passthrough, citation extraction, graph build.
Pure-logic tests run without servers; the end-to-end smoke test is gated on a live stack.
"""
import os
import pytest

from langgraph_rag.core.state import Chunk
from langgraph_rag.rerank.qwen_reranker import PassthroughReranker
from langgraph_rag.generate.generator import QwenGenerator


def _c(cid, text="t", **kw):
    return Chunk(id=cid, text=text, **kw)


def test_passthrough_reranker_keeps_order_and_truncates():
    chunks = [_c("a"), _c("b"), _c("c")]
    out = PassthroughReranker().rerank("q", chunks, top_n=2)
    assert [c.id for c in out] == ["a", "b"]


def test_citation_extraction_maps_brackets_to_sources():
    ctx = [_c("x0", url="u0", title="T0"), _c("x1", url="u1", title="T1"), _c("x2")]
    ans = "Fusion does CAD [1]. It also does CAM [2][2]. Out of range [9] ignored."
    cites = QwenGenerator._extract_citations(ans, ctx)
    ns = [c["n"] for c in cites]
    assert ns == [1, 2]                       # deduped, sorted, in-range only
    assert cites[0]["url"] == "u0" and cites[1]["chunk_id"] == "x1"


def test_rrf_fusion_rewards_agreement(monkeypatch):
    from langgraph_rag.retrieval import hybrid

    dense_run = [_c("A"), _c("B"), _c("C")]      # A best in dense
    bm25_run = [_c("B"), _c("A"), _c("D")]       # B best in bm25, A second
    monkeypatch.setattr(hybrid.DenseRetriever, "retrieve",
                        lambda self, q, k: list(dense_run))
    monkeypatch.setattr(hybrid.BM25Retriever, "retrieve",
                        lambda self, q, k: list(bm25_run))

    h = hybrid.HybridRetriever.__new__(hybrid.HybridRetriever)
    h.rrf_k = 60
    h.dense = hybrid.DenseRetriever.__new__(hybrid.DenseRetriever)
    h.bm25 = hybrid.BM25Retriever.__new__(hybrid.BM25Retriever)
    out = h.retrieve("q", top_k=4)
    ids = [c.id for c in out]
    # A and B appear in both runs near the top -> should outrank C/D (single-list)
    assert set(ids[:2]) == {"A", "B"}
    assert ids[-1] in {"C", "D"}


@pytest.mark.skipif(os.environ.get("RAG_STACK_UP") != "1",
                    reason="needs live embedding+rerank+generator servers")
def test_end_to_end_smoke():
    from langgraph_rag.graph.build_graph import run_query
    out = run_query("What does Fusion 360 do?")
    assert out["answer"]
    assert "retrieve_ms" in out["trace"]
