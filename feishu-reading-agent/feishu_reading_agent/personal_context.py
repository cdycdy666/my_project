from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CONTEXT_FILES = (
    ("90-context/CURRENT_CONTEXT.md", 1200),
    ("90-context/PROFILE.md", 800),
)

EVIDENCE_SECTION_KEYWORDS = (
    "今日概览",
    "发生了什么",
    "今天遇到的问题",
    "我做出的判断",
    "为什么这么判断",
    "判断依据",
    "结果",
    "反馈",
    "还没解决",
    "明天要推进",
    "后续动作",
    "值得沉淀",
    "得以沉淀",
    "给 AI",
    "给AI",
    "长期上下文",
)

QUERY_KEYWORDS = (
    "Obsidian",
    "daily note",
    "personal-kb",
    "知识库",
    "上下文",
    "长期记忆",
    "反馈闭环",
    "飞书",
    "如流",
    "OpenClaw",
    "微信读书",
    "读书",
    "沟通",
    "分手",
    "关系",
    "机器人",
    "自动化",
    "服务器",
    "阿里云",
    "GitHub",
    "Git",
    "大模型",
    "GAM",
    "memory",
)
QUERY_KEYWORD_SET = {keyword.lower() for keyword in QUERY_KEYWORDS}


def _read_optional(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[:max_chars]


def _load_memory_indexes(vault_dir: Path, limit: int = 14) -> list[dict[str, Any]]:
    index_dir = vault_dir / "90-context" / "memory-index"
    if not index_dir.exists():
        return []

    indexes: list[dict[str, Any]] = []
    for path in sorted(index_dir.glob("*.json"), reverse=True)[:limit]:
        if path.name == "README.md":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            data["_index_path"] = path
            indexes.append(data)
    return indexes


def _query_terms(query: str) -> list[str]:
    normalized = query.strip().lower()
    terms: list[str] = []
    for keyword in QUERY_KEYWORDS:
        if keyword.lower() in normalized:
            terms.append(keyword.lower())

    for token in re.findall(r"[A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,}", normalized):
        if token not in terms:
            terms.append(token)
    return terms[:20]


def _index_text(index: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "date",
        "summary",
        "topics",
        "people",
        "overview",
        "problems",
        "decisions",
        "decision_basis",
        "feedback",
        "open_loops",
        "next_steps",
        "lessons",
        "ai_notes",
    ):
        value = index.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return "\n".join(parts).lower()


def _score_index(index: dict[str, Any], query: str) -> int:
    terms = _query_terms(query)
    if not terms:
        return 0

    text = _index_text(index)
    score = 0
    for term in terms:
        if term in text:
            score += 3 if term in QUERY_KEYWORD_SET else 1
    return score


def _select_memory_indexes(indexes: list[dict[str, Any]], query: str, limit: int = 4) -> list[dict[str, Any]]:
    if not indexes:
        return []

    if not query.strip():
        return indexes[:limit]

    scored = [(index, _score_index(index, query)) for index in indexes]
    relevant = [item for item in sorted(scored, key=lambda item: item[1], reverse=True) if item[1] > 0]
    selected = [index for index, _score in relevant[:limit]]

    # Keep a little recency even when the query is broad, but do not pad all the
    # way to the old 5-note raw context. The memory index is the default context.
    for index in indexes[:2]:
        if len(selected) >= limit:
            break
        if index not in selected:
            selected.append(index)

    return selected


def _format_list(value: Any, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    items = [str(item).strip() for item in value if str(item).strip()][:limit]
    return "\n".join(f"- {item}" for item in items)


def _format_memory_indexes(indexes: list[dict[str, Any]], max_total_chars: int = 5000) -> str:
    if not indexes:
        return ""

    chunks = [
        "说明：这是从 daily note 生成的轻量记忆索引，用于给读书推荐提供处境摘要；具体事实仍以 source_pages 原文为准。"
    ]
    total_chars = len(chunks[0])
    for index in indexes:
        lines = [
            f"### {index.get('date', 'unknown')} ({index.get('page_id', 'unknown')})",
            f"source_pages: {', '.join(index.get('source_pages', []) or [])}",
        ]
        if index.get("topics"):
            lines.append(f"topics: {', '.join(index['topics'])}")
        if index.get("people"):
            lines.append(f"people: {', '.join(index['people'])}")
        if index.get("summary"):
            lines.append(f"summary: {index['summary']}")

        for key, label in (
            ("overview", "overview"),
            ("decisions", "decisions"),
            ("open_loops", "open_loops"),
            ("next_steps", "next_steps"),
            ("lessons", "lessons"),
        ):
            formatted = _format_list(index.get(key))
            if formatted:
                lines.append(f"{label}:\n{formatted}")

        chunk = "\n".join(lines)
        if total_chars + len(chunk) > max_total_chars:
            break
        chunks.append(chunk)
        total_chars += len(chunk)

    return "\n\n".join(chunks)


def _source_paths_from_indexes(indexes: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for index in indexes:
        for path in index.get("source_pages", []) or []:
            if isinstance(path, str) and path not in paths:
                paths.append(path)
    return paths


def _recent_daily_notes(
    vault_dir: Path,
    limit: int = 2,
    max_total_chars: int = 3000,
    preferred_paths: list[str] | None = None,
) -> str:
    daily_dir = vault_dir / "10-daily"
    if not daily_dir.exists():
        return ""

    ordered_paths: list[Path] = []
    for relative_path in preferred_paths or []:
        path = vault_dir / relative_path
        if path.exists() and path.suffix == ".md" and path not in ordered_paths:
            ordered_paths.append(path)

    for path in sorted(daily_dir.glob("*/*.md"), reverse=True):
        if path not in ordered_paths:
            ordered_paths.append(path)

    chunks: list[str] = []
    total_chars = 0
    for path in ordered_paths[:limit]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        chunk = f"--- {path.name} ---\n{text[:1200]}"
        if total_chars + len(chunk) > max_total_chars:
            break
        chunks.append(chunk)
        total_chars += len(chunk)
    return "\n\n".join(chunks)


def _daily_evidence_excerpt(path: Path, max_chars: int = 2200) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""

    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if match:
            if current_heading:
                sections.append((current_heading, current_lines))
            current_heading = match.group(1).strip()
            current_lines = []
            continue
        if current_heading:
            current_lines.append(line)

    if current_heading:
        sections.append((current_heading, current_lines))

    chunks: list[str] = []
    total_chars = 0
    for heading, lines in sections:
        if not any(keyword in heading for keyword in EVIDENCE_SECTION_KEYWORDS):
            continue
        body = "\n".join(line for line in lines).strip()
        if not body:
            continue
        chunk = f"### {heading}\n{body[:700]}"
        if total_chars + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        total_chars += len(chunk)

    if not chunks:
        return text[:max_chars]
    return "\n\n".join(chunks)


def _format_sources(indexes: list[dict[str, Any]]) -> str:
    paths = _source_paths_from_indexes(indexes)
    if not paths:
        return ""
    return "\n".join(f"- {path}" for path in paths)


def read_personal_context(
    vault_dir: Path,
    daily_limit: int = 4,
    query: str = "",
    include_daily_notes: bool = False,
) -> str:
    chunks: list[str] = ["## PersonalContextBundle\n说明：这是为本次读书建议构造的个人处境摘要，不是完整 daily note 原文。"]

    memory_indexes = _load_memory_indexes(vault_dir)
    selected_indexes = _select_memory_indexes(memory_indexes, query, limit=daily_limit)
    formatted_indexes = _format_memory_indexes(selected_indexes)
    if formatted_indexes:
        chunks.append(f"## 当前处境摘要（memory-index）\n{formatted_indexes}")

    sources = _format_sources(selected_indexes)
    if sources:
        chunks.append(f"## 可追溯来源\n{sources}")

    for relative_path, max_chars in CONTEXT_FILES:
        text = _read_optional(vault_dir / relative_path, max_chars=max_chars)
        if text:
            chunks.append(f"## 长期背景：{relative_path}\n{text}")

    if include_daily_notes:
        preferred_paths = _source_paths_from_indexes(selected_indexes)
        recent_daily = _recent_daily_notes(vault_dir, limit=2, preferred_paths=preferred_paths)
        if recent_daily:
            chunks.append(f"## 相关 daily note 摘录\n{recent_daily}")

    return "\n\n".join(chunks).strip()


def read_personal_evidence_context(
    vault_dir: Path,
    query: str = "",
    daily_limit: int = 2,
    max_total_chars: int = 4500,
) -> str:
    memory_indexes = _load_memory_indexes(vault_dir)
    selected_indexes = _select_memory_indexes(memory_indexes, query, limit=daily_limit)
    source_paths = _source_paths_from_indexes(selected_indexes)
    if not source_paths:
        return ""

    chunks = [
        "说明：以下是根据 memory-index 的 source_pages 回读的 daily note 关键原文片段，用于判断候选阅读材料和真实处境的贴合度。"
    ]
    total_chars = len(chunks[0])
    for relative_path in source_paths[:daily_limit]:
        path = vault_dir / relative_path
        if not path.exists() or path.suffix != ".md":
            continue
        excerpt = _daily_evidence_excerpt(path)
        if not excerpt:
            continue
        chunk = f"## {relative_path}\n{excerpt}"
        if total_chars + len(chunk) > max_total_chars:
            break
        chunks.append(chunk)
        total_chars += len(chunk)

    return "\n\n".join(chunks).strip() if len(chunks) > 1 else ""
