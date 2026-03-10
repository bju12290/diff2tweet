#!/usr/bin/env python3
"""
dev_tools/run_eval.py

LLM output quality evaluator for diff2tweet.

For each repo in repos.yaml:
  1. Discovers git context (same as production)
  2. Generates tweet candidates using the configured provider/model
  3. Sends candidates + original context to a critic LLM (gpt-5.1) scored
     against a rubric

Outputs:
  dev_tools/last_eval.md   — human-readable scored report
  dev_tools/last_eval.json — structured results for programmatic comparison

Usage:
    python dev_tools/run_eval.py

Requires OPENAI_API_KEY in .env (same as production runs).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pydantic import SecretStr

from difftotweet.config.config_schema import DiffToTweetConfig
from difftotweet.config.load_config import RuntimeConfig, load_config
from difftotweet.git import GitDiscoveryError, discover_git_context
from difftotweet.notes import discover_notes
from difftotweet.prompt import build_prompt_with_diagnostics
from difftotweet.providers import get_provider

REPOS_FILE = Path(__file__).parent / "repos.yaml"
SCRATCH_DIR = Path(__file__).parent / "scratch"
REPORT_FILE = Path(__file__).parent / "last_eval.md"
JSON_FILE = Path(__file__).parent / "last_eval.json"
BASE_CONFIG_FILE = REPO_ROOT / "diff2tweet.yaml"

CRITIC_MODEL = "gpt-5.1"

RUBRIC_CRITERIA: list[tuple[str, str]] = [
    ("tweetability", "Is this change actually interesting enough to tweet? A pre-commit config tweak, CI action bump, lock file update, or documentation-only fix — even described precisely — is rarely tweetable. Score 1–4 if the underlying change wouldn't engage the target audience regardless of how well it's written. A tweet that cannot be understood while scrolling (due to density or jargon) cannot score above 5 for tweetability — illegible tweets are not tweetable."),
    ("specificity", "Names the actual thing built/changed — a feature, capability, behavior, or user-facing outcome — not vague phrases like 'made improvements'. Listing file paths, exact strings changed, or version numbers is NOT specificity. Score 1–4 if the tweet only describes what files were touched rather than what the user can now do or what problem is solved."),
    ("accuracy", "Only references things present in the source commits and diff — no hallucination or invented details. If a claim cannot be confirmed from the provided source material but is not demonstrably false, note it in feedback but do not penalize the score — reserve low scores (1–3) for claims that are clearly fabricated or contradict the diff."),
    ("punchiness", "No filler words, no corporate speak, direct and concise — earns every word"),
    ("authenticity", "Has a human voice — an opinion, reaction, or framing that a person chose. Score 1–3 if it reads like a commit message, CHANGELOG entry, or bug report reformatted to 280 chars with no human framing added. Score 7+ only if it sounds like something a developer would genuinely write — not just a diff summary with line breaks removed."),
    ("hook_quality", "The opening line/sentence makes you want to read it — leads with something interesting enough to stop scrolling"),
    ("standalone_clarity", "Could someone who doesn't maintain this project understand what changed and why it matters? Score low if the tweet only makes sense to the committer — jargon without payoff, file paths without context, or version numbers with no explanation of impact."),
    ("readability", "Is the tweet actually legible while scrolling? Hard cap: score 1–3 if the reader must mentally parse raw syntax to understand the point — this includes regex patterns with escape sequences (\\b, \\d, (?:...) etc.), stacked escaped characters, multiple file paths, or version numbers with no plain-language gloss. Score 4 only if such syntax appears but is clearly subordinate to a plain-language explanation. A tweet about an interesting change still fails this criterion if a reader cannot grasp the point in one pass without the source open."),
    ("audience_fit", "Resonates with the target audience described in the project config"),
    ("tone_match", "Matches the configured project tone (technical / founder / casual)"),
]

CRITERIA_KEYS = [k for k, _ in RUBRIC_CRITERIA]

# Weights for computing overall score. Gate criteria are weighted higher so a
# low tweetability or authenticity can't be rescued by high secondary scores.
CRITERIA_WEIGHTS: dict[str, float] = {
    "tweetability":      2.0,
    "authenticity":      1.0,
    "accuracy":          1.0,
    "readability":       1.5,
    "specificity":       1.0,
    "hook_quality":      1.0,
    "punchiness":        1.0,
    "standalone_clarity": 1.0,
    "audience_fit":      0.75,
    "tone_match":        0.75,
}
_WEIGHT_TOTAL = sum(CRITERIA_WEIGHTS.values())


def compute_overall(scores: dict[str, int | float]) -> float:
    """Weighted average of per-criterion scores. Deterministic — not LLM-generated."""
    weighted_sum = sum(scores.get(k, 0) * CRITERIA_WEIGHTS.get(k, 1.0) for k in CRITERIA_KEYS)
    return round(weighted_sum / _WEIGHT_TOTAL, 2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    repos_config = _load_repos_config()
    repos = repos_config.get("repos", [])
    if not repos:
        print("No repos defined in repos.yaml.")
        sys.exit(1)

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    base_runtime_config = load_config(BASE_CONFIG_FILE)
    base_yaml_config = _load_base_yaml_config()

    openai_api_key = base_runtime_config.openai_api_key
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY is required for eval runs.")
        sys.exit(1)

    print(f"Running eval against {len(repos)} repos (generator: {base_runtime_config.model}, critic: {CRITIC_MODEL})...")

    results: list[dict[str, Any]] = []
    for i, repo_entry in enumerate(repos, 1):
        url: str = repo_entry["url"]
        name: str = repo_entry.get("name") or _repo_name_from_url(url)
        config_overrides: dict[str, Any] = repo_entry.get("config") or {}

        print(f"  [{i}/{len(repos)}] {name} ...", end=" ", flush=True)

        try:
            repo_path = _ensure_repo(url, name)
            config = _build_eval_config(base_yaml_config, config_overrides, openai_api_key)
            git_context = discover_git_context(config, cwd=repo_path)
            notes_text = _discover_notes_safe(repo_path)
            prompt, diagnostics = build_prompt_with_diagnostics(config, git_context, notes_text)

            if diagnostics.budget.commit_chars == 0 and diagnostics.budget.diff_chars == 0:
                print("skipped (no context)")
                results.append({
                    "name": name,
                    "url": url,
                    "config_overrides": config_overrides,
                    "commit_range": git_context.commit_range,
                    "candidates": None,
                    "critique": None,
                    "error": None,
                    "no_context": True,
                })
                continue

            provider = get_provider(config)
            candidates = provider.generate_tweets(prompt, config)
            print("generated ...", end=" ", flush=True)

            critique = _critique_candidates(
                candidates=candidates,
                context_excerpt=_context_excerpt(git_context),
                config=config,
                api_key=openai_api_key.get_secret_value(),
            )
            print("critiqued")

            results.append({
                "name": name,
                "url": url,
                "config_overrides": config_overrides,
                "commit_range": git_context.commit_range,
                "candidates": candidates,
                "critique": critique,
                "error": None,
                "no_context": False,
            })

        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({
                "name": name,
                "url": url,
                "config_overrides": config_overrides,
                "commit_range": None,
                "candidates": None,
                "critique": None,
                "error": str(exc),
                "no_context": False,
            })

    timestamp = datetime.now().isoformat(timespec="seconds")
    git_sha = _current_git_sha()

    report = _build_report(results, timestamp, git_sha, base_runtime_config.model)
    REPORT_FILE.write_text(report, encoding="utf-8")

    json_output = {
        "timestamp": timestamp,
        "git_sha": git_sha,
        "generator_model": base_runtime_config.model,
        "critic_model": CRITIC_MODEL,
        "aggregate": _compute_aggregate(results),
        "repos": results,
    }
    JSON_FILE.write_text(json.dumps(json_output, indent=2, ensure_ascii=False), encoding="utf-8")

    evaluated_count = sum(1 for r in results if r["error"] is None and not r.get("no_context"))
    skipped_count = sum(1 for r in results if r.get("no_context"))
    error_count = sum(1 for r in results if r["error"] is not None)
    print(f"\nReport: {REPORT_FILE.relative_to(REPO_ROOT)}")
    print(f"JSON:   {JSON_FILE.relative_to(REPO_ROOT)}")
    print(f"Repos: {evaluated_count} evaluated, {skipped_count} skipped (no context), {error_count} error(s)")

    agg = json_output["aggregate"]
    if agg:
        print(f"\nOverall average: {agg['overall_avg']:.2f} / 10")
        for key in CRITERIA_KEYS:
            print(f"  {key}: {agg['criteria_avgs'][key]:.2f}")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_repos_config() -> dict[str, Any]:
    if not REPOS_FILE.exists():
        raise FileNotFoundError(f"repos.yaml not found at {REPOS_FILE}")
    with REPOS_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_base_yaml_config() -> DiffToTweetConfig:
    with BASE_CONFIG_FILE.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return DiffToTweetConfig.model_validate(raw)


def _repo_name_from_url(url: str) -> str:
    parts = url.rstrip("/").removesuffix(".git").split("/")
    return f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else parts[-1]


def _build_eval_config(
    base: DiffToTweetConfig,
    overrides: dict[str, Any],
    openai_api_key: SecretStr,
) -> RuntimeConfig:
    merged = base.model_dump()
    known_fields = set(DiffToTweetConfig.model_fields.keys())
    for key, value in overrides.items():
        if key in known_fields:
            merged[key] = value

    extra_patterns = merged.pop("diff_ignore_patterns_extra", [])
    if extra_patterns:
        merged["diff_ignore_patterns"] = merged["diff_ignore_patterns"] + extra_patterns

    # Clear project-specific identity fields so the generator doesn't contaminate
    # tweets about foreign repos with diff2tweet's own name and description.
    merged["project_name"] = ""
    merged["project_summary"] = ""

    return RuntimeConfig.model_construct(
        **merged,
        provider_api_key=openai_api_key,
        openai_api_key=openai_api_key,
        anthropic_api_key=None,
        gemini_api_key=None,
    )


# ---------------------------------------------------------------------------
# Repo management (shared with run_batch.py)
# ---------------------------------------------------------------------------


def _ensure_repo(url: str, name: str) -> Path:
    dir_name = name.replace("/", "_")
    repo_path = SCRATCH_DIR / dir_name

    if (repo_path / ".git").exists():
        subprocess.run(
            ["git", "-C", str(repo_path), "pull", "--quiet", "--ff-only"],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth=50", url, str(repo_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    return repo_path


def _discover_notes_safe(repo_path: Path) -> str | None:
    try:
        return discover_notes(cwd=repo_path)
    except Exception:
        return None


def _context_excerpt(git_context: Any) -> str:
    """Compact context summary passed to the critic so it can score accuracy/specificity."""
    parts: list[str] = []
    if git_context.commit_messages:
        parts.append("## Commits\n" + "\n".join(f"- {m.splitlines()[0]}" for m in git_context.commit_messages))
    if git_context.diff_text:
        # First 3000 chars of the raw diff — enough for the critic to verify claims
        excerpt = git_context.diff_text[:3000]
        if len(git_context.diff_text) > 3000:
            excerpt += "\n[...truncated]"
        parts.append("## Diff (excerpt)\n" + excerpt)
    return "\n\n".join(parts)


def _current_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------


def _build_critic_prompt(
    candidates: list[str],
    context_excerpt: str,
    config: RuntimeConfig,
) -> str:
    rubric_lines = "\n".join(
        f"- **{key}** (1-10): {desc}" for key, desc in RUBRIC_CRITERIA
    )
    candidates_block = "\n\n".join(
        f"Candidate {i}:\n{text}" for i, text in enumerate(candidates, 1)
    )
    criteria_json_keys = ", ".join(f'"{k}"' for k in CRITERIA_KEYS)

    project_lines: list[str] = []
    if config.project_name:
        project_lines.append(f"Name: {config.project_name}")
    if config.project_summary:
        project_lines.append(f"Summary: {config.project_summary.strip()}")
    if config.project_audience:
        project_lines.append(f"Target audience: {config.project_audience}")
    project_lines.append(f"Stage: {config.project_stage}")
    project_lines.append(f"Tone: {config.project_tone}")
    project_block = "\n".join(project_lines)

    return f"""You are an expert content marketer specializing in developer-focused social media. Your job is to score tweet candidates that were generated from a software project's recent commits.

## Project Context
{project_block}

## Source Material
The tweets below were generated from these commits and diff:

{context_excerpt}

## Tweet Candidates
{candidates_block}

## Scoring Rubric
Score each candidate 1–10 on each criterion:
{rubric_lines}

## Scoring Calibration
Use the full 1–10 range. Do not cluster scores in the 7–9 band.
- **1–3**: Poor — fails this criterion clearly
- **4–5**: Adequate / average — meets the bar but not well
- **6–7**: Good — noticeably above average
- **8–9**: Excellent — genuinely strong, reserve for standout examples
- **10**: Near-perfect — rare, do not award casually

## Instructions
- Score strictly and independently — do not let one criterion inflate others.
- **tweetability** is the primary gate — if the underlying change isn't worth tweeting, no amount of good writing fixes it. Score it first. Additionally: if **readability** ≤ 3, tweetability may not exceed 5 — a tweet you cannot parse while scrolling is not tweetable regardless of topic.
- **authenticity** is the secondary gate — a technically accurate summary of a diff is not a tweet. Score 1–3 for anything that reads like a commit message or CHANGELOG entry with no human framing.
- **readability** is an independent gate with a hard cap rule: if the tweet body requires the reader to mentally parse raw regex syntax, stacked escape sequences, or multiple file paths to understand the point, the score must be 1–3. Score 4 only when such syntax is present but clearly secondary to a plain-language explanation. Do not award 5+ because the tweet "can be parsed with effort" — score what a casual scroll would experience.
- **specificity** requires naming a user-facing feature, capability, or outcome — not file paths or changed strings. High scores (7+) require that the tweet names something a user of the project can understand and care about.
- **accuracy** must be grounded in the source material above. Score 1–3 only for claims that are clearly fabricated or contradict the diff. If a claim cannot be confirmed from the provided excerpt but is not demonstrably false, flag it in feedback and hold the score at 5–6 — do not treat "I can't verify this from the excerpt" the same as hallucination.
- **feedback** must be one concrete, actionable sentence identifying the single most important improvement for that candidate.
- Do NOT include an overall score — that is computed separately.

Return a JSON object with this exact schema:
{{
  "candidates": [
    {{
      "text": "<the candidate tweet text>",
      "scores": {{{criteria_json_keys}}},
      "feedback": "<one sentence>"
    }}
  ]
}}

Return {len(candidates)} candidate objects in the same order as the input."""


def _critique_candidates(
    candidates: list[str],
    context_excerpt: str,
    config: RuntimeConfig,
    api_key: str,
) -> list[dict[str, Any]]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package required for eval runs") from exc

    client = OpenAI(api_key=api_key)
    critic_prompt = _build_critic_prompt(candidates, context_excerpt, config)

    response = client.chat.completions.create(
        model=CRITIC_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a rigorous content quality evaluator. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": critic_prompt,
            },
        ],
    )

    content = response.choices[0].message.content
    payload = json.loads(content)
    critique_list = payload.get("candidates", [])

    if len(critique_list) != len(candidates):
        raise RuntimeError(
            f"Critic returned {len(critique_list)} results for {len(candidates)} candidates"
        )

    # Enforce tweetability cap: readability <= 3 means tweetability may not exceed 5.
    # Applied before overall computation so the cap flows through to the weighted score.
    for item in critique_list:
        scores = item.get("scores", {})
        if scores.get("readability", 10) <= 3 and scores.get("tweetability", 0) > 5:
            scores["tweetability"] = 5

    # Compute overall deterministically from weighted criteria — not LLM-generated.
    for item in critique_list:
        item["overall"] = compute_overall(item.get("scores", {}))

    return critique_list


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _compute_aggregate(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    all_critiques: list[dict[str, Any]] = []
    for r in results:
        if r["critique"] and not r.get("no_context"):
            all_critiques.extend(r["critique"])

    if not all_critiques:
        return None

    criteria_avgs = {}
    for key in CRITERIA_KEYS:
        scores = [c["scores"][key] for c in all_critiques if key in c.get("scores", {})]
        criteria_avgs[key] = round(sum(scores) / len(scores), 2) if scores else 0.0

    # overall_avg is the weighted average of per-criterion averages, matching compute_overall.
    overall_avg = compute_overall({k: criteria_avgs[k] for k in CRITERIA_KEYS})

    return {
        "overall_avg": overall_avg,
        "criteria_avgs": criteria_avgs,
        "candidate_count": len(all_critiques),
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _build_report(
    results: list[dict[str, Any]],
    timestamp: str,
    git_sha: str,
    generator_model: str,
) -> str:
    success_count = sum(1 for r in results if r["error"] is None and not r.get("no_context"))
    skipped_count = sum(1 for r in results if r.get("no_context"))
    error_count = sum(1 for r in results if r["error"] is not None)

    lines: list[str] = [
        "# diff2tweet Eval Run",
        "",
        f"**Generated:** {timestamp}  ",
        f"**diff2tweet SHA:** `{git_sha}`  ",
        f"**Generator model:** `{generator_model}`  ",
        f"**Critic model:** `{CRITIC_MODEL}`  ",
        f"**Repos tested:** {len(results)} | **Evaluated:** {success_count} | **Skipped (no context):** {skipped_count} | **Errors:** {error_count}",
        "",
    ]

    # Aggregate summary table
    all_critiques: list[dict[str, Any]] = []
    for r in results:
        if r["critique"] and not r.get("no_context"):
            all_critiques.extend(r["critique"])

    if all_critiques:
        lines += ["## Aggregate Scores", ""]
        lines.append("| Criterion | Avg (1–10) |")
        lines.append("|-----------|-----------|")
        criteria_avgs: dict[str, float] = {}
        for key in CRITERIA_KEYS:
            scores = [c["scores"][key] for c in all_critiques if key in c.get("scores", {})]
            criteria_avgs[key] = round(sum(scores) / len(scores), 2) if scores else 0.0
            lines.append(f"| {key} | {criteria_avgs[key]} |")

        overall_avg = compute_overall(criteria_avgs)
        lines += [
            f"| **overall (weighted)** | **{overall_avg}** |",
            "",
            f"*Based on {len(all_critiques)} candidates across {success_count} repos.*  ",
            f"*Overall is a weighted average — tweetability ×2, readability ×1.5, others ×1 or less.*",
            "",
        ]

    lines += ["---", ""]

    for i, result in enumerate(results, 1):
        lines += _format_repo_section(i, result)

    return "\n".join(lines)


def _format_repo_section(index: int, result: dict[str, Any]) -> list[str]:
    name: str = result["name"]
    url: str = result["url"]
    error: str | None = result["error"]

    lines: list[str] = [
        f"## {index}. {name}",
        "",
        f"**URL:** {url}  ",
    ]

    if result.get("no_context"):
        lines += [
            f"**Commit range:** `{result.get('commit_range', 'N/A')}`  ",
            "",
            "> **SKIPPED:** All commits and diff sections were filtered — no content to generate from.",
            "",
            "---",
            "",
        ]
        return lines

    if error:
        lines += [f"**Commit range:** N/A  ", "", f"> **ERROR:** {error}", "", "---", ""]
        return lines

    lines.append(f"**Commit range:** `{result['commit_range']}`")
    lines.append("")

    critique: list[dict[str, Any]] = result["critique"]
    for j, item in enumerate(critique, 1):
        text: str = item.get("text", "")
        scores: dict[str, Any] = item.get("scores", {})
        overall: float = item.get("overall", 0)
        feedback: str = item.get("feedback", "")

        lines += [
            f"### Candidate {j} — overall: {overall:.2f} (weighted)",
            "",
            f"> {text}",
            "",
        ]

        lines.append("| Criterion | Score |")
        lines.append("|-----------|-------|")
        for key in CRITERIA_KEYS:
            lines.append(f"| {key} | {scores.get(key, '—')} |")
        lines.append("")

        if feedback:
            lines.append(f"**Critic:** {feedback}")
            lines.append("")

    lines += ["---", ""]
    return lines


if __name__ == "__main__":
    main()
