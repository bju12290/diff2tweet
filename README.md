# diff2tweet

> Stop forgetting to tweet about your code wins.

`diff2tweet` feeds your recent git commits and diffs to an LLM and generates a tweet draft. Run it after you push, approve or skip the candidate, and move on.

---

## Install

Requires Python 3.11+.

```bash
pip install difftotweet
```

Or install from source:

```bash
git clone https://github.com/yourusername/difftotweet.git
cd difftotweet
pip install -e .
```

---

## Setup

**1. Add your OpenAI API key**

Create a `.env` file in your repo root (or export the variable):

```
OPENAI_API_KEY=sk-...
```

**2. Add a config file**

Create `diff2tweet.yaml` in your repo root. Minimal config:

```yaml
model: gpt-5.1

project_name: your-project
project_summary: One sentence about what your project does.
project_audience: Who you're building for.
project_stage: prototype  # prototype | beta | launched
project_tone: technical   # technical | founder | casual
```

A full annotated example is at [`diff2tweet.yaml`](./diff2tweet.yaml) in this repo.

---

## Run

From anywhere inside your git repo:

```bash
diff2tweet
```

The tool will:
1. Find your `diff2tweet.yaml` and `.env` at the repo root
2. Pull your recent committed changes
3. Generate a tweet candidate
4. Ask you to approve (`y`) or skip (`n`)
5. Save the result to `.diff2tweet/`

---

## Optional: Add context with NOTES.md

Drop a `NOTES.md` in your repo root to give the LLM extra context that wouldn't be visible in commits — what you're working toward, anything worth emphasizing, framing you want it to use. Gets included automatically.

---

## Config Reference

| Key | Default | Description |
|-----|---------|-------------|
| `model` | — | OpenAI model name (required) |
| `project_name` | `""` | Project name for prompt context |
| `project_summary` | `""` | What the project does |
| `project_audience` | `""` | Who it's for |
| `project_stage` | `prototype` | `prototype`, `beta`, or `launched` |
| `project_tone` | `technical` | `technical`, `founder`, or `casual` |
| `project_key_terms` | `[]` | Domain vocabulary to inform framing |
| `num_candidates` | `1` | Number of tweet drafts to generate |
| `character_limit` | `280` | Max tweet length |
| `lookback_commits` | `5` | Commits to include on first run |
| `forced_hashtags` | `[]` | Hashtags always included when they fit |
| `custom_instructions` | `""` | Extra guidance appended to the prompt |
| `context_max_chars` | `12000` | Max characters of context sent to the LLM |
| `output_folder` | `.diff2tweet` | Where logs and drafts are saved |

---

## Output

Each run writes a markdown artifact to `.diff2tweet/runs/` with the tweet candidates and your approval decisions. Runs are also logged to `.diff2tweet/run_log.jsonl` so subsequent runs only pick up new commits.

Add `.diff2tweet/` to your `.gitignore`, or commit it if you want a record of your tweet history.
