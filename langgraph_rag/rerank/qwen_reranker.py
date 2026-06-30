"""Cross-encoder reranker via vLLM's /rerank endpoint (Qwen3-Reranker).

Reranking is optional: if disabled in config the graph uses PassthroughReranker
instead, so removing it never breaks the pipeline.
"""
from __future__ import annotations

import httpx

from ..core.config import load_config
from ..core.interfaces import BaseReranker
from ..core.registry import register
from ..core.state import Chunk


@register("reranker", "qwen")
class QwenReranker(BaseReranker):
    def __init__(self):
        cfg = load_config().get_path("models.reranker")
        self.base_url = cfg["base_url"].rstrip("/")
        self.model = cfg["model"]
        self.timeout = cfg.get("timeout", 60)

    def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[Chunk]:
        if not chunks:
            return []
        docs = [c.text for c in chunks]
        payload = {"model": self.model, "query": query, "documents": docs,
                   "top_n": min(top_n, len(docs))}
        # vLLM exposes /rerank (some builds /v1/rerank); try both
        last_err = None
        for path in ("/rerank", "/v1/rerank"):
            try:
                r = httpx.post(self.base_url + path, json=payload, timeout=self.timeout)
                r.raise_for_status()
                results = r.json()["results"]
                out = []
                for item in results:
                    ch = chunks[item["index"]]
                    ch.score = float(item["relevance_score"])
                    out.append(ch)
                return out[:top_n]
            except Exception as e:  # noqa: BLE001
                last_err = e
        raise RuntimeError(f"rerank endpoint failed: {last_err}")


@register("reranker", "passthrough")
class PassthroughReranker(BaseReranker):
    """No-op reranker: keeps incoming order, returns top_n. Used when rerank disabled."""

    def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[Chunk]:
        return chunks[:top_n]
