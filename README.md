# diff2tweet

> Stop forgetting to tweet about your code wins.

`diff2tweet` feeds your recent git commits and diffs to an LLM and generates a tweet draft. Run it after you push, review the candidates, and move on.

---

## Install

```bash
pip install diff2tweet
```

For Anthropic or Gemini providers, install the extras you need:

```bash
pip install 'diff2tweet[anthropic]'   # Claude
pip install 'diff2tweet[gemini]'      # Gemini
pip install 'diff2tweet[all-providers]'  # everything
```

Verify the install:

```bash
diff2tweet --help
```

---

## Setup

**1. Add your API key**

Create a `.env` file in your repo root (or export the variable):

```
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=...
```

All three providers are supported. Based on testing with `gpt-5.1`, `claude-sonnet-4-6`, and `gemini-2.5-flash-lite-preview`, Claude produced the best output quality. OpenAI was solid. Gemini struggled with context grounding. Your mileage may vary by model.

**2. Add a config file**

Create `diff2tweet.yaml` in your repo root. Minimal config:

```yaml
provider: openai
model: gpt-4o

project_name: your-project
project_summary: One sentence about what your project does.
project_audience: Who you're building for.
project_stage: prototype  # prototype | beta | launched
project_tone: technical   # technical | founder | casual
```

A full annotated example is at [`diff2tweet.yaml`](https://github.com/bju12290/diff2tweet/blob/master/diff2tweet.yaml) in the repo.

---

## Run

From anywhere inside your git repo:

```bash
diff2tweet
```

The tool will:
1. Find your `diff2tweet.yaml` and `.env` at the repo root
2. Pull your recent committed changes since the last run
3. Generate tweet candidates
4. Save the result to `.diff2tweet/`

---

## Optional: Add context with NOTES.md

Drop a `NOTES.md` in your repo root to give the LLM extra context that wouldn't be visible in commits — what you're working toward, anything worth emphasizing, framing you want it to use. Gets included automatically.

---

## Config Reference

| Key | Default | Description |
|-----|---------|-------------|
| `provider` | `openai` | `openai`, `anthropic`, or `gemini` |
| `model` | — | Model name for the selected provider (required) |
| `project_name` | `""` | Project name for prompt context |
| `project_summary` | `""` | What the project does |
| `project_audience` | `""` | Who it's for |
| `project_stage` | `prototype` | `prototype`, `beta`, or `launched` |
| `project_tone` | `technical` | `technical`, `founder`, or `casual` |
| `project_key_terms` | `[]` | Domain vocabulary to inform framing |
| `num_candidates` | `1` | Number of tweet drafts to generate |
| `character_limit` | `280` | Max tweet length |
| `lookback_commits` | `5` | Commits to include on first run |
| `commit_subject_min_chars` | `20` | Min chars for a commit subject to be included |
| `readme_max_chars` | `0` | Max README.md chars to include as context |
| `forced_hashtags` | `[]` | Hashtags always included when they fit |
| `custom_instructions` | `""` | Extra guidance appended to the prompt |
| `context_max_chars` | `12000` | Max characters of context sent to the LLM |
| `max_doc_diff_sections` | `3` | Max documentation diff sections to include |
| `max_doc_section_chars` | `1000` | Max chars per individual doc diff section |
| `diff_ignore_patterns` | (list) | Glob patterns to exclude from diff context |
| `output_folder` | `.diff2tweet` | Where logs and drafts are saved |

---

## Output

Each run writes a markdown artifact to `.diff2tweet/runs/` with the tweet candidates. Runs are also logged to `.diff2tweet/run_log.jsonl` so subsequent runs only pick up new commits.

Add `.diff2tweet/` to your `.gitignore`, or commit it if you want a record of your tweet history.
