# Micro Agent Manager (Micro-Agent Architecture)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Slack](https://img.shields.io/badge/Channel-Slack-4A154B.svg?logo=slack)](https://api.slack.com/apps)
[![Telegram](https://img.shields.io/badge/Channel-Telegram-26A5E4.svg?logo=telegram)](https://core.telegram.org/bots)
[![Codex SDK](https://img.shields.io/badge/Runtime-Codex-111111.svg)](https://developers.openai.com/codex/sdk)
[![OpenCode SDK](https://img.shields.io/badge/Runtime-OpenCode-0F7B6C.svg)](https://opencode.ai/docs/sdk/)

**One channel connection. One Project Orchestrator. Every workspace runs through its own isolated Workspace Orchestrator.**

Micro Agent Manager is an orchestration layer for project trees. A message arrives from Slack or Telegram, the **Project Orchestrator (PO)** routes it, builds a dependency-aware execution plan, and delegates each workspace task to a **Workspace Orchestrator (WO)**.

This version keeps the Python control plane, but expands execution beyond a single-runtime model:

- `claude` runs through the existing Python `claude-agent-sdk`
- `codex` runs through a local Node bridge that uses the official `@openai/codex-sdk`
- `opencode` runs through the same bridge with `@opencode-ai/sdk`
- initial setup is handled by a Textual TUI that proposes the `PO` root, `ARCHIVE` path, workspace candidates, WO runtime assignments, and root guidance files

Guidance is runtime-aware:

- `claude` prefers `CLAUDE.md` and existing `.claude/` memory/rules
- `codex` prefers `AGENTS.md` and explicit repo instructions
- `opencode` also works best with `AGENTS.md`, and requires provider login before execution

Short glossary:

- **PO**: the control plane that routes requests, builds phases, and coordinates execution
- **Workspace**: a real directory that contains code or documents
- **WO**: the runtime worker assigned to one workspace
- **Remote Workspace**: a workspace executed through the remote listener on another host or pod

---

## Micro-Agent Architecture (MAA)

Just as **Microservice Architecture (MSA)** decomposed the monolith into independently deployable services, Micro Agent Manager decomposes one large assistant session into independently executing workspace workers. Each WO owns one workspace, one runtime, and one bounded context.

We call this pattern **Micro-Agent Architecture (MAA)**.

```mermaid
graph LR
    subgraph MSA["Microservice Architecture · MSA"]
        MONO["Monolith<br/><small>single deploy</small>"]

        MONO -->|"decompose"| US
        MONO -->|"decompose"| OS
        MONO -->|"decompose"| AS

        subgraph SB["isolated service boundaries"]
            US["User service"] --> US_DB[("DB")]
            OS["Order service"] --> OS_DB[("DB")]
            AS["Auth service"] --> AS_DB[("DB")]
        end
    end
```

```mermaid
graph LR
    subgraph MAA["Micro-Agent Architecture · MAA"]
        SINGLE["Single runtime session<br/><small>shared context</small>"]

        SINGLE -->|"decompose"| WA
        SINGLE -->|"decompose"| WB
        SINGLE -->|"decompose"| WC

        subgraph IB["isolated workspace boundaries"]
            WA["WO: backend"] --> WA_CTX["AGENTS.md / CLAUDE.md / .claude"]
            WB["WO: frontend"] --> WB_CTX["AGENTS.md / CLAUDE.md / .claude"]
            WC["WO: staging"] --> WC_CTX["runtime config + remote listener"]
        end
    end
```

> **monolith ≡ single session · microservice ≡ workspace worker · DB ≡ workspace guidance + runtime boundary**

### Core Principles — Shared Between MSA and MAA

| Principle | MSA | MAA |
|-----------|-----|-----|
| **Unit of decomposition** | Service | Workspace worker (`WO`) |
| **State ownership** | Each service owns its DB | Each WO owns its workspace guidance and runtime |
| **Isolation boundary** | Process / container | Fresh runtime session with `cwd=workspace/` |
| **Inter-unit communication** | API calls / message queue | Upstream context passed between phases |
| **Orchestration** | API gateway / service mesh | Project Orchestrator (`PO`) |
| **Scaling** | Add service instances | Add workspaces or remote listeners |
| **Failure isolation** | One service fails, others continue | One WO can fail without collapsing the whole plan |

```mermaid
flowchart TB
    INPUT["Slack / Telegram"]
    ADAPTER["Channel Adapter<br/><small>receive message, confirm gate</small>"]
    ROUTER["Router<br/><small>identify target workspace set</small>"]
    PO["PO<br/><small>analyze request and build phased plan</small>"]

    INPUT --> ADAPTER --> ROUTER --> PO

    subgraph EXEC["Executor"]
        subgraph P1["Phase 1 · parallel"]
            W1["WO: backend<br/><small>runtime = claude</small>"]
            W2["WO: auth<br/><small>runtime = codex</small>"]
        end

        subgraph P2["Phase 2 · downstream"]
            W3["WO: staging<br/><small>runtime = opencode or remote</small>"]
        end

        P1 -->|"upstream context"| P2
    end

    PO --> EXEC
    EXEC --> LOG["Task Log<br/><small>.tasks/ with retention</small>"]
    LOG --> OUTPUT["Channel response"]
```

---

## Why This Over Claude Code's Built-in Channels?

Claude Code has a Channels feature that forwards chat messages into a running CLI session. Micro Agent Manager solves a different problem.

| Feature | Claude Code Channels | Micro Agent Manager |
|---------|---------------------|---------------------|
| **Architecture** | Single CLI session, single cwd | Always-on PO with phased workspace orchestration |
| **Session model** | Bound to a running session | Background daemon with per-workspace execution |
| **Workspace orchestration** | None | Phase-based planning with upstream context passing |
| **Session isolation** | Shared session | One isolated WO per workspace |
| **Runtime** | Single Claude session bridge | `claude`, `codex`, `opencode` through one control plane |
| **Remote workspaces** | Not supported | HTTP listener for remote hosts and pods |
| **Task logging** | None | `.tasks/` logging with runtime metadata |
| **Confirm gate** | None | Built-in confirm/cancel flow |
| **Setup** | Connect a channel to one session | TUI discovers PO root, workspaces, and runtimes |

**In short**: Channels is a message bridge into one session. Micro Agent Manager is an orchestration layer that can coordinate multiple workspaces and multiple runtimes from one shared channel.

---

## Team Collaboration — Shared Channel, Zero Handoff

Traditional setups tie the assistant to one person's laptop or one long-running terminal session. Micro Agent Manager flips that: the orchestrator lives in the shared channel, not in one person's shell.

```mermaid
flowchart TB
    subgraph SLACK["Shared channel"]
        APP["Orchestrator app"]
        T1["Teammate A"]
        T2["Teammate B"]
        Y["You (offline)"]
    end

    T1 -->|"Deploy staging"| APP
    T2 -->|"Run backend tests"| APP
    Y -.->|"away"| APP

    APP --> PO["PO"]
    PO --> W1["WO: backend"]
    PO --> W2["WO: staging"]
    PO --> W3["WO: qa"]

    W1 --> T1
    W2 --> T1
    W3 --> T2
```

**No handoff required.** The orchestrator already knows workspace structure through `orchestrator.yaml`, shared instructions in `AGENTS.md`, Claude-specific context in `CLAUDE.md` or `.claude/`, and workspace-specific runtime settings. A teammate does not need your local terminal state or your memory of "how this repo works."

| Scenario | Without Tunnels | With Tunnels |
|----------|----------------|--------------|
| You're on vacation | Team waits or guesses | Team uses the shared channel |
| New team member joins | Needs project-by-project onboarding | Asks the channel and gets routed correctly |
| Urgent hotfix at 3 AM | Someone SSHs in and runs commands manually | Anyone with channel access can trigger the pipeline |

---

## How Delegation Works

The PO reads a natural-language request, decides which workspaces are involved, determines dependency order, and hands each workspace-specific task to a WO.

Two properties make that useful:

**1. Isolated execution per workspace.** Each WO runs in one workspace with one runtime and one working directory.

**2. Phase-aware coordination.** Workspaces in the same phase run in parallel. Downstream phases receive upstream summaries as context.

**3. Explicit workspace registration.** The setup TUI proposes workspace candidates, and the final `workspaces:` block becomes the source of truth for planning and execution.

### Delegation Flow

```mermaid
sequenceDiagram
    actor User
    participant CH as Channel Adapter
    participant CG as ConfirmGate
    participant RT as Router
    participant PO as PO
    participant EX as Executor
    participant WO as WOs
    participant LOG as Task Log

    User->>CH: message
    CH->>CG: store pending request
    CG-->>User: confirm?
    User->>CG: yes
    CG->>RT: confirmed request
    RT->>PO: target workspaces
    PO->>PO: plan phases
    PO->>EX: phased execution plan
    EX->>WO: phase 1 in parallel
    WO-->>EX: results
    EX->>WO: phase 2 with upstream context
    WO-->>EX: results
    EX->>LOG: write .tasks log
    LOG-->>CH: formatted output
    CH-->>User: result
```

### Workspace Structure

The current branch is optimized for one `PO` root with an explicit workspace registry:

```text
po-root/
├── orchestrator/
├── orchestrator.yaml
├── start-orchestrator.sh
├── ARCHIVE/
├── backend/
├── frontend/
└── services/
    └── staging/
```

The `workspaces:` block in `orchestrator.yaml` is the preferred source of truth. Legacy directory scanning and `remote_workspaces:` fallback still exist so older setups keep working.

### Delegation Scenarios

Below are three concrete examples of how one request becomes phased WO execution.

#### Scenario 1 — Multi-workspace feature and deploy

> **Slack**: _"Add auth to the backend, wire the frontend login flow, then deploy staging"_

```mermaid
flowchart LR
    subgraph P1["Phase 1 · parallel"]
        A1["backend/api"]
        A2["backend/auth"]
    end

    subgraph P2["Phase 2"]
        B1["frontend/web"]
    end

    subgraph P3["Phase 3 · parallel"]
        C1["services/staging"]
        C2["qa/smoke"]
    end

    A1 -->|"upstream context"| B1
    A2 -->|"upstream context"| B1
    B1 -->|"deploy input"| C1
    C1 -->|"release info"| C2
```

#### Scenario 2 — Shared library upgrade across runtimes

> **Telegram**: _"Upgrade the shared types package and update all dependent workspaces"_

```mermaid
flowchart LR
    subgraph P1["Phase 1"]
        A["shared/types"]
    end

    subgraph P2["Phase 2 · parallel"]
        B1["backend/api<br/><small>WO runtime = codex</small>"]
        B2["frontend/web<br/><small>WO runtime = claude</small>"]
        B3["worker/jobs<br/><small>WO runtime = opencode</small>"]
    end

    subgraph P3["Phase 3 · parallel"]
        C1["backend/tests"]
        C2["frontend/tests"]
        C3["worker/tests"]
    end

    A --> B1
    A --> B2
    A --> B3
    B1 --> C1
    B2 --> C2
    B3 --> C3
```

#### Scenario 3 — Local to remote handoff

> **Slack**: _"Change the deployment manifest and roll it out to the remote staging workspace"_

```mermaid
flowchart LR
    subgraph P1["Phase 1 · local"]
        A["infra/manifests"]
    end

    subgraph P2["Phase 2 · remote"]
        B["services/staging<br/><small>WO mode = remote</small>"]
    end

    subgraph P3["Phase 3"]
        C["qa/smoke"]
    end

    A -->|"remote listener payload"| B --> C
```

---

## Quick Start

```bash
git clone https://github.com/matteblack9/claude-code-tunnels.git
cd claude-code-tunnels

./install.sh
.venv/bin/python -m orchestrator.setup_tui
./start-orchestrator.sh --fg
```

The repository name is still `claude-code-tunnels`; the README title is runtime-neutral because this branch supports multiple coding agents.

The setup TUI:

1. checks whether the current folder already looks like a `PO` root
2. suggests the `PO` root, `ARCHIVE` path, and workspace candidates
3. lets you assign one `WO` per selected workspace
4. writes `orchestrator.yaml`, `start-orchestrator.sh`, and root runtime guidance files (`AGENTS.md`, `CLAUDE.md`) when needed
5. shows the exact commands to run next

---

## How To Run

If you are seeing terms like `PO` and `WO` for the first time, read this section as:

- **PO root**: the directory that contains `orchestrator/`, `orchestrator.yaml`, `start-orchestrator.sh`, and `ARCHIVE/`
- **Workspace**: a real target directory such as `backend/` or `services/staging/`
- **WO**: the runtime worker assigned to one workspace

Operationally, the tree looks like this:

```mermaid
flowchart TD
    START["Run start-orchestrator.sh"] --> MAIN["orchestrator.main"]
    MAIN --> CHANNEL["Slack / Telegram adapter"]
    CHANNEL --> GATE["ConfirmGate"]
    GATE --> ROUTER["Router"]
    ROUTER --> PO["PO"]
    PO --> EXEC["Executor"]

    EXEC --> PH1["Phase 1"]
    PH1 --> WO1["WO: ws-a"]
    PH1 --> WO2["WO: ws-b"]
    WO1 --> PH2["Phase 2"]
    WO2 --> PH2
    PH2 --> WO3["WO: ws-c"]

    WO1 --> LOG["Task log"]
    WO2 --> LOG
    WO3 --> LOG
    LOG --> RESP["Formatted channel response"]
    RESP --> CHANNEL
```

After setup has written `orchestrator.yaml` and `start-orchestrator.sh`, run from the `PO` root:

```bash
# Foreground, recommended for first run or debugging
./start-orchestrator.sh --fg

# Background daemon mode
./start-orchestrator.sh

# Re-open setup
.venv/bin/python -m orchestrator.setup_tui

# Follow logs
tail -f /tmp/orchestrator-$(date +%Y%m%d).log

# Stop background execution
kill $(pgrep -f "orchestrator.main")
```

---

## Commands

| Command | Description |
|---------|-------------|
| `.venv/bin/python -m orchestrator.setup_tui` | Full-screen setup wizard for PO/workspace/WO configuration |
| `/setup-orchestrator` | Plugin skill shortcut that launches the setup workflow |
| `/connect-slack` | Add Slack credentials to an existing orchestrator |
| `/connect-telegram` | Add Telegram credentials to an existing orchestrator |
| `/setup-remote-project` | Deploy the remote listener through SSH or kubectl |
| `/setup-remote-workspace` | Register a specific remote workspace |

---

## Architecture

### Component Overview

```text
po-root/
├── orchestrator/
│   ├── __init__.py              # config loading, workspace/runtime resolution
│   ├── main.py                  # entry point
│   ├── server.py                # ConfirmGate, planning, execution flow
│   ├── router.py                # target identification
│   ├── po.py                    # phased execution planning
│   ├── executor.py              # phase-by-phase WO execution
│   ├── direct_handler.py        # non-workspace task handling
│   ├── task_log.py              # .tasks/ writer
│   ├── sanitize.py              # prompt safety checks
│   ├── http_api.py              # optional HTTP surface
│   ├── setup_tui.py             # Textual setup app
│   ├── setup_support.py         # setup discovery and rendering helpers
│   ├── channel/
│   │   ├── base.py              # shared confirm/cancel/session flow
│   │   ├── session.py           # per-source conversation context
│   │   ├── slack.py             # Slack adapter
│   │   └── telegram.py          # Telegram adapter
│   ├── runtime/
│   │   ├── __init__.py          # runtime-neutral execution layer
│   │   └── bridge.py            # persistent Node bridge client
│   └── remote/
│       ├── listener.py          # standalone remote listener
│       └── deploy.py            # SSH/kubectl deployment helper
├── bridge/
│   ├── daemon.mjs               # Node bridge process
│   ├── lib/runtime.mjs          # Codex/OpenCode runtime calls
│   └── tests/runtime.test.mjs
├── templates/
├── skills/
├── orchestrator.yaml
├── start-orchestrator.sh
├── package.json
├── requirements.txt
└── requirements-dev.txt
```

### Multi-Runtime Structure

```mermaid
flowchart TD
    subgraph CHANNELS["Channels"]
        U["Slack / Telegram"]
        CA["Channel adapters"]
    end

    subgraph CONTROL["Python control plane"]
        G["ConfirmGate"]
        R["Router"]
        P["PO"]
        D["Direct handler"]
        E["Executor"]
        L["Task log (.tasks/)"]
    end

    subgraph LOCAL["Local execution"]
        RL["Runtime layer"]
        CSDK["Claude SDK"]
        BR["Node bridge"]
        CX["Codex SDK"]
        OC["OpenCode SDK"]
    end

    subgraph REMOTE["Remote execution"]
        REM["Remote listener"]
        RR["Remote runtime"]
    end

    U --> CA --> G
    G --> R
    R --> P
    R --> D
    P --> E
    D --> CA

    E --> RL
    E --> REM
    RL --> CSDK
    RL --> BR
    BR --> CX
    BR --> OC
    REM --> RR

    CSDK --> L
    CX --> L
    OC --> L
    RR --> L
    L --> CA
```

### Agent Model Strategy

| Role | Default runtime | Max turns | Responsibility |
|------|-----------------|-----------|----------------|
| Router | `claude` | 8 | Fast target identification |
| PO | `claude` | 15 | Phased execution planning |
| Executor | `claude` | 5 | Workspace execution |
| DirectHandler | `claude` | 30 | Non-workspace operations |
| JSON Repair | `claude` | 1 | Malformed JSON recovery |

### Runtime Resolution Order

Runtime selection follows this order:

1. `workspaces[].wo.runtime`
2. `runtime.roles[role]`
3. `runtime.default`
4. fallback `claude`

### Runtime Guidance Files

Runtime guidance is runtime-aware. The same repository can expose different instructions to different coding agents:

| Runtime | Primary guidance | Characteristics | Best use |
|---------|------------------|-----------------|----------|
| `claude` | `CLAUDE.md` and `.claude/` | Hierarchical project memory, rules, and existing Claude workflows are loaded naturally through the Python SDK path | Reusing existing Claude Code project setups without rewriting guidance |
| `codex` | `AGENTS.md` | Works best with explicit repo instructions and structured task framing; the Node bridge is also used for schema-driven output | Shared coding rules, step-by-step repo policies, and structured execution |
| `opencode` | `AGENTS.md` | Similar guidance style to Codex, but requires provider login and runs through the OpenCode SDK session flow | Multi-runtime teams that want one shared instruction file outside the Claude ecosystem |

Supporting files:

| File | Used by | Purpose |
|------|---------|---------|
| `AGENTS.md` | Primarily `codex` and `opencode`; also useful as shared human-readable guidance | Canonical runtime-neutral operating rules |
| `CLAUDE.md` | `claude` | Claude-specific project and workspace guidance |
| `.claude/` | `claude` and legacy Claude setups | Existing Claude memory, rules, and skills |

Recommended pattern:

- Put shared workflow rules, repo conventions, and task expectations in `AGENTS.md`
- Keep `CLAUDE.md` for Claude-specific prompt framing or compatibility with existing Claude projects
- Keep `.claude/` only when you actively rely on Claude memory, rules, or skills

### Session State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> PENDING_CONFIRM : user message

    PENDING_CONFIRM --> IDLE : cancel
    PENDING_CONFIRM --> IDLE : clarification needed
    PENDING_CONFIRM --> AWAITING_FOLLOWUP : direct answer
    PENDING_CONFIRM --> AWAITING_FOLLOWUP : direct request
    PENDING_CONFIRM --> PENDING_EXEC_CONFIRM : planned workspace execution

    PENDING_EXEC_CONFIRM --> EXECUTING : yes
    PENDING_EXEC_CONFIRM --> IDLE : cancel

    EXECUTING --> AWAITING_FOLLOWUP : results sent

    AWAITING_FOLLOWUP --> IDLE : done or end
    AWAITING_FOLLOWUP --> IDLE : new request
```

### Execution Flow

1. A message arrives via Slack or Telegram
2. `ConfirmGate` registers the request and asks for confirmation
3. Router identifies the target workspace set or switches to direct handling
4. `PO` creates a phased execution plan
5. Executor runs WOs phase by phase:
   - parallel within a phase
   - sequential across phases
6. upstream summaries become downstream context
7. results are written to `.tasks/`
8. formatted output is sent back to the channel

---

## Remote Workspaces

When a workspace lives on another machine or Kubernetes pod, use a remote listener.

### Listener Environment

The remote listener understands:

- `LISTENER_CWD`
- `LISTENER_PORT`
- `LISTENER_TOKEN`
- `LISTENER_RUNTIME`

### Setup

```bash
# Via SSH
/setup-remote-project

# Via kubectl
/setup-remote-workspace
```

The deploy helper in `orchestrator/remote/deploy.py` supports both SSH and `kubectl`.

### Config

Preferred new schema:

```yaml
workspaces:
  - id: staging
    path: services/staging
    wo:
      runtime: opencode
      mode: remote
      remote:
        host: 10.0.0.5
        port: 9100
        token: ""
```

Legacy compatibility projection:

```yaml
remote_workspaces:
  - name: staging
    host: 10.0.0.5
    port: 9100
    token: ""
    runtime: opencode
```

### Remote Host Requirements

- Python 3.10+
- `claude-agent-sdk` and `aiohttp` if the remote runtime is `claude`
- `codex` CLI if the remote runtime is `codex`
- `opencode` CLI plus provider credentials if the remote runtime is `opencode`

---

## Channel Setup Guides

### Slack

Slack support exists in `orchestrator/channel/slack.py`, but Slack libraries are optional.

Install them if you want Slack support:

```bash
.venv/bin/pip install slack-bolt slack-sdk
```

Then:

1. create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. enable Socket Mode
3. generate an app-level token with `connections:write`
4. add bot scopes:
   - `chat:write`
   - `channels:history`
   - `groups:history`
   - `im:history`
   - `mpim:history`
   - `app_mentions:read`
5. subscribe to bot events:
   - `message.channels`
   - `message.groups`
   - `message.im`
   - `app_mention`
6. install the app to the workspace
7. write credentials into `ARCHIVE/slack/credentials`

### Telegram

Telegram support is implemented in `orchestrator/channel/telegram.py`.

1. create a bot with [@BotFather](https://t.me/botfather)
2. write `ARCHIVE/telegram/credentials`
3. enable Telegram in `orchestrator.yaml`

---

## Configuration Reference

`orchestrator.yaml` now looks like this:

```yaml
root: /path/to/po-root
archive: /path/to/po-root/ARCHIVE

runtime:
  default: claude
  roles:
    router: claude
    planner: claude
    executor: claude
    direct_handler: claude
    repair: claude

channels:
  slack:
    enabled: false
  telegram:
    enabled: true

workspaces:
  - id: backend
    path: backend
    wo:
      runtime: codex
      mode: local

  - id: staging
    path: services/staging
    wo:
      runtime: opencode
      mode: remote
      remote:
        host: 10.0.0.5
        port: 9100
        token: ""

remote_workspaces:
  - name: staging
    host: 10.0.0.5
    port: 9100
    token: ""
    runtime: opencode
```

Key fields:

- `root`: the PO root
- `archive`: credential storage path
- `runtime.default`: default runtime for roles without explicit overrides
- `runtime.roles`: per-role runtime overrides
- `workspaces[].id`: workspace identifier used by the planner and executor
- `workspaces[].path`: actual workspace path relative to `root`
- `workspaces[].wo.runtime`: runtime for that workspace
- `workspaces[].wo.mode`: `local` or `remote`
- `workspaces[].wo.remote`: remote listener connection information
- `remote_workspaces`: legacy compatibility projection used by older remote lookups

---

## Credential File Format

All credential files use `key : value` format with spaces around the colon.

```text
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

1. **User-controlled input isolation**: channel content is wrapped and handled separately from system instructions
2. **Workspace validation**: only configured or discovered real workspaces are eligible targets
3. **Path traversal prevention**: invalid names and blocked paths are rejected
4. **Sensitive directory blocking**: `ARCHIVE/`, `.tasks/`, `.git/`, `.claude/`, and `orchestrator/` are excluded from targeting
5. **Workspace sandboxing**: each WO executes with its own `cwd`
6. **Channel confirmation**: channel execution is gated by explicit confirm/cancel state

---

## Customization

### Adding a Custom Channel

Inherit from `BaseChannel` in `orchestrator/channel/base.py`:

```python
from orchestrator.channel.base import BaseChannel


class MyChannel(BaseChannel):
    channel_name = "mychannel"

    async def _send(self, callback_info, text):
        ...

    async def start(self):
        ...

    async def stop(self):
        ...
```

Then register it in `orchestrator/main.py`.

### Customizing the Direct Handler

Adjust the system prompt in `orchestrator/direct_handler.py` to integrate your own internal tools or policies.

### Customizing Workspace Behavior

Control WO behavior through guidance files:

- `AGENTS.md` should hold shared repo rules for `codex` and `opencode`, and is the best default for runtime-neutral instructions
- `CLAUDE.md` should hold Claude-specific framing when the `claude` runtime needs extra project context
- `.claude/` should be kept only for Claude memory, rules, and skills you still actively depend on

The setup flow creates root-level `AGENTS.md` and `CLAUDE.md` when missing. In practice, treat `AGENTS.md` as the shared contract across runtimes, then layer Claude-only behavior in `CLAUDE.md` or `.claude/` where necessary.

---

## Dependencies

| Package | Required | When |
|---------|----------|------|
| `claude-agent-sdk` | Always | Claude runtime |
| `aiohttp` | Always | HTTP server/client and remote listener |
| `pyyaml` | Always | Config loading |
| `requests` | If remote deployment helpers are used | SSH and kubectl deployment flows |
| `textual` | Always | Setup TUI |
| `@openai/codex-sdk` | Always after `npm install` | Codex runtime bridge |
| `@opencode-ai/sdk` | Always after `npm install` | OpenCode runtime bridge |
| `slack-bolt` + `slack-sdk` | If Slack | Slack adapter |

Telegram uses `aiohttp`, which is already required.

---

## Running

```bash
# Foreground
./start-orchestrator.sh --fg

# Background
./start-orchestrator.sh

# Logs
tail -f /tmp/orchestrator-$(date +%Y%m%d).log

# Reconfigure
.venv/bin/python -m orchestrator.setup_tui

# Stop
kill $(pgrep -f "orchestrator.main")
```

---

## Scaling Beyond — Hierarchical Orchestration

A single PO manages one project tree. If your organization has multiple systems, each system can run its own orchestrator and a higher-level orchestrator can route across them.

```mermaid
flowchart TB
    USER["Single channel connection"]
    TOP["Global Orchestrator"]
    KOR["Division Orchestrator: Korea"]
    USA["Division Orchestrator: US"]
    PROD["PO: product"]
    INFRA["PO: infrastructure"]
    ML["PO: ml-platform"]

    USER --> TOP
    TOP --> KOR
    TOP --> USA
    KOR --> PROD
    KOR --> INFRA
    USA --> ML
```

The same rule still applies: each layer only needs to know its direct children.

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b codex/my-feature`
3. Commit your changes
4. Push the branch
5. Open a Pull Request

### Areas We'd Love Help With

- new channel adapters
- stronger remote runtime support
- test coverage and CI
- documentation translations

---

## Roadmap

- [ ] Microsoft Teams channel adapter
- [ ] Discord channel adapter
- [ ] Web dashboard for runtime and workspace visibility
- [ ] Richer hierarchical orchestration support
- [ ] Automatic workspace dependency graph inference
- [ ] Rollback support on failed workspace execution
- [ ] Streaming progress updates back to the channel
- [ ] Cost tracking by task, workspace, and runtime

---

## License

MIT License
