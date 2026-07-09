from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AGENT_BY_ID, AGENTS, AgentConfig


ALERT_RE = re.compile(r"(error|exception|traceback|failed|fail|timeout|unavailable|denied)", re.I)
SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_\-]{12,}|Bearer\s+[A-Za-z0-9._\-]{16,}|app_secret['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,})"
)
LOG_TIME_RE = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redact(text: str) -> str:
    return SECRET_RE.sub("[redacted]", text)


def _run(cmd: list[str], timeout: int = 4) -> dict[str, Any]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": completed.returncode == 0,
            "code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover - defensive for minimal server envs
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc)}


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text[:-1] + "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.astimezone()
        except ValueError:
            continue
    return None


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _tail_text(path: Path, max_bytes: int = 512_000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
                fh.readline()
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _iter_jsonl(path: Path, max_bytes: int = 8_000_000) -> list[dict[str, Any]]:
    text = _tail_text(path, max_bytes=max_bytes)
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            row.setdefault("_source_file", str(path))
            row.setdefault("_line_no", line_no)
            events.append(row)
    return events


def _event_time(event: dict[str, Any]) -> datetime | None:
    return _parse_ts(event.get("ts") or event.get("time") or event.get("created_at"))


def _event_label(event: dict[str, Any]) -> str:
    name = str(event.get("event") or event.get("tool") or "event")
    if name == "agent_next_action":
        return str(event.get("action") or name)
    if name == "llm_request":
        return f"LLM: {event.get('purpose') or 'request'}"
    if name == "tool_result":
        return f"Tool: {event.get('tool') or 'result'}"
    if name in {"weread_request", "weread_response"}:
        return f"WeRead: {event.get('endpoint') or name}"
    return name


def _event_kind(event: dict[str, Any]) -> str:
    name = str(event.get("event") or "")
    if ALERT_RE.search(name) or event.get("ok") is False:
        return "error" if "gate" not in name and "check" not in name else "warn"
    if name in {"reply_start", "message_received"}:
        return "input"
    if name in {"progress", "agent_loop_turn"}:
        return "progress"
    if name == "agent_next_action":
        return "planner"
    if name.startswith("llm_") or "reply" in name and name != "reply_complete":
        return "llm"
    if name in {"tool_result", "weread_request", "weread_response", "verified_materials_loaded"}:
        return "tool"
    if "gate" in name or "check" in name:
        return "gate"
    if name == "reply_complete":
        return "output"
    return "event"


def _extract_message(events: list[dict[str, Any]]) -> str:
    for event in events:
        for key in ("message", "user_message", "text"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                if event.get("event") in {"final_reply", "reply_complete"} and key == "text":
                    continue
                return value.strip()[:220]
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get("user_message")
            if isinstance(value, str) and value.strip():
                return value.strip()[:220]
    return ""


def _status_from_events(events: list[dict[str, Any]]) -> str:
    names = [str(event.get("event") or "") for event in events]
    has_complete = any(name in {"reply_complete", "final_reply", "final_reply_sent"} for name in names)
    hard_error = any(ALERT_RE.search(str(event.get("event") or "")) for event in events)
    hard_error = hard_error or any(event.get("event") == "error" for event in events)
    gate_failed = any(("gate" in str(event.get("event") or "") or "check" in str(event.get("event") or "")) and event.get("ok") is False for event in events)
    if has_complete and gate_failed:
        return "warning"
    if has_complete:
        return "success"
    if hard_error:
        return "failed"
    return "running"


def _duration_ms(events: list[dict[str, Any]]) -> int | None:
    for event in reversed(events):
        if event.get("event") == "reply_complete" and isinstance(event.get("elapsed_ms"), int):
            return event["elapsed_ms"]
    times = [_event_time(event) for event in events]
    times = [time for time in times if time]
    if len(times) >= 2:
        return int((max(times) - min(times)).total_seconds() * 1000)
    return None


def _summarize_trace(agent: AgentConfig, trace_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda item: _event_time(item) or datetime.min.replace(tzinfo=timezone.utc))
    times = [_event_time(event) for event in ordered]
    times = [time for time in times if time]
    completion = next((event for event in reversed(ordered) if event.get("event") == "reply_complete"), None)
    final = next((event for event in reversed(ordered) if event.get("event") == "final_reply"), None)
    counters = {
        "events": len(ordered),
        "llm": sum(1 for event in ordered if str(event.get("event") or "").startswith("llm_")),
        "tools": sum(1 for event in ordered if event.get("event") in {"tool_result", "weread_request", "weread_response"}),
        "gates": sum(1 for event in ordered if "gate" in str(event.get("event") or "") or "check" in str(event.get("event") or "")),
        "gate_failures": sum(
            1
            for event in ordered
            if ("gate" in str(event.get("event") or "") or "check" in str(event.get("event") or "")) and event.get("ok") is False
        ),
    }
    return {
        "id": trace_id,
        "trace_id": trace_id,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "kind": "trace",
        "status": _status_from_events(ordered),
        "title": _extract_message(ordered) or f"{agent.name} trace",
        "flow": (completion or {}).get("flow") or "agent_trace",
        "started_at": _iso(min(times) if times else None),
        "ended_at": _iso(max(times) if times else None),
        "duration_ms": _duration_ms(ordered),
        "counters": counters,
        "final_preview": str((final or {}).get("text") or "")[:260],
        "actions": [_event_label(event) for event in ordered if event.get("event") in {"agent_next_action", "tool_result", "llm_request"}][:14],
        "events": ordered,
    }


def _trace_files(agent: AgentConfig) -> list[Path]:
    if not agent.trace_dir:
        return []
    trace_dir = agent.root / agent.trace_dir
    if not trace_dir.exists():
        return []
    return sorted(trace_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:8]


def _trace_runs(agent: AgentConfig) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in _trace_files(agent):
        for event in _iter_jsonl(path):
            trace_id = str(event.get("trace_id") or f"{path.name}:{event.get('_line_no')}")
            grouped.setdefault(trace_id, []).append(event)
    return [_summarize_trace(agent, trace_id, events) for trace_id, events in grouped.items()]


def _log_line_to_event(agent: AgentConfig, source: str, line: str, index: int) -> dict[str, Any]:
    match = LOG_TIME_RE.search(line)
    ts = _iso(_parse_ts(match.group("ts"))) if match else None
    event_name = "log_alert" if ALERT_RE.search(line) else "log_line"
    text = _redact(line.strip())
    digest = hashlib.sha1(f"{agent.id}:{source}:{index}:{text}".encode("utf-8")).hexdigest()[:12]
    return {
        "event": event_name,
        "ts": ts,
        "source": source,
        "text": text[:1200],
        "trace_id": f"log-{agent.id}-{digest}",
    }


def _log_runs(agent: AgentConfig) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for rel in agent.log_files:
        path = agent.root / rel
        text = _tail_text(path, max_bytes=320_000)
        if not text:
            continue
        lines = [line for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines[-80:]):
            if not LOG_TIME_RE.search(line):
                continue
            event = _log_line_to_event(agent, rel, line, index)
            if event["event"] == "log_line" and not any(token in line for token in ("received", "sent reply", "completed", "no user text")):
                continue
            status = "failed" if event["event"] == "log_alert" else "success"
            runs.append(
                {
                    "id": event["trace_id"],
                    "trace_id": event["trace_id"],
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "kind": "log",
                    "status": status,
                    "title": f"{rel}: {event['text'][:180]}",
                    "flow": "service_log",
                    "started_at": event.get("ts"),
                    "ended_at": event.get("ts"),
                    "duration_ms": None,
                    "counters": {"events": 1, "llm": 0, "tools": 0, "gates": 0, "gate_failures": 0},
                    "final_preview": event["text"][:260],
                    "actions": [event["event"]],
                    "events": [event],
                }
            )
    return runs


def collect_runs(agent_id: str | None = None, limit: int = 200, include_events: bool = False) -> list[dict[str, Any]]:
    agents = [AGENT_BY_ID[agent_id]] if agent_id in AGENT_BY_ID else list(AGENTS)
    runs: list[dict[str, Any]] = []
    for agent in agents:
        runs.extend(_trace_runs(agent))
        if not agent.trace_dir:
            runs.extend(_log_runs(agent))
    runs.sort(key=lambda run: run.get("ended_at") or run.get("started_at") or "", reverse=True)
    trimmed = runs[:limit]
    if include_events:
        return trimmed
    return [{key: value for key, value in run.items() if key != "events"} for run in trimmed]


def collect_run_detail(trace_id: str) -> dict[str, Any] | None:
    for run in collect_runs(limit=500, include_events=True):
        if run["trace_id"] == trace_id or run["id"] == trace_id:
            events = []
            for index, event in enumerate(run.get("events") or []):
                events.append(
                    {
                        "index": index + 1,
                        "event": event.get("event") or "event",
                        "kind": _event_kind(event),
                        "label": _event_label(event),
                        "ts": _iso(_event_time(event)) or event.get("ts"),
                        "ok": event.get("ok"),
                        "summary": _event_summary(event),
                        "io": _event_io(event),
                        "raw": _safe_event(event),
                    }
                )
            detail = {key: value for key, value in run.items() if key != "events"}
            detail["events"] = events
            return detail
    return None


def _compact(value: Any, string_limit: int = 30_000, list_limit: int = 80, depth: int = 0) -> Any:
    if depth > 4:
        return "[nested]"
    if isinstance(value, str):
        redacted = _redact(value)
        if len(redacted) > string_limit:
            return redacted[:string_limit] + f"... [truncated {len(redacted) - string_limit} chars]"
        return redacted
    if isinstance(value, dict):
        return {str(key): _compact(item, string_limit, list_limit, depth + 1) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, list):
        compacted = [_compact(item, string_limit, list_limit, depth + 1) for item in value[:list_limit]]
        if len(value) > list_limit:
            compacted.append(f"... [{len(value) - list_limit} more]")
        return compacted
    return value


def _pick(event: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: _compact(event[key]) for key in keys if key in event and event[key] not in (None, "", [], {})}


def _event_io(event: dict[str, Any]) -> dict[str, Any]:
    name = str(event.get("event") or "")
    meta = _pick(event, ("ts", "trace_id", "chat_id", "elapsed_ms"))
    if name == "reply_start":
        return {
            "input": _pick(event, ("user_message", "message", "chat_id")),
            "output": _pick(event, ("trace_id",)),
            "meta": meta,
        }
    if name == "agent_loop_turn":
        return {
            "input": _pick(event, ("turn",)),
            "output": _pick(
                event,
                (
                    "evidence_count",
                    "paper_evidence_count",
                    "search_rounds",
                    "paper_search_rounds",
                    "paper_fetch_rounds",
                    "detail_rounds",
                    "draft_rounds",
                    "material_verification_rounds",
                    "supplemental_rounds",
                    "has_verified_materials",
                    "has_personal_evidence",
                    "has_material_scoring",
                    "has_reply",
                ),
            ),
            "meta": meta,
        }
    if name == "agent_next_action":
        action_args = {
            key: value
            for key, value in event.items()
            if key
            not in {
                "event",
                "trace_id",
                "ts",
                "chat_id",
                "raw_text",
                "reason",
                "action",
                "_source_file",
                "_line_no",
            }
        }
        return {
            "input": _pick(event, ("raw_text",)),
            "output": {
                "action": _compact(event.get("action")),
                "reason": _compact(event.get("reason")),
                "args": _compact(action_args),
            },
            "meta": meta,
        }
    if name == "llm_request":
        return {
            "input": _pick(event, ("purpose", "model", "base_url", "temperature", "prompt_chars", "metadata", "messages", "request_payload")),
            "output": {"request": "sent"},
            "meta": meta,
        }
    if name == "llm_response":
        return {
            "input": _pick(event, ("purpose", "model")),
            "output": _pick(event, ("elapsed_ms", "response_keys", "response_text", "usage", "raw_text", "text", "response")),
            "meta": meta,
        }
    if name == "weread_request":
        return {
            "input": _pick(event, ("api_name", "endpoint", "params")),
            "output": {"request": "sent"},
            "meta": meta,
        }
    if name == "weread_response":
        return {
            "input": _pick(event, ("api_name", "endpoint", "params")),
            "output": _pick(event, ("summary", "response", "elapsed_ms", "ok", "error")),
            "meta": meta,
        }
    if name == "tool_result":
        return {
            "input": _pick(event, ("tool", "arguments")),
            "output": _pick(event, ("ok", "error", "metadata", "content", "episodes", "papers", "episode_count", "paper_count", "result")),
            "meta": meta,
        }
    if "gate" in name or "check" in name:
        return {
            "input": _pick(event, ("reply_chars", "queries", "extra_queries", "final_reply_chars", "verified_materials_context_chars")),
            "output": _pick(event, ("ok", "reason", "extra_queries", "raw_text")),
            "meta": meta,
        }
    if name == "final_reply":
        return {
            "input": _pick(event, ("chars",)),
            "output": _pick(event, ("text",)),
            "meta": meta,
        }
    if name == "reply_complete":
        return {
            "input": _pick(event, ("flow",)),
            "output": _pick(event, ("elapsed_ms", "chars")),
            "meta": meta,
        }
    if name in {"progress", "personal_context_loaded", "weread_context_loaded", "verified_materials_loaded"}:
        return {
            "input": _pick(event, ("stage", "text")),
            "output": _pick(event, ("chars", "count", "summary")),
            "meta": meta,
        }
    if name in {"log_line", "log_alert"}:
        return {
            "input": _pick(event, ("source",)),
            "output": _pick(event, ("text",)),
            "meta": meta,
        }
    return {
        "input": _pick(event, ("event", "message", "user_message", "source", "tool", "purpose", "action")),
        "output": _pick(event, ("ok", "reason", "summary", "text", "metadata")),
        "meta": meta,
    }


def _safe_event(event: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in event.items():
        if key.startswith("_"):
            continue
        if isinstance(value, str):
            safe[key] = _redact(value[:50_000])
        else:
            safe[key] = _compact(value, string_limit=50_000, list_limit=160)
    return safe


def _event_summary(event: dict[str, Any]) -> str:
    for key in ("reason", "text", "message", "tool", "purpose", "action", "source"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return _redact(value.strip())[:260]
    metadata = event.get("metadata")
    if isinstance(metadata, dict):
        return ", ".join(f"{key}={value}" for key, value in list(metadata.items())[:4])[:260]
    return ""


def _service_status(unit: str) -> dict[str, Any]:
    active = _run(["systemctl", "is-active", unit])
    show = _run(
        [
            "systemctl",
            "show",
            unit,
            "--no-pager",
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "MainPID",
            "-p",
            "NRestarts",
            "-p",
            "ExecMainStatus",
            "-p",
            "ActiveEnterTimestamp",
        ]
    )
    fields: dict[str, str] = {}
    for line in show["stdout"].splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value
    return {
        "unit": unit,
        "active": active["stdout"] or "unknown",
        "ok": active["stdout"] == "active",
        "fields": fields,
        "error": active["stderr"] or show["stderr"],
    }


def _timer_status(unit: str) -> dict[str, Any]:
    timer = _run(["systemctl", "list-timers", "--all", "--no-pager", "--plain", unit])
    lines = [line for line in timer["stdout"].splitlines() if unit in line]
    return {"unit": unit, "line": lines[0] if lines else "", "ok": bool(lines)}


def _recent_alerts(agent: AgentConfig, limit: int = 6) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for rel in agent.log_files:
        text = _tail_text(agent.root / rel, max_bytes=220_000)
        for index, line in enumerate(text.splitlines()[-200:]):
            if ALERT_RE.search(line):
                alerts.append(_log_line_to_event(agent, rel, line, index))
    alerts.sort(key=lambda item: item.get("ts") or "", reverse=True)
    return alerts[:limit]


def collect_summary() -> dict[str, Any]:
    runs = collect_runs(limit=120, include_events=False)
    agents_payload: list[dict[str, Any]] = []
    for agent in AGENTS:
        agent_runs = [run for run in runs if run["agent_id"] == agent.id]
        latest = agent_runs[0] if agent_runs else None
        agents_payload.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "root": str(agent.root),
                "accent": agent.accent,
                "services": [_service_status(unit) for unit in agent.service_units],
                "timers": [_timer_status(unit) for unit in agent.timer_units],
                "latest_run": latest,
                "recent_alerts": _recent_alerts(agent),
                "trace_enabled": bool(agent.trace_dir),
            }
        )
    return {
        "generated_at": _now_iso(),
        "agents": agents_payload,
        "metrics": {
            "agent_count": len(AGENTS),
            "active_services": sum(
                1 for agent in agents_payload for service in agent["services"] if service.get("active") == "active"
            ),
            "recent_runs": len(runs),
            "failed_runs": sum(1 for run in runs if run.get("status") == "failed"),
            "warning_runs": sum(1 for run in runs if run.get("status") == "warning"),
        },
    }


def collect_architecture() -> dict[str, Any]:
    return {
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "accent": agent.accent,
                "nodes": list(agent.architecture),
            }
            for agent in AGENTS
        ]
    }
