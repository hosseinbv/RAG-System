"""Data loaders for the Streamlit eval/admin dashboard."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .feedback_store import default_feedback_path, load_feedback


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def dashboard_paths(root: str | Path | None = None) -> dict[str, Path]:
    base = Path(root) if root else project_root()
    reports = base / "reports"
    return {
        "corpus_eval": reports / "eval_report_corpus_only.json",
        "web_eval": reports / "eval_report_web_augmented.json",
        "ab_report_json": reports / "eval_report_ab.json",
        "ab_report_md": reports / "eval_report_ab.md",
        "sample_answers": reports / "sample_answers_corpus_only.md",
        "feedback": (base / "data" / "ui" / "feedback.jsonl") if root else default_feedback_path(),
    }


def load_json_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_eval_result(path: str | Path) -> dict[str, Any]:
    data = load_json_file(path)
    result = data.get("result", data)
    return result if isinstance(result, dict) else {}


def flatten_metric_groups(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in ("retrieval", "generation", "citation", "abstention", "web", "system"):
        values = result.get(group) or {}
        for metric, value in values.items():
            rows.append({"group": group, "metric": metric, "value": value})
    return rows


def ab_delta_rows(ab_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ab_report.get("rows", []):
        if len(row) != 4:
            continue
        metric, corpus_only, web_augmented, delta = row
        rows.append({
            "metric": metric,
            "corpus_only": corpus_only,
            "web_augmented": web_augmented,
            "delta": delta,
        })
    return rows


def feedback_summary(records: list[dict[str, Any]]) -> dict[str, int]:
    positive = sum(1 for r in records if r.get("label") == "positive")
    negative = sum(1 for r in records if r.get("label") == "negative")
    return {
        "total": len(records),
        "positive": positive,
        "negative": negative,
        "new": sum(1 for r in records if r.get("review_status", "new") == "new"),
    }


def recent_feedback(
    records: list[dict[str, Any]],
    *,
    label: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    filtered = [r for r in records if label in (None, "all") or r.get("label") == label]
    return sorted(filtered, key=lambda r: str(r.get("created_at", "")), reverse=True)[:limit]


def load_text(path: str | Path, max_chars: int = 20000) -> str:
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars]


def load_admin_dashboard_data(
    root: str | Path | None = None,
    *,
    feedback_path: str | Path | None = None,
) -> dict[str, Any]:
    paths = dashboard_paths(root)
    if feedback_path is not None:
        paths["feedback"] = Path(feedback_path)

    corpus_eval = load_eval_result(paths["corpus_eval"])
    web_eval = load_eval_result(paths["web_eval"])
    ab_report = load_json_file(paths["ab_report_json"])
    feedback_records = load_feedback(paths["feedback"])

    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "path_exists": {name: path.exists() for name, path in paths.items()},
        "corpus_eval": corpus_eval,
        "web_eval": web_eval,
        "corpus_metric_rows": flatten_metric_groups(corpus_eval),
        "web_metric_rows": flatten_metric_groups(web_eval),
        "ab_rows": ab_delta_rows(ab_report),
        "sample_answers": load_text(paths["sample_answers"]),
        "feedback_summary": feedback_summary(feedback_records),
        "feedback_recent": recent_feedback(feedback_records, limit=20),
        "feedback_negative": recent_feedback(feedback_records, label="negative", limit=20),
    }
