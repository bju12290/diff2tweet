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
- `diff_ignore_patterns`: File globs filtered out of diff context before the prompt budget is applied. Defaults cover lock files, minified assets, and common build output directories. Replaces the default list entirely when set.
- `diff_ignore_patterns_extra`: Additional globs appended to `diff_ignore_patterns` without replacing the defaults. Use this when you want to keep the built-in exclusions and only add your own.
- `max_doc_diff_sections`: Maximum number of documentation diff sections (files in `docs/`, `doc/`, `documentation/`, or ending in `.md`/`.rst`) to include. Defaults to `3`. Set to `0` to exclude all doc diffs.
- `max_doc_section_chars`: Maximum characters per included documentation diff section. Sections exceeding this are truncated at a line boundary with a `[...truncated]` marker. Defaults to `1000`.
- `output_folder`: Relative folder where generated drafts and run logs are stored.
- `auto_tweet`: When `true`, prompts for approval of each candidate after generation and records the decision in the run log. Defaults to `false`.

## Filtering

Before building the prompt, `diff2tweet` filters both commit messages and diff sections to reduce noise. Understanding what gets dropped helps diagnose cases where the tool picks the wrong change to write about, or where relevant context goes missing.

### Commit message filtering

Each commit message is evaluated on its subject line (the first non-empty line). A message is **dropped** if any of these conditions are true:

| Condition | Example | Config |
|-----------|---------|--------|
| Subject is an exact match for a low-signal word | `fix`, `wip`, `update`, `misc`, `cleanup`, `typo`, `temp` | hard-coded |
| Subject is shorter than the minimum | `docs` (3 chars < default 20) | `commit_subject_min_chars` |
| Subject matches a bot/dependency pattern | `chore(deps): bump lodash`, `Bump react from 17 to 18` | hard-coded |
| Message body contains a dependency automation signal | body contains `dependabot[bot]` or `updated-dependencies:` | hard-coded |

Kept messages are also cleaned before being sent to the LLM:

- `Co-authored-by:`, `Signed-off-by:`, `Reviewed-by:`, and similar git trailers are stripped from the message body.
- CI skip directives (`[skip ci]`, `[ci skip]`, `[no ci]`, `[skip actions]`) are removed.

To lower the subject length threshold, set `commit_subject_min_chars` to a smaller value. Setting it to `0` disables length filtering entirely (only exact-match junk subjects and bot commits are still dropped).

### Diff filtering

Each file section in the diff is evaluated independently. A section is **dropped** if any of these conditions are true:

| Condition | Notes | Config |
|-----------|-------|--------|
| Path matches an ignore pattern | Checked against all patterns in `diff_ignore_patterns` + `diff_ignore_patterns_extra` | `diff_ignore_patterns` / `diff_ignore_patterns_extra` |
| Section contains only deletions, no additions | Whole-file deletions, removed dead code — rarely tweetable | hard-coded |
| First non-header line contains an auto-generated marker | Looks for `// auto-generated`, `# generated by`, `# do not edit`, `/* eslint-disable */` near the top of the section | hard-coded |
| Section is a doc file and the doc cap has been reached | Docs are `docs/`, `doc/`, `documentation/` directories, or `.md`/`.rst` files | `max_doc_diff_sections` |

Kept sections are reformatted: the `diff --git a/... b/...` header is replaced with a compact `# filename` line, and metadata lines (`---`, `+++`, `@@`) are removed. Only `+`, `-`, and context lines remain.

Doc sections that pass the cap check are further truncated to `max_doc_section_chars` characters, cut at a line boundary, with a `[...truncated]` marker appended.

**Default `diff_ignore_patterns` cover:**
- Dependency lock files (`*.lock`, `package-lock.json`, `poetry.lock`, `go.sum`, etc.)
- Minified and compiled assets (`*.min.js`, `*.min.css`, `*.d.ts`)
- Build output directories (`dist/**`, `build/**`)
- Test files (`test_*.py`, `*.test.ts`, `tests/**`, `**/__tests__/**`, etc.)
- Noisy tooling config (`.prettierrc`, `.eslintrc`, `.editorconfig`)
- CI and GitHub config (`.github/**`)
- Generated changelogs (`CHANGELOG.md`, `HISTORY.md`, `release-notes.md`, etc.)

To keep the defaults and add your own, use `diff_ignore_patterns_extra` rather than overriding `diff_ignore_patterns`.

### Context budget and priority

After filtering, all context is packed into the prompt within a character budget set by `context_max_chars`. Sections are included in strict priority order:

1. **Project fields** — always included in full; they are not subject to the budget cap.
2. **NOTES.md** — included next if present; the LLM is instructed to treat it as the highest-priority source.
3. **Commit messages** — filtered messages, concatenated.
4. **Filtered diff** — remainder of the budget after the above sections are placed.

If the budget runs out, lower-priority sections are truncated at a character boundary. Increasing `context_max_chars` gives the diff more room; decreasing it biases the prompt toward commit messages and notes.

## Environment variables

The selected provider must have its matching API key available in the environment or `.env` file:

- `provider: openai` -> `OPENAI_API_KEY`
- `provider: anthropic` -> `ANTHROPIC_API_KEY`
- `provider: gemini` -> `GEMINI_API_KEY` or `GOOGLE_API_KEY`
