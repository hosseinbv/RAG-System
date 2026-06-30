"""Structure-aware chunking.

Our cleaned text is newline-separated paragraphs (trafilatura/bs4 output). We build
chunks by accumulating whole paragraphs up to a token budget, with overlap, so we never
split mid-sentence. Each chunk is prefixed with the doc title for retrieval context.

Token counts are approximated from words (no model tokenizer needed at ingest time):
  tokens ~= words / 0.75   ->   words_budget = target_tokens * 0.75
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.config import load_config
from ..core.state import Chunk

_WORDS_PER_TOKEN = 0.75


def _wbudget(tokens: int) -> int:
    return max(1, int(tokens * _WORDS_PER_TOKEN))


def chunk_text(text: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    """Greedy paragraph-packing with word-overlap between consecutive chunks."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    budget = _wbudget(target_tokens)
    overlap = _wbudget(overlap_tokens)

    chunks: list[str] = []
    cur: list[str] = []          # list of words in the current chunk
    for para in paras:
        words = para.split()
        if not words:
            continue
        # a single huge paragraph: hard-split into budget-sized windows
        if len(words) > budget:
            if cur:
                chunks.append(" ".join(cur))
                cur = []
            for i in range(0, len(words), budget):
                chunks.append(" ".join(words[i:i + budget]))
            continue
        if len(cur) + len(words) > budget and cur:
            chunks.append(" ".join(cur))
            cur = cur[-overlap:] if overlap else []   # carry overlap forward
        cur.extend(words)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def build_chunks(docs_path: str | None = None, out_path: str | None = None) -> dict:
    cfg = load_config()
    work = Path(cfg.get_path("paths.work_dir"))
    docs_path = Path(docs_path or work / "clean_docs.jsonl")
    out_path = Path(out_path or work / "chunks.jsonl")
    target = cfg.get_path("ingest.chunk.target_tokens", 512)
    overlap = cfg.get_path("ingest.chunk.overlap_tokens", 64)

    n_docs = 0
    n_chunks = 0
    with open(docs_path) as f, open(out_path, "w") as out:
        for line in f:
            doc = json.loads(line)
            n_docs += 1
            pieces = chunk_text(doc["text"], target, overlap)
            title = doc.get("title", "")
            for i, piece in enumerate(pieces):
                # prepend title so each chunk is self-describing for retrieval
                body = f"{title}\n\n{piece}" if title else piece
                ch = Chunk(
                    id=f"{doc['id']}::{i}",
                    text=body,
                    url=doc.get("url", ""),
                    title=title,
                    product=doc.get("product", ""),
                    page_type=doc.get("page_type", ""),
                    snapshot_date=doc.get("snapshot_date", ""),
                    source="corpus",
                    extra={"doc_id": doc["id"], "chunk_index": i},
                )
                out.write(json.dumps(ch.to_dict(), ensure_ascii=False) + "\n")
                n_chunks += 1
    return {"docs": n_docs, "chunks": n_chunks, "out_path": str(out_path),
            "target_tokens": target, "overlap_tokens": overlap}


if __name__ == "__main__":
    print(json.dumps(build_chunks(), indent=2))
