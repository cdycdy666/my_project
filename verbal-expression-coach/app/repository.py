from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .db import get_connection
from .models import AnalysisResult, PracticeRecord, PracticeSummary


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_practice(
    practice_id: str,
    title: str,
    focus_note: Optional[str],
    reference_filename: str,
    reference_path: Path,
    attempt_filename: str,
    attempt_path: Path,
) -> None:
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO practices (
                id, title, focus_note, reference_filename, reference_path,
                attempt_filename, attempt_path, status, analysis_json,
                error_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                practice_id,
                title,
                focus_note,
                reference_filename,
                str(reference_path),
                attempt_filename,
                str(attempt_path),
                "queued",
                None,
                None,
                now,
                now,
            ),
        )


def update_practice_status(practice_id: str, status: str, error_message: Optional[str] = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE practices
            SET status = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, error_message, utc_now_iso(), practice_id),
        )


def save_analysis(practice_id: str, analysis: AnalysisResult) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE practices
            SET status = ?, analysis_json = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            ("done", analysis.model_dump_json(), None, utc_now_iso(), practice_id),
        )


def get_practice(practice_id: str) -> Optional[PracticeRecord]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM practices WHERE id = ?", (practice_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_practices() -> list[PracticeSummary]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, status, created_at, updated_at
            FROM practices
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [
        PracticeSummary(
            id=row["id"],
            title=row["title"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        for row in rows
    ]


def _row_to_record(row) -> PracticeRecord:
    analysis_json = row["analysis_json"]
    analysis = AnalysisResult.model_validate_json(analysis_json) if analysis_json else None
    return PracticeRecord(
        id=row["id"],
        title=row["title"],
        focus_note=row["focus_note"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        reference_filename=row["reference_filename"],
        attempt_filename=row["attempt_filename"],
        error_message=row["error_message"],
        analysis=analysis,
    )
