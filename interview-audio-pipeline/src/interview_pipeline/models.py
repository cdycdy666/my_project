from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class InterviewInput:
    audio_url: str | None
    candidate: str
    role: str
    round: str
    interview_date: date
    audio_file: str | None = None

    def record_title(self) -> str:
        candidate = self.candidate.strip()
        if candidate:
            return candidate
        if self.audio_file:
            stem = Path(self.audio_file).stem.strip()
            if stem:
                return stem
        round_text = self.round.strip() or "面试"
        return f"{self.interview_date.isoformat()}_{round_text}"

    def safe_label(self) -> str:
        raw = self.record_title()
        return "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_") or "interview"


@dataclass
class TranscriptSegment:
    text: str
    start: float | None = None
    end: float | None = None
    speaker: str | None = None


@dataclass
class QuestionAnswerPair:
    question: str
    answer: str


@dataclass
class MediaInsightResult:
    task_id: str
    status: str
    transcript_text: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    chapters: list[str] = field(default_factory=list)
    qa_pairs: list[QuestionAnswerPair] = field(default_factory=list)
    segments: list[TranscriptSegment] = field(default_factory=list)
    transcript_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredAssessment:
    summary: str
    strengths: list[str]
    risks: list[str]
    follow_ups: list[str]
    recommendation: str
    transcript_text: str


@dataclass
class NotionPropertyMapping:
    candidate: str
    role: str
    interview_date: str
    round: str
    status: str
    audio_url: str
    transcript_url: str
    decision: str
    tags: str
    summary: str
