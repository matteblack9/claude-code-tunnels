---
name: connect-telegram
description: "Connect Telegram to an existing orchestrator by collecting a BotFather token, optional allowlist, and validating long-polling startup."
---

# connect-telegram

## When To Use

- The user wants to connect Telegram to the orchestrator
- Telegram credentials are missing or need rotation
- `channels.telegram.enabled` must be enabled in `orchestrator.yaml`

## Runtime Adaptation

- `claude`
  Read this file first, then use `CLAUDE.md` or `.claude/` only as extra repo context.
- `cursor`
  Follow this file first, then apply `.cursor/rules`, `AGENTS.md`, and `CLAUDE.md` if they add repo-specific policy.
- `codex`
  Treat this file as the main Telegram setup checklist.
- `opencode`
  Follow this file first, then layer `AGENTS.md` and any OpenCode-only overrides on top.

## Rules

- Never overwrite existing Telegram credentials without confirmation
- Present detected values as numbered choices where possible
- Store credentials under `ARCHIVE/telegram/credentials`
- Empty `allowed_users` means the bot accepts all reachable Telegram users

## Procedure

### 1. Verify Orchestrator

Check that `orchestrator.yaml` exists. If not, stop and run the `setup-orchestrator` skill first.

Resolve `ARCHIVE_PATH` from `orchestrator.yaml`, then inspect whether `ARCHIVE/telegram/credentials` already exists.

### 2. Telegram Bot Guide

If the user does not already have a bot token, guide them through BotFather:

```text
1. Open Telegram and search for @BotFather
2. Send /newbot
3. Choose a bot display name
4. Choose a bot username ending in `bot`
5. Copy the full token BotFather returns
```

### 3. Collect Credentials

Ask for:

```text
bot_token
allowed_users (optional, comma-separated usernames or numeric user IDs)
```

Validation rules:

- `bot_token` is required and must contain a colon
- `allowed_users` is optional

Summary before writing:

```text
Telegram credentials entered:
  bot_token:      123456:...
  allowed_users:  username1, username2

Save with these values? (yes/no)
```

### 4. Save And Configure

Write:

```text
bot_token : 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
allowed_users : username1, username2
```

to:

```text
ARCHIVE/telegram/credentials
```

Then enable:

```yaml
channels:
  telegram:
    enabled: true
```

Telegram does not require extra packages beyond the existing orchestrator HTTP stack.

### 5. Validate The Channel

Restart the orchestrator and confirm:

- logs show Telegram startup without auth errors
- the bot identifies correctly
- a real Telegram message reaches the bot
- the confirm/cancel flow works

## Notes

- `allowed_users` is optional
- A Telegram token contains a colon, which is safe because credentials are parsed using ` : ` with spaces

## Completion Checklist

- `ARCHIVE/telegram/credentials` exists and is correctly formatted
- `channels.telegram.enabled` is true in `orchestrator.yaml`
- the orchestrator starts without Telegram errors
- the user has completed a real message round-trip
