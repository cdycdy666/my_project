from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .trace import InteractionTrace


READING_COACH_PROMPT = """你是用户的处境驱动读书智能体。

你的职责不是泛泛推荐书，而是把用户当前处境、近期问题、判断卡点和可获得的阅读线索连接起来，给出具体、轻量、当下可执行的阅读动作。

要求：
- 中文。
- 语气自然、克制、具体，不要鸡汤。
- 只基于输入上下文判断用户处境，不要编造用户经历、阅读数据或书架状态。
- 微信读书书架只是线索，不是推荐范围限制，也不是推荐优先级；最重要的是推荐是否贴合用户当前处境。
- 默认不要推荐“读完整本书”；书只是材料来源，不是任务本身。
- 每次优先推荐一个低门槛阅读动作：一章、一节、一段、一个概念、一个关键词搜索、一个 10-20 分钟的问题式阅读任务。
- 默认不要因为某本书已经在书架里，就优先推荐它。
- 如果输出多个阅读动作，至少一个必须是“书架外”的概念、文章、章节、关键词或主题搜索。
- 如果只输出一个阅读动作，优先选择最贴合处境的材料；它可以是书架外。
- 只有明确出现在“书架完整电子书清单”里的书，才能标注“书架内”。
- “已验证材料上下文”中的搜索结果和目录只能证明书籍可检索、目录可验证，不能证明它在书架内。
- 如果某本书没有出现在书架完整清单里，即使微信读书搜索到了，也必须标注“书架外”或“微信读书可检索，未在书架内”。
- 如果书架里确实有最合适的材料，可以推荐并标注“书架内”，但必须说明为什么它比书架外线索更适合当下。
- 如果书架外有更合适的书、文章、章节、概念或阅读主题，可以直接推荐并标注“书架外”；不要假装它已经在用户书架里。
- 书架外推荐不能只给书名。必须尽量精确到章节、小节、概念、关键词或可搜索短语，例如“《幸福的婚姻》第 5 章：关注对方的情感需求”“搜索 John Gottman bids for connection”“只看《打造第二大脑》里 Organize for action / PARA 的介绍”。
- 如果无法可靠确定章节号，不要编造章节号；改为给出可搜索的章节名、概念名或关键词，并说明“先搜这个词，看 10-15 分钟的介绍即可”。
- 涉及具体书名、章节、篇章位置时，必须优先依据“已验证材料上下文”。如果已验证材料上下文没有对应目录，不要编造章节号或章节名。
- 如果某个推荐来自模型常识但未被目录验证，必须降级成“关键词/概念搜索”，不要说“第几章”。
- “已验证材料上下文”不是全文。目录只能证明位置存在；热门划线、公开点评、个人划线/想法只能作为片段证据；公开点评是他人观点，不等于原文结论。
- 推荐具体章节时，必须区分“目录已验证”和“内容片段佐证”。如果只有目录，没有热门划线/点评/个人笔记支撑，只能说“从目录看这个位置可能相关，正文未验证”。
- “目录已验证”不能单独作为内容结论依据。只要没有看到同一本书下方出现热门划线、公开点评、你的划线或你的想法，就必须在依据里写“正文未验证”。
- 推荐具体观点或主题时，必须给出证据等级：`目录已验证`、`热门划线佐证`、`公开点评佐证`、`你的划线/想法佐证`、`正文未验证，仅建议关键词搜索` 之一或多个。
- 如果证据不足，不要强行推荐具体章节；改成“搜索关键词/概念，先看 10-15 分钟”。
- 书架外推荐要说明为什么值得现在读，并给出一个低门槛可执行动作，例如“搜索这个关键词”“先读导言”“只看某一章的小节”“找一篇介绍文章”。
- 输出里要弱化“任务感”，强调“只需 10-20 分钟”“读一小段”“带着一个问题看”。
- 输出推荐时，至少包含一行“依据：...”，用自然语言写清楚证据等级，不要展示接口细节或 bookId。
- 飞书消息要适合手机阅读：短句、短段落、少铺陈。
- 不要使用 Markdown 加粗、标题符号、表格或代码块。
- 默认总长度控制在 700 个汉字以内；除非用户明确要求详细展开。
- 推荐阅读/换一本/这本适合吗 的输出格式固定为：
  读书建议
  结论：一句话说明是否推荐、推荐它解决什么当下问题。

  读什么：书名/章节/概念/关键词，标注书架内或书架外。
  怎么读：10-20 分钟内的具体动作，只给一个最小动作。
  为什么现在：连接用户当前处境，不超过两句话。
  依据：证据等级 + 简短说明。
  读后回收：一个能沉淀到 personal-kb 的问题。
- 如果确实需要给多个动作，最多给 2 个，并用“方案 A”“方案 B”分隔；每个方案都必须有“依据：...”。
- 输出要能直接发给用户。
- 当用户问“推荐阅读/换一本/这本适合吗”时，给出明确建议。
- 当用户说“读完了：...”时，帮助提炼读后反馈，并追问一个能沉淀到个人知识库的问题。
- 你当前只负责读书对话，不负责写入 Obsidian 或 personal-kb。
- 绝对不要说“发给我”“我会帮你整理进 daily note”“我会写入 Obsidian”“我会按规则整理进当天记录”。
- 如果建议用户沉淀，必须明确说：“可以发给 Obsidian Capture 记录机器人”，或“可以手动记到 daily note”。不要把读书智能体和记录机器人混为一谈。
"""


MATERIAL_QUERY_PROMPT = """你是读书推荐的材料检索规划器。
任务：根据用户消息和个人处境，列出需要去微信读书验证的候选书名、概念名或关键词。

要求：
- 只输出 JSON，不要解释。
- JSON 格式：{"queries":["关键词1","关键词2"]}
- 最多 4 个 query。
- query 可以是书名、作者+书名、章节名、概念英文名/中文名。
- 优先选择能帮助验证书名、章节目录或关键概念的 query。
- 不要输出空泛词，比如“沟通”“知识管理”；要尽量具体。
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


def _reinforce_evidence_boundaries(text: str) -> str:
    content_evidence_labels = (
        "热门划线佐证",
        "公开点评佐证",
        "你的划线",
        "个人划线",
        "你的想法",
        "个人想法",
        "内容片段佐证",
    )
    lines: list[str] = []
    for line in text.splitlines():
        if (
            "依据：" in line
            and "目录已验证" in line
            and "正文未验证" not in line
            and not any(label in line for label in content_evidence_labels)
        ):
            stripped = line.rstrip()
            trailing = line[len(stripped) :]
            if stripped.endswith("）"):
                line = f"{stripped[:-1]}，正文未验证）{trailing}"
            else:
                line = f"{stripped}（正文未验证）{trailing}"
        lines.append(line)
    return "\n".join(lines)


def _format_for_feishu_text(text: str) -> str:
    lines: list[str] = []
    blank_seen = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            if not blank_seen and lines:
                lines.append("")
            blank_seen = True
            continue

        blank_seen = False
        stripped = re.sub(r"^\s{0,3}#{1,6}\s*", "", stripped)
        stripped = stripped.replace("**", "").replace("__", "")
        stripped = stripped.replace("`", "")
        stripped = re.sub(r"^\s*[-*]\s+", "- ", stripped)
        lines.append(stripped)

    return "\n".join(lines).strip()


def _post_chat_completion(
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
    retries: int,
    trace: InteractionTrace | None = None,
    purpose: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> dict:
    started_at = time.monotonic()
    if trace:
        messages = payload.get("messages")
        prompt_chars = 0
        if isinstance(messages, list):
            for message in messages:
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    prompt_chars += len(message["content"])
        trace.event(
            "llm_request",
            purpose=purpose,
            model=payload.get("model"),
            base_url=base_url,
            temperature=payload.get("temperature"),
            prompt_chars=prompt_chars,
            metadata=metadata or {},
        )

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
                data = json.loads(response.read().decode("utf-8"))
                if trace:
                    trace.event(
                        "llm_response",
                        purpose=purpose,
                        model=payload.get("model"),
                        elapsed_ms=int((time.monotonic() - started_at) * 1000),
                        response_keys=sorted(data.keys()) if isinstance(data, dict) else [],
                    )
                return data
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if trace:
                trace.event(
                    "llm_error",
                    purpose=purpose,
                    model=payload.get("model"),
                    elapsed_ms=int((time.monotonic() - started_at) * 1000),
                    error=f"HTTP {exc.code} {body[:800]}",
                )
            raise RuntimeError(f"LLM API failed: HTTP {exc.code} {body[:800]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2 * (attempt + 1))

    if trace:
        trace.event(
            "llm_error",
            purpose=purpose,
            model=payload.get("model"),
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
            error=str(last_error),
        )
    raise RuntimeError(f"LLM API failed after {retries + 1} attempts: {last_error}") from last_error


def generate_reading_reply(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    personal_context: str,
    weread_context: str,
    verified_materials_context: str = "",
    trace: InteractionTrace | None = None,
) -> str:
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": READING_COACH_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"个人处境上下文：\n{personal_context.strip()[-14000:]}\n\n"
                    f"微信读书上下文：\n{weread_context.strip()[-7000:]}\n\n"
                    f"已验证材料上下文，可为空：\n{verified_materials_context.strip()[-12000:]}"
                ),
            },
        ],
        "temperature": 0.5,
    }
    data = _post_chat_completion(
        api_key,
        base_url,
        payload,
        timeout=90,
        retries=1,
        trace=trace,
        purpose="reading_reply",
        metadata={
            "user_message": user_message.strip(),
            "personal_context_chars": len(personal_context),
            "weread_context_chars": len(weread_context),
            "verified_materials_context_chars": len(verified_materials_context),
        },
    )

    text = _extract_response_text(data).strip()
    if not text:
        raise RuntimeError("LLM API returned an empty reading reply")
    reply = _format_for_feishu_text(_reinforce_evidence_boundaries(text))
    if trace:
        trace.event("final_reply", chars=len(reply), text=reply)
    return reply


def generate_material_queries(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    personal_context: str,
    weread_context: str,
    trace: InteractionTrace | None = None,
) -> list[str]:
    if not api_key:
        return []

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": MATERIAL_QUERY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"个人处境上下文：\n{personal_context.strip()[-8000:]}\n\n"
                    f"微信读书上下文：\n{weread_context.strip()[-4000:]}"
                ),
            },
        ],
        "temperature": 0.2,
    }
    data = _post_chat_completion(
        api_key,
        base_url,
        payload,
        timeout=60,
        retries=1,
        trace=trace,
        purpose="material_queries",
        metadata={
            "user_message": user_message.strip(),
            "personal_context_chars": len(personal_context),
            "weread_context_chars": len(weread_context),
        },
    )

    text = _extract_response_text(data).strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    raw_queries = parsed.get("queries") if isinstance(parsed, dict) else None
    if not isinstance(raw_queries, list):
        return []

    queries: list[str] = []
    for item in raw_queries:
        if isinstance(item, str) and item.strip() and item.strip() not in queries:
            queries.append(item.strip())
        if len(queries) >= 4:
            break
    if trace:
        trace.event("material_queries", raw_text=text, queries=queries)
    return queries
