from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import lark_oapi as lark
from lark_oapi.api.im.v1 import ListMessageRequest

from .config import Config


SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class HistoryMessage:
    created_at: datetime
    message_id: str
    sender_type: str
    message_type: str
    text: str


def day_time_range(date_text: str) -> tuple[str, str]:
    day = date.fromisoformat(date_text)
    start = datetime.combine(day, time.min, SHANGHAI)
    end = datetime.combine(day, time.max, SHANGHAI)
    return str(int(start.timestamp())), str(int(end.timestamp()))


def _message_content_text(raw_content: Any) -> str:
    if not raw_content:
        return ""
    if isinstance(raw_content, dict):
        return str(raw_content.get("text") or "")
    if isinstance(raw_content, str):
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            return raw_content
        if isinstance(parsed, dict):
            return str(parsed.get("text") or "")
    return str(raw_content)


def _created_at(value: int | None) -> datetime:
    timestamp = int(value or 0)
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp, SHANGHAI)


def _request_builder(chat_id: str, start_time: str, end_time: str, page_token: str | None) -> ListMessageRequest:
    builder = (
        ListMessageRequest.builder()
        .container_id_type("chat")
        .container_id(chat_id)
        .start_time(start_time)
        .end_time(end_time)
        .sort_type("ByCreateTimeAsc")
        .page_size(50)
    )
    if page_token:
        builder = builder.page_token(page_token)
    return builder.build()


def fetch_chat_history(config: Config, chat_id: str, date_text: str) -> list[HistoryMessage]:
    client = (
        lark.Client.builder()
        .app_id(config.app_id)
        .app_secret(config.app_secret)
        .log_level(lark.LogLevel.INFO)
        .build()
    )
    start_time, end_time = day_time_range(date_text)
    messages: list[HistoryMessage] = []
    page_token: str | None = None

    while True:
        response = client.im.v1.message.list(_request_builder(chat_id, start_time, end_time, page_token))
        if not response.success():
            raise RuntimeError(f"fetch history failed: code={response.code} msg={response.msg}")

        data = response.data
        for item in data.items or []:
            content = item.body.content if item.body else ""
            text = _message_content_text(content).strip()
            sender_type = item.sender.sender_type if item.sender else ""
            messages.append(
                HistoryMessage(
                    created_at=_created_at(item.create_time),
                    message_id=item.message_id or "",
                    sender_type=sender_type or "",
                    message_type=item.msg_type or "",
                    text=text,
                )
            )

        if not data.has_more:
            break
        page_token = data.page_token
        if not page_token:
            break

    return messages


def user_text_records(messages: list[HistoryMessage]) -> list[HistoryMessage]:
    ignored_commands = {"帮助", "help", "/help", "绑定", "/bind", "整理今天", "/summary", "summary"}
    records: list[HistoryMessage] = []
    for message in messages:
        if message.sender_type != "user":
            continue
        if message.message_type != "text":
            continue
        if not message.text or message.text in ignored_commands:
            continue
        records.append(message)
    return records


def format_records_markdown(records: list[HistoryMessage], date_text: str) -> str:
    lines = [f"# {date_text} 飞书原始记录"]
    for record in records:
        lines.append("")
        lines.append(f"## {record.created_at.strftime('%H:%M')}")
        if record.message_id:
            lines.append(f"<!-- record_id: feishu-{record.message_id} -->")
        lines.append(record.text)
    return "\n".join(lines).rstrip() + "\n"
