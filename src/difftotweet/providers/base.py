from __future__ import annotations

from abc import ABC, abstractmethod

from difftotweet.config import RuntimeConfig


class ProviderError(RuntimeError):
    """Raised when a configured LLM provider cannot generate tweet candidates."""


class BaseProvider(ABC):
    """Abstract provider interface for tweet generation."""

    @abstractmethod
    def generate_tweets(self, prompt_text: str, config: RuntimeConfig) -> list[str]:
        """Generate exactly config.num_candidates tweet candidates from the prepared prompt."""
