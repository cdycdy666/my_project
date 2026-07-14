from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from feishu_reading_agent.tools import ReadPersonalContextTool, ReadPersonalEvidenceTool, ToolContext


class FakeResearchResult:
    planned_queries = ["推荐阅读", "当前处境"]
    rounds = 1
    hits = [object()]
    evidence = [object()]
    sufficient = True
    warnings: list[str] = []

    def summary_context(self) -> str:
        return "hybrid summary"

    def evidence_context(self) -> str:
        return "page-id evidence"


class FakeResearcher:
    calls = 0

    def __init__(self, config: object) -> None:
        self.config = config

    def research(self, message: str, trace: object = None) -> FakeResearchResult:
        FakeResearcher.calls += 1
        return FakeResearchResult()


class MemoryResearcherAdapterTest(unittest.TestCase):
    def test_context_and_evidence_share_one_research_result(self) -> None:
        FakeResearcher.calls = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SimpleNamespace(
                memory_research_enabled=True,
                memory_embedding_api_key="key",
                memory_embedding_base_url="https://example.invalid/v1",
                memory_embedding_model="embedding-test",
                memory_embedding_dimensions=3,
                memory_research_cache_dir=Path(temp_dir),
                memory_research_max_rounds=2,
                personal_kb_dir=Path(temp_dir),
                llm_api_key="",
                llm_base_url="",
                llm_model="",
            )
            context = ToolContext(config=config)
            with patch("feishu_reading_agent.tools.MemoryResearcher", FakeResearcher):
                summary = ReadPersonalContextTool().run(context, message="推荐阅读")
                evidence = ReadPersonalEvidenceTool().run(context, message="推荐阅读")

        self.assertEqual(FakeResearcher.calls, 1)
        self.assertEqual(summary.content, "hybrid summary")
        self.assertEqual(evidence.content, "page-id evidence")
        self.assertEqual(summary.metadata["methods"], ["bm25", "embedding", "page_id"])


if __name__ == "__main__":
    unittest.main()
