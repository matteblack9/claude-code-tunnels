"""Remote workspace listener for executing workspace tasks over HTTP.

This script is intentionally standalone so it can be copied to a remote host
without the full repository. Claude uses the Python SDK directly; Cursor,
Codex, and OpenCode use their local CLIs on the remote machine.

Run:
  LISTENER_CWD=/path/to/workspace LISTENER_PORT=9100 python3 listener.py

Environment variables:
  LISTENER_CWD      workspace directory (default: cwd)
  LISTENER_PORT     port to listen on (default: 9100)
  LISTENER_TOKEN    optional bearer token for auth
  LISTENER_RUNTIME  default runtime for requests without explicit runtime
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

# Remove env vars that interfere with SDK/CLI subprocess spawning.
for _key in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"):
    os.environ.pop(_key, None)

from aiohttp import web
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

logging.basicConfig(level=logging.INFO, format="%(asctime)s [listener] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_CWD = Path(os.environ.get("LISTENER_CWD", os.getcwd())).resolve()
LISTENER_PORT = int(os.environ.get("LISTENER_PORT", "9100"))
LISTENER_TOKEN = os.environ.get("LISTENER_TOKEN", "")
LISTENER_RUNTIME = os.environ.get("LISTENER_RUNTIME", "claude").strip().lower() or "claude"
CURSOR_CLI_TIMEOUT_SECONDS = 30 * 60

RESPONSE_FORMAT_INSTRUCTION = """
## Response format (CRITICAL — must be followed exactly)

When the task is complete, output only this JSON:

{
  "changed_files": ["path/to/changed/file"],
  "summary": "Detailed task report",
  "test_result": "pass | fail | skip",
  "downstream_context": ""
}
"""


def extract_json(text: str) -> dict:
    """Extract JSON from text with multiple fallback strategies."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for match in re.finditer(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL):
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue

    candidates: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escape_next = False

    for index, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and depth > 0:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start != -1:
                candidates.append(text[start : index + 1])
                start = -1

    for candidate in sorted(candidates, key=len, reverse=True):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError("No valid JSON found in response")


def build_prompt(
    task: str,
    upstream_context: dict[str, str] | None,
    skill_context: str = "",
) -> str:
    """Build the remote executor prompt."""
    sections: list[str] = []
    if skill_context:
        sections.append(skill_context.strip())
    if upstream_context:
        lines = [f"- {workspace}: {summary}" for workspace, summary in upstream_context.items()]
        sections.append(
            "<upstream_context>\n"
            + "\n".join(lines)
            + "\n</upstream_context>\n"
            "Incorporate the above changes and perform the task below.\n"
        )
    sections.append(f"<task>\n{task}\n</task>")
    sections.append(RESPONSE_FORMAT_INSTRUCTION)
    return "\n".join(sections)


async def run_claude(prompt: str) -> str:
    """Execute the remote task with claude-agent-sdk."""
    options = ClaudeAgentOptions(
        cwd=str(WORKSPACE_CWD),
        max_turns=5,
        permission_mode="bypassPermissions",
        setting_sources=["project"],
    )

    collected_texts: list[str] = []
    final_result: str | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    collected_texts.append(block.text)
        elif isinstance(message, ResultMessage) and message.result:
            final_result = message.result

    return final_result or (collected_texts[-1] if collected_texts else "")


def _run_subprocess(command: list[str], timeout: int | None = None) -> str:
    try:
        proc = subprocess.run(
            command,
            cwd=str(WORKSPACE_CWD),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"{command[0]} not found on the remote host.") from exc
    except subprocess.TimeoutExpired as exc:
        if timeout is None:
            raise RuntimeError(f"{command[0]} timed out.") from exc
        raise RuntimeError(
            f"{command[0]} timed out after {timeout // 60} minutes on the remote host."
        ) from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        message = stderr or stdout or f"command failed ({proc.returncode})"
        raise RuntimeError(message)
    return stdout


def run_codex(prompt: str) -> str:
    """Execute the remote task with the Codex CLI."""
    with tempfile.TemporaryDirectory(prefix="listener-codex-") as temp_dir:
        output_path = Path(temp_dir) / "last-message.txt"
        command = [
            "codex",
            "exec",
            "-C",
            str(WORKSPACE_CWD),
            "--skip-git-repo-check",
            "-s",
            "workspace-write",
            "-a",
            "never",
            "-o",
            str(output_path),
            prompt,
        ]
        _run_subprocess(command)
        return output_path.read_text(encoding="utf-8").strip()


def _extract_cursor_text_from_json(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""

    payloads: list[dict] = []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            payloads = [parsed]
        elif isinstance(parsed, list):
            payloads = [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                payloads.append(payload)

    if not payloads:
        return text

    for payload in reversed(payloads):
        if payload.get("is_error"):
            message = payload.get("error") or payload.get("message") or payload.get("result")
            raise RuntimeError(str(message or "Cursor CLI returned an error."))
        for key in ("result", "text", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return text


def run_cursor(prompt: str) -> str:
    """Execute the remote task with the Cursor CLI."""
    command = [
        "cursor-agent",
        "--print",
        "--output-format",
        "json",
        "--force",
        prompt,
    ]
    stdout = _run_subprocess(command, timeout=CURSOR_CLI_TIMEOUT_SECONDS)
    return _extract_cursor_text_from_json(stdout) or stdout


def _extract_text_from_json_events(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    texts: list[str] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            for key in ("text", "content", "message"):
                value = payload.get(key)
                if isinstance(value, str):
                    texts.append(value)
            info = payload.get("info")
            if isinstance(info, dict):
                if isinstance(info.get("text"), str):
                    texts.append(info["text"])
                structured = info.get("structured_output")
                if structured is not None:
                    texts.append(json.dumps(structured))
    return "\n".join(chunk for chunk in texts if chunk).strip()


def run_opencode(prompt: str) -> str:
    """Execute the remote task with the OpenCode CLI."""
    command = [
        "opencode",
        "run",
        "--dir",
        str(WORKSPACE_CWD),
        "--format",
        "json",
        prompt,
    ]
    stdout = _run_subprocess(command)
    return _extract_text_from_json_events(stdout) or stdout


async def execute_task(
    task: str,
    runtime: str,
    upstream_context: dict[str, str] | None,
    skill_context: str = "",
) -> dict:
    """Execute the task and return structured JSON-compatible output."""
    runtime_name = (runtime or LISTENER_RUNTIME or "claude").strip().lower()
    prompt = build_prompt(task, upstream_context, skill_context)

    if runtime_name == "claude":
        raw = await run_claude(prompt)
    elif runtime_name == "cursor":
        raw = await asyncio.to_thread(run_cursor, prompt)
    elif runtime_name == "codex":
        raw = await asyncio.to_thread(run_codex, prompt)
    elif runtime_name == "opencode":
        raw = await asyncio.to_thread(run_opencode, prompt)
    else:
        raise RuntimeError(f"Unsupported runtime: {runtime_name}")

    try:
        parsed = extract_json(raw)
    except ValueError:
        parsed = {
            "changed_files": [],
            "summary": raw[:2000] if raw else "No response from remote runtime",
            "test_result": "skip",
            "downstream_context": "",
        }
    parsed.setdefault("runtime", runtime_name)
    return parsed


def _is_authorized(request: web.Request) -> bool:
    if not LISTENER_TOKEN:
        return True
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {LISTENER_TOKEN}"


async def handle_health(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "cwd": str(WORKSPACE_CWD),
            "runtime": LISTENER_RUNTIME,
        }
    )


async def handle_execute(request: web.Request) -> web.Response:
    if not _is_authorized(request):
        return web.json_response({"error": "unauthorized"}, status=401)

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    task = str(payload.get("task", "")).strip()
    runtime = str(payload.get("runtime") or LISTENER_RUNTIME).strip().lower()
    upstream_context = payload.get("upstream_context") or {}
    skill_context = str(payload.get("skill_context") or "")

    if not task:
        return web.json_response({"error": "task is required"}, status=400)

    try:
        result = await execute_task(task, runtime, upstream_context, skill_context)
        return web.json_response(result)
    except Exception as exc:
        logger.exception("Remote execution failed")
        return web.json_response(
            {
                "changed_files": [],
                "summary": f"Remote runtime failed: {exc}",
                "test_result": "fail",
                "downstream_context": "",
                "error": str(exc),
                "runtime": runtime,
            },
            status=500,
        )


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/execute", handle_execute)
    return app


def main() -> None:
    logger.info("Starting listener on port %s (cwd=%s, runtime=%s)", LISTENER_PORT, WORKSPACE_CWD, LISTENER_RUNTIME)
    web.run_app(create_app(), port=LISTENER_PORT)


if __name__ == "__main__":
    main()
