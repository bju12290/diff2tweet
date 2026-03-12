from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from diff2tweet.git import GitContext
from diff2tweet.logs import write_run_entry


_TEST_TEMP_ROOT = Path("tests") / ".tmp"


def test_write_run_entry_appends_jsonl_entry_with_head_sha():
    case_dir = _TEST_TEMP_ROOT / f"logs-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        head_sha = _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")

        output_dir = repo_dir / ".diff2tweet"
        git_context = GitContext(
            repo_root=repo_dir,
            commit_range="abc..HEAD",
            commit_messages=["Add app"],
            diff_text="diff --git a/app.py b/app.py\n",
        )

        result = write_run_entry(output_dir, git_context, ["one", "two", "three"])
        payload = json.loads(result.run_log_path.read_text(encoding="utf-8").splitlines()[-1])

        assert payload["last_processed_sha"] == head_sha
        assert payload["commit_range"] == "abc..HEAD"
        assert payload["tweets"] == ["one", "two", "three"]
        assert payload["timestamp"] == result.generation_timestamp
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


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
