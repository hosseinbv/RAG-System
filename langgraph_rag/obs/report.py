"""Append-only build/eval report. Each phase calls `add_section` to log what it
produced, so reports/BUILD_REPORT.md accumulates a narrative as we go."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from ..core.config import load_config

DEFAULT_REPORT = "BUILD_REPORT.md"


def _reports_dir() -> Path:
    d = Path(load_config().get_path("paths.reports_dir", "reports"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def add_section(title: str, body: str, report: str = DEFAULT_REPORT) -> Path:
    """Append a timestamped section to the report file. Returns its path."""
    path = _reports_dir() / report
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n\n## {title}\n_{ts}_\n\n"
    if not path.exists():
        path.write_text(f"# Autodesk RAG — Build & Eval Report\n")
    with open(path, "a") as f:
        f.write(header + body.rstrip() + "\n")
    return path


def md_table(headers: list[str], rows: list[list]) -> str:
    """Render a markdown table."""
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)
