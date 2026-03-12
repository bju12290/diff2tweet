from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from typer.testing import CliRunner

from diff2tweet.cli import app


_TEST_TEMP_ROOT = Path("tests") / ".tmp"
_runner = CliRunner()


class _FakeProvider:
    def generate_tweets(self, prompt_text: str, config) -> list[str]:
        return [
            "Shipped the first draft generator for diff2tweet.",
            "Now turning committed diffs into tweet candidates automatically.",
            "Built the first end-to-end LLM tweet flow for recent commits.",
        ]


def test_cli_prints_generated_candidates_and_writes_run_log(monkeypatch):
    case_dir = (_TEST_TEMP_ROOT / f"cli-generate-{uuid.uuid4().hex}").resolve()
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")
        _commit_file(repo_dir, "app.py", "print('two')\n", "Update app")

        (repo_dir / "README.md").write_text("Project headline\nMore details\n", encoding="utf-8")
        (repo_dir / "NOTES.md").write_text("Mention the CLI polish.\n", encoding="utf-8")
        (repo_dir / ".env").write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
        (repo_dir / "diff2tweet.yaml").write_text(
            """
provider: openai
model: gpt-4.1-mini
project_name: diff2tweet
project_summary: Turn committed diffs into tweet drafts.
project_audience: Developers building in public.
project_stage: beta
project_tone: founder
project_key_terms:
  - CLI
  - git workflow
custom_instructions: Keep it specific.
forced_hashtags:
  - "#buildinpublic"
character_limit: 280
lookback_commits: 1
readme_max_chars: 8
context_max_chars: 200
diff_ignore_patterns:
  - "*.lock"
output_folder: .diff2tweet
auto_tweet: true
""".strip(),
            encoding="utf-8",
        )

        approvals = iter([True, True, True])
        monkeypatch.setattr("diff2tweet.cli.get_provider", lambda config: _FakeProvider())
        monkeypatch.setattr("diff2tweet.cli.typer.confirm", lambda *args, **kwargs: next(approvals))
        monkeypatch.chdir(nested_dir)
        result = _runner.invoke(app, [])

        assert result.exit_code == 0
        assert "diff2tweet candidates" in result.stdout
        assert "1. Shipped the first draft generator for diff2tweet." in result.stdout
        assert "2. Now turning committed diffs into tweet candidates automatically." in result.stdout

        run_log_path = repo_dir / ".diff2tweet" / "run_log.jsonl"
        lines = run_log_path.read_text(encoding="utf-8").splitlines()
        generation_payload = json.loads(lines[-2])
        approval_payload = json.loads(lines[-1])
        assert generation_payload["commit_range"].endswith("..HEAD")
        assert generation_payload["tweets"][0] == "Shipped the first draft generator for diff2tweet."
        assert generation_payload["last_processed_sha"]
        assert approval_payload["type"] == "approval"
        assert approval_payload["approvals"] == {"1": True, "2": True, "3": True}

        artifact_path = repo_dir / ".diff2tweet" / "runs" / f"{generation_payload['timestamp'].replace(':', '-')}.md"
        artifact_contents = artifact_path.read_text(encoding="utf-8")
        assert "### Tweet 1 (approved)" in artifact_contents
        assert "### Tweet 3 (approved)" in artifact_contents
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_cli_writes_mixed_approval_artifact(monkeypatch):
    case_dir = (_TEST_TEMP_ROOT / f"cli-mixed-approval-{uuid.uuid4().hex}").resolve()
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")
        _commit_file(repo_dir, "app.py", "print('two')\n", "Update app")
        (repo_dir / ".env").write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
        (repo_dir / "diff2tweet.yaml").write_text(
            """
provider: openai
model: gpt-4.1-mini
lookback_commits: 1
output_folder: .diff2tweet
auto_tweet: true
""".strip(),
            encoding="utf-8",
        )

        approvals = iter([True, False, True])
        monkeypatch.setattr("diff2tweet.cli.get_provider", lambda config: _FakeProvider())
        monkeypatch.setattr("diff2tweet.cli.typer.confirm", lambda *args, **kwargs: next(approvals))
        monkeypatch.chdir(repo_dir)
        result = _runner.invoke(app, [])

        assert result.exit_code == 0
        log_lines = (repo_dir / ".diff2tweet" / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
        generation_payload = json.loads(log_lines[-2])
        approval_payload = json.loads(log_lines[-1])
        assert approval_payload["approvals"] == {"1": True, "2": False, "3": True}

        artifact_contents = (
            repo_dir / ".diff2tweet" / "runs" / f"{generation_payload['timestamp'].replace(':', '-')}.md"
        ).read_text(encoding="utf-8")
        assert "### Tweet 1 (approved)" in artifact_contents
        assert "### Tweet 2 (denied)" in artifact_contents
        assert "### Tweet 3 (approved)" in artifact_contents
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_cli_writes_denied_artifact(monkeypatch):
    case_dir = (_TEST_TEMP_ROOT / f"cli-deny-approval-{uuid.uuid4().hex}").resolve()
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")
        _commit_file(repo_dir, "app.py", "print('two')\n", "Update app")
        (repo_dir / ".env").write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
        (repo_dir / "diff2tweet.yaml").write_text(
            """
provider: openai
model: gpt-4.1-mini
lookback_commits: 1
output_folder: .diff2tweet
auto_tweet: true
""".strip(),
            encoding="utf-8",
        )

        approvals = iter([False, False, False])
        monkeypatch.setattr("diff2tweet.cli.get_provider", lambda config: _FakeProvider())
        monkeypatch.setattr("diff2tweet.cli.typer.confirm", lambda *args, **kwargs: next(approvals))
        monkeypatch.chdir(repo_dir)
        result = _runner.invoke(app, [])

        assert result.exit_code == 0
        log_lines = (repo_dir / ".diff2tweet" / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
        generation_payload = json.loads(log_lines[-2])
        approval_payload = json.loads(log_lines[-1])
        assert approval_payload["approvals"] == {"1": False, "2": False, "3": False}

        artifact_contents = (
            repo_dir / ".diff2tweet" / "runs" / f"{generation_payload['timestamp'].replace(':', '-')}.md"
        ).read_text(encoding="utf-8")
        assert "### Tweet 1 (denied)" in artifact_contents
        assert "### Tweet 2 (denied)" in artifact_contents
        assert "### Tweet 3 (denied)" in artifact_contents
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_cli_prints_clean_error_when_config_is_missing(monkeypatch):
    case_dir = (_TEST_TEMP_ROOT / f"cli-missing-config-{uuid.uuid4().hex}").resolve()
    repo_dir = case_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        _commit_file(repo_dir, "app.py", "print('one')\n", "Add app")

        monkeypatch.chdir(repo_dir)
        result = _runner.invoke(app, [])

        assert result.exit_code == 1
        assert "Error: Config file not found:" in result.output
        assert "Traceback" not in result.output
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
