"""Lexical (BM25) retriever. Good for exact tokens dense retrieval fumbles:
product names, edition suffixes ("AutoCAD LT"), version strings."""
from __future__ import annotations

import json
import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..core.config import load_config
from ..core.interfaces import BaseRetriever
from ..core.registry import register
from ..core.state import Chunk
from ..ingest.build_index import tokenize


@lru_cache(maxsize=2)
def _load_bm25(index_dir: str):
    d = Path(index_dir)
    with open(d / "bm25.pkl", "rb") as f:
        bm25 = pickle.load(f)
    chunks = [json.loads(l) for l in open(d / "chunks.jsonl")]
    return bm25, chunks


@register("retriever", "bm25")
class BM25Retriever(BaseRetriever):
    def __init__(self, index_dir: str | None = None):
        self.index_dir = index_dir or str(
            Path(load_config().get_path("paths.work_dir")) / "index"
        )

    def retrieve(self, query: str, top_k: int) -> list[Chunk]:
        bm25, chunks = _load_bm25(self.index_dir)
        scores = bm25.get_scores(tokenize(query))
        idx = np.argsort(-scores)[:top_k]
        out = []
        for i in idx:
            c = Chunk.from_dict(chunks[int(i)])
            c.score = float(scores[int(i)])
            out.append(c)
        return out
