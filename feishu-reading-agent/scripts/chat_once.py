from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_reading_agent.config import load_config
from feishu_reading_agent.reading_agent import ReadingAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the local reading agent once.")
    parser.add_argument("message", nargs="*", help="Message to the reading agent. Defaults to 推荐阅读.")
    args = parser.parse_args()

    text = " ".join(args.message).strip() or "推荐阅读"
    config = load_config(Path(__file__).resolve().parents[1])
    agent = ReadingAgent(config)

    try:
        print(agent.reply(text))
    except Exception as exc:
        print(f"读书智能体回复失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
