from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from difftotweet.config import RuntimeConfig
from difftotweet.providers import ProviderError, get_provider
from difftotweet.providers.openai_provider import OpenAIProvider


def test_get_provider_returns_openai_provider_for_openai_config():
    provider = get_provider(_runtime_config())

    assert isinstance(provider, OpenAIProvider)


def test_get_provider_raises_for_unimplemented_provider():
    config = _runtime_config(provider="anthropic")

    with pytest.raises(ProviderError, match="not implemented"):
        get_provider(config)


def test_openai_provider_generates_three_tweets(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"tweets": ["Tweet one", "Tweet two", "Tweet three"]}'
                        )
                    )
                ]
            )

    class _FakeOpenAI:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    tweets = OpenAIProvider().generate_tweets("prompt body", _runtime_config())

    assert tweets == ["Tweet one", "Tweet two", "Tweet three"]
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["messages"][1]["content"] == "prompt body"


def _runtime_config(*, provider: str = "openai") -> RuntimeConfig:
    return RuntimeConfig(
        provider=provider,
        model="gpt-4.1-mini",
        custom_instructions="",
        forced_hashtags=[],
        character_limit=280,
        lookback_commits=5,
        readme_max_chars=2000,
        context_max_chars=12000,
        diff_ignore_patterns=["*.lock", "dist/**"],
        output_folder=Path(".diff2tweet"),
        provider_api_key="test-key",
        openai_api_key="test-key",
        anthropic_api_key="test-key" if provider == "anthropic" else None,
    )
