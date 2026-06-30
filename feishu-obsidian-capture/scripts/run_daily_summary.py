from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_obsidian_capture.daily_job import run_daily_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Feishu history and summarize into Obsidian.")
    parser.add_argument("--date", help="Date to summarize, e.g. 2026-06-30")
    parser.add_argument("--no-notify", action="store_true", help="Do not send Feishu completion message")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    path = run_daily_summary(date_text=args.date, notify=not args.no_notify)
    print(path or "no records")


if __name__ == "__main__":
    main()
