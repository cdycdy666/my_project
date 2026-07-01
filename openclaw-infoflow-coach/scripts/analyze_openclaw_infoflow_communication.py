#!/usr/bin/env python3
"""Analyze exported OpenClaw InfoFlow group logs and write communication advice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
COACH_DIR = ROOT_DIR / "feishu-communication-coach"
DEFAULT_CHAT_LOG_DIR = ROOT_DIR / "openclaw-infoflow-logs"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "openclaw-infoflow-advice"
DEFAULT_REFERENCE_DIR = COACH_DIR / "references"
DEFAULT_REFERENCE_CARD_PATH = COACH_DIR / "reference-notes/communication-principle-cards.md"
DEFAULT_OPENCLAW_CONFIG = Path.home() / ".openclaw/openclaw.json"
DEFAULT_GROUP_ID = "12829093"
DEFAULT_FOCUS_USERS = ("chendingyu", "linbeike")
CHAT_LINE_RE = re.compile(r"^- \*\*(?P<time>\d{2}:\d{2}:\d{2}) (?P<speaker>[^*]+)\*\*：(?P<body>.*)$")

sys.path.insert(0, str(COACH_DIR))

from feishu_communication_coach.llm import chat_completion  # noqa: E402
from feishu_communication_coach.references import build_reference_context  # noqa: E402


SYSTEM_PROMPT = """你是用户的群聊沟通教练。

任务：阅读当天如流群聊记录，结合参考资料，给用户可执行的沟通建议。

重点分析对象：{focus_users}

要求：
- 中文输出。
- 聚焦用户自己的表达方式，不评价别人，不做心理诊断。
- 只基于聊天记录做低置信度判断，避免过度解读。
- 你看到的是 OpenClaw 已捕获记录，不等于真实群聊全量历史；涉及缺失时必须说“已捕获记录中未看到”，不要说“当天没有”。
- 主要分析重点对象之间或围绕重点对象发生的对话；机器人回复和其他人发言只作为必要背景。
- 如果某个重点对象在已捕获记录中没有发言，明确说明样本不足，不要强行分析关系。
- 如果一天内包含多个不相关话题，先按话题分组；只挑 1-2 个最有沟通价值的话题深入分析，不要平均铺开。
- 优先使用“沟通原则卡片库”；每次必须选 2-3 张最相关卡片作为分析框架。
- 优先指出 1 个最值得调整的沟通模式。
- 建议必须能落到下一次真实聊天的一句话或一个动作。
- 必须实质使用参考资料：先提炼 2-3 个参考原则，再把每个原则映射到具体聊天片段，最后给出行动建议。
- 参考原则要标注来源资料名，但不要长篇引用原文；引用原句时每条不超过 20 个字。
- 不要堆书名。只使用能解释当天聊天的资料原则。
- 如果当天记录主要是测试/调试机器人，也要从“表达清晰度、验证方式、协作推进”角度给建议。

固定输出结构：
# 沟通建议 - {date}

## 话题分组
- 话题：
  涉及片段：
  是否深入分析：

## 今日观察
...

## 参考框架
- 原则：
  来源：
  对应聊天片段：
  解释：

## 最值得调整
...

## 下一次可以这样说
...

## 可借用的原则
...
"""


@dataclass(frozen=True)
class ModelConfig:
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class InfoFlowConfig:
    api_host: str
    app_key: str
    app_secret: str
    connection_mode: str


@dataclass(frozen=True)
class ChatMessage:
    time_label: str
    speaker: str
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze exported InfoFlow group logs.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--chat-log-dir", type=Path, default=DEFAULT_CHAT_LOG_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--reference-card-path", type=Path, default=DEFAULT_REFERENCE_CARD_PATH)
    parser.add_argument("--openclaw-config", type=Path, default=DEFAULT_OPENCLAW_CONFIG)
    parser.add_argument("--group-id", default=DEFAULT_GROUP_ID)
    parser.add_argument(
        "--focus-user",
        action="append",
        default=None,
        help="Speaker name to prioritize in the analysis. Repeat to include multiple users.",
    )
    parser.add_argument("--send-to-group", action="store_true", help="Send the advice back to the InfoFlow group.")
    parser.add_argument("--send-timeout", type=int, default=30)
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Build inputs but do not call the LLM.")
    return parser.parse_args()


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_model_config(openclaw_config: Path) -> ModelConfig:
    env: dict[str, str] = {}
    env.update(read_env_file(ROOT_DIR / ".env"))
    env.update(read_env_file(COACH_DIR / ".env"))

    api_key = env.get("LLM_API_KEY") or env.get("COMATE_API_KEY") or env.get("DASHSCOPE_API_KEY") or ""
    base_url = env.get("LLM_BASE_URL") or env.get("COMATE_BASE_URL") or env.get("DASHSCOPE_BASE_URL") or ""
    model = env.get("LLM_MODEL") or env.get("COMATE_MODEL") or env.get("DASHSCOPE_MODEL") or ""
    if api_key and base_url and model:
        return ModelConfig(api_key=api_key, base_url=base_url, model=model)

    config = read_json(openclaw_config.expanduser())
    primary = (
        config.get("agents", {})
        .get("defaults", {})
        .get("model", {})
        .get("primary", "")
    )
    provider_name, _, model_name = str(primary).partition("/")
    provider = config.get("models", {}).get("providers", {}).get(provider_name, {})
    if not api_key:
        api_key = str(provider.get("apiKey") or "")
    if not base_url:
        base_url = str(provider.get("baseUrl") or "")
    if not model:
        model = model_name or str(provider.get("model") or "")
    if not api_key or not base_url or not model:
        raise RuntimeError("No LLM config found in .env or ~/.openclaw/openclaw.json")
    return ModelConfig(api_key=api_key, base_url=base_url, model=model)


def load_infoflow_config(openclaw_config: Path) -> InfoFlowConfig:
    config = read_json(openclaw_config.expanduser())
    raw = config.get("channels", {}).get("infoflow", {})
    if not isinstance(raw, dict):
        raw = {}

    account_id = str(raw.get("defaultAccount") or "default")
    accounts = raw.get("accounts")
    account = accounts.get(account_id, {}) if isinstance(accounts, dict) else {}
    if not isinstance(account, dict):
        account = {}

    merged = {key: value for key, value in raw.items() if key not in {"accounts", "defaultAccount"}}
    merged.update(account)

    api_host = str(merged.get("apiHost") or "https://apiin.im.baidu.com").rstrip("/")
    app_key = os.environ.get("INFOFLOW_APP_KEY", "").strip() or str(merged.get("appKey") or "")
    app_secret = os.environ.get("INFOFLOW_APP_SECRET", "").strip() or str(merged.get("appSecret") or "")
    connection_mode = str(merged.get("connectionMode") or "webhook")
    if not app_key or not app_secret:
        raise RuntimeError("InfoFlow appKey/appSecret not found in ~/.openclaw/openclaw.json")
    return InfoFlowConfig(
        api_host=ensure_https(api_host),
        app_key=app_key,
        app_secret=app_secret,
        connection_mode=connection_mode,
    )


def ensure_https(api_host: str) -> str:
    if api_host.startswith("http://") and "localhost" not in api_host and "127.0.0.1" not in api_host:
        return "https://" + api_host.removeprefix("http://")
    return api_host


def read_chat_log(chat_log_dir: Path, date_label: str) -> str:
    path = chat_log_dir.expanduser() / f"{date_label}.md"
    if not path.exists():
        raise FileNotFoundError(f"Chat log not found: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def read_reference_cards(path: Path) -> str:
    expanded = path.expanduser()
    if not expanded.exists():
        return ""
    return expanded.read_text(encoding="utf-8", errors="ignore").strip()


def trim_middle(text: str, max_chars: int, omission_note: str) -> str:
    if len(text) <= max_chars:
        return text
    head_len = max_chars // 2
    tail_len = max_chars - head_len
    return text[:head_len].rstrip() + f"\n\n{omission_note}\n\n" + text[-tail_len:].lstrip()


def trim_reference_cards(text: str, max_chars: int = 16000) -> str:
    return trim_middle(text, max_chars, "...（中间部分卡片略，保留首尾卡片和示例）...")


def parse_chat_messages(chat_log: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    current: dict[str, str] | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal current, body_lines
        if current is None:
            return
        messages.append(
            ChatMessage(
                time_label=current["time"],
                speaker=current["speaker"],
                body="\n".join(body_lines).strip(),
            )
        )
        current = None
        body_lines = []

    for line in chat_log.splitlines():
        match = CHAT_LINE_RE.match(line)
        if match:
            flush()
            current = {"time": match.group("time"), "speaker": match.group("speaker").strip()}
            body_lines = [match.group("body").strip()]
            continue
        if current is not None:
            body_lines.append(line[2:] if line.startswith("  ") else line)
    flush()
    return messages


def normalize_speaker(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().lower()


def format_message(message: ChatMessage) -> str:
    body = message.body.replace("\n", "\n  ")
    return f"- **{message.time_label} {message.speaker}**：{body}"


def coverage_label(messages: list[ChatMessage]) -> str:
    if not messages:
        return "无"
    return f"{messages[0].time_label} - {messages[-1].time_label}"


def build_focus_chat_log(date_label: str, group_id: str, chat_log: str, focus_users: tuple[str, ...]) -> str:
    messages = parse_chat_messages(chat_log)
    focus_names = {normalize_speaker(user) for user in focus_users}
    focused = [message for message in messages if normalize_speaker(message.speaker) in focus_names]
    present = sorted({message.speaker for message in focused}, key=normalize_speaker)
    missing = [user for user in focus_users if normalize_speaker(user) not in {normalize_speaker(name) for name in present}]

    lines = [
        f"# 重点聊天记录 - {date_label}",
        "",
        f"群聊：`{group_id}`",
        f"完整记录时间范围：`{coverage_label(messages)}`（本地时间，仅代表 OpenClaw 已捕获消息）",
        f"重点记录时间范围：`{coverage_label(focused)}`（本地时间）",
        f"重点对象：{', '.join(focus_users)}",
        f"命中消息数：{len(focused)}",
    ]
    if missing:
        lines.append(f"已捕获记录中缺少发言：{', '.join(missing)}")
    lines.extend(["", "## 重点记录", ""])
    if focused:
        lines.extend(format_message(message) for message in focused)
    else:
        lines.append("未发现重点对象的发言。")
    return "\n".join(lines).strip()


def build_reference_query(focus_chat_log: str) -> str:
    return "\n".join(
        [
            focus_chat_log[-5000:],
            "观察 感受 需要 请求 倾听 复述 确认 反馈 边界",
            "开放式问题 校准问题 镜像 标注 战术共情 谈判",
            "表达清晰 意图 对齐 关系推进 冲突 降低防御",
        ]
    )


def build_prompt(
    date_label: str,
    chat_log: str,
    focus_chat_log: str,
    reference_cards: str,
    reference_context: str,
    focus_users: tuple[str, ...],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(date=date_label, focus_users=", ".join(focus_users)),
        },
        {
            "role": "user",
            "content": (
                f"日期：{date_label}\n\n"
                f"重点聊天记录：\n{focus_chat_log[-12000:]}\n\n"
                f"完整背景记录（只在判断上下文时参考，不要被机器人测试对话带偏）：\n{chat_log[-4000:]}\n\n"
                f"沟通原则卡片库（优先使用；必须先选 2-3 张卡片作为分析框架）：\n"
                f"{trim_reference_cards(reference_cards) if reference_cards else '无'}\n\n"
                f"原始参考资料片段（用于补充卡片，不要照抄；不要只在最后泛泛提到）：\n"
                f"{reference_context[-9000:] if reference_context else '无'}"
            ),
        },
    ]


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"InfoFlow API failed: HTTP {exc.code} {body[:500]}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"InfoFlow API returned non-JSON response: {body[:500]}") from exc
    return parsed if isinstance(parsed, dict) else {}


def infoflow_headers(config: InfoFlowConfig, extra: dict[str, str] | None = None) -> dict[str, str]:
    access_channel = (
        "plugin_openclaw_sandbox"
        if config.connection_mode == "webhook" and os.environ.get("INFOFLOW_APP_KEY", "").strip()
        else "plugin_openclaw_local"
    )
    headers = {"X-OP-ACCESS-CHANNEL": access_channel}
    headers.update(extra or {})
    return headers


def fetch_infoflow_token(config: InfoFlowConfig, timeout: int) -> str:
    signed_secret = hashlib.md5(config.app_secret.encode("utf-8")).hexdigest().lower()
    data = post_json(
        f"{config.api_host}/api/v1/auth/app_access_token",
        {"app_key": config.app_key, "app_secret": signed_secret},
        infoflow_headers(config, {"Content-Type": "application/json"}),
        timeout,
    )
    token = data.get("data", {}).get("app_access_token")
    if data.get("code") != "ok" or not token:
        message = data.get("message") or data.get("errmsg") or data.get("code") or "unknown error"
        raise RuntimeError(f"Failed to get InfoFlow token: {message}")
    return str(token)


def trim_group_message(advice: str, max_chars: int = 2800) -> str:
    text = advice.rstrip()
    if len(text) <= max_chars:
        return text
    suffix = "\n\n...完整版本已保存到本地建议文件。"
    return text[: max_chars - len(suffix)].rstrip() + suffix


def send_infoflow_group_message(
    *,
    config: InfoFlowConfig,
    group_id: str,
    content: str,
    timeout: int,
) -> str:
    token = fetch_infoflow_token(config, timeout)
    data = post_json(
        f"{config.api_host}/api/v1/robot/msg/groupmsgsend",
        {
            "message": {
                "header": {
                    "toid": int(group_id),
                    "totype": "GROUP",
                    "msgtype": "MD",
                    "clientmsgid": int(time.time() * 1000),
                    "role": "robot",
                },
                "body": [{"type": "MD", "content": trim_group_message(content)}],
            }
        },
        infoflow_headers(
            config,
            {
                "Authorization": f"Bearer-{token}",
                "Content-Type": "application/json",
            },
        ),
        timeout,
    )
    if data.get("code") != "ok":
        message = data.get("message") or data.get("errmsg") or data.get("code") or "unknown error"
        raise RuntimeError(f"Failed to send InfoFlow group message: {message}")
    inner = data.get("data")
    if isinstance(inner, dict) and inner.get("errcode") not in (None, 0, "0"):
        raise RuntimeError(f"Failed to send InfoFlow group message: {inner.get('errmsg') or inner.get('errcode')}")
    message_id = ""
    if isinstance(inner, dict):
        nested = inner.get("data")
        if isinstance(nested, dict):
            message_id = str(nested.get("messageid") or nested.get("msgid") or "")
        message_id = message_id or str(inner.get("messageid") or inner.get("msgid") or "")
    return message_id


def main() -> int:
    args = parse_args()
    date_label = args.date
    focus_users = tuple(args.focus_user or DEFAULT_FOCUS_USERS)
    chat_log = read_chat_log(args.chat_log_dir, date_label)
    focus_chat_log = build_focus_chat_log(date_label, args.group_id, chat_log, focus_users)
    reference_cards = read_reference_cards(args.reference_card_path)
    reference_context = build_reference_context(
        args.reference_dir.expanduser(),
        build_reference_query(focus_chat_log),
        max_chars=9000,
        max_chunks=8,
    )
    messages = build_prompt(date_label, chat_log, focus_chat_log, reference_cards, reference_context, focus_users)

    if args.dry_run:
        print(messages[-1]["content"][:4000])
        return 0

    model_config = load_model_config(args.openclaw_config)
    advice = chat_completion(
        api_key=model_config.api_key,
        base_url=model_config.base_url,
        model=model_config.model,
        messages=messages,
        temperature=0.35,
        timeout=90,
    )

    if args.print_only:
        print(advice)
        return 0

    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_label}.md"
    output_path.write_text(advice.rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    if args.send_to_group:
        infoflow_config = load_infoflow_config(args.openclaw_config)
        message_id = send_infoflow_group_message(
            config=infoflow_config,
            group_id=args.group_id,
            content=advice,
            timeout=args.send_timeout,
        )
        print(f"Sent advice to InfoFlow group {args.group_id}" + (f": {message_id}" if message_id else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
