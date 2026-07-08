from __future__ import annotations

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from feishu_podcast_guide.config import load_config
from feishu_podcast_guide.podcast_index import PodcastIndex
from feishu_podcast_guide.rss import rss_age_hours


def _yes(value: object) -> str:
    return "ok" if bool(value) else "missing"


def main() -> None:
    config = load_config(PROJECT_DIR)
    index = PodcastIndex.load(config.agent_path, config.rl_path, config.rss_path)

    print(f"bot_display_name: {config.bot_display_name}")
    print(f"PODCAST_FEISHU_APP_ID: {_yes(config.app_id)}")
    print(f"PODCAST_FEISHU_APP_SECRET: {_yes(config.app_secret)}")
    print(f"PODCAST_FEISHU_VERIFICATION_TOKEN: {_yes(config.verification_token)}")
    print(f"PODCAST_FEISHU_ENCRYPT_KEY: {_yes(config.encrypt_key)}")
    print(f"PODCAST_LLM_ENABLED: {config.llm_enabled}")
    print(f"PODCAST_LLM_API_KEY: {_yes(config.llm_api_key)}")
    print(f"PODCAST_RSS_PATH: {config.rss_path}")
    print(f"PODCAST_RSS_EXISTS: {_yes(config.rss_path.exists())}")
    age = rss_age_hours(config.rss_path)
    print(f"PODCAST_RSS_AUTO_REFRESH: {config.rss_auto_refresh}")
    print(f"PODCAST_RSS_MAX_AGE_HOURS: {config.rss_max_age_hours}")
    print(f"PODCAST_RSS_AGE_HOURS: {age:.2f}" if age is not None else "PODCAST_RSS_AGE_HOURS: missing")
    print(index.stats())

    if not config.app_id or not config.app_secret:
        raise SystemExit("missing required Feishu config: PODCAST_FEISHU_APP_ID / PODCAST_FEISHU_APP_SECRET")


if __name__ == "__main__":
    main()
