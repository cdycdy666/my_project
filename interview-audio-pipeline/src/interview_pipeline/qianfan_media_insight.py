from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import QianfanSettings
from .mcp_client import McpTool, StreamableHttpMcpClient
from .models import InterviewInput, MediaInsightResult, TranscriptSegment


@dataclass
class ToolSelection:
    create_tool: McpTool
    status_tool: McpTool
    result_tool: McpTool | None


class QianfanMediaInsightService:
    def __init__(self, settings: QianfanSettings) -> None:
        self._settings = settings
        self._client = StreamableHttpMcpClient(
            url=settings.mcp_url,
            bearer_token=settings.bearer_token,
            protocol_version=settings.protocol_version,
            disable_proxy=settings.disable_proxy,
        )
        self._tool_selection: ToolSelection | None = None

    def run(self, interview: InterviewInput) -> MediaInsightResult:
        selection = self._ensure_tool_selection()
        submit_args = _build_submit_args(selection.create_tool, interview)
        submit_payload = self._client.call_tool(selection.create_tool.name, submit_args)
        task_id = _extract_task_id(submit_payload)
        if not task_id:
            raise RuntimeError(f"Could not extract task id from submit payload: {submit_payload}")

        completed_payload = self._wait_for_completion(task_id, selection)
        if selection.result_tool and not _payload_contains_content(completed_payload):
            result_payload = self._client.call_tool(
                selection.result_tool.name,
                _build_lookup_args(selection.result_tool, task_id),
            )
        else:
            result_payload = completed_payload

        self._persist_raw_result(interview, task_id, result_payload)
        return _normalize_media_result(task_id=task_id, payload=result_payload)

    def describe_tools(self) -> dict[str, Any]:
        tools = self._client.list_tools()
        selected_names: dict[str, str] = {}
        selection_error: str | None = None

        try:
            selection = self._tool_selection or self._select_tools(tools)
            self._tool_selection = selection
            selected_names = {
                selection.create_tool.name: "create",
                selection.status_tool.name: "status",
            }
            if selection.result_tool is not None:
                selected_names[selection.result_tool.name] = "result"
        except Exception as exc:
            selection = None
            selection_error = str(exc)

        return {
            "selected_tools": {
                "create": selection.create_tool.name if selection else None,
                "status": selection.status_tool.name if selection else None,
                "result": selection.result_tool.name if selection and selection.result_tool else None,
            },
            "selection_error": selection_error,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "selected_as": selected_names.get(tool.name),
                }
                for tool in tools
            ],
        }

    def _wait_for_completion(self, task_id: str, selection: ToolSelection) -> dict[str, Any]:
        deadline = time.monotonic() + self._settings.timeout_seconds
        while time.monotonic() < deadline:
            payload = self._client.call_tool(
                selection.status_tool.name,
                _build_lookup_args(selection.status_tool, task_id),
            )
            status = _extract_status(payload).lower()
            if status in {"succeeded", "success", "completed", "done", "finished"}:
                return payload
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"Media insight task {task_id} failed with payload: {payload}")
            time.sleep(self._settings.poll_interval_seconds)
        raise TimeoutError(
            f"Media insight task {task_id} timed out after {self._settings.timeout_seconds} seconds"
        )

    def _ensure_tool_selection(self) -> ToolSelection:
        if self._tool_selection is not None:
            return self._tool_selection

        tools = self._client.list_tools()
        self._tool_selection = self._select_tools(tools)
        return self._tool_selection

    def _select_tools(self, tools: list[McpTool]) -> ToolSelection:
        by_name = {tool.name: tool for tool in tools}

        create_tool = _pick_tool(
            tools,
            explicit_name=self._settings.create_tool,
            fallback_keywords=("create", "submit", "start", "taskcreate"),
            required_keywords=(),
            by_name=by_name,
        )
        status_tool = _pick_tool(
            tools,
            explicit_name=self._settings.status_tool,
            fallback_keywords=("status", "query", "get", "detail", "querytask"),
            required_keywords=(),
            by_name=by_name,
        )
        result_tool = None
        if self._settings.result_tool:
            result_tool = _pick_tool(
                tools,
                explicit_name=self._settings.result_tool,
                fallback_keywords=("result", "get", "detail", "querytask"),
                required_keywords=(),
                by_name=by_name,
            )
        else:
            candidates = _filter_tools(
                tools,
                fallback_keywords=("result", "transcript", "summary", "querytask"),
                required_keywords=(),
            )
            result_tool = candidates[0] if candidates else None

        return ToolSelection(
            create_tool=create_tool,
            status_tool=status_tool,
            result_tool=result_tool,
        )

    def _persist_raw_result(self, interview: InterviewInput, task_id: str, payload: dict[str, Any]) -> None:
        output_dir = self._settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_candidate = interview.safe_label()
        file_path = output_dir / f"{interview.interview_date.isoformat()}_{safe_candidate}_{task_id}.json"
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _pick_tool(
    tools: list[McpTool],
    *,
    explicit_name: str | None,
    fallback_keywords: tuple[str, ...],
    required_keywords: tuple[str, ...],
    by_name: dict[str, McpTool],
) -> McpTool:
    if explicit_name:
        tool = by_name.get(explicit_name)
        if not tool:
            raise RuntimeError(f"Configured MCP tool not found: {explicit_name}")
        return tool

    candidates = _filter_tools(
        tools,
        fallback_keywords=fallback_keywords,
        required_keywords=required_keywords,
    )
    if not candidates:
        raise RuntimeError(
            f"Could not discover MCP tool for keywords {fallback_keywords}. "
            "Set QIANFAN_CREATE_TOOL / QIANFAN_STATUS_TOOL / QIANFAN_RESULT_TOOL explicitly."
        )
    return candidates[0]


def _filter_tools(
    tools: list[McpTool],
    *,
    fallback_keywords: tuple[str, ...],
    required_keywords: tuple[str, ...],
) -> list[McpTool]:
    scored: list[tuple[int, McpTool]] = []
    for tool in tools:
        haystack = f"{tool.name} {tool.description}".lower()
        if not all(keyword in haystack for keyword in required_keywords):
            continue
        score = sum(keyword in haystack for keyword in fallback_keywords)
        if score:
            scored.append((score, tool))
    return [tool for _, tool in sorted(scored, key=lambda item: item[0], reverse=True)]


def _build_submit_args(tool: McpTool, interview: InterviewInput) -> dict[str, Any]:
    args: dict[str, Any] = {}
    schema = tool.input_schema or {}
    properties = schema.get("properties", {})

    url_key = _pick_field_name(
        properties.keys(),
        ("url", "audio_url", "media_url", "file_url", "source_url", "download_url"),
    )
    if not url_key:
        raise RuntimeError(f"Could not find audio url field in schema for tool {tool.name}")
    args[url_key] = interview.audio_url

    metadata_candidates = {
        "candidate": interview.record_title(),
        "candidate_name": interview.record_title(),
        "name": interview.record_title(),
        "role": interview.role,
        "job": interview.role,
        "position": interview.role,
        "round": interview.round,
        "interview_round": interview.round,
        "date": interview.interview_date.isoformat(),
        "interview_date": interview.interview_date.isoformat(),
        "title": f"{interview.record_title()} - {interview.role} - {interview.round}",
    }
    for field_name, field_value in metadata_candidates.items():
        if field_name in properties and field_name not in args:
            args[field_name] = field_value
    return args


def _build_lookup_args(tool: McpTool, task_id: str) -> dict[str, Any]:
    schema = tool.input_schema or {}
    properties = schema.get("properties", {})
    task_key = _pick_field_name(properties.keys(), ("task_id", "taskId", "id", "job_id", "jobId"))
    if not task_key:
        raise RuntimeError(f"Could not find task id field in schema for tool {tool.name}")
    return {task_key: task_id}


def _pick_field_name(candidates: Any, preferred_names: tuple[str, ...]) -> str | None:
    candidate_list = list(candidates)
    lower_map = {item.lower(): item for item in candidate_list if isinstance(item, str)}
    for name in preferred_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def _extract_task_id(payload: Any) -> str | None:
    return _find_first_string(payload, {"task_id", "taskid", "id", "job_id", "jobid"})


def _extract_status(payload: Any) -> str:
    status = _find_first_string(payload, {"status", "state", "task_status", "job_status"})
    return status or "unknown"


def _payload_contains_content(payload: dict[str, Any]) -> bool:
    return bool(
        _find_first_string(payload, {"transcript", "transcript_text", "summary", "abstract"})
        or _find_first_list(payload, {"segments", "utterances", "chapters"})
    )


def _normalize_media_result(task_id: str, payload: dict[str, Any]) -> MediaInsightResult:
    transcript_text = (
        _find_first_string(payload, {"transcript_text", "transcript", "full_text", "text"}) or ""
    )
    summary = _find_first_string(payload, {"summary", "abstract", "memo", "digest"}) or ""
    transcript_url = _find_first_string(payload, {"transcript_url", "result_url", "download_url"})
    key_points = _normalize_string_list(
        _find_first_list(payload, {"key_points", "highlights", "points", "keywords"})
    )
    chapters = _normalize_string_list(
        _find_first_list(payload, {"chapters", "sections", "outline", "paragraphs"})
    )
    segments = _normalize_segments(
        _find_first_list(payload, {"segments", "utterances", "sentences", "transcripts"})
    )
    if not transcript_text and segments:
        transcript_text = "\n".join(segment.text for segment in segments if segment.text)

    return MediaInsightResult(
        task_id=task_id,
        status=_extract_status(payload),
        transcript_text=transcript_text,
        summary=summary,
        key_points=key_points,
        chapters=chapters,
        segments=segments,
        transcript_url=transcript_url,
        raw_payload=payload,
    )


def _normalize_string_list(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    normalized: list[str] = []
    for item in raw_value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(text)
        elif isinstance(item, dict):
            text = _find_first_string(item, {"text", "summary", "title", "content"})
            if text:
                normalized.append(text)
    return normalized


def _normalize_segments(raw_value: Any) -> list[TranscriptSegment]:
    if not isinstance(raw_value, list):
        return []
    segments: list[TranscriptSegment] = []
    for item in raw_value:
        if isinstance(item, str) and item.strip():
            segments.append(TranscriptSegment(text=item.strip()))
            continue
        if not isinstance(item, dict):
            continue
        text = _find_first_string(item, {"text", "content", "sentence", "transcript"})
        if not text:
            continue
        speaker = _find_first_string(item, {"speaker", "speaker_name", "role"})
        start = _find_first_number(item, {"start", "start_time", "begin"})
        end = _find_first_number(item, {"end", "end_time", "finish"})
        segments.append(TranscriptSegment(text=text, start=start, end=end, speaker=speaker))
    return segments


def _find_first_string(payload: Any, keys: set[str]) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in keys and isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            found = _find_first_string(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_string(item, keys)
            if found:
                return found
    return None


def _find_first_number(payload: Any, keys: set[str]) -> float | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in keys and isinstance(value, (int, float)):
                return float(value)
        for value in payload.values():
            found = _find_first_number(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_number(item, keys)
            if found is not None:
                return found
    return None


def _find_first_list(payload: Any, keys: set[str]) -> list[Any] | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in keys and isinstance(value, list):
                return value
        for value in payload.values():
            found = _find_first_list(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_list(item, keys)
            if found:
                return found
    return None
