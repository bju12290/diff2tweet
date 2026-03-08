# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`difftotweet` (CLI name: `diff2tweet`) is a Python CLI tool that feeds git commits, diffs, and an optional `NOTES.md` context file to an LLM and outputs candidate tweets. Tagline: *"Stop forgetting to tweet about your code wins."*

## Build & Commands

No build system exists yet. When implementing:
- Language: Python
- CLI entrypoint: `diff2tweet` (no arguments; auto-discovers git diff and optional `NOTES.md` from repo root)
- Config: YAML file (`diff2tweet.yaml`) with a validator
- Default LLM provider: OpenAI (API key via `.env`, never in `diff2tweet.yaml`)

## Architecture

### Planned Data Flow
```
Git commits/diffs + optional NOTES.md → LLM prompt → Tweet candidates → Approval workflow → Log
```

### Milestones
1. **Milestone 1 (MVP):** CLI tool with OpenAI, simple y/n approval, outputs draft tweets to MD + log file
2. **Milestone 2:** Local LLMs (Ollama/LMStudio), Claude + Gemini support, git hook integration
3. **GitHub Launch:** Target `diff2tweet` repo name, 500+ stars goal
4. **Milestone 3:** GitHub Actions — drop YAML into repo, every merge to main produces tweet candidate in Slack/Discord
5. **Milestone 4:** Approve/deny via Slack/Discord UI (emoji reactions)
6. **Milestone 5:** Optional auto-post to X after approval

### Config Options (YAML)
- `model` — LLM model name
- `custom_instructions` — custom prompt injections
- `forced_hashtags` — always-included hashtags
- `character_limit` — defaults to Twitter limits; user-configurable
- `output_folder` — where run artifacts live

### Key Design Notes
- `NOTES.md` is a dedicated context file (not a general notes file) for users to feed optional context to the LLM that wouldn't be visible in commits/diffs
- Biggest challenge: prompting the LLM to produce punchy, specific tweets rather than generic ones like "Pushed a commit that optimizes stability!"
- Log files track all tweets with approval status, creation time, approval/denial time
- Provide a CLI command to clean run artifacts (with y/n confirmation) to avoid bloating user repos

## Agent System (`agents/` directory)

The `agents/` directory contains documentation for AI agent workflows on this project:
- `agents/README.md` — Start here; read order: root `AGENTS.md` → `SESSION_STATE.md` → `ARCHITECTURE.md` → `DECISIONS.md`
- `agents/SESSION_STATE.md` — Tracks current project state (update at the end of each session)
- `agents/ARCHITECTURE.md` — Key system design and file map (populate as code is written)
- `agents/DECISIONS.md` — Important historical decisions (log decisions here as they are made)

Root `AGENTS.md` contains behavior/workflow rules for AI agents on this project.

When starting a new session, read `agents/SESSION_STATE.md` to understand where the project left off.
