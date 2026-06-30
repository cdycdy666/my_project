---
name: feishu-bot-configuration
description: Configure Feishu/Lark custom bots and debug Feishu bot integrations. Use when Codex needs to help create a Feishu self-built app bot, enable bot capabilities, configure permissions/scopes, set event subscriptions, choose long-connection versus callback delivery, send messages as a bot, handle chat_id/message_id, diagnose Feishu OpenAPI errors, or prevent duplicate message replies.
---

# Feishu Bot Configuration

Use this skill when implementing or debugging a Feishu custom bot.

## Configuration Workflow

Follow this order:

1. Create a self-built app in Feishu Open Platform.
2. Enable the bot capability.
3. Add only the required permissions.
4. Configure event subscription.
5. Publish the app after permission changes.
6. Add the bot to the target single chat or group.
7. Verify message receive and message send separately.
8. Persist the real `chat_id` from received events.

Store secrets only in server-side environment files:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=
```

Never commit Feishu secrets, verification tokens, encryption keys, app tickets, access tokens, or real event payloads containing user IDs.

## Delivery Mode

Prefer long connection for personal or small internal projects:

- No public domain is required.
- No HTTPS certificate is required.
- No inbound firewall rule is required.
- The service still must run continuously.

Use developer-server callback mode when the project needs a shared gateway, centralized audit, or production web infrastructure.

## Minimal Useful Scopes

Start with the minimum scopes needed by the actual API calls.

For a simple bot that receives user messages and replies:

```text
im:message.p2p_msg:readonly
im:message.group_at_msg:readonly
im:message:send_as_bot
```

When an API returns a missing-scope error, copy the exact scopes from the error, add only the needed ones, save, publish, and re-authorize.

## Event Handling

For `im.message.receive_v1`, extract:

- `message_id` for idempotency.
- `chat_id` for future replies.
- `message_type` for type-specific handling.
- `content` for text body parsing.
- sender fields only when the app truly needs identity logic.

Record `chat_id` from real events. Do not guess or hand-type it.

## Idempotency

Feishu can redeliver the same event. Always deduplicate by `message_id`.

Use this sequence:

```text
receive event
  -> read message_id
  -> if already processed, return quickly
  -> mark message_id processed
  -> process asynchronously if work may be slow
```

Mark the message as processed before slow work starts. This prevents duplicate replies when Feishu retries during an LLM call or network operation.

## Slow Work

Do not block the event callback on long model calls, file operations, or remote APIs.

Bad pattern:

```text
receive event -> call LLM for 15s -> reply
```

Preferred pattern:

```text
receive event -> deduplicate -> enqueue/background thread -> reply when done
```

If the task can take minutes, use a real queue or job table instead of an in-process thread.

## Sending Messages

When sending to a chat:

- Use `receive_id_type=chat_id`.
- Use a `chat_id` captured from an event.
- Send with bot identity using the required send-as-bot scope.

## Common Errors

`99991672 Access denied`:

- Missing app scopes.
- Add the exact scope listed in the error.
- Re-publish the app.
- Re-authorize if required.

`230001 invalid_receive_id`:

- `receive_id_type` does not match the ID value.
- Use `chat_id` with `receive_id_type=chat_id`.
- Verify the ID came from an actual message event.

Duplicate replies:

- Check for multiple running listener processes.
- Check whether the same `message_id` appears multiple times in logs.
- Add `message_id` idempotency.
- Move slow work out of the callback path.

## Validation

Verify:

- The bot receives one test text message.
- Logs include `message_id` and `chat_id`.
- The bot replies using captured `chat_id`.
- Replayed duplicate events are ignored.
- Permission changes are published before retesting.
- Secrets are absent from Git history and logs.
