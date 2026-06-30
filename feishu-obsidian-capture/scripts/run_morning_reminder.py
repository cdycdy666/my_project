from __future__ import annotations

import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_obsidian_capture.morning_job import run_morning_reminder


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    message = run_morning_reminder()
    print(message)


if __name__ == "__main__":
    main()
