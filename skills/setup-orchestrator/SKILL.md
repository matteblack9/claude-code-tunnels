---
name: setup-orchestrator
description: "Install or reconfigure the local Project Orchestrator root, then validate the generated control-plane files."
---

# setup-orchestrator

## When To Use

- The user wants to install, bootstrap, repair, or reconfigure the orchestrator root
- `orchestrator.yaml`, `start-orchestrator.sh`, `AGENTS.md`, or `CLAUDE.md` are missing or stale
- The team wants to change default runtimes, channel enablement, or workspace registry settings

## Runtime Adaptation

- `claude`
  Read this file first, then honor existing `CLAUDE.md` and `.claude/` memory if present.
- `cursor`
  Read this file first, then apply `.cursor/rules`, `AGENTS.md`, `CLAUDE.md`, and legacy `.cursorrules` as additional repo rules.
- `codex`
  Treat this file plus `AGENTS.md` as the primary procedure. Do not assume slash-command support.
- `opencode`
  Read this file first, then apply `AGENTS.md` plus any `opencode.json` or `.opencode/skills/` overrides that already exist.

## Operating Rules

- Work from the orchestrator repository root
- Prefer the setup TUI instead of editing `orchestrator.yaml` by hand unless the user explicitly asks for manual edits
- Present auto-detected values as numbered choices when asking the user to confirm them
- If dependencies are missing, install or repair them before launching the TUI
- Do not overwrite an existing config blindly; inspect current files first and explain what will change

## Procedure

### 1. Preflight

1. Verify that this repository contains `install.sh`, `orchestrator/setup_tui.py`, and `templates/`
2. Check whether `.venv/`, `node_modules/`, and required CLIs already exist
3. If dependencies are missing or broken, run `./install.sh`
4. Inspect current orchestrator assets if they already exist:
   - `orchestrator.yaml`
   - `start-orchestrator.sh`
   - `AGENTS.md`
   - `CLAUDE.md`
   - `opencode.json` and `.opencode/` when OpenCode is in use

### 2. Launch Setup

Run:

```bash
.venv/bin/python -m orchestrator.setup_tui
```

Let the TUI classify the current folder as one of:

- existing orchestrator root
- new orchestrator candidate
- single workspace that should be wrapped by a new orchestrator root

### 3. Confirm Generated Settings

Inside the TUI, confirm or edit:

- orchestrator root path
- `ARCHIVE` path
- enabled channels
- default runtime and executor runtime
- workspace ids, relative paths, runtime, and mode

Runtime-specific checks:

- `claude` remains the safest default when no strong reason exists to change it
- `cursor` requires a working `cursor-agent` CLI and authenticated Cursor environment
- `codex` requires the local `codex` CLI and Node dependencies
- `opencode` requires `opencode`, provider login, and creates `opencode.json` plus `.opencode/skills/` when selected

### 4. Verify Generated Files

After setup completes, verify that the expected files exist and look coherent:

- `orchestrator.yaml`
- `start-orchestrator.sh`
- `AGENTS.md`
- `CLAUDE.md`
- `opencode.json` and `.opencode/` when OpenCode was selected

Cursor-specific files do not need to be scaffolded. Existing `.cursor/rules` or `.cursorrules` should be preserved.

### 5. Validate The Environment

Run the startup flow the TUI prints:

```bash
./start-orchestrator.sh --fg
```

Then confirm:

- the orchestrator boots without import/runtime errors
- the configured channel adapters initialize correctly
- runtime detection matches the requested default and executor runtimes

### 6. Finish

Summarize:

- which files were generated or updated
- which runtimes were configured
- which follow-up command the user should use for foreground/background start

## Completion Checklist

- `orchestrator.yaml` matches the current environment
- runtime guidance files exist and were not accidentally overwritten with stale content
- the start script launches successfully
- any missing runtime dependency or auth prerequisite is called out explicitly
