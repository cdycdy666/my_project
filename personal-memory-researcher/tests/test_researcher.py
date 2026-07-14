from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_memory_researcher import MemoryResearcher, ResearcherConfig


class FakeEmbeddingProvider:
    @staticmethod
    def _vector(text: str) -> list[float]:
        normalized = text.lower()
        return [
            float(sum(normalized.count(term) for term in ("服务器", "迁移", "任务", "飞书"))),
            float(sum(normalized.count(term) for term in ("分手", "关系", "沟通"))),
            1.0,
        ]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


class RecordingTrace:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def event(self, event_type: str, **payload: object) -> None:
        self.events.append((event_type, payload))


class MemoryResearcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name)
        (self.vault / "90-context" / "memory-index").mkdir(parents=True)
        (self.vault / "00-inbox" / "feishu" / "2026").mkdir(parents=True)
        (self.vault / "90-context").mkdir(exist_ok=True)
        (self.vault / "90-context" / "CURRENT_CONTEXT.md").write_text(
            "当前重点是让个人 Agent 在服务器上稳定运行。",
            encoding="utf-8",
        )
        inbox_path = self.vault / "00-inbox" / "feishu" / "2026" / "2026-07-15.md"
        inbox_path.write_text(
            """## 09:00 记录
<!-- record_id: feishu-target -->
我把飞书自动化迁移到了阿里云服务器，现在要确认定时任务和常驻服务是否稳定。

## 10:00 记录
<!-- record_id: feishu-other -->
最近分手后在思考如何减少关系里的沟通压力。
""",
            encoding="utf-8",
        )
        index = {
            "schema_version": 2,
            "page_id": "daily-2026-07-15",
            "date": "2026-07-15",
            "summary": "服务器迁移与关系恢复",
            "topics": ["飞书自动化", "关系恢复"],
            "source_pages": ["00-inbox/feishu/2026/2026-07-15.md"],
            "events": [
                {
                    "event_id": "event-server-migration",
                    "title": "飞书服务迁移到服务器",
                    "summary": "迁移后检查常驻监听和定时任务是否稳定。",
                    "problems": ["服务器任务稳定性"],
                    "source_record_ids": ["feishu-target"],
                },
                {
                    "event_id": "event-breakup",
                    "title": "关系恢复",
                    "summary": "分手后减少沟通压力。",
                    "source_record_ids": ["feishu-other"],
                },
            ],
        }
        (self.vault / "90-context" / "memory-index" / "2026-07-15.json").write_text(
            json.dumps(index, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_hybrid_search_and_page_id_readback(self) -> None:
        trace = RecordingTrace()
        researcher = MemoryResearcher(
            ResearcherConfig(
                vault_dir=self.vault,
                embedding_api_key="unused",
                embedding_base_url="https://example.invalid/v1",
                embedding_cache_path=self.vault / "cache.json",
                max_rounds=2,
            ),
            embedding_provider=FakeEmbeddingProvider(),
        )

        result = researcher.research("飞书迁移到服务器后任务是否稳定", trace=trace)

        self.assertTrue(result.hits)
        self.assertEqual(result.hits[0].document.document_id, "event-server-migration")
        self.assertIn("bm25", result.hits[0].methods)
        self.assertIn("embedding", result.hits[0].methods)
        self.assertTrue(result.evidence)
        self.assertIn("阿里云服务器", result.evidence[0].content)
        self.assertNotIn("分手后", result.evidence[0].content)
        self.assertIn("record-ID", result.evidence_context())

        event_names = [name for name, _payload in trace.events]
        self.assertIn("memory_bm25_search", event_names)
        self.assertIn("memory_vector_search", event_names)
        self.assertIn("memory_hybrid_fusion", event_names)
        self.assertIn("memory_page_id_retrieval", event_names)
        self.assertIn("memory_research_complete", event_names)


if __name__ == "__main__":
    unittest.main()
