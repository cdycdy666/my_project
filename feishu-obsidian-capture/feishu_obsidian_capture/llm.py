from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any


SYSTEM_PROMPT = """你是用户的个人处境知识库整理助手。
任务：把用户一天中发给飞书机器人的原始记录，整理成 Obsidian daily note。

要求：
- 只基于原始记录，不要编造事实。
- 保留用户的具体处境、判断、依据、反馈和下一步。
- 同一天可能有多个互不相关的事情，必须先按主题/事件分组，不要把不相关内容混进同一组。
- 如果原始记录包含“记录会话”，同一会话下的多轮用户记录/用户补充应合并为一个事件。
- “AI追问（上下文，不作为事实）”只用于理解用户后续回答，不得当作已经发生的事实写入 daily note。
- “AI提取事实（草稿，需用户原文支持）”只是辅助草稿，必须能被用户原文支持；无法支持时不要采用。
- 如果包含“飞书历史校验”，它只用于补漏和去重，不要和记录会话重复总结。
- 原始记录中的 `record_id` 是来源标识。每个“## 事件 N：...”标题下一行必须输出一个隐藏来源注释，格式为 `<!-- sources: record_id_1, record_id_2 -->`。
- 来源注释只能填写该事件实际使用、且确实出现在原始记录中的 record_id；不要编造 ID。零散记录也尽量在对应条目后标注来源。
- 每个事件标题要具体，使用 “## 事件 1：...” 这种二级标题。
- 如果某个事件下的小节没有信息，写 "- 暂无"。
- 输出纯 Markdown，不要代码块。
- 必须使用以下整体结构：
## 今日概览
- 用 2 到 5 条概括今天的主要事件、状态和后续关注点。

## 事件 1：事件名称
<!-- sources: record_id_1, record_id_2 -->
### 发生了什么
-
### 我怎么处理的
-
### 我做出的判断
-
### 判断依据
-
### 结果 / 反馈
-
### 后续动作
-
### 值得沉淀
-

如有多个不相关事件，继续输出：
## 事件 2：事件名称
并使用同样的三级标题。

## 零散记录
- 放不足以形成事件组、但仍应保留的内容；没有则写 "- 暂无"。

## 给 AI 的长期上下文
- 放需要以后持续记住的事实、偏好、约束、模式；没有则写 "- 暂无"。
"""


MORNING_PROMPT = """你是用户的个人处境知识库提醒助手。
任务：基于用户最近几天的 Obsidian 记录，生成一条早上发给用户的飞书提醒。

要求：
- 中文。
- 1 到 2 句话，总长度不超过 90 字。
- 语气自然、克制、具体，不要鸡汤。
- 不要说“根据你的记录”。
- 不要编造新事实。
- 目标是降低记录门槛，提醒用户今天遇到问题、判断、反馈、下一步时随手发给机器人。
- 如果最近记录里有明确未完成事项或判断主题，可以轻轻点一下。
"""


RECORD_FEEDBACK_PROMPT = """你是用户的个人处境知识库反馈助手。
用户刚刚通过飞书发来一条即时记录，你要立刻给出一条有帮助的反馈。

要求：
- 中文。
- 1 到 2 句话，总长度不超过 120 字。
- 不要复述“已记录”，系统会保存记录。
- 不要整理成 Markdown，不要列表。
- 反馈要具体，指出这条记录更像问题、判断、依据、反馈、下一步或值得沉淀的经验。
- 如果记录缺少关键信息，可以只追问一个最有价值的问题。
- 不要鸡汤，不要泛泛鼓励，不要编造事实。
"""


RECORD_FEEDBACK_JSON_PROMPT = """你是用户的个人处境知识库反馈助手。
用户刚刚通过飞书发来一条即时记录。你要同时完成两件事：
1. 给用户一句即时反馈。
2. 判断这条记录是否属于一个正在进行的“记录会话”。

要求：
- 只输出 JSON，不要 Markdown，不要代码块，不要解释。
- 反馈用中文，1 到 2 句话，总长度不超过 120 字。
- 不要复述“已记录”，系统会保存记录。
- 不要编造事实。
- 如果缺少关键信息，最多追问一个最有价值的问题。
- 对“任务完成、处理动作、判断、问题发现”类记录，如果缺少结果反馈、验证方式、判断依据或下一步，need_follow_up 应为 true，并追问最关键的一个缺口。
- 只有当记录已经足够完整，或只是无需展开的零散记录时，need_follow_up 才为 false。
- 如果有 active_session，优先判断新记录是否是在回答上一轮追问；是则 continue，不是则 open。
- 如果用户表达“完成、先这样、就这样、暂时这样、结束”，session_action 应为 close。
- session_title 要具体，但不要超过 18 个汉字。
- summary_fact 是给晚间整理参考的事实草稿，必须能被用户原文支持；不确定就留空。

输出 JSON schema：
{
  "session_action": "open|continue|close",
  "session_title": "具体事件标题",
  "record_type": "问题|处理|判断|依据|反馈|下一步|值得沉淀|零散记录",
  "summary_fact": "可由用户原文支持的事实草稿，可为空",
  "need_follow_up": true,
  "follow_up_question": "只问一个问题；不需要追问则为空",
  "reply": "发给用户的即时反馈"
}
"""


def _extract_response_text(data: dict) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return content.strip()

    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    parts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("LLM JSON response is not an object")
    return value


def _string_value(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) else default


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def _normalize_record_feedback_decision(value: dict[str, Any]) -> dict[str, Any]:
    action = _string_value(value.get("session_action"), "open").lower()
    if action not in {"open", "continue", "close"}:
        action = "open"

    record_type = _string_value(value.get("record_type"), "零散记录")
    if record_type not in {"问题", "处理", "判断", "依据", "反馈", "下一步", "值得沉淀", "零散记录"}:
        record_type = "零散记录"

    return {
        "session_action": action,
        "session_title": _string_value(value.get("session_title"), "未命名记录")[:40],
        "record_type": record_type,
        "summary_fact": _string_value(value.get("summary_fact")),
        "need_follow_up": _bool_value(value.get("need_follow_up")),
        "follow_up_question": _string_value(value.get("follow_up_question")),
        "reply": _string_value(value.get("reply")),
    }


def _record_ids(text: str) -> set[str]:
    return {
        value.strip()
        for value in re.findall(r"<!--\s*record_id:\s*([^>]+?)\s*-->", text, flags=re.IGNORECASE)
        if value.strip()
    }


def _normalize_summary_source_comments(summary: str, raw_records: str) -> str:
    allowed = _record_ids(raw_records)
    if not allowed:
        return re.sub(r"\n?<!--\s*sources:\s*[^>]*-->", "", summary, flags=re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        requested = [item.strip() for item in match.group(1).split(",") if item.strip()]
        valid = list(dict.fromkeys(item for item in requested if item in allowed))
        return f"<!-- sources: {', '.join(valid)} -->" if valid else ""

    return re.sub(
        r"<!--\s*sources:\s*([^>]*)-->",
        replace,
        summary,
        flags=re.IGNORECASE,
    )


def _post_chat_completion(api_key: str, base_url: str, payload: dict[str, Any], timeout: int, retries: int) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API failed: HTTP {exc.code} {body[:800]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"LLM API failed after {retries + 1} attempts: {last_error}") from last_error


def summarize_daily_records(api_key: str, base_url: str, model: str, date_text: str, raw_records: str) -> str:
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"日期：{date_text}\n\n原始记录：\n{raw_records.strip()}",
            },
        ],
        "temperature": 0.2,
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=180, retries=2)

    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("LLM API returned an empty summary")
    return _normalize_summary_source_comments(text, raw_records)


def generate_morning_message(api_key: str, base_url: str, model: str, recent_context: str) -> str:
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": MORNING_PROMPT},
            {"role": "user", "content": f"最近记录：\n{recent_context.strip()}"},
        ],
        "temperature": 0.7,
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=90, retries=1)

    text = _extract_response_text(data).replace("\n", " ").strip()
    if not text:
        raise RuntimeError("LLM API returned an empty morning message")
    return text


def generate_record_feedback(
    api_key: str,
    base_url: str,
    model: str,
    record_text: str,
    today_context: str = "",
) -> str:
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RECORD_FEEDBACK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"刚刚的新记录：\n{record_text.strip()}\n\n"
                    f"今天已有记录上下文，可为空：\n{today_context.strip()[-3000:]}"
                ),
            },
        ],
        "temperature": 0.5,
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=45, retries=1)

    text = _extract_response_text(data).replace("\n", " ").strip()
    if not text:
        raise RuntimeError("LLM API returned an empty record feedback")
    return text


def generate_record_feedback_decision(
    api_key: str,
    base_url: str,
    model: str,
    record_text: str,
    today_context: str = "",
    active_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RECORD_FEEDBACK_JSON_PROMPT},
            {
                "role": "user",
                "content": (
                    f"刚刚的新记录：\n{record_text.strip()}\n\n"
                    f"active_session，可为空：\n{json.dumps(active_session or {}, ensure_ascii=False)}\n\n"
                    f"今天已有记录上下文，可为空：\n{today_context.strip()[-3000:]}"
                ),
            },
        ],
        "temperature": 0.3,
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=45, retries=1)

    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("LLM API returned an empty record feedback decision")
    return _normalize_record_feedback_decision(_extract_json_object(text))
