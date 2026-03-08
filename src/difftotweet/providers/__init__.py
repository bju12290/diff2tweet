from __future__ import annotations

from difftotweet.config import LlmProvider, RuntimeConfig

from .base import BaseProvider, ProviderError
from .openai_provider import OpenAIProvider


def get_provider(config: RuntimeConfig) -> BaseProvider:
    """Return the provider implementation for the current runtime config."""

    if config.provider == LlmProvider.OPENAI:
        return OpenAIProvider()

    raise ProviderError(f"Provider '{config.provider}' is not implemented yet.")


__all__ = ["BaseProvider", "ProviderError", "get_provider"]
