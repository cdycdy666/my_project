from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .bos_storage import BosStorageClient
from .config import AppSettings, load_settings
from .doubao_miaoji import DoubaoMiaojiService
from .formatter import (
    build_mock_interview_review_markdown,
    build_page_markdown,
    build_structured_assessment,
)
from .http import HttpClient
from .local_whisper import LocalWhisperTranscriptionService
from .models import InterviewInput, MediaInsightResult, StructuredAssessment
from .notion_client import NotionClient
from .qianfan_media_insight import QianfanMediaInsightService


@dataclass
class PipelineOutcome:
    interview: InterviewInput
    result: MediaInsightResult
    assessment: StructuredAssessment
    page_markdown: str
    review_markdown: str
    notion_page: dict[str, Any] | None = None


def execute_pipeline(
    *,
    env_file: str = ".env",
    audio_file: str | None = None,
    audio_url: str | None = None,
    candidate: str = "",
    role: str = "",
    round_name: str = "",
    interview_date_text: str = "",
    write_to_notion: bool = False,
    include_mock_review: bool = False,
) -> PipelineOutcome:
    settings = load_settings(env_file=env_file, require_notion=write_to_notion)
    resolved_audio_url = resolve_audio_url(audio_file=audio_file, audio_url=audio_url, settings=settings)
    interview_date, resolved_round, resolved_role = resolve_interview_metadata(
        audio_file=audio_file,
        role=role,
        round_name=round_name,
        interview_date_text=interview_date_text,
    )
    interview = InterviewInput(
        audio_url=resolved_audio_url,
        candidate=candidate,
        role=resolved_role,
        round=resolved_round,
        interview_date=interview_date,
        audio_file=audio_file,
    )
    result = run_transcription(settings=settings, interview=interview, audio_file=audio_file)
    assessment = build_structured_assessment(interview, result)
    page_markdown = build_page_markdown(interview, result, assessment)
    review_markdown = build_mock_interview_review_markdown(interview, result, assessment)
    notion_page = None
    if write_to_notion:
        if settings.notion is None:
            raise RuntimeError("Notion client is unavailable. Provide Notion config or disable write_to_notion.")
        notion_client = NotionClient(settings.notion)
        full_page_markdown = page_markdown
        if include_mock_review:
            full_page_markdown = f"{page_markdown}\n\n{review_markdown}"
        notion_page = notion_client.create_interview_record(
            interview=interview,
            result=result,
            assessment=assessment,
            page_markdown=full_page_markdown,
        )
    return PipelineOutcome(
        interview=interview,
        result=result,
        assessment=assessment,
        page_markdown=page_markdown,
        review_markdown=review_markdown,
        notion_page=notion_page,
    )


def resolve_audio_url(*, audio_file: str | None, audio_url: str | None, settings: AppSettings) -> str | None:
    if audio_url:
        return audio_url
    if not audio_file:
        return None
    if settings.bos is None:
        return None
    client = BosStorageClient(settings.bos)
    result = client.upload_file(audio_file)
    return result.signed_url


def resolve_interview_metadata(
    *,
    audio_file: str | None,
    role: str,
    round_name: str,
    interview_date_text: str,
) -> tuple[date, str, str]:
    inferred_date = infer_date_from_audio_path(audio_file)
    inferred_round = infer_round_from_audio_path(audio_file)
    interview_date = date.fromisoformat(interview_date_text) if interview_date_text else inferred_date or date.today()
    resolved_round = (round_name or inferred_round or "待补充").strip()
    resolved_role = (role or "待补充").strip()
    return interview_date, resolved_round, resolved_role


def infer_date_from_audio_path(audio_file: str | None) -> date | None:
    if not audio_file:
        return None
    stem = Path(audio_file).stem
    matched = re.search(r"(?<!\d)(\d{2})(\d{2})(?!\d)", stem)
    if not matched:
        return None
    month = int(matched.group(1))
    day = int(matched.group(2))
    year = date.today().year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def infer_round_from_audio_path(audio_file: str | None) -> str | None:
    if not audio_file:
        return None
    stem = Path(audio_file).stem
    candidates = ("初筛", "一面", "二面", "三面", "四面", "终面", "HR面", "hr面")
    for item in candidates:
        if item in stem:
            return "HR面" if item == "hr面" else item
    return None


def run_transcription(*, settings: AppSettings, interview: InterviewInput, audio_file: str | None):
    provider = settings.transcription_provider
    if provider == "qianfan":
        media_service = QianfanMediaInsightService(settings.qianfan)
        return media_service.run(interview)
    if provider == "doubao_miaoji":
        media_service = DoubaoMiaojiService(settings.doubao_miaoji)
        return media_service.run(interview)
    if provider == "local_whisper":
        cleanup_path: Path | None = None
        local_audio_file = audio_file
        if not local_audio_file:
            if not interview.audio_url:
                raise RuntimeError("TRANSCRIPTION_PROVIDER=local_whisper requires an audio_file or audio_url.")
            cleanup_path = _download_audio_to_tempfile(
                interview.audio_url,
                disable_proxy=settings.bos.disable_proxy if settings.bos else False,
            )
            local_audio_file = str(cleanup_path)
        media_service = LocalWhisperTranscriptionService(settings.local_whisper)
        try:
            return media_service.run(local_audio_file)
        finally:
            if cleanup_path is not None:
                cleanup_path.unlink(missing_ok=True)
    raise RuntimeError(f"Unsupported transcription provider: {provider}")


def _download_audio_to_tempfile(audio_url: str, *, disable_proxy: bool) -> Path:
    client = HttpClient()
    status, _headers, payload = client.request(
        "GET",
        audio_url,
        disable_proxy=disable_proxy,
        timeout=300,
    )
    if status >= 400:
        raise RuntimeError(f"Failed to download remote audio for local_whisper: HTTP {status}")

    suffix = Path(urlparse(audio_url).path).suffix or ".bin"
    with tempfile.NamedTemporaryFile(prefix="local-whisper-url-", suffix=suffix, delete=False) as handle:
        handle.write(payload)
        return Path(handle.name)
