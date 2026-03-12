from __future__ import annotations

import json

from diff2tweet.config import RuntimeConfig

from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    """Google Gemini implementation for tweet generation."""

    def generate_tweets(self, prompt_text: str, config: RuntimeConfig) -> list[str]:
        api_key = config.provider_api_key.get_secret_value() if config.provider_api_key else None
        if not api_key:
            raise ProviderError("Gemini provider is missing an API key.")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                "The 'google-genai' package is required for provider 'gemini'. "
                "Install it with: pip install 'diff2tweet[gemini]'"
            ) from exc

        client = genai.Client(api_key=api_key)
        tweets: list[str] = []
        for _ in range(config.num_candidates):
            response = client.models.generate_content(
                model=config.model,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    system_instruction="You generate tweet drafts from git context. Return only valid JSON.",
                    response_mime_type="application/json",
                ),
            )
            tweets.append(_parse_gemini_response(response))
        return tweets


def _parse_gemini_response(response: object) -> str:
    text = getattr(response, "text", None)
    if not text:
        raise ProviderError("Gemini returned an empty response.")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("Gemini response was not valid JSON.") from exc

    tweet = payload.get("tweet")
    if not isinstance(tweet, str) or not tweet.strip():
        raise ProviderError("Gemini response did not include a 'tweet' string.")

    return tweet.strip()
