from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "feishu-obsidian-capture"))
sys.path.insert(0, str(PROJECT_ROOT / "feishu-reading-agent"))

from feishu_obsidian_capture.llm import _normalize_summary_source_comments
from feishu_obsidian_capture.obsidian import append_feishu_inbox_message
from feishu_reading_agent.personal_context import read_personal_evidence_context


def _load_memory_builder():
    path = PROJECT_ROOT / "personal-kb" / "scripts" / "build_memory_index.py"
    spec = importlib.util.spec_from_file_location("personal_kb_memory_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GamMemoryFlowTest(unittest.TestCase):
    def test_record_metadata_and_source_whitelist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            path = append_feishu_inbox_message(
                vault,
                "服务器迁移已经完成。",
                date_text="2026-07-14",
                session_title="服务器迁移",
                record_id="feishu-om_valid",
                session_id="session-1",
            )
            raw = path.read_text(encoding="utf-8")
            self.assertIn("<!-- record_id: feishu-om_valid -->", raw)
            self.assertIn("<!-- session_id: session-1 -->", raw)

            summary = "## 事件 1：迁移\n<!-- sources: feishu-om_valid, made-up -->\n### 发生了什么\n- 完成"
            normalized = _normalize_summary_source_comments(summary, raw)
            self.assertIn("<!-- sources: feishu-om_valid -->", normalized)
            self.assertNotIn("made-up", normalized)

    def test_index_v2_and_precise_raw_evidence(self) -> None:
        builder = _load_memory_builder()
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            daily = vault / "10-daily" / "2026" / "2026-07-14.md"
            inbox = vault / "00-inbox" / "feishu" / "2026-07-14.md"
            daily.parent.mkdir(parents=True)
            inbox.parent.mkdir(parents=True)

            daily.write_text(
                """# 2026-07-14 日志

## 今日概览
- 完成服务迁移。

## 事件 1：服务器迁移
<!-- sources: feishu-om_target -->
### 发生了什么
- 服务已经迁移到服务器。
### 我做出的判断
- 后续以服务器为主要运行环境。
### 后续动作
- 观察定时任务。

## 事件 2：无关采购
<!-- sources: feishu-om_other -->
### 发生了什么
- 购买了一件无关物品。

## 原始记录
- 保留原文。
""",
                encoding="utf-8",
            )
            inbox.write_text(
                """# 2026-07-14 飞书原始记录

## 10:00 记录会话：服务器迁移
<!-- record_id: feishu-om_target -->
<!-- session_id: session-1 -->
### 用户记录（反馈）
我已经确认迁移后的服务正常运行。

## 11:00 记录会话：其他事情
<!-- record_id: feishu-om_other -->
### 用户记录
这条无关内容不应被精确回读。
""",
                encoding="utf-8",
            )

            written = builder.build_memory_indexes(vault, date_text="2026-07-14")
            self.assertEqual(len(written), 1)
            index = json.loads(written[0].read_text(encoding="utf-8"))
            self.assertEqual(index["schema_version"], 2)
            self.assertEqual(index["source_record_ids"], ["feishu-om_target", "feishu-om_other"])
            self.assertEqual(len(index["events"]), 2)
            self.assertIn("00-inbox/feishu/2026-07-14.md", index["source_pages"])

            evidence = read_personal_evidence_context(vault, query="服务器迁移")
            self.assertIn("我已经确认迁移后的服务正常运行", evidence)
            self.assertNotIn("这条无关内容不应被精确回读", evidence)


if __name__ == "__main__":
    unittest.main()
