from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath

from difftotweet.config import RuntimeConfig
from difftotweet.git import GitContext


_BASE_PROMPT = """You write punchy, specific developer tweets about shipped code changes.

Rules:
- Each tweet must stay within the configured character limit.
- Be concrete about what changed; do not invent outcomes not supported by the context.
- Avoid generic filler like 'improved stability' unless the context clearly supports it.
- Write like a real developer sharing a win, not a press release.
- Include forced hashtags only when they fit naturally.
- Do not use numbering, labels, or surrounding commentary.
"""


def build_prompt(
    config: RuntimeConfig,
    git_context: GitContext,
    notes_text: str | None,
    readme_text: str | None,
) -> str:
    """Assemble the final LLM prompt from repo context and config."""

    sections = [
        ("README", readme_text or ""),
        ("COMMIT MESSAGES", "\n".join(git_context.commit_messages)),
        ("NOTES", notes_text or ""),
        ("FILTERED DIFF", _filter_diff(git_context.diff_text, config.diff_ignore_patterns)),
    ]

    context_parts: list[str] = []
    remaining_chars = config.context_max_chars
    for title, content in sections:
        if remaining_chars <= 0:
            break
        section_text = _format_section(title, content, remaining_chars)
        if not section_text:
            continue
        context_parts.append(section_text)
        remaining_chars -= len(section_text)

    hashtags_text = ", ".join(config.forced_hashtags) if config.forced_hashtags else "none"
    prompt_parts = [
        _BASE_PROMPT.strip(),
        (
            f"Return exactly {config.num_candidates} tweet candidates as JSON with this shape\n"
            + '{"tweets": ["tweet 1", "tweet 2", "..."]}'
        ),
        f"Character limit: {config.character_limit}",
        f"Forced hashtags: {hashtags_text}",
        f"Commit range: {git_context.commit_range}",
    ]
    if config.custom_instructions:
        prompt_parts.append("Custom instructions:\n" + config.custom_instructions.strip())
    prompt_parts.append("Context:\n" + ("\n\n".join(context_parts) if context_parts else "(none)"))
    return "\n\n".join(prompt_parts)


def _format_section(title: str, content: str, remaining_chars: int) -> str:
    content = content.strip()
    if not content:
        return ""

    header = f"## {title}\n"
    if remaining_chars <= len(header):
        return ""

    available = remaining_chars - len(header)
    trimmed_content = content[:available].rstrip()
    if not trimmed_content:
        return ""

    return header + trimmed_content


def _filter_diff(diff_text: str, ignore_patterns: list[str]) -> str:
    if not diff_text.strip():
        return ""

    kept_sections: list[str] = []
    current_section: list[str] = []
    current_path: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            _append_diff_section(kept_sections, current_section, current_path, ignore_patterns)
            current_section = [line]
            current_path = _extract_diff_path(line)
            continue
        current_section.append(line)

    _append_diff_section(kept_sections, current_section, current_path, ignore_patterns)
    return "\n".join(kept_sections).strip()


def _append_diff_section(
    kept_sections: list[str],
    section_lines: list[str],
    path: str | None,
    ignore_patterns: list[str],
) -> None:
    if not section_lines:
        return
    if path and _matches_ignore_pattern(path, ignore_patterns):
        return
    kept_sections.append("\n".join(section_lines))


def _extract_diff_path(diff_header: str) -> str | None:
    parts = diff_header.split()
    if len(parts) < 4:
        return None

    for candidate in reversed(parts[-2:]):
        if candidate.startswith("b/"):
            return candidate[2:]
        if candidate.startswith("a/"):
            return candidate[2:]
    return None


def _matches_ignore_pattern(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    for pattern in patterns:
        if pure_path.match(pattern) or fnmatch.fnmatch(normalized, pattern):
            return True
    return False
