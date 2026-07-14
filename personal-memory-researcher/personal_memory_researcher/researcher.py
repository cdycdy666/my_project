from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import MemoryDocument, MemoryEvidence, MemoryResearchResult, SearchHit
from .retrieval import (
    BM25Retriever,
    DenseRetriever,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingClient,
    reciprocal_rank_fusion,
)
from .store import MemoryStore


PLANNER_PROMPT = """你是个人长期记忆系统的检索规划器。
根据用户请求和可用记忆概览，生成最多 3 个用于检索历史记录的查询。
查询应覆盖用户原话、可能的同义表达，以及必要的时间/人物/项目限定。
只输出 JSON：{"queries":["..."],"reason":"..."}。
不要回答用户问题，不要编造记忆内容。"""

REFLECTION_PROMPT = """你是个人长期记忆系统的检索反思器。
判断当前检索到的来源是否足以支撑下游 Agent 理解用户处境。
如果信息不足，指出缺什么，并提供最多 2 个补充检索 query。
只输出 JSON：
{"sufficient":true,"missing_information":[],"refined_queries":[],"reason":"..."}
不要根据常识补事实，只评估给定来源。"""


@dataclass(frozen=True)
class ResearcherConfig:
    vault_dir: Path
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = 1024
    embedding_cache_path: Path = Path("data/memory-embeddings.json")
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    max_rounds: int = 2
    search_limit: int = 8
    fused_limit: int = 5
    max_pages: int = 5


def _emit(trace: Any, event: str, **payload: Any) -> None:
    if not trace or not hasattr(trace, "event"):
        return
    try:
        trace.event(event, **payload)
    except Exception:
        pass


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response is not a JSON object")
    return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


class MemoryResearcher:
    def __init__(
        self,
        config: ResearcherConfig,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.config = config
        self.store = MemoryStore(config.vault_dir)
        self.embedding_provider = embedding_provider or OpenAICompatibleEmbeddingClient(
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            model=config.embedding_model,
            dimensions=config.embedding_dimensions,
            cache_path=config.embedding_cache_path,
        )

    def research(self, query: str, trace: Any = None) -> MemoryResearchResult:
        documents = self.store.load_documents()
        if not documents:
            return MemoryResearchResult(
                query=query,
                planned_queries=[query],
                hits=[],
                evidence=[],
                baseline_context=self.store.baseline_context(),
                sufficient=False,
                missing_information=["personal-kb 中没有可检索的 memory-index"],
                warnings=["empty_memory_index"],
            )

        _emit(
            trace,
            "memory_research_start",
            query=query,
            document_count=len(documents),
            retrieval_methods=["bm25", "embedding", "page_id"],
        )
        warnings: list[str] = []
        planned_queries = self._plan_queries(query, documents, trace, warnings)
        bm25 = BM25Retriever(documents)
        dense = DenseRetriever(documents, self.embedding_provider)
        hit_map: dict[str, SearchHit] = {}
        evidence_map: dict[str, MemoryEvidence] = {}
        missing_information: list[str] = []
        sufficient = False
        rounds_run = 0
        current_queries = planned_queries[:]

        for round_number in range(1, max(1, self.config.max_rounds) + 1):
            rounds_run = round_number
            _emit(trace, "memory_research_round", round=round_number, queries=current_queries)
            bm25_results: list[tuple[MemoryDocument, float]] = []
            vector_results: list[tuple[MemoryDocument, float]] = []
            for planned_query in current_queries:
                local_bm25 = bm25.search(planned_query, limit=self.config.search_limit)
                bm25_results.extend(local_bm25)
                _emit(
                    trace,
                    "memory_bm25_search",
                    round=round_number,
                    query=planned_query,
                    results=[{"document_id": doc.document_id, "score": score} for doc, score in local_bm25],
                )
                try:
                    local_vector = dense.search(planned_query, limit=self.config.search_limit)
                    vector_results.extend(local_vector)
                    _emit(
                        trace,
                        "memory_vector_search",
                        round=round_number,
                        query=planned_query,
                        model=self.config.embedding_model,
                        results=[{"document_id": doc.document_id, "score": score} for doc, score in local_vector],
                    )
                except Exception as exc:
                    warning = f"embedding search failed: {exc}"
                    if warning not in warnings:
                        warnings.append(warning)
                    _emit(trace, "memory_vector_search_error", round=round_number, query=planned_query, error=str(exc))

            fused = reciprocal_rank_fusion(
                self._merge_results(bm25_results),
                self._merge_results(vector_results),
                limit=self.config.fused_limit,
            )
            self._merge_hits(hit_map, fused)
            ranked_hits = sorted(hit_map.values(), key=lambda hit: hit.fused_score, reverse=True)[: self.config.fused_limit]
            _emit(trace, "memory_hybrid_fusion", round=round_number, hits=[hit.as_dict() for hit in ranked_hits])

            evidence = self.store.read_hits(
                ranked_hits,
                max_pages=self.config.max_pages,
            )
            for item in evidence:
                evidence_map[item.evidence_id] = item
            _emit(
                trace,
                "memory_page_id_retrieval",
                round=round_number,
                document_ids=[hit.document.document_id for hit in ranked_hits],
                evidence=[item.as_dict() for item in evidence],
            )

            sufficient, missing_information, refined_queries = self._reflect(
                query,
                ranked_hits,
                list(evidence_map.values()),
                round_number,
                trace,
                warnings,
            )
            if sufficient or round_number >= self.config.max_rounds:
                break
            current_queries = [item for item in refined_queries if item and item not in planned_queries][:2]
            if not current_queries:
                break
            planned_queries.extend(current_queries)

        hits = sorted(hit_map.values(), key=lambda hit: hit.fused_score, reverse=True)[: self.config.fused_limit]
        result = MemoryResearchResult(
            query=query,
            planned_queries=planned_queries,
            hits=hits,
            evidence=list(evidence_map.values()),
            baseline_context=self.store.baseline_context(),
            rounds=rounds_run,
            sufficient=sufficient,
            missing_information=missing_information,
            warnings=warnings,
        )
        _emit(
            trace,
            "memory_research_complete",
            rounds=result.rounds,
            sufficient=result.sufficient,
            hit_count=len(result.hits),
            evidence_count=len(result.evidence),
            planned_queries=result.planned_queries,
            warnings=result.warnings,
            summary_context=result.summary_context(),
            evidence_context=result.evidence_context(),
        )
        return result

    def _plan_queries(
        self,
        query: str,
        documents: list[MemoryDocument],
        trace: Any,
        warnings: list[str],
    ) -> list[str]:
        overview = "\n".join(
            f"- {document.document_id} | {document.date} | {document.title}"
            for document in documents[:60]
        )
        if not self.config.llm_api_key or not self.config.llm_model:
            _emit(trace, "memory_query_plan", query=query, queries=[query], reason="LLM planner is not configured")
            return [query]
        try:
            value = self._chat_json(
                PLANNER_PROMPT,
                f"用户请求：\n{query}\n\n可用记忆概览：\n{overview}",
                trace,
                purpose="memory_query_planning",
            )
            raw_queries = value.get("queries")
            queries = [str(item).strip() for item in raw_queries if str(item).strip()] if isinstance(raw_queries, list) else []
            planned = list(dict.fromkeys([query, *queries]))[:3]
            _emit(trace, "memory_query_plan", query=query, queries=planned, reason=str(value.get("reason") or ""))
            return planned
        except Exception as exc:
            warnings.append(f"memory query planning failed: {exc}")
            _emit(trace, "memory_query_plan_error", query=query, error=str(exc))
            return [query]

    def _reflect(
        self,
        query: str,
        hits: list[SearchHit],
        evidence: list[MemoryEvidence],
        round_number: int,
        trace: Any,
        warnings: list[str],
    ) -> tuple[bool, list[str], list[str]]:
        if not evidence:
            _emit(
                trace,
                "memory_research_reflection",
                round=round_number,
                sufficient=False,
                missing_information=["没有回读到可用原文"],
                refined_queries=[query],
                reason="Page-ID retrieval returned no evidence",
            )
            return False, ["没有回读到可用原文"], [query]
        if not self.config.llm_api_key or not self.config.llm_model:
            _emit(
                trace,
                "memory_research_reflection",
                round=round_number,
                sufficient=True,
                missing_information=[],
                refined_queries=[],
                reason="Deterministic fallback accepted retrieved source evidence",
            )
            return True, [], []
        evidence_text = "\n\n".join(
            f"[{item.evidence_id}] {item.source_page}\n{item.content[:1200]}"
            for item in evidence[: self.config.max_pages]
        )
        try:
            value = self._chat_json(
                REFLECTION_PROMPT,
                f"用户请求：\n{query}\n\n当前命中：\n{json.dumps([hit.as_dict() for hit in hits], ensure_ascii=False)}\n\n原文证据：\n{evidence_text}",
                trace,
                purpose="memory_research_reflection",
            )
            sufficient = _as_bool(value.get("sufficient"))
            raw_missing = value.get("missing_information")
            missing = [str(item).strip() for item in raw_missing if str(item).strip()] if isinstance(raw_missing, list) else []
            raw_queries = value.get("refined_queries")
            refined = [str(item).strip() for item in raw_queries if str(item).strip()] if isinstance(raw_queries, list) else []
            _emit(
                trace,
                "memory_research_reflection",
                round=round_number,
                sufficient=sufficient,
                missing_information=missing,
                refined_queries=refined[:2],
                reason=str(value.get("reason") or ""),
            )
            return sufficient, missing, refined[:2]
        except Exception as exc:
            warnings.append(f"memory reflection failed: {exc}")
            _emit(trace, "memory_research_reflection_error", round=round_number, error=str(exc))
            return True, [], []

    def _chat_json(self, system_prompt: str, user_prompt: str, trace: Any, purpose: str) -> dict[str, Any]:
        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        _emit(trace, "memory_llm_request", purpose=purpose, request_payload=payload)
        request = urllib.request.Request(
            f"{self.config.llm_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"memory LLM failed: HTTP {exc.code} {body[:800]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise RuntimeError(f"memory LLM failed: {exc}") from exc
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("memory LLM returned no choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        text = message.get("content") if isinstance(message, dict) else ""
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("memory LLM returned empty content")
        _emit(trace, "memory_llm_response", purpose=purpose, response_text=text, usage=data.get("usage"))
        return _extract_json(text)

    @staticmethod
    def _merge_results(results: list[tuple[MemoryDocument, float]]) -> list[tuple[MemoryDocument, float]]:
        merged: dict[str, tuple[MemoryDocument, float]] = {}
        for document, score in results:
            current = merged.get(document.document_id)
            if current is None or score > current[1]:
                merged[document.document_id] = (document, score)
        return sorted(merged.values(), key=lambda item: item[1], reverse=True)

    @staticmethod
    def _merge_hits(target: dict[str, SearchHit], incoming: list[SearchHit]) -> None:
        for hit in incoming:
            current = target.get(hit.document.document_id)
            if current is None:
                target[hit.document.document_id] = hit
                continue
            current.fused_score = max(current.fused_score, hit.fused_score)
            current.bm25_score = max(current.bm25_score, hit.bm25_score)
            current.vector_score = max(current.vector_score, hit.vector_score)
            for method in hit.methods:
                if method not in current.methods:
                    current.methods.append(method)
