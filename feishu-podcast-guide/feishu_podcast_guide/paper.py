from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
USER_AGENT = "feishu-podcast-guide/0.1"


@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    published: str
    abs_url: str
    pdf_url: str


def extract_arxiv_identifier(value: str) -> str:
    text = value.strip()
    if not text:
        return ""

    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([A-Za-z0-9.\-_/]+)",
        r"\barXiv:([A-Za-z0-9.\-_/]+)",
        r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            identifier = match.group(1).strip()
            identifier = re.sub(r"\.pdf$", "", identifier, flags=re.IGNORECASE)
            return identifier.strip("/")
    return ""


def search_arxiv(query: str, limit: int = 5, timeout: int = 20) -> list[Paper]:
    safe_query = query.strip()
    if not safe_query:
        return []

    identifier = extract_arxiv_identifier(safe_query)
    if identifier:
        params = urllib.parse.urlencode({"id_list": identifier})
    else:
        params = urllib.parse.urlencode(
            {
                "search_query": _build_search_query(safe_query),
                "start": 0,
                "max_results": max(1, min(limit, 10)),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )

    data = _get_url(f"{ARXIV_API_URL}?{params}", timeout=timeout)
    root = ET.fromstring(data)
    papers = [_entry_to_paper(entry) for entry in root.findall(f"{ATOM_NS}entry")]
    return [paper for paper in papers if paper.title][: max(1, min(limit, 10))]


def fetch_arxiv_paper(
    identifier_or_query: str,
    cache_dir: Path,
    max_pages: int = 8,
    max_chars: int = 18000,
) -> tuple[Paper, str, bool]:
    paper = _resolve_paper(identifier_or_query)
    paper_dir = cache_dir / _safe_paper_id(paper.paper_id)
    paper_dir.mkdir(parents=True, exist_ok=True)
    meta_path = paper_dir / "metadata.json"
    pdf_path = paper_dir / "paper.pdf"
    text_path = paper_dir / "paper.txt"

    meta_path.write_text(json.dumps(asdict(paper), ensure_ascii=False, indent=2), encoding="utf-8")

    if text_path.exists() and text_path.stat().st_size > 0:
        return paper, text_path.read_text(encoding="utf-8")[:max_chars], True

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        _download(paper.pdf_url, pdf_path)

    text = _extract_pdf_text(pdf_path, max_pages=max_pages, max_chars=max_chars)
    text_path.write_text(text, encoding="utf-8")
    return paper, text, bool(text.strip())


def format_paper_search_results(papers: list[Paper]) -> str:
    if not papers:
        return "没有从 arXiv 搜到明确相关的论文。"

    lines: list[str] = []
    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.authors[:4]) or "unknown authors"
        lines.append(
            "\n".join(
                [
                    f"{index}. {paper.title}",
                    f"arXiv：{paper.paper_id}",
                    f"链接：{paper.abs_url}",
                    f"作者：{authors}",
                    f"摘要：{_compact(paper.summary, 700)}",
                ]
            )
        )
    return "\n\n".join(lines)


def format_paper_detail(paper: Paper, text: str, extracted: bool) -> str:
    authors = ", ".join(paper.authors[:6]) or "unknown authors"
    lines = [
        f"论文标题：{paper.title}",
        f"arXiv：{paper.paper_id}",
        f"论文链接：{paper.abs_url}",
        f"PDF：{paper.pdf_url}",
        f"作者：{authors}",
        f"发布时间：{paper.published or 'unknown'}",
        f"摘要：{_compact(paper.summary, 1200)}",
    ]
    if extracted and text.strip():
        lines.extend(
            [
                "",
                "PDF 解析摘录（前几页/关键开头，供技术分析使用）：",
                _compact(text, 9000),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "PDF 正文解析失败或为空；当前只能基于 arXiv 元信息和摘要分析，不能声称读过全文。",
            ]
        )
    return "\n".join(lines)


def paper_ref(paper: Paper) -> dict[str, str]:
    return {
        "id": paper.paper_id,
        "title": paper.title,
        "abs_url": paper.abs_url,
        "pdf_url": paper.pdf_url,
    }


def _resolve_paper(identifier_or_query: str) -> Paper:
    papers = search_arxiv(identifier_or_query, limit=1)
    if not papers:
        raise RuntimeError(f"没有找到 arXiv 论文：{identifier_or_query}")
    return papers[0]


def _build_search_query(query: str) -> str:
    if re.search(r"\b(?:all|ti|abs|au|cat):", query):
        return query
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{1,}|\d{4}\.\d{4,5}", query)
    stopwords = {
        "about",
        "and",
        "are",
        "for",
        "from",
        "into",
        "of",
        "on",
        "the",
        "to",
        "use",
        "with",
    }
    terms = [token for token in tokens if token.lower() not in stopwords]
    if len(terms) >= 2:
        return " AND ".join(f"all:{term}" for term in terms[:8])
    return f"all:{query}"


def _entry_to_paper(entry: ET.Element) -> Paper:
    entry_id = _text(entry, "id")
    paper_id = extract_arxiv_identifier(entry_id) or entry_id.rsplit("/", 1)[-1]
    title = _normalize_ws(_text(entry, "title"))
    summary = _normalize_ws(_text(entry, "summary"))
    authors = [
        _normalize_ws(_text(author, "name"))
        for author in entry.findall(f"{ATOM_NS}author")
        if _normalize_ws(_text(author, "name"))
    ]
    pdf_url = ""
    for link in entry.findall(f"{ATOM_NS}link"):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            pdf_url = link.attrib.get("href", "")
            break
    abs_url = entry_id.replace("http://", "https://")
    if not pdf_url and paper_id:
        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
    return Paper(
        paper_id=paper_id,
        title=title,
        summary=summary,
        authors=authors,
        published=_text(entry, "published"),
        abs_url=abs_url,
        pdf_url=pdf_url.replace("http://", "https://"),
    )


def _text(node: ET.Element, tag: str) -> str:
    child = node.find(f"{ATOM_NS}{tag}")
    return child.text.strip() if child is not None and child.text else ""


def _get_url(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _download(url: str, path: Path) -> None:
    data = _get_url(url, timeout=45)
    path.write_bytes(data)


def _extract_pdf_text(path: Path, max_pages: int, max_chars: int) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise RuntimeError("缺少 pypdf，无法解析 PDF 正文") from exc

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages[: max(1, max_pages)]:
        if len("\n".join(pages)) >= max_chars:
            break
        pages.append(page.extract_text() or "")
    return _normalize_pdf_text("\n\n".join(pages))[:max_chars]


def _normalize_pdf_text(value: str) -> str:
    text = value.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _compact(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _safe_paper_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe or "unknown"
