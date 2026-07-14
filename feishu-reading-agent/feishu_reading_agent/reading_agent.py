from __future__ import annotations

from typing import Callable

from .config import Config
from .llm import (
    check_final_reply_materials,
    generate_evidence_aware_material_scoring,
    generate_general_reply,
    generate_material_queries,
    generate_reading_reply,
    plan_next_reading_action,
)
from .tools import ToolContext, ToolRegistry, create_default_tool_registry
from .trace import InteractionTrace
from .weread import fetch_shelf_context


HELP_TEXT = """我是你的读书智能体，会结合个人处境给阅读建议，必要时再读取微信读书书架。

可以这样发：
- 推荐阅读
- 换一本
- 书架
- 这本书适合我现在读吗：书名
- 读完了：你的读后感
"""

NO_SHELF_CONTEXT = "本次未读取微信读书书架。推荐范围不局限书架；除非用户明确要求“从书架里推荐”，否则不要假设任何书在用户书架内。"

ProgressCallback = Callable[[str], None]


class ReadingAgent:
    def __init__(self, config: Config, tool_registry: ToolRegistry | None = None) -> None:
        self.config = config
        self.tool_registry = tool_registry or create_default_tool_registry()

    def _progress(
        self,
        callback: ProgressCallback | None,
        trace: InteractionTrace | None,
        stage: str,
        text: str,
    ) -> None:
        if trace:
            trace.event("progress", stage=stage, text=text)
        if not callback:
            return
        try:
            callback(text)
        except Exception as exc:
            if trace:
                trace.event("progress_error", stage=stage, error=str(exc))

    def _tool_context(
        self,
        trace: InteractionTrace | None,
        progress_callback: ProgressCallback | None,
    ) -> ToolContext:
        return ToolContext(
            config=self.config,
            trace=trace,
            progress_callback=progress_callback,
        )

    def _weread_context(self, trace: InteractionTrace | None = None) -> str:
        if not self.config.weread_api_key:
            return "未配置 WEREAD_API_KEY，无法读取微信读书书架。"
        try:
            return fetch_shelf_context(self.config.weread_api_key, trace=trace)
        except Exception as exc:
            return f"微信读书数据暂时无法读取：{exc}"

    def _needs_shelf_context(self, message: str) -> bool:
        normalized = message.strip().lower()
        if not normalized:
            return False
        shelf_keywords = ("书架", "书架内", "已有的书", "已有书", "现有的书", "我有的书", "手头的书")
        return any(keyword in normalized for keyword in shelf_keywords)

    def _needs_material_verification(self, message: str) -> bool:
        keywords = ("推荐", "读什么", "换一本", "适合", "章节", "哪一章", "哪部分", "哪一节")
        return any(keyword in message for keyword in keywords)

    def _needs_reading_reflection(self, message: str) -> bool:
        keywords = ("读完了", "读完：", "读完:", "读后", "读后感", "阅读复盘", "读书复盘", "看完《", "看完了《")
        return any(keyword in message for keyword in keywords)

    def _run_reading_reflection(
        self,
        message: str,
        trace: InteractionTrace,
        progress_callback: ProgressCallback | None = None,
    ) -> str:
        self._progress(progress_callback, trace, "personal_context", "正在读取你的个人处境上下文...")
        personal_result = self.tool_registry.call(
            "personal.read_context",
            self._tool_context(trace, progress_callback),
            message=message,
        )
        personal_context = personal_result.content if personal_result.ok else "暂无个人处境上下文。"
        trace.event("personal_context_loaded", chars=len(personal_context), flow="reading_reflection")

        self._progress(progress_callback, trace, "reading_reflection", "正在整理这次读后反馈...")
        return generate_reading_reply(
            self.config.llm_api_key,
            self.config.llm_base_url,
            self.config.llm_model,
            message,
            personal_context,
            NO_SHELF_CONTEXT,
            trace=trace,
        )

    def _evidence_aware_material_scoring_context(
        self,
        message: str,
        personal_context: str,
        personal_evidence_context: str,
        verified_materials_context: str,
        trace: InteractionTrace | None = None,
    ) -> str:
        if not self._needs_material_verification(message):
            return ""
        if not verified_materials_context.strip():
            if trace:
                trace.event("evidence_aware_material_scoring_skipped", reason="empty_verified_materials")
            return ""

        try:
            return generate_evidence_aware_material_scoring(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                personal_context,
                personal_evidence_context,
                verified_materials_context,
                trace=trace,
            )
        except Exception as exc:
            if trace:
                trace.event("evidence_aware_material_scoring_error", error=str(exc))
            return ""

    def _with_loop_history(self, material_scoring_context: str, loop_history: list[str]) -> str:
        if not loop_history:
            return material_scoring_context
        history = "\n\n".join(loop_history)[-5000:]
        return f"{material_scoring_context.strip()}\n\n## Agent loop history\n{history}".strip()

    def _state_summary(
        self,
        verified_materials_context: str,
        personal_evidence_context: str,
        material_scoring_context: str,
        reply: str,
        material_verification_rounds: int,
        supplemental_rounds: int,
        last_gate_reason: str,
    ) -> str:
        return "\n".join(
            [
                f"has_verified_materials: {bool(verified_materials_context.strip())}",
                f"has_personal_evidence: {bool(personal_evidence_context.strip())}",
                f"has_material_scoring: {bool(material_scoring_context.strip())}",
                f"has_draft_reply: {bool(reply.strip())}",
                f"material_verification_rounds: {material_verification_rounds}",
                f"supplemental_rounds: {supplemental_rounds}",
                f"last_gate_reason: {last_gate_reason or 'none'}",
            ]
        )

    def _fallback_action(
        self,
        verified_materials_context: str,
        personal_evidence_context: str,
        material_scoring_context: str,
        reply: str,
    ) -> str:
        if not verified_materials_context.strip():
            return "verify_materials"
        if not personal_evidence_context.strip():
            return "read_personal_evidence"
        if not material_scoring_context.strip():
            return "score_materials"
        if not reply.strip():
            return "draft_reply"
        return "fail"

    def _fallback_after_verify_limit(
        self,
        verified_materials_context: str,
        personal_evidence_context: str,
        material_scoring_context: str,
        reply: str,
    ) -> str:
        if not verified_materials_context.strip():
            return "fail"
        if not personal_evidence_context.strip():
            return "read_personal_evidence"
        if not material_scoring_context.strip():
            return "score_materials"
        if not reply.strip():
            return "draft_reply"
        return "fail"

    def _coerce_next_action(
        self,
        planned_action: dict[str, object],
        verified_materials_context: str,
        personal_evidence_context: str,
        material_scoring_context: str,
        reply: str,
        material_verification_rounds: int,
        max_material_verification_rounds: int,
        trace: InteractionTrace,
    ) -> dict[str, object]:
        action = str(planned_action.get("action") or "")
        allowed_actions = {"verify_materials", "read_personal_evidence", "score_materials", "draft_reply", "fail"}
        fallback = self._fallback_action(
            verified_materials_context,
            personal_evidence_context,
            material_scoring_context,
            reply,
        )

        if action not in allowed_actions:
            trace.event("agent_action_forced", from_action=action, to_action=fallback, reason="unknown_action")
            action = fallback
        elif action == "verify_materials" and material_verification_rounds >= max_material_verification_rounds:
            next_action = self._fallback_after_verify_limit(
                verified_materials_context,
                personal_evidence_context,
                material_scoring_context,
                reply,
            )
            trace.event(
                "agent_action_forced",
                from_action=action,
                to_action=next_action,
                reason="material_verification_round_limit",
            )
            action = next_action
        elif action == "score_materials" and not verified_materials_context.strip():
            trace.event("agent_action_forced", from_action=action, to_action="verify_materials", reason="score_requires_verified_materials")
            action = "verify_materials"
        elif action == "score_materials" and not personal_evidence_context.strip():
            trace.event("agent_action_forced", from_action=action, to_action="read_personal_evidence", reason="score_requires_personal_evidence")
            action = "read_personal_evidence"
        elif action == "draft_reply" and not verified_materials_context.strip():
            trace.event("agent_action_forced", from_action=action, to_action="verify_materials", reason="draft_requires_verified_materials")
            action = "verify_materials"
        elif action == "read_personal_evidence" and personal_evidence_context.strip():
            trace.event("agent_action_forced", from_action=action, to_action=fallback, reason="personal_evidence_already_loaded")
            action = fallback
        elif action == "score_materials" and material_scoring_context.strip():
            trace.event("agent_action_forced", from_action=action, to_action=fallback, reason="material_scoring_already_loaded")
            action = fallback

        coerced = dict(planned_action)
        coerced["action"] = action if action else fallback
        return coerced

    def _run_recommendation_loop(
        self,
        message: str,
        trace: InteractionTrace,
        progress_callback: ProgressCallback | None = None,
        max_turns: int = 10,
        max_material_verification_rounds: int = 2,
        max_supplemental_rounds: int = 2,
    ) -> str:
        tool_context = self._tool_context(trace, progress_callback)
        loop_history: list[str] = []

        self._progress(progress_callback, trace, "personal_context", "正在读取你的个人处境上下文...")
        personal_result = self.tool_registry.call("personal.read_context", tool_context, message=message)
        personal_context = personal_result.content or "暂无个人处境上下文。"
        loop_history.append(personal_result.as_history_text(max_chars=1200))
        trace.event("personal_context_loaded", chars=len(personal_context))

        if self._needs_shelf_context(message):
            self._progress(progress_callback, trace, "weread_shelf", "正在读取微信读书书架...")
            shelf_result = self.tool_registry.call("weread.fetch_shelf", tool_context)
            weread_context = shelf_result.content
            loop_history.append(shelf_result.as_history_text(max_chars=1200))
        else:
            weread_context = NO_SHELF_CONTEXT
            trace.event("weread_shelf_skipped", reason="message_does_not_request_shelf")
        trace.event("weread_context_loaded", chars=len(weread_context))

        verified_materials_context = ""
        personal_evidence_context = ""
        material_scoring_context = ""
        reply = ""
        supplemental_rounds = 0
        material_verification_rounds = 0
        last_gate_reason = ""

        for turn in range(1, max_turns + 1):
            trace.event(
                "agent_loop_turn",
                turn=turn,
                has_verified_materials=bool(verified_materials_context.strip()),
                has_personal_evidence=bool(personal_evidence_context.strip()),
                has_material_scoring=bool(material_scoring_context.strip()),
                has_reply=bool(reply.strip()),
                material_verification_rounds=material_verification_rounds,
                supplemental_rounds=supplemental_rounds,
            )

            if not reply.strip():
                state_summary = self._state_summary(
                    verified_materials_context,
                    personal_evidence_context,
                    material_scoring_context,
                    reply,
                    material_verification_rounds,
                    supplemental_rounds,
                    last_gate_reason,
                )
                try:
                    planned_action = plan_next_reading_action(
                        self.config.llm_api_key,
                        self.config.llm_base_url,
                        self.config.llm_model,
                        message,
                        state_summary,
                        "\n\n".join(loop_history),
                        trace=trace,
                    )
                except Exception as exc:
                    trace.event("agent_next_action_error", error=str(exc))
                    planned_action = {
                        "action": self._fallback_action(
                            verified_materials_context,
                            personal_evidence_context,
                            material_scoring_context,
                            reply,
                        ),
                        "queries": [],
                        "reason": f"planner error: {exc}",
                        "progress": "",
                    }
                action_plan = self._coerce_next_action(
                    planned_action,
                    verified_materials_context,
                    personal_evidence_context,
                    material_scoring_context,
                    reply,
                    material_verification_rounds,
                    max_material_verification_rounds,
                    trace,
                )
                action = str(action_plan.get("action") or "")
                loop_history.append(
                    f"agent_next_action: action={action}; queries={action_plan.get('queries')}; reason={action_plan.get('reason')}"
                )
            else:
                action_plan = {"action": "check_reply", "queries": []}
                action = "check_reply"

            if action == "verify_materials":
                planned_queries = action_plan.get("queries")
                queries = [str(query).strip() for query in planned_queries if str(query).strip()] if isinstance(planned_queries, list) else []
                try:
                    if not queries:
                        self._progress(progress_callback, trace, "material_queries", "正在根据你的处境规划检索词...")
                        queries = generate_material_queries(
                            self.config.llm_api_key,
                            self.config.llm_base_url,
                            self.config.llm_model,
                            message,
                            personal_context,
                            weread_context,
                            trace=trace,
                        )
                except Exception as exc:
                    trace.event("material_query_error", error=str(exc))
                    loop_history.append(f"material_queries error: {exc}")
                    continue

                loop_history.append(f"material_queries: {queries}")
                if not queries:
                    trace.event("material_verification_skipped", reason="empty_material_queries")
                    loop_history.append("material_verification_skipped: empty queries")
                    continue

                material_verification_rounds += 1
                self._progress(progress_callback, trace, "weread_verification", "正在查微信读书目录、划线和点评...")
                material_result = self.tool_registry.call(
                    "weread.verify_materials",
                    tool_context,
                    queries=queries,
                    max_queries=4,
                    max_books_per_query=1,
                    phase="initial" if material_verification_rounds == 1 else f"agent_loop_{material_verification_rounds}",
                )
                if verified_materials_context.strip() and material_result.ok:
                    verified_materials_context = (
                        f"{verified_materials_context}\n\n"
                        f"## Agent 补充验证材料（第 {material_verification_rounds} 轮）\n"
                        f"{material_result.content.strip()}"
                    ).strip()
                elif not verified_materials_context.strip():
                    verified_materials_context = material_result.content
                loop_history.append(material_result.as_history_text(max_chars=1800))
                trace.event("verified_materials_loaded", chars=len(verified_materials_context))
                continue

            if action == "read_personal_evidence":
                self._progress(progress_callback, trace, "personal_evidence_context", "正在回读相关 daily note 原文片段...")
                evidence_result = self.tool_registry.call("personal.read_evidence", tool_context, message=message)
                personal_evidence_context = evidence_result.content or "暂无 personal-kb 原文片段。"
                loop_history.append(evidence_result.as_history_text(max_chars=1400))
                trace.event("personal_evidence_context_loaded", chars=len(personal_evidence_context))
                continue

            if action == "score_materials":
                self._progress(progress_callback, trace, "material_scoring", "正在比较候选材料和你的真实处境...")
                material_scoring_context = self._evidence_aware_material_scoring_context(
                    message,
                    personal_context,
                    personal_evidence_context,
                    verified_materials_context,
                    trace=trace,
                )
                loop_history.append(f"material_scoring chars: {len(material_scoring_context)}")
                trace.event("material_scoring_loaded", chars=len(material_scoring_context))
                continue

            if action == "draft_reply":
                self._progress(progress_callback, trace, "reading_reply", "正在生成这次阅读建议...")
                reply = generate_reading_reply(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    message,
                    personal_context,
                    weread_context,
                    verified_materials_context,
                    self._with_loop_history(material_scoring_context, loop_history),
                    trace=trace,
                )
                continue

            if action == "fail":
                reason = str(action_plan.get("reason") or "planner failed")
                trace.event("agent_loop_planner_failed", turn=turn, reason=reason)
                return f"这次读书建议没有找到足够可靠的材料支撑。\n原因：{reason}"

            self._progress(progress_callback, trace, "final_reply_material_check", "正在做材料校验...")
            try:
                material_check = check_final_reply_materials(
                    self.config.llm_api_key,
                    self.config.llm_base_url,
                    self.config.llm_model,
                    message,
                    reply,
                    verified_materials_context,
                    trace=trace,
                )
            except Exception as exc:
                trace.event("final_reply_material_check_error", error=str(exc))
                return reply

            if material_check.get("ok"):
                trace.event("final_reply_material_gate_passed", turn=turn, reason=material_check.get("reason"))
                return reply

            last_gate_reason = str(material_check.get("reason") or "最终回复引入了未验证材料。")
            extra_queries = material_check.get("extra_queries")
            loop_history.append(f"final_reply_material_gate_failed: {last_gate_reason}; extra_queries={extra_queries}")

            if not extra_queries:
                trace.event(
                    "final_reply_material_gate_blocked",
                    turn=turn,
                    reason=last_gate_reason,
                    extra_queries=[],
                )
                return f"这次推荐没有通过材料校验，我先不硬推具体材料。\n原因：{last_gate_reason}\n校验器没有给出可补查的检索词。"

            if supplemental_rounds >= max_supplemental_rounds:
                trace.event(
                    "final_reply_material_gate_blocked",
                    turn=turn,
                    reason=last_gate_reason,
                    extra_queries=extra_queries,
                    max_supplemental_rounds=max_supplemental_rounds,
                )
                return f"这次推荐没有通过材料校验，我先不硬推具体材料。\n原因：{last_gate_reason}\n可以换个更具体的问题再试一次。"

            supplemental_rounds += 1
            self._progress(progress_callback, trace, "final_reply_supplemental_verification", "发现有材料需要补查，正在补充验证...")
            supplemental_result = self.tool_registry.call(
                "weread.verify_materials",
                tool_context,
                queries=extra_queries,
                max_queries=2,
                max_books_per_query=1,
                phase="final_reply_check",
            )
            loop_history.append(supplemental_result.as_history_text(max_chars=1800))
            if supplemental_result.ok and supplemental_result.content.strip():
                verified_materials_context = (
                    f"{verified_materials_context}\n\n"
                    f"## 最终回复补充验证材料（第 {supplemental_rounds} 轮）\n"
                    f"{supplemental_result.content.strip()}"
                ).strip()
                reply = ""
                continue

            trace.event(
                "final_reply_supplemental_verification_empty",
                turn=turn,
                queries=extra_queries,
                error=supplemental_result.error,
            )
            return f"这次推荐没有通过材料校验，我先不硬推具体材料。\n原因：{last_gate_reason}\n补查也没有拿到足够证据。"

        trace.event("agent_loop_max_turns", max_turns=max_turns, has_reply=bool(reply.strip()), reason=last_gate_reason)
        if reply.strip():
            return "这次读书建议已经生成，但没有在轮次上限内完成最终材料校验，所以我先不发具体推荐。可以稍后再试一次。"
        return "这次读书建议没有在轮次上限内生成成功，可以稍后再试一次，或把问题说得更具体一点。"

    def reply(self, text: str, progress_callback: ProgressCallback | None = None) -> str:
        message = text.strip()
        trace = InteractionTrace(self.config.trace_log_dir, enabled=self.config.trace_log_enabled)
        trace.event("reply_start", user_message=message)
        if not message:
            trace.event("reply_short_circuit", reason="empty_message")
            return "你可以直接问我：推荐阅读，或发“读完了：...”让我帮你做读后沉淀。"

        try:
            if message in {"帮助", "help", "/help"}:
                trace.event("reply_short_circuit", reason="help")
                return HELP_TEXT

            if message in {"书架", "我的书架", "检查微信读书", "/shelf"}:
                reply = self._weread_context(trace=trace)
                trace.event("reply_complete", elapsed_ms=trace.elapsed_ms(), chars=len(reply))
                return reply

            if self._needs_material_verification(message):
                reply = self._run_recommendation_loop(message, trace, progress_callback=progress_callback)
                trace.event("reply_complete", elapsed_ms=trace.elapsed_ms(), chars=len(reply), flow="restricted_loop")
                return reply

            if self._needs_reading_reflection(message):
                reply = self._run_reading_reflection(message, trace, progress_callback=progress_callback)
                trace.event("reply_complete", elapsed_ms=trace.elapsed_ms(), chars=len(reply), flow="reading_reflection")
                return reply

            reply = generate_general_reply(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                trace=trace,
            )
            trace.event("reply_complete", elapsed_ms=trace.elapsed_ms(), chars=len(reply), flow="general")
            return reply
        except Exception as exc:
            trace.event("reply_error", elapsed_ms=trace.elapsed_ms(), error=str(exc))
            raise
