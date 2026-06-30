"""Dense retriever over the numpy-backed embedding store.

Loads embeddings.npy + chunks.jsonl once; cosine search via a single matmul
(embeddings are pre-normalized, so dot product == cosine similarity).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..core.config import load_config
from ..core.interfaces import BaseRetriever
from ..core.registry import register
from ..core.state import Chunk
from .embedding_client import embed_query


@lru_cache(maxsize=2)
def _load_store(index_dir: str) -> tuple[np.ndarray, list[dict]]:
    d = Path(index_dir)
    emb = np.load(d / "embeddings.npy")
    chunks = [json.loads(l) for l in open(d / "chunks.jsonl")]
    return emb, chunks


@register("retriever", "dense")
class DenseRetriever(BaseRetriever):
    def __init__(self, index_dir: str | None = None):
        self.index_dir = index_dir or str(
            Path(load_config().get_path("paths.work_dir")) / "index"
        )

    def retrieve(self, query: str, top_k: int) -> list[Chunk]:
        emb, chunks = _load_store(self.index_dir)
        q = embed_query(query)
        scores = emb @ q                      # (n,)
        idx = np.argsort(-scores)[:top_k]
        out = []
        for i in idx:
            c = Chunk.from_dict(chunks[int(i)])
            c.score = float(scores[int(i)])
            out.append(c)
        return out
