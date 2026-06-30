from langgraph_rag.app.session_store import (
    create_session,
    delete_session,
    list_sessions,
    load_session,
    message_record,
    save_session,
    session_title,
)
from langgraph_rag.app.ui_adapter import graph_history


def test_create_save_load_and_list_session(tmp_path):
    session = create_session(storage_dir=tmp_path)
    session["messages"] = [
        message_record("user", "What does Fusion 360 do?"),
        message_record("assistant", "Fusion 360 is CAD software.", {"citations": []}),
    ]
    saved = save_session(session, storage_dir=tmp_path)

    loaded = load_session(saved["id"], storage_dir=tmp_path)
    listed = list_sessions(storage_dir=tmp_path)

    assert loaded["id"] == saved["id"]
    assert loaded["title"] == "What does Fusion 360 do?"
    assert loaded["messages"][1]["payload"] == {"citations": []}
    assert listed[0]["id"] == saved["id"]
    assert listed[0]["n_messages"] == 2


def test_delete_session(tmp_path):
    session = create_session(storage_dir=tmp_path)

    delete_session(session["id"], storage_dir=tmp_path)

    assert list_sessions(storage_dir=tmp_path) == []


def test_session_title_uses_first_user_message_and_truncates():
    title = session_title([
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "  " + "word " * 40},
    ])

    assert title.startswith("word word")
    assert title.endswith("...")
    assert len(title) <= 80


def test_loaded_messages_feed_graph_history(tmp_path):
    session = create_session(storage_dir=tmp_path)
    session["messages"] = [
        message_record("user", "What is Maya used for?"),
        message_record("assistant", "Maya is used for animation.", {"trace": {"top_score": 0.9}}),
    ]
    saved = save_session(session, storage_dir=tmp_path)

    loaded = load_session(saved["id"], storage_dir=tmp_path)

    assert graph_history(loaded["messages"]) == [
        {"role": "user", "content": "What is Maya used for?"},
        {"role": "assistant", "content": "Maya is used for animation."},
    ]
