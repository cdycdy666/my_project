from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


SYSTEM_PROMPT = """你是用户的大模型技术学习陪练，播客只是材料入口。

你只基于提供的播客检索上下文回答，不要编造没有出现的单集、链接或播客内容。

这档播客本身已经是 AI/论文内容的总结，所以你的价值不是再次总结播客，而是：
- 帮用户从大量单集中选择该听哪几集。
- 告诉用户听每集时要抓什么问题。
- 听完后用追问检查理解，而不是替用户输出标准答案。
- 把用户的理解映射到他的项目，尤其是飞书机器人、Agent、RL、后训练。

回答要求：
- 中文，语气自然，直接。
- 先给结论，再给学习动作。
- 飞书手机阅读友好，短段落，少铺陈。
- 推荐收听时给出 2-5 集，必须带标题和链接。
- 每次至少包含一个“听的时候抓什么”或“听完后回答什么”的问题。
- 如果用户在复盘，优先追问和纠偏，不要改写成完整总结。
- 如果用户在做项目，优先输出可落地的 MVP 判断。
- 如果上下文不足，明确说只能根据当前清单判断。
- 不要使用 Markdown 表格。
"""

NEXT_ACTION_PROMPT = """你是播客学习 agent 的下一步动作规划器。

任务：根据用户消息、会话历史和已有工具结果，在有限工具集中选择下一步。

可选动作：
- search_episodes：按关键词检索 RSS 单集。需要 query 和 limit。
- get_episode_detail：读取某一集详情。需要 episode_id、url 或 title。
- list_learning_path：读取 Agent 或 RL 学习路径。需要 topic。
- refresh_rss：用户明确要求刷新/更新 RSS 时使用。
- draft_reply：已有足够工具证据，可以生成最终回复草稿。
- fail：证据不足且无法继续。

要求：
- 只输出 JSON，不要解释。
- JSON 格式：{"action":"search_episodes","query":"RAG agent","limit":6,"reason":"一句话理由"}
- 不要输出不存在的工具。
- 如果还没有任何单集证据，通常先 search_episodes 或 list_learning_path。
- 如果用户问“从哪开始/第一轮/学习路径”，优先 list_learning_path。
- 如果用户说“听完了/我的理解是/考考我”，优先找到相关单集，再 draft_reply 做追问。
- 如果用户问“这集怎么听/介绍这集”，优先 get_episode_detail；不知道是哪集就先 search_episodes。
- 如果已有工具结果足够回答，就 draft_reply。
- 不要选择 finish；最终能否结束由程序证据门决定。
"""


AGENT_REPLY_PROMPT = """你是用户的大模型技术学习陪练，播客只是材料入口。

你只能基于本轮工具结果和会话历史回答，不要编造没有出现的单集、链接或播客内容。

核心定位：
- 不做播客二次长摘要。
- 帮用户选该听哪几集。
- 给听前抓手。
- 听完后追问和纠偏。
- 把材料迁移到用户的飞书机器人、Agent、RAG、RL、后训练等项目判断。

回答要求：
- 中文，语气自然，直接。
- 先给结论，再给学习动作。
- 飞书手机阅读友好，短段落，不用表格。
- 如果推荐收听，给 1-5 集，每集必须带标题和链接。
- 每次至少包含一个“听的时候抓什么”或“听完后回答什么”的问题。
- 如果用户在复盘，优先追问，不要改写成完整标准答案。
- 如果用户在做项目，优先输出 MVP 判断和下一步实验。
- 明确证据边界：当前只基于 RSS、路线标注和简介，不读取音频全文。
"""


def _strip_json_fence(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


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
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _post_chat_completion(
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int = 45,
) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed: HTTP {exc.code} {body[:500]}") from exc


def generate_podcast_reply(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    context: str,
    stats: str,
    mode: str = "general",
) -> str:
    if not api_key:
        raise RuntimeError("missing LLM API key")

    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"播客索引状态：{stats}\n\n"
                    f"交互模式：{mode}\n\n"
                    f"用户问题：{user_message}\n\n"
                    f"检索上下文：\n{context}\n\n"
                    "请基于这些上下文回答。不要做二次摘要，要给学习动作、追问或项目映射。"
                ),
            },
        ],
    }

    data = _post_chat_completion(api_key, base_url, payload, timeout=45)

    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("LLM returned empty response")
    return text


def plan_next_podcast_action(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    conversation_history: str,
    state_summary: str,
    tool_history: str,
) -> dict[str, Any]:
    fallback = {
        "action": "fail",
        "query": "",
        "limit": 6,
        "reason": "LLM planner unavailable",
    }
    if not api_key:
        return fallback

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": NEXT_ACTION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"会话历史：\n{conversation_history.strip()[-3000:]}\n\n"
                    f"当前状态：\n{state_summary.strip()}\n\n"
                    f"已有工具结果：\n{tool_history.strip()[-5000:]}"
                ),
            },
        ],
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=45)
    text = _strip_json_fence(_extract_response_text(data))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {**fallback, "reason": "planner returned non-json", "raw_text": text}
    if not isinstance(parsed, dict):
        return {**fallback, "reason": "planner returned non-dict", "raw_text": text}

    allowed = {
        "search_episodes",
        "get_episode_detail",
        "list_learning_path",
        "refresh_rss",
        "draft_reply",
        "fail",
    }
    action = parsed.get("action")
    if action not in allowed:
        action = "fail"
    result = dict(parsed)
    result["action"] = action
    result["raw_text"] = text
    return result


def generate_agent_podcast_reply(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    conversation_history: str,
    tool_history: str,
    stats: str,
) -> str:
    if not api_key:
        raise RuntimeError("missing LLM API key")

    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": AGENT_REPLY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"播客索引状态：{stats}\n\n"
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"会话历史：\n{conversation_history.strip()[-4000:]}\n\n"
                    f"本轮工具证据：\n{tool_history.strip()[-9000:]}\n\n"
                    "请基于工具证据回答。不要编造不存在的单集、链接或播客内容。"
                ),
            },
        ],
    }
    data = _post_chat_completion(api_key, base_url, payload, timeout=60)
    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("LLM returned empty response")
    return text
