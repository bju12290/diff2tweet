# Config

`diff2tweet` reads its non-secret project config from `diff2tweet.yaml` in the repo root.

Secrets such as LLM API keys do not belong in YAML. Supply them through environment variables or a repo-local `.env` file.

## Supported YAML fields

- `provider`: LLM provider to use. Supported values today are `openai`, `anthropic`, and `gemini`.
- `model`: Model name for the selected provider.
- `custom_instructions`: Extra prompt guidance added to the default tweet-writing prompt.
- `forced_hashtags`: Hashtags the tool should try to preserve in generated drafts. Each entry must start with `#`.
- `character_limit`: Maximum length for a generated tweet draft.
- `lookback_commits`: First-run fallback commit count when no prior run log exists.
- `output_folder`: Relative folder where generated drafts and run logs are stored.

## Environment variables

The selected provider must have its matching API key available in the environment or `.env` file:

- `provider: openai` -> `OPENAI_API_KEY`
- `provider: anthropic` -> `ANTHROPIC_API_KEY`
- `provider: gemini` -> `GEMINI_API_KEY` or `GOOGLE_API_KEY`
