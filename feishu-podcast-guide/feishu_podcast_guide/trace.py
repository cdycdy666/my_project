from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


_TRACE_LOCK = threading.RLock()


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
                **payload,
            }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            with _TRACE_LOCK:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as file:
                    file.write(line + "\n")
        except Exception:
            return
