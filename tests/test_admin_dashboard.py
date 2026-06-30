import json

from langgraph_rag.app.admin_dashboard import (
    ab_delta_rows,
    feedback_summary,
    flatten_metric_groups,
    load_admin_dashboard_data,
    load_eval_result,
    recent_feedback,
)


def test_load_eval_result_unwraps_result(tmp_path):
    path = tmp_path / "eval.json"
    path.write_text(json.dumps({
        "result": {
            "condition": "corpus_only",
            "retrieval": {"mrr": 0.75},
            "system": {"latency_ms_mean": 100},
        }
    }))

    result = load_eval_result(path)

    assert result["condition"] == "corpus_only"
    assert result["retrieval"]["mrr"] == 0.75


def test_flatten_metric_groups_keeps_group_names():
    rows = flatten_metric_groups({
        "retrieval": {"mrr": 0.75},
        "generation": {"faithfulness": 0.9},
        "ignored": {"x": 1},
    })

    assert rows == [
        {"group": "retrieval", "metric": "mrr", "value": 0.75},
        {"group": "generation", "metric": "faithfulness", "value": 0.9},
    ]


def test_ab_delta_rows_normalizes_existing_report_shape():
    rows = ab_delta_rows({
        "rows": [
            ["mrr", 0.7, 0.8, 0.1],
            ["bad-row", 1],
        ]
    })

    assert rows == [{
        "metric": "mrr",
        "corpus_only": 0.7,
        "web_augmented": 0.8,
        "delta": 0.1,
    }]


def test_feedback_summary_and_recent_filtering():
    records = [
        {"id": "old", "label": "positive", "created_at": "2026-06-29T00:00:00Z"},
        {"id": "new", "label": "negative", "created_at": "2026-06-30T00:00:00Z"},
        {"id": "reviewed", "label": "negative", "review_status": "done", "created_at": "2026-06-28T00:00:00Z"},
    ]

    assert feedback_summary(records) == {"total": 3, "positive": 1, "negative": 2, "new": 2}
    assert [r["id"] for r in recent_feedback(records, label="negative")] == ["new", "reviewed"]


def test_load_admin_dashboard_data_collects_reports_feedback_and_samples(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "eval_report_corpus_only.json").write_text(json.dumps({
        "result": {
            "condition": "corpus_only",
            "n_items": 2,
            "retrieval": {"mrr": 0.5},
            "system": {"latency_ms_mean": 10},
        }
    }))
    (reports / "eval_report_web_augmented.json").write_text(json.dumps({
        "result": {
            "condition": "web_augmented",
            "n_items": 2,
            "web": {"trigger_rate": 0.5},
            "system": {"latency_ms_mean": 12},
        }
    }))
    (reports / "eval_report_ab.json").write_text(json.dumps({
        "rows": [["latency_mean_ms", 10, 12, 2]]
    }))
    (reports / "sample_answers_corpus_only.md").write_text("# Samples\n\nAnswer")
    feedback_path = tmp_path / "feedback.jsonl"
    feedback_path.write_text(json.dumps({
        "id": "f1",
        "label": "negative",
        "review_status": "new",
        "query": "Q",
        "created_at": "2026-06-30T00:00:00Z",
    }) + "\n")

    data = load_admin_dashboard_data(tmp_path, feedback_path=feedback_path)

    assert data["corpus_eval"]["condition"] == "corpus_only"
    assert data["web_eval"]["condition"] == "web_augmented"
    assert data["ab_rows"][0]["metric"] == "latency_mean_ms"
    assert data["feedback_summary"] == {"total": 1, "positive": 0, "negative": 1, "new": 1}
    assert data["feedback_negative"][0]["id"] == "f1"
    assert data["sample_answers"].startswith("# Samples")
    assert data["path_exists"]["corpus_eval"] is True
