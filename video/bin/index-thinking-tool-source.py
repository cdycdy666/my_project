#!/usr/bin/env python3
"""Index the local Modern Thinking Tools course source.

The script intentionally stores metadata only. It does not copy full course text
into the video repo, so downstream videos can cite and transform the source
without turning the production folder into a duplicate course archive.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ModuleNotFoundError as exc:  # pragma: no cover - friendly CLI failure.
    raise SystemExit(
        "Missing dependency: pypdf. Run with the Codex bundled Python runtime "
        "or install pypdf into your active Python environment."
    ) from exc


NOISE_RE = re.compile(r"[\[［]防断更[^］\]]*[\]］]")
SPACE_RE = re.compile(r"\s+")


def clean_stem(path: Path) -> str:
    stem = NOISE_RE.sub("", path.stem).strip()
    stem = stem.replace("： ", "：")
    stem = re.sub(r"^(\d{2})\s+", r"\1", stem)
    stem = SPACE_RE.sub(" ", stem)
    return stem


def pair_key(path: Path) -> str:
    return clean_stem(path).replace(" ", "")


def source_kind(title: str) -> str:
    if "问答" in title:
        return "qa"
    if "特别" in title or "直播" in title:
        return "special"
    if title.startswith("00"):
        return "preface"
    return "lesson"


def source_number(title: str) -> str:
    match = re.match(r"^(\d{2})", title)
    return match.group(1) if match else ""


def pdf_stats(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"page_count": None, "extractable": False, "sample_chars_first_2_pages": 0}

    reader = PdfReader(str(path))
    text_parts = []
    for page in reader.pages[:2]:
        text_parts.append(page.extract_text() or "")
    sample = "\n".join(text_parts).strip()
    return {
        "page_count": len(reader.pages),
        "extractable": len(sample) >= 200,
        "sample_chars_first_2_pages": len(sample),
    }


def build_manifest(source_dir: Path) -> dict[str, object]:
    groups: dict[str, dict[str, object]] = {}
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in {".pdf", ".mp3"}:
            continue

        key = pair_key(path)
        title = clean_stem(path)
        record = groups.setdefault(
            key,
            {
                "title": title,
                "number": source_number(title),
                "kind": source_kind(title),
                "pdf_path": None,
                "audio_path": None,
            },
        )
        if ext == ".pdf":
            record["pdf_path"] = str(path)
        else:
            record["audio_path"] = str(path)

    records = []
    for record in groups.values():
        pdf_path = Path(record["pdf_path"]) if record["pdf_path"] else None
        stats = pdf_stats(pdf_path)
        records.append(
            {
                **record,
                **stats,
                "status": "indexed",
                "recommended_use": "primary" if record["kind"] == "lesson" else "supporting",
            }
        )

    records.sort(key=lambda item: (item["number"], item["kind"], item["title"]))
    for idx, record in enumerate(records, start=1):
        record["source_id"] = f"MTT-{idx:03d}"

    return {
        "source_name": "万维钢·现代思维工具100讲",
        "source_dir": str(source_dir),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "record_count": len(records),
        "records": records,
    }


def write_markdown(manifest: dict[str, object], output_path: Path) -> None:
    records = manifest["records"]
    assert isinstance(records, list)

    lines = [
        "# 课程源索引",
        "",
        f"- 来源：`{manifest['source_dir']}`",
        f"- 生成时间：{manifest['generated_at']}",
        f"- 条目数：{manifest['record_count']}",
        "",
        "## 使用规则",
        "",
        "- 本索引只保存元数据，不复制课程全文。",
        "- 正课优先作为视频主原料，问答和特别放送作为补充反驳或案例来源。",
        "- 每条视频引用课程源时，必须转化为自己的工具卡、场景和行动建议，不直接搬运原文。",
        "",
        "## 条目",
        "",
        "| ID | 类型 | 标题 | PDF | 音频 | 页数 | 可抽文本 | 用途 |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]

    for record in records:
        pdf = "yes" if record["pdf_path"] else "no"
        audio = "yes" if record["audio_path"] else "no"
        extractable = "yes" if record["extractable"] else "no"
        lines.append(
            f"| {record['source_id']} | {record['kind']} | {record['title']} | "
            f"{pdf} | {audio} | {record['page_count'] or ''} | {extractable} | "
            f"{record['recommended_use']} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args.source_dir)

    manifest_path = args.out_dir / "source-manifest.json"
    index_path = args.out_dir / "course-source-index.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(manifest, index_path)

    print(f"wrote {manifest_path}")
    print(f"wrote {index_path}")
    print(f"records {manifest['record_count']}")


if __name__ == "__main__":
    main()
