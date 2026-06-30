"""Phase 5: web fallback trigger logic, retriever shape, and graph wiring.

These tests do not use live internet. The WebRetriever network call is stubbed so
CI/local unit tests stay deterministic.
"""
from copy import deepcopy

from langgraph_rag.core.config import Config, load_config
from langgraph_rag.core.state import Chunk
from langgraph_rag.graph.build_graph import build_pipeline
from langgraph_rag.graph.nodes import Nodes, should_use_web
from langgraph_rag.rerank.qwen_reranker import PassthroughReranker
from langgraph_rag.retrieval.web import (
    WebRetriever,
    _is_allowed_url,
    _normalize_result_url,
)


def _cfg(web_enabled: bool = True) -> Config:
    cfg = Config(deepcopy(load_config()))
    cfg["web"]["enabled"] = web_enabled
    return cfg


def test_web_trigger_recency_in_domain():
    cfg = _cfg()
    use_web, reason = should_use_web("What's the latest release for Maya?", 0.99, 5, cfg)
    assert use_web is True
    assert reason == "recency_or_dynamic_in_domain"


def test_web_trigger_low_confidence_in_domain_only():
    cfg = _cfg()
    assert should_use_web("AutoCAD subscription details", 0.1, 5, cfg)[0] is True
    assert should_use_web("Autodesk Revit subscription install count", 0.99, 5, cfg)[0] is False
    assert should_use_web("What is the capital of France?", 0.1, 5, cfg)[0] is False
    assert should_use_web("What does Fusion 360 do?", 0.9, 5, cfg)[0] is False


def test_web_url_helpers():
    ddg = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.autodesk.com%2Fproducts%2Fmaya%2Foverview"
    url = _normalize_result_url(ddg)
    assert url == "https://www.autodesk.com/products/maya/overview"
    assert _is_allowed_url(url, ["autodesk.com"])
    assert not _is_allowed_url("https://example.com/products/maya", ["autodesk.com"])


def test_web_retriever_returns_chunks_without_fetch(monkeypatch):
    cfg = _cfg()
    cfg["web"]["fetch_pages"] = False
    retriever = WebRetriever(cfg)
    monkeypatch.setattr(
        retriever,
        "_search_duckduckgo_html",
        lambda query, top_k: [
            {
                "title": "Maya latest features",
                "url": "https://www.autodesk.com/products/maya/features",
                "snippet": "Maya includes tools for animation, modeling, simulation, and rendering.",
            }
        ],
    )
    out = retriever.retrieve("latest Maya release", top_k=3)
    assert len(out) == 1
    assert out[0].source == "web"
    assert out[0].product == "maya"
    assert out[0].url.endswith("/products/maya/features")


def test_merge_contexts_preserves_corpus_contexts_when_web_empty():
    nodes = Nodes.__new__(Nodes)
    nodes.reranker = PassthroughReranker()
    nodes.top_n = 5
    corpus = [
        Chunk(id="c1", text="Corpus answer", url="https://www.autodesk.com/a",
              score=0.9).to_dict()
    ]
    state = {
        "query": "latest Maya release",
        "reranked": corpus,
        "contexts": corpus,
        "web_results": [],
        "trace": {"web_triggered": True, "n_web_results": 0},
    }

    out = nodes.merge_contexts(state)

    assert "contexts" not in out
    assert "reranked" not in out
    assert out["trace"]["web_fallback_failed"] is True
    assert out["trace"]["final_context_sources"] == {"corpus": 1, "web": 0}


def test_graph_wires_web_nodes_only_when_enabled():
    cfg = _cfg(web_enabled=True)
    nodes = set(build_pipeline(cfg).get_graph().nodes)
    assert {"decide_web", "web_retrieve", "merge_contexts", "finalize_contexts"} <= nodes

    cfg_off = _cfg(web_enabled=False)
    nodes_off = set(build_pipeline(cfg_off).get_graph().nodes)
    assert "decide_web" not in nodes_off
