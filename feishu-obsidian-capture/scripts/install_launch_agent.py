from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path


JOBS = {
    "com.chendingyu.feishu-obsidian-morning-reminder": {
        "script": "run_morning_reminder.py",
        "time_key": "DAILY_MORNING_TIME",
        "default_time": "07:30",
    },
    "com.chendingyu.feishu-obsidian-daily-summary": {
        "script": "run_daily_summary.py",
        "time_key": "DAILY_SUMMARY_TIME",
        "default_time": "23:00",
    },
}


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


def _time_value(root_dir: Path, key: str, default: str) -> tuple[int, int]:
    value = _read_env(root_dir / ".env").get(key, default)
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text), int(minute_text)


def _install_job(base_dir: Path, root_dir: Path, label: str, script: str, time_key: str, default_time: str) -> None:
    python_path = base_dir / ".venv" / "bin" / "python"
    run_path = base_dir / "scripts" / script
    log_dir = base_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    hour, minute = _time_value(root_dir, time_key, default_time)

    if not python_path.exists():
        raise SystemExit(f"Missing virtualenv python: {python_path}")
    if not run_path.exists():
        raise SystemExit(f"Missing script: {run_path}")

    plist = {
        "Label": label,
        "ProgramArguments": [str(python_path), str(run_path)],
        "WorkingDirectory": str(base_dir),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(log_dir / f"{label}.out.log"),
        "StandardErrorPath": str(log_dir / f"{label}.err.log"),
    }

    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{label}.plist"
    plist_path.write_bytes(plistlib.dumps(plist, sort_keys=False))

    domain = f"gui/{os.getuid()}"
    service = f"{domain}/{label}"
    subprocess.run(["launchctl", "bootout", domain, str(plist_path)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], check=True)
    subprocess.run(["launchctl", "enable", service], check=True)

    print(f"installed: {plist_path} at {hour:02d}:{minute:02d}")


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    root_dir = base_dir.parent
    for label, job in JOBS.items():
        _install_job(base_dir, root_dir, label, job["script"], job["time_key"], job["default_time"])
    print(f"logs: {base_dir / 'logs'}")


if __name__ == "__main__":
    main()
