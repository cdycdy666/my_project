from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


_TRACE_LOCK = threading.RLock()
_SENSITIVE_KEY_NAMES = {"authorization", "password", "secret", "token", "key"}
DEFAULT_MAX_TEXT = 100_000
DEFAULT_MAX_LIST_ITEMS = 500


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in _SENSITIVE_KEY_NAMES
        or normalized.endswith("_key")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
        or normalized.endswith("_password")
    )


def _sanitize(value: Any, max_text: int = DEFAULT_MAX_TEXT) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            sanitized[key_text] = "[REDACTED]" if _is_sensitive_key(key_text) else _sanitize(item, max_text=max_text)
        return sanitized
    if isinstance(value, list):
        sanitized = [_sanitize(item, max_text=max_text) for item in value[:DEFAULT_MAX_LIST_ITEMS]]
        if len(value) > DEFAULT_MAX_LIST_ITEMS:
            sanitized.append(f"... [{len(value) - DEFAULT_MAX_LIST_ITEMS} more items]")
        return sanitized
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= max_text:
            return text
        return f"{text[:max_text].rstrip()}... [truncated {len(text) - max_text} chars]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return repr(value)


class PodcastTrace:
    def __init__(self, project_dir: Path, chat_id: str, user_message: str) -> None:
        now = datetime.now(timezone.utc)
        self.trace_id = now.strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
        self.chat_id = chat_id
        self.path = project_dir / "logs" / "traces" / f"{now.astimezone().date().isoformat()}.jsonl"
        self.event("reply_start", user_message=user_message)

    def event(self, event: str, **payload: object) -> None:
        try:
            record = {
                "event": event,
                "trace_id": self.trace_id,
                "chat_id": self.chat_id,
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                **_sanitize(payload),
            }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            with _TRACE_LOCK:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as file:
                    file.write(line + "\n")
        except Exception:
            return
