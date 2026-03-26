---
name: setup-remote-project
description: "Deploy a remote listener over SSH or kubectl so the orchestrator can execute one project/workspace on another machine."
---

# setup-remote-project

## When To Use

- The user wants the orchestrator to execute a project or workspace on a different host
- Remote runtime binaries and project files already live on the target machine
- A listener must be deployed and registered in `remote_workspaces`

The listener runs on the remote machine itself. Claude uses the Python SDK there, while Cursor/Codex/OpenCode use their own CLIs there.

## Runtime Adaptation

- `claude`
  Verify `claude-agent-sdk` is importable on the remote host before deployment.
- `cursor`
  Verify `cursor-agent` exists on the remote host and the remote machine is authenticated in Cursor.
- `codex`
  Verify `codex` exists on the remote host and works non-interactively.
- `opencode`
  Verify `opencode` exists, provider login is complete, and any project-local `.opencode/` config is already on the remote machine.

## Rules

- Never deploy a remote listener silently; confirm the target first
- Present detected values as numbered choices whenever possible
- Use one listener per remote workspace; the same host can run multiple listeners on different ports
- Preserve existing runtime guidance on the remote project: `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/rules`, `.cursorrules`, `opencode.json`, `.opencode/`
- The listener must remain running after setup; `nohup` is acceptable, but a service manager is better

## Procedure

### 1. Local Preflight

Verify:

- `orchestrator.yaml` exists
- `orchestrator/remote/deploy.py` and `orchestrator/remote/listener.py` exist
- at least one remote access path is available: `ssh` or `kubectl`
- current `remote_workspaces` entries are reviewed to avoid duplicate host/port conflicts

If `orchestrator.yaml` is missing, stop and run the `setup-orchestrator` skill first.

### 2. Collect Connection Details

Gather:

- `workspace_name` in `project/workspace` format
- remote access method: `ssh` or `kubectl`
- host, user, key file for SSH
- namespace, pod, container, kubeconfig for kubectl

Run an immediate connectivity test after collecting the transport details.

### 3. Remote Project Path

Ask for the absolute remote project path and verify it exists on the remote machine.

Choose:

- listener port
- optional bearer token
- target runtime for that remote workspace

The port must not collide with existing listeners on the same host.

### 4. Remote Environment Pre-check

Verify on the remote machine:

- `python3`
- `aiohttp`
- the selected runtime binary or SDK
- any required runtime authentication state
- the project path already contains the runtime guidance files that runtime expects

If a prerequisite is missing, offer to install or stop and let the user fix it manually.

### 5. Deploy And Register

Before executing, summarize:

```text
Remote deployment summary:
  workspace:  my-project/backend
  access:     ssh irteam@10.0.0.5
  path:       /home/user/my-project
  port:       9100
  runtime:    cursor
  token:      configured

Proceed? (yes/no)
```

Then:

1. copy the listener to the remote host
2. stop any conflicting process on the same port
3. start the listener and capture logs
4. register the new entry in `orchestrator.yaml`

### 6. Validate

Run:

```bash
curl http://$HOST:$LISTENER_PORT/health
```

Expected shape:

```json
{"status": "ok", "cwd": "...", "runtime": "cursor"}
```

If validation fails, inspect remote logs and stop instead of retrying blindly.

## Completion Checklist

- the remote listener is reachable from the orchestrator host
- `remote_workspaces` contains the correct host, port, token, and runtime
- the remote project exposes the right runtime guidance files
- the user knows how to inspect remote listener logs
