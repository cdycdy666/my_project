from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    app_id: str
    app_secret: str
    verification_token: str
    encrypt_key: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    weread_api_key: str
    personal_kb_dir: Path
    state_path: Path
    trace_log_enabled: bool
    trace_log_dir: Path


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


def _env_bool(env: dict[str, str], key: str, default: bool) -> bool:
    raw_value = env.get(key)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(base_dir: Path) -> Config:
    root_dir = base_dir.resolve().parent
    env = _read_env(root_dir / ".env")

    return Config(
        app_id=env.get("READING_FEISHU_APP_ID", ""),
        app_secret=env.get("READING_FEISHU_APP_SECRET", ""),
        verification_token=env.get("READING_FEISHU_VERIFICATION_TOKEN", ""),
        encrypt_key=env.get("READING_FEISHU_ENCRYPT_KEY", ""),
        llm_api_key=env.get("READING_LLM_API_KEY")
        or env.get("LLM_API_KEY")
        or env.get("DASHSCOPE_API_KEY")
        or env.get("OPENAI_API_KEY", ""),
        llm_base_url=env.get("READING_LLM_BASE_URL")
        or env.get("LLM_BASE_URL")
        or env.get("DASHSCOPE_BASE_URL")
        or "https://api.openai.com/v1",
        llm_model=env.get("READING_LLM_MODEL")
        or env.get("LLM_MODEL")
        or env.get("WISDOM_ADVISOR_MODEL")
        or env.get("OPENAI_MODEL", "qwen-plus"),
        weread_api_key=env.get("WEREAD_API_KEY", ""),
        personal_kb_dir=Path(
            env.get("READING_PERSONAL_KB_DIR")
            or env.get("PERSONAL_KB_DIR")
            or env.get("OBSIDIAN_VAULT_DIR")
            or root_dir / "personal-kb"
        ).expanduser(),
        state_path=base_dir / "state.json",
        trace_log_enabled=_env_bool(env, "READING_TRACE_LOG_ENABLED", True),
        trace_log_dir=Path(env.get("READING_TRACE_LOG_DIR") or base_dir / "logs" / "traces").expanduser(),
    )


def require_feishu_config(config: Config) -> None:
    missing = []
    if not config.app_id:
        missing.append("READING_FEISHU_APP_ID")
    if not config.app_secret:
        missing.append("READING_FEISHU_APP_SECRET")
    if missing:
        raise RuntimeError(f"Missing Feishu config: {', '.join(missing)}")
