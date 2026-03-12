from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from diff2tweet.config import RuntimeConfig
from diff2tweet.git import GitDiscoveryError, discover_git_context
from diff2tweet.notes import discover_notes


_TEST_TEMP_ROOT = Path("tests") / ".tmp"


def test_discover_git_context_uses_last_processed_sha_when_run_log_exists():
    case_dir = _TEST_TEMP_ROOT / f"git-log-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        first_commit = _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")
        _commit_file(repo_dir, "app.py", "print('two')\n", "Update app")

        output_dir = repo_dir / ".diff2tweet"
        output_dir.mkdir()
        (output_dir / "run_log.jsonl").write_text(
            json.dumps({"last_processed_sha": first_commit}) + "\n",
            encoding="utf-8",
        )

        context = discover_git_context(_runtime_config(), cwd=repo_dir)

        assert context.commit_range == f"{first_commit}..HEAD"
        assert context.commit_messages == ["Update app"]
        assert "-print('one')" in context.diff_text
        assert "+print('two')" in context.diff_text
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_git_context_falls_back_to_lookback_commits_on_first_run():
    case_dir = _TEST_TEMP_ROOT / f"git-lookback-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        _commit_file(repo_dir, "one.txt", "one\n", "Commit one")
        _commit_file(repo_dir, "two.txt", "two\n", "Commit two")
        _commit_file(repo_dir, "three.txt", "three\n", "Commit three")

        context = discover_git_context(_runtime_config(lookback_commits=2), cwd=repo_dir)

        assert context.commit_range.endswith("..HEAD")
        assert context.commit_messages == ["Commit three", "Commit two"]
        assert "two.txt" in context.diff_text
        assert "three.txt" in context.diff_text
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_git_context_raises_clear_error_when_range_is_empty():
    case_dir = _TEST_TEMP_ROOT / f"git-empty-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        head_sha = _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")

        output_dir = repo_dir / ".diff2tweet"
        output_dir.mkdir()
        (output_dir / "run_log.jsonl").write_text(
            json.dumps({"last_processed_sha": head_sha}) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(GitDiscoveryError, match="No committed changes were found"):
            discover_git_context(_runtime_config(), cwd=repo_dir)
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_notes_returns_contents_when_notes_file_exists():
    case_dir = _TEST_TEMP_ROOT / f"notes-present-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        (repo_dir / "NOTES.md").write_text("Launch copy for the CLI.\n", encoding="utf-8")

        assert discover_notes(cwd=nested_dir) == "Launch copy for the CLI.\n"
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_notes_returns_none_when_notes_file_is_absent():
    case_dir = _TEST_TEMP_ROOT / f"notes-absent-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)

        assert discover_notes(cwd=nested_dir) is None
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def _runtime_config(*, lookback_commits: int = 5) -> RuntimeConfig:
    return RuntimeConfig(
        provider="openai",
        model="gpt-4.1-mini",
        project_name="",
        project_summary="",
        project_audience="",
        project_stage="prototype",
        project_tone="technical",
        project_key_terms=[],
        custom_instructions="",
        forced_hashtags=[],
        character_limit=280,
        num_candidates=3,
        lookback_commits=lookback_commits,
        commit_subject_min_chars=20,
        readme_max_chars=0,
        context_max_chars=12000,
        max_doc_diff_sections=3,
        max_doc_section_chars=1000,
        diff_ignore_patterns=["*.lock", "dist/**"],
        output_folder=Path(".diff2tweet"),
        auto_tweet=False,
        provider_api_key="test-key",
        openai_api_key="test-key",
    )


def _init_git_repo(repo_dir: Path) -> None:
    _run_git(repo_dir, "init")
    _run_git(repo_dir, "config", "user.name", "Diff To Tweet Tests")
    _run_git(repo_dir, "config", "user.email", "tests@example.com")


def _commit_file(repo_dir: Path, relative_path: str, contents: str, message: str) -> str:
    file_path = repo_dir / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(contents, encoding="utf-8")
    _run_git(repo_dir, "add", relative_path)
    _run_git(repo_dir, "commit", "-m", message)
    return _run_git(repo_dir, "rev-parse", "HEAD").strip()


def _run_git(repo_dir: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout
