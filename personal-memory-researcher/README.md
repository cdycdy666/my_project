# Personal Memory Researcher

这是 `personal-kb` 的通用只读 Researcher，实现论文《General Agentic Memory Via Deep Research》中的在线检索部分。

## 三路检索

```text
用户问题
  -> LLM 规划检索 query
  -> BM25 关键词检索 ┐
  -> Embedding 语义检索 ├-> RRF 融合排序
                        └-> Page-ID / record-ID 回读原文
  -> 证据充分性反思
  -> 必要时补查一轮
  -> MemoryResearchBundle + MemoryEvidence
```

- BM25：本地执行，中文使用连续词片段和二元字组，适合人名、项目名和明确术语。
- Embedding：默认通过 OpenAI 兼容接口调用 `text-embedding-v4`，文档向量按内容哈希缓存。
- Page-ID：根据融合结果读取 `source_pages`；schema v2 索引优先按 `source_record_ids` 精确回读飞书原文。

## 边界

- 只读 `personal-kb`，不修改 daily note、inbox 或 memory-index。
- 向量缓存写入本项目 `data/`，不写回知识库，也不提交 Git。
- 最多研究两轮，每轮最多返回 5 个候选和 5 份原文证据。
- 向量接口失败时保留 BM25 + Page-ID 降级结果，并在 trace 中明确记录错误。
- 输出上下文仍需由具体业务 Agent 使用；Researcher 不直接替用户做最终判断。

## 配置

阅读 Agent 默认复用现有模型 API Key，并支持以下覆盖项：

```env
MEMORY_RESEARCH_ENABLED=true
MEMORY_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MEMORY_EMBEDDING_MODEL=text-embedding-v4
MEMORY_EMBEDDING_DIMENSIONS=1024
MEMORY_RESEARCH_MAX_ROUNDS=2
MEMORY_RESEARCH_CACHE_DIR=/opt/feishu-reading-agent/data/memory-researcher
```

## 运行测试

```bash
cd /Users/chendingyu/my_project/personal-memory-researcher
python3 -m unittest discover -s tests -v
```
