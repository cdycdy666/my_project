from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
)

from .config import Config, load_config
from .git_sync import pull_vault
from .llm import generate_record_feedback
from .obsidian import (
    append_feishu_inbox_message,
    read_feishu_inbox,
)
from .state import (
    remember_processed_message,
    remember_chat,
)


HELP_TEXT = """你可以随时发送今天的记录，我会先保存原始消息，晚上统一整理到 Obsidian。

发送「整理今天」可立即触发当天整理。
发送「绑定」可把当前飞书会话设为每日提醒接收位置。
"""


def _get(obj: Any, *names: str) -> Any:
    current = obj
    for name in names:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(name)
        else:
            current = getattr(current, name, None)
    return current


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


def _preview(value: Any, limit: int = 500) -> str:
    text = repr(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


class FeishuObsidianService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = (
            lark.Client.builder()
            .app_id(config.app_id)
            .app_secret(config.app_secret)
            .log_level(lark.LogLevel.INFO)
            .build()
        )

    def send_text(self, chat_id: str, text: str) -> None:
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        response = self.client.im.v1.message.create(request)
        if not response.success():
            logging.error("send message failed: code=%s msg=%s", response.code, response.msg)
            return
        logging.info("sent reply to chat_id=%s", chat_id)

    def handle_message(self, data: Any) -> None:
        event = _get(data, "event")
        message = _get(event, "message")
        chat_id = _get(message, "chat_id")
        message_id = _get(message, "message_id") or ""
        message_type = _get(message, "message_type")
        text = _message_content_text(_get(message, "content")).strip()

        logging.info(
            "received Feishu event: chat_id=%s message_id=%s message_type=%s text=%r event=%s",
            chat_id,
            message_id,
            message_type,
            text,
            _preview(event),
        )

        if not chat_id:
            logging.warning("message ignored: missing chat_id, data=%s", _preview(data))
            return

        remember_chat(self.config.state_path, chat_id)
        if message_id and not remember_processed_message(self.config.state_path, message_id):
            logging.info("duplicate Feishu message ignored: message_id=%s text=%r", message_id, text)
            return

        threading.Thread(
            target=self._process_message,
            args=(chat_id, message_type, text),
            daemon=True,
        ).start()

    def _process_message(self, chat_id: str, message_type: str, text: str) -> None:
        try:
            self._process_message_inner(chat_id, message_type, text)
        except Exception:
            logging.exception("message processing failed")
            self.send_text(chat_id, "这条记录处理失败，请稍后重发一次。")

    def _process_message_inner(self, chat_id: str, message_type: str, text: str) -> None:
        if message_type != "text":
            self.send_text(chat_id, "已收到，但第一版只处理文字。语音可先用飞书转文字后发送「记录：...」。")
            return

        if text in {"帮助", "help", "/help"}:
            self.send_text(chat_id, HELP_TEXT)
            return

        if text in {"绑定", "/bind"}:
            self.send_text(chat_id, "已绑定当前飞书会话，后续每日提醒会发到这里。")
            return

        if text in {"整理今天", "/summary", "summary"}:
            from .daily_job import run_daily_summary

            try:
                run_daily_summary(notify=True)
            except Exception as exc:
                logging.exception("manual daily summary failed")
                self.send_text(chat_id, f"手动整理失败：{exc}")
            return

        if text:
            if text.startswith("记录：") or text.startswith("记录:"):
                text = text.split(":", 1)[1].strip() if text.startswith("记录:") else text.split("：", 1)[1].strip()
            path = append_feishu_inbox_message(self.config.vault_dir, text)
            try:
                feedback = generate_record_feedback(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    text,
                    read_feishu_inbox(self.config.vault_dir),
                )
            except Exception:
                logging.exception("record feedback failed")
                feedback = "模型反馈暂时失败，但记录已保存，晚上仍会统一整理。"
            self.send_text(chat_id, f"已记录。\n{feedback}\n原始记录：{path.name}")
            return

        self.send_text(chat_id, "记录内容为空。直接回复今天的记录即可；发送「帮助」查看推荐格式。")

    def handle_debug_event(self, data: Any) -> None:
        logging.info("received Feishu debug event: %s", _preview(data, limit=1000))


def build_event_handler(service: FeishuObsidianService) -> lark.EventDispatcherHandler:
    return (
        lark.EventDispatcherHandler.builder(
            service.config.encrypt_key,
            service.config.verification_token,
        )
        .register_p2_customized_event("im.message.receive_v1", service.handle_message)
        .register_p2_customized_event(
            "im.chat.access_event.bot_p2p_chat_entered_v1",
            service.handle_debug_event,
        )
        .register_p2_customized_event("im.chat.member.bot.added_v1", service.handle_debug_event)
        .build()
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    base_dir = Path(__file__).resolve().parents[1]
    config = load_config(base_dir)
    pull_vault(config.vault_dir)
    service = FeishuObsidianService(config)

    handler = build_event_handler(service)
    ws_client = lark.ws.Client(
        config.app_id,
        config.app_secret,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )
    logging.info("Feishu Obsidian capture service started.")
    ws_client.start()


if __name__ == "__main__":
    main()
