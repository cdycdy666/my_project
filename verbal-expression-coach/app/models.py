from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


PracticeStatus = Literal["queued", "processing", "done", "failed"]


class ScoreSet(BaseModel):
    content_fidelity: int = Field(ge=0, le=100)
    structure_clarity: int = Field(ge=0, le=100)
    language_naturalness: int = Field(ge=0, le=100)
    conciseness: int = Field(ge=0, le=100)
    delivery_rhythm: int = Field(ge=0, le=100)
    visual_presence: int = Field(ge=0, le=100)


class SummaryBlock(BaseModel):
    overall_comment: str
    total_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    provisional: bool = False


class StrengthItem(BaseModel):
    title: str
    evidence: str


class IssueEvidence(BaseModel):
    reference: Optional[str] = None
    attempt: Optional[str] = None
    metric: Optional[str] = None
    observation: Optional[str] = None


class IssueItem(BaseModel):
    title: str
    severity: Literal["low", "medium", "high"]
    dimension: str
    evidence: IssueEvidence
    why_it_matters: str
    fix: str


class NextTask(BaseModel):
    focus: str
    instruction: str
    drill: str


class RewriteSuggestion(BaseModel):
    original_attempt: str
    suggested_version: str


class VideoMetadata(BaseModel):
    filename: str
    size_bytes: int
    size_mb: float
    suffix: str


class AnalysisResult(BaseModel):
    summary: SummaryBlock
    scores: ScoreSet
    strengths: list[StrengthItem]
    top_issues: list[IssueItem]
    next_task: NextTask
    rewrite_suggestions: list[RewriteSuggestion]
    coach_message: str
    reference_video: VideoMetadata
    attempt_video: VideoMetadata
    pipeline_notes: list[str]


class PracticeRecord(BaseModel):
    id: str
    title: str
    focus_note: Optional[str] = None
    status: PracticeStatus
    created_at: datetime
    updated_at: datetime
    reference_filename: str
    attempt_filename: str
    error_message: Optional[str] = None
    analysis: Optional[AnalysisResult] = None


class PracticeSummary(BaseModel):
    id: str
    title: str
    status: PracticeStatus
    created_at: datetime
    updated_at: datetime


class PracticeCreated(BaseModel):
    id: str
    status: PracticeStatus
    title: str
    created_at: datetime
