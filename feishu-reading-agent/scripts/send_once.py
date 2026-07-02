from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_reading_agent.config import load_config
from feishu_reading_agent.reading_agent import ReadingAgent
from feishu_reading_agent.service import FeishuReadingService
from feishu_reading_agent.state import get_last_chat_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one reading-agent reply and send it to bound Feishu chat.")
    parser.add_argument("message", nargs="*", help="Message to the reading agent. Defaults to 推荐阅读.")
    args = parser.parse_args()

    text = " ".join(args.message).strip() or "推荐阅读"
    base_dir = Path(__file__).resolve().parents[1]
    config = load_config(base_dir)
    chat_id = get_last_chat_id(config.state_path)
    if not chat_id:
        print("还没有绑定飞书会话。先启动服务并给新机器人发送：绑定", file=sys.stderr)
        raise SystemExit(1)

    try:
        reply = ReadingAgent(config).reply(text)
        FeishuReadingService(config).send_text_chunks(chat_id, reply)
        print(reply)
    except Exception as exc:
        print(f"发送失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
