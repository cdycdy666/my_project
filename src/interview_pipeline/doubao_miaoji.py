from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .config import DoubaoMiaojiSettings
from .http import HttpClient
from .models import InterviewInput, MediaInsightResult, QuestionAnswerPair, TranscriptSegment


class DoubaoMiaojiService:
    def __init__(self, settings: DoubaoMiaojiSettings) -> None:
        self._settings = settings
        self._http = HttpClient()

    def run(self, interview: InterviewInput) -> MediaInsightResult:
        if not interview.audio_url:
            raise RuntimeError("Doubao Miaoji requires a downloadable audio URL.")

        request_id = str(uuid.uuid4())
        status, headers, body = self._http.request(
            "POST",
            self._settings.submit_url,
            headers=self._headers(request_id),
            json_body=_build_submit_payload(self._settings, interview.audio_url),
            disable_proxy=self._settings.disable_proxy,
            timeout=60,
        )
        _raise_if_http_error(status, body, "submit Doubao Miaoji task")
        _raise_if_api_error(headers, body, "submit Doubao Miaoji task")
        submit_payload = _parse_json_bytes(body)
        task_id = _extract_submit_task_id(submit_payload, headers, request_id)

        payload = self._wait_for_completion(task_id)
        payload = self._hydrate_result_files(payload)
        self._persist_raw_result(interview, task_id, payload)
        return _normalize_media_result(task_id, payload)

    def _wait_for_completion(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self._settings.timeout_seconds
        while time.monotonic() < deadline:
            status, headers, body = self._http.request(
                "POST",
                self._settings.query_url,
                headers=self._headers(task_id),
                json_body=_build_query_payload(task_id),
                disable_proxy=self._settings.disable_proxy,
                timeout=60,
            )
            _raise_if_http_error(status, body, "query Doubao Miaoji task")
            _raise_if_api_error(headers, body, "query Doubao Miaoji task")

            payload = _parse_json_bytes(body)
            task_status = _extract_status(payload).lower()
            if task_status in {"succeeded", "success", "completed", "done", "finished"}:
                return payload
            if _payload_contains_content(payload) and task_status in {"unknown", "processing", "running"}:
                return payload
            if task_status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"Doubao Miaoji task {task_id} failed: {json.dumps(payload, ensure_ascii=False)}")
            time.sleep(self._settings.poll_interval_seconds)

        raise TimeoutError(
            f"Doubao Miaoji task {task_id} timed out after {self._settings.timeout_seconds} seconds"
        )

    def _headers(self, task_id: str) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Api-Resource-Id": self._settings.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
        }
        if self._settings.api_key:
            headers["X-Api-Key"] = self._settings.api_key
        else:
            headers["X-Api-App-Key"] = self._settings.app_key
            headers["X-Api-Access-Key"] = self._settings.access_key
        return headers

    def _persist_raw_result(self, interview: InterviewInput, task_id: str, payload: dict[str, Any]) -> None:
        output_dir = self._settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_candidate = interview.safe_label()
        file_path = output_dir / f"{interview.interview_date.isoformat()}_{safe_candidate}_{task_id}_doubao_miaoji.json"
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _hydrate_result_files(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = payload.get("Data", {}).get("Result", {})
        if not isinstance(result, dict):
            return payload

        hydrated = dict(payload)
        data = dict(hydrated.get("Data", {}))
        data_result = dict(result)

        for field_name in (
            "AudioTranscriptionFile",
            "ChapterFile",
            "InformationExtractionFile",
            "SummarizationFile",
        ):
            url = data_result.get(field_name)
            if not isinstance(url, str) or not url:
                continue
            file_payload = self._fetch_json_file(url)
            if file_payload is not None:
                data_result[f"{field_name}Payload"] = file_payload

        data["Result"] = data_result
        hydrated["Data"] = data
        return hydrated

    def _fetch_json_file(self, url: str) -> dict[str, Any] | list[Any] | None:
        status, _, body = self._http.request(
            "GET",
            url,
            disable_proxy=self._settings.disable_proxy,
            timeout=60,
        )
        if status >= 400:
            return None
        text = body.decode("utf-8", errors="replace").strip()
        if not text:
            return None
        return json.loads(text)


def _build_submit_payload(settings: DoubaoMiaojiSettings, audio_url: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "Input": {
            "Offline": {
                "FileURL": audio_url,
                "FileType": settings.file_type,
            }
        },
        "Params": {
            "AllActivate": settings.all_activate,
            "SourceLang": settings.source_lang,
            "AudioTranscriptionEnable": settings.audio_transcription_enable,
            "AudioTranscriptionParams": {
                "SpeakerIdentification": settings.speaker_identification,
                "NumberOfSpeaker": settings.number_of_speaker,
                "HotWords": settings.hot_words,
            },
            "TranslationEnable": settings.translation_enable,
            "TranslationParams": {
                "TargetLang": settings.target_lang,
            },
            "InformationExtractionEnabled": settings.information_extraction_enable,
            "InformationExtractionParams": {
                "Types": settings.information_extraction_types,
            },
            "SummarizationEnabled": settings.summarization_enable,
            "SummarizationParams": {
                "Types": settings.summarization_types,
            },
            "ChapterEnabled": settings.chapter_enable,
        },
    }
    return payload


def _build_query_payload(task_id: str) -> dict[str, Any]:
    return {
        "TaskID": task_id,
        "TaskId": task_id,
        "task_id": task_id,
    }


def _raise_if_http_error(status: int, body: bytes, action: str) -> None:
    if status >= 400:
        raise RuntimeError(f"Failed to {action}: {body.decode('utf-8', errors='replace')}")


def _raise_if_api_error(headers: dict[str, str], body: bytes, action: str) -> None:
    api_status = headers.get("X-Api-Status-Code")
    if api_status and api_status != "20000000":
        message = headers.get("X-Api-Message", "")
        raise RuntimeError(
            f"Failed to {action}: X-Api-Status-Code={api_status}, "
            f"X-Api-Message={message}, body={body.decode('utf-8', errors='replace')}"
        )


def _parse_json_bytes(body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _extract_submit_task_id(
    payload: dict[str, Any],
    headers: dict[str, str],
    fallback_request_id: str,
) -> str:
    payload_task_id = _find_first_string(payload, {"task_id", "taskid", "id", "job_id", "jobid"})
    if payload_task_id:
        return payload_task_id
    header_task_id = headers.get("X-Api-Request-Id") or headers.get("X-Request-Id")
    if header_task_id:
        return header_task_id
    return fallback_request_id


def _extract_status(payload: Any) -> str:
    status = _find_first_string(payload, {"status", "state", "task_status", "job_status", "progress"})
    return status or "unknown"


def _payload_contains_content(payload: dict[str, Any]) -> bool:
    return bool(
        _find_first_string(payload, {"transcript", "transcript_text", "summary", "abstract", "text"})
        or _find_first_list(payload, {"segments", "utterances", "chapters", "question_answer", "question_answers"})
    )


def _normalize_media_result(task_id: str, payload: dict[str, Any]) -> MediaInsightResult:
    result_root = _find_first_dict(payload, {"result"}) or payload
    transcript_payload = result_root.get("AudioTranscriptionFilePayload")
    chapter_payload = result_root.get("ChapterFilePayload")
    extraction_payload = result_root.get("InformationExtractionFilePayload")
    summarization_payload = result_root.get("SummarizationFilePayload")

    segments = _normalize_segments(
        transcript_payload
        if isinstance(transcript_payload, list)
        else _find_first_list(result_root, {"segments", "utterances", "sentences", "transcripts"})
    )
    transcript_text = "\n".join(segment.text for segment in segments if segment.text)
    if not transcript_text:
        transcript_text = (
            _find_first_string(result_root, {"transcript_text", "transcript", "full_text", "text", "audio_transcription"})
            or ""
        )

    summary = _extract_summary(summarization_payload) or _find_first_string(
        result_root, {"summary", "abstract", "full_summary", "audio_summary"}
    ) or ""
    transcript_url = _find_first_string(
        result_root, {"transcript_url", "result_url", "download_url", "audiotranscriptionfile"}
    )
    chapters = _normalize_chapters(chapter_payload)
    qa_pairs = _normalize_qa_pairs(
        extraction_payload.get("question_answer")
        if isinstance(extraction_payload, dict)
        else _find_first_list(result_root, {"question_answer", "question_answers", "qa_pairs", "qas"})
    )
    key_points = []
    if qa_pairs:
        key_points = [pair.question for pair in qa_pairs if pair.question][:5]

    return MediaInsightResult(
        task_id=task_id,
        status=_extract_status(payload),
        transcript_text=transcript_text,
        summary=summary,
        key_points=key_points,
        chapters=chapters,
        qa_pairs=qa_pairs,
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
        speaker = _extract_speaker(item)
        start = _find_first_number(item, {"start", "start_time", "begin"})
        end = _find_first_number(item, {"end", "end_time", "finish"})
        segments.append(TranscriptSegment(text=text, start=start, end=end, speaker=speaker))
    return segments


def _normalize_qa_pairs(raw_value: Any) -> list[QuestionAnswerPair]:
    if not isinstance(raw_value, list):
        return []
    pairs: list[QuestionAnswerPair] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        question = _find_first_string(item, {"question", "ask", "q"})
        answer = _find_first_string(item, {"answer", "reply", "a"})
        if question and answer:
            pairs.append(QuestionAnswerPair(question=question, answer=answer))
    return pairs


def _normalize_chapters(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, dict):
        return _normalize_string_list(raw_value)
    items = raw_value.get("chapter_summary")
    if not isinstance(items, list):
        return []
    chapters: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = _find_first_string(item, {"title"}) or ""
        summary = _clean_summary_text(_find_first_string(item, {"summary"}) or "")
        text = title.strip()
        if summary.strip():
            text = f"{text}: {summary.strip()}" if text else summary.strip()
        if text:
            chapters.append(text)
    return chapters


def _extract_summary(raw_value: Any) -> str:
    if isinstance(raw_value, dict):
        paragraph = raw_value.get("paragraph")
        if isinstance(paragraph, str) and paragraph.strip():
            return _clean_summary_text(paragraph.strip())
        title = raw_value.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return ""


def _extract_speaker(item: dict[str, Any]) -> str | None:
    speaker = item.get("speaker")
    if isinstance(speaker, dict):
        return _find_first_string(speaker, {"name", "id", "speaker_name"})
    return _find_first_string(item, {"speaker", "speaker_name", "role"})


def _clean_summary_text(text: str) -> str:
    cleaned = text.replace("**", "").replace("* ", "").replace("\\n", "\n").strip()
    lines = [line.strip(" -*\t") for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""
    condensed = " ".join(lines)
    condensed = condensed.replace("  ", " ")
    return condensed


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


def _find_first_dict(payload: Any, keys: set[str]) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in keys and isinstance(value, dict):
                return value
        for value in payload.values():
            found = _find_first_dict(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_dict(item, keys)
            if found:
                return found
    return None
