from __future__ import annotations

import html as html_lib
import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


SUPPORTED_SUFFIXES = {".md", ".txt", ".epub", ".pdf"}
MAX_FILE_CHARS = 120_000


@dataclass(frozen=True)
class ReferenceChunk:
    title: str
    source: str
    text: str
    score: int


def list_reference_titles(reference_dir: Path) -> list[str]:
    docs = reference_files(reference_dir)
    if not docs:
        return []
    return [path.stem for path in docs]


def build_reference_context(
    reference_dir: Path,
    query: str,
    max_chars: int = 3200,
    max_chunks: int = 4,
) -> str:
    chunks = find_relevant_chunks(reference_dir, query, max_chunks=max_chunks)
    if not chunks:
        return ""

    lines: list[str] = []
    used = 0
    for chunk in chunks:
        block = f"来源：{chunk.title} / {chunk.source}\n{chunk.text.strip()}"
        if used + len(block) > max_chars:
            continue
        lines.append(block)
        used += len(block)
    return "\n\n---\n\n".join(lines)


def find_relevant_chunks(reference_dir: Path, query: str, max_chunks: int = 4) -> list[ReferenceChunk]:
    tokens = tokenize(query)
    scored: list[ReferenceChunk] = []
    for path in reference_files(reference_dir):
        title, blocks = read_blocks(path)
        for source, text in blocks:
            score = score_text(text, tokens)
            if score > 0:
                scored.append(ReferenceChunk(title=title, source=source, text=text, score=score))

    scored.sort(key=lambda item: item.score, reverse=True)
    if scored:
        return diversify_chunks(scored, max_chunks)

    fallback: list[ReferenceChunk] = []
    for path in reference_files(reference_dir):
        title, blocks = read_blocks(path)
        for source, text in blocks[:1]:
            fallback.append(ReferenceChunk(title=title, source=source, text=text, score=0))
    return fallback[:max_chunks]


def diversify_chunks(chunks: list[ReferenceChunk], max_chunks: int) -> list[ReferenceChunk]:
    """Prefer top-scoring chunks while avoiding a single book dominating the context."""
    selected: list[ReferenceChunk] = []
    seen_titles: set[str] = set()

    for chunk in chunks:
        if chunk.title in seen_titles:
            continue
        selected.append(chunk)
        seen_titles.add(chunk.title)
        if len(selected) >= max_chunks:
            return selected

    for chunk in chunks:
        if chunk in selected:
            continue
        selected.append(chunk)
        if len(selected) >= max_chunks:
            break
    return selected


def reference_files(reference_dir: Path) -> list[Path]:
    if not reference_dir.exists():
        return []
    return sorted(
        path
        for path in reference_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and path.name.lower() != "readme.md"
    )


def read_blocks(path: Path) -> tuple[str, list[tuple[str, str]]]:
    if path.suffix.lower() == ".epub":
        return read_epub_blocks(path)
    if path.suffix.lower() == ".pdf":
        return read_pdf_blocks(path)

    text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_CHARS]
    return read_text_blocks(path, text)


def read_text_blocks(path: Path, text: str) -> tuple[str, list[tuple[str, str]]]:
    title = extract_title(path, text)
    raw_blocks = split_blocks(text[:MAX_FILE_CHARS])
    blocks: list[tuple[str, str]] = []
    current_heading = "摘录"
    for block in raw_blocks:
        heading_match = re.match(r"^#{1,4}\s+(.+)$", block.strip())
        if heading_match:
            current_heading = heading_match.group(1).strip()
            continue
        cleaned = block.strip()
        if len(cleaned) < 20:
            continue
        blocks.append((current_heading, cleaned[:1200]))
    return title, blocks


def read_epub_blocks(path: Path) -> tuple[str, list[tuple[str, str]]]:
    try:
        with zipfile.ZipFile(path) as book:
            opf_path = find_opf_path(book)
            if not opf_path:
                return path.stem, []
            opf_xml = book.read(opf_path)
            title, chapter_paths = parse_opf(opf_xml, opf_path)
            blocks: list[tuple[str, str]] = []
            for chapter_path in chapter_paths:
                if chapter_path not in book.namelist():
                    continue
                raw_html = book.read(chapter_path).decode("utf-8", errors="ignore")
                chapter_text = html_to_text(raw_html)
                _, chapter_blocks = read_text_blocks(Path(chapter_path), chapter_text)
                source = Path(chapter_path).stem
                for heading, text in chapter_blocks:
                    blocks.append((heading if heading != "摘录" else source, text))
                if sum(len(text) for _, text in blocks) >= MAX_FILE_CHARS:
                    break
            return title or path.stem, blocks
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError):
        return path.stem, []


def read_pdf_blocks(path: Path) -> tuple[str, list[tuple[str, str]]]:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return path.stem, []

    try:
        reader = PdfReader(str(path))
    except Exception:
        return path.stem, []

    title = ""
    metadata = getattr(reader, "metadata", None)
    if metadata:
        title = normalize_pdf_metadata_text(getattr(metadata, "title", "") or metadata.get("/Title", ""))

    blocks: list[tuple[str, str]] = []
    used = 0
    for index, page in enumerate(reader.pages, start=1):
        if used >= MAX_FILE_CHARS:
            break
        try:
            page_text = page.extract_text() or ""
        except Exception:
            continue
        for block in split_blocks(page_text):
            cleaned = block.strip()
            if len(cleaned) < 20:
                continue
            blocks.append((f"p.{index}", cleaned[:1200]))
            used += len(cleaned)
            if used >= MAX_FILE_CHARS:
                break
    return title or path.stem, blocks


def normalize_pdf_metadata_text(value: object) -> str:
    return str(value).strip() if value else ""


def find_opf_path(book: zipfile.ZipFile) -> str | None:
    try:
        container_xml = book.read("META-INF/container.xml")
    except KeyError:
        return None
    root = ElementTree.fromstring(container_xml)
    for element in root.iter():
        if local_name(element.tag) == "rootfile":
            full_path = element.attrib.get("full-path")
            if full_path:
                return full_path
    return None


def parse_opf(opf_xml: bytes, opf_path: str) -> tuple[str, list[str]]:
    root = ElementTree.fromstring(opf_xml)
    title = ""
    manifest: dict[str, tuple[str, str]] = {}
    spine_ids: list[str] = []
    base_path = posixpath.dirname(opf_path)

    for element in root.iter():
        name = local_name(element.tag)
        if name == "title" and not title and element.text:
            title = element.text.strip()
        elif name == "item":
            item_id = element.attrib.get("id")
            href = element.attrib.get("href")
            media_type = element.attrib.get("media-type", "")
            if item_id and href:
                manifest[item_id] = (href, media_type)
        elif name == "itemref":
            idref = element.attrib.get("idref")
            if idref:
                spine_ids.append(idref)

    chapter_paths: list[str] = []
    ids = spine_ids or list(manifest)
    for item_id in ids:
        entry = manifest.get(item_id)
        if not entry:
            continue
        href, media_type = entry
        if media_type not in {"application/xhtml+xml", "text/html", ""}:
            continue
        chapter_paths.append(posixpath.normpath(posixpath.join(base_path, href)))
    return title, chapter_paths


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?i)</(p|div|section|article|h[1-6]|li|blockquote)>", "\n\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", text)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def split_blocks(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    blocks: list[str] = []
    for part in parts:
        if len(part) <= 1200:
            blocks.append(part)
            continue
        for index in range(0, len(part), 900):
            blocks.append(part[index : index + 900])
    return blocks


def extract_title(path: Path, text: str) -> str:
    for line in text.splitlines()[:20]:
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return match.group(1).strip()
    return path.stem


def tokenize(query: str) -> set[str]:
    tokens = {item.lower() for item in re.findall(r"[A-Za-z0-9_]{2,}", query)}
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", query)
    tokens.update("".join(chinese_chars[index : index + 2]) for index in range(len(chinese_chars) - 1))
    tokens.update("".join(chinese_chars[index : index + 3]) for index in range(len(chinese_chars) - 2))
    return {token for token in tokens if token.strip()}


def score_text(text: str, tokens: set[str]) -> int:
    if not tokens:
        return 0
    lowered = text.lower()
    score = 0
    for token in tokens:
        if token in lowered:
            score += 2 if len(token) >= 3 else 1
    return score
