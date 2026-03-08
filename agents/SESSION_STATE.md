# SESSION_STATE

## Project
Feed project git commits, diffs, and a NOTES.md file to get candidate tweets output from an LLM.

## Current Goal
Build the first CLI flow that auto-discovers config, git context, and optional notes, then prepares that data for tweet generation.

## Current Architecture
Implemented the config and discovery foundation under `src/difftotweet/`:
- `config/config_schema.py` validates non-secret YAML config with Pydantic v2, including `lookback_commits`
- `config/settings.py` loads provider API keys from `.env` / environment via `pydantic-settings`
- `config/load_config.py` reads YAML, validates it, merges env settings, and returns a typed runtime config with provider-specific key validation
- `git.py` discovers the repo root, resolves the commit range from the run log or `lookback_commits`, and returns committed messages plus diff text in `GitContext`
- `notes.py` walks up from CWD to the repo root and returns `NOTES.md` contents when present
- `tests/test_config_loader.py` and `tests/test_git_and_notes.py` cover the implemented config and discovery behavior

## Constraints
- Python project, CLI entrypoint `diff2tweet` (no args - auto-discovers everything)
- Config is YAML (`diff2tweet.yaml`) validated with Pydantic v2
- Default LLM provider is OpenAI with a user-supplied API key via `.env`
- Git input is committed changes only - no staged, working tree, or untracked content

## Open Problems
- Final config discovery rules are not implemented yet (walk up from CWD? require repo root?)
- Provider abstraction design is undecided (how to swap OpenAI -> Claude/Gemini/Ollama cleanly)
- CLI behavior for missing or invalid config is still undefined
- Run-log writing is not implemented yet, so `last_processed_sha` is only consumed today, not produced

## Resolved Decisions
- API keys via `.env` / env vars only; never in `diff2tweet.yaml`
- CLI invocation is `diff2tweet` with no args; auto-discovers git diff and `NOTES.md`
- Output folder (`.diff2tweet/`) is gitignored by default; users opt in to committing logs
- Config implementation uses Pydantic v2 `BaseModel` for YAML, `pydantic-settings` `BaseSettings` for secrets, and a merged runtime config object for CLI consumption
- Provider-specific validation happens at load time: the selected provider must have its corresponding API key in env / `.env`
- Git discovery reads committed changes only, uses `lookback_commits` on first run, and raises a clear error on empty ranges
- Notes discovery walks up to the repo root and returns `None` when `NOTES.md` is absent

## Recent Changes
- Added `lookback_commits` to the YAML config schema, runtime config, sample config, and config docs
- Implemented `src/difftotweet/git.py` with repo-root discovery, run-log lookup, commit-range selection, and committed diff/message collection
- Implemented `src/difftotweet/notes.py` for optional `NOTES.md` discovery from any nested working directory
- Added `tests/test_git_and_notes.py` covering last-run behavior, first-run fallback, empty-range errors, and notes presence/absence
- Verified the implemented tests with `python -m pytest tests/test_config_loader.py tests/test_git_and_notes.py -q`

## Next Step
Implement the first CLI entrypoint and orchestration layer.

### Suggested scope
- Add a `diff2tweet` CLI entrypoint in `pyproject.toml`
- Discover and load `diff2tweet.yaml` from the repo context
- Call `load_config()`, `discover_git_context()`, and `discover_notes()` in one top-level flow
- Define the user-facing error handling for missing config, missing repo, and empty git ranges
- Return or print a structured preview payload for the next prompt-generation step
