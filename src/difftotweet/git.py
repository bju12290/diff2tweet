from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from difftotweet.config import RuntimeConfig


_RUN_LOG_NAME = "run_log.jsonl"


class GitDiscoveryError(RuntimeError):
    """Raised when git context discovery cannot produce usable committed changes."""


@dataclass(frozen=True)
class GitContext:
    """Committed git data used to build the tweet generation prompt."""

    repo_root: Path
    commit_range: str
    commit_messages: list[str]
    diff_text: str


def discover_git_context(
    config: RuntimeConfig,
    *,
    cwd: Path | None = None,
) -> GitContext:
    """Discover committed git context for the current repo."""

    repo_root = find_repo_root(cwd)
    commit_range = _resolve_commit_range(repo_root, config)
    commit_messages = _read_commit_messages(repo_root, commit_range)
    if not commit_messages:
        raise GitDiscoveryError(
            "No committed changes were found for the detected range. Make a new commit before running diff2tweet."
        )

    diff_text = _run_git_command(repo_root, "diff", commit_range)
    return GitContext(
        repo_root=repo_root,
        commit_range=commit_range,
        commit_messages=commit_messages,
        diff_text=diff_text,
    )


def find_repo_root(cwd: Path | None = None) -> Path:
    """Walk upward from the starting directory to find the git repo root."""

    start = (cwd or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise GitDiscoveryError("diff2tweet must be run inside a git repository.")


def get_head_sha(repo_root: Path) -> str:
    """Return the current HEAD SHA for the repository."""

    return _run_git_command(repo_root, "rev-parse", "HEAD").strip()


def _resolve_commit_range(repo_root: Path, config: RuntimeConfig) -> str:
    last_processed_sha = _read_last_processed_sha(repo_root / config.output_folder / _RUN_LOG_NAME)
    if last_processed_sha:
        return f"{last_processed_sha}..HEAD"

    return _resolve_lookback_range(repo_root, config.lookback_commits)


def _read_last_processed_sha(run_log_path: Path) -> str | None:
    if not run_log_path.exists():
        return None

    try:
        lines = run_log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GitDiscoveryError(f"Unable to read run log: {run_log_path}") from exc

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        last_processed_sha = payload.get("last_processed_sha")
        if isinstance(last_processed_sha, str) and last_processed_sha.strip():
            return last_processed_sha.strip()

    return None


def _resolve_lookback_range(repo_root: Path, lookback_commits: int) -> str:
    try:
        base_sha = _run_git_command(repo_root, "rev-parse", f"HEAD~{lookback_commits}").strip()
    except GitDiscoveryError as exc:
        raise GitDiscoveryError(
            "No committed changes were found for the requested lookback range. "
            "The repository may be empty or have fewer commits than lookback_commits."
        ) from exc

    return f"{base_sha}..HEAD"


def _read_commit_messages(repo_root: Path, commit_range: str) -> list[str]:
    log_output = _run_git_command(repo_root, "log", "--format=%x00%B", commit_range)
    return [msg.strip() for msg in log_output.split("\x00") if msg.strip()]


def _run_git_command(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise GitDiscoveryError("git is required but was not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown git error"
        raise GitDiscoveryError(f"Git command failed ({' '.join(args)}): {stderr}") from exc

    return completed.stdout
