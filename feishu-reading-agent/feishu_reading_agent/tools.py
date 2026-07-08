from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Config
from .personal_context import read_personal_context, read_personal_evidence_context
from .trace import InteractionTrace
from .weread import fetch_shelf_context, fetch_verified_materials_context


ToolProgressCallback = Callable[[str], None]


@dataclass
class ToolContext:
    config: Config
    trace: InteractionTrace | None = None
    progress_callback: ToolProgressCallback | None = None

    def progress(self, text: str) -> None:
        if not self.progress_callback:
            return
        self.progress_callback(text)


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    content: str = ""
    evidence_level: str = ""
    verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def as_history_text(self, max_chars: int = 5000) -> str:
        status = "ok" if self.ok else "error"
        lines = [
            f"## tool_result: {self.tool_name}",
            f"- status: {status}",
            f"- verified: {self.verified}",
        ]
        if self.evidence_level:
            lines.append(f"- evidence_level: {self.evidence_level}")
        if self.metadata:
            lines.append(f"- metadata: {self.metadata}")
        if self.error:
            lines.append(f"- error: {self.error}")
        if self.content:
            content = self.content.strip()
            if len(content) > max_chars:
                content = f"{content[:max_chars].rstrip()}... [truncated {len(content) - max_chars} chars]"
            lines.append(content)
        return "\n".join(lines)


class BaseTool:
    name = ""
    description = ""

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("tool.name is required")
        self._tools[tool.name] = tool

    def call(self, name: str, context: ToolContext, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Unknown tool: {name}")

        if context.trace:
            context.trace.event("tool_call", tool=name, arguments=kwargs)

        try:
            result = tool.run(context, **kwargs)
        except Exception as exc:
            result = ToolResult(tool_name=name, ok=False, error=str(exc))

        if context.trace:
            context.trace.event(
                "tool_result",
                tool=name,
                ok=result.ok,
                verified=result.verified,
                evidence_level=result.evidence_level,
                chars=len(result.content),
                metadata=result.metadata,
                error=result.error,
            )
        return result


class ReadPersonalContextTool(BaseTool):
    name = "personal.read_context"
    description = "Read the PersonalContextBundle summary from personal-kb."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        message = str(kwargs.get("message") or "")
        content = read_personal_context(context.config.personal_kb_dir, query=message)
        return ToolResult(
            tool_name=self.name,
            ok=True,
            content=content or "暂无个人处境上下文。",
            evidence_level="personal_context_summary",
            verified=True,
            metadata={"chars": len(content or "")},
        )


class ReadPersonalEvidenceTool(BaseTool):
    name = "personal.read_evidence"
    description = "Read relevant daily note source excerpts from personal-kb."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        message = str(kwargs.get("message") or "")
        content = read_personal_evidence_context(context.config.personal_kb_dir, query=message)
        return ToolResult(
            tool_name=self.name,
            ok=True,
            content=content or "暂无 personal-kb 原文片段。",
            evidence_level="personal_daily_note_excerpt",
            verified=True,
            metadata={"chars": len(content or "")},
        )


class FetchWereadShelfTool(BaseTool):
    name = "weread.fetch_shelf"
    description = "Fetch the user's WeRead shelf context."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        if not context.config.weread_api_key:
            return ToolResult(
                tool_name=self.name,
                ok=False,
                content="未配置 WEREAD_API_KEY，无法读取微信读书书架。",
                evidence_level="missing_api_key",
                error="missing WEREAD_API_KEY",
            )
        content = fetch_shelf_context(context.config.weread_api_key, trace=context.trace)
        return ToolResult(
            tool_name=self.name,
            ok=True,
            content=content,
            evidence_level="weread_shelf",
            verified=True,
            metadata={"chars": len(content)},
        )


class VerifyWereadMaterialsTool(BaseTool):
    name = "weread.verify_materials"
    description = "Search WeRead and verify books, chapters, highlights, reviews, and personal notes for queries."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        if not context.config.weread_api_key:
            return ToolResult(
                tool_name=self.name,
                ok=False,
                content="未配置 WEREAD_API_KEY，无法验证书名或章节目录。",
                evidence_level="missing_api_key",
                error="missing WEREAD_API_KEY",
            )

        raw_queries = kwargs.get("queries")
        queries = [str(item).strip() for item in raw_queries if str(item).strip()] if isinstance(raw_queries, list) else []
        max_queries = int(kwargs.get("max_queries") or 4)
        max_books_per_query = int(kwargs.get("max_books_per_query") or 1)
        phase = str(kwargs.get("phase") or "initial")

        if not queries:
            return ToolResult(
                tool_name=self.name,
                ok=False,
                content="没有可验证的材料查询。涉及章节时不能编造位置，只能推荐关键词搜索。",
                evidence_level="empty_queries",
                error="empty queries",
            )

        content = fetch_verified_materials_context(
            context.config.weread_api_key,
            queries,
            max_queries=max_queries,
            max_books_per_query=max_books_per_query,
            phase=phase,
            trace=context.trace,
        )
        return ToolResult(
            tool_name=self.name,
            ok=bool(content.strip()),
            content=content or "微信读书未返回可验证材料。",
            evidence_level="weread_directory_and_snippet_evidence",
            verified=bool(content.strip()),
            metadata={
                "queries": queries[:max_queries],
                "phase": phase,
                "chars": len(content or ""),
            },
        )


def create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ReadPersonalContextTool())
    registry.register(ReadPersonalEvidenceTool())
    registry.register(FetchWereadShelfTool())
    registry.register(VerifyWereadMaterialsTool())
    return registry
