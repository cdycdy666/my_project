from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

from .agent import PodcastGuideAgent
from .config import Config, load_config, require_feishu_config
from .state import remember_chat, remember_processed_message


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


class FeishuPodcastGuideService:
    def __init__(self, config: Config) -> None:
        require_feishu_config(config)
        self.config = config
        self.agent = PodcastGuideAgent(config)
        self.client = (
            lark.Client.builder()
            .app_id(config.app_id)
            .app_secret(config.app_secret)
            .log_level(lark.LogLevel.WARNING)
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
        logging.info("sent podcast reply to chat_id=%s", chat_id)

    def send_text_chunks(self, chat_id: str, text: str, chunk_size: int = 3000) -> None:
        content = text.strip()
        if not content:
            return

        chunks = [content[index : index + chunk_size] for index in range(0, len(content), chunk_size)]
        for index, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                self.send_text(chat_id, f"播客导览 {index}/{len(chunks)}\n{chunk}")
            else:
                self.send_text(chat_id, chunk)

    def handle_message(self, data: Any) -> None:
        event = _get(data, "event")
        message = _get(event, "message")
        chat_id = _get(message, "chat_id")
        message_id = _get(message, "message_id") or ""
        message_type = _get(message, "message_type")
        text = _message_content_text(_get(message, "content")).strip()

        logging.info(
            "received Feishu podcast event: chat_id=%s message_id=%s message_type=%s text=%r event=%s",
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
            logging.info("duplicate message ignored: message_id=%s", message_id)
            return

        threading.Thread(
            target=self._process_message,
            args=(chat_id, message_type, text),
            daemon=True,
        ).start()

    def _process_message(self, chat_id: str, message_type: str, text: str) -> None:
        try:
            if message_type != "text":
                self.send_text(chat_id, "我第一版先处理文字消息。你可以问：Agent 从哪几集开始听？")
                return

            reply = self.agent.reply(text, chat_id=chat_id)
            self.send_text_chunks(chat_id, reply)
        except Exception as exc:
            logging.exception("podcast message processing failed")
            self.send_text(chat_id, f"这次播客导览失败：{exc}")

    def handle_debug_event(self, data: Any) -> None:
        logging.info("received Feishu debug event: %s", _preview(data, limit=1000))


def build_event_handler(service: FeishuPodcastGuideService) -> lark.EventDispatcherHandler:
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
    project_dir = Path(__file__).resolve().parents[1]
    config = load_config(project_dir)
    service = FeishuPodcastGuideService(config)

    handler = build_event_handler(service)
    ws_client = lark.ws.Client(
        config.app_id,
        config.app_secret,
        event_handler=handler,
        log_level=lark.LogLevel.WARNING,
    )
    logging.info("%s service started. %s", config.bot_display_name, service.agent.index.stats())
    ws_client.start()


if __name__ == "__main__":
    main()
