from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


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
