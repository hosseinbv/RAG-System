"""Local feedback logging for the Streamlit chat UI.

Feedback is stored as append-only JSONL under `data/ui/feedback.jsonl`. Each record keeps
the answer, cited evidence, final context ids, and trace fields needed for later review or
conversion into curated eval examples.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..core.config import load_config
from .session_store import utc_now

VALID_FEEDBACK_LABELS = {"positive", "negative"}


def default_feedback_path() -> Path:
    return Path(load_config().get_path("paths.work_dir")) / "ui" / "feedback.jsonl"


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _unique_nonempty(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _message_at(messages: list[dict[str, Any]], index: int) -> dict[str, Any]:
    try:
        message = messages[index]
    except IndexError as exc:
        raise ValueError(f"assistant message index out of range: {index}") from exc
    if message.get("role") != "assistant":
        raise ValueError(f"message at index {index} is not an assistant message")
    return message


def _preceding_user(messages: list[dict[str, Any]], assistant_index: int) -> tuple[int, dict[str, Any]]:
    for index in range(assistant_index - 1, -1, -1):
        message = messages[index]
        if message.get("role") == "user":
            return index, message
    raise ValueError("feedback requires a preceding user message")


def build_feedback_record(
    *,
    session_id: str,
    messages: list[dict[str, Any]],
    assistant_index: int,
    label: str,
    comment: str = "",
    feedback_id: str | None = None,
) -> dict[str, Any]:
    """Build a review-ready feedback record for one assistant answer."""
    if label not in VALID_FEEDBACK_LABELS:
        raise ValueError(f"invalid feedback label: {label!r}")

    assistant = _message_at(messages, assistant_index)
    user_index, user = _preceding_user(messages, assistant_index)
    payload = assistant.get("payload") or {}
    citations = _jsonable(payload.get("citations") or [])
    contexts = _jsonable(payload.get("contexts") or [])
    trace = _jsonable(payload.get("trace") or {})
    metrics = _jsonable(payload.get("metrics") or {})

    context_ids = _unique_nonempty([
        ctx.get("chunk_id") or ctx.get("id")
        for ctx in contexts
        if isinstance(ctx, dict)
    ])
    source_urls = _unique_nonempty(
        [
            citation.get("url")
            for citation in citations
            if isinstance(citation, dict)
        ]
        + [
            ctx.get("url")
            for ctx in contexts
            if isinstance(ctx, dict)
        ]
    )

    record = {
        "id": feedback_id or uuid.uuid4().hex,
        "created_at": utc_now(),
        "review_status": "new",
        "session_id": str(session_id),
        "turn_id": f"{session_id}:{assistant_index}",
        "assistant_message_index": assistant_index,
        "assistant_message_id": str(assistant.get("id") or ""),
        "user_message_index": user_index,
        "user_message_id": str(user.get("id") or ""),
        "query": str(user.get("content") or payload.get("question") or ""),
        "answer": str(assistant.get("content") or payload.get("answer") or ""),
        "label": label,
        "comment": str(comment or "").strip(),
        "citations": citations,
        "context_ids": context_ids,
        "source_urls": source_urls,
        "trace": trace,
        "metrics": metrics,
        "top_score": metrics.get("top_score", trace.get("top_score", 0.0)),
        "total_latency_ms": metrics.get("total_latency_ms", 0),
        "abstained": bool(payload.get("abstained", False)),
    }
    return _jsonable(record)


def append_feedback(
    record: dict[str, Any],
    feedback_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one feedback record to the local JSONL queue."""
    path = Path(feedback_path) if feedback_path else default_feedback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _jsonable(record)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(normalized, ensure_ascii=False) + "\n")
    return normalized


def submit_feedback(
    *,
    session_id: str,
    messages: list[dict[str, Any]],
    assistant_index: int,
    label: str,
    comment: str = "",
    feedback_path: str | Path | None = None,
) -> dict[str, Any]:
    record = build_feedback_record(
        session_id=session_id,
        messages=messages,
        assistant_index=assistant_index,
        label=label,
        comment=comment,
    )
    return append_feedback(record, feedback_path)


def load_feedback(
    feedback_path: str | Path | None = None,
    *,
    label: str | None = None,
) -> list[dict[str, Any]]:
    """Load feedback records, optionally filtering by label for review."""
    if label is not None and label not in VALID_FEEDBACK_LABELS:
        raise ValueError(f"invalid feedback label: {label!r}")

    path = Path(feedback_path) if feedback_path else default_feedback_path()
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if label is None or record.get("label") == label:
            records.append(record)
    return records
