"""Abstract interfaces for every pluggable component.

Concrete implementations register themselves with the registry (see registry.py).
A node in the graph only ever talks to these interfaces, so swapping an
implementation is a config change, never a code change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .state import Chunk


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int) -> list[Chunk]:
        """Return up to top_k candidate chunks for the query."""


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[Chunk]:
        """Reorder chunks by relevance, set .score, return top_n."""


class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, query: str, contexts: list[Chunk], chat_history: list[dict]) -> dict:
        """Return {"answer": str, "citations": [...], "abstained": bool}."""


class BaseGuard(ABC):
    """A guard inspects/transforms state and reports a verdict (e.g. grounding)."""

    @abstractmethod
    def check(self, query: str, answer: str, contexts: list[Chunk]) -> dict:
        ...


class BaseJudge(ABC):
    @abstractmethod
    def score(self, sample: dict) -> dict:
        """Score one eval sample; return metric_name -> value."""
