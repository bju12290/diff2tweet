from __future__ import annotations

from pathlib import Path

from .git import find_repo_root


def discover_notes(*, cwd: Path | None = None) -> str | None:
    """Return repo-root NOTES.md contents when present."""

    repo_root = find_repo_root(cwd)
    notes_path = repo_root / "NOTES.md"
    if not notes_path.exists():
        return None

    return notes_path.read_text(encoding="utf-8")
