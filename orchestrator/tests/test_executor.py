"""Tests for orchestrator.executor and runtime-aware workspace execution."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import orchestrator
from orchestrator.executor import execute_phases, run_workspace
from orchestrator.runtime import RuntimeExecution


def _runtime_result(text: str, runtime: str = "claude") -> RuntimeExecution:
    return RuntimeExecution(runtime=runtime, final_text=text)


@pytest.fixture(autouse=True)
def _reset_config(monkeypatch):
    monkeypatch.setattr(orchestrator, "CONFIG", {})


class TestRunWorkspace:
    @pytest.mark.asyncio
    async def test_workspace_registry_path_and_runtime_are_used(self, monkeypatch):
        monkeypatch.setattr(
            orchestrator,
            "CONFIG",
            {
                "workspaces": [
                    {
                        "id": "backend",
                        "path": "services/backend",
                        "wo": {"runtime": "codex", "mode": "local"},
                    }
                ],
                "runtime": {"default": "claude", "roles": {"executor": "claude"}},
            },
        )

        with patch("orchestrator.executor.execute_runtime", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _runtime_result(
                '{"changed_files": [], "summary": "done", "test_result": "pass", "downstream_context": ""}',
                runtime="codex",
            )

            result = await run_workspace(
                project=".",
                workspace="backend",
                task="update service",
                base_dir=Path("/tmp/project"),
            )

            invocation = mock_execute.await_args.args[0]
            assert invocation.runtime == "codex"
            assert Path(invocation.cwd) == Path("/tmp/project/services/backend").resolve()
            assert result["runtime"] == "codex"

    @pytest.mark.asyncio
    async def test_json_response_is_parsed(self):
        with patch("orchestrator.executor.execute_runtime", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _runtime_result(
                '{"changed_files": ["api.py"], "summary": "added endpoint", '
                '"test_result": "pass", "downstream_context": "Added GET /health"}',
                runtime="claude",
            )

            result = await run_workspace(
                project="project",
                workspace="server",
                task="task",
                base_dir=Path("/test"),
            )

            assert result["changed_files"] == ["api.py"]
            assert result["summary"] == "added endpoint"
            assert result["test_result"] == "pass"
            assert result["downstream_context"] == "Added GET /health"
            assert result["runtime"] == "claude"

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_after_repair(self):
        with patch("orchestrator.executor.execute_runtime", new_callable=AsyncMock) as mock_execute, patch(
            "orchestrator.executor.repair_json", new_callable=AsyncMock
        ) as mock_repair:
            mock_execute.return_value = _runtime_result("not valid json", runtime="opencode")
            mock_repair.return_value = None

            result = await run_workspace(
                project="project",
                workspace="server",
                task="task",
                base_dir=Path("/test"),
            )

            assert result["test_result"] == "skip"
            assert "not valid json" in result["summary"]
            assert result["runtime"] == "opencode"

    @pytest.mark.asyncio
    async def test_upstream_context_is_embedded_in_prompt(self):
        with patch("orchestrator.executor.execute_runtime", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _runtime_result(
                '{"changed_files": [], "summary": "ok", "test_result": "pass", "downstream_context": ""}'
            )

            await run_workspace(
                project="project",
                workspace="frontend",
                task="update frontend",
                upstream_context={"server": "Added GET /health endpoint"},
                base_dir=Path("/test"),
            )

            invocation = mock_execute.await_args.args[0]
            assert "<upstream_context>" in invocation.prompt
            assert "server: Added GET /health endpoint" in invocation.prompt
            assert "<task>" in invocation.prompt

    @pytest.mark.asyncio
    async def test_matching_skill_is_preloaded_into_prompt(self, tmp_path):
        skill_dir = tmp_path / "skills" / "connect-slack"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: connect-slack\ndescription: connect slack\n---\n\n# Connect Slack\n\nDo the Slack flow.\n",
            encoding="utf-8",
        )

        with patch("orchestrator.executor.execute_runtime", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _runtime_result(
                '{"changed_files": [], "summary": "ok", "test_result": "pass", "downstream_context": ""}'
            )

            await run_workspace(
                project="project",
                workspace="frontend",
                task="connect slack channel for this orchestrator",
                base_dir=tmp_path,
            )

            invocation = mock_execute.await_args.args[0]
            assert "Local Skill Playbooks" in invocation.prompt
            assert '<skill name="connect-slack"' in invocation.prompt


class TestExecutePhases:
    @pytest.mark.asyncio
    async def test_single_phase_multi_workspace(self):
        async def fake_run(project, workspace, task, upstream_context=None, base_dir=None):
            return {
                "changed_files": [],
                "summary": f"{workspace} done",
                "test_result": "pass",
                "downstream_context": "",
            }

        with patch("orchestrator.executor.run_workspace", side_effect=fake_run):
            results = await execute_phases(
                project="project",
                phases=[["ws1", "ws2"]],
                tasks={"ws1": "t1", "ws2": "t2"},
            )

            assert set(results) == {"ws1", "ws2"}
            assert results["ws1"]["test_result"] == "pass"
            assert results["ws2"]["test_result"] == "pass"

    @pytest.mark.asyncio
    async def test_upstream_context_flows_between_phases(self):
        seen_contexts = {}

        async def fake_run(project, workspace, task, upstream_context=None, base_dir=None):
            seen_contexts[workspace] = upstream_context
            if workspace == "server":
                return {
                    "changed_files": ["api.py"],
                    "summary": "added API",
                    "test_result": "pass",
                    "downstream_context": "Added GET /health endpoint",
                }
            return {
                "changed_files": ["app.vue"],
                "summary": "updated frontend",
                "test_result": "pass",
                "downstream_context": "",
            }

        with patch("orchestrator.executor.run_workspace", side_effect=fake_run):
            results = await execute_phases(
                project="project",
                phases=[["server"], ["frontend"]],
                tasks={"server": "api", "frontend": "ui"},
            )

            assert seen_contexts["server"] is None
            assert seen_contexts["frontend"] == {"server": "Added GET /health endpoint"}
            assert results["frontend"]["summary"] == "updated frontend"

    @pytest.mark.asyncio
    async def test_failed_workspace_is_carried_as_context_failure(self):
        seen_contexts = {}

        async def fake_run(project, workspace, task, upstream_context=None, base_dir=None):
            seen_contexts[workspace] = upstream_context
            if workspace == "server":
                return {
                    "changed_files": [],
                    "summary": "boom",
                    "test_result": "fail",
                    "downstream_context": "",
                    "error": "boom",
                }
            return {
                "changed_files": [],
                "summary": "frontend saw failure",
                "test_result": "pass",
                "downstream_context": "",
            }

        with patch("orchestrator.executor.run_workspace", side_effect=fake_run):
            await execute_phases(
                project="project",
                phases=[["server"], ["frontend"]],
                tasks={"server": "api", "frontend": "ui"},
            )

            assert seen_contexts["frontend"] == {"server": "FAILED: boom"}
