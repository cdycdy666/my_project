---
name: lightweight-bot-automation
description: Design and implement lightweight chat-bot automations. Use when Codex needs to build systems where a chat bot captures user input, gives immediate feedback, runs scheduled batch processing, writes to files or knowledge bases, calls LLMs, avoids duplicate message handling, and backs up results with Git.
---

# Lightweight Bot Automation

Use this skill to design small reliable bot systems before adding heavier infrastructure.

## Architecture

Separate real-time interaction from batch processing:

```text
chat bot
  -> listener service
    -> idempotency
    -> raw capture
    -> async immediate feedback

scheduler
  -> fetch or read accumulated records
  -> LLM batch processing
  -> write durable output
  -> backup/sync
```

## Listener Responsibilities

Keep the listener narrow:

- Receive events.
- Extract message IDs and conversation IDs.
- Deduplicate events before work starts.
- Persist raw input.
- Start slow feedback work asynchronously.
- Reply with success or failure.

Do not make the listener responsible for full daily organization, heavy reports, or long-running sync.

## Scheduler Responsibilities

Use scheduled jobs for:

- Daily or periodic summarization.
- History fetch.
- Final note/report generation.
- Git commit and push.
- Backfill checks.

Keep scheduled jobs idempotent enough that manual reruns are safe.

## Data Boundaries

Separate these categories:

- Service code: project repository.
- Raw captured records: data or knowledge repository.
- Final organized output: data or knowledge repository.
- Runtime state: local server state, not Git.
- Logs: local server logs, not Git.
- Secrets: `.env` or secret manager, not Git.

Use `.gitignore` patterns:

```gitignore
.env
.env.*
!.env.example
.venv/
state.json
logs/
__pycache__/
*.pyc
```

## Idempotency

Every event-driven bot must define an idempotency key:

- Feishu/Lark: `message_id`.
- Slack: event ID or message timestamp plus channel.
- Telegram: update ID.
- Generic webhooks: delivery ID header when available.

Persist recent processed IDs. Use a bounded list or durable store.

## LLM Calls

Use different prompts for different interaction layers:

- Immediate feedback: short, concrete, one useful response.
- Reminder: context-aware, low-friction nudge.
- Batch summary: structured, auditable, grouped by topic/event.

Avoid synchronous LLM calls in webhook callbacks unless the platform explicitly allows long callback duration.

## Sync Strategy

If the server is the primary writer and Git is a backup:

```text
service start: optional git pull once
batch write complete: git add / commit / push
```

Avoid pulling before every read unless humans also edit the remote repository.

## Runtime

Use `systemd` for a long-running listener:

```ini
Restart=always
RestartSec=5
After=network-online.target
Wants=network-online.target
```

Use cron for simple scheduled jobs:

```cron
CRON_TZ=Asia/Shanghai
30 7 * * * ...
0 23 * * * ...
```

## Validation

Before calling the system done:

- Send one test message and verify one reply.
- Replay or observe duplicate delivery and verify it is ignored.
- Confirm raw capture exists.
- Run one scheduled job manually.
- Confirm generated output is written.
- Confirm Git backup excludes secrets, logs, and runtime state.
- Restart the server service and confirm it reconnects.
