---
name: setup-remote-workspace
description: "Register one specific remote workspace with the orchestrator by deploying a listener and binding it to a single workspace id."
---

# setup-remote-workspace

## When To Use

- One workspace of an existing project must run remotely while the rest stay local
- The user wants a remote listener bound to one explicit workspace id
- The project already exists locally, but a specific workspace should execute elsewhere

This skill uses the same listener model as `setup-remote-project`, but registration happens at the workspace level instead of for a whole project.

## Runtime Adaptation

- `claude`
  Verify `claude-agent-sdk` is importable on the remote host.
- `cursor`
  Verify `cursor-agent` exists on the remote host and is authenticated.
- `codex`
  Verify `codex` is installed on the remote host and works non-interactively.
- `opencode`
  Verify `opencode` plus provider login are already available on the remote host.

## Difference From setup-remote-project

| | setup-remote-project | setup-remote-workspace |
|---|---|---|
| Target | Entire project or top-level workspace registration | One specific workspace id |
| Registration | Project/workspace chosen directly | Project and workspace are collected separately |
| Best fit | Moving a whole remote codebase | Mixing local and remote workspaces inside one project |

## Rules

- Never deploy or overwrite a remote listener without confirmation
- Present detected values as numbered choices whenever possible
- Use one port per remote workspace listener, even when multiple listeners share the same host
- Preserve runtime guidance files on the remote workspace: `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/rules`, `.cursorrules`, `opencode.json`, `.opencode/`

## Procedure

### 1. Environment Preflight

Verify:

- `orchestrator.yaml` exists
- `orchestrator/remote/` contains the deployment utilities
- current `remote_workspaces` entries are reviewed so the new listener does not collide with existing host/port pairs
- `ssh` or `kubectl` is available for deployment

### 2. Identify The Target

Collect:

- local project name
- workspace name
- final registration name in `project/workspace` format

The local project must already exist so the planner can route to it later.

### 3. Collect Connection Details

If using SSH, collect and test:

- host
- user
- key file or default agent usage

If using kubectl, collect and test:

- namespace
- pod
- container when needed
- kubeconfig

### 4. Remote Workspace Path

Ask for the absolute remote workspace path and verify it exists.

Choose:

- listener port
- optional bearer token
- target runtime

The recommended port should avoid all already-registered ports on the same host.

### 5. Remote Environment Pre-check

Verify on the remote machine:

- `python3`
- `aiohttp`
- the selected runtime binary or SDK
- runtime authentication state
- workspace guidance files expected by the selected runtime

If a prerequisite is missing, offer to install or stop.

### 6. Deploy And Register

Before executing, summarize:

```text
Deployment summary:
  workspace:  my-project/data-pipeline
  access:     ssh irteam@10.0.0.5
  path:       /home/user/my-project/data-pipeline
  port:       9102
  runtime:    codex
  token:      none

Proceed? (yes/no)
```

Then:

1. deploy the listener
2. start it on the chosen host and port
3. write the new `remote_workspaces` entry into `orchestrator.yaml`

### 7. Validation

Run:

```bash
curl http://$HOST:$LISTENER_PORT/health
```

Expected shape:

```json
{"status": "ok", "cwd": "...", "runtime": "codex"}
```

If validation fails, inspect the remote log and stop instead of retrying blindly.

## Viewing Logs

```bash
ssh $USER@$HOST cat /tmp/claude-listener-$LISTENER_PORT.log
kubectl exec $POD -n $NAMESPACE -- cat /tmp/claude-listener-$LISTENER_PORT.log
```

## Completion Checklist

- the workspace id is unique and maps to the intended local project
- the remote listener is reachable on the chosen host and port
- `orchestrator.yaml` contains the new `remote_workspaces` entry
- the selected runtime is installed and authenticated on the remote host
