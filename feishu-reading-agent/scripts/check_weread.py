from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_reading_agent.config import load_config
from feishu_reading_agent.weread import call_weread_gateway, fetch_shelf_context


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    config = load_config(base_dir)
    if not config.weread_api_key:
        print("缺少 WEREAD_API_KEY，请写入 /Users/chendingyu/my_project/.env", file=sys.stderr)
        raise SystemExit(1)

    api_list = call_weread_gateway(config.weread_api_key, "/_list")
    api_count = len(api_list.get("apis", [])) if isinstance(api_list.get("apis"), list) else 0
    print(f"微信读书 gateway 连接成功，可用接口数：{api_count}")
    print()
    print(fetch_shelf_context(config.weread_api_key))


if __name__ == "__main__":
    main()
