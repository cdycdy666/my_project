import sqlite3

from .config import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practices (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                focus_note TEXT,
                reference_filename TEXT NOT NULL,
                reference_path TEXT NOT NULL,
                attempt_filename TEXT NOT NULL,
                attempt_path TEXT NOT NULL,
                status TEXT NOT NULL,
                analysis_json TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
