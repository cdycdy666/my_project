from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .analyzer import run_analysis
from .config import ALLOWED_VIDEO_SUFFIXES, BASE_DIR, UPLOAD_DIR
from .db import init_db
from .models import PracticeCreated, PracticeRecord, PracticeSummary
from .repository import create_practice, get_practice, list_practices


app = FastAPI(title="Verbal Expression Coach", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/practices", response_model=list[PracticeSummary])
def api_list_practices() -> list[PracticeSummary]:
    return list_practices()


@app.get("/api/practices/{practice_id}", response_model=PracticeRecord)
def api_get_practice(practice_id: str) -> PracticeRecord:
    practice = get_practice(practice_id)
    if practice is None:
        raise HTTPException(status_code=404, detail="Practice not found")
    return practice


@app.post("/api/practices", response_model=PracticeCreated, status_code=201)
async def api_create_practice(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    focus_note: str = Form(""),
    reference_video: UploadFile = File(...),
    attempt_video: UploadFile = File(...),
) -> PracticeCreated:
    validate_video(reference_video, "reference_video")
    validate_video(attempt_video, "attempt_video")

    practice_id = str(uuid4())
    reference_name = f"{practice_id}_reference{Path(reference_video.filename).suffix.lower()}"
    attempt_name = f"{practice_id}_attempt{Path(attempt_video.filename).suffix.lower()}"
    reference_path = UPLOAD_DIR / reference_name
    attempt_path = UPLOAD_DIR / attempt_name

    await save_upload(reference_video, reference_path)
    await save_upload(attempt_video, attempt_path)

    create_practice(
        practice_id=practice_id,
        title=title.strip(),
        focus_note=focus_note.strip() or None,
        reference_filename=reference_name,
        reference_path=reference_path,
        attempt_filename=attempt_name,
        attempt_path=attempt_path,
    )

    background_tasks.add_task(run_analysis, practice_id)
    created_at = datetime.now(timezone.utc)
    return PracticeCreated(
        id=practice_id,
        status="queued",
        title=title.strip(),
        created_at=created_at,
    )


def validate_video(upload: UploadFile, field_name: str) -> None:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_SUFFIXES))
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a video file with one of these suffixes: {allowed}",
        )


async def save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

