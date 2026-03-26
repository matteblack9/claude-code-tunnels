---
name: connect-slack
description: "Connect Slack to an existing orchestrator by collecting Socket Mode credentials, saving them under ARCHIVE, and validating the channel."
---

# connect-slack

## When To Use

- The user wants to connect or repair the Slack channel
- Slack credentials are missing, expired, or stored in the wrong place
- `channels.slack.enabled` must be turned on in `orchestrator.yaml`

Slack uses Socket Mode, so no public callback URL is required.

## Runtime Adaptation

- `claude`
  Read this file first, then use `CLAUDE.md` or `.claude/` only as extra repo context.
- `cursor`
  Follow this file first, then apply `.cursor/rules`, `AGENTS.md`, and `CLAUDE.md` if they add local policy.
- `codex`
  Treat this file as the operational checklist. Do not assume slash-command wrappers exist.
- `opencode`
  Follow this file first, then honor `AGENTS.md` and any OpenCode-specific config already present.

## Rules

- Never overwrite an existing credentials file without explicit confirmation
- Present auto-detected values as numbered choices whenever possible
- Credential files use `key : value` formatting with spaces on both sides of the colon
- `ARCHIVE/` must stay outside git tracking
- Ask for secrets one field at a time and mask them in summaries

## Procedure

### 1. Environment Preflight

Connecting Slack requires the orchestrator to be installed, Python packages to be available, and a writable credential location.

#### 1-1. Verify `orchestrator.yaml`

If the file is missing, stop and run the `setup-orchestrator` skill first.

#### 1-2. Verify `ARCHIVE_PATH`

Resolve it from `orchestrator.yaml`:

```bash
ARCHIVE_PATH=$(python3 -c "import yaml; print(yaml.safe_load(open('orchestrator.yaml')).get('archive', 'ARCHIVE'))")
```

Confirm the value before writing secrets.

#### 1-3. Verify Python packages

```bash
$PYTHON_CMD -c "import slack_bolt" 2>/dev/null
$PYTHON_CMD -c "import slack_sdk" 2>/dev/null
```

If either package is missing, offer:

```text
[1] Install now
[2] Install manually and continue later
```

#### 1-4. Check for existing credentials

If `ARCHIVE/slack/credentials` already exists, show a masked summary and ask whether to overwrite it.

### 2. Slack App Setup Guide

If the user has not created a Slack App yet, guide them through:

```text
1. https://api.slack.com/apps -> Create New App -> From scratch
2. Choose the workspace
3. Settings -> Socket Mode -> Enable
4. Create an App-Level Token with `connections:write`
5. Event Subscriptions -> Enable events
6. Subscribe to `message.channels` and `app_mention`
7. OAuth & Permissions -> add `chat:write`, `channels:history`, `app_mentions:read`
8. Install the app to the workspace
```

### 3. Collect Credentials

Ask for these fields one at a time:

1. `app_id`
2. `client_id`
3. `client_secret`
4. `signing_secret`
5. `app_level_token`
6. `bot_token`

Validation rules:

- `app_level_token` must start with `xapp-`
- `bot_token` must start with `xoxb-`

Summary before writing:

```text
Slack credentials entered:
  app_id:           A0123456789
  client_id:        1234567890.1234567890
  client_secret:    ****
  signing_secret:   ****
  app_level_token:  xapp-1-...
  bot_token:        xoxb-...

Save with these values? (yes/no)
```

### 4. Save Configuration

After confirmation, write:

```text
ARCHIVE/slack/credentials
```

with:

```text
app_id : ...
client_id : ...
client_secret : ...
signing_secret : ...
app_level_token : ...
bot_token : ...
```

Then update:

```yaml
channels:
  slack:
    enabled: true
```

### 5. Validate The Channel

Run:

```bash
./start-orchestrator.sh --fg
```

Confirm:

- Slack startup logs appear without auth/import errors
- the Socket Mode connection is established
- the user can send a real Slack message to the bot

If validation fails, show the error and stop instead of retrying automatically.

## Completion Checklist

- `ARCHIVE/slack/credentials` exists with the expected keys
- `channels.slack.enabled` is true in `orchestrator.yaml`
- the orchestrator starts without Slack auth errors
- the user has a real Slack message test path
