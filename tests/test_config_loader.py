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
