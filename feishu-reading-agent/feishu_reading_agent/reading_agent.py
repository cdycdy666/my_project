from __future__ import annotations

from .config import Config
from .llm import (
    generate_material_queries,
    generate_material_ranking,
    generate_reading_reply,
    generate_supplemental_material_queries,
)
from .personal_context import read_personal_context
from .trace import InteractionTrace
from .weread import fetch_shelf_context, fetch_verified_materials_context


HELP_TEXT = """我是你的读书智能体，会结合个人处境和微信读书书架给阅读建议。

可以这样发：
- 推荐阅读
- 换一本
- 书架
- 这本书适合我现在读吗：书名
- 读完了：你的读后感
"""


class ReadingAgent:
    def __init__(self, config: Config) -> None:
        self.config = config

    def _personal_context(self) -> str:
        context = read_personal_context(self.config.personal_kb_dir)
        return context or "暂无个人处境上下文。"

    def _weread_context(self, trace: InteractionTrace | None = None) -> str:
        if not self.config.weread_api_key:
            return "未配置 WEREAD_API_KEY，无法读取微信读书书架。"
        try:
            return fetch_shelf_context(self.config.weread_api_key, trace=trace)
        except Exception as exc:
            return f"微信读书数据暂时无法读取：{exc}"

    def _needs_material_verification(self, message: str) -> bool:
        keywords = ("推荐", "读什么", "换一本", "适合", "章节", "哪一章", "哪部分", "哪一节")
        return any(keyword in message for keyword in keywords)

    def _verified_materials_context(
        self,
        message: str,
        personal_context: str,
        weread_context: str,
        trace: InteractionTrace | None = None,
    ) -> str:
        if not self._needs_material_verification(message):
            if trace:
                trace.event("material_verification_skipped", reason="message_does_not_need_verification")
            return ""
        if not self.config.weread_api_key:
            if trace:
                trace.event("material_verification_skipped", reason="missing_weread_api_key")
            return "未配置 WEREAD_API_KEY，无法验证书名或章节目录。"

        try:
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
            if trace:
                trace.event("material_query_error", error=str(exc))
            return f"材料查询规划失败：{exc}。涉及章节时不能编造位置，只能推荐关键词搜索。"

        if not queries:
            if trace:
                trace.event("material_verification_skipped", reason="empty_material_queries")
            return "没有生成可验证的材料查询。涉及章节时不能编造位置，只能推荐关键词搜索。"

        try:
            return fetch_verified_materials_context(self.config.weread_api_key, queries, trace=trace)
        except Exception as exc:
            if trace:
                trace.event("material_verification_error", error=str(exc), queries=queries)
            return f"材料目录验证失败：{exc}。涉及章节时不能编造位置，只能推荐关键词搜索。"

    def _supplemental_verified_materials_context(
        self,
        message: str,
        personal_context: str,
        weread_context: str,
        verified_materials_context: str,
        trace: InteractionTrace | None = None,
    ) -> str:
        if not self._needs_material_verification(message):
            return ""
        if not self.config.weread_api_key:
            if trace:
                trace.event("supplemental_material_verification_skipped", reason="missing_weread_api_key")
            return ""
        if not verified_materials_context.strip():
            if trace:
                trace.event("supplemental_material_verification_skipped", reason="empty_verified_materials")
            return ""

        try:
            queries = generate_supplemental_material_queries(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                personal_context,
                weread_context,
                verified_materials_context,
                trace=trace,
            )
        except Exception as exc:
            if trace:
                trace.event("supplemental_material_query_error", error=str(exc))
            return ""

        if not queries:
            if trace:
                trace.event("supplemental_material_verification_skipped", reason="empty_supplemental_queries")
            return ""

        try:
            return fetch_verified_materials_context(
                self.config.weread_api_key,
                queries,
                max_queries=2,
                trace=trace,
                phase="supplemental",
            )
        except Exception as exc:
            if trace:
                trace.event("supplemental_material_verification_error", error=str(exc), queries=queries)
            return ""

    def _material_ranking_context(
        self,
        message: str,
        personal_context: str,
        weread_context: str,
        verified_materials_context: str,
        trace: InteractionTrace | None = None,
    ) -> str:
        if not self._needs_material_verification(message):
            return ""
        if not verified_materials_context.strip():
            if trace:
                trace.event("material_ranking_skipped", reason="empty_verified_materials")
            return ""

        try:
            return generate_material_ranking(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                personal_context,
                weread_context,
                verified_materials_context,
                trace=trace,
            )
        except Exception as exc:
            if trace:
                trace.event("material_ranking_error", error=str(exc))
            return ""

    def reply(self, text: str) -> str:
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

            personal_context = self._personal_context()
            trace.event("personal_context_loaded", chars=len(personal_context))
            weread_context = self._weread_context(trace=trace)
            trace.event("weread_context_loaded", chars=len(weread_context))
            verified_materials_context = self._verified_materials_context(
                message,
                personal_context,
                weread_context,
                trace=trace,
            )
            trace.event("verified_materials_loaded", chars=len(verified_materials_context))
            supplemental_materials_context = self._supplemental_verified_materials_context(
                message,
                personal_context,
                weread_context,
                verified_materials_context,
                trace=trace,
            )
            trace.event("supplemental_verified_materials_loaded", chars=len(supplemental_materials_context))
            if supplemental_materials_context:
                verified_materials_context = (
                    f"{verified_materials_context}\n\n"
                    f"## 补充验证材料\n{supplemental_materials_context}"
                ).strip()
            material_ranking_context = self._material_ranking_context(
                message,
                personal_context,
                weread_context,
                verified_materials_context,
                trace=trace,
            )
            trace.event("material_ranking_loaded", chars=len(material_ranking_context))
            reply = generate_reading_reply(
                self.config.llm_api_key,
                self.config.llm_base_url,
                self.config.llm_model,
                message,
                personal_context,
                weread_context,
                verified_materials_context,
                material_ranking_context,
                trace=trace,
            )
            trace.event("reply_complete", elapsed_ms=trace.elapsed_ms(), chars=len(reply))
            return reply
        except Exception as exc:
            trace.event("reply_error", elapsed_ms=trace.elapsed_ms(), error=str(exc))
            raise
