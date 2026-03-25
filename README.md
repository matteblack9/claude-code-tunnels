# Claude-Code-Tunnels (Micro-Agent Architecture)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-CLI-blueviolet.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Slack](https://img.shields.io/badge/Channel-Slack-4A154B.svg?logo=slack)](https://api.slack.com/apps)
[![Telegram](https://img.shields.io/badge/Channel-Telegram-26A5E4.svg?logo=telegram)](https://core.telegram.org/bots)

**One channel connection. Unlimited projects. Every workspace runs in its own isolated session.**

Claude-Code-Tunnels is a plugin that creates a **Project Orchestrator (PO)** layer on top of [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code). Send a message from Slack or Telegram — the orchestrator routes to the right projects, plans dependency-aware phases, and delegates each task to a **fresh, isolated Claude session** scoped to that workspace's `.claude/` context. Add as many projects and workspaces as you want: one channel connection scales to any tree depth.

---

## Micro-Agent Architecture (MAA)

Just as **Microservice Architecture (MSA)** decomposed the monolith into independently deployable services — each with its own database, its own boundary, its own scaling — Claude-Code-Tunnels decomposes the single AI session into independently executing **micro-agents**, each with its own workspace, its own `.claude/` context, and its own session lifecycle.

We call this pattern **Micro-Agent Architecture (MAA)**.

```mermaid
graph LR
    subgraph MSA["Microservice Architecture · MSA"]
        MONO["🧱 Monolith<br/><small>single deploy</small>"]

        MONO -->|"decompose"| US
        MONO -->|"decompose"| OS
        MONO -->|"decompose"| AS

        subgraph SB["isolated service boundaries"]
            US["User service"] --> US_DB[("DB")]
            OS["Order service"] --> OS_DB[("DB")]
            AS["Auth service"] --> AS_DB[("DB")]
        end
    end

    style MSA fill:#E1F5EE,stroke:#0F6E56
    style SB fill:#E6F1FB,stroke:#185FA5
    style MONO fill:#F1EFE8,stroke:#5F5E5A,color:#444441
    style US fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style OS fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style AS fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style US_DB fill:#FAEEDA,stroke:#854F0B,color:#633806
    style OS_DB fill:#FAEEDA,stroke:#854F0B,color:#633806
    style AS_DB fill:#FAEEDA,stroke:#854F0B,color:#633806
```

> **monolith ≡ single session · microservice ≡ micro-agent · DB ≡ `.claude/`**

```mermaid
graph LR
    subgraph MAA["Micro-Agent Architecture · MAA"]
        SINGLE["🤖 Single session<br/><small>shared context</small>"]

        SINGLE -->|"decompose"| WA
        SINGLE -->|"decompose"| WB
        SINGLE -->|"decompose"| WC

        subgraph IB["isolated session boundaries"]
            WA["workspace-a agent"] --> WA_CTX[(".claude/")]
            WB["workspace-b agent"] --> WB_CTX[(".claude/")]
            WC["workspace-c agent"] --> WC_CTX[(".claude/")]
        end
    end

    style MAA fill:#EEEDFE,stroke:#534AB7
    style IB fill:#E6F1FB,stroke:#185FA5
    style SINGLE fill:#F1EFE8,stroke:#5F5E5A,color:#444441
    style WA fill:#CECBF6,stroke:#534AB7,color:#26215C
    style WB fill:#CECBF6,stroke:#534AB7,color:#26215C
    style WC fill:#CECBF6,stroke:#534AB7,color:#26215C
    style WA_CTX fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style WB_CTX fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style WC_CTX fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

### Core Principles — Shared Between MSA and MAA

| Principle | MSA | MAA |
|-----------|-----|-----|
| **Unit of decomposition** | Service | Micro-agent (workspace session) |
| **State ownership** | Each service owns its DB | Each agent loads only its `.claude/` context |
| **Isolation boundary** | Process / container | Fresh Claude session with `cwd=workspace/` |
| **Inter-unit communication** | API calls / message queue | Upstream context passing between phases |
| **Orchestration** | API gateway / service mesh | Project Orchestrator (PO) |
| **Horizontal scaling** | Add service instances | Add workspaces — tree grows without reconfiguration |
| **Independent deployment** | Deploy one service without touching others | Execute one workspace without affecting others |
| **Failure isolation** | One service crashes, others survive | One agent fails, other phases continue with partial results |

> **The key insight**: In MSA, the API gateway routes requests to the right service. In MAA, the Project Orchestrator routes tasks to the right workspace agent. In both architectures, the orchestration layer is the only component that needs to understand the full topology — individual units focus on their own bounded context.

---

```mermaid
flowchart TB
    INPUT["💬 Slack / Telegram"]
    ADAPTER["Channel Adapter<br/><small>receive message, confirm gate</small>"]
    ROUTER["Router<br/><small>identify target project</small>"]
    PO["PO<br/><small>read CLAUDE.md → build execution plan with phases</small>"]

    INPUT --> ADAPTER --> ROUTER --> PO

    subgraph EXEC["Executor"]
        subgraph P1["Phase 1 · parallel"]
            S_A["Claude session<br/><small>cwd: ws-a/</small>"]
            S_B["Claude session<br/><small>cwd: ws-b/</small>"]
            CTX_A[".claude/<br/><small>memory, rules, skills</small>"]
            CTX_B[".claude/<br/><small>memory, rules, skills</small>"]
            S_A -.- CTX_A
            S_B -.- CTX_B
        end

        subgraph P2["Phase 2 · after phase 1, with upstream context"]
            S_C["Claude session<br/><small>cwd: ws-c/</small>"]
            CTX_C[".claude/<br/><small>memory, rules, skills</small>"]
            S_C -.- CTX_C
        end

        P1 -->|"upstream context"| P2
    end

    PO --> EXEC
    EXEC --> LOG["📋 Task Log<br/><small>.tasks/ with 30-day retention</small>"]
    LOG --> OUTPUT["📤 Channel<br/><small>send formatted results back</small>"]

    style INPUT fill:#F1EFE8,stroke:#5F5E5A,color:#444441
    style ADAPTER fill:#E6F1FB,stroke:#185FA5,color:#0C447C
    style ROUTER fill:#E6F1FB,stroke:#185FA5,color:#0C447C
    style PO fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style EXEC fill:#E1F5EE,stroke:#0F6E56
    style P1 fill:#E6F1FB,stroke:#185FA5
    style P2 fill:#FAEEDA,stroke:#854F0B
    style S_A fill:#CECBF6,stroke:#534AB7,color:#26215C
    style S_B fill:#CECBF6,stroke:#534AB7,color:#26215C
    style S_C fill:#CECBF6,stroke:#534AB7,color:#26215C
    style CTX_A fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style CTX_B fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style CTX_C fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style LOG fill:#FAEEDA,stroke:#854F0B,color:#633806
    style OUTPUT fill:#F1EFE8,stroke:#5F5E5A,color:#444441
```

---

## Why This Over Claude Code's Built-in Channels?

Claude Code [recently introduced Channels](https://docs.anthropic.com/en/docs/claude-code/channels) (research preview) — a way to push messages from Telegram/Discord into a running CLI session. Here's why Claude-Code-Tunnels is fundamentally different:

| Feature | Claude Code Channels | Claude Code Tunnels |
|---------|---------------------|---------------------|
| **Architecture** | Single CLI session, single cwd | Always-on server with multi-project orchestration |
| **Session model** | Session-bound (stops when CLI closes) | Background daemon (survives disconnects) |
| **Multi-project** | One session = one project | PO routes to any project, runs multiple in parallel |
| **Workspace orchestration** | None — flat message bridge | Phase-based dependency analysis, parallel execution, upstream context passing |
| **Session isolation** | Shared session for everything | Each workspace gets its own fresh Claude session + `.claude/` context |
| **Scalability** | Single project, single session | Unlimited projects & workspaces; tree grows without reconfiguration |
| **Supported channels** | Telegram, Discord (preview) | **Slack, Telegram** |
| **ConfirmGate** | None | Built-in: user must confirm before execution starts |
| **Task logging** | None | `.tasks/` auto-logging with 30-day retention |
| **Remote workspaces** | Not possible | SSH/kubectl listener for external machines and K8s pods |
| **Conversation memory** | Single session context | Per-source session with turn history and state machine |
| **Custom channels** | Requires `--dangerously-load-development-channels` | Python `BaseChannel` inheritance — add any channel in minutes |
| **Security model** | Sender allowlist only | XML tag isolation + path traversal prevention + prompt injection defense |
| **Runtime** | Requires Bun | Python only (`pip install`) |
| **Enterprise** | Needs org-level `channelsEnabled` toggle | Self-hosted, no org restrictions |
| **Permission model** | Interactive prompts block execution | `bypassPermissions` for unattended operation |

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

```
# 1. Install the plugin
/plugin install claude-tunnels@claude-tunnels

# 2. Go to your project directory and run the setup wizard
cd /path/to/your/projects
/setup-orchestrator
```

The `/setup-orchestrator` command will interactively:
1. Ask for your project root path
2. Copy the orchestrator code
3. Discover your workspaces
4. Connect your preferred channel (Slack/Telegram)
5. Test the connection

---

## Commands

| Command | Description |
|---------|-------------|
| `/setup-orchestrator` | Full installation wizard — copies code, discovers workspaces, connects channels |
| `/connect-slack` | Add Slack channel to an existing orchestrator |
| `/connect-telegram` | Add Telegram channel to an existing orchestrator |
| `/setup-remote-project` | Deploy listener on a remote host (SSH/kubectl) for remote project access |
| `/setup-remote-workspace` | Connect a specific remote workspace to the orchestrator |

---

## Architecture

### Component Overview

```
your-projects/
├── orchestrator/                 # The brain
│   ├── __init__.py              # Config loading, JSON extraction
│   ├── main.py                  # Entry point (starts enabled channels)
│   ├── server.py                # ConfirmGate, handle_request, format_results
│   ├── router.py                # Lightweight project identification (Sonnet)
│   ├── po.py                    # Execution plan generation (Opus)
│   ├── executor.py              # Phase-based workspace execution
│   ├── direct_handler.py        # Non-project tasks (customizable)
│   ├── task_log.py              # .tasks/ logging with retention
│   ├── sanitize.py              # Prompt injection defense
│   ├── http_api.py              # External HTTP gateway
│   ├── channel/
│   │   ├── base.py              # Abstract channel + session state machine
│   │   ├── session.py           # Per-source conversation tracking
│   │   ├── slack.py             # Slack Socket Mode + Web API
│   │   └── telegram.py          # Telegram long-polling + Bot API
│   └── remote/
│       ├── listener.py          # HTTP listener for remote workspaces
│       └── deploy.py            # SSH/kubectl deployment helpers
├── orchestrator.yaml             # Configuration
├── start-orchestrator.sh         # Launch script
├── ARCHIVE/                      # Credentials (never commit)
├── .tasks/                       # Execution logs (auto-generated)
├── .claude/rules/                # Orchestrator behavior rules
├── CLAUDE.md                     # Project-level instructions
├── project-a/                    # Your projects
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
| DirectHandler | Sonnet | 30 | Misc tasks (no workspace) |
| JSON Repair | Haiku | 1 | Cost-effective malformed JSON recovery |

### Session State Machine

```
[User sends message]
    │
[IDLE] → create_request() → send confirm message
    │
[PENDING_CONFIRM] ← user sends "yes" or "cancel"
    ├── "yes"    → confirm() → handle_request()
    ├── "cancel" → cancel request → IDLE
    └── other    → treat as new request
    │
[EXECUTING] ← handle_request() processing
    │
[AWAITING_FOLLOWUP] ← results sent
    ├── "done"/"end" → session cleared
    └── other        → new request (preserves context)
```

### Execution Flow

1. **Message arrives** via channel adapter (Slack/Telegram)
2. **ConfirmGate** registers request, asks user to confirm
3. **Router** (Sonnet) identifies target project(s)
4. **PO** (Opus) reads project structure, creates execution plan with phases
5. **Executor** runs workspaces — parallel within phase, sequential between phases
6. **Upstream context** passes from completed phases to downstream workspaces
7. **Task log** records everything to `.tasks/{date}/{project}/`
8. **Results** formatted and sent back to the channel

---

## Remote Workspaces

When your projects live on different machines or Kubernetes pods, use remote workspaces:

```
                  Orchestrator Host
                  ┌─────────────┐
                  │  Executor    │
                  │              │──── HTTP ────→ Remote Host A
                  │  query(cwd=) │               ┌──────────┐
                  │  for local   │               │ listener  │
                  │  workspaces  │               │ port 9100 │
                  │              │               └──────────┘
                  │              │──── HTTP ────→ K8s Pod B
                  └─────────────┘               ┌──────────┐
                                                │ listener  │
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

The listener is a lightweight HTTP server that receives tasks and executes `claude-agent-sdk query(cwd=local_path/)` on the remote machine. Requirements on the remote host:
- Python 3.10+
- `claude-agent-sdk` and `aiohttp` installed
- Claude Code CLI in PATH

### Config

Remote workspaces are registered in `orchestrator.yaml`:

```yaml
remote_workspaces:
  - name: my-project/backend    # workspace identifier
    host: 10.0.0.5              # remote host (or pod IP)
    port: 9100                  # listener port
    token: ""                   # optional auth token
```

---

## Channel Setup Guides

### Slack

1. Create app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** → generate app-level token (`xapp-...`)
3. Subscribe to events: `message.channels`, `app_mention`
4. Bot scopes: `chat:write`, `channels:history`, `app_mentions:read`
5. Install to workspace, copy Bot Token (`xoxb-...`)
6. Run `/connect-slack` and enter credentials

### Telegram

1. Open [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`, follow prompts
3. Copy the bot token
4. Run `/connect-telegram` and enter the token

---

## Configuration Reference

`orchestrator.yaml`:

```yaml
# Project root — the directory containing your projects
root: /home/user/my-projects

# Credential storage (never commit this)
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

All credential files use `key : value` format (spaces around colon):

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

1. **XML Tag Isolation**: User input wrapped in `<user_message>` tags — system prompts explicitly warn agents to ignore instructions inside these tags
2. **Filesystem Validation**: Only real project/workspace directories are accepted
3. **Path Traversal Prevention**: Names with `/`, `\`, `..` are rejected
4. **Sensitive Directory Blocking**: `ARCHIVE/`, `.tasks/`, `.git/`, `.claude/` blocked from task targeting
5. **Workspace Sandboxing**: Each executor agent is confined to its workspace via `cwd=`

---

## Customization

### Adding a Custom Channel

Inherit from `BaseChannel`:

```python
from orchestrator.channel.base import BaseChannel

class MyChannel(BaseChannel):
    channel_name = "mychannel"

    async def _send(self, callback_info, text):
        # Send message via your transport
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

### Customizing the Direct Handler

Edit `orchestrator/direct_handler.py` to add your organization's tools and APIs to the system prompt. This is where you integrate internal services (Jira, Confluence, monitoring, etc.).

### Customizing Workspace Behavior

Each workspace's `CLAUDE.md` controls how the executor agent behaves. Add build commands, test instructions, coding conventions, etc.

---

## Dependencies

| Package | Required | When |
|---------|----------|------|
| `claude-agent-sdk` | Always | Core orchestration |
| `aiohttp` | Always | HTTP server/client |
| `pyyaml` | Always | Config loading |
| `slack-bolt` + `slack-sdk` | If Slack | Socket Mode |

Telegram uses `aiohttp` (already required).

---

## Running

```bash
# Foreground (see logs in terminal)
./start-orchestrator.sh --fg

# Background (daemon mode)
./start-orchestrator.sh

# Check logs
tail -f /tmp/orchestrator-$(date +%Y%m%d).log

# Stop
kill $(pgrep -f "orchestrator.main")
```

---

## Scaling Beyond — Hierarchical Orchestration

A single PO manages one project tree. But what if your organization has dozens of independent systems, spread across teams, divisions, even regions — each with its own orchestrator?

**Stack another layer.** And another. And another. The orchestrator pattern is recursive: any orchestrator can sit above other orchestrators. There is no depth limit. One channel connection at the top cascades through as many layers as your organization needs.

```mermaid
flowchart TB
    USER["💬 Single channel connection<br/><small>Slack / Telegram</small>"]

    INF["⋮<br/><small>add more layers above — no limit</small>"]

    ON1["🧠 Orchestrator · layer N+1<br/><small>routes across divisions</small>"]

    USER -.-> INF -.-> ON1

    ON1 --> OA["🧠 Orchestrator<br/><small>Infrastructure</small>"]
    ON1 --> OB["🧠 Orchestrator<br/><small>Product</small>"]
    ON1 --> OC["🧠 Orchestrator<br/><small>ML Platform</small>"]

    subgraph SA["Infrastructure"]
        OA --> POA1["PO · networking"]
        OA --> POA2["PO · compute"]
        POA1 --> WA1["terraform"]
        POA1 --> WA2["vpc-config"]
        POA2 --> WA3["k8s"]
        POA2 --> WA4["monitoring"]
    end

    subgraph SB["Product"]
        OB --> POB1["PO · backend"]
        OB --> POB2["PO · frontend"]
        POB1 --> WB1["api"]
        POB1 --> WB2["auth"]
        POB2 --> WB3["web-ui"]
        POB2 --> WB4["mobile"]
    end

    subgraph SC["ML Platform"]
        OC --> POC1["PO · training"]
        OC --> POC2["PO · serving"]
        POC1 --> WC1["model-train"]
        POC1 --> WC2["eval"]
        POC2 --> WC3["inference"]
        POC2 --> WC4["a-b-test"]
    end

    style USER fill:#F1EFE8,stroke:#5F5E5A,color:#444441
    style INF fill:none,stroke:none,color:#888780
    style ON1 fill:#FAEEDA,stroke:#854F0B,color:#633806

    style OA fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style OB fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    style OC fill:#EEEDFE,stroke:#534AB7,color:#3C3489

    style SA fill:#E1F5EE,stroke:#0F6E56
    style SB fill:#E6F1FB,stroke:#185FA5
    style SC fill:#FAECE7,stroke:#993C1D

    style POA1 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style POA2 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style POB1 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style POB2 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style POC1 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
    style POC2 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C

    style WA1 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style WA2 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style WA3 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style WA4 fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style WB1 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style WB2 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style WB3 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style WB4 fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style WC1 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
    style WC2 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
    style WC3 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
    style WC4 fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
```

The pattern is fractal:

```
Channel ─→ Layer 0: Global Orchestrator
              ├─→ Layer 1: Division Orchestrator (Korea)
              │      ├─→ Layer 2: System PO (Product)
              │      │      ├─→ workspace: backend
              │      │      └─→ workspace: frontend
              │      └─→ Layer 2: System PO (Infrastructure)
              │             ├─→ workspace: k8s
              │             └─→ workspace: monitoring
              ├─→ Layer 1: Division Orchestrator (US)
              │      ├─→ Layer 2: System PO (Data Platform)
              │      └─→ Layer 2: System PO (ML Platform)
              ├─→ Layer 1: Division Orchestrator (EU)
              │      └─→ ...
              └─→ ...any depth
```

This is the same principle that makes MAA scale: **each layer only knows about its direct children**. The Global Orchestrator doesn't know what workspaces exist inside Korea's Product system — it only knows that the Korea Division Orchestrator handles Korean operations. Korea's Division Orchestrator doesn't know the US division exists. Bounded context at every level, just like microservices behind an API gateway hierarchy.

> **One channel. One message. Any depth.** _"Retrain the recommendation model on the US ML platform, update the Korean product backend to consume the new API, and roll out both to their respective staging clusters"_ — the global layer fans out to US and Korea division orchestrators, each cascading down through their system POs to the right workspaces.

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/my-feature`
3. **Commit** your changes: `git commit -m "feat: add my feature"`
4. **Push** to the branch: `git push origin feat/my-feature`
5. **Open** a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages. For major changes, open an issue first to discuss what you'd like to change.

### Areas We'd Love Help With

- New channel adapters (Discord, Microsoft Teams, etc.)
- Remote workspace listeners for additional runtimes (Docker, ECS, etc.)
- Test coverage and CI/CD pipeline
- Documentation translations

---

## Roadmap

- [ ] **Microsoft Teams channel adapter** — extend beyond Slack/Telegram
- [ ] **Discord channel adapter** — extend beyond Slack/Telegram
- [ ] **Web dashboard** — real-time task monitoring and workspace status UI
- [ ] **Meta-Orchestrator** — hierarchical PO stacking for cross-system orchestration (see [Scaling Beyond](#scaling-beyond--hierarchical-orchestration))
- [ ] **Workspace dependency graph** — auto-detect inter-workspace imports and infer phase ordering
- [ ] **Rollback support** — automatic git-based rollback on workspace execution failure
- [ ] **Plugin marketplace** — community-contributed channel adapters, direct handlers, and workspace templates
- [ ] **Streaming results** — real-time progress updates sent back to the channel during execution
- [ ] **Cost tracking** — per-task token usage and model cost breakdown in task logs

---

## License

MIT License
