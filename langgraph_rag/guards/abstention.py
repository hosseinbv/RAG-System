"""Abstention guard (pure logic): if the best reranked context is too weak, the system
should decline rather than hallucinate. Threshold is calibrated in Phase 4.

This is a *retrieval-confidence* signal, not a content check — cheap and deterministic.
"""
from __future__ import annotations

from ..core.config import load_config
from ..core.registry import register


@register("guard", "abstention")
class AbstentionGuard:
    def __init__(self, cfg=None):
        cfg = cfg or load_config()
        self.min_score = cfg.get_path("guards.abstention.min_rerank_score", 0.30)

    def should_abstain(self, top_score: float, n_contexts: int) -> bool:
        return n_contexts == 0 or top_score < self.min_score

    # BaseGuard-style entry for uniformity
    def check(self, query, answer, contexts):
        top = max((c.score for c in contexts), default=0.0)
        abstain = self.should_abstain(top, len(contexts))
        return {"abstain": abstain, "top_score": top, "threshold": self.min_score}
