from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DAILY_TEMPLATE = """# {date} 日志

## 今日概览
- 

## 事件 1：
### 发生了什么
- 

### 我怎么处理的
- 

### 我做出的判断
- 

### 判断依据
- 

### 结果 / 反馈
- 

### 后续动作
- 

### 值得沉淀
- 

## 零散记录
- 

## 给 AI 的长期上下文
- 
"""


LEGACY_DAILY_TEMPLATE = """# {date} 日志

## 今天遇到的问题
- 

## 我怎么处理的
- 

## 我做出的判断
- 

## 为什么这么判断
- 

## 结果 / 反馈
- 

## 还没解决
- 

## 明天要推进
- 

## 值得沉淀
- 

## 给 AI 的备注
- 
"""


def shanghai_today() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def daily_note_path(vault_dir: Path, date_text: str) -> Path:
    year = date_text[:4]
    return vault_dir / "10-daily" / year / f"{date_text}.md"


def feishu_inbox_path(vault_dir: Path, date_text: str) -> Path:
    return vault_dir / "00-inbox" / "feishu" / f"{date_text}.md"


def ensure_daily_note(vault_dir: Path, date_text: str) -> Path:
    path = daily_note_path(vault_dir, date_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DAILY_TEMPLATE.format(date=date_text), encoding="utf-8")
    return path


def append_feishu_inbox_message(vault_dir: Path, text: str, date_text: str | None = None) -> Path:
    date_text = date_text or shanghai_today()
    path = feishu_inbox_path(vault_dir, date_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")

    if path.exists():
        content = path.read_text(encoding="utf-8").rstrip()
    else:
        content = f"# {date_text} 飞书原始记录\n"

    content = content.rstrip() + f"\n\n## {now}\n{text.strip()}\n"
    path.write_text(content + "\n", encoding="utf-8")
    return path


def read_feishu_inbox(vault_dir: Path, date_text: str | None = None) -> str:
    date_text = date_text or shanghai_today()
    path = feishu_inbox_path(vault_dir, date_text)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_feishu_inbox(vault_dir: Path, date_text: str, content: str) -> Path:
    path = feishu_inbox_path(vault_dir, date_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def write_daily_summary(vault_dir: Path, date_text: str, summary_markdown: str, raw_records: str) -> Path:
    path = daily_note_path(vault_dir, date_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_block = raw_records.strip() or "暂无"
    content = f"""# {date_text} 日志

{summary_markdown.strip()}

## 原始记录
{raw_block}
"""
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


SECTION_ALIASES = {
    "今天遇到的问题": {
        "问题",
        "遇到的问题",
        "今天遇到的问题",
        "困难",
        "卡点",
    },
    "我怎么处理的": {
        "处理",
        "怎么处理",
        "我怎么处理的",
        "行动",
        "做法",
    },
    "我做出的判断": {
        "判断",
        "决定",
        "决策",
        "我做出的判断",
    },
    "为什么这么判断": {
        "依据",
        "判断依据",
        "为什么",
        "原因",
        "为什么这么判断",
    },
    "结果 / 反馈": {
        "结果",
        "反馈",
        "结果反馈",
    },
    "还没解决": {
        "还没解决",
        "未解决",
        "待解决",
        "阻塞",
    },
    "明天要推进": {
        "明天",
        "明天要推进",
        "下一步",
        "推进",
    },
    "值得沉淀": {
        "沉淀",
        "值得沉淀",
        "经验",
        "原则",
        "复盘",
    },
    "给 AI 的备注": {
        "备注",
        "给AI",
        "给 AI",
        "给 AI 的备注",
        "上下文",
    },
}


def _alias_to_section(label: str) -> str | None:
    normalized = re.sub(r"\s+", "", label).strip()
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if normalized == re.sub(r"\s+", "", alias):
                return section
    return None


def _parse_structured_items(text: str) -> dict[str, list[str]]:
    items: dict[str, list[str]] = {}
    current_section: str | None = None

    for raw_line in text.strip().splitlines():
        line = raw_line.strip().lstrip("-*").strip()
        if not line:
            continue

        match = re.match(r"^([^:：]{1,12})[:：]\s*(.*)$", line)
        if match:
            section = _alias_to_section(match.group(1))
            if section:
                current_section = section
                value = match.group(2).strip()
                if value:
                    items.setdefault(section, []).append(value)
                continue

        if current_section:
            items.setdefault(current_section, []).append(line)
        else:
            items.setdefault("给 AI 的备注", []).append(line)

    return items


def _append_bullets_to_section(content: str, heading: str, bullets: list[str], now: str) -> str:
    if not bullets:
        return content

    marker = f"## {heading}"
    if marker not in content:
        content = content.rstrip() + f"\n\n{marker}\n"

    start = content.find(marker)
    next_start = content.find("\n## ", start + len(marker))
    if next_start == -1:
        before = content
        after = ""
    else:
        before = content[:next_start]
        after = content[next_start:]

    before = re.sub(r"\n- \s*(?=\n|$)", "\n", before.rstrip())
    additions = "".join(f"\n- {now} {bullet.strip()}" for bullet in bullets if bullet.strip())
    return before + additions + "\n" + after


def append_raw_record(vault_dir: Path, text: str, date_text: str | None = None) -> Path:
    date_text = date_text or shanghai_today()
    path = ensure_daily_note(vault_dir, date_text)
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
    content = path.read_text(encoding="utf-8")
    block = f"\n### {now} 飞书记录\n{text.strip()}\n"

    if "## 原始记录" not in content:
        content = content.rstrip() + "\n\n## 原始记录\n"

    content = content.rstrip() + block
    path.write_text(content + "\n", encoding="utf-8")
    return path


def append_organized_record(vault_dir: Path, text: str, date_text: str | None = None) -> tuple[Path, list[str]]:
    date_text = date_text or shanghai_today()
    path = ensure_daily_note(vault_dir, date_text)
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
    content = path.read_text(encoding="utf-8")
    structured_items = _parse_structured_items(text)

    for heading, bullets in structured_items.items():
        content = _append_bullets_to_section(content, heading, bullets, now)

    if "## 原始记录" not in content:
        content = content.rstrip() + "\n\n## 原始记录\n"

    raw_block = f"\n### {now} 飞书记录\n{text.strip()}\n"
    content = content.rstrip() + raw_block
    path.write_text(content + "\n", encoding="utf-8")
    return path, list(structured_items.keys())
