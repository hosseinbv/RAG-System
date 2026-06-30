"""Small presentation helpers for the chat UI.

The Streamlit app should stay mostly concerned with rendering. These helpers turn raw
LangGraph outputs into stable display payloads that are easy to test without a browser or
live model services.
"""
from __future__ import annotations

from typing import Any


def graph_history(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert UI messages to the chat_history shape expected by the graph."""
    history: list[dict[str, str]] = []
    for msg in messages:
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def total_latency_ms(trace: dict[str, Any]) -> int:
    """Sum node timings recorded as `*_ms` trace fields."""
    return int(sum(v for k, v in trace.items() if k.endswith("_ms") and isinstance(v, int | float)))


def stage_latency_ms(trace: dict[str, Any]) -> dict[str, int]:
    """Return UI-facing per-stage latency counters from graph trace timings."""
    return {
        "retrieve_ms": int(trace.get("retrieve_ms") or 0),
        "rerank_ms": int(trace.get("rerank_ms") or 0),
        "generate_ms": int(trace.get("generate_ms") or 0),
        "web_ms": int(trace.get("web_ms") or 0),
        "total_latency_ms": total_latency_ms(trace),
    }


def unique_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate citations by URL first, then chunk id."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for citation in citations or []:
        key = citation.get("url") or citation.get("chunk_id") or str(citation)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "n": citation.get("n"),
            "title": citation.get("title") or "Untitled source",
            "url": citation.get("url") or "",
            "chunk_id": citation.get("chunk_id") or "",
        })
    return out


def context_rows(output: dict[str, Any]) -> list[dict[str, Any]]:
    """Return display-ready final context rows."""
    contexts = output.get("contexts") or output.get("reranked") or output.get("retrieved") or []
    rows: list[dict[str, Any]] = []
    for i, ctx in enumerate(contexts, start=1):
        rows.append({
            "rank": i,
            "title": ctx.get("title") or "Untitled source",
            "url": ctx.get("url") or "",
            "chunk_id": ctx.get("id") or "",
            "score": round(float(ctx.get("score", 0.0)), 4),
            "source": ctx.get("source", "corpus"),
            "product": ctx.get("product", ""),
            "page_type": ctx.get("page_type", ""),
            "text": ctx.get("text", ""),
        })
    return rows


def build_display_payload(question: str, output: dict[str, Any]) -> dict[str, Any]:
    """Normalize graph output for the UI layer."""
    trace = output.get("trace") or {}
    grounding = output.get("grounding") or {}
    latencies = stage_latency_ms(trace)
    return {
        "question": question,
        "answer": str(output.get("answer", "")).strip(),
        "abstained": bool(output.get("abstained", False)),
        "citations": unique_citations(output.get("citations", [])),
        "contexts": context_rows(output),
        "trace": trace,
        "grounding": grounding,
        "metrics": {
            "top_score": round(float(trace.get("top_score", 0.0)), 4),
            **latencies,
            "web_triggered": bool(trace.get("web_triggered", False)),
            "n_web_results": int(trace.get("n_web_results") or 0),
            "groundedness": grounding.get("groundedness"),
        },
    }


def service_error_message(exc: Exception) -> str:
    """Short user-facing model-service failure message."""
    detail = str(exc).strip()
    if len(detail) > 300:
        detail = detail[:297] + "..."
    return (
        "The RAG pipeline could not complete the request. Check that the vLLM model "
        f"services are running, then try again. Details: {detail}"
    )
