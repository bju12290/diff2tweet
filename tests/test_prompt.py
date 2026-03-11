from __future__ import annotations

from pathlib import Path

from difftotweet.config import RuntimeConfig
from difftotweet.config.config_schema import DiffToTweetConfig
from difftotweet.git import GitContext
from difftotweet.prompt import _truncate_doc_section, build_prompt


def test_build_prompt_orders_context_by_priority_and_filters_diff_noise():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context", "Tighten CLI output for review flow"],
        diff_text=(
            "diff --git a/package-lock.json b/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "+lock noise\n"
            "diff --git a/tests/test_prompt.py b/tests/test_prompt.py\n"
            "+++ b/tests/test_prompt.py\n"
            "+assert True\n"
            "diff --git a/src/app.py b/src/app.py\n"
            "+++ b/src/app.py\n"
            "+print('ship it')\n"
        ),
    )

    prompt = build_prompt(config, git_context, "Mention the launch thread.")

    assert prompt.index("## Project") < prompt.index("## NOTES")
    assert prompt.index("## NOTES") < prompt.index("## COMMIT MESSAGES")
    assert prompt.index("## COMMIT MESSAGES") < prompt.index("## FILTERED DIFF")
    assert "package-lock.json" not in prompt
    assert "tests/test_prompt.py" not in prompt
    assert "src/app.py" not in prompt
    assert "# app.py" in prompt
    assert "Name: diff2tweet" in prompt
    assert "Stage: prototype" in prompt
    assert "Tone: technical" in prompt
    assert "Key terms: CLI, git workflow" in prompt
    assert "#buildinpublic" in prompt
    assert "Return the single best tweet as JSON" in prompt


def test_build_prompt_renders_only_present_optional_project_fields():
    config = _runtime_config(
        context_max_chars=1000,
        project_name="",
        project_summary="Turns diffs into tweets.",
        project_audience="",
        project_key_terms=[],
    )
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context"],
        diff_text="",
    )

    prompt = build_prompt(config, git_context, None)

    assert "## Project" in prompt
    assert "Summary: Turns diffs into tweets." in prompt
    assert "Stage: prototype" in prompt
    assert "Tone: technical" in prompt
    assert "Name:" not in prompt
    assert "Audience:" not in prompt
    assert "Key terms:" not in prompt


def test_build_prompt_keeps_project_section_with_stage_and_tone_defaults():
    config = _runtime_config(
        context_max_chars=1000,
        project_name="",
        project_summary="",
        project_audience="",
        project_key_terms=[],
    )
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context"],
        diff_text="",
    )

    prompt = build_prompt(config, git_context, None)

    assert "## Project" in prompt
    assert "Stage: prototype" in prompt
    assert "Tone: technical" in prompt



def test_build_prompt_enforces_context_budget_in_priority_order():
    config = _runtime_config(context_max_chars=30)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Commit details with enough context"],
        diff_text="diff --git a/src/app.py b/src/app.py\n+code\n",
    )

    prompt = build_prompt(config, git_context, "Notes section")
    context_block = prompt.split("Context:\n", maxsplit=1)[1]

    assert len(context_block) >= len("## Project\nStage: prototype")
    assert "## Project" in context_block
    assert "## NOTES" not in context_block
    assert "## COMMIT MESSAGES" not in context_block
    assert "## FILTERED DIFF" not in context_block


def test_build_prompt_filters_pure_whole_file_deletions_from_diff():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context"],
        diff_text=(
            "diff --git a/src/old_module.py b/src/old_module.py\n"
            "--- a/src/old_module.py\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n"
            "-old code\n"
            "-more old code\n"
            "diff --git a/src/app.py b/src/app.py\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1,2 @@\n"
            " print('existing')\n"
            "+print('new')\n"
        ),
    )

    prompt = build_prompt(config, git_context, None)

    assert "old_module.py" not in prompt
    assert "src/app.py" not in prompt
    assert "# app.py" in prompt
    assert "+print('new')" in prompt


def test_build_prompt_filters_auto_generated_diff_sections():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context"],
        diff_text=(
            "diff --git a/src/generated_client.py b/src/generated_client.py\n"
            "--- a/src/generated_client.py\n"
            "+++ b/src/generated_client.py\n"
            "@@ -1 +1,2 @@\n"
            "+// auto-generated by openapi\n"
            "+export const client = {}\n"
            "diff --git a/src/app.py b/src/app.py\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1,2 @@\n"
            " print('existing')\n"
            "+print('ship it')\n"
        ),
    )

    prompt = build_prompt(config, git_context, None)

    assert "generated_client.py" not in prompt
    assert "auto-generated" not in prompt.lower()
    assert "# app.py" in prompt


def test_build_prompt_reformats_diff_to_compact_headers_and_content_only():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder with better context"],
        diff_text=(
            "diff --git a/src/app.py b/src/app.py\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1,3 @@\n"
            " print('existing')\n"
            "-print('old')\n"
            "+print('new')\n"
        ),
    )

    prompt = build_prompt(config, git_context, None)

    assert "# app.py" in prompt
    assert "diff --git" not in prompt
    assert "--- a/src/app.py" not in prompt
    assert "+++ b/src/app.py" not in prompt
    assert "@@ -1 +1,3 @@" not in prompt
    assert " print('existing')" in prompt
    assert "-print('old')" in prompt
    assert "+print('new')" in prompt


def test_build_prompt_filters_useless_commit_subjects():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=[
            "fix\n\nsmall tweak",
            "Ship better prompt filtering for noisy diffs\n\nIncludes smarter formatting.",
            "cleanup",
        ],
        diff_text="",
    )

    prompt = build_prompt(config, git_context, None)

    assert "fix\n\nsmall tweak" not in prompt
    assert "cleanup" not in prompt
    assert "Ship better prompt filtering for noisy diffs" in prompt
    assert "Includes smarter formatting." in prompt


def test_build_prompt_filters_short_commit_subjects_but_keeps_longer_ones():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=[
            "ship it",
            "Refine prompt diff filtering for generated files",
            "   \n\nshort subject\n\nbody text",
        ],
        diff_text="",
    )

    prompt = build_prompt(config, git_context, None)

    assert "ship it" not in prompt
    assert "short subject" not in prompt
    assert "body text" not in prompt
    assert "Refine prompt diff filtering for generated files" in prompt


def test_build_prompt_uses_configurable_commit_subject_min_chars():
    config = _runtime_config(context_max_chars=1000, commit_subject_min_chars=10)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=[
            "Small tweak",
            "ship it",
        ],
        diff_text="",
    )

    prompt = build_prompt(config, git_context, None)

    assert "Small tweak" in prompt
    assert "ship it" not in prompt


def test_truncate_doc_section_passes_through_short_text():
    text = "# README.md\n+line one\n+line two\n"
    result = _truncate_doc_section(text, max_chars=1000)
    assert result == text


def test_truncate_doc_section_truncates_at_line_boundary_with_marker():
    header = "# README.md"
    body_lines = [f"+line {i}" for i in range(50)]
    text = header + "\n" + "\n".join(body_lines)
    max_chars = 50
    result = _truncate_doc_section(text, max_chars=max_chars)
    assert result.endswith("\n[...truncated]")
    assert result.startswith(header)
    assert len(result) < len(text)
    # The non-truncation-marker portion must fit within max_chars
    content_before_marker = result[: result.rfind("\n[...truncated]")]
    assert len(content_before_marker) <= max_chars


def test_diff_ignore_patterns_defaults_include_tests_and_noisy_config_files():
    config = DiffToTweetConfig(model='gpt-4.1-mini')

    assert 'test_*.py' in config.diff_ignore_patterns
    assert '*_test.py' in config.diff_ignore_patterns
    assert '*.test.js' in config.diff_ignore_patterns
    assert '*.test.ts' in config.diff_ignore_patterns
    assert '*.spec.js' in config.diff_ignore_patterns
    assert '*.spec.ts' in config.diff_ignore_patterns
    assert '*.vitest.ts' in config.diff_ignore_patterns
    assert 'tests/**' in config.diff_ignore_patterns
    assert 'test/**' in config.diff_ignore_patterns
    assert '**/tests/**' in config.diff_ignore_patterns
    assert '**/__tests__/**' in config.diff_ignore_patterns
    assert '.prettierrc' in config.diff_ignore_patterns
    assert '.eslintrc' in config.diff_ignore_patterns
    assert '.eslintignore' in config.diff_ignore_patterns
    assert '.editorconfig' in config.diff_ignore_patterns
    assert '.github/**' in config.diff_ignore_patterns


def _runtime_config(
    *,
    context_max_chars: int,
    num_candidates: int = 3,
    commit_subject_min_chars: int = 20,
    project_name: str = "diff2tweet",
    project_summary: str = "Turn recent commits into tweet drafts.",
    project_audience: str = "Developers building in public.",
    project_stage: str = "prototype",
    project_tone: str = "technical",
    project_key_terms: list[str] | None = None,
) -> RuntimeConfig:
    return RuntimeConfig(
        provider="openai",
        model="gpt-4.1-mini",
        project_name=project_name,
        project_summary=project_summary,
        project_audience=project_audience,
        project_stage=project_stage,
        project_tone=project_tone,
        project_key_terms=["CLI", "git workflow"] if project_key_terms is None else project_key_terms,
        custom_instructions="Stay sharp.",
        forced_hashtags=["#buildinpublic"],
        character_limit=280,
        num_candidates=num_candidates,
        lookback_commits=5,
        commit_subject_min_chars=commit_subject_min_chars,
        readme_max_chars=0,
        context_max_chars=context_max_chars,
        max_doc_diff_sections=3,
        max_doc_section_chars=1000,
        diff_ignore_patterns=[
            "*.lock",
            "package-lock.json",
            "dist/**",
            "tests/**",
            ".github/**",
        ],
        output_folder=Path(".diff2tweet"),
        auto_tweet=False,
        provider_api_key="test-key",
        openai_api_key="test-key",
    )
