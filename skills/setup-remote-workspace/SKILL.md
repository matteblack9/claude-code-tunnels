---
name: setup-remote-workspace
description: "원격 장비의 특정 workspace를 Orchestrator에 연결. setup-remote-project와 유사하지만 단일 workspace 단위로 설정. /setup-remote-workspace 로 실행. 'remote workspace 연결', '원격 워크스페이스 설정' 요청에 사용."
---

# Setup Remote Workspace

원격 장비의 특정 workspace 하나를 Orchestrator에 연결한다.

## Difference from /setup-remote-project

- `/setup-remote-project`: 프로젝트 전체를 원격으로 연결 (하위 workspace 포함)
- `/setup-remote-workspace`: 특정 workspace 하나만 원격으로 연결

## Flow

### Step 1: Identify Target

Ask the user:
```
1. Which project does this workspace belong to?
2. Workspace name (as it will appear in execution plans)
3. Connection method: ssh / kubectl
```

### Step 2: Connection Details

Same as /setup-remote-project:
- SSH: host, user, key path
- kubectl: pod, namespace, kubeconfig, container

### Step 3: Remote Workspace Path

```
remote_cwd: /absolute/path/to/workspace/on/remote
listener_port: 9100 (or next available)
```

### Step 4: Deploy & Register

1. Deploy listener.py to remote host
2. Add entry to orchestrator.yaml remote_workspaces
3. Test health check

### Step 5: Verify Integration

The workspace should now be callable by the orchestrator. When the PO includes this workspace in an execution plan, the executor will call the remote listener instead of local `query(cwd=)`.

## Rules

- One listener per workspace (each on a different port if on the same host)
- Remote workspace must have CLAUDE.md for the PO to understand it
- Ensure the remote listener stays running (consider systemd/supervisord)
