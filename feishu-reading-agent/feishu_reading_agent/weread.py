from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from .trace import InteractionTrace


WEREAD_GATEWAY_URL = "https://i.weread.qq.com/api/agent/gateway"
WEREAD_SKILL_VERSION = "1.0.4"


def _summarize_weread_response(api_name: str, data: dict[str, Any]) -> dict[str, Any]:
    if api_name == "/shelf/sync":
        books = data.get("books") if isinstance(data.get("books"), list) else []
        albums = data.get("albums") if isinstance(data.get("albums"), list) else []
        return {
            "books": len(books),
            "albums": len(albums),
            "has_mp": bool(data.get("mp")),
        }

    if api_name == "/store/search":
        books = _iter_search_books(data)
        return {
            "book_count": len(books),
            "top_books": [
                {
                    "bookId": book.get("bookId"),
                    "title": book.get("title"),
                    "author": book.get("author"),
                }
                for book in books[:5]
            ],
        }

    if api_name == "/book/chapterinfo":
        chapters = data.get("chapters") if isinstance(data.get("chapters"), list) else []
        return {
            "chapter_count": len(chapters),
            "top_chapters": [
                {"chapterUid": item.get("chapterUid"), "title": item.get("title")}
                for item in chapters[:8]
                if isinstance(item, dict)
            ],
        }

    if api_name == "/book/bestbookmarks":
        items = data.get("items") if isinstance(data.get("items"), list) else []
        return {"item_count": len(items)}

    if api_name in {"/review/list", "/review/list/mine"}:
        reviews = data.get("reviews") if isinstance(data.get("reviews"), list) else []
        return {
            "review_count": len(reviews),
            "has_more": data.get("hasMore") or data.get("reviewsHasMore"),
        }

    if api_name == "/book/bookmarklist":
        updated = data.get("updated") if isinstance(data.get("updated"), list) else []
        return {"highlight_count": len(updated)}

    return {"keys": sorted(data.keys())[:20]}


def call_weread_gateway(
    api_key: str,
    api_name: str,
    trace: InteractionTrace | None = None,
    **params: Any,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("WEREAD_API_KEY is not configured")

    started_at = time.monotonic()
    if trace:
        trace.event("weread_request", api_name=api_name, params=params)

    body = {
        "api_name": api_name,
        "skill_version": WEREAD_SKILL_VERSION,
        **params,
    }
    request = urllib.request.Request(
        WEREAD_GATEWAY_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        if trace:
            trace.event(
                "weread_error",
                api_name=api_name,
                params=params,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                error=f"HTTP {exc.code} {text[:500]}",
            )
        raise RuntimeError(f"WeRead API failed: HTTP {exc.code} {text[:500]}") from exc
    except urllib.error.URLError as exc:
        if trace:
            trace.event(
                "weread_error",
                api_name=api_name,
                params=params,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                error=str(exc),
            )
        raise RuntimeError(f"WeRead API network failed: {exc}") from exc

    if isinstance(data, dict) and data.get("upgrade_info"):
        if trace:
            trace.event(
                "weread_error",
                api_name=api_name,
                params=params,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                error="upgrade_required",
                upgrade_info=data.get("upgrade_info"),
            )
        raise RuntimeError(f"WeRead skill requires upgrade: {data['upgrade_info']}")

    errcode = data.get("errcode") if isinstance(data, dict) else None
    if errcode not in (None, 0):
        errmsg = data.get("errmsg") or data.get("msg") or "unknown error"
        if trace:
            trace.event(
                "weread_error",
                api_name=api_name,
                params=params,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                errcode=errcode,
                error=errmsg,
            )
        raise RuntimeError(f"WeRead API returned errcode={errcode}: {errmsg}")

    if trace:
        trace.event(
            "weread_response",
            api_name=api_name,
            params=params,
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
            summary=_summarize_weread_response(api_name, data if isinstance(data, dict) else {}),
            response=data,
        )
    return data


def _format_timestamp(value: Any) -> str:
    if not isinstance(value, (int, float)) or value <= 0:
        return ""
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d")


def summarize_shelf(data: dict[str, Any], limit: int = 12) -> str:
    books = data.get("books") if isinstance(data.get("books"), list) else []
    albums = data.get("albums") if isinstance(data.get("albums"), list) else []
    mp = data.get("mp")
    mp_count = 1 if mp else 0
    total = len(books) + len(albums) + mp_count

    recent_books = sorted(
        [item for item in books if isinstance(item, dict)],
        key=lambda item: item.get("readUpdateTime") or 0,
        reverse=True,
    )[:limit]

    lines = [
        f"书架可见条目：{total} 个",
        f"电子书：{len(books)} 个",
        f"有声书/专辑：{len(albums)} 个",
        f"文章收藏入口：{mp_count} 个",
    ]

    if recent_books:
        lines.append("最近阅读的电子书：")
        for item in recent_books:
            title = item.get("title") or "未命名"
            author = item.get("author") or "未知作者"
            read_date = _format_timestamp(item.get("readUpdateTime"))
            suffix = f"（最近阅读：{read_date}）" if read_date else ""
            lines.append(f"- {title} / {author}{suffix}")

    if books:
        lines.append("书架完整电子书清单（用于严格判断书架内/外）：")
        for item in books:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or "未命名"
            author = item.get("author") or "未知作者"
            lines.append(f"- {title} / {author}")

    return "\n".join(lines)


def fetch_shelf_context(api_key: str, trace: InteractionTrace | None = None) -> str:
    data = call_weread_gateway(api_key, "/shelf/sync", trace=trace)
    return summarize_shelf(data)


def _iter_search_books(data: dict[str, Any]) -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    results = data.get("results")
    if not isinstance(results, list):
        return books

    for group in results:
        if not isinstance(group, dict):
            continue
        group_books = group.get("books")
        if not isinstance(group_books, list):
            continue
        for item in group_books:
            if not isinstance(item, dict):
                continue
            book_info = item.get("bookInfo")
            if isinstance(book_info, dict) and book_info.get("bookId"):
                books.append(book_info)
    return books


def search_books(
    api_key: str,
    keyword: str,
    count: int = 3,
    trace: InteractionTrace | None = None,
) -> list[dict[str, Any]]:
    data = call_weread_gateway(api_key, "/store/search", trace=trace, keyword=keyword, scope=10, count=count)
    return _iter_search_books(data)[:count]


def _truncate_text(value: Any, max_chars: int = 180) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


def _chapter_titles(chapters: Any) -> dict[str, str]:
    if not isinstance(chapters, list):
        return {}
    titles: dict[str, str] = {}
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_uid = chapter.get("chapterUid")
        title = chapter.get("title")
        if chapter_uid is not None and isinstance(title, str) and title:
            titles[str(chapter_uid)] = title
    return titles


def _chapter_label(chapter_uid: Any, chapter_titles: dict[str, str]) -> str:
    if chapter_uid is None:
        return ""
    return chapter_titles.get(str(chapter_uid), f"chapterUid={chapter_uid}")


def _summarize_chapters(chapters: list[Any], max_chapters: int = 40) -> list[str]:
    lines: list[str] = []
    for chapter in chapters[:max_chapters]:
        if not isinstance(chapter, dict):
            continue
        title = chapter.get("title")
        if not title:
            continue
        idx = chapter.get("chapterIdx")
        level = chapter.get("level")
        prefix = f"{idx}. " if isinstance(idx, int) else ""
        indent = "  " * max(int(level or 1) - 1, 0)
        lines.append(f"{indent}- {prefix}{title}")
    return lines


def _summarize_best_bookmarks(data: dict[str, Any], max_items: int = 5) -> list[str]:
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return []

    chapter_titles = _chapter_titles(data.get("chapters"))
    lines = ["- 内容片段证据 - 热门划线（不是全文）："]
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        mark_text = _truncate_text(item.get("markText"), 160)
        if not mark_text:
            continue
        chapter = _chapter_label(item.get("chapterUid"), chapter_titles)
        count = item.get("totalCount")
        suffix_parts = []
        if chapter:
            suffix_parts.append(f"章节：{chapter}")
        if isinstance(count, int):
            suffix_parts.append(f"{count} 人划线")
        suffix = f"（{'，'.join(suffix_parts)}）" if suffix_parts else ""
        lines.append(f"  - {mark_text}{suffix}")
    return lines if len(lines) > 1 else []


def _public_review_payload(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    wrapper = item.get("review")
    if not isinstance(wrapper, dict):
        return {}
    inner = wrapper.get("review")
    if isinstance(inner, dict):
        return inner
    return wrapper


def _summarize_public_reviews(data: dict[str, Any], max_reviews: int = 3) -> list[str]:
    reviews = data.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        return []

    lines = ["- 公开点评佐证（他人观点，不代表原文）："]
    for item in reviews[:max_reviews]:
        review = _public_review_payload(item)
        content = _truncate_text(review.get("content") or review.get("htmlContent"), 180)
        if not content:
            continue
        chapter_name = review.get("chapterName")
        star = review.get("star")
        suffix_parts = []
        if isinstance(chapter_name, str) and chapter_name:
            suffix_parts.append(f"章节点评：{chapter_name}")
        if isinstance(star, int) and star > 0:
            suffix_parts.append(f"评分：{star}/100")
        suffix = f"（{'，'.join(suffix_parts)}）" if suffix_parts else ""
        lines.append(f"  - {content}{suffix}")
    return lines if len(lines) > 1 else []


def _summarize_personal_highlights(data: dict[str, Any], max_items: int = 4) -> list[str]:
    highlights = data.get("updated")
    if not isinstance(highlights, list) or not highlights:
        return []

    chapter_titles = _chapter_titles(data.get("chapters"))
    lines = ["- 你的个人划线佐证："]
    for item in highlights[:max_items]:
        if not isinstance(item, dict):
            continue
        mark_text = _truncate_text(item.get("markText"), 160)
        if not mark_text:
            continue
        chapter = _chapter_label(item.get("chapterUid"), chapter_titles)
        suffix = f"（章节：{chapter}）" if chapter else ""
        lines.append(f"  - {mark_text}{suffix}")
    return lines if len(lines) > 1 else []


def _summarize_personal_reviews(data: dict[str, Any], max_items: int = 3) -> list[str]:
    reviews = data.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        return []

    lines = ["- 你的个人想法/点评佐证："]
    for item in reviews[:max_items]:
        if not isinstance(item, dict):
            continue
        review = item.get("review")
        if not isinstance(review, dict):
            continue
        abstract = _truncate_text(review.get("abstract"), 120)
        content = _truncate_text(review.get("content"), 160)
        chapter_name = review.get("chapterName")
        if not abstract and not content:
            continue
        prefix_parts = []
        if isinstance(chapter_name, str) and chapter_name:
            prefix_parts.append(f"章节：{chapter_name}")
        prefix = f"（{'，'.join(prefix_parts)}）" if prefix_parts else ""
        if abstract and content:
            lines.append(f"  - 原文：{abstract}；想法：{content}{prefix}")
        elif abstract:
            lines.append(f"  - 原文：{abstract}{prefix}")
        else:
            lines.append(f"  - 想法：{content}{prefix}")
    return lines if len(lines) > 1 else []


def _fetch_book_evidence_lines(api_key: str, book_id: str, trace: InteractionTrace | None = None) -> list[str]:
    lines: list[str] = []
    has_content_evidence = False

    evidence_fetchers = [
        (
            "热门划线获取失败",
            lambda: _summarize_best_bookmarks(
                call_weread_gateway(api_key, "/book/bestbookmarks", trace=trace, bookId=book_id, chapterUid=0)
            ),
        ),
        (
            "公开点评获取失败",
            lambda: _summarize_public_reviews(
                call_weread_gateway(api_key, "/review/list", trace=trace, bookId=book_id, reviewListType=1, count=3)
            ),
        ),
        (
            "个人划线获取失败",
            lambda: _summarize_personal_highlights(
                call_weread_gateway(api_key, "/book/bookmarklist", trace=trace, bookId=book_id)
            ),
        ),
        (
            "个人想法获取失败",
            lambda: _summarize_personal_reviews(
                call_weread_gateway(api_key, "/review/list/mine", trace=trace, bookid=book_id, count=3)
            ),
        ),
    ]

    for error_label, fetcher in evidence_fetchers:
        try:
            evidence_lines = fetcher()
            if evidence_lines:
                has_content_evidence = True
            lines.extend(evidence_lines)
        except Exception as exc:
            lines.append(f"- {error_label}：{exc}")

    if not has_content_evidence:
        lines.append("- 内容片段证据：未获取到热门划线、公开点评或你的个人笔记；不要推断正文内容，输出依据时必须标注“正文未验证”。")
    return lines


def fetch_verified_materials_context(
    api_key: str,
    queries: list[str],
    max_queries: int = 4,
    max_books_per_query: int = 1,
    phase: str = "initial",
    trace: InteractionTrace | None = None,
) -> str:
    chunks: list[str] = []
    seen: set[str] = set()
    if trace:
        trace.event(
            "material_verification_start",
            phase=phase,
            queries=queries,
            max_queries=max_queries,
            max_books_per_query=max_books_per_query,
        )

    for raw_query in queries:
        query = raw_query.strip()
        if not query or query in seen:
            continue
        seen.add(query)
        if len(seen) > max_queries:
            break

        chunks.append(f"## 查询：{query}")
        try:
            books = search_books(api_key, query, count=2, trace=trace)
        except Exception as exc:
            chunks.append(f"- 微信读书搜索失败：{exc}")
            continue

        if not books:
            chunks.append("- 微信读书未找到明确匹配书籍。若推荐该方向，只能作为关键词/概念搜索，不能编造章节。")
            continue

        if trace:
            trace.event(
                "material_search_results",
                query=query,
                books=[
                    {
                        "bookId": book.get("bookId"),
                        "title": book.get("title"),
                        "author": book.get("author"),
                    }
                    for book in books
                ],
            )

        chunks.append("- 注意：以下是微信读书搜索/目录验证结果，只能证明该书可检索、目录可验证；不能证明它在用户书架内。")
        chunks.append("- 验证边界：微信读书 skill 不提供章节全文；内容判断只能来自简介、目录、热门划线、公开点评和你的个人笔记。")
        for book in books[:max_books_per_query]:
            book_id = str(book.get("bookId") or "")
            title = book.get("title") or "未命名"
            author = book.get("author") or "未知作者"
            publisher = book.get("publisher") or ""
            category = book.get("category") or ""
            chunks.append(f"### {title} / {author}")
            chunks.append(f"- bookId: {book_id}")
            if publisher:
                chunks.append(f"- 出版社：{publisher}")
            if category:
                chunks.append(f"- 分类：{category}")
            intro = (book.get("intro") or "").strip()
            if intro:
                chunks.append(f"- 简介：{intro[:500]}")

            if not book_id:
                chunks.append("- 无 bookId，无法验证目录。")
                continue

            try:
                chapter_data = call_weread_gateway(api_key, "/book/chapterinfo", trace=trace, bookId=book_id)
            except Exception as exc:
                chunks.append(f"- 目录获取失败：{exc}")
                continue

            chapters = chapter_data.get("chapters")
            if not isinstance(chapters, list) or not chapters:
                chunks.append("- 未返回目录。不要编造章节号；只能推荐书名内搜索关键词。")
                continue

            chunks.append("- 位置证据 - 可验证目录片段：")
            chunks.extend(_summarize_chapters(chapters))
            chunks.append("- 证据使用规则：目录只证明章节位置存在；如果下面没有内容片段证据，不能声称已验证章节内容。")
            chunks.extend(_fetch_book_evidence_lines(api_key, book_id, trace=trace))

    context = "\n".join(chunks).strip()
    if trace:
        trace.event("verified_materials_context", chars=len(context), preview=context[:8000])
    return context
