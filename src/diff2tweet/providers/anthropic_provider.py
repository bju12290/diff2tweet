from __future__ import annotations

import json

from diff2tweet.config import RuntimeConfig

from .base import BaseProvider, ProviderError


class AnthropicProvider(BaseProvider):
    """Anthropic Messages API implementation for tweet generation."""

    def generate_tweets(self, prompt_text: str, config: RuntimeConfig) -> list[str]:
        api_key = config.provider_api_key.get_secret_value() if config.provider_api_key else None
        if not api_key:
            raise ProviderError("Anthropic provider is missing an API key.")

        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "The 'anthropic' package is required for provider 'anthropic'. "
                "Install it with: pip install 'diff2tweet[anthropic]'"
            ) from exc

        client = anthropic.Anthropic(api_key=api_key)
        tweets: list[str] = []
        for _ in range(config.num_candidates):
            message = client.messages.create(
                model=config.model,
                max_tokens=256,
                system="You generate tweet drafts from git context. Return only valid JSON with no markdown fencing.",
                messages=[
                    {"role": "user", "content": prompt_text},
                ],
            )
            tweets.append(_parse_anthropic_response(message))
        return tweets


def _parse_anthropic_response(message: object) -> str:
    content = getattr(message, "content", None)
    if not content:
        raise ProviderError("Anthropic returned no content.")

    raw = getattr(content[0], "text", None)
    if not raw:
        raise ProviderError("Anthropic returned an empty text block.")

    # Strip markdown fencing if the model wrapped the JSON anyway
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("Anthropic response was not valid JSON.") from exc

    tweet = payload.get("tweet")
    if not isinstance(tweet, str) or not tweet.strip():
        raise ProviderError("Anthropic response did not include a 'tweet' string.")

    return tweet.strip()
