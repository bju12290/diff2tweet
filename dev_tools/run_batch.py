#!/usr/bin/env python3
"""
dev_tools/run_batch.py

Batch prompt-filter test harness for diff2tweet.

Clones (or fast-forward-pulls) every repo listed in repos.yaml into
dev_tools/scratch/, runs prompt assembly + filter diagnostics against each
using the root diff2tweet.yaml as the base config, and writes a detailed
report to dev_tools/last_run.md.

No LLM calls are made — this is pure prompt-assembly and filter inspection.

Usage:
    python dev_tools/run_batch.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Make src/diff2tweet importable without installing the package
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pydantic import SecretStr

from diff2tweet.config.config_schema import DiffToTweetConfig
from diff2tweet.config.load_config import RuntimeConfig
from diff2tweet.git import GitDiscoveryError, discover_git_context
from diff2tweet.notes import discover_notes
from diff2tweet.prompt import FilterDiagnostics, build_prompt_with_diagnostics

REPOS_FILE = Path(__file__).parent / "repos.yaml"
SCRATCH_DIR = Path(__file__).parent / "scratch"
REPORT_FILE = Path(__file__).parent / "last_run.md"
BASE_CONFIG_FILE = REPO_ROOT / "diff2tweet.yaml"


def main() -> None:
    repos_config = _load_repos_config()
    repos = repos_config.get("repos", [])

    if not repos:
        print("No repos defined in repos.yaml.")
        sys.exit(1)

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    base_yaml_config = _load_base_yaml_config()

    print(f"Running batch against {len(repos)} repos...")

    results: list[dict[str, Any]] = []
    for i, repo_entry in enumerate(repos, 1):
        url: str = repo_entry["url"]
        name: str = repo_entry.get("name") or _repo_name_from_url(url)
        config_overrides: dict[str, Any] = repo_entry.get("config") or {}

        print(f"  [{i}/{len(repos)}] {name} ...", end=" ", flush=True)

        try:
            repo_path = _ensure_repo(url, name)
            config = _build_batch_config(base_yaml_config, config_overrides)
            git_context = discover_git_context(config, cwd=repo_path)
            notes_text = _discover_notes_safe(repo_path)
            prompt, diagnostics = build_prompt_with_diagnostics(config, git_context, notes_text)

            results.append(
                {
                    "name": name,
                    "url": url,
                    "config_overrides": config_overrides,
                    "commit_range": git_context.commit_range,
                    "prompt": prompt,
                    "diagnostics": diagnostics,
                    "error": None,
                }
            )
            print("OK")

        except Exception as exc:
            results.append(
                {
                    "name": name,
                    "url": url,
                    "config_overrides": config_overrides,
                    "commit_range": None,
                    "prompt": None,
                    "diagnostics": None,
                    "error": str(exc),
                }
            )
            print(f"ERROR: {exc}")

    report = _build_report(results)
    REPORT_FILE.write_text(report, encoding="utf-8")

    success_count = sum(1 for r in results if r["error"] is None)
    error_count = len(results) - success_count
    print(f"\nReport written to: {REPORT_FILE.relative_to(REPO_ROOT)}")
    print(f"Repos: {success_count} OK, {error_count} error(s)")


# ---------------------------------------------------------------------------
# Config & repo management
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


def _ensure_repo(url: str, name: str) -> Path:
    """Clone the repo if absent, otherwise fast-forward-pull."""
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


def _build_batch_config(
    base: DiffToTweetConfig,
    overrides: dict[str, Any],
) -> RuntimeConfig:
    """
    Merge base config with per-repo overrides and construct a RuntimeConfig.

    Provider key validation is bypassed — we never call the LLM in batch mode.
    """
    merged = base.model_dump()
    known_fields = set(DiffToTweetConfig.model_fields.keys())
    for key, value in overrides.items():
        if key in known_fields:
            merged[key] = value

    extra_patterns = merged.pop("diff_ignore_patterns_extra", [])
    if extra_patterns:
        merged["diff_ignore_patterns"] = merged["diff_ignore_patterns"] + extra_patterns

    # model_construct skips @model_validator so no API key is required
    return RuntimeConfig.model_construct(
        **merged,
        provider_api_key=None,
        openai_api_key=SecretStr("batch-mode-no-llm-call"),
        anthropic_api_key=None,
        gemini_api_key=None,
    )


def _discover_notes_safe(repo_path: Path) -> str | None:
    try:
        return discover_notes(cwd=repo_path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _build_report(results: list[dict[str, Any]]) -> str:
    timestamp = datetime.now().isoformat(timespec="seconds")
    success_count = sum(1 for r in results if r["error"] is None)
    error_count = len(results) - success_count

    lines: list[str] = [
        "# diff2tweet Batch Filter Run",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Base config:** `diff2tweet.yaml`  ",
        f"**Repos tested:** {len(results)} | **OK:** {success_count} | **Errors:** {error_count}",
        "",
        "---",
        "",
    ]

    for i, result in enumerate(results, 1):
        lines += _format_repo_section(i, result)

    return "\n".join(lines)


def _format_repo_section(index: int, result: dict[str, Any]) -> list[str]:
    name: str = result["name"]
    url: str = result["url"]
    overrides: dict[str, Any] = result["config_overrides"]
    error: str | None = result["error"]

    lines: list[str] = [
        f"## {index}. {name}",
        "",
        f"**URL:** {url}  ",
    ]

    if overrides:
        override_str = ", ".join(f"`{k}: {v}`" for k, v in overrides.items())
        lines.append(f"**Config overrides:** {override_str}  ")
    else:
        lines.append("**Config overrides:** none  ")

    if error:
        lines += ["", f"> **ERROR:** {error}", "", "---", ""]
        return lines

    commit_range: str = result["commit_range"]
    diagnostics: FilterDiagnostics = result["diagnostics"]
    prompt: str = result["prompt"]

    lines.append(f"**Commit range:** `{commit_range}`")
    lines.append("")

    # Commits
    kept_commits = [r for r in diagnostics.commit_results if r.kept]
    filtered_commits = [r for r in diagnostics.commit_results if not r.kept]
    lines.append(f"### Commits ({len(kept_commits)} kept, {len(filtered_commits)} filtered)")
    lines.append("")
    lines.append("| | Subject | Reason |")
    lines.append("|---|---------|--------|")
    for cr in diagnostics.commit_results:
        icon = "✓" if cr.kept else "✗"
        reason = cr.reason or "—"
        subject = (cr.subject[:77] + "…") if len(cr.subject) > 80 else cr.subject
        lines.append(f"| {icon} | {subject} | {reason} |")
    lines.append("")

    # Diff sections
    kept_diff = [r for r in diagnostics.diff_section_results if r.kept]
    filtered_diff_sections = [r for r in diagnostics.diff_section_results if not r.kept]
    lines.append(
        f"### Diff Sections ({len(kept_diff)} kept, {len(filtered_diff_sections)} filtered)"
    )
    lines.append("")
    lines.append("| | File | Reason |")
    lines.append("|---|------|--------|")
    for dr in diagnostics.diff_section_results:
        icon = "✓" if dr.kept else "✗"
        reason = dr.reason or "—"
        lines.append(f"| {icon} | {dr.path} | {reason} |")
    lines.append("")

    # Budget
    b = diagnostics.budget
    pct = int(b.total_used / b.max_chars * 100) if b.max_chars else 0
    lines.append(f"### Context Budget ({b.total_used:,} / {b.max_chars:,} chars — {pct}%)")
    lines.append("")
    lines.append("| Section | Chars |")
    lines.append("|---------|-------|")
    lines.append(f"| Project fields | {b.project_chars:,} |")
    notes_display = f"{b.notes_chars:,}" if b.notes_chars else "absent"
    lines.append(f"| NOTES | {notes_display} |")
    lines.append(f"| Commit messages | {b.commit_chars:,} |")
    lines.append(f"| Diff | {b.diff_chars:,} |")
    lines.append("")

    # Assembled prompt (collapsible)
    lines.append("### Assembled Prompt")
    lines.append("")
    lines.append("<details>")
    lines.append("<summary>Expand</summary>")
    lines.append("")
    lines.append("```")
    lines.append(prompt)
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")

    return lines


if __name__ == "__main__":
    main()
