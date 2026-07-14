from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import load_config
from .git_sync import commit_and_push_vault
from .history import fetch_chat_history, format_records_markdown, user_text_records
from .llm import summarize_daily_records
from .memory_index import build_memory_index_for_date
from .obsidian import read_feishu_inbox, shanghai_today, write_daily_summary, write_feishu_inbox
from .service import FeishuObsidianService
from .state import get_last_chat_id, remember_summary_done


def _has_session_context(text: str) -> bool:
    return "记录会话：" in text or "AI追问（上下文，不作为事实）" in text or "AI提取事实" in text


def _without_title(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return markdown.strip()


def _summary_input(existing_inbox: str, history_records: str) -> str:
    if not existing_inbox.strip() or not _has_session_context(existing_inbox):
        return history_records

    history_body = _without_title(history_records)
    if not history_body:
        return existing_inbox

    return (
        existing_inbox.rstrip()
        + "\n\n## 飞书历史校验（用户消息原文，用于补漏和去重）\n"
        + history_body
        + "\n"
    )


def _visible_summary(markdown: str) -> str:
    return re.sub(r"\n?<!--\s*sources:\s*[^>]*-->", "", markdown, flags=re.IGNORECASE).strip()


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
    history_records = format_records_markdown(records, date_text)
    existing_inbox = read_feishu_inbox(config.vault_dir, date_text)
    raw_records = _summary_input(existing_inbox, history_records)
    inbox_path = write_feishu_inbox(config.vault_dir, date_text, raw_records)

    if not records and not existing_inbox.strip():
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
    index_path: Path | None = None
    try:
        index_path = build_memory_index_for_date(config.vault_dir, date_text)
    except Exception:
        logging.exception("memory index build failed for %s", date_text)
    remember_summary_done(config.state_path, date_text)
    commit_and_push_vault(config.vault_dir, f"daily: {date_text}")

    if notify:
        service.send_text(
            chat_id,
            (
                f"今日整理完成。\n原始记录：{inbox_path.name}\nDaily note：{daily_path.name}\n"
                f"记忆索引：{index_path.name if index_path else '本次未生成'}\n\n下面是整理后的内容："
            ),
        )
        service.send_text_chunks(chat_id, _visible_summary(summary))
    return daily_path
