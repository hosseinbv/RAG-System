"""Build a golden evaluation set.

Two parts:
  1. SYNTHETIC: sample chunks (stratified by product) and have the judge LLM write a
     self-contained question + reference answer grounded in that chunk. The chunk's
     doc_id is the retrieval ground-truth (relevance = any chunk from that doc).
  2. CURATED: hand-authored hard / unanswerable / out-of-scope items (incl. the 5 sample
     questions) so the set isn't optimistically self-consistent and abstention is tested.

Synthetic generation is reference-based eval scaffolding; the brief's "validity" question is
answered separately by judge-vs-human agreement (see judge.py / run_eval.py).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from openai import OpenAI

from ..core.config import load_config
from ..core.llm import chat, parse_json

_GEN_SYS = (
    "You write evaluation questions for an Autodesk product help bot. Given a SOURCE passage, "
    "write ONE natural customer question that is fully answerable from the passage alone, and a "
    "concise factual ANSWER grounded only in the passage. The question must be self-contained "
    "(name the product explicitly; do NOT say 'the passage'/'the text'). "
    'Respond as JSON: {"question": "...", "answer": "..."}'
)

# Hand-authored items. gold_doc_id=None means "should abstain" (not answerable from corpus).
CURATED = [
    {"question": "What does Fusion 360 do?", "product": "fusion-360", "type": "factual"},
    {"question": "What's the difference between AutoCAD and Revit?", "product": "autocad", "type": "comparison"},
    {"question": "Does AutoCAD LT do 3D?", "product": "autocad", "type": "factual"},
    {"question": "What's the latest release for Maya?", "product": "maya", "type": "recency"},
    {"question": "Can I use Fusion 360 on a Mac?", "product": "fusion-360", "type": "factual"},
    {"question": "How much does an AutoCAD subscription cost per year?", "product": "autocad",
     "type": "unanswerable", "expect_abstain": True},
    {"question": "What is the capital of France?", "product": "", "type": "out_of_scope",
     "expect_abstain": True},
    {"question": "What is Autodesk Maya used for?", "product": "maya", "type": "factual"},
]


def _client():
    jc = load_config().get_path("models.judge")
    return OpenAI(base_url=jc["base_url"], api_key=jc.get("api_key", "EMPTY")), jc["model"]


def _stratified_sample(chunks: list[dict], per_product: int, products: list[str]) -> list[dict]:
    by_prod: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        p = c.get("product", "")
        # answerable content: product/support pages with enough text
        if p in products and c.get("page_type") in {"products", "support", "solutions"} \
                and len(c["text"]) > 500:
            by_prod[p].append(c)
    sample = []
    for p in products:
        items = by_prod.get(p, [])
        step = max(1, len(items) // per_product)
        sample.extend(items[::step][:per_product])
    return sample


def build_synthetic(per_product: int = 4) -> list[dict]:
    cfg = load_config()
    chunks = [json.loads(l) for l in
              open(Path(cfg.get_path("paths.work_dir")) / "index" / "chunks.jsonl")]
    products = ["fusion-360", "autocad", "maya", "revit", "civil-3d",
                "inventor", "navisworks", "3ds-max", "infraworks", "moldflow"]
    client, model = _client()
    out = []
    for c in _stratified_sample(chunks, per_product, products):
        try:
            text = chat(client, model, _GEN_SYS, f"SOURCE:\n{c['text'][:1800]}",
                        max_tokens=300, temperature=0.3)
            data = parse_json(text)
        except Exception:  # noqa: BLE001
            data = None
        if not data or "question" not in data or "answer" not in data:
            continue
        out.append({
            "id": f"syn::{c['id']}",
            "question": data["question"].strip(),
            "reference_answer": data["answer"].strip(),
            "gold_doc_id": c["extra"]["doc_id"],
            "gold_chunk_id": c["id"],
            "product": c["product"],
            "page_type": c["page_type"],
            "type": "synthetic",
            "source": "synthetic",
        })
    return out


def build(per_product: int = 4, out_path: str | None = None) -> dict:
    cfg = load_config()
    out_path = Path(out_path or cfg.get_path("eval.golden_set_path"))
    syn = build_synthetic(per_product)
    curated = [{**c, "id": f"curated::{i}", "source": "curated"} for i, c in enumerate(CURATED)]
    items = syn + curated
    with open(out_path, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return {"synthetic": len(syn), "curated": len(curated), "total": len(items),
            "out_path": str(out_path)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
