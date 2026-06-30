"""Thin client for the OpenAI-compatible embedding endpoint (served by vLLM).

Keeping this behind one function means switching embedding models/backends is a
config change only. Returns L2-normalized vectors so dot product == cosine.
"""
from __future__ import annotations

import numpy as np
from openai import OpenAI

from ..core.config import load_config


def _client() -> tuple[OpenAI, str]:
    cfg = load_config().get_path("models.embedding")
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg.get("api_key", "EMPTY"))
    return client, cfg["model"]


def embed_texts(texts: list[str], batch_size: int = 64, normalize: bool = True) -> np.ndarray:
    """Embed a list of texts -> (n, dim) float32 matrix."""
    client, model = _client()
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        out.extend(d.embedding for d in resp.data)
    arr = np.asarray(out, dtype=np.float32)
    if normalize and len(arr):
        arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12)
    return arr


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]
