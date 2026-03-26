# Claude-Code-Tunnels

Turn a project folder into an always-on Project Orchestrator that receives requests from Slack or Telegram, plans phased workspace execution, runs each workspace with `claude`, `codex`, or `opencode`, and sends structured results back.

## Terminology

- **Project Orchestrator (PO)**: The control plane. It receives requests, routes them, builds execution plans, and coordinates execution.
- **Workspace**: A real directory that contains the code or documents to operate on.
- **Workspace Orchestrator (WO)**: The execution unit for one workspace. A WO runs one runtime such as `claude`, `codex`, or `opencode`.
- **Executor**: The component that runs WOs phase by phase, with parallel execution inside a phase and ordered dependencies between phases.
- **Remote Workspace**: A workspace executed through the remote HTTP listener on another host or pod.

## Current Architecture

The current repository implements a multi-runtime architecture:

- `claude` stays on the Python `claude-agent-sdk`
- `codex` runs through a local Node bridge with `@openai/codex-sdk`
- `opencode` runs through a local Node bridge with `@opencode-ai/sdk`
- setup is now driven by a full-screen Textual TUI
- the TUI helps decide whether the current folder is already a `PO`, should become a new `PO`, or looks like a single `Workspace`
- the TUI writes `orchestrator.yaml`, `start-orchestrator.sh`, and root guidance files

## Recommended Model

The recommended setup is one `PO` root with an explicit workspace registry:

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

The current setup flow is optimized for that layout. Legacy filesystem discovery still works when `workspaces:` is not configured, but the TUI writes the explicit registry format by default.

## Architecture

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
        RT["Runtime layer"]
        CSDK["Claude SDK"]
        BR["Node bridge"]
        CX["Codex SDK"]
        OC["OpenCode SDK"]
    end

    subgraph REMOTE["Remote execution"]
        RL["Remote listener"]
        RR["Remote runtime"]
    end

    U --> CA --> G
    G --> R
    R --> P
    R --> D
    P --> E
    D --> CA

    E --> RT
    E --> RL
    RT --> CSDK
    RT --> BR
    BR --> CX
    BR --> OC
    RL --> RR

    CSDK --> L
    CX --> L
    OC --> L
    RR --> L
    L --> CA
```

## Quick Start

```bash
git clone https://github.com/matteblack9/claude-code-tunnels.git
cd claude-code-tunnels

./install.sh
.venv/bin/python -m orchestrator.setup_tui
./start-orchestrator.sh --fg
```

## Setup Flow

The setup TUI is the main entry point:

```bash
.venv/bin/python -m orchestrator.setup_tui
```

It performs these steps:

1. Checks the current folder and classifies it as:
   - `existing_po`
   - `new_po_candidate`
   - `workspace_candidate`
   - `unknown`
2. Suggests:
   - `PO root`
   - `ARCHIVE` path
   - workspace candidates
3. Lets you define one `WO` per selected workspace:
   - workspace id
   - relative path
   - runtime
   - local or remote mode
4. Lets you choose:
   - global default runtime
   - executor runtime
   - Slack enablement
   - Telegram enablement
5. Writes:
   - `orchestrator.yaml`
   - `start-orchestrator.sh`
   - `CLAUDE.md` when missing
   - `AGENTS.md` when missing
6. Shows the exact run commands for foreground and background execution

### Folder Heuristics

The TUI uses these rules:

- `existing_po`: at least two of `orchestrator.yaml`, `orchestrator/`, `start-orchestrator.sh`, `ARCHIVE/`, `.tasks/` exist
- `new_po_candidate`: multiple visible child directories exist and the current folder does not strongly look like a single codebase
- `workspace_candidate`: the current folder contains codebase markers such as `.git`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, or `requirements.txt`
- `unknown`: neither side is strongly implied

## How To Run

After setup has written `orchestrator.yaml` and `start-orchestrator.sh`, run from the `PO` root:

### Operational Flow

```mermaid
flowchart TD
    START["Run start-orchestrator.sh"] --> ORCH["orchestrator.main"]
    ORCH --> CHANNEL["Slack / Telegram adapter"]
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
    LOG --> RESULT["Formatted channel response"]
    RESULT --> CHANNEL
```

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

## Runtime Model

### Supported Runtimes

| Runtime | Local implementation | Typical use |
|---------|----------------------|-------------|
| `claude` | Python `claude-agent-sdk` | Default routing, planning, repair, general execution |
| `codex` | Node bridge + `@openai/codex-sdk` | Workspace execution with Codex |
| `opencode` | Node bridge + `@opencode-ai/sdk` | Workspace execution with OpenCode |

### Default Role Mapping

| Role | Default runtime | Max turns |
|------|-----------------|-----------|
| Router | `claude` | 8 |
| Planner (`PO`) | `claude` | 15 |
| Executor | `claude` | 5 |
| Direct handler | `claude` | 30 |
| JSON repair | `claude` | 1 |

### Runtime Resolution Order

Runtime selection follows this order:

1. `workspaces[].wo.runtime`
2. `runtime.roles[role]`
3. `runtime.default`
4. fallback `claude`

### Runtime Notes

- `claude` uses `CLAUDE.md` and `.claude/`
- `codex` is expected to use `AGENTS.md`
- `opencode` requires provider credentials and can also work with `AGENTS.md`-style guidance
- the local multi-runtime bridge is persistent and communicates with Python over stdio JSON messages
- the remote listener is standalone and uses the local runtime available on that host

## Configuration

The setup TUI writes `orchestrator.yaml` in this shape:

```yaml
root: /path/to/po-root
archive: /path/to/po-root/ARCHIVE

runtime:
  default: claude
  roles:
    router: claude
    planner: claude
    executor: codex
    direct_handler: claude
    repair: claude

channels:
  slack:
    enabled: true
  telegram:
    enabled: false

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

### Key Fields

- `root`: the `PO` root
- `archive`: credential storage path
- `runtime.default`: default runtime for roles without explicit overrides
- `runtime.roles`: per-role runtime overrides
- `workspaces[].id`: workspace identifier used by the planner and executor
- `workspaces[].path`: actual workspace path relative to `root`
- `workspaces[].wo.runtime`: runtime for that workspace
- `workspaces[].wo.mode`: `local` or `remote`
- `workspaces[].wo.remote`: remote listener connection information
- `remote_workspaces`: legacy compatibility projection used by older lookup paths

## Execution Flow

The request lifecycle is:

1. Message received through Slack or Telegram
2. `ConfirmGate` stores the pending request
3. User confirms intent
4. Router identifies the target project or switches to direct handling
5. `PO` builds phased execution
6. Executor runs each phase:
   - parallel within a phase
   - sequential across phases
7. completed phase summaries become upstream context for downstream workspaces
8. results are written to `.tasks/`
9. formatted results are sent back to the channel

### Two-Step Confirmation

- first confirmation: confirm the request interpretation
- second confirmation: only for workspace-modifying planned executions
- direct answers and direct requests skip the second confirmation

## Remote Workspaces

Remote workspaces are executed through the HTTP listener in `orchestrator/remote/listener.py`.

### Listener Environment

The listener accepts:

- `LISTENER_CWD`
- `LISTENER_PORT`
- `LISTENER_TOKEN`
- `LISTENER_RUNTIME`

### Remote Host Requirements

- Python 3.10+
- `claude-agent-sdk` and `aiohttp` if using `claude`
- `codex` CLI if using `codex`
- `opencode` CLI plus provider credentials if using `opencode`

### Remote Setup

You can use the existing setup skills:

- `/setup-remote-project`
- `/setup-remote-workspace`

The deploy helper supports both SSH and `kubectl` paths through `orchestrator/remote/deploy.py`.

## Channel Setup

### Slack

Slack support exists in `orchestrator/channel/slack.py`, but the required Slack libraries are optional.

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

Example credential file:

```text
app_id : A0XXXXXXXXX
client_id : 1234567890.9876543210
client_secret : your-client-secret
signing_secret : your-signing-secret
app_level_token : xapp-1-XXXXXXXXXXX
bot_token : xoxb-XXXXXXXXXXX
```

### Telegram

Telegram support is implemented in `orchestrator/channel/telegram.py`.

1. create a bot with [@BotFather](https://t.me/botfather)
2. write `ARCHIVE/telegram/credentials`

Example credential file:

```text
bot_token : 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
allowed_users : username1, username2
```

3. enable Telegram in `orchestrator.yaml`

## Guidance Files

Workspace behavior is controlled by runtime-specific guidance files:

- `CLAUDE.md` for Claude-oriented workflows
- `AGENTS.md` for Codex and OpenCode-oriented workflows
- `.claude/` for existing Claude project memory and rules

The setup flow creates root-level `CLAUDE.md` and `AGENTS.md` when they are missing. Workspace-level guidance remains under your control.

## Repository Layout

```text
claude-code-tunnels/
├── orchestrator/
│   ├── main.py
│   ├── server.py
│   ├── router.py
│   ├── po.py
│   ├── executor.py
│   ├── direct_handler.py
│   ├── task_log.py
│   ├── setup_tui.py
│   ├── setup_support.py
│   ├── runtime/
│   │   ├── __init__.py
│   │   └── bridge.py
│   ├── channel/
│   │   ├── slack.py
│   │   └── telegram.py
│   └── remote/
│       ├── listener.py
│       └── deploy.py
├── bridge/
│   ├── daemon.mjs
│   ├── lib/runtime.mjs
│   └── tests/runtime.test.mjs
├── templates/
├── skills/
├── install.sh
├── package.json
├── requirements.txt
└── requirements-dev.txt
```

## Customization

### Add a Custom Channel

Inherit from `BaseChannel` in `orchestrator/channel/base.py`, then register it in `orchestrator/main.py`.

### Customize Direct Handling

Adjust the system prompt in `orchestrator/direct_handler.py` to integrate your own internal tools or policies.

### Customize Runtime Behavior

Adjust workspace guidance files and runtime selections in `orchestrator.yaml`. Executor output is expected to end in structured JSON with `changed_files`, `summary`, `test_result`, and `downstream_context`.

## Security Model

- user-controlled input is isolated inside XML-like tags
- workspace and project identifiers are validated before execution
- blocked directories include `ARCHIVE`, `.tasks`, `orchestrator`, `.claude`, and `.git`
- each local workspace execution is restricted by `cwd`
- channel execution is guarded by confirmation state

## Development And Testing

Bootstrap dependencies:

```bash
./install.sh
```

Run tests:

```bash
# ensure a working node/npm installation is first on PATH
node --test
.venv/bin/python -m pytest orchestrator/tests -q
```

What is currently covered:

- runtime resolution
- executor behavior
- task log output
- setup helper rendering
- setup TUI write path
- remote listener helpers
- Node bridge helper logic

## Dependencies

### Python

- `claude-agent-sdk`
- `aiohttp`
- `pyyaml`
- `requests`
- `textual`
- `pytest`
- `pytest-asyncio`

### Node

- `@openai/codex-sdk`
- `@opencode-ai/sdk`

## License

MIT
