from __future__ import annotations

from pathlib import Path

from difftotweet.config import RuntimeConfig

from .git import find_repo_root


def discover_readme(
    config: RuntimeConfig,
    *,
    cwd: Path | None = None,
) -> str | None:
    """Return repo-root README.md contents truncated to the configured limit."""

    if config.readme_max_chars == 0:
        return None

    repo_root = find_repo_root(cwd)
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return None

    readme_text = readme_path.read_text(encoding="utf-8")
    return readme_text[: config.readme_max_chars]