from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from feishu_podcast_guide.config import load_config


def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, headers: dict) -> dict:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    config = load_config(PROJECT_DIR)
    if not config.app_id or not config.app_secret:
        raise SystemExit("missing PODCAST_FEISHU_APP_ID / PODCAST_FEISHU_APP_SECRET")

    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        token_data = _post_json(
            token_url,
            {
                "app_id": config.app_id,
                "app_secret": config.app_secret,
            },
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"tenant token request failed: HTTP {exc.code} {body[:300]}") from exc

    code = token_data.get("code")
    if code != 0:
        raise SystemExit(f"tenant token failed: code={code} msg={token_data.get('msg')}")

    token = token_data.get("tenant_access_token")
    print("tenant_access_token: ok")

    bot_url = "https://open.feishu.cn/open-apis/bot/v3/info"
    try:
        bot_data = _get_json(bot_url, {"Authorization": f"Bearer {token}"})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"bot info check skipped/failed: HTTP {exc.code} {body[:300]}")
        return

    print(f"bot_info_code: {bot_data.get('code')}")
    print(f"bot_info_msg: {bot_data.get('msg')}")
    bot = bot_data.get("bot") or bot_data.get("data") or {}
    if isinstance(bot, dict):
        name = bot.get("app_name") or bot.get("name") or bot.get("bot_name")
        open_id = bot.get("open_id") or bot.get("bot_open_id")
        if name:
            print(f"bot_name: {name}")
        if open_id:
            print(f"bot_open_id: {open_id}")


if __name__ == "__main__":
    main()
