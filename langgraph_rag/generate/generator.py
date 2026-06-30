"""Answer generator via the OpenAI-compatible chat endpoint (vLLM / Qwen3-4B).

Returns the answer plus the citations actually referenced ([n] -> source URL), which
powers both the transparent source display and citation-correctness evaluation.
"""
from __future__ import annotations

import re

from openai import OpenAI

from ..core.config import load_config
from ..core.interfaces import BaseGenerator
from ..core.registry import register
from ..core.state import Chunk
from .prompts import build_messages

_CITE = re.compile(r"\[(\d+)\]")


@register("generator", "qwen")
class QwenGenerator(BaseGenerator):
    def __init__(self):
        cfg = load_config()
        gc = cfg.get_path("models.generator")
        self.client = OpenAI(base_url=gc["base_url"], api_key=gc.get("api_key", "EMPTY"))
        self.model = gc["model"]
        self.max_tokens = gc.get("max_tokens", 1024)
        self.temperature = gc.get("temperature", 0.2)
        self.snapshot_date = cfg.get_path("paths.snapshot_date", "")

    def generate(self, query: str, contexts: list[Chunk], chat_history: list[dict]) -> dict:
        messages = build_messages(query, contexts, chat_history, self.snapshot_date)
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages,
            max_tokens=self.max_tokens, temperature=self.temperature,
        )
        answer = resp.choices[0].message.content.strip()
        citations = self._extract_citations(answer, contexts)
        abstained = answer.lower().startswith("i don't have enough information")
        return {"answer": answer, "citations": citations, "abstained": abstained}

    @staticmethod
    def _extract_citations(answer: str, contexts: list[Chunk]) -> list[dict]:
        used = sorted({int(n) for n in _CITE.findall(answer)})
        cites = []
        for n in used:
            if 1 <= n <= len(contexts):
                c = contexts[n - 1]
                cites.append({"n": n, "url": c.url, "title": c.title, "chunk_id": c.id})
        return cites
