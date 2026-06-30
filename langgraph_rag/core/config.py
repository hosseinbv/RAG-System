"""Config loading. Single entry point so every module reads the same settings."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DEFAULT = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"


class Config(dict):
    """Dict with dotted-path access: cfg.get_path('models.generator.model')."""

    def get_path(self, dotted: str, default: Any = None) -> Any:
        node: Any = self
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node


@lru_cache(maxsize=4)
def load_config(path: str | None = None) -> Config:
    cfg_path = Path(path or os.environ.get("RAG_CONFIG", _DEFAULT))
    with open(cfg_path) as f:
        data = yaml.safe_load(f)
    return Config(data)
