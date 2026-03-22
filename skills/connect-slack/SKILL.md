---
name: connect-slack
description: "Slack 채널을 기존 Orchestrator에 연결. Slack App 생성 가이드, credential 입력, Socket Mode 설정, 연결 테스트까지 수행. /connect-slack 으로 실행. 'slack 연결', 'connect slack', 'slack 채널 추가' 요청에 사용."
---

# Connect Slack Channel

기존에 설치된 Orchestrator에 Slack 채널을 추가로 연결한다.

## Prerequisites

- `orchestrator/` 디렉토리가 현재 폴더에 존재해야 함
- `orchestrator.yaml` 파일이 존재해야 함

## Flow

### Step 1: Verify Orchestrator

1. Check `orchestrator.yaml` exists in current directory
2. Load config to find ARCHIVE_PATH
3. If not found → "Please run /setup-orchestrator first"

### Step 2: Slack App Guide

If no credentials found, show the user:

```
Slack App Setup Guide:
1. Go to https://api.slack.com/apps → Create New App
2. Choose "From scratch", name your app, select workspace
3. Settings → Socket Mode → Enable Socket Mode
   - Generate app-level token (xapp-...) with connections:write scope
4. Event Subscriptions → Enable Events
   - Subscribe to: message.channels, app_mention
5. OAuth & Permissions → Bot Token Scopes:
   - chat:write, channels:history, app_mentions:read
6. Install App to Workspace
7. Copy the Bot Token (xoxb-...)
```

### Step 3: Collect Credentials

```
app_id:
client_id:
client_secret:
signing_secret:
app_level_token: (xapp-...)
bot_token: (xoxb-...)
```

### Step 4: Save & Configure

1. Create ARCHIVE_PATH/slack/credentials
2. Update orchestrator.yaml: set channels.slack.enabled = true
3. Install dependencies: `pip install slack-bolt slack-sdk`

### Step 5: Test

1. Restart orchestrator
2. Check logs for "Slack channel starting (Socket Mode)..."
3. Instruct user to send a test message in Slack

## Rules

- If orchestrator not installed, redirect to /setup-orchestrator
- Never overwrite existing credentials without confirmation
