from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from feishu_podcast_guide.config import load_config
from feishu_podcast_guide.daily_reco import run_daily_reco
from feishu_podcast_guide.service import FeishuPodcastGuideService


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(PROJECT_DIR)
    if not config.daily_reco_enabled:
        logging.info("daily reco disabled (set PODCAST_DAILY_RECO_ENABLED=true to enable)")
        return

    service = FeishuPodcastGuideService(config)
    today = date.today().isoformat()
    result = run_daily_reco(config, service.send_text, today, index=service.agent.index)
    logging.info("daily reco result: %s", result)


if __name__ == "__main__":
    main()
