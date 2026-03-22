---
name: setup-remote-project
description: "원격 장비(SSH/kubectl)에 listener를 배포하여 Orchestrator가 해당 장비의 프로젝트를 workspace로 사용 가능하게 설정. /setup-remote-project 로 실행. 'remote project 연결', '원격 프로젝트 설정', 'SSH 프로젝트 연결' 요청에 사용."
---

# Setup Remote Project

원격 장비(SSH) 또는 Kubernetes Pod에 listener를 배포하여, Orchestrator가 원격 환경의 프로젝트를 workspace로 사용할 수 있게 한다.

## How It Works

1. 원격 장비에 lightweight HTTP listener(`listener.py`)를 배포
2. listener는 Orchestrator로부터 HTTP로 task를 수신
3. listener가 로컬에서 `claude-agent-sdk query(cwd=workspace/)` 실행
4. 결과를 JSON으로 반환

## Flow

### Step 1: Connection Method

Ask the user:
- SSH: host, user, (optional) SSH key path
- kubectl: pod name, namespace, (optional) kubeconfig path, (optional) container name

### Step 2: Remote Workspace Info

```
remote_cwd: /path/to/project/on/remote/host
listener_port: 9100 (default)
workspace_name: project-name/workspace-name (how it appears in orchestrator)
```

### Step 3: Deploy Listener

#### Via SSH
```bash
# The deploy script handles:
# 1. Copy listener.py to remote host
# 2. Start listener with nohup
# 3. Verify health check

python3 -c "
from orchestrator.remote.deploy import deploy_via_ssh
deploy_via_ssh(
    host='HOST',
    remote_cwd='REMOTE_CWD',
    port=PORT,
    user='USER',
    key_file='KEY_FILE',
)
"
```

#### Via kubectl
```bash
python3 -c "
from orchestrator.remote.deploy import deploy_via_kubectl
deploy_via_kubectl(
    pod='POD_NAME',
    namespace='NAMESPACE',
    remote_cwd='REMOTE_CWD',
    port=PORT,
    kubeconfig='KUBECONFIG_PATH',
)
"
```

### Step 4: Register in Config

Add to `orchestrator.yaml`:
```yaml
remote_workspaces:
  - name: project/workspace
    host: remote-host-or-pod-ip
    port: 9100
    token: ""
```

### Step 5: Test

```bash
curl http://HOST:PORT/health
```

Should return: `{"status": "ok", "cwd": "/path/to/workspace", "port": 9100}`

## Prerequisites on Remote Host

- Python 3.10+
- claude-agent-sdk installed (`pip install claude-agent-sdk`)
- aiohttp installed (`pip install aiohttp`)
- Claude Code CLI available in PATH

## Rules

- listener.py requires claude-agent-sdk on the remote host
- If SSH key auth fails, suggest password auth or key setup
- Always test health check after deployment
- Port must be accessible from the orchestrator host
