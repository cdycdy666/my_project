from __future__ import annotations

from pathlib import Path


CONTEXT_FILES = (
    "90-context/CURRENT_CONTEXT.md",
    "90-context/PROFILE.md",
    "90-context/CAPTURE_RULES.md",
)


def _read_optional(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[:max_chars]


def _recent_daily_notes(vault_dir: Path, limit: int = 5, max_total_chars: int = 12000) -> str:
    daily_dir = vault_dir / "10-daily"
    if not daily_dir.exists():
        return ""

    chunks: list[str] = []
    total_chars = 0
    for path in sorted(daily_dir.glob("*/*.md"), reverse=True)[:limit]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        chunk = f"--- {path.name} ---\n{text[:3000]}"
        if total_chars + len(chunk) > max_total_chars:
            break
        chunks.append(chunk)
        total_chars += len(chunk)
    return "\n\n".join(chunks)


def read_personal_context(vault_dir: Path, daily_limit: int = 5) -> str:
    chunks: list[str] = []

    for relative_path in CONTEXT_FILES:
        text = _read_optional(vault_dir / relative_path)
        if text:
            chunks.append(f"## {relative_path}\n{text}")

    recent_daily = _recent_daily_notes(vault_dir, limit=daily_limit)
    if recent_daily:
        chunks.append(f"## 最近 daily note\n{recent_daily}")

    return "\n\n".join(chunks).strip()
