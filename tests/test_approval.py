from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from diff2tweet.artifacts import write_markdown
from diff2tweet.logs import write_approval_entry


_TEST_TEMP_ROOT = Path("tests") / ".tmp"


def test_write_approval_entry_appends_jsonl_record():
    case_dir = _TEST_TEMP_ROOT / f"approval-log-{uuid.uuid4().hex}"
    output_dir = case_dir / ".diff2tweet"
    output_dir.mkdir(parents=True, exist_ok=False)

    try:
        run_log_path = write_approval_entry(
            output_dir,
            "2026-03-08T12:00:00+00:00",
            {1: True, 2: False, 3: True},
            "2026-03-08T12:05:00+00:00",
        )
        payload = json.loads(run_log_path.read_text(encoding="utf-8").splitlines()[-1])

        assert payload == {
            "type": "approval",
            "generation_timestamp": "2026-03-08T12:00:00+00:00",
            "approvals": {"1": True, "2": False, "3": True},
            "approval_timestamp": "2026-03-08T12:05:00+00:00",
        }
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_write_markdown_writes_review_artifact_with_approvals():
    case_dir = _TEST_TEMP_ROOT / f"approval-md-{uuid.uuid4().hex}"
    output_dir = case_dir / ".diff2tweet"

    try:
        artifact_path = write_markdown(
            output_dir,
            "2026-03-08T12:00:00+00:00",
            "abc123..HEAD",
            ["one", "two", "three"],
            {1: True, 2: False, 3: True},
            "2026-03-08T12:05:00+00:00",
        )
        contents = artifact_path.read_text(encoding="utf-8")

        assert artifact_path == output_dir / "runs" / "2026-03-08T12-00-00+00-00.md"
        assert "- Generation timestamp: 2026-03-08T12:00:00+00:00" in contents
        assert "- Approval timestamp: 2026-03-08T12:05:00+00:00" in contents
        assert "- Commit range: abc123..HEAD" in contents
        assert "### Tweet 1 (approved)" in contents
        assert "### Tweet 2 (denied)" in contents
        assert "three" in contents
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_write_markdown_writes_artifact_without_approval_labels():
    case_dir = _TEST_TEMP_ROOT / f"approval-md-none-{uuid.uuid4().hex}"
    output_dir = case_dir / ".diff2tweet"

    try:
        artifact_path = write_markdown(
            output_dir,
            "2026-03-08T12:00:00+00:00",
            "abc123..HEAD",
            ["one", "two", "three"],
            None,
            None,
        )
        contents = artifact_path.read_text(encoding="utf-8")

        assert "- Generation timestamp: 2026-03-08T12:00:00+00:00" in contents
        assert "- Approval timestamp:" not in contents
        assert "### Tweet 1\n" in contents
        assert "### Tweet 2\n" in contents
        assert "(approved)" not in contents
        assert "(denied)" not in contents
        assert "three" in contents
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
