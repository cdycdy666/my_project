#!/usr/bin/env python3
"""Extract full PDF text for the Practical Thinking Tools source library."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        cleaned.append(line)
        previous_blank = blank
    return "\n".join(cleaned).strip() + "\n"


def extract_pdf(path: Path) -> tuple[str, list[int]]:
    reader = PdfReader(str(path))
    parts: list[str] = []
    page_chars: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        page_chars.append(len(text))
        parts.append(f"## Page {index}\n\n{text}")
    return "\n".join(parts).strip() + "\n", page_chars


def safe_filename(source_id: str, title: str) -> str:
    title = re.sub(r"[\\/:*?\"<>|]", "-", title)
    title = re.sub(r"\s+", "-", title).strip("-")
    return f"{source_id}-{title}.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = data["records"]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    report = []
    for record in records:
        pdf_path = record.get("pdf_path")
        if not pdf_path:
            report.append({**record, "extracted_path": None, "text_chars": 0, "status": "missing_pdf"})
            continue

        pdf = Path(pdf_path)
        text, page_chars = extract_pdf(pdf)
        filename = safe_filename(record["source_id"], record["title"])
        out_path = args.out_dir / filename
        header = [
            f"# {record['title']}",
            "",
            "## Source Metadata",
            "",
            f"- Source ID: `{record['source_id']}`",
            f"- Type: `{record['kind']}`",
            f"- Lesson No: `{record['number']}`",
            f"- PDF Path: `{record['pdf_path']}`",
            f"- Audio Path: `{record['audio_path'] or ''}`",
            f"- Page Count: {record['page_count']}",
            "",
            "## Full Extracted Text",
            "",
        ]
        out_path.write_text("\n".join(header) + text, encoding="utf-8")
        report.append(
            {
                "source_id": record["source_id"],
                "title": record["title"],
                "kind": record["kind"],
                "number": record["number"],
                "page_count": record["page_count"],
                "text_chars": len(text),
                "page_chars": page_chars,
                "extracted_path": str(out_path),
                "status": "extracted",
            }
        )

    report_path = args.out_dir / "_extraction-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"extracted {sum(1 for item in report if item['status'] == 'extracted')} files")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
