from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
)

from .config import Config, load_config
from .git_sync import pull_vault
from .llm import generate_record_feedback, generate_record_feedback_decision
from .obsidian import (
    append_feishu_inbox_message,
    read_feishu_inbox,
)
from .state import (
    clear_active_capture_session,
    get_active_capture_session,
    remember_active_capture_session,
    remember_processed_message,
    remember_chat,
)


HELP_TEXT = """你可以随时发送今天的记录，我会先保存原始消息，晚上统一整理到 Obsidian。

发送「整理今天」可立即触发当天整理。
发送「绑定」可把当前飞书会话设为每日提醒接收位置。
发送「完成」「先这样」可结束当前记录会话。
发送「新记录：...」可强制开启一个新事件。
"""

CLOSE_SESSION_COMMANDS = {"完成", "结束", "先这样", "就这样", "暂时这样", "先到这", "先到这里"}
NEW_RECORD_PREFIXES = ("新记录：", "新记录:")
RECORD_PREFIXES = ("记录：", "记录:")


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


def _strip_prefixed_text(text: str, prefixes: tuple[str, ...]) -> tuple[str, bool]:
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip(), True
    return text, False


def _new_session_id() -> str:
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


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

    def send_text_chunks(self, chat_id: str, text: str, chunk_size: int = 3000) -> None:
        content = text.strip()
        if not content:
            return

        chunks = [content[index : index + chunk_size] for index in range(0, len(content), chunk_size)]
        for index, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                self.send_text(chat_id, f"整理内容 {index}/{len(chunks)}\n{chunk}")
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
            args=(chat_id, message_type, text, message_id),
            daemon=True,
        ).start()

    def _process_message(self, chat_id: str, message_type: str, text: str, message_id: str = "") -> None:
        try:
            self._process_message_inner(chat_id, message_type, text, message_id)
        except Exception:
            logging.exception("message processing failed")
            self.send_text(chat_id, "这条记录处理失败，请稍后重发一次。")

    def _process_message_inner(
        self,
        chat_id: str,
        message_type: str,
        text: str,
        message_id: str = "",
    ) -> None:
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

        if text in CLOSE_SESSION_COMMANDS:
            if get_active_capture_session(self.config.state_path):
                clear_active_capture_session(self.config.state_path)
                self.send_text(chat_id, "已结束当前记录会话。后续消息会作为新的记录处理。")
            else:
                self.send_text(chat_id, "当前没有进行中的记录会话。直接发送新内容即可记录。")
            return

        if text:
            text, force_new = _strip_prefixed_text(text, NEW_RECORD_PREFIXES)
            if not force_new:
                text, _ = _strip_prefixed_text(text, RECORD_PREFIXES)
            if not text:
                self.send_text(chat_id, "记录内容为空。直接回复今天的记录即可；发送「帮助」查看推荐格式。")
                return

            active_session = None if force_new else get_active_capture_session(self.config.state_path)
            try:
                decision = generate_record_feedback_decision(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    text,
                    read_feishu_inbox(self.config.vault_dir),
                    active_session,
                )
                session_action = str(decision.get("session_action") or "open")
                title = str(decision.get("session_title") or "")
                if active_session and session_action in {"continue", "close"}:
                    title = title or str(active_session.get("title") or "")
                title = title or "未命名记录"
                role = "用户补充" if active_session and not force_new else "用户记录"
                follow_up = str(decision.get("follow_up_question") or "") if decision.get("need_follow_up") else ""
                session_id = (
                    str(active_session.get("id") or "")
                    if active_session and not force_new
                    else _new_session_id()
                )
                path = append_feishu_inbox_message(
                    self.config.vault_dir,
                    text,
                    session_title=title,
                    record_role=role,
                    record_type=str(decision.get("record_type") or ""),
                    ai_follow_up=follow_up,
                    ai_summary_fact=str(decision.get("summary_fact") or ""),
                    record_id=f"feishu-{message_id}" if message_id else f"capture-{uuid.uuid4().hex}",
                    session_id=session_id,
                )

                if session_action != "close" and follow_up:
                    remember_active_capture_session(
                        self.config.state_path,
                        {
                            "id": session_id,
                            "title": title,
                            "started_at": active_session.get("started_at") if active_session else "",
                            "last_question": follow_up,
                        },
                    )
                else:
                    clear_active_capture_session(self.config.state_path)

                feedback = str(decision.get("reply") or follow_up or "这条记录已进入今天的整理上下文。")
            except Exception:
                logging.exception("structured record feedback failed")
                path = append_feishu_inbox_message(
                    self.config.vault_dir,
                    text,
                    record_id=f"feishu-{message_id}" if message_id else f"capture-{uuid.uuid4().hex}",
                )
                try:
                    feedback = generate_record_feedback(
                        self.config.llm_api_key,
                        self.config.llm_base_url,
                        self.config.llm_model,
                        text,
                        read_feishu_inbox(self.config.vault_dir),
                    )
                except Exception:
                    logging.exception("record feedback fallback failed")
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
