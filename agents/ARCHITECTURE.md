# key system design and file map

## Current file map

- `pyproject.toml`: Packaging metadata, runtime dependencies, dev test dependencies, and the `diff2tweet` console script entrypoint
- `diff2tweet.yaml`: Root project config scaffold for provider selection, model selection, prompt customization, tweet length, git lookback, prompt budgeting, diff filtering, and output location
- `docs/config.md`: Human-readable explanation of YAML config fields and required provider env vars
- `docs/DESIGN.md`: Product and milestone planning notes
- `src/difftotweet/__init__.py`: Top-level package marker
- `src/difftotweet/cli.py`: Typer CLI entrypoint that auto-discovers repo context, generates 3 tweet candidates, prints them, and logs the run
- `src/difftotweet/git.py`: Git repo discovery, commit-range resolution, run-log lookup, committed diff/message collection, and HEAD SHA lookup for logging
- `src/difftotweet/logs.py`: JSONL run-log writer for successful tweet-generation runs
- `src/difftotweet/notes.py`: Repo-root `NOTES.md` discovery that walks up from the current working directory
- `src/difftotweet/prompt.py`: Prompt builder that combines README, commit messages, NOTES, and filtered diff text under the configured context budget
- `src/difftotweet/readme.py`: Repo-root `README.md` discovery with configurable truncation
- `src/difftotweet/providers/__init__.py`: Public provider factory that returns the configured provider implementation
- `src/difftotweet/providers/base.py`: Abstract provider contract and shared provider error type
- `src/difftotweet/providers/openai_provider.py`: OpenAI chat-completions implementation that parses a JSON `tweets` array
- `src/difftotweet/config/__init__.py`: Public config API exports
- `src/difftotweet/config/config_schema.py`: Pydantic v2 schema for non-secret YAML config, including git lookback, README truncation, prompt budget, and diff ignore patterns
- `src/difftotweet/config/load_config.py`: YAML reader and merged runtime config loader with provider-specific validation
- `src/difftotweet/config/settings.py`: `pydantic-settings` models for provider API keys from env / `.env`
- `tests/test_cli.py`: CLI generation-path coverage for successful candidate output, run logging, and clean error handling
- `tests/test_config_loader.py`: Focused config validation test for missing provider API keys
- `tests/test_git_and_notes.py`: Git discovery, run-log consumption, and notes discovery coverage for happy-path and error-path behavior
- `tests/test_logs.py`: JSONL run-log writing coverage for successful runs
- `tests/test_prompt.py`: Prompt ordering, diff-noise filtering, and context-budget enforcement coverage
- `tests/test_providers.py`: Provider factory coverage and mocked OpenAI client call-shape coverage
- `tests/test_readme.py`: README discovery coverage for truncation, absence, and opt-out behavior
- `agents/README.md`: Quick start file for future agents
- `agents/SESSION_STATE.md`: Short-lived project status for the next agent session
- `agents/DECISIONS.md`: Record of durable implementation decisions
