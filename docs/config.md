# Config

`diff2tweet` reads its non-secret project config from `diff2tweet.yaml` in the repo root.

Secrets such as LLM API keys do not belong in YAML. Supply them through environment variables or a repo-local `.env` file.

## Supported YAML fields

- `provider`: LLM provider to use. Supported values today are `openai`, `anthropic`, and `gemini`.
- `model`: Model name for the selected provider.
- `project_name`: Optional short project name shown to the LLM as part of structured project context.
- `project_summary`: Optional plain-language summary of what the project does.
- `project_audience`: Optional description of the people the project is for.
- `project_stage`: Project maturity hint for the prompt. Supported values are `prototype`, `beta`, and `launched`. Defaults to `prototype`.
- `project_tone`: Writing voice hint for the prompt. Supported values are `technical`, `founder`, and `casual`. Defaults to `technical`.
- `project_key_terms`: Optional list of domain terms, product vocabulary, or phrases that help the LLM stay specific.
- `custom_instructions`: Extra prompt guidance added to the default tweet-writing prompt.
- `forced_hashtags`: Hashtags the tool should try to preserve in generated drafts. Each entry must start with `#`.
- `character_limit`: Maximum length for a generated tweet draft.
- `num_candidates`: Number of tweet candidates to request and validate per run. Must be between `1` and `10`.
- `lookback_commits`: First-run fallback commit count when no prior run log exists.
- `commit_subject_min_chars`: Minimum subject-line length required for a commit message to be included in prompt context. Defaults to `20`. Exact-match low-signal subjects such as `fix` and `wip` are still dropped separately.
- `readme_max_chars`: Maximum number of repo-root `README.md` characters to include as extra context. Defaults to `0`, which disables README context in favor of the structured project fields above.
- `context_max_chars`: Maximum total characters reserved for project fields, commit messages, `NOTES.md`, and filtered diff content inside the LLM prompt.
- `diff_ignore_patterns`: File globs filtered out of diff context before the prompt budget is applied. Defaults cover lock files, minified assets, and common build output directories.
- `output_folder`: Relative folder where generated drafts and run logs are stored.

## Environment variables

The selected provider must have its matching API key available in the environment or `.env` file:

- `provider: openai` -> `OPENAI_API_KEY`
- `provider: anthropic` -> `ANTHROPIC_API_KEY`
- `provider: gemini` -> `GEMINI_API_KEY` or `GOOGLE_API_KEY`
