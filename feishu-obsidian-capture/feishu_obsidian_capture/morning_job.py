from __future__ import annotations

import logging
from datetime import date
from datetime import timedelta
from pathlib import Path

from .config import load_config
from .daily_job import run_daily_summary
from .llm import generate_morning_message
from .obsidian import daily_note_path, shanghai_today
from .service import FeishuObsidianService
from .state import get_last_chat_id, get_last_summary_date


FALLBACK_MESSAGE = "早上好。今天遇到问题、做判断、有反馈或下一步时，随手发我一句就行，晚上我会整理进 Obsidian。"


def _recent_daily_notes(vault_dir: Path, limit: int = 5) -> str:
    daily_dir = vault_dir / "10-daily"
    if not daily_dir.exists():
        return ""

    paths = sorted(daily_dir.glob("*/*.md"), reverse=True)[:limit]
    chunks: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        chunks.append(f"--- {path.name} ---\n{text[:2500]}")
    return "\n\n".join(chunks)


def _ensure_yesterday_summary(base_dir: Path, notify: bool = True) -> None:
    config = load_config(base_dir)
    today = shanghai_today()
    yesterday_text = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    if get_last_summary_date(config.state_path) == yesterday_text:
        return
    if daily_note_path(config.vault_dir, yesterday_text).exists():
        return

    logging.info("yesterday summary missing, backfilling %s", yesterday_text)
    run_daily_summary(date_text=yesterday_text, notify=notify)


def run_morning_reminder() -> str:
    base_dir = Path(__file__).resolve().parents[1]
    config = load_config(base_dir)
    chat_id = get_last_chat_id(config.state_path)
    if not chat_id:
        raise RuntimeError("No bound Feishu chat_id. Run the long-connection service once and send 绑定.")

    _ensure_yesterday_summary(base_dir, notify=True)

    context = _recent_daily_notes(config.vault_dir)
    if context and config.llm_api_key:
        message = generate_morning_message(
            config.llm_api_key,
            config.llm_base_url,
            config.llm_model,
            context,
        )
    else:
        message = FALLBACK_MESSAGE

    service = FeishuObsidianService(config)
    service.send_text(chat_id, message)
    return message
