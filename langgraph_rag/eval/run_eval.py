"""Phase 4: run the full evaluation over the golden set and write a report.

Computes, per the brief:
  Retrieval (synthetic items, doc-level relevance = chunks sharing the gold doc):
     hit@k, MRR, nDCG@k
  Generation (answered items, LLM judge): faithfulness, answer_relevance
  Citation: has-citation rate, gold-doc-cited rate
  Abstention (curated items): abstain recall on unanswerable, false-abstain on answerable
  System: latency mean / p90

Usage:
  python -m langgraph_rag.eval.run_eval --condition corpus_only
  python -m langgraph_rag.eval.run_eval --condition web_augmented
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

from ..core.config import load_config
from ..graph.build_graph import build_pipeline
from ..obs.report import add_section, md_table
from . import metrics as M
from .judge import GenerationJudge, validate_judge


def _load_golden() -> list[dict]:
    path = load_config().get_path("eval.golden_set_path")
    return [json.loads(l) for l in open(path)]


def _doc_of(chunk: dict) -> str:
    return chunk.get("extra", {}).get("doc_id", "")


def _config_for_condition(condition: str):
    cfg = load_config()
    if condition == "corpus_only":
        cfg.setdefault("web", {})["enabled"] = False
    elif condition == "web_augmented":
        cfg.setdefault("web", {})["enabled"] = True
    else:
        raise ValueError("condition must be 'corpus_only' or 'web_augmented'")
    return cfg


def evaluate(condition: str = "corpus_only", limit: int | None = None) -> dict:
    cfg = _config_for_condition(condition)
    k_values = cfg.get_path("eval.k_values", [1, 3, 5, 10])
    app = build_pipeline(cfg)
    judge = GenerationJudge(cfg)
    golden = _load_golden()
    if limit:
        golden = golden[:limit]

    retrieval_rows, gen_rows, latencies = [], [], []
    abstain_eval = {"should_abstain_total": 0, "should_abstain_hit": 0,
                    "answerable_total": 0, "false_abstain": 0}
    citation = {"answered": 0, "has_citation": 0, "gold_doc_cited": 0, "synthetic_answered": 0}
    web_eval = {"triggered": 0, "with_results": 0, "web_context_final": 0}
    per_item = []

    for item in golden:
        out = app.invoke({"query": item["question"], "chat_history": []})
        trace = out.get("trace", {})
        latencies.append(sum(v for k, v in trace.items() if k.endswith("_ms")))
        answer, abstained = out.get("answer", ""), out.get("abstained", False)
        contexts = out.get("contexts") or out.get("reranked") or []
        web_triggered = bool(trace.get("web_triggered"))
        web_eval["triggered"] += int(web_triggered)
        web_eval["with_results"] += int((trace.get("n_web_results") or 0) > 0)
        web_eval["web_context_final"] += int(
            (trace.get("final_context_sources") or {}).get("web", 0) > 0
        )

        # --- retrieval (synthetic items only: they have a gold doc) ---
        if item.get("gold_doc_id"):
            ranked = out.get("retrieved", [])
            ranked_ids = [c["id"] for c in ranked]
            relevant = {c["id"] for c in ranked if _doc_of(c) == item["gold_doc_id"]}
            # relevance is doc-level: any retrieved chunk from the gold doc counts
            rm = M.retrieval_metrics(ranked_ids, relevant, k_values)
            retrieval_rows.append(rm)

        # --- abstention ---
        if item.get("expect_abstain"):
            abstain_eval["should_abstain_total"] += 1
            abstain_eval["should_abstain_hit"] += int(abstained)
        elif item["source"] == "curated" and not item.get("expect_abstain"):
            abstain_eval["answerable_total"] += 1
            abstain_eval["false_abstain"] += int(abstained)

        # --- generation (judge) for answered items ---
        gen = {"faithfulness": None, "answer_relevance": None}
        if not abstained:
            citation["answered"] += 1
            cites = out.get("citations", [])
            citation["has_citation"] += int(len(cites) > 0)
            if item.get("gold_doc_id"):
                citation["synthetic_answered"] += 1
                cited_docs = {c["chunk_id"].split("::")[0] for c in cites}
                citation["gold_doc_cited"] += int(item["gold_doc_id"] in cited_docs)
            gen = judge.score({"question": item["question"], "answer": answer,
                               "contexts": [c["text"] for c in contexts]})
            gen_rows.append(gen)

        per_item.append({
            "id": item["id"],
            "question": item["question"],
            "type": item.get("type", item["source"]),
            "source": item["source"],
            "gold_doc_id": item.get("gold_doc_id"),
            "abstained": abstained,
            "answer": answer,
            "citations": out.get("citations", []),
            "trace": trace,
            "context_ids": [c["id"] for c in contexts],
            "context_sources": [c.get("source", "corpus") for c in contexts],
            **gen,
        })

    result = {
        "condition": condition,
        "n_items": len(golden),
        "retrieval": M.aggregate(retrieval_rows) if retrieval_rows else {},
        "generation": M.aggregate([{k: v for k, v in g.items()} for g in gen_rows]) if gen_rows else {},
        "citation": {
            "has_citation_rate": _safe(citation["has_citation"], citation["answered"]),
            "gold_doc_cited_rate": _safe(citation["gold_doc_cited"], citation["synthetic_answered"]),
        },
        "abstention": {
            "abstain_recall_on_unanswerable": _safe(abstain_eval["should_abstain_hit"],
                                                     abstain_eval["should_abstain_total"]),
            "false_abstain_rate_on_answerable": _safe(abstain_eval["false_abstain"],
                                                      abstain_eval["answerable_total"]),
        },
        "web": {
            "trigger_rate": _safe(web_eval["triggered"], len(golden)),
            "web_result_rate": _safe(web_eval["with_results"], len(golden)),
            "final_web_context_rate": _safe(web_eval["web_context_final"], len(golden)),
        },
        "system": {
            "latency_ms_mean": round(st.mean(latencies)) if latencies else 0,
            "latency_ms_p90": round(sorted(latencies)[int(len(latencies) * 0.9)]) if latencies else 0,
        },
    }
    return result, per_item


def _safe(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def write_report(result: dict, judge_validation: dict, condition: str) -> None:
    r = result
    ret = r["retrieval"]
    gen = r["generation"]
    ret_tbl = md_table(["metric", "value"], [[k, v] for k, v in ret.items()])
    body = f"""**Condition: `{condition}`** · golden items: {r['n_items']}

### Judge validity (judge vs human labels)
accuracy = **{judge_validation['accuracy']}**, Cohen's kappa = **{judge_validation['cohen_kappa']}**
on {judge_validation['n']} hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
{ret_tbl}

### Generation (LLM judge, answered items)
- faithfulness = **{gen.get('faithfulness')}**
- answer_relevance = **{gen.get('answer_relevance')}**

### Citation
- has-citation rate (answered) = {r['citation']['has_citation_rate']}
- gold-doc-cited rate (synthetic answered) = {r['citation']['gold_doc_cited_rate']}

### Abstention
- abstain recall on unanswerable/out-of-scope = {r['abstention']['abstain_recall_on_unanswerable']}
- false-abstain rate on answerable = {r['abstention']['false_abstain_rate_on_answerable']}

### Web
- web trigger rate = {r.get('web', {}).get('trigger_rate')}
- web result rate = {r.get('web', {}).get('web_result_rate')}
- final context contains web rate = {r.get('web', {}).get('final_web_context_rate')}

### System
- latency mean = {r['system']['latency_ms_mean']} ms · p90 = {r['system']['latency_ms_p90']} ms
"""
    phase = "Phase 5" if condition == "web_augmented" else "Phase 4"
    add_section(f"{phase} — Evaluation ({condition})", body)
    rep_dir = Path(load_config().get_path("paths.reports_dir"))
    (rep_dir / f"eval_report_{condition}.json").write_text(
        json.dumps({"result": result, "judge_validation": judge_validation}, indent=2))


def write_per_item_report(per_item: list[dict], condition: str) -> Path:
    rep_dir = Path(load_config().get_path("paths.reports_dir"))
    path = rep_dir / f"eval_items_{condition}.jsonl"
    with open(path, "w") as f:
        for row in per_item:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _flat_metrics(result: dict) -> dict:
    return {
        "mrr": result["retrieval"].get("mrr"),
        "hit@10": result["retrieval"].get("hit@10"),
        "faithfulness": result["generation"].get("faithfulness"),
        "answer_relevance": result["generation"].get("answer_relevance"),
        "has_citation_rate": result["citation"].get("has_citation_rate"),
        "gold_doc_cited_rate": result["citation"].get("gold_doc_cited_rate"),
        "abstain_recall": result["abstention"].get("abstain_recall_on_unanswerable"),
        "false_abstain": result["abstention"].get("false_abstain_rate_on_answerable"),
        "latency_mean_ms": result["system"].get("latency_ms_mean"),
        "latency_p90_ms": result["system"].get("latency_ms_p90"),
        "web_trigger_rate": result.get("web", {}).get("trigger_rate"),
        "final_web_context_rate": result.get("web", {}).get("final_web_context_rate"),
    }


def write_ab_report() -> None:
    rep_dir = Path(load_config().get_path("paths.reports_dir"))
    corpus_path = rep_dir / "eval_report_corpus_only.json"
    web_path = rep_dir / "eval_report_web_augmented.json"
    if not corpus_path.exists() or not web_path.exists():
        return
    corpus = json.loads(corpus_path.read_text())["result"]
    web = json.loads(web_path.read_text())["result"]
    cflat, wflat = _flat_metrics(corpus), _flat_metrics(web)
    rows = []
    for metric in cflat:
        cval, wval = cflat[metric], wflat.get(metric)
        delta = None if cval is None or wval is None else round(wval - cval, 4)
        rows.append([metric, cval, wval, delta])
    body = f"""# Corpus-only vs web-augmented A/B report

| metric | corpus_only | web_augmented | delta |
| --- | --- | --- | --- |
{chr(10).join(f"| {m} | {c} | {w} | {d} |" for m, c, w, d in rows)}

Notes:
- Positive quality deltas are good for retrieval, generation, citation, and abstention recall.
- Lower latency deltas are good.
- Web trigger/context rates are expected to be null or zero for corpus-only and nonzero for web.
- Inspect `eval_items_web_augmented.jsonl` for recency examples such as latest release questions.
"""
    (rep_dir / "eval_report_ab.md").write_text(body)
    (rep_dir / "eval_report_ab.json").write_text(
        json.dumps({"corpus_only": corpus, "web_augmented": web, "rows": rows}, indent=2)
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", default="corpus_only")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    jv = validate_judge()
    result, per_item = evaluate(args.condition, args.limit)
    write_report(result, jv, args.condition)
    write_per_item_report(per_item, args.condition)
    if args.condition == "web_augmented":
        write_ab_report()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
