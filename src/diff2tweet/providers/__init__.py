from __future__ import annotations

from diff2tweet.config import LlmProvider, RuntimeConfig

from .anthropic_provider import AnthropicProvider
from .base import BaseProvider, ProviderError
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


def get_provider(config: RuntimeConfig) -> BaseProvider:
    """Return the provider implementation for the current runtime config."""

    if config.provider == LlmProvider.OPENAI:
        return OpenAIProvider()
    if config.provider == LlmProvider.ANTHROPIC:
        return AnthropicProvider()
    if config.provider == LlmProvider.GEMINI:
        return GeminiProvider()

    raise ProviderError(f"Provider '{config.provider}' is not implemented.")


__all__ = ["BaseProvider", "ProviderError", "get_provider"]
