"""Conversation rewrite: turn a context-dependent follow-up ("does it run on Mac?")
into a standalone query ("does Fusion 360 run on Mac?") for retrieval.

Guarded by a heuristic so we only rewrite when needed — rewriting an already-standalone
query risks corrupting it. Uses the generator LLM; if it errors, we fall back to the
raw query (graceful degradation).
"""
from __future__ import annotations

import re

from openai import OpenAI

from ..core.config import load_config
from ..core.registry import register

# pronouns / deictics / elliptical openers that signal dependence on prior turns
_DEPENDENT = re.compile(
    r"\b(it|its|they|them|their|that|this|these|those|the same|he|she|"
    r"one|ones)\b|^(and|what about|how about|why|and what|ok|also)\b",
    re.I,
)

_REWRITE_SYS = (
    "Rewrite the user's latest message into a fully self-contained search query using the "
    "conversation context. Resolve pronouns and references to explicit product names. "
    "Return ONLY the rewritten query, no preamble."
)


def is_context_dependent(text: str) -> bool:
    return bool(_DEPENDENT.search(text.strip()))


@register("guard", "conversation_rewrite")
class ConversationRewriter:
    def __init__(self, cfg=None):
        cfg = cfg or load_config()
        gc = cfg.get_path("models.generator")
        self.client = OpenAI(base_url=gc["base_url"], api_key=gc.get("api_key", "EMPTY"))
        self.model = gc["model"]

    def rewrite(self, query: str, chat_history: list[dict]) -> str:
        if not chat_history or not is_context_dependent(query):
            return query                       # standalone -> leave untouched
        convo = "\n".join(f"{t['role']}: {t['content']}" for t in chat_history[-4:])
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.0, max_tokens=128,
                messages=[
                    {"role": "system", "content": _REWRITE_SYS},
                    {"role": "user", "content": f"Conversation:\n{convo}\n\nLatest: {query}"},
                ],
            )
            out = resp.choices[0].message.content.strip().strip('"')
            return out or query
        except Exception:                       # noqa: BLE001 - degrade to raw query
            return query
