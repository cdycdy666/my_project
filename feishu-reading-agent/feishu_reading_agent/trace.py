from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


_TRACE_LOCK = threading.RLock()
_SENSITIVE_KEY_NAMES = {"authorization", "password", "secret", "token", "key"}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in _SENSITIVE_KEY_NAMES
        or normalized.endswith("_key")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
        or normalized.endswith("_password")
    )


def _utc_timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _sanitize(value: Any, max_text: int = 4000) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = "[REDACTED]"
            else:
                sanitized[key_text] = _sanitize(item, max_text=max_text)
        return sanitized

    if isinstance(value, list):
        return [_sanitize(item, max_text=max_text) for item in value[:80]]

    if isinstance(value, str):
        text = value.strip()
        if len(text) <= max_text:
            return text
        return f"{text[:max_text].rstrip()}... [truncated {len(text) - max_text} chars]"

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    return repr(value)


class InteractionTrace:
    def __init__(self, log_dir: Path, enabled: bool = True) -> None:
        self.enabled = enabled
        self.log_dir = log_dir
        self.trace_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        self.started_at = time.monotonic()

    def event(self, event_type: str, **payload: Any) -> None:
        if not self.enabled:
            return

        record = {
            "ts": _utc_timestamp(),
            "trace_id": self.trace_id,
            "event": event_type,
            **_sanitize(payload),
        }

        path = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with _TRACE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file:
                file.write(line + "\n")

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_at) * 1000)
