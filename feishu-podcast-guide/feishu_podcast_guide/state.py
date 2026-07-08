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


def get_last_chat_id(path: Path) -> str:
    with _STATE_LOCK:
        value = load_state(path).get("last_chat_id")
        return value if isinstance(value, str) else ""


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


def conversation_history(path: Path, chat_id: str, max_turns: int = 12) -> list[dict[str, str]]:
    if not chat_id:
        return []
    with _STATE_LOCK:
        state = load_state(path)
        raw_by_chat = state.get("conversation_history")
        by_chat = raw_by_chat if isinstance(raw_by_chat, dict) else {}
        raw_items = by_chat.get(chat_id)
        items = raw_items if isinstance(raw_items, list) else []
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            content = str(item.get("content") or "")
            if role in {"user", "assistant"} and content:
                cleaned.append({"role": role, "content": content})
        return cleaned[-max_turns:]


def append_conversation_turn(
    path: Path,
    chat_id: str,
    role: str,
    content: str,
    max_turns: int = 12,
) -> None:
    if not chat_id or role not in {"user", "assistant"} or not content.strip():
        return
    with _STATE_LOCK:
        state = load_state(path)
        raw_by_chat = state.get("conversation_history")
        by_chat = raw_by_chat if isinstance(raw_by_chat, dict) else {}
        raw_items = by_chat.get(chat_id)
        items = raw_items if isinstance(raw_items, list) else []
        items.append({"role": role, "content": content.strip()[:4000]})
        by_chat[chat_id] = items[-max_turns:]
        state["conversation_history"] = by_chat
        save_state(path, state)


def remember_learning_record(
    path: Path,
    chat_id: str,
    user_message: str,
    assistant_reply: str,
    episode_ids: list[str],
    max_items: int = 100,
) -> None:
    if not chat_id or not user_message.strip():
        return
    with _STATE_LOCK:
        state = load_state(path)
        raw_records = state.get("learning_records")
        records = raw_records if isinstance(raw_records, list) else []
        records.append(
            {
                "chat_id": chat_id,
                "user_message": user_message.strip()[:2000],
                "assistant_reply": assistant_reply.strip()[:2000],
                "episode_ids": episode_ids[:10],
            }
        )
        state["learning_records"] = records[-max_items:]
        save_state(path, state)


_DAILY_RECO_DEFAULTS: dict[str, Any] = {
    "chat_id": "",
    "current_theme": "",
    "pushed_count": 0,
    "pushed_episode_ids": [],
    "theme_started_at": "",
    "last_push_date": "",
    "pending_theme_switch": False,
    "candidate_themes": [],
    "prompts_since_last_reply": 0,
}


def load_daily_reco(path: Path) -> dict[str, Any]:
    with _STATE_LOCK:
        raw = load_state(path).get("daily_reco")
    daily = dict(_DAILY_RECO_DEFAULTS)
    if isinstance(raw, dict):
        for key in _DAILY_RECO_DEFAULTS:
            if key in raw:
                daily[key] = raw[key]
    return daily


def save_daily_reco(path: Path, daily: dict[str, Any]) -> None:
    cleaned = {key: daily.get(key, default) for key, default in _DAILY_RECO_DEFAULTS.items()}
    with _STATE_LOCK:
        state = load_state(path)
        state["daily_reco"] = cleaned
        save_state(path, state)


def set_daily_theme(path: Path, theme: str, today: str) -> None:
    with _STATE_LOCK:
        daily = load_daily_reco(path)
        daily["current_theme"] = theme
        daily["pushed_count"] = 0
        daily["theme_started_at"] = today
        daily["pending_theme_switch"] = False
        daily["candidate_themes"] = []
        daily["prompts_since_last_reply"] = 0
        save_daily_reco(path, daily)


def keep_daily_theme(path: Path) -> None:
    with _STATE_LOCK:
        daily = load_daily_reco(path)
        daily["pushed_count"] = 0
        daily["pending_theme_switch"] = False
        daily["candidate_themes"] = []
        daily["prompts_since_last_reply"] = 0
        save_daily_reco(path, daily)
