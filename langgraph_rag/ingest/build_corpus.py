"""Phase 1a: turn the raw HTML dump into a clean, deduped, metadata-rich doc set.

Run:  python -m langgraph_rag.ingest.build_corpus
Outputs:
  data/clean_docs.jsonl   one JSON doc per line (id, url, title, product, page_type, text)
  reports/corpus_stats.md  selection rationale + kept/dropped breakdown
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from tqdm import tqdm

from ..core.config import load_config
from ..obs.report import add_section, md_table
from .clean import extract_main_text, is_junk
from .metadata import extract_meta

_MIN_TEXT_CHARS = 200       # after extraction, drop near-empty pages


def _doc_id(path: Path) -> str:
    return path.stem


def build() -> dict:
    cfg = load_config()
    corpus_dir = Path(cfg.get_path("paths.corpus_dir"))
    work_dir = Path(cfg.get_path("paths.work_dir"))
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = work_dir / "clean_docs.jsonl"

    min_bytes = cfg.get_path("ingest.min_bytes", 3072)
    english_only = cfg.get_path("ingest.english_only", True)
    drop_types = set(cfg.get_path("ingest.drop_page_types", []))

    files = sorted(corpus_dir.glob("*.html"))
    drop = Counter()
    kept_by_type: Counter = Counter()
    method_used: Counter = Counter()
    char_counts: list[int] = []
    seen_text_hashes: set[str] = set()
    kept = 0

    with open(out_path, "w") as out:
        for path in tqdm(files, desc="ingest"):
            raw = path.read_bytes()
            if len(raw) < min_bytes:
                drop["too_small"] += 1
                continue
            html = raw.decode("utf-8", errors="ignore")
            if is_junk(html):
                drop["junk_block_page"] += 1
                continue
            meta = extract_meta(html)
            if english_only and meta.lang and not meta.is_english:
                drop["non_english"] += 1
                continue
            if meta.page_type in drop_types:
                drop["dropped_page_type"] += 1
                continue

            text, method = extract_main_text(html)
            if len(text) < _MIN_TEXT_CHARS:
                drop["empty_after_extraction"] += 1
                continue

            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
            if text_hash in seen_text_hashes:
                drop["duplicate_content"] += 1
                continue
            seen_text_hashes.add(text_hash)

            doc = {
                "id": _doc_id(path),
                "url": meta.url,
                "title": meta.title,
                "product": meta.product,
                "page_type": meta.page_type or "unknown",
                "lang": meta.lang,
                "snapshot_date": cfg.get_path("paths.snapshot_date", ""),
                "extract_method": method,
                "text": text,
            }
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            kept += 1
            kept_by_type[doc["page_type"]] += 1
            method_used[method] += 1
            char_counts.append(len(text))

    stats = {
        "total_files": len(files),
        "kept": kept,
        "dropped": dict(drop),
        "kept_by_page_type": dict(kept_by_type.most_common()),
        "extract_method": dict(method_used),
        "char_stats": _char_stats(char_counts),
        "out_path": str(out_path),
    }
    _write_report(stats)
    return stats


def _char_stats(counts: list[int]) -> dict:
    if not counts:
        return {}
    counts = sorted(counts)
    n = len(counts)
    return {
        "min": counts[0], "max": counts[-1],
        "median": counts[n // 2],
        "mean": round(sum(counts) / n),
        "p10": counts[int(n * 0.10)], "p90": counts[int(n * 0.90)],
    }


def _write_report(stats: dict) -> None:
    drop_rows = [[k, v] for k, v in sorted(stats["dropped"].items(), key=lambda x: -x[1])]
    type_rows = [[k, v] for k, v in stats["kept_by_page_type"].items()]
    body = f"""**Status: DONE.** Cleaned the raw HTML dump into a deduped, metadata-rich doc set.

- Raw files: **{stats['total_files']}**  →  kept docs: **{stats['kept']}**
- Output: `{stats['out_path']}`
- Extraction methods used: {stats['extract_method']}
- Text length (chars): {stats['char_stats']}

**Dropped (selection rationale):**
{md_table(['reason', 'count'], drop_rows)}

**Kept by page_type:**
{md_table(['page_type', 'docs'], type_rows)}

Rationale: dropped bot-block pages, tiny redirects, non-English localized pages,
near-empty templates, exact-content duplicates, and low-value `legal`/`terms-of-use`
pages. Each kept doc carries `url`, `product`, `page_type` for cited, filterable retrieval.
"""
    add_section("Phase 1a — Ingestion & Document Selection", body)
    # also write a standalone corpus_stats.md
    rep_dir = Path(load_config().get_path("paths.reports_dir"))
    (rep_dir / "corpus_stats.md").write_text(
        "# Corpus statistics\n\n" + json.dumps(stats, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    s = build()
    print(json.dumps(s, indent=2)[:1500])
