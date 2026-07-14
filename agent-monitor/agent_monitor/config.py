from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT_PREFIX = Path(os.environ.get("AGENT_MONITOR_ROOT_PREFIX", "/opt"))


@dataclass(frozen=True)
class AgentConfig:
    id: str
    name: str
    role: str
    root: Path
    service_units: tuple[str, ...]
    timer_units: tuple[str, ...] = ()
    trace_dir: str | None = None
    log_files: tuple[str, ...] = ()
    accent: str = "#6ee7b7"
    architecture: tuple[dict[str, Any], ...] = field(default_factory=tuple)


AGENTS: tuple[AgentConfig, ...] = (
    AgentConfig(
        id="obsidian",
        name="Obsidian Capture",
        role="飞书记录 -> 即时反馈 -> 晚间整理写入 personal-kb",
        root=ROOT_PREFIX / "feishu-obsidian-capture",
        service_units=("feishu-obsidian-listener.service",),
        log_files=(
            "logs/listener.err.log",
            "logs/listener.log",
            "logs/cron-morning.log",
            "logs/cron-summary.log",
        ),
        accent="#79e6f3",
        architecture=(
            {
                "id": "feishu",
                "label": "接收飞书记录",
                "kind": "input",
                "goal": "把用户随手发来的文字或语音转写记录变成可追踪的一条 capture。",
                "input": ["飞书消息事件", "chat_id", "message_id", "用户原文"],
                "output": ["trace_id", "去重后的记录任务", "待写入 inbox 的原始文本"],
                "depends": ["飞书长连接事件", "message_id 去重状态"],
                "risk": ["重复事件导致重复回复", "语音/富文本解析不完整"],
            },
            {
                "id": "inbox",
                "label": "保存原始记录",
                "kind": "storage",
                "goal": "先落盘原文，保证后续模型失败也不会丢记录。",
                "input": ["去重后的用户原文", "消息时间", "发送者信息"],
                "output": ["带 record_id/session_id 的 inbox 条目", "可供即时反馈参考的今日上下文"],
                "depends": ["personal-kb 路径", "daily/inbox 文件写权限"],
                "risk": ["本地和服务器 Git 状态冲突", "文件路径或日期归属错误"],
            },
            {
                "id": "feedback_llm",
                "label": "即时反馈 LLM",
                "kind": "llm",
                "goal": "给用户一两句反馈或追问，帮助记录形成闭环。",
                "input": ["刚刚的新记录", "今日 inbox 上下文", "反馈 prompt"],
                "output": ["1-2 句反馈", "记录类型判断", "必要时的追问"],
                "depends": ["LLM API", "今日上下文读取"],
                "risk": ["反馈太像总结而不是追问", "多轮追问没有被纳入晚间整理"],
            },
            {
                "id": "summary_job",
                "label": "晚间整理任务",
                "kind": "schedule",
                "goal": "把当天零散记录整理成结构化 daily note。",
                "input": ["当天飞书记录/inbox", "daily note 模板", "整理 prompt"],
                "output": ["带事件来源引用的 daily note", "整理完成通知", "memory-index 构建输入"],
                "depends": ["定时任务", "LLM API", "personal-kb Git 仓库"],
                "risk": ["Mac/服务器定时任务漏跑", "整理覆盖或遗漏上下文"],
            },
            {
                "id": "daily_note",
                "label": "写入 Daily Note",
                "kind": "output",
                "goal": "沉淀问题、处理、判断、依据、反馈和明日推进。",
                "input": ["晚间整理结果", "当天日期", "daily note 文件路径"],
                "output": ["personal-kb/10-daily/YYYY/YYYY-MM-DD.md", "可被其他 Agent 读取的长期上下文"],
                "depends": ["Obsidian 文件结构", "Git push"],
                "risk": ["敏感信息进入 Git", "后续 Agent 读取到过时处境"],
            },
            {
                "id": "memory_index",
                "label": "生成轻量记忆索引",
                "kind": "storage",
                "goal": "把 daily note 压缩为可检索索引，同时保留回读原始记录的来源链。",
                "input": ["daily note", "source_record_ids", "source_pages"],
                "output": ["90-context/memory-index/YYYY-MM-DD.json", "events", "可追溯原文入口"],
                "depends": ["personal-kb/scripts/build_memory_index.py", "00-inbox/feishu 原始记录"],
                "risk": ["索引生成失败但 daily note 已成功", "旧记录没有 record_id 时只能回读整页"],
            },
        ),
    ),
    AgentConfig(
        id="reading",
        name="Reading Agent",
        role="个人处境 + 微信读书验证 -> 低门槛阅读建议",
        root=ROOT_PREFIX / "feishu-reading-agent",
        service_units=("feishu-reading-agent.service",),
        trace_dir="logs/traces",
        log_files=("logs/service.err.log", "logs/service.log", "logs/weekly.log"),
        accent="#a7f36b",
        architecture=(
            {
                "id": "feishu",
                "label": "接收阅读请求",
                "kind": "input",
                "goal": "识别用户是否在请求推荐、换一本、解释材料或追问。",
                "input": ["飞书用户消息", "chat_id", "conversation history"],
                "output": ["阅读推荐任务", "trace_id", "会话上下文"],
                "depends": ["飞书机器人", "state.json 会话状态"],
                "risk": ["短消息意图不清", "多轮上下文过长或过旧"],
            },
            {
                "id": "memory_plan",
                "label": "Researcher 规划记忆查询",
                "kind": "llm",
                "goal": "结合用户原话和记忆索引概览，生成最多三条历史检索 query。",
                "input": ["用户消息", "memory-index 事件概览", "项目/人物/时间线索"],
                "output": ["planned_queries", "检索理由", "最多两轮研究预算"],
                "depends": ["LLM API", "personal-kb/90-context/memory-index"],
                "risk": ["query 过宽导致噪音", "LLM 规划失败时退回用户原话"],
            },
            {
                "id": "memory_search",
                "label": "BM25 + Embedding 融合检索",
                "kind": "tool",
                "goal": "同时覆盖明确关键词与语义相近的历史记忆，并用 RRF 合并排序。",
                "input": ["planned_queries", "schema v2 事件索引", "text-embedding-v4 向量缓存"],
                "output": ["BM25 hits", "embedding hits", "fused memory hits"],
                "depends": ["本地 BM25", "DashScope embeddings", "本地向量缓存"],
                "risk": ["向量接口不可用时降级为 BM25", "旧索引粒度较粗"],
            },
            {
                "id": "planner",
                "label": "LLM 规划材料检索",
                "kind": "llm",
                "goal": "决定要验证哪些书名、概念或关键词。",
                "input": ["用户消息", "PersonalContextBundle", "loop_history", "当前已验证材料状态"],
                "output": ["下一步 action", "material queries", "规划理由"],
                "depends": ["LLM API", "工具注册表"],
                "risk": ["query 过泛", "规划反复空转", "引入未经验证的新概念"],
            },
            {
                "id": "weread",
                "label": "微信读书验证材料",
                "kind": "tool",
                "goal": "验证书籍、目录位置、热门划线、公开点评和个人笔记。",
                "input": ["material queries", "max_queries", "max_books_per_query", "WEREAD_API_KEY"],
                "output": ["书籍搜索结果", "目录片段", "划线/点评片段", "verified_materials_context"],
                "depends": ["微信读书 skill/API", "网络和 API 配额"],
                "risk": ["微信读书不提供全文", "目录只能证明位置存在", "搜索命中偏题"],
            },
            {
                "id": "evidence",
                "label": "Page-ID / record-ID 回读原文",
                "kind": "tool",
                "goal": "按融合命中的来源标识回读原文，避免只靠轻量索引推断用户处境。",
                "input": ["fused memory hits", "source_pages", "source_record_ids"],
                "output": ["MemoryEvidence", "daily 摘录", "精确 inbox 原始记录"],
                "depends": ["personal-kb/10-daily", "personal-kb/00-inbox", "memory-index"],
                "risk": ["回读片段不够相关", "上下文过长挤占 token"],
            },
            {
                "id": "scoring",
                "label": "LLM 候选材料打分",
                "kind": "llm",
                "goal": "在已验证材料中选出最适合当下处境的低门槛阅读动作。",
                "input": ["个人处境", "personal_evidence_context", "verified_materials_context"],
                "output": ["候选排序", "primary", "primary_problem", "should_output_count"],
                "depends": ["LLM API", "已验证材料"],
                "risk": ["评分解释偏主观", "候选材料证据强弱混在一起"],
            },
            {
                "id": "reply",
                "label": "LLM 生成阅读建议",
                "kind": "llm",
                "goal": "生成低门槛、可执行、具体到章节或搜索动作的回复。",
                "input": ["用户消息", "材料打分结果", "已验证材料", "回复格式约束"],
                "output": ["飞书回复草稿", "推荐阅读动作", "读完后问题"],
                "depends": ["LLM API", "材料打分结果"],
                "risk": ["回复临时冒出未验证材料", "推荐整本书导致门槛过高"],
            },
            {
                "id": "gate",
                "label": "最终材料校验闸门",
                "kind": "gate",
                "goal": "确保最终回复里的书名、章节、概念都能追溯到本轮验证材料。",
                "input": ["最终回复草稿", "verified_materials_context"],
                "output": ["ok / blocked", "extra_queries", "拦截原因"],
                "depends": ["LLM 校验 prompt", "补检索轮次限制"],
                "risk": ["校验过严导致 warning", "补检索后仍无法验证"],
            },
        ),
    ),
    AgentConfig(
        id="podcast",
        name="Podcast Guide",
        role="播客 RSS + arXiv 工具循环 -> 学习陪练",
        root=ROOT_PREFIX / "feishu-podcast-guide",
        service_units=("feishu-podcast-guide.service",),
        timer_units=("feishu-podcast-guide-daily-reco.timer",),
        trace_dir="logs/traces",
        log_files=("logs/service.err.log", "logs/service.log", "logs/daily-reco.log"),
        accent="#f9d66d",
        architecture=(
            {
                "id": "feishu",
                "label": "接收学习请求",
                "kind": "input",
                "goal": "识别用户是在找播客、读论文、做复盘还是请求学习路径。",
                "input": ["飞书消息", "chat_id", "message_id"],
                "output": ["学习陪练任务", "trace_id", "意图线索"],
                "depends": ["飞书机器人", "消息去重"],
                "risk": ["播客/论文意图混合", "请求太宽导致搜索范围过大"],
            },
            {
                "id": "history",
                "label": "读取会话历史",
                "kind": "storage",
                "goal": "让复盘和连续追问能接上前几轮上下文。",
                "input": ["chat_id", "state.json", "最近交互记录"],
                "output": ["conversation_history", "recent recommendations"],
                "depends": ["state.json", "历史压缩策略"],
                "risk": ["历史太长", "失败回复没有被记住"],
            },
            {
                "id": "planner",
                "label": "LLM Planner",
                "kind": "llm",
                "goal": "在工具循环中决定下一步搜索播客、查详情、搜论文或生成回复。",
                "input": ["用户消息", "conversation_history", "state_summary", "tool_history"],
                "output": ["tool action", "query/identifier", "规划理由"],
                "depends": ["LLM API", "工具注册表", "max_turns"],
                "risk": ["planner 非 JSON", "动作被纠偏后仍不够灵活"],
            },
            {
                "id": "tools",
                "label": "RSS / arXiv 工具",
                "kind": "tool",
                "goal": "只从真实 RSS 条目和 arXiv/PDF 缓存中取证据。",
                "input": ["tool action", "query", "episode id/url", "arXiv id/url"],
                "output": ["episodes", "papers", "tool content", "metadata"],
                "depends": ["RSS 索引", "arXiv API", "PDF 缓存"],
                "risk": ["RSS 不含全文", "论文 PDF 解析失败", "搜索关键词过窄"],
            },
            {
                "id": "draft",
                "label": "证据化回复生成",
                "kind": "llm",
                "goal": "基于工具返回的真实材料生成学习建议或论文拆解。",
                "input": ["用户消息", "conversation_history", "tool_history", "RSS/arXiv stats"],
                "output": ["回复草稿", "推荐单集/论文", "听前抓手或技术拆解"],
                "depends": ["LLM API", "已允许引用的材料集合"],
                "risk": ["生成不存在的单集", "不小心做成长篇二次摘要"],
            },
            {
                "id": "gate",
                "label": "标题 / 链接证据门",
                "kind": "gate",
                "goal": "校验回复引用的单集、论文标题和链接来自本轮工具结果。",
                "input": ["回复草稿", "allowed_episodes", "allowed_papers"],
                "output": ["ok / blocked", "extra_queries", "失败原因"],
                "depends": ["证据门规则", "补查轮次"],
                "risk": ["标题匹配过松或过严", "补查后仍无证据"],
            },
            {
                "id": "reply",
                "label": "飞书回复",
                "kind": "output",
                "goal": "把通过证据门的建议发回飞书，并记录本轮会话。",
                "input": ["通过校验的最终回复", "chat_id"],
                "output": ["飞书消息", "state.json 交互记录", "trace 完成事件"],
                "depends": ["飞书发送接口", "state 写入"],
                "risk": ["飞书发送失败", "多线程回复交错"],
            },
        ),
    ),
)


AGENT_BY_ID = {agent.id: agent for agent in AGENTS}
