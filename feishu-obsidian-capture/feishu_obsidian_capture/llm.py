from __future__ import annotations

import json
import urllib.error
import urllib.request


SYSTEM_PROMPT = """你是用户的个人处境知识库整理助手。
任务：把用户一天中发给飞书机器人的原始记录，整理成 Obsidian daily note。

要求：
- 只基于原始记录，不要编造事实。
- 保留用户的具体处境、判断、依据、反馈和下一步。
- 同一天可能有多个互不相关的事情，必须先按主题/事件分组，不要把不相关内容混进同一组。
- 每个事件标题要具体，使用 “## 事件 1：...” 这种二级标题。
- 如果某个事件下的小节没有信息，写 "- 暂无"。
- 输出纯 Markdown，不要代码块。
- 必须使用以下整体结构：
## 今日概览
- 用 2 到 5 条概括今天的主要事件、状态和后续关注点。

## 事件 1：事件名称
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
任务：基于用户最近几天的 Obsidian 记录，生成一条早上 9 点发给用户的飞书提醒。

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
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API failed: HTTP {exc.code} {body[:800]}") from exc

    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("LLM API returned an empty summary")
    return text


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
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API failed: HTTP {exc.code} {body[:800]}") from exc

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
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API failed: HTTP {exc.code} {body[:800]}") from exc

    text = _extract_response_text(data).replace("\n", " ").strip()
    if not text:
        raise RuntimeError("LLM API returned an empty record feedback")
    return text
