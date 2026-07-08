from __future__ import annotations

import json
import re
import socket
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
- 微信读书上下文可能明确说明“本次未读取书架”。这种情况下，不要推断用户书架里有哪些书，也不要把任何书标成“书架内”。
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
- 最终回复必须优先从“已验证材料上下文”里选择材料。最终阶段不要临时引入新的书名、作者、概念或关键词；系统会在回复后做材料校验，发现未验证材料时才补查并重写。
- 如果某个书名、作者、概念或关键词没有出现在用户消息、微信读书上下文或“已验证材料上下文”里，不要把它作为正式推荐对象。
- 如果没有候选材料打分上下文，仍然只能从“已验证材料上下文”中选择正式推荐对象；不要用模型常识临时新增更好的书名、作者、理论、概念或关键词。
- 最终回复必须服从“候选材料打分上下文”。如果打分上下文给出 primary，就优先推荐 primary；如果 should_output_count 为 1，不要输出方案 B。
- 如果打分上下文把某个候选标为 extension，只能作为一句延伸提醒，不能展开成完整方案。
- 涉及具体书名、章节、篇章位置时，必须优先依据“已验证材料上下文”。如果已验证材料上下文没有对应目录，不要编造章节号或章节名。
- 如果某个推荐来自模型常识但未被目录验证，必须降级成“关键词/概念搜索”，不要说“第几章”。
- “已验证材料上下文”不是全文。目录只能证明位置存在；热门划线、公开点评、个人划线/想法只能作为片段证据；公开点评是他人观点，不等于原文结论。
- 推荐具体章节时，必须区分“目录已验证”和“内容片段佐证”。如果只有目录，没有热门划线/点评/个人笔记支撑，只能说“从目录看这个位置可能相关，正文未验证”。
- “目录已验证”不能单独作为内容结论依据。只要没有看到同一本书下方出现热门划线、公开点评、你的划线或你的想法，就必须在依据里写“正文未验证”。
- 推荐具体观点或主题时，必须给出证据等级：`目录已验证`、`热门划线佐证`、`公开点评佐证`、`你的划线/想法佐证`、`正文未验证，仅建议关键词搜索` 之一或多个。
- 如果核心推荐概念本身没有出现在内容片段证据里，即使同一本书有热门划线，也必须在依据里写“核心概念正文未验证”。
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


EVIDENCE_AWARE_SCORING_PROMPT = """你是读书推荐的处境证据打分器。
任务：结合 personal-kb 原文片段和微信读书已验证材料，对候选阅读材料打分，并选出一个最适合当前处境的 primary。

要求：
- 只输出 JSON，不要解释。
- JSON 格式：
{
  "primary_problem": "用户此刻最需要用阅读辅助解决的具体问题",
  "primary": "最终最推荐的书名/章节/概念/关键词",
  "candidates": [
    {
      "material": "书名/章节/概念/关键词",
      "fit_score": 1-10,
      "reading_cost": "低/中/高",
      "evidence_level": "目录已验证/热门划线佐证/公开点评佐证/你的划线或想法佐证/正文未验证，仅建议关键词搜索",
      "personal_evidence": "它和 personal-kb 原文片段中的哪个处境、判断或 open loop 对应",
      "recommendation": "primary/secondary/extension/reject",
      "reason": "一句话排序理由"
    }
  ],
  "should_output_count": 1,
  "reason": "为什么最终只输出 1 个或 2 个阅读动作"
}
- 只能比较“已验证材料上下文”里出现过的候选材料，不要新增书名、作者、概念、理论、章节或关键词。
- material 字段必须复制或紧贴“已验证材料上下文”中的书名、章节名、概念名或 query。
- personal_evidence 必须来自“个人处境原文片段”或“个人处境摘要”，不要编造用户处境。
- 默认 should_output_count 为 1，优先只推荐一个 10-20 分钟的最小阅读动作。
- 只有两个候选分别解决两个非常强、非常不同、且都和用户当前消息直接相关的问题时，should_output_count 才能为 2。
- 排序优先级：当前处境贴合度 > 可执行性/阅读门槛 > 证据等级 > 是否在书架内。
- 书架内不是优先理由；书架外也不是扣分理由。
- evidence_level 必须诚实。没有全文时要写“正文未验证”；只有目录时不能说内容已验证。
- candidates 最多 4 个。
"""


FINAL_REPLY_CHECK_PROMPT = """你是读书推荐的最终回复材料校验器。
任务：检查最终回复是否引入了未被“已验证材料上下文”验证过的正式推荐对象。

要求：
- 只输出 JSON，不要解释。
- JSON 格式：{"ok":true,"extra_queries":[],"reason":"一句话原因"}
- 如果最终回复的“读什么”或核心建议里出现了新的书名、作者、理论、概念、章节、英文术语或关键词，而它没有出现在“已验证材料上下文”中，ok 必须为 false，并把需要补检索的词放入 extra_queries。
- extra_queries 最多 2 个，要能直接用于微信读书搜索。
- 如果最终回复只是在“依据”或“为什么现在”里复述个人处境，不算新材料。
- 如果最终回复建议“关键词搜索”，这个关键词本身也必须出现在“已验证材料上下文”中；否则需要补检索。
- 不要因为“依据：正文未验证”就放过未检索材料。未检索材料仍必须补检索。
- 不要输出空泛词，比如“沟通”“亲密关系”“知识管理”。
"""


NEXT_ACTION_PROMPT = """你是读书推荐 agent 的下一步动作规划器。
任务：根据用户消息、当前状态和已有工具结果，在有限动作集中选择下一步。

可选动作：
- verify_materials：需要去微信读书验证候选材料。必须给出 1-4 个具体 queries。
- read_personal_evidence：需要回读 personal-kb 的 daily note 原文片段。
- score_materials：需要比较已验证材料和用户处境。
- draft_reply：证据足够，可以生成最终建议草稿。
- fail：证据不足或无法继续。

要求：
- 只输出 JSON，不要解释。
- JSON 格式：{"action":"verify_materials","queries":["关键词1"],"reason":"一句话理由","progress":"一句给用户看的进度"}
- 不要输出空泛 query，比如“沟通”“亲密关系”“心理学”“成长”。
- verify_materials 的 query 要能验证书名、章节、概念或关键词。
- 不要选择 finish；最终能否结束由材料校验闸门决定。
- 不要要求不存在的工具。
- 如果状态显示还没有已验证材料，通常应选择 verify_materials。
- 如果已有已验证材料但没有 personal-kb 原文片段，通常应选择 read_personal_evidence。
- 如果已有已验证材料和 personal-kb 原文片段但没有材料打分，通常应选择 score_materials。
- 如果已有材料打分且尚未生成回复，通常应选择 draft_reply。
- 如果上一轮材料校验失败且提供了 extra_queries，应优先选择 verify_materials 并使用这些 extra_queries 或更具体的同义 query。
"""


def _strip_json_fence(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.startswith("json"):
            content = content[4:].strip()
    return content


def _dedupe_queries(raw_queries: Any, limit: int) -> list[str]:
    if not isinstance(raw_queries, list):
        return []

    queries: list[str] = []
    for item in raw_queries:
        if isinstance(item, str) and item.strip() and item.strip() not in queries:
            queries.append(item.strip())
        if len(queries) >= limit:
            break
    return queries


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
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
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
    material_scoring_context: str = "",
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
                    f"已验证材料上下文，可为空：\n{verified_materials_context.strip()[-12000:]}\n\n"
                    f"候选材料打分上下文，可为空：\n{material_scoring_context.strip()[-5000:]}"
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
            "material_scoring_context_chars": len(material_scoring_context),
        },
    )

    text = _extract_response_text(data).strip()
    if not text:
        raise RuntimeError("LLM API returned an empty reading reply")
    reply = _format_for_feishu_text(_reinforce_evidence_boundaries(text))
    if trace:
        trace.event("final_reply", chars=len(reply), text=reply)
    return reply


def check_final_reply_materials(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    final_reply: str,
    verified_materials_context: str,
    trace: InteractionTrace | None = None,
) -> dict[str, Any]:
    if not api_key or not final_reply.strip() or not verified_materials_context.strip():
        return {"ok": True, "extra_queries": [], "reason": "material check skipped"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": FINAL_REPLY_CHECK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"已验证材料上下文：\n{verified_materials_context.strip()[-12000:]}\n\n"
                    f"最终回复：\n{final_reply.strip()}"
                ),
            },
        ],
        "temperature": 0.1,
    }
    data = _post_chat_completion(
        api_key,
        base_url,
        payload,
        timeout=45,
        retries=1,
        trace=trace,
        purpose="final_reply_material_check",
        metadata={
            "user_message": user_message.strip(),
            "final_reply_chars": len(final_reply),
            "verified_materials_context_chars": len(verified_materials_context),
        },
    )

    text = _strip_json_fence(_extract_response_text(data))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if trace:
            trace.event("final_reply_material_check", raw_text=text, queries=[], parse_error=True)
        return {"ok": False, "extra_queries": [], "reason": "material check parse error", "parse_error": True}

    if not isinstance(parsed, dict):
        if trace:
            trace.event("final_reply_material_check", raw_text=text, ok=False, reason="non_dict_response")
        return {"ok": False, "extra_queries": [], "reason": "material check non-dict response"}

    ok = bool(parsed.get("ok"))
    queries = []
    if not ok:
        queries = _dedupe_queries(parsed.get("extra_queries"), limit=2)
        queries = [query for query in queries if query not in verified_materials_context]
    reason = parsed.get("reason") or ""

    if trace:
        trace.event(
            "final_reply_material_check",
            raw_text=text,
            ok=ok,
            queries=queries,
            reason=reason,
        )
    return {"ok": ok, "extra_queries": queries, "reason": reason}


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

    text = _strip_json_fence(_extract_response_text(data))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    queries = _dedupe_queries(parsed.get("queries") if isinstance(parsed, dict) else None, limit=4)
    if trace:
        trace.event("material_queries", raw_text=text, queries=queries)
    return queries


def plan_next_reading_action(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    state_summary: str,
    loop_history: str,
    trace: InteractionTrace | None = None,
) -> dict[str, Any]:
    fallback = {
        "action": "fail",
        "queries": [],
        "reason": "LLM planner unavailable",
        "progress": "正在继续处理...",
    }
    if not api_key:
        return fallback

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": NEXT_ACTION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"当前状态：\n{state_summary.strip()}\n\n"
                    f"已有工具结果和循环历史：\n{loop_history.strip()[-5000:]}"
                ),
            },
        ],
        "temperature": 0.1,
    }
    data = _post_chat_completion(
        api_key,
        base_url,
        payload,
        timeout=45,
        retries=1,
        trace=trace,
        purpose="agent_next_action",
        metadata={
            "user_message": user_message.strip(),
            "state_summary_chars": len(state_summary),
            "loop_history_chars": len(loop_history),
        },
    )

    text = _strip_json_fence(_extract_response_text(data))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if trace:
            trace.event("agent_next_action", raw_text=text, parse_error=True, action=fallback["action"])
        return fallback

    allowed_actions = {"verify_materials", "read_personal_evidence", "score_materials", "draft_reply", "fail"}
    action = parsed.get("action") if isinstance(parsed, dict) else None
    if action not in allowed_actions:
        action = "fail"

    queries = _dedupe_queries(parsed.get("queries") if isinstance(parsed, dict) else None, limit=4)
    result = {
        "action": action,
        "queries": queries,
        "reason": str(parsed.get("reason") or "") if isinstance(parsed, dict) else "",
        "progress": str(parsed.get("progress") or "") if isinstance(parsed, dict) else "",
        "raw_text": text,
    }
    if trace:
        trace.event(
            "agent_next_action",
            raw_text=text,
            action=result["action"],
            queries=result["queries"],
            reason=result["reason"],
            progress=result["progress"],
        )
    return result


def generate_evidence_aware_material_scoring(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    personal_context: str,
    personal_evidence_context: str,
    verified_materials_context: str,
    trace: InteractionTrace | None = None,
) -> str:
    if not api_key or not verified_materials_context.strip():
        return ""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": EVIDENCE_AWARE_SCORING_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户消息：\n{user_message.strip()}\n\n"
                    f"个人处境摘要：\n{personal_context.strip()[-4000:]}\n\n"
                    f"个人处境原文片段：\n{personal_evidence_context.strip()[-5000:]}\n\n"
                    "注意：你只能比较下面的已验证材料，不要从模型常识、书架或个人处境中新增候选。\n\n"
                    f"已验证材料上下文：\n{verified_materials_context.strip()[-10000:]}"
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
        purpose="evidence_aware_material_scoring",
        metadata={
            "user_message": user_message.strip(),
            "personal_context_chars": len(personal_context),
            "personal_evidence_context_chars": len(personal_evidence_context),
            "verified_materials_context_chars": len(verified_materials_context),
        },
    )

    text = _strip_json_fence(_extract_response_text(data))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if trace:
            trace.event("evidence_aware_material_scoring", raw_text=text, parse_error=True)
        return ""

    scoring_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    if trace:
        trace.event(
            "evidence_aware_material_scoring",
            raw_text=text,
            scoring=parsed,
            primary=parsed.get("primary") if isinstance(parsed, dict) else None,
            should_output_count=parsed.get("should_output_count") if isinstance(parsed, dict) else None,
            primary_problem=parsed.get("primary_problem") if isinstance(parsed, dict) else None,
        )
    return scoring_text
