"""Shared data structures: the retrieval unit (Chunk) and the LangGraph state.

Optional keys default to None/empty so nodes degrade gracefully when an upstream
optional node (rerank, web, guards) is disabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional, TypedDict


@dataclass
class Chunk:
    """One retrievable unit of corpus text plus its provenance metadata."""

    id: str
    text: str
    url: str = ""
    title: str = ""
    product: str = ""
    page_type: str = ""
    snapshot_date: str = ""
    score: float = 0.0          # filled by retriever/reranker
    source: str = "corpus"      # "corpus" or "web"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


class GraphState(TypedDict, total=False):
    """State threaded through the LangGraph. `total=False` -> all keys optional."""

    # inputs
    query: str
    chat_history: list[dict]          # [{"role": "user"/"assistant", "content": str}]

    # query understanding
    rewritten_query: str
    route: str                        # "corpus_only" | "web_augmented" | "out_of_scope"

    # retrieval
    retrieved: list[dict]             # Chunk.to_dict()
    reranked: list[dict]
    web_results: list[dict]
    contexts: list[dict]              # final contexts handed to the generator

    # generation
    answer: str
    citations: list[dict]            # [{"url", "title", "chunk_id"}]
    abstained: bool

    # guards / observability
    grounding: dict                   # {"passed": bool, "unsupported": [...]}
    trace: dict                       # timings, scores, decisions
