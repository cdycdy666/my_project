from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import LocalWhisperSettings
from .models import MediaInsightResult, TranscriptSegment


class LocalWhisperTranscriptionService:
    def __init__(self, settings: LocalWhisperSettings) -> None:
        self._settings = settings
        self._whisper_model = None

    def run(self, audio_file: str | Path) -> MediaInsightResult:
        path = Path(audio_file)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Local transcription source file not found: {path}")

        model = self._ensure_model()
        segments_iter, info = model.transcribe(
            str(path),
            beam_size=self._settings.beam_size,
            language=self._settings.language,
            vad_filter=self._settings.vad_filter,
        )
        segments = [
            TranscriptSegment(
                text=(segment.text or "").strip(),
                start=float(segment.start) if segment.start is not None else None,
                end=float(segment.end) if segment.end is not None else None,
            )
            for segment in segments_iter
            if (segment.text or "").strip()
        ]
        transcript_text = "\n".join(segment.text for segment in segments)
        summary = transcript_text[:240].strip() if transcript_text else ""
        task_id = f"local-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        raw_payload = {
            "provider": "local_whisper",
            "audio_file": str(path),
            "model_name": self._settings.model_name,
            "language": getattr(info, "language", self._settings.language),
            "duration": getattr(info, "duration", None),
            "segments": [
                {
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end,
                }
                for segment in segments
            ],
        }
        self._persist_raw_result(task_id, raw_payload)
        return MediaInsightResult(
            task_id=task_id,
            status="completed",
            transcript_text=transcript_text,
            summary=summary,
            segments=segments,
            raw_payload=raw_payload,
        )

    def _ensure_model(self):
        if self._whisper_model is not None:
            return self._whisper_model

        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError:
            vendor_dir = Path(__file__).resolve().parents[2] / ".vendor"
            if vendor_dir.exists():
                sys.path.insert(0, str(vendor_dir))
            try:
                from faster_whisper import WhisperModel
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Missing local ASR dependency. Install `faster-whisper` or run `python3 -m pip install -e .`."
                ) from exc

        self._whisper_model = WhisperModel(
            self._settings.model_name,
            device=self._settings.device,
            compute_type=self._settings.compute_type,
        )
        return self._whisper_model

    def _persist_raw_result(self, task_id: str, payload: dict[str, object]) -> None:
        output_dir = self._settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{task_id}_local_whisper.json"
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
