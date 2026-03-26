"""Tests for skills-first prompt injection across orchestrator agents."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from orchestrator.direct_handler import handle_direct_request
from orchestrator.po import get_execution_plan
from orchestrator.router import route_request
from orchestrator.runtime import RuntimeExecution
from orchestrator.skills import build_skills_prompt, discover_skill_documents


def _write_skill(base_dir: Path, name: str, description: str, body: str) -> None:
    skill_dir = base_dir / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_discover_skill_documents_reads_frontmatter(tmp_path):
    _write_skill(tmp_path, "setup-orchestrator", "bootstrap", "# Setup")

    documents = discover_skill_documents(tmp_path)

    assert len(documents) == 1
    assert documents[0].name == "setup-orchestrator"
    assert documents[0].description == "bootstrap"


def test_build_skills_prompt_preloads_matching_skill(tmp_path):
    _write_skill(tmp_path, "connect-slack", "connect slack", "# Connect Slack\n\nUse Socket Mode.")
    _write_skill(tmp_path, "setup-orchestrator", "bootstrap", "# Setup")

    prompt = build_skills_prompt("Please connect slack to this orchestrator", tmp_path)

    assert "Available skills:" in prompt
    assert '<skill name="connect-slack"' in prompt


def test_build_skills_prompt_can_render_catalog_only(tmp_path):
    _write_skill(tmp_path, "connect-slack", "connect slack", "# Connect Slack")

    prompt = build_skills_prompt("refactor API handler", tmp_path, include_full_text=False)

    assert "Available skills:" in prompt
    assert "<skill " not in prompt


@pytest.mark.asyncio
async def test_router_system_prompt_includes_skill_catalog(tmp_path):
    _write_skill(tmp_path, "connect-slack", "connect slack", "# Connect Slack")

    with patch("orchestrator.router.execute_runtime", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = RuntimeExecution(
            runtime="claude",
            final_text='{"no_project": true, "refined_message": "connect slack"}',
        )

        await route_request("connect slack", base_dir=tmp_path)

        invocation = mock_execute.await_args.args[0]
        assert "Local Skill Playbooks" in invocation.system_prompt
        assert "connect-slack" in invocation.system_prompt


@pytest.mark.asyncio
async def test_planner_system_prompt_preloads_matching_skill(tmp_path):
    _write_skill(tmp_path, "connect-slack", "connect slack", "# Connect Slack\n\nUse Socket Mode.")

    with patch("orchestrator.po.execute_runtime", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = RuntimeExecution(
            runtime="claude",
            final_text='{"direct_answer": "ok"}',
        )

        await get_execution_plan("connect slack", base_dir=tmp_path)

        invocation = mock_execute.await_args.args[0]
        assert "Local Skill Playbooks" in invocation.system_prompt
        assert '<skill name="connect-slack"' in invocation.system_prompt


@pytest.mark.asyncio
async def test_direct_handler_system_prompt_preloads_matching_skill(tmp_path, monkeypatch):
    _write_skill(tmp_path, "connect-telegram", "connect telegram", "# Connect Telegram")
    monkeypatch.setattr("orchestrator.direct_handler.BASE", tmp_path)

    with patch("orchestrator.direct_handler.execute_runtime", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = RuntimeExecution(runtime="claude", final_text="done")

        await handle_direct_request("connect telegram")

        invocation = mock_execute.await_args.args[0]
        assert "Local Skill Playbooks" in invocation.system_prompt
        assert '<skill name="connect-telegram"' in invocation.system_prompt
