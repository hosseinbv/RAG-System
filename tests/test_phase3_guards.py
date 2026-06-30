"""Phase 3: pure-logic guard tests (no servers) + gated e2e for LLM-backed guards."""
import os
import pytest

from langgraph_rag.guards.abstention import AbstentionGuard
from langgraph_rag.guards.conversation_rewrite import is_context_dependent
from langgraph_rag.guards.grounding import split_claims


def test_abstention_threshold():
    g = AbstentionGuard()
    g.min_score = 0.30
    assert g.should_abstain(top_score=0.1, n_contexts=5) is True
    assert g.should_abstain(top_score=0.9, n_contexts=5) is False
    assert g.should_abstain(top_score=0.9, n_contexts=0) is True   # nothing retrieved


def test_context_dependence_detection():
    assert is_context_dependent("Does it run on Mac?")          # pronoun
    assert is_context_dependent("What about Revit?")            # elliptical
    assert not is_context_dependent("What does Fusion 360 do?")  # standalone


def test_split_claims_filters_noise():
    ans = "Fusion 360 is CAD software [1]. It also has CAM [2]. [3]"
    claims = split_claims(ans)
    assert len(claims) == 2                 # citation-only fragment dropped
    assert "Fusion 360 is CAD software" in claims[0]


@pytest.mark.skipif(os.environ.get("RAG_STACK_UP") != "1",
                    reason="needs live stack incl. judge server")
def test_e2e_conversation_rewrite_resolves_pronoun():
    from langgraph_rag.graph.build_graph import build_pipeline
    app = build_pipeline()
    hist = [{"role": "user", "content": "What does Fusion 360 do?"},
            {"role": "assistant", "content": "It is a 3D CAD/CAM tool."}]
    out = app.invoke({"query": "Does it run on a Mac?", "chat_history": hist})
    assert out["trace"].get("rewritten") is True
    assert "fusion" in out["rewritten_query"].lower()   # pronoun resolved to product


@pytest.mark.skipif(os.environ.get("RAG_STACK_UP") != "1",
                    reason="needs live stack incl. judge server")
def test_e2e_grounding_annotates_answer():
    from langgraph_rag.graph.build_graph import build_pipeline
    out = build_pipeline().invoke({"query": "Does AutoCAD LT do 3D?", "chat_history": []})
    g = out["grounding"]
    assert "groundedness" in g and 0.0 <= g["groundedness"] <= 1.0
