from __future__ import annotations

import math
from typing import Any

from .config import NotionSettings
from .http import HttpClient
from .models import InterviewInput, MediaInsightResult, StructuredAssessment


class NotionClient:
    def __init__(self, settings: NotionSettings) -> None:
        self._settings = settings
        self._http = HttpClient()
        self._database_cache: dict[str, Any] | None = None

    def create_interview_record(
        self,
        interview: InterviewInput,
        result: MediaInsightResult,
        assessment: StructuredAssessment,
        page_markdown: str,
    ) -> dict[str, Any]:
        database = self._retrieve_database()
        db_properties = database.get("properties", {})
        properties = self._build_properties(
            db_properties=db_properties,
            interview=interview,
            result=result,
            assessment=assessment,
            status_value=self._settings.status_done,
        )
        page = self._create_page(properties)
        self._append_markdown_blocks(page["id"], page_markdown)
        return page

    def update_interview_record(
        self,
        page_id: str,
        interview: InterviewInput,
        result: MediaInsightResult,
        assessment: StructuredAssessment,
        page_markdown: str,
    ) -> dict[str, Any]:
        database = self._retrieve_database()
        db_properties = database.get("properties", {})
        properties = self._build_properties(
            db_properties=db_properties,
            interview=interview,
            result=result,
            assessment=assessment,
            status_value=self._settings.status_done,
        )
        page = self._update_page_properties(page_id, properties)
        self._append_markdown_blocks(page_id, page_markdown)
        return page

    def _create_page(self, properties: dict[str, Any]) -> dict[str, Any]:
        status, _, body = self._http.request(
            "POST",
            "https://api.notion.com/v1/pages",
            headers=self._headers(),
            json_body={
                "parent": {"database_id": self._settings.database_id},
                "properties": properties,
            },
        )
        if status >= 400:
            raise RuntimeError(f"Failed to create Notion page: {body.decode('utf-8', errors='replace')}")

        return _parse_json(body)

    def _update_page_properties(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        status, _, body = self._http.request(
            "PATCH",
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=self._headers(),
            json_body={"properties": properties},
        )
        if status >= 400:
            raise RuntimeError(f"Failed to update Notion page: {body.decode('utf-8', errors='replace')}")
        return _parse_json(body)

    def inspect_database(self) -> dict[str, Any]:
        database = self._retrieve_database()
        db_properties = database.get("properties", {})
        mapping = self._settings.property_mapping
        mapped_fields = {
            "candidate": mapping.candidate,
            "role": mapping.role,
            "interview_date": mapping.interview_date,
            "round": mapping.round,
            "status": mapping.status,
            "audio_url": mapping.audio_url,
            "transcript_url": mapping.transcript_url,
            "decision": mapping.decision,
            "tags": mapping.tags,
            "summary": mapping.summary,
        }

        validation = []
        for logical_name, notion_name in mapped_fields.items():
            schema = db_properties.get(notion_name)
            validation.append(
                {
                    "field": logical_name,
                    "mapped_name": notion_name,
                    "exists": bool(schema),
                    "type": schema.get("type") if schema else None,
                }
            )

        return {
            "database_id": database.get("id"),
            "title": _extract_database_title(database),
            "url": database.get("url"),
            "properties": [
                {
                    "name": name,
                    "type": schema.get("type"),
                    "id": schema.get("id"),
                }
                for name, schema in db_properties.items()
            ],
            "mapping_validation": validation,
        }

    def _retrieve_database(self) -> dict[str, Any]:
        if self._database_cache is not None:
            return self._database_cache
        status, _, body = self._http.request(
            "GET",
            f"https://api.notion.com/v1/databases/{self._settings.database_id}",
            headers=self._headers(),
        )
        if status >= 400:
            raise RuntimeError(
                f"Failed to retrieve Notion database: {body.decode('utf-8', errors='replace')}"
            )
        self._database_cache = _parse_json(body)
        return self._database_cache

    def _append_markdown_blocks(self, page_id: str, page_markdown: str) -> None:
        blocks = build_notion_blocks(page_markdown)
        for chunk in _chunks(blocks, 100):
            status, _, append_body = self._http.request(
                "PATCH",
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=self._headers(),
                json_body={"children": chunk},
            )
            if status >= 400:
                raise RuntimeError(
                    "Failed to append Notion content: "
                    f"{append_body.decode('utf-8', errors='replace')}"
                )

    def _build_properties(
        self,
        db_properties: dict[str, Any],
        interview: InterviewInput,
        result: MediaInsightResult,
        assessment: StructuredAssessment,
        status_value: str,
    ) -> dict[str, Any]:
        mapping = self._settings.property_mapping
        values = {
            mapping.candidate: interview.record_title(),
            mapping.role: interview.role,
            mapping.interview_date: interview.interview_date.isoformat(),
            mapping.round: interview.round,
            mapping.status: status_value,
            mapping.audio_url: interview.audio_url,
            mapping.transcript_url: result.transcript_url or interview.audio_url,
            mapping.decision: _normalize_decision(assessment.recommendation),
            mapping.tags: self._settings.default_tags,
            mapping.summary: assessment.summary,
        }
        return self._build_properties_from_values(db_properties, values)

    def _build_properties_from_values(
        self,
        db_properties: dict[str, Any],
        values: dict[str, Any],
    ) -> dict[str, Any]:
        mapping = self._settings.property_mapping
        notion_properties: dict[str, Any] = {}
        for property_name, value in values.items():
            if value is None:
                continue
            schema = db_properties.get(property_name)
            if not schema:
                continue
            notion_value = _serialize_property_value(schema.get("type", ""), value)
            if notion_value is not None:
                notion_properties[property_name] = notion_value

        if mapping.candidate not in notion_properties:
            raise RuntimeError(
                f"Title property '{mapping.candidate}' was not found in the target Notion database."
            )
        return notion_properties

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.token}",
            "Notion-Version": self._settings.version,
            "Content-Type": "application/json",
        }


def build_notion_blocks(markdown_text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current_bullets: list[str] = []

    def flush_bullets() -> None:
        nonlocal current_bullets
        for bullet in current_bullets:
            blocks.extend(_rich_text_blocks("bulleted_list_item", bullet))
        current_bullets = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            flush_bullets()
            continue
        if line.startswith("### "):
            flush_bullets()
            blocks.append(_heading_block("heading_3", line[4:]))
            continue
        if line.startswith("## "):
            flush_bullets()
            blocks.append(_heading_block("heading_2", line[3:]))
            continue
        if line.startswith("- "):
            current_bullets.append(line[2:])
            continue
        flush_bullets()
        blocks.extend(_rich_text_blocks("paragraph", line))
    flush_bullets()
    return blocks


def _heading_block(block_type: str, text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [_text_object(text[:2000])],
        },
    }


def _rich_text_blocks(block_type: str, text: str) -> list[dict[str, Any]]:
    chunks = _split_text(text, 1800)
    blocks: list[dict[str, Any]] = []
    for chunk in chunks:
        blocks.append(
            {
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": [_text_object(chunk)],
                },
            }
        )
    return blocks


def _text_object(text: str) -> dict[str, Any]:
    return {"type": "text", "text": {"content": text}}


def _split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunk_count = math.ceil(len(text) / limit)
    return [text[index * limit : (index + 1) * limit] for index in range(chunk_count)]


def _serialize_property_value(property_type: str, value: Any) -> dict[str, Any] | None:
    if property_type == "title":
        return {"title": [_text_object(str(value))]}
    if property_type == "rich_text":
        return {"rich_text": [_text_object(str(value))]}
    if property_type == "url":
        return {"url": str(value)}
    if property_type == "date":
        return {"date": {"start": str(value)}}
    if property_type == "status":
        return {"status": {"name": str(value)}}
    if property_type == "select":
        return {"select": {"name": str(value)}}
    if property_type == "multi_select":
        items = value if isinstance(value, list) else [value]
        return {"multi_select": [{"name": str(item)} for item in items]}
    if property_type == "checkbox":
        return {"checkbox": bool(value)}
    if property_type == "number":
        return {"number": value}
    return None


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _parse_json(body: bytes) -> dict[str, Any]:
    import json

    return json.loads(body.decode("utf-8"))


def _extract_database_title(database: dict[str, Any]) -> str:
    title_items = database.get("title", [])
    parts: list[str] = []
    for item in title_items:
        plain_text = item.get("plain_text")
        if plain_text:
            parts.append(plain_text)
    return "".join(parts)


def _normalize_decision(value: str) -> str:
    allowed = {"强推", "推荐", "待定", "不推荐"}
    if value in allowed:
        return value
    return "待定"
