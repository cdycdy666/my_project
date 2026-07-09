from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


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
    architecture: tuple[dict[str, str], ...] = field(default_factory=tuple)


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
            {"id": "feishu", "label": "飞书消息", "kind": "input"},
            {"id": "listener", "label": "常驻监听", "kind": "service"},
            {"id": "inbox", "label": "Obsidian inbox", "kind": "storage"},
            {"id": "feedback_llm", "label": "即时反馈 LLM", "kind": "llm"},
            {"id": "summary_job", "label": "23:00 整理任务", "kind": "schedule"},
            {"id": "daily_note", "label": "Daily Note", "kind": "storage"},
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
            {"id": "feishu", "label": "飞书请求", "kind": "input"},
            {"id": "context", "label": "PersonalContextBundle", "kind": "tool"},
            {"id": "planner", "label": "材料检索规划 LLM", "kind": "llm"},
            {"id": "weread", "label": "微信读书 API 验证", "kind": "tool"},
            {"id": "scoring", "label": "候选材料打分 LLM", "kind": "llm"},
            {"id": "gate", "label": "最终材料校验闸门", "kind": "gate"},
            {"id": "reply", "label": "飞书回复", "kind": "output"},
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
            {"id": "feishu", "label": "飞书请求", "kind": "input"},
            {"id": "history", "label": "会话历史", "kind": "storage"},
            {"id": "planner", "label": "LLM Planner", "kind": "llm"},
            {"id": "tools", "label": "RSS / arXiv 工具", "kind": "tool"},
            {"id": "draft", "label": "证据化回复生成", "kind": "llm"},
            {"id": "gate", "label": "标题 / 链接证据门", "kind": "gate"},
            {"id": "reply", "label": "飞书回复", "kind": "output"},
        ),
    ),
)


AGENT_BY_ID = {agent.id: agent for agent in AGENTS}
