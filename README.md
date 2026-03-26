# Claude-Code-Tunnels

**Turn any project folder into an AI-orchestrated workspace with Slack and Telegram integration.**

Claude-Code-Tunnels is a plugin that builds a **Project Orchestrator (PO)** layer on top of [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code). Send a message from Slack or Telegram and the orchestrator analyzes the request, identifies the appropriate project and workspace, builds an execution plan with dependency awareness, delegates tasks to workspace-level Claude agents, and returns structured results.

---

## Difference from Claude Code's Built-in Channels

Claude Code recently introduced a [Channels feature](https://docs.anthropic.com/en/docs/claude-code/channels) (research preview) — it forwards Telegram/Discord messages to a running CLI session. Here is why Claude-Code-Tunnels is fundamentally different:

| Feature | Claude Code Channels | Claude-Code-Tunnels |
|---------|---------------------|---------------------|
| **Architecture** | Single CLI session, single working directory | Always-on server with multi-project orchestration |
| **Session Model** | Session-dependent (stops when CLI exits) | Background daemon (persists after disconnect) |
| **Multi-project** | 1 session = 1 project | PO routes to all projects, parallel execution possible |
| **Workspace Orchestration** | None — simple message bridge | Phase-based dependency analysis, parallel execution, upstream context passing |
| **Supported Channels** | Telegram, Discord (preview) | **Slack, Telegram** |
| **Confirm Gate** | None | Built-in: user confirmation required before execution |
| **Task Log** | None | `.tasks/` auto-logging, 30-day retention |
| **Remote Workspaces** | Not supported | SSH/kubectl listener for external servers and K8s pods |
| **Conversation Memory** | Single session context | Per-source sessions (turn history + state machine) |
| **Add Custom Channel** | Requires `--dangerously-load-development-channels` | Inherit Python `BaseChannel` — add in minutes |
| **Security Model** | Sender allowlist only | XML tag isolation + path traversal prevention + prompt injection defense |
| **Runtime** | Requires Bun | Python only (`pip install`) |
| **Permissions Model** | Interactive prompts block execution | `bypassPermissions` support for unattended operation |

**In short**: Claude Code Channels is a raw message bridge into a single session. Claude-Code-Tunnels is a full orchestration layer — each workspace runs in its own isolated session, and one channel connection scales to any number of projects.

---

## Team Collaboration — Shared Channel, Zero Handoff

Traditional setups tie the AI assistant to one person's session. Claude-Code-Tunnels flips this: **the orchestrator lives in the Slack channel, not on anyone's laptop**. Invite the app to a shared channel, invite your teammates — now anyone in the channel can interact with the orchestrator. When you're on vacation, out sick, or simply offline, your team keeps working with full access to every project and workspace.
```mermaid
flowchart TB
    subgraph SLACK["#dev-orchestrator · Slack Channel"]
        APP["🤖 Orchestrator App<br/><small>always online</small>"]
        YOU["👤 You<br/><small>on vacation 🏖️</small>"]
        TM1["👤 Teammate A"]
        TM2["👤 Teammate B"]
    end

    TM1 -->|"💬 'Deploy hotfix to staging'"| APP
    TM2 -->|"💬 'Run tests on backend'"| APP
    YOU -.->|"offline"| APP

    APP --> PO["🧠 Project Orchestrator"]

    PO --> W1["backend<br/><small>hotfix applied</small>"]
    PO --> W2["infra/staging<br/><small>deployed</small>"]
    PO --> W3["backend/tests<br/><small>test suite run</small>"]

    W1 & W2 -->|"results"| TM1
    W3 -->|"results"| TM2

    style SLACK fill:#F1EFE8,stroke:#5F5E5A
    style APP fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style YOU fill:#FAEEDA,stroke:#854F0B,color:#633806
    style TM1 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style TM2 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style PO fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style W1 fill:#CECBF6,stroke:#534AB7,color:#26215C
    style W2 fill:#CECBF6,stroke:#534AB7,color:#26215C
    style W3 fill:#CECBF6,stroke:#534AB7,color:#26215C
```

**No handoff required.** The orchestrator already knows every project's structure via `CLAUDE.md` files and workspace configurations. A teammate doesn't need your local environment, your CLI session, or your explanation of "how things are set up." They just type a message in the channel.

| Scenario | Without Tunnels | With Tunnels |
|----------|----------------|--------------|
| You're on vacation | Team waits or struggles with unfamiliar setup | Team messages the channel, orchestrator handles it |
| New team member joins | Needs onboarding on every project's tooling | Posts in the channel, gets results immediately |
| Urgent hotfix at 3 AM | Someone must SSH in and run commands manually | Anyone in the channel triggers the full pipeline |
| Knowledge transfer | Docs, meetings, shadowing sessions | The orchestrator *is* the institutional knowledge |

> **One app. One channel. The whole team.** The orchestrator doesn't care who's asking — it routes to the right project, builds the execution plan, and delegates to workspace agents. Your team's velocity is no longer bottlenecked by any single person's availability.

---

## How Delegation Works

The core value of Claude-Code-Tunnels is **delegation** — even with dozens of projects and workspaces, the PO analyzes a single natural-language request, identifies the right targets, builds a dependency-aware execution plan, and delegates each piece to the appropriate workspace agent. You never have to specify which project or workspace to touch.

Two properties make this scale:

**1. Isolated sessions per workspace.** Every delegation spawns a *fresh* Claude session with `cwd=workspace/` and loads only that workspace's `.claude/` settings and memory. Each agent works with full focus on exactly one workspace — no context bleed between workspaces, no shared state.

**2. Unbounded tree depth.** One channel connection is all you need. Add more projects, add more workspaces inside them, add remote workspaces on other machines — the tree can grow arbitrarily deep. The PO discovers structure at runtime by reading `CLAUDE.md` files, so there's nothing to reconfigure as the tree grows.

### Delegation Flow

```mermaid
sequenceDiagram
    actor User
    participant CH as Channel Adapter
    participant CG as ConfirmGate
    participant RT as Router · Sonnet
    participant PO as PO · Opus
    participant EX as Executor
    participant WS as Workspaces
    participant LOG as Task Log

    User->>CH: 💬 message via Slack / Telegram
    CH->>CG: register request
    CG-->>User: "Confirm execution? (yes/cancel)"
    User->>CG: yes

    CG->>RT: confirmed message
    RT->>RT: identify target project(s)
    RT->>PO: project list

    PO->>PO: read CLAUDE.md → analyze dependencies
    PO->>EX: phased execution plan

    rect rgb(225, 245, 238)
        Note over EX,WS: Phase 1 · parallel
        EX->>WS: spawn session (cwd: ws-a/, .claude/ injected)
        EX->>WS: spawn session (cwd: ws-b/, .claude/ injected)
        WS-->>EX: results a, b
    end

    rect rgb(230, 241, 251)
        Note over EX,WS: Phase 2 · with upstream context from Phase 1
        EX->>WS: spawn session (cwd: ws-c/, .claude/ + upstream context)
        WS-->>EX: result c
    end

    rect rgb(250, 238, 218)
        Note over EX,WS: Phase 3 · parallel
        EX->>WS: spawn session (cwd: ws-d/)
        EX->>WS: spawn session (cwd: ws-e/)
        WS-->>EX: results d, e
    end

    EX->>LOG: write to .tasks/{date}/{project}/
    LOG-->>CH: formatted results
    CH-->>User: 📤 results via channel
```

> **Key insight**: Phase 1 workspaces run **in parallel**. Phase 2 waits for Phase 1 to complete and receives its results as **upstream context**. This means downstream workspaces always have the full picture of what changed upstream.

### Workspace Structure

The PO delegates across multiple projects and workspaces. Each project contains independent workspaces that can be targeted individually or as a group:

```mermaid
graph TB
    PO["🧠 Project Orchestrator"]

    subgraph PA["project-alpha"]
        PA_BE["backend<br/><small>API, auth</small>"]
        PA_FE["frontend<br/><small>UI, auth-ui</small>"]
        PA_INFRA["infra<br/><small>staging, CD</small>"]
        PA_DB["db<br/><small>migrations</small>"]
        PA_QA["qa<br/><small>integration, e2e</small>"]
    end

    subgraph PB["project-beta"]
        PB_API["api-server<br/><small>REST endpoints</small>"]
        PB_WORKER["worker<br/><small>Background jobs</small>"]
        PB_CFG["shared-config"]
    end

    subgraph SL["shared-lib"]
        SL_CORE["core<br/><small>Utility v2</small>"]
        SL_TYPES["types<br/><small>TS definitions</small>"]
    end

    subgraph REMOTE["remote workspaces ☁️"]
        R_K8S["k8s-staging<br/><small>kubectl listener</small>"]
        R_HOST["remote-host-a<br/><small>SSH listener:9100</small>"]
    end

    PO -->|"delegate"| PA
    PO -->|"delegate"| PB
    PO -->|"delegate"| SL
    PO -->|"delegate via HTTP"| REMOTE

    SL_CORE -.->|"imports"| PA_BE
    SL_CORE -.->|"imports"| PB_API

    style PA fill:#E1F5EE,stroke:#0F6E56
    style PB fill:#E6F1FB,stroke:#185FA5
    style SL fill:#FAECE7,stroke:#993C1D
    style REMOTE fill:#FAEEDA,stroke:#854F0B
    style PO fill:#EEEDFE,stroke:#534AB7
```

### Delegation Scenarios

Below are four real-world scenarios showing how a single message gets decomposed into phased, dependency-aware workspace tasks.

#### Scenario 1 — Multi-project deployment

> **Slack**: _"Add an auth module to the backend API, integrate the login UI on the frontend, then deploy to staging"_

```mermaid
flowchart LR
    subgraph "Phase 1 · parallel"
        A1["backend/auth<br/><small>JWT auth module</small>"]
        A2["backend/api<br/><small>apply auth guard</small>"]
    end

    subgraph "Phase 2 · sequential"
        B1["frontend/auth-ui<br/><small>login page, token management</small>"]
    end

    subgraph "Phase 3 · parallel"
        C1["infra/staging<br/><small>Docker build, deploy</small>"]
        C2["infra/monitoring<br/><small>health check, alert setup</small>"]
    end

    A1 & A2 -->|"upstream context"| B1
    B1 -->|"build output"| C1 & C2

    style A1 fill:#E1F5EE,stroke:#0F6E56
    style A2 fill:#E1F5EE,stroke:#0F6E56
    style B1 fill:#E6F1FB,stroke:#185FA5
    style C1 fill:#FAEEDA,stroke:#854F0B
    style C2 fill:#FAEEDA,stroke:#854F0B
```

| Phase | Mode | Workspaces | What happens |
|-------|------|------------|-------------|
| 1 | **Parallel** | `backend/auth`, `backend/api` | JWT module + guard applied simultaneously |
| 2 | Sequential | `frontend/auth-ui` | Receives Phase 1 API changes as context |
| 3 | **Parallel** | `infra/staging`, `infra/monitoring` | Deploy + monitoring setup after frontend ready |

#### Scenario 2 — Cross-project refactoring

> **Telegram**: _"Upgrade the shared utility library to v2 and run tests across all dependent projects"_

```mermaid
flowchart LR
    subgraph "Phase 1 · sequential"
        A["shared-lib/core<br/><small>v2 migration, breaking changes</small>"]
    end

    subgraph "Phase 2 · parallel"
        B1["project-alpha/backend<br/><small>apply v2, fix imports</small>"]
        B2["project-alpha/frontend<br/><small>apply v2, fix type errors</small>"]
        B3["project-beta/api-server<br/><small>apply v2, compatibility patch</small>"]
    end

    subgraph "Phase 3 · parallel"
        C1["project-alpha/backend<br/><small>unit + integration tests</small>"]
        C2["project-alpha/frontend<br/><small>E2E tests</small>"]
        C3["project-beta/api-server<br/><small>full test suite</small>"]
    end

    A -->|"change list"| B1 & B2 & B3
    B1 --> C1
    B2 --> C2
    B3 --> C3

    style A fill:#FAECE7,stroke:#993C1D
    style B1 fill:#E6F1FB,stroke:#185FA5
    style B2 fill:#E6F1FB,stroke:#185FA5
    style B3 fill:#E6F1FB,stroke:#185FA5
    style C1 fill:#FAEEDA,stroke:#854F0B
    style C2 fill:#FAEEDA,stroke:#854F0B
    style C3 fill:#FAEEDA,stroke:#854F0B
```

The PO identifies that `shared-lib` must be updated **first**, then fans out to all dependent projects **in parallel**, and finally runs each project's test suite.

#### Scenario 3 — Remote workspace orchestration

> **Telegram**: _"Update the main server API and apply the changes to the K8s staging pod"_

```mermaid
flowchart LR
    subgraph "Phase 1 · local"
        A["main-server/api<br/><small>endpoint changes, schema migration</small>"]
    end

    subgraph "Phase 2 · remote (kubectl)"
        B["k8s-staging/deploy<br/><small>image build, rolling update</small>"]
    end

    subgraph "Phase 3 · mixed"
        C1["k8s-staging/smoke-test ☁️<br/><small>health check, smoke tests</small>"]
        C2["main-server/docs<br/><small>auto-update API docs</small>"]
    end

    A -->|"HTTP → remote listener"| B
    B -->|"deploy confirmed"| C1 & C2

    style A fill:#E1F5EE,stroke:#0F6E56
    style B fill:#E6F1FB,stroke:#185FA5
    style C1 fill:#FAEEDA,stroke:#854F0B
    style C2 fill:#FAEEDA,stroke:#854F0B
```

Remote workspaces are delegated over HTTP — the executor sends tasks to a lightweight listener running on the remote host or K8s pod, which runs `claude-agent-sdk query(cwd=...)` locally.

#### Scenario 4 — 4-phase complex pipeline

> **Slack**: _"DB schema change → backend migration → frontend update → full integration tests"_

```mermaid
flowchart TB
    subgraph "Phase 1"
        A["db/migrations<br/><small>schema change SQL, rollback scripts</small>"]
    end

    subgraph "Phase 2 · parallel"
        B1["backend/models<br/><small>update ORM models</small>"]
        B2["backend/api<br/><small>response DTOs, serializers</small>"]
    end

    subgraph "Phase 3"
        C["frontend/data<br/><small>regenerate API client, update components</small>"]
    end

    subgraph "Phase 4 · parallel"
        D1["qa/integration<br/><small>integration test suite</small>"]
        D2["qa/e2e<br/><small>E2E scenario tests</small>"]
    end

    A -->|"migration result"| B1 & B2
    B1 & B2 -->|"API changes"| C
    C -->|"full integration"| D1 & D2

    style A fill:#E1F5EE,stroke:#0F6E56
    style B1 fill:#E6F1FB,stroke:#185FA5
    style B2 fill:#E6F1FB,stroke:#185FA5
    style C fill:#FAEEDA,stroke:#854F0B
    style D1 fill:#FCEBEB,stroke:#A32D2D
    style D2 fill:#FCEBEB,stroke:#A32D2D
```

Each phase strictly depends on the previous one. The PO ensures that no workspace starts until its upstream dependencies are fully resolved and their context is passed down.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/matteblack9/claude-code-tunnels.git
cd claude-code-tunnels

# 2. Install
chmod +x install.sh && ./install.sh

# 3. Set up from your project directory
cd /path/to/your/projects
/setup-orchestrator
```

The `/setup-orchestrator` command interactively guides you through:
1. Enter project root path
2. Copy orchestrator code
3. Auto-discover workspaces
4. Connect preferred channel (Slack/Telegram)
5. Test the connection

---

## Commands

| Command | Description |
|---------|-------------|
| `/setup-orchestrator` | Full install wizard — copy code, discover workspaces, connect channels |
| `/connect-slack` | Add a Slack channel to an existing orchestrator |
| `/connect-telegram` | Add a Telegram channel to an existing orchestrator |
| `/setup-remote-project` | Deploy listener to remote host (SSH/kubectl) to access remote projects |
| `/setup-remote-workspace` | Connect a specific remote workspace to the orchestrator |

---

## Architecture

### Component Structure

```
your-projects/
├── orchestrator/                 # Core engine
│   ├── __init__.py              # Config loading, JSON extraction
│   ├── main.py                  # Entry point (starts enabled channels)
│   ├── server.py                # ConfirmGate, handle_request, format_results
│   ├── router.py                # Lightweight project identification (Sonnet)
│   ├── po.py                    # Execution plan generation (Opus)
│   ├── executor.py              # Phase-by-phase workspace execution
│   ├── direct_handler.py        # Non-project task handling (customizable)
│   ├── task_log.py              # .tasks/ logging and archival
│   ├── sanitize.py              # Prompt injection defense
│   ├── http_api.py              # External HTTP gateway
│   ├── channel/
│   │   ├── base.py              # Abstract channel + session state machine
│   │   ├── session.py           # Per-source conversation tracking
│   │   ├── slack.py             # Slack Socket Mode + Web API
│   │   └── telegram.py          # Telegram long polling + Bot API
│   └── remote/
│       ├── listener.py          # HTTP listener for remote workspaces
│       └── deploy.py            # SSH/kubectl deployment helper
├── orchestrator.yaml             # Configuration file
├── start-orchestrator.sh         # Start script
├── ARCHIVE/                      # Credentials (never commit)
├── .tasks/                       # Execution logs (auto-generated)
├── .claude/rules/                # Orchestrator behavior rules
├── CLAUDE.md                     # Project-level instructions
├── project-a/                    # Project folder
│   ├── CLAUDE.md
│   └── workspace-1/
└── project-b/
    └── ...
```

### Agent Model Strategy

| Agent | Model | Max Turns | Role |
|-------|-------|-----------|------|
| Router | Sonnet | 8 | Fast project identification |
| PO | Opus | 15 | Deep planning with dependency analysis |
| Executor | Default | 100 | Full workspace code modification |
| DirectHandler | Sonnet | 30 | Handle other tasks (outside workspaces) |
| JSON Repair | Haiku | 1 | Cost-efficient malformed JSON recovery |

### Session State Machine (2-Step Confirmation)

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> PENDING_CONFIRM : user message → create_request()

    state PENDING_CONFIRM {
        direction LR
        [*] --> wait_1st : 1st confirm\n"Did I understand correctly?"
    }

    PENDING_CONFIRM --> IDLE : "cancel"
    PENDING_CONFIRM --> IDLE : other text → treat as new request
    PENDING_CONFIRM --> IDLE : "yes" → clarification_needed

    PENDING_CONFIRM --> AWAITING_FOLLOWUP : "yes" → direct_answer\n(no code change)
    PENDING_CONFIRM --> AWAITING_FOLLOWUP : "yes" → direct_request\n(execute immediately)

    PENDING_CONFIRM --> PENDING_EXEC_CONFIRM : "yes" → planned\n(workspace modification)

    state PENDING_EXEC_CONFIRM {
        direction LR
        [*] --> wait_2nd : 2nd confirm\nshow execution plan
    }

    PENDING_EXEC_CONFIRM --> EXECUTING : "yes" → execute plan
    PENDING_EXEC_CONFIRM --> IDLE : "cancel" → discard plan
    PENDING_EXEC_CONFIRM --> IDLE : other text → discard plan

    EXECUTING --> AWAITING_FOLLOWUP : results sent

    AWAITING_FOLLOWUP --> IDLE : "done" / "end" → reset session
    AWAITING_FOLLOWUP --> IDLE : other text → new request\n(context retained)
```

The 2-step confirmation ensures that:
- **1st confirm** (`PENDING_CONFIRM`): User verifies the request was understood correctly
- **2nd confirm** (`PENDING_EXEC_CONFIRM`, workspace modifications only): User reviews the execution plan before code changes are made
- Non-modifying requests (`direct_answer`, `direct_request`) skip the 2nd confirm and go straight to `AWAITING_FOLLOWUP`

### Execution Flow

1. **Message Received** — delivered via channel adapter (Slack/Telegram)
2. **ConfirmGate** — register request, ask user for confirmation
3. **Router** (Sonnet) — identify target project
4. **PO** (Opus) — understand project structure, build phased execution plan
5. **Executor** — run workspaces (parallel within phase, sequential between phases)
6. **Upstream Context** — pass completed phase results to downstream workspaces
7. **Task Log** — record everything in `.tasks/{date}/{project}/`
8. **Return Results** — format and send back to channel

---

## Remote Workspaces

Use remote workspaces when your project lives on a different server or Kubernetes pod:

```
                  Orchestrator Host
                  ┌─────────────┐
                  │  Executor   │
                  │             │──── HTTP ────→ Remote Host A
                  │  query(cwd=)│               ┌──────────┐
                  │  local      │               │ Listener  │
                  │  workspaces │               │ port 9100 │
                  │             │               └──────────┘
                  │             │──── HTTP ────→ K8s Pod B
                  └─────────────┘               ┌──────────┐
                                                │ Listener  │
                                                │ port 9100 │
                                                └──────────┘
```

### Setup

```bash
# Via SSH
/setup-remote-project
# → Enter: host, user, remote path, port

# Via kubectl
/setup-remote-workspace
# → Enter: pod, namespace, remote path, port
```

The listener is a lightweight HTTP server that receives tasks and runs `claude-agent-sdk query(cwd=local_path/)` on the remote server. Remote host requirements:
- Python 3.10+
- `claude-agent-sdk` and `aiohttp` installed
- Claude Code CLI registered in PATH

### Configuration

Register remote workspaces in `orchestrator.yaml`:

```yaml
remote_workspaces:
  - name: my-project/backend    # workspace identifier
    host: 10.0.0.5              # remote host (or pod IP)
    port: 9100                  # listener port
    token: ""                   # optional auth token
```

---

## Channel Setup Guide

### Slack

1. Create app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** → generate app-level token (`xapp-...`)
3. Subscribe to events: `message.channels`, `app_mention`
4. Bot scopes: `chat:write`, `channels:history`, `app_mentions:read`
5. Install to workspace, copy Bot Token (`xoxb-...`)
6. Run `/connect-slack` and enter credentials

### Telegram

1. Open [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token
4. Run `/connect-telegram` and enter the token

---

## Configuration File Reference

`orchestrator.yaml`:

```yaml
# Project root — directory containing your projects
root: /home/user/my-projects

# Credential storage path (never commit)
archive: /home/user/my-projects/ARCHIVE

# Channel configuration
channels:
  slack:
    enabled: false
  telegram:
    enabled: false

# Remote workspaces
remote_workspaces:
  - name: project/workspace
    host: 10.0.0.5
    port: 9100
    token: ""
```

---

## Credential File Format

All credential files use `key : value` format (space on both sides of colon):

```
# ARCHIVE/slack/credentials
app_id : A012345
client_id : 123456.789012
client_secret : your-secret
signing_secret : your-signing-secret
app_level_token : xapp-1-xxx
bot_token : xoxb-xxx

# ARCHIVE/telegram/credentials
bot_token : 123456:ABC-DEF1234
allowed_users : username1, username2
```

---

## Security Model

1. **XML Tag Isolation**: User input wrapped in `<user_message>` tags; system prompt explicitly ignores instructions inside that tag
2. **Filesystem Validation**: Only actual project/workspace directories allowed
3. **Path Traversal Prevention**: Rejects names containing `/`, `\`, `..`
4. **Sensitive Directory Blocking**: `ARCHIVE/`, `.tasks/`, `.git/`, `.claude/` excluded from task targets
5. **Workspace Sandboxing**: Each executor agent restricted to its workspace via `cwd=`

---

## Customization

### Add a Custom Channel

Inherit from `BaseChannel`:

```python
from orchestrator.channel.base import BaseChannel

class MyChannel(BaseChannel):
    channel_name = "mychannel"

    async def _send(self, callback_info, text):
        # Send message however you like
        ...

    async def start(self):
        # Start receiving messages
        ...

    async def stop(self):
        # Cleanup
        ...
```

Register in `main.py`:
```python
my_ch = MyChannel(confirm_gate)
register_channel("mychannel", my_ch)
```

### Customize the Direct Handler

Modify the system prompt in `orchestrator/direct_handler.py` to integrate your organization's tools and APIs (Jira, Confluence, monitoring, etc.).

### Customize Workspace Behavior

Control executor agent behavior via each workspace's `CLAUDE.md`. Add build commands, test instructions, coding conventions, etc.

---

## Dependencies

| Package | Required | When |
|---------|----------|------|
| `claude-agent-sdk` | Always | Core orchestration |
| `aiohttp` | Always | HTTP server/client |
| `pyyaml` | Always | Config file loading |
| `slack-bolt` + `slack-sdk` | If using Slack | Socket Mode |

Telegram uses `aiohttp` (already a required dependency).

---

## Running

```bash
# Foreground (view logs in terminal)
./start-orchestrator.sh --fg

# Background (daemon mode)
./start-orchestrator.sh

# View logs
tail -f /tmp/orchestrator-$(date +%Y%m%d).log

# Stop
kill $(pgrep -f "orchestrator.main")
```

---

## License

MIT
