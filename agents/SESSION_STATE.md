# SESSION_STATE

## Project
Feed project git commits, diffs, and repo context files into a CLI that generates candidate tweets via an LLM.

## Current Goal
Improve prompt quality by replacing freeform README context with structured project fields, then iterate on prompt output against real repos.

## To Do
- Consider documenting the reviewed artifact format in `docs/config.md` or a workflow doc
- After structured fields land, test against real repos and iterate on prompt based on output quality

## Current Architecture
Implemented the first reviewed generation flow under `src/difftotweet/`:
- `config/config_schema.py` validates non-secret YAML config with Pydantic v2, including `num_candidates`, `lookback_commits`, `readme_max_chars` (default 0), `context_max_chars`, `diff_ignore_patterns`, and the four structured project context fields
- `config/settings.py` loads provider API keys from `.env` / environment via `pydantic-settings`
- `config/load_config.py` reads YAML, validates it, merges env settings, and returns a typed runtime config with provider-specific key validation
- `git.py` discovers the repo root, resolves the commit range from the run log or `lookback_commits`, returns committed messages plus diff text in `GitContext`, and exposes `get_head_sha()` for successful-run logging
- `notes.py` walks up from CWD to the repo root and returns `NOTES.md` contents when present
- `readme.py` discovers repo-root `README.md`, truncates it to `readme_max_chars`, and returns `None` when absent or disabled
- `prompt.py` assembles the final prompt, renders structured project fields as a `## Project` section, filters noisy diff sections with `diff_ignore_patterns`, and applies the `context_max_chars` budget in priority order: project fields -> commits -> NOTES -> diff remainder
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
- Prompt quality needs iteration — structured project fields are the first improvement pass; further tuning expected after real-repo testing

## Resolved Decisions
- API keys via `.env` / env vars only; never in `diff2tweet.yaml`
- CLI invocation is `diff2tweet` with no args; auto-discovers git diff and `NOTES.md`
- Output folder (`.diff2tweet/`) is gitignored by default; users opt in to committing logs
- Config implementation uses Pydantic v2 `BaseModel` for YAML, `pydantic-settings` `BaseSettings` for secrets, and a merged runtime config object for CLI consumption
- Provider-specific validation happens at load time: the selected provider must have its corresponding API key in env / `.env`
- Git discovery reads committed changes only, uses `lookback_commits` on first run, and raises a clear error on empty ranges
- Notes discovery walks up to the repo root and returns `None` when `NOTES.md` is absent
- Typer is the CLI framework
- `README.md` context is opt-in (`readme_max_chars` defaults to 0); replaced in practice by the four structured project context fields
- Git commit messages use `--format=%B` (full body) for maximum LLM context
- Config discovery is fixed at `<repo-root>/diff2tweet.yaml`
- Provider abstraction: `BaseProvider` ABC in `providers/base.py`, concrete implementations per provider, `get_provider(config)` factory dispatches by `config.provider`
- Tweet candidate count is driven by `num_candidates` config (default 3, ge=1, le=10); enforced at the provider level via `config.num_candidates`
- Prompt context assembled in priority order: project fields (always included in full) -> commit messages -> NOTES.md -> filtered diff (remainder of `context_max_chars`)
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
Implement the four structured project context fields as prompt quality improvement phase 1.

### Config changes
- Add four optional string/list fields to `config_schema.py` and `RuntimeConfig`, all defaulting to empty:
  - `project_name: str = Field(default="")`
  - `project_summary: str = Field(default="")`
  - `project_audience: str = Field(default="")`
  - `project_key_terms: list[str] = Field(default_factory=list)`
- Change `readme_max_chars` default from 2000 to 0
- Add all four fields to `diff2tweet.yaml` (with comments) and `docs/config.md`

### `prompt.py`
- Replace the `## README` section with a `## Project` section built from the four structured fields
- Project fields are rendered before the context budget is applied — they are always included in full (small by design)
- Only render fields that are non-empty; skip the `## Project` section entirely if all four are empty
- Budget priority order: project fields -> commit messages -> NOTES.md -> filtered diff

### `readme.py` / `cli.py`
- `readme.py` and its discovery call in `cli.py` can be removed if `readme_max_chars` defaults to 0 and no test relies on it — or keep the module and just change the default. Keeping is safer for users who have set a non-zero value.

### Tests
- Update `test_prompt.py` to cover the `## Project` section rendering (all fields, partial fields, all empty)
- Update `test_config_loader.py` for the new fields and the `readme_max_chars` default change
