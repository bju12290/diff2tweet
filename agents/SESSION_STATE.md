# SESSION_STATE

## Project
Feed project git commits, diffs, and repo context files into a CLI that generates candidate tweets via an LLM.

## Current Goal
Real-world testing in the developer's own projects to validate prompt quality, context filtering, and UX against genuine commit history.

## To Do
- Test in real projects and note where commit filtering over/under-fires on actual commit styles
- Observe how much NOTES.md moves output quality in practice (untested in eval)
- Consider surfacing the critic score to the user in CLI output so they can make an informed approval decision
- Consider documenting current prompt filtering behavior in `docs/config.md` once heuristics stabilize from real-world use

## Current Architecture
Implemented the full reviewed generation flow under `src/difftotweet/`:
- `config/config_schema.py` validates non-secret YAML config with Pydantic v2, including `num_candidates` (default 1), `commit_subject_min_chars` (default 20), `readme_max_chars` (default 0), `context_max_chars`, `diff_ignore_patterns`, and the six structured project context fields
- `config/settings.py` loads provider API keys from `.env` / environment via `pydantic-settings`
- `config/load_config.py` reads YAML, validates it, merges env settings, and returns a typed runtime config with provider-specific key validation
- `git.py` discovers the repo root, resolves the commit range from the run log or `lookback_commits`, returns committed messages plus diff text in `GitContext`, and exposes `get_head_sha()` for successful-run logging
- `notes.py` walks up from CWD to the repo root and returns `NOTES.md` contents when present
- `readme.py` discovers repo-root `README.md`, truncates it to `readme_max_chars`, and returns `None` when absent or disabled; the CLI no longer uses it by default in prompt assembly
- `prompt.py` assembles the final prompt with a tuned `_BASE_PROMPT` (see Generator Prompt below), renders structured project fields as a `## Project` section, filters commit messages by useful subject lines using the configurable `commit_subject_min_chars` threshold plus hard-coded junk-subject rules, filters noisy diff sections with filename and content heuristics, reformats diffs to compact basename headers, and applies the `context_max_chars` budget in priority order: project fields -> NOTES -> commit messages -> filtered diff remainder
- `providers/base.py` defines the provider contract, `providers/__init__.py` dispatches by `config.provider`, and `providers/openai_provider.py` implements OpenAI chat-completions with one independent API call per candidate (loop of `num_candidates` calls), each returning a single `{"tweet": "..."}` JSON object
- `logs.py` appends successful generation runs to `<output_folder>/run_log.jsonl`, returns the generation timestamp for downstream linking, and appends approval entries that reference the generation record
- `artifacts.py` writes one markdown artifact per reviewed run to `<output_folder>/runs/` with commit range, timestamps, candidates, and approval status
- `cli.py` is the Typer entrypoint; it finds `<repo-root>/diff2tweet.yaml`, loads config, gathers git and `NOTES.md` context, builds the prompt, generates the configured number of tweet candidates, prints them, prompts `typer.confirm()` for each candidate, and persists both append-only log entries and a markdown review artifact with clean exit-code-1 errors for user-facing failures
- `tests/test_approval.py`, `tests/test_cli.py`, `tests/test_config_loader.py`, `tests/test_git_and_notes.py`, `tests/test_readme.py`, `tests/test_prompt.py`, `tests/test_providers.py`, and `tests/test_logs.py` cover the implemented flow

## Generator Prompt
The `_BASE_PROMPT` in `prompt.py` has been tuned through multiple eval iterations. Current rules (in priority order):
1. Pick ONE change — the single most interesting or user-visible thing in the context; no kitchen-sink summaries
2. Lead with why it matters to the user — what they can now do, avoid, or understand; do not open with file names or implementation
3. Describe what changed for the user, not how it was implemented — omit internal function/class names, file paths, and mechanisms unless they are the only way to express the change
4. Stay within the configured character limit
5. Be concrete; do not invent outcomes not supported by the context
6. Avoid generic filler
7. Write like a real developer sharing a win, not a press release
8. Include forced hashtags only when they fit naturally
9. No numbering, labels, or surrounding commentary

The prompt asks for `{"tweet": "..."}` — one tweet per call. Candidate variety comes from independent calls, not from a single multi-output call.

## Eval Pipeline (`dev_tools/`)
`run_eval.py` runs generation + critic scoring against a fixed set of repos defined in `repos.yaml`. Key design points:
- Critic model: `gpt-5.1`; generator model is whatever is in `diff2tweet.yaml`
- Rubric has 10 criteria; `tweetability` (×2) and `readability` (×1.5) are weighted highest
- Tweetability cap enforced computationally: if `readability ≤ 3`, `tweetability` is clamped to 5 before overall is computed
- `overall` is computed deterministically from weighted criteria — never LLM-generated
- Outputs `dev_tools/last_eval.md` (human-readable) and `dev_tools/last_eval.json` (structured)
- Eval score progression: 5.29 → 6.29 → 6.61 → 6.97 (gpt-5-mini) → **7.48 (gpt-5.1 generator)**

## Constraints
- Python project, CLI entrypoint `diff2tweet` (no args - auto-discovers everything)
- Config is YAML (`diff2tweet.yaml`) validated with Pydantic v2
- Default LLM provider is OpenAI with a user-supplied API key via `.env`
- Git input is committed changes only - no staged, working tree, or untracked content
- `last_processed_sha` advances at generation time, not approval time

## Open Problems
- OpenAI is the only implemented provider; Anthropic and Gemini remain config-valid but runtime-unimplemented
- Accuracy criterion in eval scores against a 3000-char diff excerpt; truncation causes some legitimate claims to score lower than deserved — increasing excerpt size to 6000 chars may improve signal
- Authenticity ceiling (~7.5) likely requires few-shot voice examples or user-supplied tone examples to break through with prompting alone

## Resolved Decisions
- API keys via `.env` / env vars only; never in `diff2tweet.yaml`
- CLI invocation is `diff2tweet` with no args; auto-discovers git diff and `NOTES.md`
- Output folder (`.diff2tweet/`) is gitignored by default; users opt in to committing logs
- Config implementation uses Pydantic v2 `BaseModel` for YAML, `pydantic-settings` `BaseSettings` for secrets, and a merged runtime config object for CLI consumption
- Provider-specific validation happens at load time: the selected provider must have its corresponding API key in env / `.env`
- Git discovery reads committed changes only, uses `lookback_commits` on first run, and raises a clear error on empty ranges
- Notes discovery walks up to the repo root and returns `None` when `NOTES.md` is absent
- Typer is the CLI framework
- `README.md` context is opt-in (`readme_max_chars` defaults to 0); structured project fields are the preferred prompt-framing path
- Git commit messages use `--format=%B` (full body) for maximum LLM context
- Config discovery is fixed at `<repo-root>/diff2tweet.yaml`
- Provider abstraction: `BaseProvider` ABC in `providers/base.py`, concrete implementations per provider, `get_provider(config)` factory dispatches by `config.provider`
- `num_candidates` defaults to 1; each candidate is generated via an independent API call with no cross-candidate awareness; candidate variety comes from temperature, not multi-output prompting
- Prompt context assembled in priority order: project fields (always included in full) -> NOTES.md -> commit messages -> filtered diff (remainder of `context_max_chars`)
- Structured project metadata includes `project_name`, `project_summary`, `project_audience`, `project_stage`, `project_tone`, and `project_key_terms`; stage and tone are literal-constrained prompt hints with defaults of `prototype` and `technical`
- Diff noise filtering in `prompt.py` via `diff_ignore_patterns` config list; filtering is a prompt-building concern, not a git concern
- Additional hard-filters: pure whole-file deletions dropped; auto-generated content dropped; diff headers reformatted to compact `# basename` separators
- Successful runs persisted to `<output_folder>/run_log.jsonl`; `last_processed_sha` advances at generation time
- Approval is sequential y/n per candidate; statuses appended as a second JSONL entry referencing the generation timestamp
- Markdown review artifacts always written after approval collection, even if every candidate is denied
- Pre-generation tweetability gate was considered and rejected: tool should always produce output and let the user decide; a weak tweet is better UX than a token spend with no output

## Next Step
Real-world testing in the developer's own projects.

### Suggested Focus
- Watch for commit filtering over/under-firing on your actual commit style and message conventions
- Test NOTES.md with real context to see how much it moves output quality
- Note any runs where the output feels off and trace it back to prompt, diff filtering, or content quality
- If accuracy scores remain low in eval, consider increasing `_context_excerpt` from 3000 to 6000 chars in `run_eval.py`
