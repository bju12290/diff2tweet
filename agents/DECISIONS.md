# important decisions only

- 2026-03-08: The initial config scaffold lives at the repo root as `diff2tweet.yaml` so the future CLI can use a simple default discovery path.
- 2026-03-08: API keys (e.g. `OPENAI_API_KEY`) must be supplied via environment variables or a `.env` file. They must never appear in `diff2tweet.yaml` or be committed to source control.
- 2026-03-08: CLI is invoked as `diff2tweet` with no arguments. The tool auto-discovers the git diff from the current repo and optionally reads `NOTES.md` from the repo root. Users never pass a diff file path manually.
- 2026-03-08: The output folder (`.diff2tweet/`) is gitignored by default. Users may opt in to committing logs by removing the `.diff2tweet/` entry from their `.gitignore`.
- 2026-03-08: Config implementation uses Pydantic v2 `BaseModel` for YAML, `pydantic-settings` `BaseSettings` for secrets, and a merged runtime config object for CLI consumption.
- 2026-03-08: Provider-specific validation happens at load time: the selected provider must have its corresponding API key in env / `.env`.
- 2026-03-08: Git diff source is committed changes only (`git diff <range>`). Staged changes, working tree changes, and untracked files are excluded - the tool is for tweeting about finished work.
- 2026-03-08: Default commit range is "since last run" (last-processed SHA stored in run log). First-run fallback is `lookback_commits` from config (default 5, i.e. `HEAD~5..HEAD`). Commit messages always span the same range as the diff.
- 2026-03-08: Run history for git discovery currently reads `.diff2tweet/run_log.jsonl` and uses the most recent JSON line with `last_processed_sha` as the prior processed commit.
- 2026-03-08: If the detected commit range is empty (no commits found), the tool raises a clear user-facing error rather than silently producing an empty result.
- 2026-03-08: Notes discovery walks up from the current working directory to the git repo root and treats a missing `NOTES.md` file as a non-error.
