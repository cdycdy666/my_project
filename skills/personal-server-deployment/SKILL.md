---
name: personal-server-deployment
description: Deploy personal automation services to a Linux cloud server. Use when Codex needs to move a local script, bot, scheduled job, AI automation, or personal tool from a Mac/local machine to a VPS/ECS server with SSH, /opt layout, .env configuration, Python venv, systemd, cron, logs, Git backup, deploy keys, and basic operational checks.
---

# Personal Server Deployment

Use this skill to deploy small personal automation services to a Linux server.

## Default Layout

Use `/opt` for server-owned services:

```text
/opt/project-service      # code and scripts
/opt/project-data         # data, vault, generated files
/opt/.env                 # server-only secrets and runtime config
```

Keep code, data, secrets, logs, and runtime state separate.

## Deployment Workflow

1. Confirm the server OS, IP, and SSH access.
2. Configure SSH key login.
3. Install base packages: `git`, `python3`, `python3-venv`, `rsync`.
4. Copy code into `/opt/project-service`.
5. Create `/opt/project-data` if the service writes durable data.
6. Create `/opt/.env` with secrets and runtime paths.
7. Create `.venv` and install `requirements.txt`.
8. Run core scripts manually.
9. Add a `systemd` service for long-running listeners.
10. Add cron jobs for scheduled work.
11. Configure Git backup if data or code must be versioned.
12. Reboot or restart services and verify recovery.

## Git Strategy

Decide what Git backs up:

- Code can live in the main project repository.
- Data can live in a separate private repository.
- Secrets never go to Git.
- Logs and runtime state never go to Git.

Use a deploy key when the server pushes to a private repository. Grant write access only when the server must push.

## Ignore Rules

Include these patterns in service repositories:

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

## systemd Template

Use this for listener-style services:

```ini
[Unit]
Description=Project listener
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/project-service
ExecStart=/opt/project-service/.venv/bin/python /opt/project-service/run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/opt/project-service/logs/listener.log
StandardError=append:/opt/project-service/logs/listener.err.log

[Install]
WantedBy=multi-user.target
```

After creating or editing the unit:

```bash
systemctl daemon-reload
systemctl enable --now project.service
systemctl status project.service --no-pager
```

## cron Template

Use this for scheduled jobs:

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai

30 7 * * * root cd /opt/project-service && .venv/bin/python scripts/run_morning_job.py >> /opt/project-service/logs/cron-morning.log 2>&1
0 23 * * * root cd /opt/project-service && .venv/bin/python scripts/run_daily_job.py >> /opt/project-service/logs/cron-daily.log 2>&1
```

Verify cron:

```bash
systemctl is-active cron
cat /etc/cron.d/project
```

## Security Checks

- Prefer SSH keys over password login.
- Remove unused inbound security-group rules.
- Do not expose application ports unless required.
- Keep `.env` outside Git repositories.
- Avoid printing full secrets or user-private payloads in logs.
- Scope deploy keys to one repository when possible.

## Operational Checks

Run these after deployment and after each major change:

```bash
systemctl is-active project.service
systemctl status project.service --no-pager
systemctl is-active cron
tail -n 100 /opt/project-service/logs/listener.err.log
git -C /opt/project-data status --short --branch
```

## Troubleshooting

If a service does not start:

- Check `WorkingDirectory`.
- Check `.venv/bin/python` exists.
- Run the command in `ExecStart` manually.
- Inspect `journalctl -u project.service`.

If cron does not run:

- Check cron service status.
- Use absolute paths or `cd` into the service directory.
- Ensure cron has the required environment through files or explicit variables.
- Check log redirection paths.

If Git fails:

- Verify deploy key access.
- Add GitHub to `known_hosts`.
- Check remote URL.
- Check `safe.directory` and directory ownership.
- Resolve local uncommitted conflicts before pulling.
