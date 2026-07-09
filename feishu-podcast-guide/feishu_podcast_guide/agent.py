from __future__ import annotations

import re
import threading
from datetime import date
from typing import Any

from .config import Config
from .daily_reco import DEFAULT_THEME, format_switch_prompt
from .llm import generate_agent_podcast_reply, generate_podcast_reply, plan_next_podcast_action
from .podcast_index import Episode, PodcastIndex, format_context, learning_task_for_episode
from .rss import ensure_rss_fresh
from .state import (
    append_conversation_turn,
    conversation_history,
    keep_daily_theme,
    load_daily_reco,
    remember_learning_record,
    save_daily_reco,
    set_daily_theme,
)
from .tools import PodcastToolRegistry, ToolContext, ToolResult
from .trace import PodcastTrace


HELP_TEXT = """我是你的大模型技术学习陪练，播客只是材料入口。

我不主打“再总结一遍播客”，而是帮你做四件事：
1. 从 900 多集里找到该听哪几集。
2. 告诉你每集听的时候抓什么问题。
3. 你听完后，用追问检查你是不是真的掌握。
4. 把收获映射到飞书机器人、Agent、RL 等项目里。

你可以这样问：
Agent 从哪几集开始听？
推荐几集适合做飞书 Agent 项目的
强化学习和 GRPO 相关的播客有哪些？
RAG / Deep Research 相关内容怎么听？
单一智能体的力量 这集应该怎么听？
我听完 RAG-Gym 了，我的理解是……

我当前主要基于已整理的 Agent/RL 收听清单回答；如果问题太细，我会说清楚上下文边界。
"""


class PodcastGuideAgent:
    def __init__(self, config: Config, tool_registry: PodcastToolRegistry | None = None) -> None:
        self.config = config
        self.tool_registry = tool_registry or PodcastToolRegistry()
        self._index_lock = threading.RLock()
        self._refresh_index_if_needed()
        self.index = PodcastIndex.load(config.agent_path, config.rl_path, config.rss_path)

    def reply(self, text: str, chat_id: str = "local") -> str:
        self._refresh_index_if_needed()
        message = text.strip()
        if not message:
            return HELP_TEXT

        if message.lower() in {"help", "/help", "帮助"}:
            return HELP_TEXT + "\n\n" + self.index.stats()

        if message in {"状态", "索引", "数据源"}:
            return self.index.stats()

        daily = load_daily_reco(self.config.state_path)
        if daily.get("pending_theme_switch"):
            handled = self._handle_theme_switch_reply(message, daily)
            if handled is not None:
                return handled
        if "换主题" in message or "换个主题" in message:
            return self._trigger_theme_switch(daily)

        if self.config.llm_enabled:
            trace = PodcastTrace(self.config.state_path.parent, chat_id or "local", message)
            try:
                return self._run_agent_loop(message, chat_id=chat_id or "local", trace=trace)
            except Exception as exc:
                trace.event("agent_loop_error", error=str(exc))
                reply = self._legacy_reply(message, warning=str(exc), allow_llm=False)
                trace.event("legacy_fallback", allow_llm=False, chars=len(reply))
                append_conversation_turn(self.config.state_path, chat_id or "local", "user", message)
                append_conversation_turn(self.config.state_path, chat_id or "local", "assistant", reply)
                return reply

        return self._legacy_reply(message)

    def _legacy_reply(self, message: str, warning: str = "", allow_llm: bool = True) -> str:
        if self._asks_for_reflection(message):
            query = self._reflection_focus_query(message) or message
            reply = self._reply_with_optional_llm(
                message,
                self.index.search(query, limit=6),
                "听后复盘",
                allow_llm=allow_llm,
            )
            return self._with_warning(reply, warning)

        if self._asks_for_project_mapping(message):
            query = f"{message} 飞书 Agent 工具 工作流 RAG 记忆 安全 项目 落地"
            reply = self._project_mapping_reply(message, [result.episode for result in self.index.search(query, limit=6)])
            return self._with_warning(reply, warning)

        if self._asks_for_first_round(message):
            return self._with_warning(self._first_round_reply(message), warning)

        results = self.index.search(message, limit=8)
        if not results:
            reply = (
                "我在当前播客清单里没检索到特别相关的条目。\n\n"
                "你可以换成更具体的关键词，比如：Agent、RAG、Deep Research、强化学习、DPO、GRPO、reward、记忆、多智能体。"
            )
            return self._with_warning(reply, warning)

        reply = self._reply_with_optional_llm(message, results, "收听路线", allow_llm=allow_llm)
        return self._with_warning(reply, warning)

    def _with_warning(self, reply: str, warning: str = "") -> str:
        if not warning:
            return reply
        return f"智能 agent 流程暂时失败，我先退回本地检索回答：{warning}\n\n{reply}"

    def _theme_candidates(self, daily: dict[str, Any]) -> list[str]:
        pushed_ids = {item for item in (daily.get("pushed_episode_ids") or []) if isinstance(item, str)}
        return self.index.candidate_themes(
            recent_window=self.config.daily_recent_window,
            exclude_theme=daily.get("current_theme") or "",
            pushed_ids=pushed_ids,
        )

    def _trigger_theme_switch(self, daily: dict[str, Any]) -> str:
        candidates = self._theme_candidates(daily)
        daily["pending_theme_switch"] = True
        daily["candidate_themes"] = candidates
        daily["prompts_since_last_reply"] = 0
        save_daily_reco(self.config.state_path, daily)
        theme = daily.get("current_theme") or DEFAULT_THEME
        return format_switch_prompt(theme, int(daily.get("pushed_count", 0)), candidates)

    def _handle_theme_switch_reply(self, message: str, daily: dict[str, Any]) -> str | None:
        msg = message.strip()
        candidates = [item for item in (daily.get("candidate_themes") or []) if isinstance(item, str)]
        today = date.today().isoformat()

        if msg in {"继续", "保持", "留在当前主题", "不换"}:
            keep_daily_theme(self.config.state_path)
            return f"好，继续「{daily.get('current_theme') or DEFAULT_THEME}」这个主题，我明天照常推。"

        if msg.isdigit():
            index = int(msg) - 1
            if 0 <= index < len(candidates):
                theme = candidates[index]
                set_daily_theme(self.config.state_path, theme, today)
                return f"好，从明天起聚焦「{theme}」。"
            return "序号超出范围。当前候选：\n" + self._format_candidates(candidates)

        theme = self._extract_free_theme(msg)
        if theme:
            results = self.index.search(theme, limit=8)
            if len(results) >= 3:
                set_daily_theme(self.config.state_path, theme, today)
                return f"好，从明天起聚焦「{theme}」。"
            return (
                f"「{theme}」在当前 RSS 里够料的集数偏少，换个更宽的方向试试？\n"
                + self._format_candidates(candidates)
            )
        return None

    def _extract_free_theme(self, message: str) -> str:
        msg = message.strip()
        for prefix in ("换成", "聚焦", "换主题", "换个主题", "改成", "换到"):
            if msg.startswith(prefix):
                rest = msg[len(prefix):].strip("：: 　")
                return rest[:40] if rest else ""
        if any(marker in msg for marker in ("?", "？", "怎么", "哪", "什么", "为什么", "介绍")):
            return ""
        if 2 <= len(msg) <= 16:
            return msg
        return ""

    def _format_candidates(self, candidates: list[str]) -> str:
        if not candidates:
            return "（暂时没有够料的候选，可以直接说你想聚焦的主题。）"
        return "\n".join(f"{index}) {candidate}" for index, candidate in enumerate(candidates, start=1))

    def _run_agent_loop(self, message: str, chat_id: str, trace: PodcastTrace, max_turns: int = 8) -> str:
        history_items = conversation_history(self.config.state_path, chat_id)
        history_text = self._format_conversation_history(history_items)
        tool_context = ToolContext(
            config=self.config,
            get_index=lambda: self.index,
            refresh_index=self._reload_index,
        )
        tool_history: list[str] = []
        allowed_episodes: dict[str, dict[str, str]] = {}
        allowed_papers: dict[str, dict[str, str]] = {}
        search_rounds = 0
        detail_rounds = 0
        refresh_rounds = 0
        paper_search_rounds = 0
        paper_fetch_rounds = 0
        draft_rounds = 0

        for turn in range(1, max_turns + 1):
            trace.event(
                "agent_loop_turn",
                turn=turn,
                evidence_count=len(allowed_episodes),
                paper_evidence_count=len(allowed_papers),
                search_rounds=search_rounds,
                detail_rounds=detail_rounds,
                refresh_rounds=refresh_rounds,
                paper_search_rounds=paper_search_rounds,
                paper_fetch_rounds=paper_fetch_rounds,
                draft_rounds=draft_rounds,
            )
            state_summary = self._agent_state_summary(
                turn=turn,
                allowed_episodes=allowed_episodes,
                allowed_papers=allowed_papers,
                search_rounds=search_rounds,
                detail_rounds=detail_rounds,
                refresh_rounds=refresh_rounds,
                paper_search_rounds=paper_search_rounds,
                paper_fetch_rounds=paper_fetch_rounds,
                draft_rounds=draft_rounds,
            )
            planned = plan_next_podcast_action(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                history_text,
                state_summary,
                "\n\n".join(tool_history),
                trace=trace,
            )
            action_plan = self._coerce_action(
                planned,
                message,
                allowed_episodes,
                allowed_papers,
                search_rounds,
                detail_rounds,
                refresh_rounds,
                paper_search_rounds,
                paper_fetch_rounds,
                draft_rounds,
            )
            action = str(action_plan.get("action") or "")
            trace.event(
                "agent_next_action",
                action=action,
                reason=action_plan.get("reason"),
                raw_text=str(action_plan.get("raw_text") or ""),
                plan=action_plan,
            )
            tool_history.append(
                f"agent_next_action: action={action}; reason={action_plan.get('reason')}; raw={action_plan.get('raw_text', '')[:500]}"
            )

            if action == "search_episodes":
                search_rounds += 1
                query = str(action_plan.get("query") or message)
                limit = self._safe_int(action_plan.get("limit"), fallback=6, minimum=1, maximum=10)
                result = self.tool_registry.call("search_episodes", tool_context, query=query, limit=limit)
                self._merge_episode_refs(allowed_episodes, result)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={"query": query, "limit": limit},
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text())
                continue

            if action == "get_episode_detail":
                detail_rounds += 1
                result = self.tool_registry.call(
                    "get_episode_detail",
                    tool_context,
                    episode_id=str(action_plan.get("episode_id") or ""),
                    url=str(action_plan.get("url") or ""),
                    title=str(action_plan.get("title") or action_plan.get("query") or ""),
                )
                self._merge_episode_refs(allowed_episodes, result)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={
                        "episode_id": str(action_plan.get("episode_id") or ""),
                        "url": str(action_plan.get("url") or ""),
                        "title": str(action_plan.get("title") or action_plan.get("query") or ""),
                    },
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text())
                continue

            if action == "list_learning_path":
                topic = str(action_plan.get("topic") or self._infer_topic(message))
                limit = self._safe_int(action_plan.get("limit"), fallback=8, minimum=1, maximum=12)
                result = self.tool_registry.call("list_learning_path", tool_context, topic=topic, limit=limit)
                self._merge_episode_refs(allowed_episodes, result)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={"topic": topic, "limit": limit},
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text())
                continue

            if action == "refresh_rss":
                refresh_rounds += 1
                result = self.tool_registry.call("refresh_rss", tool_context)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={},
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text())
                continue

            if action == "search_papers":
                paper_search_rounds += 1
                query = str(action_plan.get("query") or self._paper_query(message))
                limit = self._safe_int(action_plan.get("limit"), fallback=5, minimum=1, maximum=8)
                result = self.tool_registry.call("search_papers", tool_context, query=query, limit=limit)
                self._merge_paper_refs(allowed_papers, result)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={"query": query, "limit": limit},
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text(max_chars=3500))
                continue

            if action == "fetch_paper":
                paper_fetch_rounds += 1
                result = self.tool_registry.call(
                    "fetch_paper",
                    tool_context,
                    identifier=str(action_plan.get("identifier") or ""),
                    paper_id=str(action_plan.get("paper_id") or action_plan.get("arxiv_id") or ""),
                    url=str(action_plan.get("url") or ""),
                    title=str(action_plan.get("title") or ""),
                    query=str(action_plan.get("query") or ""),
                )
                self._merge_paper_refs(allowed_papers, result)
                trace.event(
                    "tool_result",
                    tool=result.tool,
                    ok=result.ok,
                    arguments={
                        "identifier": str(action_plan.get("identifier") or ""),
                        "paper_id": str(action_plan.get("paper_id") or action_plan.get("arxiv_id") or ""),
                        "url": str(action_plan.get("url") or ""),
                        "title": str(action_plan.get("title") or ""),
                        "query": str(action_plan.get("query") or ""),
                    },
                    metadata=result.metadata,
                    content=result.content,
                    episodes=result.episodes,
                    papers=result.papers,
                    episode_count=len(result.episodes),
                    paper_count=len(result.papers),
                    error=result.error,
                )
                tool_history.append(result.as_history_text(max_chars=6500))
                continue

            if action == "draft_reply":
                draft_rounds += 1
                reply = generate_agent_podcast_reply(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    message,
                    history_text,
                    "\n\n".join(tool_history),
                    self.index.stats(),
                    trace=trace,
                )
                gate = self._check_reply_evidence(reply, allowed_episodes, allowed_papers)
                trace.event("evidence_gate", ok=gate["ok"], reason=gate["reason"], extra_queries=gate["extra_queries"], reply_chars=len(reply))
                if gate["ok"]:
                    self._remember_interaction(chat_id, message, reply, allowed_episodes)
                    trace.event("reply_complete", chars=len(reply), flow="agent_loop")
                    return reply

                tool_history.append(
                    f"evidence_gate_failed: reason={gate['reason']}; extra_queries={gate['extra_queries']}"
                )
                if not gate["extra_queries"] and draft_rounds < 2:
                    continue

                if not gate["extra_queries"] or search_rounds >= 3:
                    return (
                        "这次播客导览没有通过证据校验，我先不硬推具体单集。\n"
                        f"原因：{gate['reason']}\n"
                        "你可以换一个更具体的主题，比如“RAG-Gym 怎么听”或“Agent 记忆从哪几集开始”。"
                    )
                for query in gate["extra_queries"][:2]:
                    if self._asks_for_paper_detail(message) or self._paper_identifier_from_message(query):
                        paper_search_rounds += 1
                        result = self.tool_registry.call("search_papers", tool_context, query=query, limit=4)
                        self._merge_paper_refs(allowed_papers, result)
                    else:
                        search_rounds += 1
                        result = self.tool_registry.call("search_episodes", tool_context, query=query, limit=4)
                        self._merge_episode_refs(allowed_episodes, result)
                    trace.event(
                        "tool_result",
                        tool=result.tool,
                        ok=result.ok,
                        arguments={"query": query, "limit": 4},
                        metadata=result.metadata,
                        content=result.content,
                        episodes=result.episodes,
                        papers=result.papers,
                        episode_count=len(result.episodes),
                        paper_count=len(result.papers),
                        error=result.error,
                    )
                    tool_history.append(result.as_history_text())
                continue

            if action == "fail":
                reason = str(action_plan.get("reason") or "证据不足")
                trace.event("agent_loop_failed", reason=reason)
                return f"这次我没有找到足够可靠的播客证据来回答。\n原因：{reason}"

        trace.event("agent_loop_max_turns", max_turns=max_turns)
        return "这次播客导览没有在轮次上限内完成。可以把问题说得更具体一点再试。"

    def _coerce_action(
        self,
        plan: dict[str, Any],
        message: str,
        allowed_episodes: dict[str, dict[str, str]],
        allowed_papers: dict[str, dict[str, str]],
        search_rounds: int,
        detail_rounds: int,
        refresh_rounds: int,
        paper_search_rounds: int,
        paper_fetch_rounds: int,
        draft_rounds: int,
    ) -> dict[str, Any]:
        action = str(plan.get("action") or "")
        allowed = {
            "search_episodes",
            "get_episode_detail",
            "list_learning_path",
            "refresh_rss",
            "search_papers",
            "fetch_paper",
            "draft_reply",
            "fail",
        }
        result = dict(plan)
        if action not in allowed:
            action = "search_episodes"

        paper_identifier = self._paper_identifier_from_message(message)
        wants_paper = self._asks_for_paper_detail(message)

        if action == "fail" and self._is_soft_planner_failure(plan):
            action = (
                "draft_reply"
                if allowed_episodes or allowed_papers
                else (
                    "fetch_paper"
                    if paper_identifier
                    else (
                        "search_papers"
                        if wants_paper
                        else ("list_learning_path" if self._asks_for_first_round(message) else "search_episodes")
                    )
                )
            )
        elif action == "draft_reply" and not allowed_episodes and not allowed_papers:
            action = "list_learning_path" if self._asks_for_first_round(message) else "search_episodes"

        if wants_paper and not allowed_papers:
            if paper_identifier and paper_fetch_rounds < 2:
                action = "fetch_paper"
                result["identifier"] = paper_identifier
            elif action in {"search_episodes", "get_episode_detail", "list_learning_path", "draft_reply"} and paper_search_rounds < 2:
                action = "search_papers"
                result["query"] = self._paper_query(message)

        action = self._apply_action_limits(
            action,
            allowed_episodes,
            allowed_papers,
            search_rounds,
            detail_rounds,
            refresh_rounds,
            paper_search_rounds,
            paper_fetch_rounds,
            draft_rounds,
        )

        if action == "search_episodes" and not str(result.get("query") or "").strip():
            result["query"] = message
        if action == "search_papers" and (
            not str(result.get("query") or "").strip()
            or self._has_cjk(str(result.get("query") or ""))
        ):
            result["query"] = self._paper_query(message)
        if action == "list_learning_path" and not str(result.get("topic") or "").strip():
            result["topic"] = self._infer_topic(message)
        if action == "get_episode_detail" and not any(
            str(result.get(key) or "").strip() for key in ("episode_id", "url", "title", "query")
        ):
            first_episode = next(iter(allowed_episodes.values()), None)
            if first_episode:
                result["episode_id"] = first_episode.get("id")
            else:
                action = "search_episodes"
                result["query"] = message
        if action == "fetch_paper" and not any(
            str(result.get(key) or "").strip()
            for key in ("identifier", "paper_id", "arxiv_id", "url", "title", "query")
        ):
            first_paper = next(iter(allowed_papers.values()), None)
            if first_paper:
                result["paper_id"] = first_paper.get("id")
            elif paper_identifier:
                result["identifier"] = paper_identifier
            else:
                action = "search_papers"
                result["query"] = self._paper_query(message)

        result["action"] = action
        return result

    def _apply_action_limits(
        self,
        action: str,
        allowed_episodes: dict[str, dict[str, str]],
        allowed_papers: dict[str, dict[str, str]],
        search_rounds: int,
        detail_rounds: int,
        refresh_rounds: int,
        paper_search_rounds: int,
        paper_fetch_rounds: int,
        draft_rounds: int,
    ) -> str:
        if action == "search_episodes" and search_rounds >= 3:
            return "draft_reply" if (allowed_episodes or allowed_papers) and draft_rounds < 2 else "fail"
        if action == "get_episode_detail" and detail_rounds >= 3:
            return "draft_reply" if allowed_episodes else "search_episodes"
        if action == "refresh_rss" and refresh_rounds >= 1:
            return "search_episodes"
        if action == "search_papers" and paper_search_rounds >= 2:
            return "draft_reply" if (allowed_episodes or allowed_papers) and draft_rounds < 2 else "fail"
        if action == "fetch_paper" and paper_fetch_rounds >= 2:
            return "draft_reply" if allowed_papers and draft_rounds < 2 else "search_papers"
        if action == "draft_reply" and draft_rounds >= 2:
            return "fail"
        return action

    def _is_soft_planner_failure(self, plan: dict[str, Any]) -> bool:
        reason = str(plan.get("reason") or "").lower()
        return any(
            marker in reason
            for marker in (
                "planner returned non-json",
                "planner returned non-dict",
                "llm planner unavailable",
            )
        )

    def _agent_state_summary(
        self,
        turn: int,
        allowed_episodes: dict[str, dict[str, str]],
        allowed_papers: dict[str, dict[str, str]],
        search_rounds: int,
        detail_rounds: int,
        refresh_rounds: int,
        paper_search_rounds: int,
        paper_fetch_rounds: int,
        draft_rounds: int,
    ) -> str:
        episodes = self._unique_episode_refs(allowed_episodes)
        papers = self._unique_paper_refs(allowed_papers)
        episode_lines = [
            f"- {item.get('id')} {item.get('title')} {item.get('url')}"
            for item in episodes
        ]
        paper_lines = [
            f"- {item.get('id')} {item.get('title')} {item.get('abs_url')}"
            for item in papers
        ]
        return "\n".join(
            [
                f"turn: {turn}",
                f"has_episode_evidence: {bool(episodes)}",
                f"episode_evidence_count: {len(episodes)}",
                f"has_paper_evidence: {bool(papers)}",
                f"paper_evidence_count: {len(papers)}",
                f"search_rounds: {search_rounds}",
                f"detail_rounds: {detail_rounds}",
                f"refresh_rounds: {refresh_rounds}",
                f"paper_search_rounds: {paper_search_rounds}",
                f"paper_fetch_rounds: {paper_fetch_rounds}",
                f"draft_rounds: {draft_rounds}",
                "known_episodes:",
                *episode_lines[:12],
                "known_papers:",
                *paper_lines[:8],
            ]
        )

    def _format_conversation_history(self, items: list[dict[str, str]]) -> str:
        if not items:
            return "暂无历史对话。"
        lines = []
        for item in items[-12:]:
            role = "用户" if item.get("role") == "user" else "助手"
            lines.append(f"{role}：{item.get('content', '')}")
        return "\n".join(lines)

    def _merge_episode_refs(
        self,
        allowed_episodes: dict[str, dict[str, str]],
        result: ToolResult,
    ) -> None:
        for episode in result.episodes:
            episode_id = episode.get("id")
            url = episode.get("url")
            key = episode_id or url
            if key:
                allowed_episodes[key] = episode

    def _merge_paper_refs(
        self,
        allowed_papers: dict[str, dict[str, str]],
        result: ToolResult,
    ) -> None:
        for paper in result.papers:
            paper_id = paper.get("id")
            url = paper.get("abs_url") or paper.get("pdf_url")
            key = paper_id or url
            if key:
                allowed_papers[key] = paper

    def _check_reply_evidence(
        self,
        reply: str,
        allowed_episodes: dict[str, dict[str, str]],
        allowed_papers: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        if not reply.strip():
            return {"ok": False, "reason": "回复为空", "extra_queries": []}

        paper_refs = self._unique_paper_refs(allowed_papers)
        allowed_urls = {
            self._clean_url(str(item.get("url") or ""))
            for item in self._unique_episode_refs(allowed_episodes)
            if item.get("url")
        }
        allowed_urls.update(
            self._clean_url(str(item.get(key) or ""))
            for item in paper_refs
            for key in ("abs_url", "pdf_url")
            if item.get(key)
        )
        allowed_titles = [
            self._normalize_title(str(item.get("title") or ""))
            for item in self._unique_episode_refs(allowed_episodes)
            if item.get("title")
        ]
        allowed_titles.extend(
            self._normalize_title(str(item.get("title") or ""))
            for item in paper_refs
            if item.get("title")
        )

        urls = [self._clean_url(url) for url in re.findall(r"https?://[^\s)）】>]+", reply)]
        unknown_urls = [url for url in urls if url and url not in allowed_urls]

        bracket_titles = re.findall(r"《([^》]{2,120})》", reply)
        unknown_titles = [
            title
            for title in bracket_titles
            if not self._title_is_allowed(title, allowed_titles)
        ]

        wants_episode_recommendation = any(
            keyword in reply for keyword in ("推荐", "先听", "这几集", "这集是", "论文", "arXiv", "链接")
        )
        has_allowed_url = any(url in allowed_urls for url in urls)
        if wants_episode_recommendation and (allowed_episodes or allowed_papers) and not has_allowed_url:
            return {
                "ok": False,
                "reason": "回复像是在推荐材料，但没有附带本轮工具验证过的链接。",
                "extra_queries": [],
            }

        if unknown_urls or unknown_titles:
            extra_queries = unknown_titles + unknown_urls
            return {
                "ok": False,
                "reason": "回复引用了本轮工具结果中不存在的单集或链接。",
                "extra_queries": extra_queries[:4],
            }

        return {"ok": True, "reason": "所有材料引用均来自本轮工具结果。", "extra_queries": []}

    def _remember_interaction(
        self,
        chat_id: str,
        message: str,
        reply: str,
        allowed_episodes: dict[str, dict[str, str]],
    ) -> None:
        append_conversation_turn(self.config.state_path, chat_id, "user", message)
        append_conversation_turn(self.config.state_path, chat_id, "assistant", reply)
        episode_ids = []
        for item in self._unique_episode_refs(allowed_episodes):
            episode_id = item.get("id")
            if episode_id and episode_id not in episode_ids:
                episode_ids.append(episode_id)
        if self._asks_for_reflection(message):
            remember_learning_record(self.config.state_path, chat_id, message, reply, episode_ids)

    def _reload_index(self) -> PodcastIndex:
        with self._index_lock:
            self.index = PodcastIndex.load(self.config.agent_path, self.config.rl_path, self.config.rss_path)
            return self.index

    def _infer_topic(self, message: str) -> str:
        lowered = message.lower()
        if any(token in lowered for token in ("rl", "强化", "grpo", "dpo", "sft", "reward", "后训练")):
            return "RL"
        return "Agent"

    def _asks_for_paper_detail(self, message: str) -> bool:
        lowered = message.lower()
        keywords = (
            "论文",
            "paper",
            "arxiv",
            "技术细节",
            "方法",
            "实验",
            "ablation",
            "消融",
            "公式",
            "读原文",
            "读一下",
            "细节",
        )
        return any(keyword in lowered for keyword in keywords)

    def _paper_identifier_from_message(self, message: str) -> str:
        patterns = [
            r"arxiv\.org/(?:abs|pdf)/([A-Za-z0-9.\-_/]+)",
            r"\barXiv:([A-Za-z0-9.\-_/]+)",
            r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                identifier = match.group(1).strip()
                identifier = re.sub(r"\.pdf$", "", identifier, flags=re.IGNORECASE)
                return identifier.strip("/")
        return ""

    def _paper_query(self, message: str) -> str:
        lowered = message.lower()
        if any(token in lowered for token in ("rag", "deep research", "检索", "知识库", "搜索")):
            return "retrieval augmented generation agents deep research"
        if any(token in lowered for token in ("grpo", "dpo", "sft", "rl", "强化", "reward", "后训练")):
            return "reinforcement learning language model agents tool use"
        if any(token in lowered for token in ("评估", "安全", "验证", "evaluation", "benchmark")):
            return "LLM agents evaluation benchmark tool use reliability"
        if any(token in lowered for token in ("agent", "智能体", "工具", "工作流", "落地")):
            return "LLM agents tool use planning workflow evaluation"
        return message

    def _has_cjk(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _safe_int(self, value: Any, fallback: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = fallback
        return max(minimum, min(parsed, maximum))

    def _unique_episode_refs(self, episodes_by_key: dict[str, dict[str, str]]) -> list[dict[str, str]]:
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for item in episodes_by_key.values():
            key = item.get("id") or item.get("url") or item.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _unique_paper_refs(self, papers_by_key: dict[str, dict[str, str]]) -> list[dict[str, str]]:
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for item in papers_by_key.values():
            key = item.get("id") or item.get("abs_url") or item.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _clean_url(self, value: str) -> str:
        return value.strip().rstrip(".,，。!！?？;；)")

    def _normalize_title(self, value: str) -> str:
        return re.sub(r"[\s《》「」“”\"'：:，,。.!！?？\\-—_()（）【】\\[\\]]+", "", value.lower())

    def _title_is_allowed(self, title: str, allowed_titles: list[str]) -> bool:
        normalized = self._normalize_title(title)
        if not normalized:
            return True
        if normalized in allowed_titles:
            return True
        if len(normalized) < 8:
            return False
        for known in allowed_titles:
            if not known or len(known) < 8:
                continue
            if normalized in known and len(normalized) / len(known) >= 0.65:
                return True
            if known in normalized and len(known) / len(normalized) >= 0.65:
                return True
        return False

    def _reply_with_optional_llm(self, message: str, results, mode: str, allow_llm: bool = True) -> str:
        episodes = [result.episode for result in results]
        context = format_context(results)
        if self.config.llm_enabled and allow_llm:
            try:
                return generate_podcast_reply(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    message,
                    context,
                    self.index.stats(),
                    mode=mode,
                )
            except Exception as exc:
                if mode == "听后复盘":
                    return self._reflection_reply(message, episodes, warning=str(exc))
                return self._fallback_reply(message, episodes, warning=str(exc))

        if mode == "听后复盘":
            return self._reflection_reply(message, episodes)
        return self._fallback_reply(message, episodes)

    def _asks_for_first_round(self, message: str) -> bool:
        keywords = ("从哪开始", "开始听", "第一轮", "入门", "收听顺序", "学习路径", "清单")
        return any(keyword in message for keyword in keywords)

    def _asks_for_reflection(self, message: str) -> bool:
        keywords = ("听完", "听了", "复盘", "我的理解", "我理解", "检查一下", "考考我", "掌握")
        return any(keyword in message for keyword in keywords)

    def _reflection_focus_query(self, message: str) -> str:
        match = re.search(r"(?:听完|听了)\s*[《「“\"]?(.+?)[》」”\"]?\s*(?:了|，|,|。|我的理解|我理解|$)", message)
        if not match:
            return ""
        query = match.group(1).strip()
        return query if 2 <= len(query) <= 60 else ""

    def _asks_for_project_mapping(self, message: str) -> bool:
        keywords = ("飞书", "机器人", "项目", "落地", "落一版", "做一版", "mvp", "第一版", "怎么做", "实际中")
        return any(keyword in message.lower() for keyword in keywords)

    def _asks_about_one_episode(self, message: str) -> bool:
        keywords = ("这集", "这一集", "讲什么", "介绍一下", "大概讲", "内容", "怎么听")
        return any(keyword in message for keyword in keywords)

    def _first_round_reply(self, message: str) -> str:
        episodes = self.index.first_round(message, limit=10)
        topic = "强化学习" if any(token in message.lower() for token in ("rl", "强化", "grpo", "dpo")) else "Agent"
        lines = [
            f"第一版我建议你先按这个 {topic} 顺序听。",
            "",
            "别把目标设成“听懂全部内容”。第一轮只抓三件事：它解决什么任务、用了什么工具/奖励/评估、能不能迁移到你的项目。",
            "",
        ]
        lines.extend(self._episode_lines(episodes, with_learning_task=True))
        lines.extend(
            [
                "",
                "听完任意一集后，直接发我：",
                "我听完《标题》了，我的理解是……",
                "",
                "我会继续追问你三个问题，帮你把它变成自己的理解。",
            ]
        )
        return "\n".join(lines)

    def _refresh_index_if_needed(self) -> None:
        try:
            refreshed_count = ensure_rss_fresh(self.config)
        except Exception:
            return
        if refreshed_count is None or not hasattr(self, "index"):
            return
        with self._index_lock:
            self.index = PodcastIndex.load(self.config.agent_path, self.config.rl_path, self.config.rss_path)

    def _fallback_reply(self, message: str, episodes: list[Episode], warning: str = "") -> str:
        if self._asks_about_one_episode(message) and episodes:
            return self._episode_detail_reply(episodes[0], warning=warning)

        lines = []
        if warning:
            lines.append(f"模型生成暂时不可用，我先用本地检索结果回答：{warning}")
            lines.append("")

        lines.append("我在播客清单里找到了这些最相关的内容。重点不是让它们替你学习，而是用它们做输入材料：")
        lines.append("")
        lines.extend(self._episode_lines(episodes[:5], with_learning_task=True))
        lines.append("")
        lines.append("建议听法：先听前 2 集建立直觉。每集听完只写 3 句话：它解决什么问题、关键机制是什么、能怎么迁移到你的项目。")
        return "\n".join(lines)

    def _episode_detail_reply(self, episode: Episode, warning: str = "") -> str:
        lines = []
        if warning:
            lines.append(f"模型生成暂时不可用，我先用清单信息回答：{warning}")
            lines.append("")

        lines.extend(
            [
                f"这集是：{episode.title}",
                episode.url,
                "",
                f"它在清单里的位置：{episode.stage or episode.source}",
            ]
        )

        if episode.note:
            lines.extend(["", f"清单给它的定位：{episode.note}"])
        elif episode.summary:
            lines.extend(["", f"RSS 简介：{episode.summary[:240]}"])
        else:
            lines.extend(["", "当前清单没有更细摘要，只能确定它和这个阶段主题相关。"])

        lines.extend(
            [
                "",
                "这集不需要我替你总结，建议你听的时候抓三个问题：",
                "1. 这集把 Agent / 大模型能力定义成什么问题？",
                "2. 它提到的关键机制是什么，比如工具、搜索、记忆、评估或奖励？",
                "3. 如果迁移到你的飞书机器人，第一版最小闭环是什么？",
                "",
                "听完后你发我一句“我的理解是……”，我会帮你检查哪里还虚、哪里可以变成项目设计。",
            ]
        )
        return "\n".join(lines)

    def _reflection_reply(self, message: str, episodes: list[Episode], warning: str = "") -> str:
        lines = []
        if warning:
            lines.append(f"模型生成暂时不可用，我先用固定复盘框架陪你过一遍：{warning}")
            lines.append("")

        lines.extend(
            [
                "这条消息适合做听后复盘，不适合再要一版摘要。",
                "",
                "你先用这 4 个问题检查自己：",
                "1. 这集讨论的核心任务是什么？用一句话说清。",
                "2. 里面的关键机制是什么？比如搜索、工具、记忆、reward、verifier、评估。",
                "3. 它最容易被误解或过度推广的地方是什么？",
                "4. 如果放到你的飞书机器人里，第一版能落地成哪个小功能？",
            ]
        )

        if episodes:
            lines.extend(["", "如果你想回到原材料，可以对照这几集：", ""])
            lines.extend(self._episode_lines(episodes[:3], with_learning_task=False))

        lines.extend(
            [
                "",
                "下一条你可以按这个模板回我：",
                "任务：……",
                "机制：……",
                "边界：……",
                "迁移到我的项目：……",
            ]
        )
        return "\n".join(lines)

    def _project_mapping_reply(self, message: str, episodes: list[Episode]) -> str:
        if not episodes:
            episodes = self.index.first_round("Agent", limit=5)

        lines = [
            "这个方向可以落一版，而且它的价值不是“总结播客”，而是把播客变成项目决策输入。",
            "",
            "我建议先听这几集，每集只服务一个工程判断：",
            "",
        ]
        lines.extend(self._episode_lines(episodes[:5], with_learning_task=True))
        lines.extend(
            [
                "",
                "第一版飞书机器人可以这样定义：",
                "1. 你输入学习目标，比如“我想了解 Agent 记忆”。",
                "2. 它推荐 3-5 集，并告诉你每集听时抓什么。",
                "3. 你听完发一句自己的理解。",
                "4. 它追问 3 个问题，检查任务、机制、边界和项目迁移。",
                "5. 最后生成一条“可沉淀笔记”或“项目 TODO”。",
                "",
                "第一版先别做：自动长摘要、全量音频转写、多 Agent、复杂记忆。",
                "先把“推荐 -> 听后复盘 -> 项目映射”这条闭环跑顺。",
            ]
        )
        return "\n".join(lines)

    def _episode_lines(self, episodes: list[Episode], with_learning_task: bool = False) -> list[str]:
        lines: list[str] = []
        for index, episode in enumerate(episodes, start=1):
            lines.append(f"{index}. {episode.title}")
            lines.append(f"{episode.url}")
            if episode.note:
                lines.append(f"为什么听：{episode.note}")
            elif episode.summary:
                lines.append(f"简介：{episode.summary[:180]}")
            if episode.stage:
                lines.append(f"位置：{episode.stage}")
            if with_learning_task:
                lines.append(f"听的时候抓：{self._learning_task_for_episode(episode)}")
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()
        return lines

    def _learning_task_for_episode(self, episode: Episode) -> str:
        return learning_task_for_episode(episode)
