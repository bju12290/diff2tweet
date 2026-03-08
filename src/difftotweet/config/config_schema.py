from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LlmProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class DiffToTweetConfig(BaseModel):
    """Validated non-secret project configuration loaded from YAML."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: LlmProvider = LlmProvider.OPENAI
    model: str = Field(min_length=1)
    custom_instructions: str = Field(default="")
    forced_hashtags: list[str] = Field(default_factory=list)
    character_limit: int = Field(default=280, ge=1, le=10000)
    lookback_commits: int = Field(default=5, ge=1)
    output_folder: Path = Field(default=Path(".diff2tweet"))

    @field_validator("forced_hashtags")
    @classmethod
    def validate_forced_hashtags(cls, hashtags: list[str]) -> list[str]:
        normalized: list[str] = []
        for hashtag in hashtags:
            cleaned = hashtag.strip()
            if not cleaned:
                raise ValueError("forced_hashtags cannot contain empty values")
            if not cleaned.startswith("#"):
                raise ValueError("forced_hashtags entries must start with '#'")
            normalized.append(cleaned)
        return normalized

    @field_validator("output_folder")
    @classmethod
    def validate_output_folder(cls, output_folder: Path) -> Path:
        if output_folder.is_absolute():
            raise ValueError("output_folder must be a relative path")
        return output_folder
