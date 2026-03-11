from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from .artifacts import write_markdown
from .config import load_config
from .git import GitDiscoveryError, discover_git_context, find_repo_root
from .logs import LogWriteError, current_utc_timestamp, write_approval_entry, write_run_entry
from .notes import discover_notes
from .prompt import build_prompt
from .providers import ProviderError, get_provider

app = typer.Typer(
    add_completion=False,
    help="Generate tweet drafts from recent committed git changes.",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
def generate_tweets() -> None:
    """Auto-discover repo context, generate tweet candidates, and log the run."""

    try:
        repo_root = find_repo_root(Path.cwd())
        config = load_config(repo_root / "diff2tweet.yaml")
        git_context = discover_git_context(config, cwd=repo_root)
        notes_text = discover_notes(cwd=repo_root)
        prompt_text = build_prompt(config, git_context, notes_text)
        tweets = get_provider(config).generate_tweets(prompt_text, config)
        output_folder = repo_root / config.output_folder
        run_entry = write_run_entry(output_folder, git_context, tweets)
    except (GitDiscoveryError, LogWriteError, ProviderError, ValidationError, FileNotFoundError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(_format_candidates_output(git_context.commit_range, tweets))
    approvals = _prompt_for_approvals(len(tweets), config.auto_tweet)
    approval_timestamp = current_utc_timestamp()

    try:
        write_approval_entry(
            output_folder,
            run_entry.generation_timestamp,
            approvals,
            approval_timestamp,
        )
        write_markdown(
            output_folder,
            run_entry.generation_timestamp,
            git_context.commit_range,
            tweets,
            approvals,
            approval_timestamp,
        )
    except LogWriteError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _format_candidates_output(commit_range: str, tweets: list[str]) -> str:
    lines = [
        "diff2tweet candidates",
        f"commit_range: {commit_range}",
    ]
    for index, tweet in enumerate(tweets, start=1):
        lines.append(f"{index}. {tweet}")
    return "\n".join(lines)


def _prompt_for_approvals(tweet_count: int, auto_tweet: bool) -> dict[int, bool]:
    approvals: dict[int, bool] = {}
    for index in range(1, tweet_count + 1):
        if auto_tweet:
            approvals[index] = typer.confirm(f"Approve tweet {index}?", prompt_suffix=" [y/n]: ")
        else:
            # Temporarily auto-approve all tweets when not auto-tweeting.
            # Later we can use this for auto-tweet confirmation.
            approvals[index] = True
    return approvals
