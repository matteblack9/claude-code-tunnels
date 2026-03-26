"""Tests for the remote listener helpers."""

import json

import pytest

from orchestrator.remote import listener


def test_build_prompt_wraps_task_and_upstream_context():
    prompt = listener.build_prompt(
        "deploy it",
        {"backend": "API ready"},
        "## Local Skill Playbooks\n- connect-slack",
    )

    assert "Local Skill Playbooks" in prompt
    assert "<upstream_context>" in prompt
    assert "backend: API ready" in prompt
    assert "<task>" in prompt
    assert "deploy it" in prompt


def test_extract_cursor_text_from_json_returns_result():
    raw = '{"type":"result","subtype":"success","is_error":false,"result":"done"}'

    assert listener._extract_cursor_text_from_json(raw) == "done"


@pytest.mark.asyncio
async def test_health_reports_listener_runtime(monkeypatch):
    monkeypatch.setattr(listener, "LISTENER_RUNTIME", "codex")
    response = await listener.handle_health(None)
    payload = json.loads(response.text)

    assert payload["status"] == "ok"
    assert payload["runtime"] == "codex"
