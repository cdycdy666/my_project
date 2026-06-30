from __future__ import annotations

import logging
from pathlib import Path

from .config import load_config
from .git_sync import commit_and_push_vault
from .history import fetch_chat_history, format_records_markdown, user_text_records
from .llm import summarize_daily_records
from .obsidian import shanghai_today, write_daily_summary, write_feishu_inbox
from .service import FeishuObsidianService
from .state import get_last_chat_id, remember_summary_done


def run_daily_summary(date_text: str | None = None, notify: bool = True) -> Path | None:
    base_dir = Path(__file__).resolve().parents[1]
    config = load_config(base_dir)
    date_text = date_text or shanghai_today()
    chat_id = get_last_chat_id(config.state_path)
    if not chat_id:
        raise RuntimeError("No bound Feishu chat_id. Run the long-connection service once and send 绑定.")

    service = FeishuObsidianService(config)
    messages = fetch_chat_history(config, chat_id, date_text)
    records = user_text_records(messages)
    raw_records = format_records_markdown(records, date_text)
    inbox_path = write_feishu_inbox(config.vault_dir, date_text, raw_records)

    if not records:
        logging.info("no user text records found for %s", date_text)
        remember_summary_done(config.state_path, date_text)
        commit_and_push_vault(config.vault_dir, f"daily: {date_text}")
        if notify:
            service.send_text(chat_id, f"{date_text} 没有拉取到用户文本记录，暂不整理。")
        return None

    summary = summarize_daily_records(
        config.llm_api_key,
        config.llm_base_url,
        config.llm_model,
        date_text,
        raw_records,
    )
    daily_path = write_daily_summary(config.vault_dir, date_text, summary, raw_records)
    remember_summary_done(config.state_path, date_text)
    commit_and_push_vault(config.vault_dir, f"daily: {date_text}")

    if notify:
        service.send_text(
            chat_id,
            f"今日整理完成。\n原始记录：{inbox_path.name}\nDaily note：{daily_path.name}",
        )
    return daily_path
