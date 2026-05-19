#!/usr/bin/env python3
"""Build an Obsidian vault from extracted Practical Thinking Tools lessons."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote


P0_IDS = {"MTT-017", "MTT-020", "MTT-046", "MTT-047"}
P1_IDS = {"MTT-026", "MTT-032", "MTT-033", "MTT-039", "MTT-045", "MTT-049"}


def sanitize_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]", "-", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def yaml_string(value: object) -> str:
    if value is None:
        return '""'
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def extract_full_text(markdown: str) -> str:
    marker = "## Full Extracted Text"
    if marker not in markdown:
        return markdown.strip() + "\n"
    return markdown.split(marker, 1)[1].strip() + "\n"


def first_content_snippet(full_text: str, limit: int = 180) -> str:
    lines = []
    for raw in full_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("## Page"):
            continue
        lines.append(line)
        if sum(len(x) for x in lines) >= limit:
            break
    text = "".join(lines)
    return text[:limit]


def priority_for(source_id: str, kind: str) -> str:
    if source_id in P0_IDS:
        return "P0"
    if source_id in P1_IDS:
        return "P1"
    return "P2" if kind == "lesson" else "P3"


def obsidian_uri(vault_name: str, note_path: str) -> str:
    return "obsidian://open?vault=" + quote(vault_name) + "&file=" + quote(note_path)


def write_note(vault: Path, vault_name: str, record: dict, report: dict) -> dict:
    source_id = record["source_id"]
    title = record["title"]
    kind = record["kind"]
    priority = priority_for(source_id, kind)
    extracted_path = Path(report["extracted_path"])
    extracted = extracted_path.read_text(encoding="utf-8")
    full_text = extract_full_text(extracted)
    filename = f"{source_id} {sanitize_filename(title)}.md"
    relative_note_path = f"00-source-fulltext/{filename}"
    note_path = vault / relative_note_path
    tags = [
        "source/modern-thinking-tools",
        f"type/{kind}",
        f"priority/{priority.lower()}",
    ]
    if kind == "lesson":
        tags.append("candidate/video-source")

    frontmatter = [
        "---",
        f"source_id: {yaml_string(source_id)}",
        f"title: {yaml_string(title)}",
        f"lesson_no: {yaml_string(record.get('number', ''))}",
        f"type: {yaml_string(kind)}",
        f"recommended_use: {yaml_string(record.get('recommended_use', ''))}",
        f"priority: {yaml_string(priority)}",
        f"page_count: {record.get('page_count') or 0}",
        f"text_chars: {report.get('text_chars') or 0}",
        f"pdf_path: {yaml_string(record.get('pdf_path'))}",
        f"audio_path: {yaml_string(record.get('audio_path'))}",
        "import_status: full_text_in_obsidian",
        "tool_card_status: pending",
        "video_candidate: " + ("true" if priority in {"P0", "P1"} else "false"),
        "tags:",
        *[f"  - {tag}" for tag in tags],
        "---",
        "",
    ]

    body = [
        f"# {title}",
        "",
        "[[MOC-现代思维工具100讲]]",
        "",
        "## Production Summary",
        "",
        "- Summary: 待结构化整理。完整课程文本已保存在本页下方。",
        "- Tool Card: 待提炼",
        "- Best Video Angle: 待提炼",
        "- Common Misuse: 待提炼",
        "- First Action: 待提炼",
        "",
        "## Source Metadata",
        "",
        f"- Source ID: `{source_id}`",
        f"- Type: `{kind}`",
        f"- Lesson No: `{record.get('number', '')}`",
        f"- PDF Path: `{record.get('pdf_path') or ''}`",
        f"- Audio Path: `{record.get('audio_path') or ''}`",
        f"- Page Count: {record.get('page_count') or ''}",
        f"- Text Chars: {report.get('text_chars') or ''}",
        "",
        "## Full Extracted Text",
        "",
        full_text,
    ]
    note_path.write_text("\n".join(frontmatter + body), encoding="utf-8")

    return {
        "source_id": source_id,
        "title": title,
        "kind": kind,
        "number": record.get("number", ""),
        "priority": priority,
        "page_count": record.get("page_count"),
        "text_chars": report.get("text_chars"),
        "obsidian_path": str(note_path),
        "obsidian_note": relative_note_path,
        "obsidian_uri": obsidian_uri(vault_name, relative_note_path),
        "summary": first_content_snippet(full_text),
        "pdf_path": record.get("pdf_path"),
        "audio_path": record.get("audio_path"),
        "has_audio": bool(record.get("audio_path")),
        "recommended_use": record.get("recommended_use"),
        "video_candidate": priority in {"P0", "P1"},
    }


def write_templates(vault: Path) -> None:
    templates = vault / "_templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "structured-note-template.md").write_text(
        """# {{title}}

## One Sentence

## Core Tool

## Real Scene

## Default Mistake

## Common Misuse

## First Action

## Video Angles

## Source Links

""",
        encoding="utf-8",
    )
    (templates / "tool-card-template.md").write_text(
        """# {{tool_name}}

## One Sentence

## Best Scene

## Default Mistake

## Wrong Use

## First Action

## Visual Metaphor

## Source

""",
        encoding="utf-8",
    )


def write_moc(vault: Path, items: list[dict]) -> None:
    moc_dir = vault / "99-moc"
    moc_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MOC-现代思维工具100讲",
        "",
        "这个 vault 保存《万维钢·现代思维工具100讲》的完整 PDF 抽取文本、结构化笔记、工具卡和视频角度。",
        "",
        "## Workflow",
        "",
        "1. 在 `00-source-fulltext/` 阅读完整原文。",
        "2. 在 `01-structured-notes/` 做结构化整理。",
        "3. 在 `02-tool-cards/` 提炼工具卡。",
        "4. 在 `03-video-angles/` 生成视频选题角度。",
        "5. Notion 只保存索引、摘要、状态和 Obsidian 链接。",
        "",
        "## P0 Candidates",
        "",
    ]
    for item in items:
        if item["priority"] == "P0":
            note_name = Path(item["obsidian_note"]).stem
            lines.append(f"- [[{note_name}|{item['source_id']} {item['title']}]]")
    lines.extend(["", "## All Sources", ""])
    for item in items:
        note_name = Path(item["obsidian_note"]).stem
        lines.append(f"- [[{note_name}|{item['source_id']} {item['title']}]] `{item['kind']}` `{item['priority']}`")
    (moc_dir / "MOC-现代思维工具100讲.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--extraction-report", required=True, type=Path)
    parser.add_argument("--vault-dir", required=True, type=Path)
    parser.add_argument("--vault-name", default="Practical Thinking Tools")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report_items = json.loads(args.extraction_report.read_text(encoding="utf-8"))
    report_by_id = {item["source_id"]: item for item in report_items}

    vault = args.vault_dir
    for folder in [
        ".obsidian",
        "00-source-fulltext",
        "01-structured-notes",
        "02-tool-cards",
        "03-video-angles",
        "04-scripts",
        "99-moc",
    ]:
        (vault / folder).mkdir(parents=True, exist_ok=True)

    (vault / ".obsidian" / "app.json").write_text('{"alwaysUpdateLinks":true}\n', encoding="utf-8")

    items = []
    for record in manifest["records"]:
        items.append(write_note(vault, args.vault_name, record, report_by_id[record["source_id"]]))

    write_templates(vault)
    write_moc(vault, items)
    (vault / "notion-light-index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"vault {vault}")
    print(f"notes {len(items)}")
    print(f"index {vault / 'notion-light-index.json'}")


if __name__ == "__main__":
    main()
