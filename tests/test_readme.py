from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from difftotweet.config import RuntimeConfig
from difftotweet.readme import discover_readme


_TEST_TEMP_ROOT = Path("tests") / ".tmp"


def test_discover_readme_returns_truncated_contents_when_present():
    case_dir = _TEST_TEMP_ROOT / f"readme-present-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        (repo_dir / "README.md").write_text("abcdefghij", encoding="utf-8")

        readme_text = discover_readme(_runtime_config(readme_max_chars=4), cwd=nested_dir)

        assert readme_text == "abcd"
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_readme_returns_none_when_readme_is_absent():
    case_dir = _TEST_TEMP_ROOT / f"readme-absent-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)

        assert discover_readme(_runtime_config(readme_max_chars=4), cwd=nested_dir) is None
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_discover_readme_returns_none_when_config_disables_it():
    case_dir = _TEST_TEMP_ROOT / f"readme-disabled-{uuid.uuid4().hex}"
    repo_dir = case_dir / "repo"
    nested_dir = repo_dir / "src" / "pkg"
    nested_dir.mkdir(parents=True, exist_ok=False)

    try:
        _init_git_repo(repo_dir)
        (repo_dir / "README.md").write_text("abcdefghij", encoding="utf-8")

        assert discover_readme(_runtime_config(readme_max_chars=0), cwd=nested_dir) is None
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def _runtime_config(*, readme_max_chars: int = 0) -> RuntimeConfig:
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
        lookback_commits=5,
        commit_subject_min_chars=20,
        readme_max_chars=readme_max_chars,
        context_max_chars=12000,
        max_doc_diff_sections=3,
        max_doc_section_chars=1000,
        diff_ignore_patterns=["*.lock", "dist/**"],
        output_folder=Path(".diff2tweet"),
        provider_api_key="test-key",
        openai_api_key="test-key",
    )


def _init_git_repo(repo_dir: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo_dir), "init"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
