"""Streamlit chat UI for the LangGraph RAG pipeline.

Run:
  streamlit run langgraph_rag/app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Streamlit executes this file as a script, so depending on launch method the project root
# may not be importable. Add it explicitly before importing the package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph_rag.app.admin_dashboard import load_admin_dashboard_data
from langgraph_rag.app.feedback_store import submit_feedback
from langgraph_rag.app.session_store import (
    create_session,
    delete_session,
    list_sessions,
    load_session,
    message_record,
    save_session,
    session_title,
)
from langgraph_rag.app.ui_adapter import build_display_payload, graph_history, service_error_message
from langgraph_rag.graph.build_graph import build_pipeline


SAMPLE_QUESTIONS = [
    "What does Fusion 360 do?",
    "Does AutoCAD LT do 3D?",
    "Can I use Fusion 360 on a Mac?",
    "What is Autodesk Maya used for?",
    "What is the capital of France?",
]


@st.cache_resource(show_spinner=False)
def _app():
    return build_pipeline()


def _init_state() -> None:
    if "session_id" not in st.session_state:
        session = create_session()
        _set_session_state(session)
        return
    st.session_state.setdefault("selected_question", "")
    st.session_state.setdefault("feedback_status", {})


def _set_session_state(session: dict) -> None:
    st.session_state.session_id = session["id"]
    st.session_state.session_title = session.get("title", "New chat")
    st.session_state.session_created_at = session.get("created_at", "")
    st.session_state.session_updated_at = session.get("updated_at", "")
    st.session_state.messages = session.get("messages", [])
    st.session_state.feedback_status = {}


def _current_session_record() -> dict:
    messages = st.session_state.get("messages", [])
    return {
        "id": st.session_state.session_id,
        "title": session_title(messages),
        "created_at": st.session_state.get("session_created_at", ""),
        "messages": messages,
    }


def _save_current_session() -> None:
    session = save_session(_current_session_record())
    st.session_state.session_title = session["title"]
    st.session_state.session_updated_at = session["updated_at"]


def _new_session() -> None:
    session = create_session()
    _set_session_state(session)


def _load_session(session_id: str) -> None:
    _save_current_session()
    _set_session_state(load_session(session_id))


def _delete_current_session() -> None:
    delete_session(st.session_state.session_id)
    _set_session_state(create_session())


def _render_sources(payload: dict) -> None:
    citations = payload["citations"]
    if not citations:
        st.caption("No citations returned.")
        return
    for citation in citations:
        label = f"[{citation['n']}] {citation['title']}"
        if citation["url"]:
            st.markdown(f"- {label}: {citation['url']}")
        else:
            st.markdown(f"- {label}")


def _render_contexts(payload: dict) -> None:
    contexts = payload["contexts"]
    if not contexts:
        st.caption("No contexts available.")
        return
    for row in contexts:
        title = f"{row['rank']}. {row['title']}"
        meta = (
            f"score={row['score']} | source={row['source']} | "
            f"product={row['product'] or '-'} | page_type={row['page_type'] or '-'}"
        )
        with st.expander(title):
            if row["url"]:
                st.markdown(row["url"])
            st.caption(f"{meta} | chunk={row['chunk_id']}")
            st.write(row["text"])


def _render_trace(payload: dict) -> None:
    metrics = payload["metrics"]
    cols = st.columns(4)
    cols[0].metric("Top score", metrics["top_score"])
    cols[1].metric("Total latency", f"{metrics['total_latency_ms']} ms")
    cols[2].metric("Web", "on" if metrics["web_triggered"] else "off")
    cols[3].metric("Web results", metrics["n_web_results"])
    latency_cols = st.columns(4)
    latency_cols[0].metric("Retrieve", f"{metrics['retrieve_ms']} ms")
    latency_cols[1].metric("Rerank", f"{metrics['rerank_ms']} ms")
    latency_cols[2].metric("Generate", f"{metrics['generate_ms']} ms")
    latency_cols[3].metric("Web latency", f"{metrics['web_ms']} ms")
    if metrics["groundedness"] is not None:
        st.caption(f"Groundedness: {metrics['groundedness']}")
    with st.expander("Raw trace"):
        st.json(payload["trace"])


def _feedback_widget_key(message_index: int, suffix: str) -> str:
    return f"feedback_{suffix}_{st.session_state.session_id}_{message_index}"


def _submit_feedback(message_index: int, label: str) -> None:
    comment_key = _feedback_widget_key(message_index, "comment")
    record = submit_feedback(
        session_id=st.session_state.session_id,
        messages=st.session_state.messages,
        assistant_index=message_index,
        label=label,
        comment=st.session_state.get(comment_key, ""),
    )
    status = st.session_state.setdefault("feedback_status", {})
    status[str(message_index)] = {"label": record["label"], "id": record["id"]}


def _render_feedback_controls(message_index: int) -> None:
    status = st.session_state.get("feedback_status", {}).get(str(message_index))
    with st.expander("Feedback"):
        st.text_area(
            "Optional comment",
            key=_feedback_widget_key(message_index, "comment"),
            height=80,
            placeholder="What worked, or what should be fixed?",
        )
        cols = st.columns([1, 1, 3])
        if cols[0].button("Good answer", key=_feedback_widget_key(message_index, "positive")):
            _submit_feedback(message_index, "positive")
            st.success("Feedback saved.")
        if cols[1].button("Needs work", key=_feedback_widget_key(message_index, "negative")):
            _submit_feedback(message_index, "negative")
            st.success("Feedback saved.")
        if status:
            st.caption(f"Last saved feedback: {status['label']} ({status['id'][:8]})")


def _render_assistant(payload: dict, message_index: int) -> None:
    st.markdown(payload["answer"] or "_No answer returned._")
    if payload["abstained"]:
        st.warning("The system abstained for this answer.")
    with st.expander("Sources", expanded=bool(payload["citations"])):
        _render_sources(payload)
    with st.expander("Retrieved context"):
        _render_contexts(payload)
    with st.expander("Trace"):
        _render_trace(payload)
    _render_feedback_controls(message_index)


def _metric_value(result: dict, group: str, metric: str, default="-"):
    return (result.get(group) or {}).get(metric, default)


def _render_eval_summary(title: str, result: dict, rows: list[dict]) -> None:
    st.subheader(title)
    cols = st.columns(5)
    cols[0].metric("Items", result.get("n_items", 0))
    cols[1].metric("MRR", _metric_value(result, "retrieval", "mrr"))
    cols[2].metric("Faithfulness", _metric_value(result, "generation", "faithfulness"))
    cols[3].metric("Gold cited", _metric_value(result, "citation", "gold_doc_cited_rate"))
    cols[4].metric("Mean latency", f"{_metric_value(result, 'system', 'latency_ms_mean', 0)} ms")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_feedback_review(data: dict) -> None:
    summary = data["feedback_summary"]
    st.subheader("Feedback")
    cols = st.columns(4)
    cols[0].metric("Total", summary["total"])
    cols[1].metric("Positive", summary["positive"])
    cols[2].metric("Negative", summary["negative"])
    cols[3].metric("New", summary["new"])

    selected = st.selectbox("Feedback records", ["negative", "all", "positive"], index=0)
    records = data["feedback_negative"] if selected == "negative" else [
        r for r in data["feedback_recent"]
        if selected == "all" or r.get("label") == selected
    ]
    if not records:
        st.caption("No feedback records.")
        return

    for record in records:
        query = str(record.get("query") or "Untitled query")
        label = record.get("label", "-")
        created_at = record.get("created_at", "")
        with st.expander(f"{label} | {query[:100]}"):
            st.caption(f"{created_at} | session={record.get('session_id', '-')}")
            if record.get("comment"):
                st.write(record["comment"])
            st.markdown("**Answer**")
            st.write(record.get("answer", ""))
            st.markdown("**Evidence**")
            st.json({
                "context_ids": record.get("context_ids", []),
                "source_urls": record.get("source_urls", []),
                "top_score": record.get("top_score"),
                "total_latency_ms": record.get("total_latency_ms"),
                "abstained": record.get("abstained"),
            })


def _render_admin_dashboard() -> None:
    data = load_admin_dashboard_data()

    st.header("Eval/Admin Dashboard")
    st.caption("Current evaluation artifacts, A/B deltas, feedback, and sample answers.")

    eval_tabs = st.tabs(["Corpus-only", "Web-augmented", "A/B", "Feedback", "Samples", "Files"])
    with eval_tabs[0]:
        _render_eval_summary("Corpus-only eval", data["corpus_eval"], data["corpus_metric_rows"])
    with eval_tabs[1]:
        _render_eval_summary("Web-augmented eval", data["web_eval"], data["web_metric_rows"])
    with eval_tabs[2]:
        st.subheader("A/B deltas")
        st.dataframe(data["ab_rows"], use_container_width=True, hide_index=True)
        st.markdown(
            "- Web provider currently produced no final web evidence in the latest A/B run.\n"
            "- Recency questions can be stale when `web.enabled=false`.\n"
            "- Judge validation is a small smoke test, not a production human annotation set."
        )
    with eval_tabs[3]:
        _render_feedback_review(data)
    with eval_tabs[4]:
        st.subheader("Sample answers")
        st.markdown(data["sample_answers"] or "_No sample answer report found._")
    with eval_tabs[5]:
        st.subheader("Source files")
        rows = [
            {"artifact": name, "exists": data["path_exists"][name], "path": path}
            for name, path in data["paths"].items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _submit(question: str) -> None:
    question = question.strip()
    if not question:
        return

    history = graph_history(st.session_state.messages)
    st.session_state.messages.append(message_record("user", question))
    _save_current_session()
    try:
        with st.spinner("Searching the corpus and drafting an answer..."):
            output = _app().invoke({"query": question, "chat_history": history})
        payload = build_display_payload(question, output)
    except Exception as exc:  # noqa: BLE001 - show UI-friendly model-service errors
        payload = {
            "question": question,
            "answer": service_error_message(exc),
            "abstained": True,
            "citations": [],
            "contexts": [],
            "trace": {},
            "grounding": {},
            "metrics": {
                "top_score": 0.0,
                "retrieve_ms": 0,
                "rerank_ms": 0,
                "generate_ms": 0,
                "web_ms": 0,
                "total_latency_ms": 0,
                "web_triggered": False,
                "n_web_results": 0,
                "groundedness": None,
            },
        }
    st.session_state.messages.append(message_record("assistant", payload["answer"], payload))
    _save_current_session()


def main() -> None:
    st.set_page_config(page_title="LangGraph RAG Chat", page_icon=":material/forum:", layout="wide")
    _init_state()

    st.title("LangGraph RAG Chat")
    st.caption("Corpus-only RAG with citations, context inspection, and trace visibility.")

    with st.sidebar:
        view = st.radio("View", ["Chat", "Admin"], horizontal=True)
        st.divider()
        st.header("Session")
        st.caption(st.session_state.get("session_title", "New chat"))
        st.caption(f"ID: `{st.session_state.session_id[:8]}`")

        if st.button("New chat", use_container_width=True):
            _save_current_session()
            _new_session()
            st.rerun()

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            _save_current_session()
            st.rerun()

        if st.button("Delete current chat", use_container_width=True):
            _delete_current_session()
            st.rerun()

        sessions = list_sessions()
        if sessions:
            options = [s["id"] for s in sessions]
            labels = {
                s["id"]: f"{s['title']} ({s['n_messages']} msgs)"
                for s in sessions
            }
            current = st.session_state.session_id
            index = options.index(current) if current in options else 0
            selected = st.selectbox(
                "Load saved chat",
                options,
                index=index,
                format_func=lambda sid: labels.get(sid, sid),
            )
            if selected != current and st.button("Load selected chat", use_container_width=True):
                _load_session(selected)
                st.rerun()

        st.divider()
        st.header("Sample questions")
        for question in SAMPLE_QUESTIONS:
            if st.button(question, use_container_width=True):
                _submit(question)
                st.rerun()
        st.divider()
        st.caption("Default mode uses the local corpus. Web augmentation remains disabled.")

    if view == "Admin":
        _render_admin_dashboard()
        return

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("payload"):
                _render_assistant(msg["payload"], i)
            else:
                st.markdown(msg["content"])

    question = st.chat_input("Ask about Autodesk products, support, or documentation")
    if question:
        _submit(question)
        st.rerun()


if __name__ == "__main__":
    main()
