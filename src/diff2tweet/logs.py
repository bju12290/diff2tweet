from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from diff2tweet.git import GitContext, get_head_sha


class LogWriteError(RuntimeError):
    """Raised when a successful generation run cannot be persisted."""


@dataclass(frozen=True)
class RunLogWriteResult:
    """Metadata for a persisted generation run."""

    generation_timestamp: str
    run_log_path: Path


def write_run_entry(
    output_folder: Path,
    git_context: GitContext,
    tweets: list[str],
) -> RunLogWriteResult:
    """Append a successful generation run entry to the JSONL run log."""

    run_log_path = output_folder / "run_log.jsonl"
    generation_timestamp = _utc_now_isoformat()
    payload = {
        "timestamp": generation_timestamp,
        "last_processed_sha": get_head_sha(git_context.repo_root),
        "commit_range": git_context.commit_range,
        "tweets": tweets,
    }

    try:
        output_folder.mkdir(parents=True, exist_ok=True)
        with run_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload) + "\n")
    except OSError as exc:
        raise LogWriteError(f"Unable to write run log: {run_log_path}") from exc

    return RunLogWriteResult(
        generation_timestamp=generation_timestamp,
        run_log_path=run_log_path,
    )


def write_approval_entry(
    output_folder: Path,
    generation_timestamp: str,
    approvals: dict[int, bool],
    approval_timestamp: str,
) -> Path:
    """Append approval decisions for a previously logged generation run."""

    run_log_path = output_folder / "run_log.jsonl"
    payload = {
        "type": "approval",
        "generation_timestamp": generation_timestamp,
        "approvals": {str(index): approved for index, approved in approvals.items()},
        "approval_timestamp": approval_timestamp,
    }

    try:
        output_folder.mkdir(parents=True, exist_ok=True)
        with run_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload) + "\n")
    except OSError as exc:
        raise LogWriteError(f"Unable to write run log: {run_log_path}") from exc

    return run_log_path


def current_utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return _utc_now_isoformat()


def _utc_now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()
