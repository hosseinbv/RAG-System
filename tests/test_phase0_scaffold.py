"""Phase 0: the scaffold imports, config loads, registry + interfaces work."""
from langgraph_rag.core.config import load_config
from langgraph_rag.core.state import Chunk, GraphState
from langgraph_rag.core import registry
from langgraph_rag.core.interfaces import BaseRetriever


def test_config_loads_and_dotted_access():
    cfg = load_config()
    assert cfg.get_path("models.generator.model") == "Qwen3-4B-Instruct-2507"
    assert cfg.get_path("rerank.top_n") == 5
    assert cfg.get_path("nonexistent.key", "fallback") == "fallback"


def test_chunk_roundtrip():
    c = Chunk(id="x1", text="hello", url="http://a", product="autocad")
    d = c.to_dict()
    assert Chunk.from_dict(d) == c
    # tolerant of extra keys
    d["unknown"] = 1
    assert Chunk.from_dict(d).id == "x1"


def test_registry_register_build_and_swap():
    @registry.register("retriever", "dummy")
    class _Dummy(BaseRetriever):
        def retrieve(self, query, top_k):
            return [Chunk(id="d", text=query)]

    assert "dummy" in registry.available("retriever")
    inst = registry.build("retriever", "dummy")
    assert inst.retrieve("q", 1)[0].text == "q"

    try:
        registry.build("retriever", "missing")
        assert False, "should raise"
    except KeyError:
        pass


def test_graphstate_is_partial():
    s: GraphState = {"query": "hi"}
    assert s["query"] == "hi"
