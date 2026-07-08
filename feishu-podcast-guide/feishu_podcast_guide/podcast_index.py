from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from hashlib import sha1
from pathlib import Path


@dataclass(frozen=True)
class Episode:
    id: str
    title: str
    url: str
    source: str
    stage: str
    note: str
    order: int
    published: str = ""
    summary: str = ""

    @property
    def searchable_text(self) -> str:
        return " ".join(
            [
                self.title,
                self.stage,
                self.note,
                self.summary,
                self.published,
            ]
        ).lower()


@dataclass(frozen=True)
class SearchResult:
    episode: Episode
    score: float


KNOWN_TERMS = {
    "agent": ["agent", "智能体", "行动", "工具", "workflow", "工作流", "自主", "协作"],
    "智能体": ["agent", "智能体", "行动", "工具", "多智能体", "自主", "协作"],
    "多智能体": ["多智能体", "协作", "团队", "shared memory", "共享白板"],
    "rag": ["rag", "检索", "搜索", "知识库", "deep research", "research agent"],
    "deep research": ["deep research", "研究", "搜索", "论文搜索", "research agent"],
    "强化学习": ["强化学习", "rl", "reward", "奖励", "rlhf", "dpo", "grpo", "sft", "偏好", "后训练"],
    "rl": ["强化学习", "rl", "reward", "奖励", "rlhf", "dpo", "grpo", "sft", "偏好", "后训练"],
    "grpo": ["grpo", "rl", "强化学习", "group", "后训练", "推理"],
    "dpo": ["dpo", "偏好", "对齐", "后训练", "rlhf"],
    "sft": ["sft", "监督微调", "后训练", "泛化", "rl"],
    "reward": ["reward", "奖励", "verifier", "裁判", "评估", "reward hacking"],
    "记忆": ["记忆", "反思", "复盘", "长期记忆", "短期记忆"],
    "安全": ["安全", "评估", "验证", "越权", "成本", "裁判"],
    "项目": ["落地", "项目", "mvp", "工具", "工作流", "评估", "成本"],
    "飞书": ["飞书", "机器人", "助手", "agent", "工具", "工作流"],
}

RECENT_KEYWORDS = ("最近", "最新", "近期", "新一集", "新几集", "latest", "recent")


THEME_BUCKETS: dict[str, list[str]] = {
    "Agent 工程": ["agent", "智能体", "工具", "工作流", "多智能体", "自主"],
    "RAG / Deep Research": ["rag", "检索", "deep research", "research agent", "搜索", "知识库"],
    "强化学习与后训练": ["强化学习", "rl", "reward", "grpo", "dpo", "sft", "后训练", "偏好", "rlhf"],
    "记忆与反思": ["记忆", "反思", "复盘", "长期记忆", "短期记忆"],
    "评估与安全": ["评估", "验证", "裁判", "reward hacking", "安全", "越权", "成本"],
}


def _episode_id(title: str, url: str) -> str:
    return sha1(f"{title}\n{url}".encode("utf-8")).hexdigest()[:12]


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_table_row(line: str) -> list[str]:
    content = line.strip().strip("|")
    return [cell.strip() for cell in content.split("|")]


def _parse_markdown(path: Path, source: str) -> list[Episode]:
    if not path.exists():
        return []

    episodes: list[Episode] = []
    stage = ""
    order = 0

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            stage = line.lstrip("#").strip()
            continue
        if not line:
            continue

        table_match = re.search(r"\[(.+)\]\((https?://[^)]+)\)", line)
        if line.startswith("|") and table_match:
            cells = _split_table_row(line)
            if len(cells) < 2 or not cells[0].strip().isdigit():
                continue
            order = int(cells[0].strip())
            title = table_match.group(1).strip()
            url = table_match.group(2).strip()
            note = cells[2].strip() if len(cells) >= 3 else ""
            episodes.append(
                Episode(
                    id=_episode_id(title, url),
                    title=title,
                    url=url,
                    source=source,
                    stage=stage,
                    note=note,
                    order=order,
                )
            )
            continue

        list_match = re.match(r"(\d+)\.\s+\[(.+)\]\((https?://[^)]+)\)", line)
        if list_match:
            order = int(list_match.group(1))
            title = list_match.group(2).strip()
            url = list_match.group(3).strip()
            episodes.append(
                Episode(
                    id=_episode_id(title, url),
                    title=title,
                    url=url,
                    source=source,
                    stage=stage,
                    note="",
                    order=order,
                )
            )

    return episodes


def _parse_rss(path: Path) -> list[Episode]:
    if not path.exists():
        return []

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    episodes: list[Episode] = []
    for index, item in enumerate(root.findall(".//item"), start=1):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not title or not url:
            continue
        summary = _strip_html(item.findtext("description") or "")
        if len(summary) > 500:
            summary = summary[:500].rstrip() + "..."
        episodes.append(
            Episode(
                id=_episode_id(title, url),
                title=title,
                url=url,
                source="RSS",
                stage="全量 RSS",
                note="",
                order=index,
                published=(item.findtext("pubDate") or "").strip(),
                summary=summary,
            )
        )

    return episodes


def _query_terms(query: str) -> list[str]:
    raw_query = query.strip().lower()
    terms: list[str] = []

    for key, aliases in KNOWN_TERMS.items():
        if key in raw_query or any(alias.lower() in raw_query for alias in aliases):
            terms.extend(aliases)

    terms.extend(re.findall(r"[a-z][a-z0-9+#.-]{1,}", raw_query))
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", raw_query):
        if len(chunk) <= 8:
            terms.append(chunk)
        else:
            for known in KNOWN_TERMS:
                if known in chunk:
                    terms.append(known)

    deduped: list[str] = []
    for term in terms:
        cleaned = term.strip().lower()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _query_phrases(query: str) -> list[str]:
    phrases: list[str] = []
    for raw_part in re.split(r"[\s，。！？,.!?：:；;、]+", query.strip().lower()):
        part = raw_part.strip()
        if len(part) >= 3:
            phrases.append(part)
    return phrases


def _wants_recent(query: str) -> bool:
    return any(keyword in query.lower() for keyword in RECENT_KEYWORDS)


def _is_recent_only_token(value: str) -> bool:
    return any(keyword in value.lower() for keyword in RECENT_KEYWORDS)


class PodcastIndex:
    def __init__(self, rss_episodes: list[Episode], route_episodes: list[Episode] | None = None) -> None:
        self.route_episodes = route_episodes or []
        if not rss_episodes:
            self.episodes = self.route_episodes
            return

        by_url: dict[str, Episode] = {}
        for episode in rss_episodes:
            by_url.setdefault(episode.url, episode)

        for route in self.route_episodes:
            full_episode = by_url.get(route.url)
            if not full_episode:
                continue
            stage_parts = [full_episode.stage]
            if route.stage:
                stage_parts.append(f"{route.source}：{route.stage}")
            else:
                stage_parts.append(route.source)

            note_parts = []
            if route.note:
                note_parts.append(route.note)
            if full_episode.note:
                note_parts.append(full_episode.note)

            by_url[route.url] = replace(
                full_episode,
                stage="；".join(stage_parts),
                note="；".join(note_parts),
            )

        self.episodes = list(by_url.values())

    @classmethod
    def load(cls, agent_path: Path, rl_path: Path, rss_path: Path) -> "PodcastIndex":
        route_episodes = []
        route_episodes.extend(_parse_markdown(agent_path, "Agent 学习路径"))
        route_episodes.extend(_parse_markdown(rl_path, "RL 学习路径"))
        rss_episodes = _parse_rss(rss_path)
        return cls(rss_episodes, route_episodes=route_episodes)

    def stats(self) -> str:
        rss_count = sum(1 for item in self.episodes if item.source == "RSS")
        route_count = sum(1 for item in self.episodes if "学习路径" in item.stage)
        if rss_count:
            return f"已加载全量 RSS {rss_count} 集，其中 {route_count} 集带学习路线标注。"
        return f"未加载全量 RSS，当前仅有路线标注 {len(self.episodes)} 集。请先刷新 RSS。"

    def search(self, query: str, limit: int = 8) -> list[SearchResult]:
        terms = _query_terms(query)
        phrases = _query_phrases(query)
        wants_recent = _wants_recent(query)
        topic_terms = [term for term in terms if not _is_recent_only_token(term)]
        topic_phrases = [phrase for phrase in phrases if not _is_recent_only_token(phrase)]
        has_topic_filter = bool(topic_terms or topic_phrases)
        wants_agent = any(term in topic_terms for term in ("agent", "智能体", "工具", "工作流", "飞书"))
        wants_rl = any(term in topic_terms for term in ("强化学习", "rl", "reward", "grpo", "dpo", "sft"))

        results: list[SearchResult] = []
        for episode in self.episodes:
            text = episode.searchable_text
            score = 0.0
            matched_topic = not has_topic_filter
            if "学习路径" in episode.stage:
                score += 0.2 if wants_recent else 1.5
            if wants_agent and "Agent 学习路径" in episode.stage:
                score += 0.5 if wants_recent else 4.0
            if wants_rl and "RL 学习路径" in episode.stage:
                score += 0.5 if wants_recent else 4.0
            if wants_recent:
                score += max(0.0, 8.0 - (episode.order - 1) * 0.008)

            title = episode.title.lower()
            note = episode.note.lower()
            for phrase in topic_phrases:
                if phrase in title:
                    score += 30.0
                    matched_topic = True
                elif phrase in note:
                    score += 15.0
                    matched_topic = True
                elif phrase in text:
                    score += 8.0
                    matched_topic = True

            for term in topic_terms:
                if term in title:
                    score += 8.0
                    matched_topic = True
                if term in episode.stage.lower():
                    score += 5.0
                    matched_topic = True
                if term in episode.note.lower():
                    score += 3.0
                    matched_topic = True
                if term in episode.summary.lower():
                    score += 1.0
                    matched_topic = True
                if term and term in text:
                    score += 0.5
                    matched_topic = True

            if score > 0 and matched_topic:
                results.append(SearchResult(episode=episode, score=score))

        if wants_recent:
            results.sort(key=lambda item: (item.episode.order, -item.score))
        else:
            results.sort(key=lambda item: (-item.score, item.episode.order))
        deduped: list[SearchResult] = []
        seen_ids: set[str] = set()
        seen_urls: set[str] = set()
        for result in results:
            if result.episode.id in seen_ids or result.episode.url in seen_urls:
                continue
            seen_ids.add(result.episode.id)
            seen_urls.add(result.episode.url)
            deduped.append(result)
            if len(deduped) >= limit:
                break
        return deduped

    def first_round(self, topic: str, limit: int = 10) -> list[Episode]:
        topic_lower = topic.lower()
        if "rl" in topic_lower or "强化" in topic_lower or "grpo" in topic_lower or "dpo" in topic_lower:
            source = "RL 学习路径"
        else:
            source = "Agent 学习路径"

        route_items = [episode for episode in self.route_episodes if episode.source == source]
        route_items.sort(key=lambda item: item.order)
        by_url = {episode.url: episode for episode in self.episodes}
        return [by_url.get(episode.url, episode) for episode in route_items[:limit]]

    def episodes_for_theme(self, theme: str, exclude_ids: set[str] | None = None) -> list[Episode]:
        exclude = exclude_ids or set()
        terms = THEME_BUCKETS.get(theme)
        if terms:
            matched = [
                episode
                for episode in self.episodes
                if any(term in episode.searchable_text for term in terms)
            ]
        else:
            matched = [result.episode for result in self.search(theme, limit=50)]
        matched = [episode for episode in matched if episode.id not in exclude]
        matched.sort(key=lambda episode: episode.order)
        return matched

    def candidate_themes(
        self,
        recent_window: int = 60,
        exclude_theme: str = "",
        pushed_ids: set[str] | None = None,
        min_unpushed: int = 5,
        top: int = 3,
    ) -> list[str]:
        pushed = pushed_ids or set()
        recent = [
            episode
            for episode in self.episodes
            if episode.source == "RSS" and episode.order <= recent_window
        ] or list(self.episodes)

        ranked: list[tuple[int, str]] = []
        for theme, terms in THEME_BUCKETS.items():
            if theme == exclude_theme:
                continue
            hits = sum(
                1 for episode in recent if any(term in episode.searchable_text for term in terms)
            )
            unpushed = len(self.episodes_for_theme(theme, exclude_ids=pushed))
            if hits > 0 and unpushed >= min_unpushed:
                ranked.append((hits, theme))

        ranked.sort(key=lambda item: -item[0])
        return [theme for _, theme in ranked[:top]]

    def find_episode(self, identifier: str) -> Episode | None:
        value = identifier.strip()
        if not value:
            return None
        value_lower = value.lower()
        normalized_value = _normalize_title(value)

        for episode in self.episodes:
            if value == episode.id or value == episode.url:
                return episode
            if value_lower == episode.title.lower():
                return episode

        for episode in self.episodes:
            normalized_title = _normalize_title(episode.title)
            if normalized_value and (
                normalized_value in normalized_title or normalized_title in normalized_value
            ):
                return episode
        return None


def _normalize_title(value: str) -> str:
    return re.sub(r"[\s《》「」“”\"'：:，,。.!！?？\-—_()（）【】\[\]]+", "", value.lower())


def format_episode_detail(episode: Episode) -> str:
    lines = [
        f"标题：{episode.title}",
        f"id：{episode.id}",
        f"链接：{episode.url}",
        f"来源：{episode.source}",
        f"位置：{episode.stage or '未标注'}",
    ]
    if episode.published:
        lines.append(f"发布时间：{episode.published}")
    if episode.note:
        lines.append(f"路线标注：{episode.note}")
    if episode.summary:
        lines.append(f"RSS 简介：{episode.summary}")
    return "\n".join(lines)


def format_context(results: list[SearchResult]) -> str:
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        episode = result.episode
        lines.append(
            "\n".join(
                [
                    f"{index}. {episode.title}",
                    f"来源：{episode.source} / {episode.stage}",
                    f"链接：{episode.url}",
                    f"推荐理由：{episode.note or episode.summary or '暂无额外摘要。'}",
                ]
            )
        )
    return "\n\n".join(lines)


def learning_task_for_episode(episode: Episode) -> str:
    text = episode.searchable_text
    if any(token in text for token in ("rag", "search", "搜索", "research", "检索")):
        return "它把“找资料”拆成了哪些动作？哪些动作适合你的飞书机器人？"
    if any(token in text for token in ("reward", "奖励", "rl", "grpo", "dpo", "sft", "偏好")):
        return "这里的任务、动作、奖励/偏好信号分别是什么？它和 SFT 有什么差别？"
    if any(token in text for token in ("记忆", "复盘", "反思", "小抄")):
        return "哪些信息值得进长期记忆，哪些只该留在当前对话？"
    if any(token in text for token in ("安全", "评估", "验证", "裁判", "成本")):
        return "它用什么办法判断 Agent 做得好不好？失败时怎么兜底？"
    if any(token in text for token in ("工具", "行动", "工作流", "tool")):
        return "它调用了什么工具？工具输入输出能不能被程序稳定解析？"
    return "它解决什么任务、关键机制是什么、能不能迁移到你的项目？"
