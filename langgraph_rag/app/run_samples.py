"""Run a set of demo questions and write a markdown deliverable with answers + sources.

  python -m langgraph_rag.app.run_samples [out.md]
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..core.config import load_config
from ..graph.build_graph import build_pipeline

SAMPLE_QUESTIONS = [
    "What does Fusion 360 do?",
    "What's the difference between AutoCAD and Revit?",
    "Does AutoCAD LT do 3D?",
    "What's the latest release for Maya?",
    "Can I use Fusion 360 on a Mac?",
    # extra questions that showcase behavior:
    "How much does AutoCAD cost?",                       # likely thin/absent -> abstain
    "What is the capital of France?",                    # out-of-scope
    "What is Autodesk Maya used for?",                   # clear in-corpus
]


def render_markdown(app, questions: list[str]) -> str:
    out_lines = ["# Sample answers — corpus-only\n"]
    for q in questions:
        res = app.invoke({"query": q, "chat_history": []})
        t = res.get("trace", {})
        out_lines.append(f"## Q: {q}\n")
        out_lines.append(res["answer"].strip() + "\n")
        cites, seen = [], set()
        for c in res.get("citations", []):
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            cites.append(f"- [{c['n']}] {c['title']} — {c['url']}")
        if cites:
            out_lines.append("**Sources:**\n" + "\n".join(cites) + "\n")
        out_lines.append(
            f"<sub>top_rerank={t.get('top_score', 0):.3f} · "
            f"abstained={res.get('abstained')} · "
            f"latency={sum(v for k, v in t.items() if k.endswith('_ms'))}ms</sub>\n"
        )
    return "\n".join(out_lines)


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(load_config().get_path("paths.reports_dir")) / "sample_answers_corpus_only.md"
    app = build_pipeline()
    out_path.write_text(render_markdown(app, SAMPLE_QUESTIONS))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
