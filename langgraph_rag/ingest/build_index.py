"""Phase 1b: build the retrieval indexes from chunks.jsonl.

Produces (all under data/index/):
  embeddings.npy   (n, dim) float32, L2-normalized   -> dense search
  chunks.jsonl     chunk metadata in row order        -> id/url/text lookup
  bm25.pkl         tokenized corpus + BM25Okapi       -> lexical search

We use a transparent numpy-backed dense store (corpus is small). It sits behind the
BaseRetriever interface, so swapping in Chroma/FAISS/Qdrant later is a config change.
"""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from ..core.config import load_config
from ..obs.report import add_section
from ..retrieval.embedding_client import embed_texts

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def build() -> dict:
    cfg = load_config()
    work = Path(cfg.get_path("paths.work_dir"))
    index_dir = work / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    chunks = [json.loads(l) for l in open(work / "chunks.jsonl")]
    texts = [c["text"] for c in chunks]

    # dense
    emb = embed_texts(texts)
    np.save(index_dir / "embeddings.npy", emb)

    # lexical
    bm25 = BM25Okapi([tokenize(t) for t in texts])
    with open(index_dir / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)

    # row-aligned metadata copy
    with open(index_dir / "chunks.jsonl", "w") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    stats = {
        "n_chunks": len(chunks),
        "embedding_dim": int(emb.shape[1]) if len(emb) else 0,
        "embedding_model": cfg.get_path("models.embedding.model"),
        "index_dir": str(index_dir),
    }
    add_section("Phase 1b — Index build", f"""**Status: DONE.**
- Indexed **{stats['n_chunks']}** chunks.
- Dense: `embeddings.npy` ({stats['embedding_dim']}-d, normalized) via `{stats['embedding_model']}`.
- Lexical: BM25Okapi over tokenized chunks (`bm25.pkl`).
- Transparent numpy-backed store behind `BaseRetriever` (swap to Chroma/FAISS = config change).
""")
    return stats


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
