from __future__ import annotations

import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import Config


def rss_item_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0
    return len(root.findall(".//item"))


def rss_age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return max(0.0, (time.time() - path.stat().st_mtime) / 3600)


def rss_is_stale(path: Path, max_age_hours: int) -> bool:
    age = rss_age_hours(path)
    return age is None or age >= max_age_hours


def refresh_rss(config: Config) -> int:
    request = urllib.request.Request(
        config.rss_url,
        headers={
            "User-Agent": "Mozilla/5.0 feishu-podcast-guide/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()

    root = ET.fromstring(content)
    item_count = len(root.findall(".//item"))
    if item_count == 0:
        raise RuntimeError("RSS downloaded but contains no item entries")

    config.rss_path.parent.mkdir(parents=True, exist_ok=True)
    config.rss_path.write_bytes(content)
    return item_count


def ensure_rss_fresh(config: Config) -> int | None:
    if not config.rss_auto_refresh:
        return None
    if not rss_is_stale(config.rss_path, config.rss_max_age_hours):
        return None
    return refresh_rss(config)
