from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryDocument:
    document_id: str
    page_id: str
    date: str
    title: str
    text: str
    source_pages: tuple[str, ...] = ()
    source_record_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    document: MemoryDocument
    fused_score: float = 0.0
    bm25_score: float = 0.0
    vector_score: float = 0.0
    methods: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document.document_id,
            "page_id": self.document.page_id,
            "date": self.document.date,
            "title": self.document.title,
            "fused_score": round(self.fused_score, 6),
            "bm25_score": round(self.bm25_score, 6),
            "vector_score": round(self.vector_score, 6),
            "methods": self.methods,
            "source_pages": list(self.document.source_pages),
            "source_record_ids": list(self.document.source_record_ids),
        }


@dataclass(frozen=True)
class MemoryEvidence:
    evidence_id: str
    document_id: str
    title: str
    date: str
    source_page: str
    source_record_ids: tuple[str, ...]
    content: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "document_id": self.document_id,
            "title": self.title,
            "date": self.date,
            "source_page": self.source_page,
            "source_record_ids": list(self.source_record_ids),
            "content": self.content,
        }


@dataclass
class MemoryResearchResult:
    query: str
    planned_queries: list[str]
    hits: list[SearchHit]
    evidence: list[MemoryEvidence]
    baseline_context: str = ""
    rounds: int = 1
    sufficient: bool = True
    missing_information: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary_context(self, max_chars: int = 6000) -> str:
        chunks = [
            "## PersonalMemoryResearchBundle",
            f"query: {self.query}",
            "retrieval: BM25 + embedding + page-id",
            f"research_rounds: {self.rounds}",
            f"sufficient: {str(self.sufficient).lower()}",
        ]
        if self.planned_queries:
            chunks.append(f"planned_queries: {', '.join(self.planned_queries)}")
        if self.missing_information:
            chunks.append(f"missing_information: {'；'.join(self.missing_information)}")
        if self.baseline_context:
            chunks.extend(["", "## 稳定背景", self.baseline_context.strip()])

        if self.hits:
            chunks.extend(["", "## 检索命中的轻量记忆"])
        for hit in self.hits:
            document = hit.document
            source_text = ", ".join(document.source_pages)
            chunks.extend(
                [
                    f"### {document.date or '长期'} · {document.title}",
                    f"document_id: {document.document_id}",
                    f"methods: {', '.join(hit.methods)}",
                    f"sources: {source_text}",
                    document.text[:1200].strip(),
                ]
            )
            if len("\n".join(chunks)) >= max_chars:
                break
        return "\n".join(chunks)[:max_chars].strip()

    def evidence_context(self, max_chars: int = 7000) -> str:
        chunks = [
            "## PersonalMemoryEvidence",
            "说明：以下证据由 Page-ID/record-ID 从 personal-kb 原文直接回读；事实以这些来源为准。",
        ]
        for item in self.evidence:
            chunks.extend(
                [
                    "",
                    f"### {item.evidence_id} · {item.date or '长期'} · {item.title}",
                    f"source_page: {item.source_page}",
                    f"source_record_ids: {', '.join(item.source_record_ids) or 'page-level'}",
                    item.content.strip(),
                ]
            )
            if len("\n".join(chunks)) >= max_chars:
                break
        return "\n".join(chunks)[:max_chars].strip()
