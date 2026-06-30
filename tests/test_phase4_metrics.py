"""Phase 4: retrieval metric correctness on known cases."""
import math

from langgraph_rag.eval.metrics import (
    recall_at_k, reciprocal_rank, ndcg_at_k, retrieval_metrics, aggregate,
)


def test_recall_and_hit():
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, {"a", "d"}, k=2) == 0.5     # found a of {a,d} in top2
    assert recall_at_k(ranked, {"a", "b"}, k=2) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "a", "y"], {"a"}) == 0.5
    assert reciprocal_rank(["a"], {"a"}) == 1.0
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_ndcg_perfect_and_partial():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, k=2) == 1.0
    # relevant doc at rank 2 only -> dcg=1/log2(3), ideal=1/log2(2)=1
    val = ndcg_at_k(["x", "a"], {"a"}, k=2)
    assert abs(val - (1 / math.log2(3))) < 1e-9


def test_retrieval_metrics_bundle_and_aggregate():
    m1 = retrieval_metrics(["a", "b"], {"a"}, [1, 2])
    m2 = retrieval_metrics(["b", "a"], {"a"}, [1, 2])
    assert m1["recall@1"] == 1.0 and m2["recall@1"] == 0.0
    agg = aggregate([m1, m2])
    assert agg["recall@1"] == 0.5
