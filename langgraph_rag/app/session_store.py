"""Local persistent chat sessions for the Streamlit UI.

The first implementation intentionally uses one JSON file per session under
`data/ui/sessions/`. That keeps the format inspectable, easy to back up, and easy to test.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.config import load_config

_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_TITLE_MAX_CHARS = 80


def utc_now() -> str:
    """Return a compact UTC timestamp suitable for JSON records."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_session_dir() -> Path:
    return Path(load_config().get_path("paths.work_dir")) / "ui" / "sessions"


def _storage_dir(storage_dir: str | Path | None = None) -> Path:
    path = Path(storage_dir) if storage_dir else default_session_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_session_id(session_id: str) -> str:
    if not session_id or not _SAFE_SESSION_ID.match(session_id):
        raise ValueError(f"invalid session id: {session_id!r}")
    return session_id


def _session_path(session_id: str, storage_dir: str | Path | None = None) -> Path:
    return _storage_dir(storage_dir) / f"{_validate_session_id(session_id)}.json"


def _jsonable(value: Any) -> Any:
    """Round-trip through JSON so saved records contain only JSON-compatible values."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def message_record(role: str, content: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a UI message record with a timestamp."""
    record: dict[str, Any] = {
        "role": role,
        "content": str(content),
        "created_at": utc_now(),
    }
    if payload is not None:
        record["payload"] = _jsonable(payload)
    return record


def session_title(messages: list[dict[str, Any]]) -> str:
    """Use the first user message as a readable session title."""
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = " ".join(str(msg.get("content", "")).split())
        if content:
            if len(content) > _TITLE_MAX_CHARS:
                return content[: _TITLE_MAX_CHARS - 3].rstrip() + "..."
            return content
    return "New chat"


def new_session(title: str = "New chat") -> dict[str, Any]:
    now = utc_now()
    return {
        "id": uuid.uuid4().hex,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }


def save_session(session: dict[str, Any], storage_dir: str | Path | None = None) -> dict[str, Any]:
    """Persist a complete session and return the normalized record."""
    now = utc_now()
    session_id = _validate_session_id(str(session.get("id") or uuid.uuid4().hex))
    messages = [_jsonable(m) for m in session.get("messages", [])]
    existing_title = str(session.get("title") or "")
    title = existing_title if existing_title and (existing_title != "New chat" or not messages) \
        else session_title(messages)
    record = {
        "id": session_id,
        "title": title,
        "created_at": str(session.get("created_at") or now),
        "updated_at": now,
        "messages": messages,
    }
    path = _session_path(session_id, storage_dir)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    tmp_path.replace(path)
    return record


def create_session(title: str = "New chat", storage_dir: str | Path | None = None) -> dict[str, Any]:
    session = new_session(title)
    return save_session(session, storage_dir)


def load_session(session_id: str, storage_dir: str | Path | None = None) -> dict[str, Any]:
    path = _session_path(session_id, storage_dir)
    return json.loads(path.read_text())


def delete_session(session_id: str, storage_dir: str | Path | None = None) -> None:
    path = _session_path(session_id, storage_dir)
    if path.exists():
        path.unlink()


def list_sessions(storage_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Return lightweight session metadata sorted by most recently updated first."""
    root = _storage_dir(storage_dir)
    sessions: list[dict[str, Any]] = []
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        sessions.append({
            "id": data.get("id", path.stem),
            "title": data.get("title") or "Untitled chat",
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "n_messages": len(data.get("messages", [])),
            "path": str(path),
        })
    return sorted(sessions, key=lambda s: (s["updated_at"], s["created_at"], s["id"]), reverse=True)
