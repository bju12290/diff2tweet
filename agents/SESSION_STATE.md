# SESSION_STATE

## Project
Feed project git commits, diffs, and repo context files into a CLI that generates candidate tweets via an LLM.

## Current Goal
Build on the new generation flow with approval workflow and artifact writing for reviewed tweet drafts.

## To Do
- Expose # of tweet candidates as a config flag

## Current Architecture
Implemented the first end-to-end generation flow under `src/difftotweet/`:
- `config/config_schema.py` validates non-secret YAML config with Pydantic v2, including `lookback_commits`, `readme_max_chars`, `context_max_chars`, and `diff_ignore_patterns`
- `config/settings.py` loads provider API keys from `.env` / environment via `pydantic-settings`
- `config/load_config.py` reads YAML, validates it, merges env settings, and returns a typed runtime config with provider-specific key validation
- `git.py` discovers the repo root, resolves the commit range from the run log or `lookback_commits`, returns committed messages plus diff text in `GitContext`, and exposes `get_head_sha()` for successful-run logging
- `notes.py` walks up from CWD to the repo root and returns `NOTES.md` contents when present
- `readme.py` discovers repo-root `README.md`, truncates it to `readme_max_chars`, and returns `None` when absent or disabled
- `prompt.py` assembles the final prompt, filters noisy diff sections with `diff_ignore_patterns`, and applies the `context_max_chars` budget in priority order: README -> commits -> NOTES -> diff remainder
- `providers/base.py` defines the provider contract, `providers/__init__.py` dispatches by `config.provider`, and `providers/openai_provider.py` implements OpenAI chat-completions generation with a JSON `{"tweets": [...]}` response contract
- `logs.py` appends successful runs to `<output_folder>/run_log.jsonl` with timestamp, `last_processed_sha`, commit range, and tweet candidates
- `cli.py` is the Typer entrypoint; it finds `<repo-root>/diff2tweet.yaml`, loads config, gathers git/notes/readme context, builds the prompt, generates 3 tweet candidates, prints them, and logs the successful run with clean exit-code-1 errors for user-facing failures
- `tests/test_cli.py`, `tests/test_config_loader.py`, `tests/test_git_and_notes.py`, `tests/test_readme.py`, `tests/test_prompt.py`, `tests/test_providers.py`, and `tests/test_logs.py` cover the implemented flow

## Constraints
- Python project, CLI entrypoint `diff2tweet` (no args - auto-discovers everything)
- Config is YAML (`diff2tweet.yaml`) validated with Pydantic v2
- Default LLM provider is OpenAI with a user-supplied API key via `.env`
- Git input is committed changes only - no staged, working tree, or untracked content
- The CLI now generates and logs candidates, but approval workflow and markdown artifact writing are still unimplemented

## Open Problems
- Approval workflow is not implemented yet; generated candidates are printed immediately with no y/n review step
- Markdown artifact writing is not implemented yet; only the JSONL run log is written today
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
- Always generate exactly 3 tweet candidates per run
- Prompt context assembled in priority order: README -> commit messages -> NOTES.md -> filtered diff (remainder of `context_max_chars`)
- Diff noise filtering in `prompt.py` via `diff_ignore_patterns` config list (defaults: lock files, minified assets, dist/build dirs); full diff is still returned by `git.py`, filtering is a prompt-building concern
- Successful runs are persisted to `<output_folder>/run_log.jsonl` with timestamp, HEAD SHA, commit range, and generated tweet candidates so the next run can diff from the latest processed commit
- `last_processed_sha` advances at generation time, not approval time — reviewing commits is enough to advance the range; denied-everything runs do not replay the same diff
- Approval is a sequential y/n prompt per candidate after all 3 are printed; statuses + approval timestamp are appended as a second JSONL entry referencing the generation timestamp, keeping the log append-only

## Recent Changes
- Added `context_max_chars` and `diff_ignore_patterns` to the YAML schema, runtime config, sample config, and config docs
- Implemented `src/difftotweet/prompt.py` for prompt assembly, diff noise filtering, and context budgeting
- Implemented provider abstraction in `src/difftotweet/providers/` with an OpenAI-backed generator
- Implemented `src/difftotweet/logs.py` for JSONL run logging and updated `src/difftotweet/git.py` with `get_head_sha()`
- Replaced the preview-only CLI flow with real candidate generation and successful-run logging in `src/difftotweet/cli.py`
- Added `tests/test_prompt.py`, `tests/test_providers.py`, and `tests/test_logs.py`; updated CLI/config/git/readme tests for the generation flow
- Verified the implemented tests with `.venv\Scripts\python.exe -m pytest tests\test_config_loader.py tests\test_git_and_notes.py tests\test_readme.py tests\test_prompt.py tests\test_providers.py tests\test_logs.py tests\test_cli.py -q`

## Next Step
Implement the approval workflow and markdown artifact writing.

### CLI changes (`cli.py`)
- After printing all 3 candidates, prompt the user sequentially: `"Approve tweet 1? [y/n]: "` for each
- Collect approval results as a `dict[int, bool]` (1-indexed)
- Call a new `logs.write_approval_entry(...)` and `artifacts.write_markdown(...)` with the results
- `typer.confirm()` is the right Typer primitive for y/n prompts

### New: `src/difftotweet/logs.py` — approval entry
- Add `write_approval_entry(output_folder, generation_timestamp, approvals, approval_timestamp)` that appends a second JSONL record to `run_log.jsonl`
- Entry shape: `{"type": "approval", "generation_timestamp": "...", "approvals": {"1": true, "2": false, "3": true}, "approval_timestamp": "..."}`
- `generation_timestamp` links back to the matching generation entry

### New: `src/difftotweet/artifacts.py`
- `write_markdown(output_folder, generation_timestamp, commit_range, tweets, approvals)` writes a single markdown file per run to `<output_folder>/runs/<generation_timestamp>.md`
- File contains: commit range, all 3 candidates with their approval status, and the timestamps
- File is written regardless of approval outcome (approved, denied, and mixed runs all get an artifact)

### Tests
- `tests/test_approval.py` — cover `write_approval_entry` JSONL shape and `write_markdown` file content
- Update `tests/test_cli.py` — mock `typer.confirm()` to test approve-all, deny-all, and mixed approval paths; assert correct artifact creation and log entry
