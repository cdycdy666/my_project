from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Protocol

from .models import MemoryDocument, SearchHit


def tokenize(text: str) -> list[str]:
    normalized = text.lower()
    tokens = re.findall(r"[a-z0-9_.-]{2,}", normalized)
    for segment in re.findall(r"[\u4e00-\u9fff]+", normalized):
        if len(segment) <= 2:
            tokens.append(segment)
            continue
        tokens.append(segment)
        tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


class BM25Retriever:
    def __init__(self, documents: list[MemoryDocument], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(document.text) for document in documents]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.frequencies = [Counter(tokens) for tokens in self.tokens]
        document_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            document_frequency.update(set(tokens))
        total = max(len(documents), 1)
        self.idf = {
            token: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def search(self, query: str, limit: int = 8) -> list[tuple[MemoryDocument, float]]:
        query_tokens = tokenize(query)
        scored: list[tuple[MemoryDocument, float]] = []
        for index, document in enumerate(self.documents):
            score = 0.0
            frequencies = self.frequencies[index]
            length = self.lengths[index]
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(self.average_length, 1)
                )
                score += self.idf.get(token, 0.0) * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append((document, score))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


_CACHE_LOCK = threading.RLock()


class OpenAICompatibleEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimensions: int,
        cache_path: Path,
        timeout: int = 90,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.cache_path = cache_path
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("memory embedding API key is not configured")
        cache = self._load_cache()
        vectors: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            cache_key = self._cache_key(text)
            cached = cache.get(cache_key)
            if isinstance(cached, list) and cached:
                vectors[index] = [float(value) for value in cached]
            else:
                missing.append((index, cache_key, text))

        for offset in range(0, len(missing), 10):
            batch = missing[offset : offset + 10]
            embedded = self._request([text for _index, _key, text in batch])
            if len(embedded) != len(batch):
                raise RuntimeError("embedding API returned an unexpected vector count")
            for (index, cache_key, _text), vector in zip(batch, embedded):
                vectors[index] = vector
                cache[cache_key] = vector

        if missing:
            self._save_cache(cache)
        return [vector or [] for vector in vectors]

    def _request(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        if self.dimensions > 0:
            payload["dimensions"] = self.dimensions
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"embedding API failed: HTTP {exc.code} {body[:800]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise RuntimeError(f"embedding API failed: {exc}") from exc

        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise RuntimeError("embedding API response has no data list")
        ordered = sorted((row for row in rows if isinstance(row, dict)), key=lambda row: int(row.get("index", 0)))
        return [
            [float(value) for value in row.get("embedding", [])]
            for row in ordered
        ]

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.model}:{self.dimensions}:{digest}"

    def _load_cache(self) -> dict[str, list[float]]:
        with _CACHE_LOCK:
            if not self.cache_path.exists():
                return {}
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
            items = data.get("items") if isinstance(data, dict) else None
            return items if isinstance(items, dict) else {}

    def _save_cache(self, items: dict[str, list[float]]) -> None:
        with _CACHE_LOCK:
            latest = self._load_cache()
            latest.update(items)
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps({"schema_version": 1, "items": latest}, ensure_ascii=False),
                encoding="utf-8",
            )
            temp_path.replace(self.cache_path)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


class DenseRetriever:
    def __init__(self, documents: list[MemoryDocument], provider: EmbeddingProvider) -> None:
        self.documents = documents
        self.provider = provider
        self._document_vectors: list[list[float]] | None = None

    def search(self, query: str, limit: int = 8) -> list[tuple[MemoryDocument, float]]:
        if self._document_vectors is None:
            self._document_vectors = self.provider.embed([document.text for document in self.documents])
        query_vector = self.provider.embed([query])[0]
        scored = [
            (document, cosine_similarity(query_vector, vector))
            for document, vector in zip(self.documents, self._document_vectors)
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


def reciprocal_rank_fusion(
    bm25_results: list[tuple[MemoryDocument, float]],
    vector_results: list[tuple[MemoryDocument, float]],
    limit: int = 6,
    rank_constant: int = 60,
) -> list[SearchHit]:
    hits: dict[str, SearchHit] = {}
    for method, results in (("bm25", bm25_results), ("embedding", vector_results)):
        for rank, (document, raw_score) in enumerate(results, start=1):
            hit = hits.setdefault(document.document_id, SearchHit(document=document))
            hit.fused_score += 1.0 / (rank_constant + rank)
            if method == "bm25":
                hit.bm25_score = raw_score
            else:
                hit.vector_score = raw_score
            if method not in hit.methods:
                hit.methods.append(method)
    return sorted(hits.values(), key=lambda hit: hit.fused_score, reverse=True)[:limit]
