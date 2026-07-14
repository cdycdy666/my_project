from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path


def build_memory_index_for_date(vault_dir: Path, date_text: str) -> Path | None:
    script_path = vault_dir / "scripts" / "build_memory_index.py"
    if not script_path.exists():
        logging.warning("memory index builder not found: %s", script_path)
        return None

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--vault-dir",
            str(vault_dir),
            "--date",
            date_text,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"memory index build failed: {detail}")

    output_path = vault_dir / "90-context" / "memory-index" / f"{date_text}.json"
    if not output_path.exists():
        raise RuntimeError(f"memory index builder did not create {output_path}")
    logging.info("memory index updated: %s", output_path)
    return output_path
