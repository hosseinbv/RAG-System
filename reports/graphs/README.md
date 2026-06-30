# System Graphs

Generated on 2026-06-29.

- `system_graph.svg` / `system_graph.png`: full runtime architecture with corpus index,
  optional web branch, model services, and eval dependency.
- `system_graph.dot`: Graphviz source for the full architecture plot.
- `langgraph_corpus_only.mmd`: exact compiled LangGraph topology with `web.enabled=false`.
- `langgraph_web_augmented.mmd`: exact compiled LangGraph topology with `web.enabled=true`.

![LangGraph RAG system](system_graph.svg)
