from __future__ import annotations

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from feishu_podcast_guide.agent import PodcastGuideAgent
from feishu_podcast_guide.config import load_config


def main() -> None:
    message = " ".join(sys.argv[1:]).strip() or "帮助"
    agent = PodcastGuideAgent(load_config(PROJECT_DIR))
    print(agent.reply(message))


if __name__ == "__main__":
    main()
