import json

import pytest

from langgraph_rag.app.feedback_store import (
    append_feedback,
    build_feedback_record,
    load_feedback,
    submit_feedback,
)


def _messages():
    return [
        {"role": "user", "content": "What does Fusion 360 do?", "id": "u1"},
        {
            "role": "assistant",
            "content": "Fusion 360 is CAD/CAM software [1].",
            "id": "a1",
            "payload": {
                "question": "What does Fusion 360 do?",
                "answer": "Fusion 360 is CAD/CAM software [1].",
                "abstained": False,
                "citations": [
                    {
                        "n": 1,
                        "title": "Fusion overview",
                        "url": "https://example.com/fusion",
                        "chunk_id": "doc-1::0",
                    }
                ],
                "contexts": [
                    {
                        "rank": 1,
                        "title": "Fusion overview",
                        "url": "https://example.com/fusion",
                        "chunk_id": "doc-1::0",
                        "score": 0.93,
                        "text": "Fusion 360 combines CAD and CAM.",
                    }
                ],
                "trace": {"retrieve_ms": 10, "top_score": 0.93},
                "metrics": {"top_score": 0.93, "total_latency_ms": 42},
            },
        },
    ]


def test_build_feedback_record_includes_review_evidence():
    record = build_feedback_record(
        session_id="session-1",
        messages=_messages(),
        assistant_index=1,
        label="negative",
        comment="Citation is useful, but answer is too short.",
        feedback_id="feedback-1",
    )

    assert record["id"] == "feedback-1"
    assert record["session_id"] == "session-1"
    assert record["turn_id"] == "session-1:1"
    assert record["query"] == "What does Fusion 360 do?"
    assert record["answer"] == "Fusion 360 is CAD/CAM software [1]."
    assert record["label"] == "negative"
    assert record["comment"] == "Citation is useful, but answer is too short."
    assert record["citations"][0]["chunk_id"] == "doc-1::0"
    assert record["context_ids"] == ["doc-1::0"]
    assert record["source_urls"] == ["https://example.com/fusion"]
    assert record["top_score"] == 0.93
    assert record["total_latency_ms"] == 42
    assert record["review_status"] == "new"


def test_append_and_load_feedback_jsonl(tmp_path):
    path = tmp_path / "feedback.jsonl"
    positive = build_feedback_record(
        session_id="session-1",
        messages=_messages(),
        assistant_index=1,
        label="positive",
        feedback_id="positive-1",
    )
    negative = build_feedback_record(
        session_id="session-1",
        messages=_messages(),
        assistant_index=1,
        label="negative",
        feedback_id="negative-1",
    )

    append_feedback(positive, path)
    append_feedback(negative, path)

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "positive-1"
    assert [record["id"] for record in load_feedback(path)] == ["positive-1", "negative-1"]
    assert [record["id"] for record in load_feedback(path, label="negative")] == ["negative-1"]


def test_submit_feedback_builds_and_appends_record(tmp_path):
    path = tmp_path / "feedback.jsonl"

    record = submit_feedback(
        session_id="session-1",
        messages=_messages(),
        assistant_index=1,
        label="positive",
        comment="Looks good.",
        feedback_path=path,
    )

    loaded = load_feedback(path)
    assert loaded == [record]
    assert loaded[0]["comment"] == "Looks good."


def test_invalid_label_is_rejected():
    with pytest.raises(ValueError, match="invalid feedback label"):
        build_feedback_record(
            session_id="session-1",
            messages=_messages(),
            assistant_index=1,
            label="maybe",
        )


def test_feedback_requires_assistant_turn_with_preceding_user():
    with pytest.raises(ValueError, match="not an assistant message"):
        build_feedback_record(
            session_id="session-1",
            messages=_messages(),
            assistant_index=0,
            label="positive",
        )

    with pytest.raises(ValueError, match="preceding user"):
        build_feedback_record(
            session_id="session-1",
            messages=[_messages()[1]],
            assistant_index=0,
            label="positive",
        )
