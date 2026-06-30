"""Hybrid retriever: fuse dense + BM25 with Reciprocal Rank Fusion (RRF).

RRF is rank-based, so it sidesteps the dense/BM25 score-scale mismatch. Each chunk's
fused score = sum over retrievers of 1/(rrf_k + rank). Degrades gracefully: if either
sub-retriever is disabled in config, it just uses the other.
"""
from __future__ import annotations

from ..core.config import load_config
from ..core.interfaces import BaseRetriever
from ..core.registry import register
from ..core.state import Chunk
from .bm25 import BM25Retriever
from .dense import DenseRetriever


@register("retriever", "hybrid")
class HybridRetriever(BaseRetriever):
    def __init__(self, index_dir: str | None = None):
        cfg = load_config()
        self.rrf_k = cfg.get_path("retrieval.hybrid.rrf_k", 60)
        self.dense = DenseRetriever(index_dir)
        self.bm25 = BM25Retriever(index_dir)

    def retrieve(self, query: str, top_k: int) -> list[Chunk]:
        # over-fetch from each arm so fusion has material to work with
        pool = max(top_k * 2, 20)
        runs = [self.dense.retrieve(query, pool), self.bm25.retrieve(query, pool)]

        fused: dict[str, float] = {}
        keep: dict[str, Chunk] = {}
        for run in runs:
            for rank, ch in enumerate(run):
                fused[ch.id] = fused.get(ch.id, 0.0) + 1.0 / (self.rrf_k + rank)
                keep.setdefault(ch.id, ch)

        ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]
        out = []
        for cid, score in ranked:
            ch = keep[cid]
            ch.score = score
            out.append(ch)
        return out
