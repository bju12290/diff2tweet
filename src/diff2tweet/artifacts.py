from __future__ import annotations

from pathlib import Path

from .logs import LogWriteError


def write_markdown(
    output_folder: Path,
    generation_timestamp: str,
    commit_range: str,
    tweets: list[str],
    approvals: dict[int, bool] | None,
    approval_timestamp: str | None,
) -> Path:
    """Write a markdown summary for a tweet-generation run."""

    runs_folder = output_folder / "runs"
    artifact_path = runs_folder / f"{_sanitize_filename_timestamp(generation_timestamp)}.md"
    lines = [
        "# diff2tweet run",
        "",
        f"- Generation timestamp: {generation_timestamp}",
    ]
    if approval_timestamp is not None:
        lines.append(f"- Approval timestamp: {approval_timestamp}")
    lines.extend(
        [
            f"- Commit range: {commit_range}",
            "",
            "## Candidates",
            "",
        ]
    )

    for index, tweet in enumerate(tweets, start=1):
        if approvals is not None:
            status = "approved" if approvals.get(index, False) else "denied"
            header = f"### Tweet {index} ({status})"
        else:
            header = f"### Tweet {index}"
        lines.extend(
            [
                header,
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
