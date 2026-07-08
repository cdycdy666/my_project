from __future__ import annotations

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from feishu_podcast_guide.config import load_config
from feishu_podcast_guide.rss import refresh_rss


def main() -> None:
    config = load_config(PROJECT_DIR)
    item_count = refresh_rss(config)
    print(f"RSS refreshed: {item_count} episodes -> {config.rss_path}")


if __name__ == "__main__":
    main()
