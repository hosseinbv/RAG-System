"""Prompt templates. Kept separate so prompt iteration doesn't touch logic."""
from __future__ import annotations

from ..core.state import Chunk

SYSTEM = """You are an Autodesk product assistant. Answer the user's question using ONLY \
the numbered sources provided. Follow these rules strictly:

1. Ground every claim in the sources. Do NOT use outside knowledge.
2. Cite sources inline with bracketed numbers like [1], [2] after the sentence they support.
3. If the sources do not contain the answer, say exactly what is missing and do not guess.
4. The documentation snapshot is dated {snapshot_date}; for "latest/newest version" questions, \
note that corpus information may be out of date as of that snapshot.
5. If live web sources are provided for latest/current/version/pricing questions, prefer those \
live web sources over stale corpus snapshot sources.
6. Be concise and factual. Prefer specifics (feature names, platforms) over vague claims."""

ABSTAIN_HINT = (
    "If the answer is not supported by the sources, begin your reply with "
    "'I don't have enough information in the Autodesk documentation to answer that' "
    "and briefly say what's missing."
)


def format_contexts(contexts: list[Chunk], snapshot_date: str) -> str:
    blocks = []
    for i, c in enumerate(contexts, 1):
        head = c.title or c.url or c.product or f"source {i}"
        source_type = (
            "live web source"
            if c.source == "web"
            else f"corpus snapshot source ({snapshot_date})"
        )
        blocks.append(f"[{i}] {head}\nSource type: {source_type}\nURL: {c.url}\n{c.text.strip()}")
    return "\n\n".join(blocks)


def build_messages(query: str, contexts: list[Chunk], chat_history: list[dict],
                   snapshot_date: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM.format(snapshot_date=snapshot_date)}]
    # include a short window of prior turns for conversational continuity
    for turn in (chat_history or [])[-4:]:
        msgs.append({"role": turn["role"], "content": turn["content"]})
    user = (
        f"{ABSTAIN_HINT}\n\nSources:\n{format_contexts(contexts, snapshot_date)}\n\n"
        f"Question: {query}\n\nAnswer (with inline [n] citations):"
    )
    msgs.append({"role": "user", "content": user})
    return msgs
