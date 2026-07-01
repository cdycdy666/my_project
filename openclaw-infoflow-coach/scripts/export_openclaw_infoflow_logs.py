#!/usr/bin/env python3
"""Export OpenClaw InfoFlow task records into daily Markdown logs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TASKS_DIR = Path.home() / ".openclaw/plugins/infoflow-private/tasks"
DEFAULT_SESSIONS_DIR = Path.home() / ".openclaw/agents/main/sessions"
ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "openclaw-infoflow-logs"
DEFAULT_GATEWAY_LOG_DIR = Path("/tmp/openclaw")
DEFAULT_CONFIG_PATH = Path.home() / ".openclaw/openclaw.json"
DEFAULT_GROUP_IDS = ("12829093",)
INFOFLOW_EVENT_RE = re.compile(r"\[事件\]\s+(?P<kind>\S+)\s+(?P<payload>\{.*\})$")
ROBOT_INFO_RE = re.compile(r"paImId=(?P<pa>\d+),\s+groupImId=(?P<group>\d+)")
INFOFLOW_ENVELOPE_RE = re.compile(
    r"^\[Infoflow\s+"
    r"(?P<context>\S+)"
    r"(?:\s+(?P<offset>\+\S+))?"
    r"\s+(?P<time>[A-Za-z]{3}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+GMT[+-]\d{1,2})"
    r"\]\s*(?P<body>.*)$",
    re.DOTALL,
)
SYSTEM_NOTE_RE = re.compile(r"\n\n\[System:.*?\]\s*$", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export local OpenClaw InfoFlow task JSON files to daily Markdown logs."
    )
    parser.add_argument("--date", help="Date to export in YYYY-MM-DD format. Defaults to all dates.")
    parser.add_argument("--tasks-dir", type=Path, default=DEFAULT_TASKS_DIR)
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--gateway-log-dir", type=Path, default=DEFAULT_GATEWAY_LOG_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--group-id",
        action="append",
        default=list(DEFAULT_GROUP_IDS),
        help="InfoFlow group ID to export. Repeat to include multiple groups.",
    )
    return parser.parse_args()


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def local_time_label(value: str | None) -> str:
    if not value:
        return "unknown"
    dt = parse_time(value)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def local_date_label(value: str | None) -> str:
    dt = parse_time(value)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return ""
    return dt.astimezone().strftime("%Y-%m-%d")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, indent=2).strip()


def normalize_output_text(value: Any) -> str:
    text = normalize_text(value)
    marker = "[[reply_to_current]]"
    if marker not in text:
        return collapse_repeated_text(text)
    before, after = text.split(marker, 1)
    before = before.strip()
    after = after.strip()
    if before and after and before == after:
        return before
    return collapse_repeated_text("\n\n".join(part for part in [before, after] if part))


def collapse_repeated_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    half = len(stripped) // 2
    if len(stripped) % 2 == 0 and stripped[:half].strip() == stripped[half:].strip():
        return stripped[:half].strip()
    return stripped


def strip_system_note(text: str) -> str:
    return SYSTEM_NOTE_RE.sub("", text).strip()


def parse_infoflow_time(value: str) -> datetime | None:
    match = re.search(r"GMT([+-])(\d{1,2})$", value)
    if not match:
        return None
    normalized = value[: match.start()] + f"{match.group(1)}{int(match.group(2)):02d}00"
    try:
        return datetime.strptime(normalized, "%a %Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None


def iso_from_epoch_ms(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def compact_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_leading_mentions(text: str) -> str:
    return re.sub(r"^(?:@[^@\s\n]+(?:\(robotid:\d+\))?\s*)+", "", text).strip()


def is_progress_message(text: str) -> bool:
    return "点我看过程" in text or "执行中...发送 stop" in text


def is_internal_coach_message(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("# 沟通建议 -") or "完整版本已保存到本地建议文件" in stripped


def is_internal_context_message(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("[Chat messages since") or "[Current message - respond to this]" in stripped


def comparable_chat(message: dict[str, str]) -> str:
    chat = message.get("chat", "")
    if message.get("source") != "group":
        return chat
    match = re.search(r"group(?:id)?:?(\d+)", chat, re.IGNORECASE)
    return f"group:{match.group(1)}" if match else chat


def comparable_body(message: dict[str, str]) -> str:
    return compact_key(strip_leading_mentions(message.get("body", "")))


def normalize_group_ids(values: list[str] | None) -> set[str]:
    return {normalize_text(value) for value in values or [] if normalize_text(value)}


def extract_group_id(value: str) -> str:
    match = re.search(r"(?:^|:)groupid:(\d+)(?:[;:]|$)", value, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(?:^|:)group:(\d+)(?:[;:]|$)", value, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def record_group_id(record: dict[str, str]) -> str:
    if record.get("source") != "group":
        return ""
    return extract_group_id(record.get("chat", ""))


def task_group_id(task: dict[str, Any]) -> str:
    return extract_group_id(normalize_text(task.get("sessionId")))


def load_robot_ids(config_path: Path = DEFAULT_CONFIG_PATH) -> set[str]:
    payload = read_json(config_path)
    if not payload:
        return set()
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return set()
    infoflow = channels.get("infoflow")
    if not isinstance(infoflow, dict):
        return set()
    robot_ids = set()
    for key in ("robotId", "paImId", "groupImId"):
        value = normalize_text(infoflow.get(key))
        if value:
            robot_ids.add(value)
    return robot_ids


def body_items_to_text(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = normalize_text(item.get("type")).upper()
        if item_type == "TEXT":
            parts.append(str(item.get("content") or ""))
        elif item_type == "AT":
            name = normalize_text(item.get("name")) or "unknown"
            robot_id = item.get("robotid")
            parts.append(f"@{name}" if robot_id is None else f"@{name}(robotid:{robot_id})")
        elif item_type == "IMAGE":
            parts.append("[图片]")
        elif item_type == "FILE":
            filename = normalize_text(item.get("filename") or item.get("name"))
            parts.append(f"[文件: {filename}]" if filename else "[文件]")
        elif item_type == "VOICE":
            parts.append("[语音]")
        else:
            content = normalize_text(item.get("content"))
            parts.append(content if content else f"[{item_type or '未知消息'}]")
    return "".join(parts).strip()


def load_infoflow_session_keys(sessions_dir: Path) -> dict[str, str]:
    index_path = sessions_dir / "sessions.json"
    payload = read_json(index_path)
    if not payload:
        return {}
    session_keys: dict[str, str] = {}
    for session_key, meta in payload.items():
        if not isinstance(session_key, str) or not session_key.startswith("agent:main:infoflow:"):
            continue
        if not isinstance(meta, dict):
            continue
        session_id = normalize_text(meta.get("sessionId"))
        if session_id:
            session_keys[session_id] = session_key
    return session_keys


def split_message_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = normalize_text(item.get("text"))
                if text:
                    texts.append(text)
            elif isinstance(item, str):
                text = normalize_text(item)
                if text:
                    texts.append(text)
        return texts
    text = normalize_text(content)
    return [text] if text else []


def parse_session_message_text(
    *,
    text: str,
    role: str,
    session_key: str,
    timestamp: str | None,
) -> dict[str, str]:
    cleaned = strip_system_note(normalize_output_text(text))
    envelope = INFOFLOW_ENVELOPE_RE.match(cleaned)
    source = "group" if ":group:" in session_key else "private"
    chat = session_key
    sender = "机器人" if role == "assistant" else "-"
    record_time = timestamp
    body = cleaned

    if envelope:
        context = envelope.group("context")
        parsed_time = parse_infoflow_time(envelope.group("time"))
        if parsed_time:
            record_time = parsed_time.isoformat()
        body = strip_system_note(envelope.group("body"))
        chat = context
        if context.startswith("group:"):
            source = "group"
            parts = context.split(":")
            sender = parts[-1] if len(parts) >= 3 else "-"
        else:
            source = "private"
            sender = context
    elif role == "assistant":
        sender = "机器人"
    elif session_key.startswith("agent:main:infoflow:direct:"):
        source = "private"
        sender = session_key.rsplit(";", 1)[-1] if ";" in session_key else "-"
        chat = session_key

    return {
        "time": record_time or "",
        "date": local_date_label(record_time),
        "source": source,
        "chat": chat,
        "sender": sender,
        "role": role,
        "body": body,
    }


def collect_session_messages(
    sessions_dir: Path,
    date_label: str | None = None,
    group_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    if not sessions_dir.exists():
        return []
    session_keys = load_infoflow_session_keys(sessions_dir)
    messages: list[dict[str, str]] = []

    for path in sorted(sessions_dir.glob("*.jsonl")):
        if path.name.endswith(".trajectory.jsonl") or path.name.startswith("probe-"):
            continue
        session_id = ""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        if not lines:
            continue
        first = json.loads(lines[0])
        if isinstance(first, dict):
            session_id = normalize_text(first.get("id"))
        session_key = session_keys.get(session_id, "")
        is_infoflow_session = session_key.startswith("agent:main:infoflow:")

        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "message":
                continue
            message = entry.get("message")
            if not isinstance(message, dict):
                continue
            role = normalize_text(message.get("role"))
            if role not in {"user", "assistant"}:
                continue
            raw_timestamp = entry.get("timestamp")
            timestamp = raw_timestamp if isinstance(raw_timestamp, str) else iso_from_epoch_ms(message.get("timestamp"))
            for text in split_message_texts(message.get("content")):
                if not is_infoflow_session and "[Infoflow " not in text:
                    continue
                record = parse_session_message_text(
                    text=text,
                    role=role,
                    session_key=session_key or f"session:{session_id}",
                    timestamp=timestamp,
                )
                if record["role"] == "assistant" and record["body"].strip() == "NO_REPLY":
                    continue
                if record["role"] == "user" and is_internal_context_message(record["body"]):
                    continue
                if group_ids is not None and record_group_id(record) not in group_ids:
                    continue
                if date_label and record["date"] != date_label:
                    continue
                messages.append(record)

    return sorted(messages, key=lambda item: (parse_time(item.get("time")), item.get("role", "")))


def collect_gateway_event_messages(
    gateway_log_dir: Path,
    date_label: str | None = None,
    group_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    if not gateway_log_dir.exists():
        return []

    paths = sorted(gateway_log_dir.glob("openclaw-*.log"))
    if date_label:
        paths = [path for path in paths if date_label in path.name]

    messages: list[dict[str, str]] = []
    seen_event_ids: set[str] = set()
    robot_ids = load_robot_ids()
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            robot_match = ROBOT_INFO_RE.search(line)
            if robot_match:
                robot_ids.update({robot_match.group("pa"), robot_match.group("group")})
        for line in lines:
            try:
                outer = json.loads(line)
            except json.JSONDecodeError:
                continue
            log_message = outer.get("message")
            if not isinstance(log_message, str) or "[事件]" not in log_message:
                continue
            match = INFOFLOW_EVENT_RE.search(log_message)
            if not match:
                continue
            try:
                payload = json.loads(match.group("payload"))
            except json.JSONDecodeError:
                continue

            message = payload.get("message")
            if not isinstance(message, dict):
                continue
            header = message.get("header")
            if not isinstance(header, dict):
                header = {}

            body = body_items_to_text(message.get("body"))
            if not body:
                continue
            if is_progress_message(body):
                continue
            if is_internal_coach_message(body):
                continue

            kind = normalize_text(match.group("kind"))
            event_type = normalize_text(payload.get("eventtype"))
            source = "group" if kind.startswith("group") or header.get("totype") == "GROUP" else "private"
            group_id = normalize_text(payload.get("groupid") or header.get("toid"))
            if group_ids is not None and group_id not in group_ids:
                continue
            sender = normalize_text(header.get("fromuserid") or payload.get("fromid")) or "-"
            role = "assistant" if sender in robot_ids else "user"
            if role == "assistant":
                body = strip_leading_mentions(body)
            message_id = normalize_text(header.get("messageid") or payload.get("msgid2") or header.get("clientmsgid"))
            event_id = f"{kind}:{event_type}:{message_id}:{compact_key(body)}"
            if event_id in seen_event_ids:
                continue
            seen_event_ids.add(event_id)

            timestamp = iso_from_epoch_ms(header.get("servertime") or payload.get("time"))
            outer_time = normalize_text(outer.get("time"))
            record = {
                "time": timestamp or outer_time,
                "date": local_date_label(timestamp or outer_time),
                "source": source,
                "chat": f"group:{group_id}:{sender}" if source == "group" else f"infoflow:{sender}",
                "sender": sender,
                "role": role,
                "body": body,
                "eventtype": event_type,
                "message_id": message_id,
            }
            if date_label and record["date"] != date_label:
                continue
            messages.append(record)

    return sorted(messages, key=lambda item: (parse_time(item.get("time")), item.get("message_id", "")))


def dedupe_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    by_message_id: dict[str, dict[str, str]] = {}
    no_message_id: list[dict[str, str]] = []
    for message in messages:
        message_id = message.get("message_id")
        if message_id:
            by_message_id.setdefault(message_id, message)
        else:
            no_message_id.append(message)

    deduped = list(by_message_id.values())
    for message in no_message_id:
        message_time = parse_time(message.get("time"))
        message_key = (
            message.get("source", ""),
            message.get("role", ""),
            message.get("chat", ""),
            message.get("sender", ""),
            compact_key(message.get("body", "")),
        )
        duplicate = False
        for existing in deduped:
            existing_key = (
                existing.get("source", ""),
                existing.get("role", ""),
                existing.get("chat", ""),
                existing.get("sender", ""),
                compact_key(existing.get("body", "")),
            )
            if message_key != existing_key:
                continue
            delta = abs((message_time - parse_time(existing.get("time"))).total_seconds())
            if delta <= 120:
                duplicate = True
                break
        if not duplicate:
            deduped.append(message)

    final: list[dict[str, str]] = []
    for message in sorted(deduped, key=lambda item: (parse_time(item.get("time")), item.get("message_id", ""))):
        message_time = parse_time(message.get("time"))
        duplicate = False
        for existing in final:
            if message.get("source") != existing.get("source"):
                continue
            if message.get("role") != existing.get("role"):
                continue
            if message.get("role") == "user" and message.get("sender") != existing.get("sender"):
                continue
            if comparable_chat(message) != comparable_chat(existing):
                continue
            if comparable_body(message) != comparable_body(existing):
                continue
            delta = abs((message_time - parse_time(existing.get("time"))).total_seconds())
            if delta <= 120:
                duplicate = True
                break
        if not duplicate:
            final.append(message)

    return sorted(final, key=lambda item: (parse_time(item.get("time")), item.get("role", "")))


def fence(text: str) -> str:
    if not text:
        return "_空_"
    if "```" not in text:
        return f"```text\n{text}\n```"
    return f"~~~text\n{text}\n~~~"


def summarize_task(task: dict[str, Any]) -> str:
    status = normalize_text(task.get("status")) or "unknown"
    model = normalize_text(task.get("modelName")) or "-"
    start = local_time_label(task.get("startTime"))
    end = local_time_label(task.get("endTime"))
    session = normalize_text(task.get("sessionId")) or "-"
    message = normalize_text(task.get("message"))
    output = normalize_output_text(task.get("output"))
    if output == "NO_REPLY":
        output = ""
    error = normalize_text(task.get("error"))

    usage = task.get("usage")
    usage_text = ""
    if isinstance(usage, dict) and usage:
        parts = [f"{key}={value}" for key, value in sorted(usage.items())]
        usage_text = " · ".join(parts)

    lines = [
        f"## {start}",
        "",
        f"- 状态: `{status}`",
        f"- 模型: `{model}`",
        f"- 结束: `{end}`",
        f"- 会话: `{session}`",
    ]
    if usage_text:
        lines.append(f"- 用量: {usage_text}")
    lines.extend(["", "### 用户", "", fence(message), "", "### 机器人", "", fence(output)])
    if error:
        lines.extend(["", "### 错误", "", fence(error)])
    return "\n".join(lines)


def summarize_message(record: dict[str, str]) -> str:
    dt = parse_time(record.get("time"))
    time = "unknown" if dt == datetime.min.replace(tzinfo=timezone.utc) else dt.astimezone().strftime("%H:%M:%S")
    sender = "机器人" if record.get("role") == "assistant" else record.get("sender") or "-"
    body = record.get("body", "").strip()
    if not body:
        body = "_空_"
    body = body.replace("\n", "\n  ")
    return f"- **{time} {sender}**：{body}"


def message_time_range(messages: list[dict[str, str]]) -> str:
    times = [parse_time(message.get("time")) for message in messages]
    times = [time for time in times if time != datetime.min.replace(tzinfo=timezone.utc)]
    if not times:
        return "无"
    start = min(times).astimezone().strftime("%H:%M:%S")
    end = max(times).astimezone().strftime("%H:%M:%S")
    return f"{start} - {end}"


def collect_tasks(day_dir: Path, group_ids: set[str] | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(day_dir.glob("*.json")):
        task = read_json(path)
        if not task:
            continue
        if group_ids is not None and task_group_id(task) not in group_ids:
            continue
        task["_source_path"] = str(path)
        tasks.append(task)
    return sorted(tasks, key=lambda item: (parse_time(item.get("startTime")), item.get("id", "")))


def render_day(
    date_label: str,
    tasks: list[dict[str, Any]],
    messages: list[dict[str, str]],
    group_ids: set[str] | None = None,
) -> str:
    group_label = ", ".join(sorted(group_ids)) if group_ids else "全部"
    lines = [
        f"# 如流群聊记录 - {date_label}",
        "",
        f"群聊：`{group_label}`",
        f"记录时间范围：`{message_time_range(messages)}`（本地时间，仅代表 OpenClaw 已捕获到的消息）",
        f"消息数：{len(messages)}",
        "",
        "## 聊天记录",
        "",
    ]
    if not messages:
        lines.append("_暂无聊天消息_")
    else:
        lines.extend(summarize_message(message) for message in messages)
    return "\n".join(lines).rstrip() + "\n"


def export_date(
    tasks_dir: Path,
    sessions_dir: Path,
    gateway_log_dir: Path,
    output_dir: Path,
    date_label: str,
    group_ids: set[str] | None = None,
) -> Path | None:
    day_dir = tasks_dir / date_label
    messages = dedupe_messages(
        collect_gateway_event_messages(gateway_log_dir, date_label, group_ids)
        + collect_session_messages(sessions_dir, date_label, group_ids)
    )
    tasks = collect_tasks(day_dir, group_ids) if day_dir.exists() else []
    if not tasks and not messages:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_label}.md"
    output_path.write_text(render_day(date_label, tasks, messages, group_ids), encoding="utf-8")
    return output_path


def available_dates(
    tasks_dir: Path,
    sessions_dir: Path,
    gateway_log_dir: Path,
    group_ids: set[str] | None = None,
) -> list[str]:
    dates = set()
    if tasks_dir.exists():
        for path in tasks_dir.iterdir():
            if path.is_dir() and collect_tasks(path, group_ids):
                dates.add(path.name)
    for message in collect_session_messages(sessions_dir, group_ids=group_ids):
        if message.get("date"):
            dates.add(message["date"])
    for message in collect_gateway_event_messages(gateway_log_dir, group_ids=group_ids):
        if message.get("date"):
            dates.add(message["date"])
    return sorted(dates)


def main() -> int:
    args = parse_args()
    tasks_dir: Path = args.tasks_dir.expanduser()
    sessions_dir: Path = args.sessions_dir.expanduser()
    gateway_log_dir: Path = args.gateway_log_dir.expanduser()
    output_dir: Path = args.output_dir.expanduser()
    group_ids = normalize_group_ids(args.group_id)

    if args.date:
        exported = export_date(tasks_dir, sessions_dir, gateway_log_dir, output_dir, args.date, group_ids)
        if not exported:
            print(f"No InfoFlow records for {args.date}: {tasks_dir / args.date}")
            return 0
        print(f"Exported {exported}")
        return 0

    exported_paths: list[Path] = []
    dates = available_dates(tasks_dir, sessions_dir, gateway_log_dir, group_ids)
    if not dates:
        print(f"No InfoFlow records found: tasks={tasks_dir}, sessions={sessions_dir}")
        return 0
    for date_label in dates:
        exported = export_date(tasks_dir, sessions_dir, gateway_log_dir, output_dir, date_label, group_ids)
        if exported:
            exported_paths.append(exported)
    for path in exported_paths:
        print(f"Exported {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
