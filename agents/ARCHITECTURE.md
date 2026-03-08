# key system design and file map

## Current file map

- `pyproject.toml`: Packaging metadata, runtime dependencies, and dev test dependencies
- `diff2tweet.yaml`: Root project config scaffold for provider selection, model selection, prompt customization, tweet length, first-run git lookback, and output location
- `docs/config.md`: Human-readable explanation of YAML config fields and required provider env vars
- `docs/DESIGN.md`: Product and milestone planning notes
- `src/difftotweet/__init__.py`: Top-level package marker
- `src/difftotweet/config/__init__.py`: Public config API exports
- `src/difftotweet/config/config_schema.py`: Pydantic v2 schema for non-secret YAML config, including `lookback_commits`
- `src/difftotweet/config/settings.py`: `pydantic-settings` models for provider API keys from env / `.env`
- `src/difftotweet/config/load_config.py`: YAML reader and merged runtime config loader with provider-specific validation
- `src/difftotweet/git.py`: Git repo discovery, commit-range resolution, run-log lookup, and committed diff/message collection
- `src/difftotweet/notes.py`: Repo-root `NOTES.md` discovery that walks up from the current working directory
- `tests/test_config_loader.py`: Focused config validation test for missing provider API keys
- `tests/test_git_and_notes.py`: Git discovery and notes discovery coverage for happy-path and error-path behavior
- `agents/SESSION_STATE.md`: Short-lived project status for the next agent session
- `agents/DECISIONS.md`: Record of durable implementation decisions
