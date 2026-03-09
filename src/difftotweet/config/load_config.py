from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, SecretStr, model_validator

from .config_schema import DiffToTweetConfig, LlmProvider
from .settings import ProviderSettings


_PROVIDER_KEY_FIELDS: dict[LlmProvider, str] = {
    LlmProvider.OPENAI: "openai_api_key",
    LlmProvider.ANTHROPIC: "anthropic_api_key",
    LlmProvider.GEMINI: "gemini_api_key",
}


class RuntimeConfig(BaseModel):
    """Merged runtime config assembled from YAML and environment settings."""

    model_config = ConfigDict(extra="forbid")

    provider: LlmProvider
    model: str
    custom_instructions: str
    forced_hashtags: list[str]
    character_limit: int
    num_candidates: int
    lookback_commits: int
    readme_max_chars: int
    context_max_chars: int
    diff_ignore_patterns: list[str]
    output_folder: Path
    provider_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_selected_provider_has_key(self) -> "RuntimeConfig":
        key_field = _PROVIDER_KEY_FIELDS[self.provider]
        if getattr(self, key_field) is None:
            raise ValueError(
                f"Provider '{self.provider}' requires the {key_field.upper()} environment variable"
            )
        return self


def load_config(
    config_path: str | Path = "diff2tweet.yaml",
    *,
    env_file: str | Path | None = None,
) -> RuntimeConfig:
    """Load and validate YAML config plus provider secrets from env or .env."""

    config_path = Path(config_path)
    raw_config = _read_yaml_config(config_path)
    yaml_config = DiffToTweetConfig.model_validate(raw_config)

    env_path = Path(env_file) if env_file is not None else config_path.with_name(".env")
    settings = ProviderSettings.from_env_file(env_path)

    merged: dict[str, Any] = {
        **yaml_config.model_dump(),
        **settings.model_dump(),
    }
    key_field = _PROVIDER_KEY_FIELDS[yaml_config.provider]
    merged["provider_api_key"] = merged.get(key_field)

    return RuntimeConfig.model_validate(merged)


def _read_yaml_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a YAML mapping at the top level")

    return loaded
