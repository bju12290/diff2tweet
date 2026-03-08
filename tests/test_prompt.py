from __future__ import annotations

from pathlib import Path

from difftotweet.config import RuntimeConfig
from difftotweet.git import GitContext
from difftotweet.prompt import build_prompt


def test_build_prompt_orders_context_by_priority_and_filters_diff_noise():
    config = _runtime_config(context_max_chars=1000)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Add prompt builder", "Tighten CLI output"],
        diff_text=(
            "diff --git a/package-lock.json b/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "+lock noise\n"
            "diff --git a/src/app.py b/src/app.py\n"
            "+++ b/src/app.py\n"
            "+print('ship it')\n"
        ),
    )

    prompt = build_prompt(config, git_context, "Mention the launch thread.", "README intro")

    assert prompt.index("## README") < prompt.index("## COMMIT MESSAGES")
    assert prompt.index("## COMMIT MESSAGES") < prompt.index("## NOTES")
    assert prompt.index("## NOTES") < prompt.index("## FILTERED DIFF")
    assert "package-lock.json" not in prompt
    assert "src/app.py" in prompt
    assert "#buildinpublic" in prompt


def test_build_prompt_enforces_context_budget_in_priority_order():
    config = _runtime_config(context_max_chars=18)
    git_context = GitContext(
        repo_root=Path("."),
        commit_range="abc..HEAD",
        commit_messages=["Commit details"],
        diff_text="diff --git a/src/app.py b/src/app.py\n+code\n",
    )

    prompt = build_prompt(config, git_context, "Notes section", "README section")
    context_block = prompt.split("Context:\n", maxsplit=1)[1]

    assert len(context_block) <= config.context_max_chars
    assert "## README" in context_block
    assert "## COMMIT MESSAGES" not in context_block
    assert "## NOTES" not in context_block
    assert "## FILTERED DIFF" not in context_block


def _runtime_config(*, context_max_chars: int) -> RuntimeConfig:
    return RuntimeConfig(
        provider="openai",
        model="gpt-4.1-mini",
        custom_instructions="Stay sharp.",
        forced_hashtags=["#buildinpublic"],
        character_limit=280,
        lookback_commits=5,
        readme_max_chars=2000,
        context_max_chars=context_max_chars,
        diff_ignore_patterns=["*.lock", "package-lock.json", "dist/**"],
        output_folder=Path(".diff2tweet"),
        provider_api_key="test-key",
        openai_api_key="test-key",
    )
