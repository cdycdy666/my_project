from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import MemoryDocument, MemoryEvidence, SearchHit


SEARCH_FIELDS = (
    "summary",
    "overview",
    "problems",
    "actions",
    "decisions",
    "decision_basis",
    "feedback",
    "open_loops",
    "next_steps",
    "lessons",
    "ai_notes",
    "topics",
    "people",
)


def _flatten(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [text for item in value for text in _flatten(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _flatten(item)]
    return [str(value)] if value not in (None, "") else []


def _document_text(index: dict[str, Any], event: dict[str, Any] | None = None) -> str:
    source = event if event is not None else index
    chunks: list[str] = []
    for key in SEARCH_FIELDS:
        chunks.extend(_flatten(source.get(key)))
    if event is not None:
        chunks.insert(0, str(event.get("title") or ""))
        chunks.extend(_flatten(index.get("summary")))
        chunks.extend(_flatten(index.get("topics")))
    return "\n".join(dict.fromkeys(chunk for chunk in chunks if chunk)).strip()


class MemoryStore:
    def __init__(self, vault_dir: Path, max_index_files: int = 180) -> None:
        self.vault_dir = vault_dir.expanduser().resolve()
        self.max_index_files = max_index_files

    def load_documents(self) -> list[MemoryDocument]:
        index_dir = self.vault_dir / "90-context" / "memory-index"
        if not index_dir.exists():
            return []

        documents: list[MemoryDocument] = []
        paths = sorted(index_dir.glob("*.json"), reverse=True)[: self.max_index_files]
        for path in paths:
            try:
                index = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(index, dict):
                continue
            documents.extend(self._documents_from_index(index, path))
        return documents

    def _documents_from_index(self, index: dict[str, Any], index_path: Path) -> list[MemoryDocument]:
        page_id = str(index.get("page_id") or index_path.stem)
        date = str(index.get("date") or index_path.stem)
        source_pages = tuple(str(item) for item in index.get("source_pages", []) if isinstance(item, str))
        events = index.get("events")
        documents: list[MemoryDocument] = []
        if isinstance(events, list) and events:
            for position, event in enumerate(events, start=1):
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get("event_id") or f"{page_id}-event-{position}")
                text = _document_text(index, event)
                if not text:
                    continue
                documents.append(
                    MemoryDocument(
                        document_id=event_id,
                        page_id=page_id,
                        date=date,
                        title=str(event.get("title") or f"事件 {position}"),
                        text=text,
                        source_pages=source_pages,
                        source_record_ids=tuple(
                            str(item) for item in event.get("source_record_ids", []) if isinstance(item, str)
                        ),
                        metadata={"schema_version": index.get("schema_version", 1), "index_path": str(index_path)},
                    )
                )
            if documents:
                return documents

        text = _document_text(index)
        if not text:
            return []
        return [
            MemoryDocument(
                document_id=page_id,
                page_id=page_id,
                date=date,
                title=str(index.get("summary") or date)[:120],
                text=text,
                source_pages=source_pages or (str(index.get("path") or ""),),
                source_record_ids=tuple(
                    str(item) for item in index.get("source_record_ids", []) if isinstance(item, str)
                ),
                metadata={"schema_version": index.get("schema_version", 1), "index_path": str(index_path)},
            )
        ]

    def baseline_context(self, max_chars: int = 2600) -> str:
        chunks: list[str] = []
        for relative_path in ("90-context/CURRENT_CONTEXT.md", "90-context/PROFILE.md"):
            path = self._safe_path(relative_path)
            if not path or not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                chunks.append(f"### {relative_path}\n{text}")
            if len("\n\n".join(chunks)) >= max_chars:
                break
        return "\n\n".join(chunks)[:max_chars].strip()

    def read_hits(self, hits: list[SearchHit], max_pages: int = 5, max_chars_per_page: int = 2400) -> list[MemoryEvidence]:
        evidence: list[MemoryEvidence] = []
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for hit in hits:
            document = hit.document
            for relative_path in document.source_pages:
                key = (relative_path, document.source_record_ids)
                if key in seen:
                    continue
                seen.add(key)
                path = self._safe_path(relative_path)
                if not path or not path.exists() or path.suffix.lower() != ".md":
                    continue
                if relative_path.startswith("00-inbox/") and document.source_record_ids:
                    content = self._record_blocks(path, document.source_record_ids, max_chars_per_page)
                else:
                    content = self._page_excerpt(path, document.text, max_chars_per_page)
                if not content:
                    continue
                digest = hashlib.sha1(
                    f"{document.document_id}:{relative_path}:{','.join(document.source_record_ids)}".encode("utf-8")
                ).hexdigest()[:10]
                evidence.append(
                    MemoryEvidence(
                        evidence_id=f"evidence-{digest}",
                        document_id=document.document_id,
                        title=document.title,
                        date=document.date,
                        source_page=relative_path,
                        source_record_ids=document.source_record_ids,
                        content=content,
                    )
                )
                if len(evidence) >= max_pages:
                    return evidence
        return evidence

    def _safe_path(self, relative_path: str) -> Path | None:
        path = (self.vault_dir / relative_path).resolve()
        try:
            path.relative_to(self.vault_dir)
        except ValueError:
            return None
        return path

    @staticmethod
    def _record_blocks(path: Path, record_ids: tuple[str, ...], max_chars: int) -> str:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        wanted = set(record_ids)
        selected: list[str] = []
        for block in re.split(r"(?=^##\s+)", text, flags=re.MULTILINE):
            match = re.search(r"<!--\s*record_id:\s*([^>]+?)\s*-->", block, flags=re.IGNORECASE)
            if not match or match.group(1).strip() not in wanted:
                continue
            cleaned = re.sub(r"\n?### AI提取事实（草稿，需用户原文支持）[\s\S]*$", "", block).strip()
            if cleaned:
                selected.append(cleaned)
            if len("\n\n".join(selected)) >= max_chars:
                break
        return "\n\n".join(selected)[:max_chars].strip()

    @staticmethod
    def _page_excerpt(path: Path, query_text: str, max_chars: int) -> str:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return ""
        terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,}", query_text)[:30]]
        blocks = re.split(r"(?=^#{2,3}\s+)", text, flags=re.MULTILINE)
        ranked = sorted(
            blocks,
            key=lambda block: sum(1 for term in terms if term in block.lower()),
            reverse=True,
        )
        selected: list[str] = []
        for block in ranked:
            block = block.strip()
            if not block:
                continue
            selected.append(block)
            if len("\n\n".join(selected)) >= max_chars:
                break
        return "\n\n".join(selected)[:max_chars].strip()
