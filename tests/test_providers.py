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


def test_openai_provider_returns_one_tweet_for_single_candidate(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"tweet": "Tweet one"}')
                    )
                ]
            )

    class _FakeOpenAI:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    tweets = OpenAIProvider().generate_tweets("prompt body", _runtime_config(num_candidates=1))

    assert tweets == ["Tweet one"]
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["messages"][1]["content"] == "prompt body"


def test_openai_provider_makes_one_call_per_candidate(monkeypatch):
    call_count = [0]

    class _FakeCompletions:
        def create(self, **kwargs):
            call_count[0] += 1
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=f'{{"tweet": "Tweet {call_count[0]}"}}'
                        )
                    )
                ]
            )

    class _FakeOpenAI:
        def __init__(self, api_key: str):
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    tweets = OpenAIProvider().generate_tweets("prompt body", _runtime_config(num_candidates=3))

    assert len(tweets) == 3
    assert call_count[0] == 3
    assert tweets == ["Tweet 1", "Tweet 2", "Tweet 3"]


def test_openai_provider_raises_on_missing_tweet_key(monkeypatch):
    class _FakeCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"tweets": ["wrong shape"]}')
                    )
                ]
            )

    class _FakeOpenAI:
        def __init__(self, api_key: str):
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    with pytest.raises(ProviderError, match="did not include a 'tweet' string"):
        OpenAIProvider().generate_tweets("prompt body", _runtime_config())


def _runtime_config(*, provider: str = "openai", num_candidates: int = 1) -> RuntimeConfig:
    return RuntimeConfig(
        provider=provider,
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
        num_candidates=num_candidates,
        lookback_commits=5,
        commit_subject_min_chars=20,
        readme_max_chars=0,
        context_max_chars=12000,
        max_doc_diff_sections=3,
        max_doc_section_chars=1000,
        diff_ignore_patterns=["*.lock", "dist/**"],
        output_folder=Path(".diff2tweet"),
        provider_api_key="test-key",
        openai_api_key="test-key",
        anthropic_api_key="test-key" if provider == "anthropic" else None,
    )
