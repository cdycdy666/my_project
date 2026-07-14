from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


_STATE_LOCK = threading.RLock()


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_chat(path: Path, chat_id: str) -> None:
    with _STATE_LOCK:
        state = load_state(path)
        state["last_chat_id"] = chat_id
        save_state(path, state)


def get_last_chat_id(path: Path) -> str | None:
    value = load_state(path).get("last_chat_id")
    return value if isinstance(value, str) and value else None


def remember_reminder_sent(path: Path, date_text: str) -> None:
    with _STATE_LOCK:
        state = load_state(path)
        state["last_reminder_date"] = date_text
        save_state(path, state)


def get_last_reminder_date(path: Path) -> str | None:
    value = load_state(path).get("last_reminder_date")
    return value if isinstance(value, str) and value else None


def remember_summary_done(path: Path, date_text: str) -> None:
    with _STATE_LOCK:
        state = load_state(path)
        state["last_summary_date"] = date_text
        save_state(path, state)


def get_last_summary_date(path: Path) -> str | None:
    value = load_state(path).get("last_summary_date")
    return value if isinstance(value, str) and value else None


def _now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_active_capture_session(path: Path, max_age_minutes: int = 60) -> dict[str, Any] | None:
    with _STATE_LOCK:
        state = load_state(path)
        session = state.get("active_capture_session")
        if not isinstance(session, dict):
            return None

        updated_at = _parse_iso(session.get("updated_at"))
        if updated_at and datetime.now(updated_at.tzinfo or ZoneInfo("Asia/Shanghai")) - updated_at > timedelta(
            minutes=max_age_minutes
        ):
            state.pop("active_capture_session", None)
            save_state(path, state)
            return None

        return session


def remember_active_capture_session(path: Path, session: dict[str, Any]) -> None:
    with _STATE_LOCK:
        state = load_state(path)
        now = _now_iso()
        current = state.get("active_capture_session")
        started_at = current.get("started_at") if isinstance(current, dict) else ""
        state["active_capture_session"] = {
            "id": str(session.get("id") or ""),
            "title": str(session.get("title") or "未命名记录"),
            "started_at": str(session.get("started_at") or started_at or now),
            "updated_at": now,
            "last_question": str(session.get("last_question") or ""),
            "status": "open",
        }
        save_state(path, state)


def clear_active_capture_session(path: Path) -> None:
    with _STATE_LOCK:
        state = load_state(path)
        if "active_capture_session" in state:
            state.pop("active_capture_session", None)
            save_state(path, state)


def remember_processed_message(path: Path, message_id: str, max_items: int = 500) -> bool:
    if not message_id:
        return True

    with _STATE_LOCK:
        state = load_state(path)
        raw_ids = state.get("processed_message_ids")
        message_ids = [item for item in raw_ids if isinstance(item, str)] if isinstance(raw_ids, list) else []
        if message_id in message_ids:
            return False

        message_ids.append(message_id)
        state["processed_message_ids"] = message_ids[-max_items:]
        save_state(path, state)
        return True
