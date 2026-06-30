"""Retrieval metrics (pure functions). Generation metrics are LLM-judge based and live
in judge.py. Keeping these pure makes them unit-testable and deterministic.

`relevant` is the set of gold-relevant ids for a query; `ranked` is the list of
retrieved ids in rank order.
"""
from __future__ import annotations

import math


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for r in ranked[:k] if r in relevant)
    return hits / len(relevant)


def hit_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(r in relevant for r in ranked[:k]) else 0.0


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for i, r in enumerate(ranked, 1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, r in enumerate(ranked[:k], 1) if r in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def aggregate(per_query: list[dict]) -> dict:
    """Mean each metric across queries."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {k: round(sum(q[k] for q in per_query) / len(per_query), 4) for k in keys}


def retrieval_metrics(ranked: list[str], relevant: set[str], k_values: list[int]) -> dict:
    out: dict[str, float] = {"mrr": reciprocal_rank(ranked, relevant)}
    for k in k_values:
        out[f"recall@{k}"] = recall_at_k(ranked, relevant, k)
        out[f"hit@{k}"] = hit_at_k(ranked, relevant, k)
        out[f"ndcg@{k}"] = ndcg_at_k(ranked, relevant, k)
    return out
