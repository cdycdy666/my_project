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
    vault_dir: Path
    morning_time: str
    reminder_time: str
    summary_time: str
    state_path: Path


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Missing env file: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config(base_dir: Path) -> Config:
    root_dir = base_dir.resolve().parent
    env_path = root_dir / ".env"
    env = _read_env(env_path)
    missing = [
        key
        for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "OBSIDIAN_VAULT_DIR")
        if not env.get(key)
    ]
    if missing:
        raise ValueError(f"Missing required env keys in {env_path}: {', '.join(missing)}")

    return Config(
        app_id=env["FEISHU_APP_ID"],
        app_secret=env["FEISHU_APP_SECRET"],
        verification_token=env.get("FEISHU_VERIFICATION_TOKEN", ""),
        encrypt_key=env.get("FEISHU_ENCRYPT_KEY", ""),
        llm_api_key=env.get("LLM_API_KEY") or env.get("DASHSCOPE_API_KEY") or env.get("OPENAI_API_KEY", ""),
        llm_base_url=env.get("LLM_BASE_URL") or env.get("DASHSCOPE_BASE_URL") or "https://api.openai.com/v1",
        llm_model=env.get("LLM_MODEL") or env.get("WISDOM_ADVISOR_MODEL") or env.get("OPENAI_MODEL", "qwen-plus"),
        vault_dir=Path(env["OBSIDIAN_VAULT_DIR"]).expanduser(),
        morning_time=env.get("DAILY_MORNING_TIME", "07:30"),
        reminder_time=env.get("DAILY_REMINDER_TIME", "21:30"),
        summary_time=env.get("DAILY_SUMMARY_TIME", "23:00"),
        state_path=base_dir / "state.json",
    )
