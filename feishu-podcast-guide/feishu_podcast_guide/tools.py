from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Config
from .paper import (
    fetch_arxiv_paper,
    format_paper_detail,
    format_paper_search_results,
    paper_ref,
    search_arxiv,
)
from .podcast_index import Episode, PodcastIndex, format_context, format_episode_detail
from .rss import refresh_rss


@dataclass(frozen=True)
class ToolContext:
    config: Config
    get_index: Callable[[], PodcastIndex]
    refresh_index: Callable[[], PodcastIndex]


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    content: str
    evidence_level: str
    episodes: list[dict[str, str]] = field(default_factory=list)
    papers: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def as_history_text(self, max_chars: int = 2000) -> str:
        status = "ok" if self.ok else "failed"
        lines = [
            f"tool_result: {self.tool}",
            f"status: {status}",
            f"evidence_level: {self.evidence_level}",
        ]
        if self.episodes:
            lines.append("episodes:")
            for episode in self.episodes:
                lines.append(
                    f"- id={episode.get('id')} title={episode.get('title')} url={episode.get('url')}"
                )
        if self.papers:
            lines.append("papers:")
            for paper in self.papers:
                lines.append(
                    f"- id={paper.get('id')} title={paper.get('title')} abs_url={paper.get('abs_url')} pdf_url={paper.get('pdf_url')}"
                )
        if self.error:
            lines.append(f"error: {self.error}")
        if self.content:
            lines.append("content:")
            lines.append(self.content[:max_chars])
        return "\n".join(lines)


class PodcastToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., ToolResult]] = {
            "search_episodes": self._search_episodes,
            "get_episode_detail": self._get_episode_detail,
            "list_learning_path": self._list_learning_path,
            "refresh_rss": self._refresh_rss,
            "search_papers": self._search_papers,
            "fetch_paper": self._fetch_paper,
        }

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def call(self, name: str, context: ToolContext, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool=name,
                ok=False,
                content="",
                evidence_level="none",
                error=f"unknown tool: {name}",
            )
        try:
            return tool(context, **kwargs)
        except Exception as exc:
            return ToolResult(
                tool=name,
                ok=False,
                content="",
                evidence_level="tool_error",
                error=str(exc),
                metadata={"arguments": kwargs},
            )

    def _search_episodes(
        self,
        context: ToolContext,
        query: str,
        limit: int = 6,
    ) -> ToolResult:
        index = context.get_index()
        safe_limit = max(1, min(int(limit or 6), 10))
        results = index.search(query, limit=safe_limit)
        episodes = [_episode_ref(item.episode) for item in results]
        content = format_context(results)
        if not results:
            content = f"没有检索到与「{query}」明确相关的 RSS 条目。"
        return ToolResult(
            tool="search_episodes",
            ok=bool(results),
            content=content,
            evidence_level="rss_search_results",
            episodes=episodes,
            metadata={"query": query, "limit": safe_limit, "result_count": len(results)},
        )

    def _get_episode_detail(
        self,
        context: ToolContext,
        episode_id: str = "",
        url: str = "",
        title: str = "",
    ) -> ToolResult:
        identifier = episode_id or url or title
        episode = context.get_index().find_episode(identifier)
        if not episode:
            return ToolResult(
                tool="get_episode_detail",
                ok=False,
                content=f"没有找到单集：{identifier}",
                evidence_level="none",
                metadata={"identifier": identifier},
            )
        return ToolResult(
            tool="get_episode_detail",
            ok=True,
            content=format_episode_detail(episode),
            evidence_level="rss_episode_detail",
            episodes=[_episode_ref(episode)],
            metadata={"identifier": identifier},
        )

    def _list_learning_path(
        self,
        context: ToolContext,
        topic: str = "Agent",
        limit: int = 8,
    ) -> ToolResult:
        safe_limit = max(1, min(int(limit or 8), 12))
        episodes = context.get_index().first_round(topic, limit=safe_limit)
        lines: list[str] = []
        for index, episode in enumerate(episodes, start=1):
            lines.append(
                "\n".join(
                    [
                        f"{index}. {episode.title}",
                        f"id：{episode.id}",
                        f"链接：{episode.url}",
                        f"位置：{episode.stage or episode.source}",
                        f"路线标注：{episode.note or episode.summary or '暂无额外标注。'}",
                    ]
                )
            )
        return ToolResult(
            tool="list_learning_path",
            ok=bool(episodes),
            content="\n\n".join(lines) if lines else f"没有找到 {topic} 学习路径。",
            evidence_level="curated_learning_path",
            episodes=[_episode_ref(episode) for episode in episodes],
            metadata={"topic": topic, "limit": safe_limit, "result_count": len(episodes)},
        )

    def _refresh_rss(self, context: ToolContext) -> ToolResult:
        count = refresh_rss(context.config)
        context.refresh_index()
        return ToolResult(
            tool="refresh_rss",
            ok=True,
            content=f"RSS 已刷新，当前下载到 {count} 集。",
            evidence_level="rss_refresh_result",
            metadata={"item_count": count},
        )

    def _search_papers(
        self,
        context: ToolContext,
        query: str,
        limit: int = 5,
    ) -> ToolResult:
        safe_limit = max(1, min(int(limit or 5), 8))
        papers = search_arxiv(query, limit=safe_limit)
        return ToolResult(
            tool="search_papers",
            ok=bool(papers),
            content=format_paper_search_results(papers),
            evidence_level="arxiv_search_results",
            papers=[paper_ref(paper) for paper in papers],
            metadata={"query": query, "limit": safe_limit, "result_count": len(papers)},
        )

    def _fetch_paper(
        self,
        context: ToolContext,
        identifier: str = "",
        paper_id: str = "",
        url: str = "",
        title: str = "",
        query: str = "",
    ) -> ToolResult:
        target = identifier or paper_id or url or title or query
        paper, text, extracted = fetch_arxiv_paper(
            target,
            context.config.paper_cache_path,
            max_pages=context.config.paper_max_pages,
            max_chars=context.config.paper_max_chars,
        )
        return ToolResult(
            tool="fetch_paper",
            ok=True,
            content=format_paper_detail(paper, text, extracted),
            evidence_level="arxiv_pdf_text" if extracted else "arxiv_metadata_only",
            papers=[paper_ref(paper)],
            metadata={
                "identifier": target,
                "paper_id": paper.paper_id,
                "text_chars": len(text),
                "pdf_text_extracted": extracted,
            },
        )


def _episode_ref(episode: Episode) -> dict[str, str]:
    return {
        "id": episode.id,
        "title": episode.title,
        "url": episode.url,
        "source": episode.source,
        "stage": episode.stage,
    }
