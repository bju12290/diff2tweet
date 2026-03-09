from __future__ import annotations

from pathlib import Path

from .logs import LogWriteError


def write_markdown(
    output_folder: Path,
    generation_timestamp: str,
    commit_range: str,
    tweets: list[str],
    approvals: dict[int, bool],
    approval_timestamp: str,
) -> Path:
    """Write a markdown summary for a reviewed tweet-generation run."""

    runs_folder = output_folder / "runs"
    artifact_path = runs_folder / f"{_sanitize_filename_timestamp(generation_timestamp)}.md"
    lines = [
        "# diff2tweet run",
        "",
        f"- Generation timestamp: {generation_timestamp}",
        f"- Approval timestamp: {approval_timestamp}",
        f"- Commit range: {commit_range}",
        "",
        "## Candidates",
        "",
    ]

    for index, tweet in enumerate(tweets, start=1):
        status = "approved" if approvals.get(index, False) else "denied"
        lines.extend(
            [
                f"### Tweet {index} ({status})",
                "",
                tweet,
                "",
            ]
        )

    try:
        runs_folder.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError as exc:
        raise LogWriteError(f"Unable to write markdown artifact: {artifact_path}") from exc

    return artifact_path


def _sanitize_filename_timestamp(timestamp: str) -> str:
    return timestamp.replace(":", "-")
