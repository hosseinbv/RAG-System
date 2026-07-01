from langgraph_rag.obs import render_graphs


def test_render_all_writes_graph_sources_when_graphviz_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(render_graphs.shutil, "which", lambda _: None)

    result = render_graphs.render_all(tmp_path)

    assert (tmp_path / "system_graph.dot").exists()
    assert (tmp_path / "langgraph_corpus_only.mmd").exists()
    assert (tmp_path / "langgraph_web_augmented.mmd").exists()
    assert result["rendered"] == {
        "system_graph.svg": False,
        "system_graph.png": False,
    }


def test_compiled_mermaid_reflects_web_toggle():
    corpus_only = render_graphs.compiled_mermaid(False)
    web_augmented = render_graphs.compiled_mermaid(True)

    assert "decide_web" not in corpus_only
    assert "decide_web" in web_augmented
    assert "web_retrieve" in web_augmented
