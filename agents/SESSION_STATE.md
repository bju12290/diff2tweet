# SESSION_STATE

## Project
Feed project git commits, diffs, and repo context files into a CLI that generates candidate tweets via an LLM.

## Current Goal
Refine the reviewed-output flow and extend configuration after approval logging and markdown artifacts landed.

## To Do
- Consider documenting the reviewed artifact format in `docs/config.md` or a workflow doc
- Exercise prompt quality against real repos and refine the generation prompt based on output quality

## Current Architecture
Implemented the first reviewed generation flow under `src/difftotweet/`:
- `config/config_schema.py` validates non-secret YAML config with Pydantic v2, including `num_candidates`, `lookback_commits`, `readme_max_chars`, `context_max_chars`, and `diff_ignore_patterns`
- `config/settings.py` loads provider API keys from `.env` / environment via `pydantic-settings`
- `config/load_config.py` reads YAML, validates it, merges env settings, and returns a typed runtime config with provider-specific key validation
- `git.py` discovers the repo root, resolves the commit range from the run log or `lookback_commits`, returns committed messages plus diff text in `GitContext`, and exposes `get_head_sha()` for successful-run logging
- `notes.py` walks up from CWD to the repo root and returns `NOTES.md` contents when present
- `readme.py` discovers repo-root `README.md`, truncates it to `readme_max_chars`, and returns `None` when absent or disabled
- `prompt.py` assembles the final prompt, filters noisy diff sections with `diff_ignore_patterns`, and applies the `context_max_chars` budget in priority order: README -> commits -> NOTES -> diff remainder
- `providers/base.py` defines the provider contract, `providers/__init__.py` dispatches by `config.provider`, and `providers/openai_provider.py` implements OpenAI chat-completions generation with a JSON `{"tweets": [...]}` response contract
- `logs.py` appends successful generation runs to `<output_folder>/run_log.jsonl`, returns the generation timestamp for downstream linking, and appends approval entries that reference the generation record
- `artifacts.py` writes one markdown artifact per reviewed run to `<output_folder>/runs/` with commit range, timestamps, candidates, and approval status
- `cli.py` is the Typer entrypoint; it finds `<repo-root>/diff2tweet.yaml`, loads config, gathers git/notes/readme context, builds the prompt, generates the configured number of tweet candidates, prints them, prompts `typer.confirm()` for each candidate, and persists both append-only log entries and a markdown review artifact with clean exit-code-1 errors for user-facing failures
- `tests/test_approval.py`, `tests/test_cli.py`, `tests/test_config_loader.py`, `tests/test_git_and_notes.py`, `tests/test_readme.py`, `tests/test_prompt.py`, `tests/test_providers.py`, and `tests/test_logs.py` cover the implemented flow

## Constraints
- Python project, CLI entrypoint `diff2tweet` (no args - auto-discovers everything)
- Config is YAML (`diff2tweet.yaml`) validated with Pydantic v2
- Default LLM provider is OpenAI with a user-supplied API key via `.env`
- Git input is committed changes only - no staged, working tree, or untracked content
- `last_processed_sha` still advances at generation time, not approval time

## Open Problems
- OpenAI is the only implemented provider; Anthropic and Gemini remain config-valid but runtime-unimplemented
- Prompt quality likely needs iteration once real outputs are exercised against more repos and diff shapes

## Resolved Decisions
- API keys via `.env` / env vars only; never in `diff2tweet.yaml`
- CLI invocation is `diff2tweet` with no args; auto-discovers git diff and `NOTES.md`
- Output folder (`.diff2tweet/`) is gitignored by default; users opt in to committing logs
- Config implementation uses Pydantic v2 `BaseModel` for YAML, `pydantic-settings` `BaseSettings` for secrets, and a merged runtime config object for CLI consumption
- Provider-specific validation happens at load time: the selected provider must have its corresponding API key in env / `.env`
- Git discovery reads committed changes only, uses `lookback_commits` on first run, and raises a clear error on empty ranges
- Notes discovery walks up to the repo root and returns `None` when `NOTES.md` is absent
- Typer is the CLI framework
- `README.md` is discovered at repo root, truncated to `readme_max_chars` (default 2000); set to 0 to exclude
- Git commit messages use `--format=%B` (full body) for maximum LLM context
- Config discovery is fixed at `<repo-root>/diff2tweet.yaml`
- Provider abstraction: `BaseProvider` ABC in `providers/base.py`, concrete implementations per provider, `get_provider(config)` factory dispatches by `config.provider`
- Tweet candidate count is driven by `num_candidates` config (default 3, ge=1, le=10); enforced at the provider level via `config.num_candidates`
- Prompt context assembled in priority order: README -> commit messages -> NOTES.md -> filtered diff (remainder of `context_max_chars`)
- Diff noise filtering in `prompt.py` via `diff_ignore_patterns` config list (defaults: lock files, minified assets, dist/build dirs); full diff is still returned by `git.py`, filtering is a prompt-building concern
- Successful runs are persisted to `<output_folder>/run_log.jsonl` with timestamp, HEAD SHA, commit range, and generated tweet candidates so the next run can diff from the latest processed commit
- `last_processed_sha` advances at generation time, not approval time - reviewing commits is enough to advance the range; denied-everything runs do not replay the same diff
- Approval is a sequential y/n prompt per candidate after all candidates are printed; statuses + approval timestamp are appended as a second JSONL entry referencing the generation timestamp, keeping the log append-only
- Markdown review artifacts are always written after approval collection, even if every candidate is denied

## Recent Changes
- Added `num_candidates` to `config/config_schema.py`, `config/load_config.py`, the sample `diff2tweet.yaml`, and `docs/config.md`
- Updated `prompt.py` to request exactly `config.num_candidates` tweet candidates instead of hard-coding 3
- Updated `providers/base.py` and `providers/openai_provider.py` so provider contracts and OpenAI response validation enforce `config.num_candidates`
- Added tests covering `num_candidates` loading from YAML plus prompt/provider behavior when `num_candidates=2`
- Verified the config, prompt, provider, CLI, and approval paths with `.venv\Scripts\python.exe -m pytest tests\test_config_loader.py tests\test_prompt.py tests\test_providers.py tests\test_cli.py tests\test_approval.py -q`

## Next Step
Consider documenting the reviewed artifact format in `docs/config.md` or a workflow doc, then exercise prompt quality against real repos and refine the generation prompt based on output quality.
