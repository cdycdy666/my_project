from __future__ import annotations

import logging
import subprocess
from pathlib import Path


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _git(vault_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(vault_dir), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _run_git(vault_dir: Path, args: list[str]) -> str:
    result = _git(vault_dir, args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def pull_vault(vault_dir: Path) -> None:
    if not _is_git_repo(vault_dir):
        logging.info("skip git pull: %s is not a git repository", vault_dir)
        return

    _run_git(vault_dir, ["pull", "--rebase", "--autostash", "origin", "main"])
    logging.info("git pull completed for %s", vault_dir)


def commit_and_push_vault(vault_dir: Path, message: str) -> bool:
    if not _is_git_repo(vault_dir):
        logging.info("skip git push: %s is not a git repository", vault_dir)
        return False

    _run_git(vault_dir, ["add", "."])
    status = _run_git(vault_dir, ["status", "--porcelain"])
    if not status:
        logging.info("skip git commit: no vault changes")
        return False

    _run_git(vault_dir, ["commit", "-m", message])
    _run_git(vault_dir, ["push", "origin", "main"])
    logging.info("git commit and push completed for %s", vault_dir)
    return True
