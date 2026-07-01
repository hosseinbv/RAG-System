# System Graphs

Generated on 2026-07-01.

- `system_graph.svg` / `system_graph.png`: full runtime architecture with corpus index,
  optional web branch, model services, and eval dependency.
- `system_graph.dot`: Graphviz source for the full architecture plot.
- `langgraph_corpus_only.mmd`: exact compiled LangGraph topology with `web.enabled=false`.
- `langgraph_web_augmented.mmd`: exact compiled LangGraph topology with `web.enabled=true`.

Regenerate all graph artifacts from the project root:

```bash
python -m langgraph_rag.obs.render_graphs
```

The command always rewrites the DOT and Mermaid files. SVG/PNG rendering requires the system
`dot` binary from Graphviz.

![LangGraph RAG system](system_graph.svg)
