from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from difftotweet.config import load_config


_TEST_TEMP_ROOT = Path("tests") / ".tmp"


def test_load_config_requires_selected_provider_api_key():
    case_dir = _TEST_TEMP_ROOT / f"config-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=False)

    try:
        config_path = case_dir / "diff2tweet.yaml"
        config_path.write_text(
            """
provider: openai
model: gpt-4.1-mini
custom_instructions: Keep it specific.
forced_hashtags:
  - "#buildinpublic"
character_limit: 280
context_max_chars: 12000
output_folder: .diff2tweet
""".strip(),
            encoding="utf-8",
        )

        env_path = case_dir / ".env"
        env_path.write_text("", encoding="utf-8")

        with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
            load_config(config_path, env_file=env_path)
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_load_config_reads_structured_project_fields_and_new_readme_default():
    case_dir = _TEST_TEMP_ROOT / f"config-project-fields-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=False)

    try:
        config_path = case_dir / "diff2tweet.yaml"
        config_path.write_text(
            """
provider: openai
model: gpt-4.1-mini
project_name: diff2tweet
project_summary: Turn git diffs into tweet drafts.
project_audience: Developers building in public.
project_stage: beta
project_tone: founder
project_key_terms:
  - CLI
  - git workflow
num_candidates: 2
commit_subject_min_chars: 12
output_folder: .diff2tweet
""".strip(),
            encoding="utf-8",
        )

        env_path = case_dir / ".env"
        env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

        config = load_config(config_path, env_file=env_path)

        assert config.project_name == "diff2tweet"
        assert config.project_summary == "Turn git diffs into tweet drafts."
        assert config.project_audience == "Developers building in public."
        assert config.project_stage == "beta"
        assert config.project_tone == "founder"
        assert config.project_key_terms == ["CLI", "git workflow"]
        assert config.num_candidates == 2
        assert config.commit_subject_min_chars == 12
        assert config.readme_max_chars == 0
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_load_config_uses_default_commit_subject_min_chars():
    case_dir = _TEST_TEMP_ROOT / f"config-commit-threshold-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=False)

    try:
        config_path = case_dir / "diff2tweet.yaml"
        config_path.write_text(
            """
provider: openai
model: gpt-4.1-mini
output_folder: .diff2tweet
""".strip(),
            encoding="utf-8",
        )

        env_path = case_dir / ".env"
        env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

        config = load_config(config_path, env_file=env_path)

        assert config.commit_subject_min_chars == 20
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
