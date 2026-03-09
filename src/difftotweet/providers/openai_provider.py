from __future__ import annotations

import json
from typing import Any

from difftotweet.config import RuntimeConfig

from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    """OpenAI chat-completions implementation for tweet generation."""

    def generate_tweets(self, prompt_text: str, config: RuntimeConfig) -> list[str]:
        api_key = config.provider_api_key.get_secret_value() if config.provider_api_key else None
        if not api_key:
            raise ProviderError("OpenAI provider is missing an API key.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError(
                "The 'openai' package is required for provider 'openai'. Install project dependencies first."
            ) from exc

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=config.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You generate tweet drafts from git context.",
                },
                {
                    "role": "user",
                    "content": prompt_text,
                },
            ],
        )
        return _parse_tweets_response(response, config.num_candidates)


def _parse_tweets_response(response: Any, expected_count: int) -> list[str]:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ProviderError("OpenAI returned no choices.")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not content:
        raise ProviderError("OpenAI returned an empty response.")

    if isinstance(content, list):
        text = "".join(
            part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
            for part in content
        )
    else:
        text = str(content)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("OpenAI response was not valid JSON.") from exc

    tweets = payload.get("tweets")
    if not isinstance(tweets, list):
        raise ProviderError("OpenAI response did not include a 'tweets' list.")

    cleaned = [tweet.strip() for tweet in tweets if isinstance(tweet, str) and tweet.strip()]
    if len(cleaned) != expected_count:
        raise ProviderError(
            f"OpenAI response must contain exactly {expected_count} tweet candidates."
        )

    return cleaned
