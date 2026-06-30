"""Command-line interface for the RAG chatbot.

  single query:   python -m langgraph_rag.app.cli "What does Fusion 360 do?"
  interactive:    python -m langgraph_rag.app.cli            (keeps chat history)

Shows the answer, the cited sources (transparency), and a one-line trace.
"""
from __future__ import annotations

import sys

from ..graph.build_graph import build_pipeline


def _render(out: dict) -> None:
    print("\n" + out["answer"].strip() + "\n")
    cites = out.get("citations", [])
    if cites:
        print("Sources:")
        seen = set()
        for c in cites:
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            print(f"  [{c['n']}] {c['title']}  {c['url']}")
    g = out.get("grounding") or {}
    t = out.get("trace", {})
    flags = []
    if out.get("abstained"):
        flags.append("ABSTAINED")
    if g.get("groundedness") is not None:
        flags.append(f"groundedness={g['groundedness']}")
    print(f"\n[top_score={t.get('top_score', 0):.3f} "
          f"latency={sum(v for k, v in t.items() if k.endswith('_ms'))}ms "
          f"{' '.join(flags)}]")


def main() -> None:
    app = build_pipeline()
    if len(sys.argv) > 1:                    # single-shot
        q = " ".join(sys.argv[1:])
        _render(app.invoke({"query": q, "chat_history": []}))
        return
    history: list[dict] = []                  # interactive, with memory
    print("RAG chatbot. Ctrl-C to exit.")
    while True:
        try:
            q = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        out = app.invoke({"query": q, "chat_history": history})
        _render(out)
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": out["answer"]})


if __name__ == "__main__":
    main()
