from langgraph_rag.app.ui_adapter import (
    build_display_payload,
    context_rows,
    graph_history,
    stage_latency_ms,
    total_latency_ms,
    unique_citations,
)


def test_graph_history_filters_ui_metadata():
    messages = [
        {"role": "user", "content": "What does Fusion 360 do?"},
        {"role": "assistant", "content": "It is CAD software.", "payload": {"ignored": True}},
        {"role": "system", "content": "ignore me"},
        {"role": "user", "content": "   "},
    ]

    assert graph_history(messages) == [
        {"role": "user", "content": "What does Fusion 360 do?"},
        {"role": "assistant", "content": "It is CAD software."},
    ]


def test_unique_citations_dedupes_by_url():
    citations = [
        {"n": 1, "title": "Fusion", "url": "https://example.com/fusion", "chunk_id": "a::0"},
        {"n": 2, "title": "Fusion duplicate", "url": "https://example.com/fusion", "chunk_id": "a::1"},
        {"n": 3, "title": "Maya", "url": "https://example.com/maya", "chunk_id": "b::0"},
    ]

    out = unique_citations(citations)

    assert [c["n"] for c in out] == [1, 3]
    assert out[0]["title"] == "Fusion"


def test_context_rows_prefers_final_contexts():
    output = {
        "contexts": [
            {
                "id": "doc::0",
                "title": "Title",
                "url": "https://example.com",
                "score": 0.98765,
                "source": "corpus",
                "product": "maya",
                "page_type": "products",
                "text": "Context text",
            }
        ],
        "retrieved": [{"id": "other::0", "text": "wrong"}],
    }

    rows = context_rows(output)

    assert len(rows) == 1
    assert rows[0]["chunk_id"] == "doc::0"
    assert rows[0]["score"] == 0.9877


def test_build_display_payload_summarizes_trace_and_contexts():
    output = {
        "answer": "Fusion 360 is cloud-based [1].",
        "abstained": False,
        "citations": [{"n": 1, "title": "Fusion", "url": "https://example.com", "chunk_id": "d::0"}],
        "contexts": [{"id": "d::0", "text": "Fusion 360 is cloud-based.", "score": 0.9}],
        "trace": {
            "retrieve_ms": 10,
            "rerank_ms": 20,
            "generate_ms": 30,
            "web_ms": 5,
            "top_score": 0.9,
        },
        "grounding": {"groundedness": 1.0},
    }

    payload = build_display_payload("What is Fusion 360?", output)

    assert payload["metrics"]["retrieve_ms"] == 10
    assert payload["metrics"]["rerank_ms"] == 20
    assert payload["metrics"]["generate_ms"] == 30
    assert payload["metrics"]["web_ms"] == 5
    assert payload["metrics"]["total_latency_ms"] == 65
    assert payload["metrics"]["top_score"] == 0.9
    assert payload["metrics"]["groundedness"] == 1.0
    assert payload["citations"][0]["url"] == "https://example.com"


def test_total_latency_ignores_non_timing_fields():
    assert total_latency_ms({"retrieve_ms": 12.5, "top_score": 0.9, "other": "x"}) == 12


def test_stage_latency_defaults_missing_timings_to_zero():
    latencies = stage_latency_ms({"retrieve_ms": 12.5, "generate_ms": 20})

    assert latencies == {
        "retrieve_ms": 12,
        "rerank_ms": 0,
        "generate_ms": 20,
        "web_ms": 0,
        "total_latency_ms": 32,
    }
