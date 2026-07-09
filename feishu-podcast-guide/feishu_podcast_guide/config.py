from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    bot_display_name: str
    app_id: str
    app_secret: str
    verification_token: str
    encrypt_key: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_enabled: bool
    agent_path: Path
    rl_path: Path
    rss_path: Path
    rss_url: str
    rss_auto_refresh: bool
    rss_max_age_hours: int
    state_path: Path
    daily_reco_enabled: bool
    daily_theme_rotate_count: int
    daily_push_time: str
    daily_recent_window: int
    paper_cache_path: Path
    paper_max_pages: int
    paper_max_chars: int


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _merged_env(project_dir: Path) -> dict[str, str]:
    root_dir = project_dir.resolve().parent
    values: dict[str, str] = {}
    values.update(_read_env(root_dir / ".env"))
    values.update(_read_env(project_dir / ".env"))
    values.update({key: value for key, value in os.environ.items() if isinstance(value, str)})
    return values


def _path(value: str | None, fallback: Path) -> Path:
    if not value:
        return fallback
    return Path(value).expanduser()


def _llm_enabled(env: dict[str, str], api_key: str) -> bool:
    raw = env.get("PODCAST_LLM_ENABLED", "auto").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return bool(api_key)


def _env_bool(env: dict[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(env: dict[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_config(project_dir: Path) -> Config:
    env = _merged_env(project_dir)
    root_dir = project_dir.resolve().parent

    llm_api_key = (
        env.get("PODCAST_LLM_API_KEY")
        or env.get("LLM_API_KEY")
        or env.get("DASHSCOPE_API_KEY")
        or env.get("OPENAI_API_KEY")
        or ""
    )

    return Config(
        bot_display_name=env.get("PODCAST_BOT_DISPLAY_NAME", "大模型陪练"),
        app_id=env.get("PODCAST_FEISHU_APP_ID", ""),
        app_secret=env.get("PODCAST_FEISHU_APP_SECRET", ""),
        verification_token=env.get("PODCAST_FEISHU_VERIFICATION_TOKEN", ""),
        encrypt_key=env.get("PODCAST_FEISHU_ENCRYPT_KEY", ""),
        llm_api_key=llm_api_key,
        llm_base_url=(
            env.get("PODCAST_LLM_BASE_URL")
            or env.get("LLM_BASE_URL")
            or env.get("DASHSCOPE_BASE_URL")
            or "https://api.openai.com/v1"
        ),
        llm_model=(
            env.get("PODCAST_LLM_MODEL")
            or env.get("LLM_MODEL")
            or env.get("OPENAI_MODEL")
            or "gpt-4.1-mini"
        ),
        llm_enabled=_llm_enabled(env, llm_api_key),
        agent_path=_path(
            env.get("PODCAST_AGENT_PATH"),
            root_dir / "output" / "podcast-index" / "aikeke-ai-life" / "agent_learning_path.md",
        ),
        rl_path=_path(
            env.get("PODCAST_RL_PATH"),
            root_dir / "output" / "podcast-index" / "aikeke-ai-life" / "rl_learning_path.md",
        ),
        rss_path=_path(env.get("PODCAST_RSS_PATH"), project_dir / "data" / "aikeke_feed_latest.xml"),
        rss_url=env.get("PODCAST_RSS_URL", "https://feed.xyzfm.space/wl9t7httkfd3"),
        rss_auto_refresh=_env_bool(env, "PODCAST_RSS_AUTO_REFRESH", True),
        rss_max_age_hours=max(1, _env_int(env, "PODCAST_RSS_MAX_AGE_HOURS", 12)),
        state_path=project_dir / "state.json",
        daily_reco_enabled=_env_bool(env, "PODCAST_DAILY_RECO_ENABLED", False),
        daily_theme_rotate_count=max(1, _env_int(env, "PODCAST_DAILY_THEME_ROTATE_COUNT", 7)),
        daily_push_time=env.get("PODCAST_DAILY_PUSH_TIME", "08:30"),
        daily_recent_window=max(1, _env_int(env, "PODCAST_DAILY_RECENT_WINDOW", 60)),
        paper_cache_path=_path(
            env.get("PODCAST_PAPER_CACHE_PATH"),
            project_dir / "data" / "papers",
        ),
        paper_max_pages=max(1, _env_int(env, "PODCAST_PAPER_MAX_PAGES", 8)),
        paper_max_chars=max(3000, _env_int(env, "PODCAST_PAPER_MAX_CHARS", 18000)),
    )


def require_feishu_config(config: Config) -> None:
    missing = []
    if not config.app_id:
        missing.append("PODCAST_FEISHU_APP_ID")
    if not config.app_secret:
        missing.append("PODCAST_FEISHU_APP_SECRET")
    if missing:
        raise RuntimeError(f"Missing Feishu config: {', '.join(missing)}")
