from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .models import NotionPropertyMapping


def _read_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _normalize_env_value(value.strip()))


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv(path: str = ".env") -> None:
    _read_env_file(Path(path))


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass
class QianfanSettings:
    mcp_url: str
    bearer_token: str
    protocol_version: str
    create_tool: str | None
    status_tool: str | None
    result_tool: str | None
    disable_proxy: bool
    poll_interval_seconds: int
    timeout_seconds: int
    output_dir: Path


@dataclass
class DoubaoMiaojiSettings:
    submit_url: str
    query_url: str
    api_key: str
    app_key: str
    access_key: str
    resource_id: str
    disable_proxy: bool
    poll_interval_seconds: int
    timeout_seconds: int
    output_dir: Path
    file_type: str
    source_lang: str
    all_activate: bool
    audio_transcription_enable: bool
    speaker_identification: bool
    number_of_speaker: int
    hot_words: str
    translation_enable: bool
    target_lang: str
    information_extraction_enable: bool
    information_extraction_types: list[str]
    summarization_enable: bool
    summarization_types: list[str]
    chapter_enable: bool


@dataclass
class LocalWhisperSettings:
    model_name: str
    device: str
    compute_type: str
    language: str | None
    beam_size: int
    vad_filter: bool
    output_dir: Path


@dataclass
class BosSettings:
    access_key_id: str
    secret_access_key: str
    bucket: str
    endpoint: str
    object_prefix: str
    signed_url_expiration_seconds: int
    multipart_threshold_bytes: int
    multipart_chunk_size_mb: int
    disable_proxy: bool


@dataclass
class NotionSettings:
    token: str
    database_id: str
    version: str
    property_mapping: NotionPropertyMapping
    status_done: str
    default_tags: list[str]


@dataclass
class AppSettings:
    transcription_provider: str
    qianfan: QianfanSettings
    doubao_miaoji: DoubaoMiaojiSettings
    local_whisper: LocalWhisperSettings
    bos: BosSettings | None
    notion: NotionSettings | None


def load_settings(*, env_file: str = ".env", require_notion: bool = True) -> AppSettings:
    load_dotenv(env_file)

    transcription_provider = os.getenv("TRANSCRIPTION_PROVIDER", "local_whisper").strip().lower()
    qianfan = QianfanSettings(
        mcp_url=os.getenv("QIANFAN_MCP_URL", "https://qianfan.baidubce.com/v2/tools/media-insight/mcp"),
        bearer_token=os.getenv("QIANFAN_BEARER_TOKEN", ""),
        protocol_version=os.getenv("QIANFAN_MCP_PROTOCOL_VERSION", "2025-06-18"),
        create_tool=os.getenv("QIANFAN_CREATE_TOOL") or None,
        status_tool=os.getenv("QIANFAN_STATUS_TOOL") or None,
        result_tool=os.getenv("QIANFAN_RESULT_TOOL") or None,
        disable_proxy=os.getenv("QIANFAN_DISABLE_PROXY", "true").lower() in {"1", "true", "yes", "on"},
        poll_interval_seconds=int(os.getenv("PIPELINE_POLL_INTERVAL_SECONDS", "15")),
        timeout_seconds=int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "900")),
        output_dir=Path(os.getenv("PIPELINE_OUTPUT_DIR", "./output")),
    )
    doubao_miaoji = DoubaoMiaojiSettings(
        submit_url=os.getenv(
            "DOUBAO_MIAOJI_SUBMIT_URL",
            "https://openspeech.bytedance.com/api/v3/auc/lark/submit",
        ),
        query_url=os.getenv(
            "DOUBAO_MIAOJI_QUERY_URL",
            "https://openspeech.bytedance.com/api/v3/auc/lark/query",
        ),
        api_key=os.getenv("DOUBAO_MIAOJI_API_KEY", ""),
        app_key=os.getenv("DOUBAO_MIAOJI_APP_KEY", ""),
        access_key=os.getenv("DOUBAO_MIAOJI_ACCESS_KEY", ""),
        resource_id=os.getenv("DOUBAO_MIAOJI_RESOURCE_ID", "volc.lark.minutes"),
        disable_proxy=os.getenv("DOUBAO_MIAOJI_DISABLE_PROXY", "true").lower() in {"1", "true", "yes", "on"},
        poll_interval_seconds=int(os.getenv("DOUBAO_MIAOJI_POLL_INTERVAL_SECONDS", os.getenv("PIPELINE_POLL_INTERVAL_SECONDS", "15"))),
        timeout_seconds=int(os.getenv("DOUBAO_MIAOJI_TIMEOUT_SECONDS", os.getenv("PIPELINE_TIMEOUT_SECONDS", "900"))),
        output_dir=Path(os.getenv("PIPELINE_OUTPUT_DIR", "./output")),
        file_type=os.getenv("DOUBAO_MIAOJI_FILE_TYPE", "audio"),
        source_lang=os.getenv("DOUBAO_MIAOJI_SOURCE_LANG", "zh_cn"),
        all_activate=os.getenv("DOUBAO_MIAOJI_ALL_ACTIVATE", "false").lower() in {"1", "true", "yes", "on"},
        audio_transcription_enable=os.getenv("DOUBAO_MIAOJI_AUDIO_TRANSCRIPTION_ENABLE", "true").lower() in {"1", "true", "yes", "on"},
        speaker_identification=os.getenv("DOUBAO_MIAOJI_SPEAKER_IDENTIFICATION", "true").lower() in {"1", "true", "yes", "on"},
        number_of_speaker=int(os.getenv("DOUBAO_MIAOJI_NUMBER_OF_SPEAKER", "0")),
        hot_words=os.getenv("DOUBAO_MIAOJI_HOT_WORDS", ""),
        translation_enable=os.getenv("DOUBAO_MIAOJI_TRANSLATION_ENABLE", "false").lower() in {"1", "true", "yes", "on"},
        target_lang=os.getenv("DOUBAO_MIAOJI_TARGET_LANG", "zh_cn"),
        information_extraction_enable=os.getenv("DOUBAO_MIAOJI_INFORMATION_EXTRACTION_ENABLE", "true").lower() in {"1", "true", "yes", "on"},
        information_extraction_types=[
            item.strip()
            for item in os.getenv("DOUBAO_MIAOJI_INFORMATION_EXTRACTION_TYPES", "question_answer").split(",")
            if item.strip()
        ],
        summarization_enable=os.getenv("DOUBAO_MIAOJI_SUMMARIZATION_ENABLE", "true").lower() in {"1", "true", "yes", "on"},
        summarization_types=[
            item.strip()
            for item in os.getenv("DOUBAO_MIAOJI_SUMMARIZATION_TYPES", "summary").split(",")
            if item.strip()
        ],
        chapter_enable=os.getenv("DOUBAO_MIAOJI_CHAPTER_ENABLE", "true").lower() in {"1", "true", "yes", "on"},
    )
    local_whisper = LocalWhisperSettings(
        model_name=os.getenv("LOCAL_WHISPER_MODEL", "small"),
        device=os.getenv("LOCAL_WHISPER_DEVICE", "auto"),
        compute_type=os.getenv("LOCAL_WHISPER_COMPUTE_TYPE", "auto"),
        language=os.getenv("LOCAL_WHISPER_LANGUAGE") or "zh",
        beam_size=int(os.getenv("LOCAL_WHISPER_BEAM_SIZE", "5")),
        vad_filter=os.getenv("LOCAL_WHISPER_VAD_FILTER", "true").lower() in {"1", "true", "yes", "on"},
        output_dir=Path(os.getenv("PIPELINE_OUTPUT_DIR", "./output")),
    )

    if transcription_provider == "qianfan" and not qianfan.bearer_token:
        raise ValueError("QIANFAN_BEARER_TOKEN is required when TRANSCRIPTION_PROVIDER=qianfan")
    if transcription_provider == "doubao_miaoji" and not (
        doubao_miaoji.api_key or (doubao_miaoji.app_key and doubao_miaoji.access_key)
    ):
        raise ValueError(
            "DOUBAO_MIAOJI_API_KEY or DOUBAO_MIAOJI_APP_KEY + DOUBAO_MIAOJI_ACCESS_KEY are required when "
            "TRANSCRIPTION_PROVIDER=doubao_miaoji"
        )

    bos = None
    if os.getenv("BOS_ACCESS_KEY_ID") and os.getenv("BOS_SECRET_ACCESS_KEY"):
        bos = BosSettings(
            access_key_id=_required("BOS_ACCESS_KEY_ID"),
            secret_access_key=_required("BOS_SECRET_ACCESS_KEY"),
            bucket=_required("BOS_BUCKET"),
            endpoint=_required("BOS_ENDPOINT"),
            object_prefix=os.getenv("BOS_OBJECT_PREFIX", "interview-audio"),
            signed_url_expiration_seconds=int(os.getenv("BOS_SIGNED_URL_EXPIRES", "86400")),
            multipart_threshold_bytes=int(os.getenv("BOS_MULTIPART_THRESHOLD_MB", "8")) * 1024 * 1024,
            multipart_chunk_size_mb=int(os.getenv("BOS_MULTIPART_CHUNK_MB", "5")),
            disable_proxy=os.getenv("BOS_DISABLE_PROXY", "true").lower() in {"1", "true", "yes", "on"},
        )

    notion = None
    if require_notion:
        notion = NotionSettings(
            token=_required("NOTION_TOKEN"),
            database_id=_required("NOTION_DATABASE_ID"),
            version=os.getenv("NOTION_VERSION", "2022-06-28"),
            property_mapping=NotionPropertyMapping(
                candidate=_required("NOTION_PROP_CANDIDATE"),
                role=_required("NOTION_PROP_ROLE"),
                interview_date=_required("NOTION_PROP_DATE"),
                round=_required("NOTION_PROP_ROUND"),
                status=_required("NOTION_PROP_STATUS"),
                audio_url=_required("NOTION_PROP_AUDIO_URL"),
                transcript_url=_required("NOTION_PROP_TRANSCRIPT_URL"),
                decision=_required("NOTION_PROP_DECISION"),
                tags=_required("NOTION_PROP_TAGS"),
                summary=_required("NOTION_PROP_SUMMARY"),
            ),
            status_done=os.getenv("DEFAULT_STATUS_DONE", "完成"),
            default_tags=[
                item.strip()
                for item in os.getenv("DEFAULT_TAGS", "").split(",")
                if item.strip()
            ],
        )
    return AppSettings(
        transcription_provider=transcription_provider,
        qianfan=qianfan,
        doubao_miaoji=doubao_miaoji,
        local_whisper=local_whisper,
        bos=bos,
        notion=notion,
    )
