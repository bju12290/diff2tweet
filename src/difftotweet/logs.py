from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from difftotweet.git import GitContext, get_head_sha


class LogWriteError(RuntimeError):
    """Raised when a successful generation run cannot be persisted."""


def write_run_entry(
    output_folder: Path,
    git_context: GitContext,
    tweets: list[str],
) -> Path:
    """Append a successful generation run entry to the JSONL run log."""

    run_log_path = output_folder / "run_log.jsonl"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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

    return run_log_path
