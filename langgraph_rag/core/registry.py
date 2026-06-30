"""Tiny name->class registry + factory.

Register a component:
    @register("retriever", "hybrid")
    class HybridRetriever(BaseRetriever): ...

Build it from config:
    build("retriever", "hybrid", **kwargs)

This is what makes components swappable by a string in settings.yaml and makes
adding a new component a matter of writing one class + one decorator.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

_REGISTRY: dict[str, dict[str, type]] = defaultdict(dict)


def register(kind: str, name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        _REGISTRY[kind][name] = cls
        return cls

    return deco


def get(kind: str, name: str) -> type:
    if name not in _REGISTRY[kind]:
        raise KeyError(
            f"No {kind!r} named {name!r}. Registered: {list(_REGISTRY[kind])}"
        )
    return _REGISTRY[kind][name]


def build(kind: str, name: str, *args: Any, **kwargs: Any) -> Any:
    return get(kind, name)(*args, **kwargs)


def available(kind: str) -> list[str]:
    return list(_REGISTRY[kind])
