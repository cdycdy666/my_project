const state = {
  summary: null,
  architecture: null,
  runs: [],
  selectedAgent: "",
  selectedRunId: null,
  loadedRunId: null,
  mode: "runs",
  runTraceMode: "steps",
  inspectorTab: "summary",
  timeRange: "24h",
  statusFilter: "all",
  selectedEventIndex: 0,
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatDuration(ms) {
  if (!ms) return "-";
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

function statusText(status) {
  return {
    success: "success",
    warning: "warning",
    failed: "failed",
    running: "running",
  }[status] || status || "-";
}

function rangeLabel() {
  return { "24h": "过去 24 小时", "7d": "过去 7 天", all: "全部记录" }[state.timeRange] || "全部记录";
}

function rangeStart() {
  if (state.timeRange === "all") return null;
  const generated = state.summary?.generated_at ? new Date(state.summary.generated_at) : new Date();
  const hours = state.timeRange === "7d" ? 24 * 7 : 24;
  return new Date(generated.getTime() - hours * 60 * 60 * 1000);
}

function isWithinRange(value) {
  const start = rangeStart();
  if (!start) return true;
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return date >= start;
}

function visibleRuns() {
  return state.runs.filter((run) => {
    const time = run.ended_at || run.started_at;
    const timeOk = isWithinRange(time);
    const statusOk = state.statusFilter === "all" || run.status === state.statusFilter;
    return timeOk && statusOk;
  });
}

function pickDefaultRun(runs) {
  return runs.find((run) => run.kind === "trace") || runs[0] || null;
}

function runKind(run) {
  if (run.kind === "log") return "服务事件";
  if (run.agent_id === "reading") return "阅读推荐";
  if (run.agent_id === "podcast" && /论文|arxiv|paper/i.test(`${run.title} ${run.actions?.join(" ")}`)) return "论文解析";
  if (run.agent_id === "podcast") return "播客陪练";
  return "Agent 执行";
}

function runTitle(run) {
  const title = run.title || run.trace_id;
  if (run.kind === "log") {
    return title.replace(/^logs\//, "").replace(/\s+chat_id=.*/, "").slice(0, 90);
  }
  return title.slice(0, 110);
}

function runPath(run) {
  if (run.kind === "log") return ["日志"];
  const actions = (run.actions || []).join(" ").toLowerCase();
  const path = ["输入"];
  if (/context|personal/.test(actions)) path.push("读处境");
  if (/planner|agent_next_action/.test(actions)) path.push("规划");
  if (/weread|tool|search|fetch|verify|rss|arxiv/.test(actions)) path.push("工具");
  if (/llm|reply|scoring|score|draft/.test(actions)) path.push("LLM");
  if ((run.counters?.gates || 0) > 0) path.push("证据门");
  path.push("回复");
  return [...new Set(path)];
}

function runNote(run) {
  const counters = run.counters || {};
  if (run.status === "warning" && counters.gate_failures > 0) return "证据门曾失败，后续已重写或完成。";
  if (run.status === "failed") return "执行失败，需要查看节点输出或日志。";
  if (run.kind === "log") return "普通服务日志，未包含结构化模块输入输出。";
  return run.final_preview ? run.final_preview.replace(/\s+/g, " ").slice(0, 120) : "点击查看每个模块的输入与输出。";
}

function objectKeys(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? Object.keys(value) : [];
}

function ioFieldKeys(value) {
  if (!value) return [];
  if (typeof value !== "object") return ["text"];
  if (Array.isArray(value)) return [`array(${value.length})`];
  return Object.keys(value);
}

function nodeIoText(event) {
  const io = event.io || {};
  const input = ioFieldKeys(io.input).slice(0, 3);
  const output = ioFieldKeys(io.output).slice(0, 3);
  const moreInput = ioFieldKeys(io.input).length > input.length ? "+" : "";
  const moreOutput = ioFieldKeys(io.output).length > output.length ? "+" : "";
  if (!input.length && !output.length) return "";
  return [
    input.length ? `IN ${input.join(", ")}${moreInput}` : "",
    output.length ? `OUT ${output.join(", ")}${moreOutput}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function preferredEventIndex(events) {
  const issue = events.findIndex((event) => event.ok === false || event.kind === "warn" || event.kind === "error" || event.status === "warning" || event.status === "failed");
  if (issue >= 0) return issue;
  const important = [
    "llm_request",
    "llm_response",
    "agent_next_action",
    "tool_result",
    "weread_response",
    "evidence_aware_material_scoring",
    "final_reply",
    "final_reply_material_check",
  ];
  const exact = events.findIndex((event) => important.includes(event.event));
  if (exact >= 0) return exact;
  const byKind = events.findIndex((event) => ["llm", "tool", "planner", "gate", "warn"].includes(event.kind));
  return byKind >= 0 ? byKind : 0;
}

const STEP_DEFS = {
  input: { label: "用户输入", kind: "input", goal: "接收请求并建立本次运行上下文" },
  context: { label: "读取上下文", kind: "tool", goal: "读取个人处境、会话历史或基础状态" },
  planner: { label: "规划下一步", kind: "planner", goal: "让模型决定下一步工具或生成策略" },
  verification: { label: "材料验证", kind: "tool", goal: "调用外部工具验证书籍、播客、论文或证据材料" },
  evidence: { label: "回读证据", kind: "tool", goal: "读取更具体的原文、日记或详情片段" },
  scoring: { label: "材料打分", kind: "llm", goal: "比较候选材料并选择主要建议" },
  reply: { label: "生成回复", kind: "llm", goal: "基于已验证材料生成用户可读回复" },
  gate: { label: "证据门", kind: "gate", goal: "校验最终回复是否引用了未经验证的内容" },
  complete: { label: "完成", kind: "output", goal: "发出回复并记录执行结果" },
  other: { label: "辅助事件", kind: "event", goal: "补充进度、调试和运行状态" },
};

function rawEvent(event) {
  return event?.raw || event || {};
}

function eventName(event) {
  return String(event?.event || rawEvent(event).event || "");
}

function eventPurpose(event) {
  return String(rawEvent(event).purpose || event?.purpose || "");
}

function eventTool(event) {
  return String(rawEvent(event).tool || event?.tool || "");
}

function semanticStepId(event) {
  const name = eventName(event);
  const purpose = eventPurpose(event).toLowerCase();
  const tool = eventTool(event);
  const raw = rawEvent(event);
  const stage = String(raw.stage || raw.text || "").toLowerCase();

  if (name === "reply_start" || name === "log_line") return "input";
  if (name === "reply_complete" || name === "final_reply_sent") return "complete";
  if (name.includes("gate") || name.includes("check")) return "gate";
  if (purpose.includes("reply") || name === "final_reply") return "reply";
  if (purpose.includes("scoring") || name.includes("scoring")) return "scoring";
  if (tool === "personal.read_evidence" || name.includes("personal_evidence") || name.includes("episode_detail") || name.includes("paper_detail")) return "evidence";
  if (
    tool === "weread.verify_materials" ||
    name.includes("material_verification") ||
    name.includes("material_search") ||
    name.includes("verified_materials") ||
    name === "weread_request" ||
    name === "weread_response" ||
    /search|fetch|rss|arxiv|paper|episode/.test(tool)
  ) {
    return "verification";
  }
  if (purpose.includes("next_action") || name === "agent_next_action" || name === "agent_loop_turn") return "planner";
  if (tool === "personal.read_context" || tool === "weread.fetch_shelf" || name.includes("context_loaded") || name.includes("history")) return "context";
  if (name === "tool_call" && /context|history/.test(String(raw.tool || ""))) return "context";
  if (name === "progress" && /context|history/.test(stage)) return "context";
  if (name === "progress" && /verify|material|search|weread|rss|arxiv|paper/.test(stage)) return "verification";
  if (name === "progress" && /reply|draft|生成/.test(stage)) return "reply";
  return "other";
}

function eventIssueText(event) {
  const raw = rawEvent(event);
  const io = event?.io || {};
  const output = io.output || {};
  return raw.reason || output.reason || raw.error || output.error || raw.text || "";
}

function eventHasIssue(event) {
  return event?.ok === false || event?.kind === "warn" || event?.kind === "error" || Boolean(eventIssueText(event) && /fail|error|失败|拦截|blocked|denied/i.test(eventIssueText(event)));
}

function compactEventIo(event, side) {
  const io = event?.io || {};
  const value = io[side];
  if (!ioHasContent(value)) return null;
  return {
    event: eventName(event) || event?.label || "event",
    label: event?.label || eventName(event) || "event",
    kind: event?.kind || "event",
    value,
  };
}

function collectPromptMessages(event) {
  const sourceEvents = event?.events || event?.rawEvents || [event];
  const messages = [];
  sourceEvents.forEach((item) => {
    const raw = rawEvent(item);
    const io = item?.io || {};
    const requestPayload = io.input?.request_payload || raw.request_payload || {};
    const directMessages = io.input?.messages || raw.messages || requestPayload.messages;
    if (Array.isArray(directMessages)) {
      messages.push(...directMessages.map((message) => ({ ...message, _event: item.label || item.event || raw.event })));
    }
  });
  return messages;
}

function buildSemanticSteps(events) {
  const order = ["input", "context", "planner", "verification", "evidence", "scoring", "reply", "gate", "complete", "other"];
  const buckets = new Map(order.map((id) => [id, []]));
  events.forEach((event) => {
    const id = semanticStepId(event);
    buckets.get(id)?.push(event);
  });

  return order
    .map((id) => {
      const groupedEvents = buckets.get(id) || [];
      if (!groupedEvents.length) return null;
      const def = STEP_DEFS[id] || STEP_DEFS.other;
      const issueEvents = groupedEvents.filter(eventHasIssue);
      const inputItems = groupedEvents.map((event) => compactEventIo(event, "input")).filter(Boolean);
      const outputItems = groupedEvents.map((event) => compactEventIo(event, "output")).filter(Boolean);
      const status = issueEvents.length ? "warning" : groupedEvents.some((event) => event.ok === true) ? "success" : "event";
      return {
        index: order.indexOf(id) + 1,
        event: `semantic_${id}`,
        kind: issueEvents.length ? "warn" : def.kind,
        status,
        ok: issueEvents.length ? false : undefined,
        label: def.label,
        summary: `${def.goal} · ${groupedEvents.length} events`,
        ts: groupedEvents[0]?.ts,
        events: groupedEvents,
        rawEvents: groupedEvents.map((event) => event.raw || event),
        io: {
          input: {
            goal: def.goal,
            event_count: groupedEvents.length,
            key_inputs: inputItems.slice(0, 18),
          },
          output: {
            key_outputs: outputItems.slice(0, 18),
            issues: issueEvents.map((event) => ({
              event: eventName(event),
              label: event.label,
              reason: eventIssueText(event),
            })),
          },
          meta: {
            mode: "semantic_step",
            raw_event_count: groupedEvents.length,
            raw_events: groupedEvents.map((event) => ({
              index: event.index,
              event: eventName(event),
              label: event.label,
              kind: event.kind,
              ok: event.ok,
            })),
          },
        },
      };
    })
    .filter(Boolean);
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function refresh() {
  $("lastUpdated").textContent = "refreshing";
  const [summary, runs, architecture] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson(`/api/runs?limit=220${state.selectedAgent ? `&agent=${state.selectedAgent}` : ""}`),
    fetchJson("/api/architecture"),
  ]);
  state.summary = summary;
  state.runs = runs.runs || [];
  state.architecture = architecture;
  $("lastUpdated").textContent = `updated ${formatTime(summary.generated_at)}`;
  renderAll();
}

function renderAll() {
  renderAgents();
  renderMetrics();
  renderAlerts();
  renderRuns();
  if (state.mode === "architecture") {
    renderArchitecture();
  } else if (visibleRuns().some((run) => run.trace_id === state.selectedRunId)) {
    loadRunDetail(state.selectedRunId);
  } else if (pickDefaultRun(visibleRuns())) {
    state.selectedRunId = pickDefaultRun(visibleRuns()).trace_id;
    loadRunDetail(state.selectedRunId);
  } else {
    renderEmptyDetail();
  }
}

function renderAgents() {
  const agents = state.summary?.agents || [];
  const activeServices = state.summary?.metrics?.active_services ?? 0;
  const allCard = `
    <article class="agent-card all-card ${state.selectedAgent ? "" : "active"}" data-agent="" style="--accent:var(--cyan)">
      <h2>All Agents</h2>
      <div class="agent-role">跨服务运行记录、证据门和错误信号总览</div>
      <div class="status-line">
        <span><span class="dot ${activeServices ? "good" : "warn"}"></span> ${activeServices}/${agents.length} active</span>
        <span>${rangeLabel()}</span>
      </div>
    </article>`;
  const agentCards = agents
    .map((agent) => {
      const service = agent.services?.[0] || {};
      const statusClass = service.active === "active" ? "good" : service.active === "unknown" ? "warn" : "bad";
      const active = state.selectedAgent === agent.id ? "active" : "";
      return `
        <article class="agent-card ${active}" data-agent="${agent.id}" style="--accent:${agent.accent}">
          <h2>${escapeHtml(agent.name)}</h2>
          <div class="agent-role">${escapeHtml(agent.role)}</div>
          <div class="status-line">
            <span><span class="dot ${statusClass}"></span> ${escapeHtml(service.active || "unknown")}</span>
            <span>${agent.trace_enabled ? "trace on" : "log only"}</span>
          </div>
        </article>`;
    })
    .join("");
  $("agentList").innerHTML = allCard + agentCards;

  document.querySelectorAll(".agent-card").forEach((card) => {
    card.addEventListener("click", async () => {
      state.selectedAgent = card.dataset.agent || "";
      state.selectedRunId = null;
      state.loadedRunId = null;
      await refresh();
    });
  });
}

function renderMetrics() {
  const metrics = state.summary?.metrics || {};
  const runs = visibleRuns();
  const rows = [
    ["Agents", metrics.agent_count ?? 0],
    ["Active", metrics.active_services ?? 0],
    [state.timeRange === "all" ? "Runs" : state.timeRange, runs.length],
    ["Warnings", runs.filter((run) => run.status === "warning").length],
    ["Failures", runs.filter((run) => run.status === "failed").length],
  ];
  $("metrics").innerHTML = rows
    .map(
      ([label, value]) => `
        <div class="metric">
          <div class="section-title">${escapeHtml(label)}</div>
          <div class="metric-value">${escapeHtml(value)}</div>
        </div>`
    )
    .join("");
}

function renderAlerts() {
  const start = rangeStart();
  const alerts = (state.summary?.agents || [])
    .filter((agent) => !state.selectedAgent || agent.id === state.selectedAgent)
    .flatMap((agent) => (agent.recent_alerts || []).map((alert) => ({ ...alert, agentName: agent.name })))
    .filter((alert) => (start ? isWithinRange(alert.ts) : true))
    .slice(0, 8);
  $("alertList").innerHTML = alerts.length
    ? alerts
        .map(
          (alert) => `
            <div class="alert-item">
              <div class="badge failed">${escapeHtml(alert.agentName)}</div>
              <div style="margin-top:8px">${escapeHtml(alert.text || alert.source || "alert")}</div>
            </div>`
        )
        .join("")
    : `<div class="alert-item">${rangeLabel()}没有错误级日志。</div>`;
}

function renderRuns() {
  const runs = visibleRuns();
  const agentName = state.selectedAgent
    ? state.summary?.agents?.find((agent) => agent.id === state.selectedAgent)?.name || state.selectedAgent
    : "All Agents";
  $("scopeLabel").textContent = `${agentName} · ${rangeLabel()} · ${state.statusFilter === "all" ? "全部状态" : state.statusFilter}`;
  $("runList").innerHTML = runs.length
    ? runs
        .map((run) => {
          const counters = run.counters || {};
          const active = run.trace_id === state.selectedRunId ? "active" : "";
          return `
            <article class="run-row ${active}" data-run="${escapeHtml(run.trace_id)}">
              <div class="run-top">
                <div>
                  <div class="run-kind">${escapeHtml(runKind(run))}</div>
                  <div class="run-title">${escapeHtml(runTitle(run))}</div>
                </div>
                <span class="badge ${escapeHtml(run.status)}">${escapeHtml(statusText(run.status))}</span>
              </div>
              <div class="run-path">
                ${runPath(run)
                  .map((step) => `<span class="path-step">${escapeHtml(step)}</span>`)
                  .join("")}
              </div>
              <div class="run-note">${escapeHtml(runNote(run))}</div>
              <div class="run-meta">
                <span>${escapeHtml(run.agent_name)}</span>
                <span>${escapeHtml(run.kind)}</span>
                <span>${formatTime(run.started_at || run.ended_at)}</span>
                <span>${formatDuration(run.duration_ms)}</span>
                <span>LLM ${counters.llm ?? 0}</span>
                <span>Tool ${counters.tools ?? 0}</span>
                <span>Gate ${counters.gate_failures ?? 0}/${counters.gates ?? 0}</span>
              </div>
            </article>`;
        })
        .join("")
    : `<div class="empty">没有找到运行记录。</div>`;

  document.querySelectorAll(".run-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.mode = "runs";
      state.selectedRunId = row.dataset.run;
      state.loadedRunId = null;
      setModeButtons();
      loadRunDetail(state.selectedRunId);
      renderRuns();
    });
  });
}

async function loadRunDetail(traceId) {
  if (!traceId) return;
  try {
    const detail = await fetchJson(`/api/runs/${encodeURIComponent(traceId)}`);
    renderRunDetail(detail);
  } catch (error) {
    renderEmptyDetail(`加载失败：${error.message}`);
  }
}

function renderRunDetail(detail) {
  const counters = detail.counters || {};
  const events = detail.events || [];
  const flowEvents = state.runTraceMode === "events" ? events : buildSemanticSteps(events);
  if (state.loadedRunId !== detail.trace_id) {
    state.selectedEventIndex = preferredEventIndex(flowEvents);
    state.loadedRunId = detail.trace_id;
  }
  $("detailHeader").innerHTML = `
    <div class="detail-title-row">
      <div>
        <h2 class="detail-title">${escapeHtml(detail.agent_name)} · ${escapeHtml(detail.flow)}</h2>
        <div class="detail-subtitle">
          ${escapeHtml(detail.trace_id)} · ${formatTime(detail.started_at)} · ${formatDuration(detail.duration_ms)}
          · Events ${counters.events ?? 0} · LLM ${counters.llm ?? 0} · Tool ${counters.tools ?? 0} · Gate ${counters.gate_failures ?? 0}/${counters.gates ?? 0}
        </div>
      </div>
      <div class="segmented micro" role="group" aria-label="运行记录粒度">
        <button class="seg mini ${state.runTraceMode === "steps" ? "active" : ""}" data-trace-mode="steps" type="button">步骤链</button>
        <button class="seg mini ${state.runTraceMode === "events" ? "active" : ""}" data-trace-mode="events" type="button">原始事件</button>
      </div>
    </div>`;
  document.querySelectorAll("[data-trace-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.runTraceMode = button.dataset.traceMode || "steps";
      state.loadedRunId = null;
      state.inspectorTab = "summary";
      renderRunDetail(detail);
    });
  });
  renderFlow(flowEvents, false);
  renderInspector(flowEvents[state.selectedEventIndex] || flowEvents[0]);
}

function renderArchitecture() {
  const agents = (state.architecture?.agents || []).filter((agent) => !state.selectedAgent || agent.id === state.selectedAgent);
  $("detailHeader").innerHTML = `
    <h2 class="detail-title">架构视图</h2>
    <div class="detail-subtitle">语义级步骤用于理解系统边界、预期输入输出和风险；运行记录保留事件级 trace。</div>`;
  const nodes = agents.flatMap((agent) =>
    (agent.nodes || []).map((node, index) => ({
      index: index + 1,
      kind: node.kind,
      label: `${agent.name}: ${node.label}`,
      summary: node.goal || agent.role,
      event: "architecture_step",
      io: {
        input: {
          goal: node.goal,
          expected_input: node.input || [],
        },
        output: {
          expected_output: node.output || [],
          risk: node.risk || [],
        },
        meta: {
          agent: agent.name,
          step_id: node.id,
          dependencies: node.depends || [],
          role: agent.role,
        },
      },
      raw: node,
    }))
  );
  state.inspectorTab = "summary";
  renderFlow(nodes, true);
  renderInspector(nodes[0]);
}

function renderFlow(events, isArchitecture) {
  state.selectedEventIndex = Math.min(state.selectedEventIndex, Math.max(events.length - 1, 0));
  $("flowView").innerHTML = events.length
    ? `<div class="flow-track">${events
        .map((event, index) => {
          const selected = index === state.selectedEventIndex ? "selected" : "";
          const kind = event.kind || "event";
          return `
            <button class="flow-node ${escapeHtml(kind)} ${selected}" data-index="${index}" type="button">
              <div class="node-kind">${escapeHtml(kind)}</div>
              <div class="node-label">${escapeHtml(event.label || event.event || "event")}</div>
              <div class="node-summary">${escapeHtml(event.summary || event.ts || "")}</div>
              ${nodeIoText(event) ? `<div class="node-io">${escapeHtml(nodeIoText(event))}</div>` : ""}
            </button>`;
        })
        .join("")}</div>`
    : `<div class="empty">没有可视化事件。</div>`;

  document.querySelectorAll(".flow-node").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedEventIndex = Number(node.dataset.index || 0);
      state.inspectorTab = "summary";
      renderFlow(events, isArchitecture);
      renderInspector(events[state.selectedEventIndex]);
    });
  });
}

function describeValue(value) {
  if (Array.isArray(value)) return `array · ${value.length}`;
  if (value && typeof value === "object") return `object · ${Object.keys(value).length}`;
  if (typeof value === "string") return `text · ${value.length}`;
  if (value === null || value === undefined) return "empty";
  return typeof value;
}

function renderPrimitive(value) {
  return `<pre>${escapeHtml(value)}</pre>`;
}

function isChatMessages(key, value) {
  return (
    key === "messages" &&
    Array.isArray(value) &&
    value.every((item) => item && typeof item === "object" && ("role" in item || "content" in item))
  );
}

function renderMessages(value) {
  return `<div class="message-stack">${value
    .map((message, index) => {
      const role = message.role || `message ${index + 1}`;
      const content = typeof message.content === "string" ? message.content : JSON.stringify(message.content, null, 2);
      const rest = Object.fromEntries(Object.entries(message).filter(([key]) => !["role", "content"].includes(key)));
      return `
        <article class="message-card">
          <div class="message-role">${escapeHtml(role)}</div>
          <pre>${escapeHtml(content || "")}</pre>
          ${Object.keys(rest).length ? `<pre class="message-extra">${escapeHtml(JSON.stringify(rest, null, 2))}</pre>` : ""}
        </article>`;
    })
    .join("")}</div>`;
}

function previewText(value) {
  if (value === null || value === undefined || value === "") return "empty";
  if (typeof value === "string") return value.replace(/\s+/g, " ").slice(0, 360);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    if (isChatMessages("messages", value)) {
      return value
        .map((message) => `${message.role || "message"}: ${typeof message.content === "string" ? message.content : JSON.stringify(message.content)}`)
        .join(" | ")
        .replace(/\s+/g, " ")
        .slice(0, 360);
    }
    return `array(${value.length}) ${JSON.stringify(value.slice(0, 2), null, 0).slice(0, 300)}`;
  }
  if (typeof value === "object") {
    const preferred = ["response_text", "text", "content", "preview", "raw_text", "reason", "query", "summary"];
    const key = preferred.find((item) => typeof value[item] === "string" && value[item]);
    if (key) return `${key}: ${String(value[key]).replace(/\s+/g, " ").slice(0, 320)}`;
    return `object(${objectKeys(value).length}) ${objectKeys(value).slice(0, 8).join(", ")}`;
  }
  return String(value);
}

function renderIoPreview(title, value) {
  if (!ioHasContent(value)) {
    return `
      <section class="io-preview-card">
        <div class="io-preview-title">${escapeHtml(title)}</div>
        <div class="io-preview-empty">empty</div>
      </section>`;
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    return `
      <section class="io-preview-card">
        <div class="io-preview-title">${escapeHtml(title)}</div>
        <div class="io-preview-row">
          <span class="field-name">value</span>
          <span>${escapeHtml(previewText(value))}</span>
        </div>
      </section>`;
  }
  return `
    <section class="io-preview-card">
      <div class="io-preview-title">${escapeHtml(title)}</div>
      ${Object.entries(value)
        .map(
          ([key, fieldValue]) => `
            <div class="io-preview-row">
              <span class="field-name">${escapeHtml(key)}</span>
              <span>${escapeHtml(previewText(fieldValue))}</span>
            </div>`
        )
        .join("")}
    </section>`;
}

function renderField(key, value) {
  const body = isChatMessages(key, value)
    ? renderMessages(value)
    : value && typeof value === "object"
      ? `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`
      : renderPrimitive(value);
  return `
    <details class="value-section" open>
      <summary>
        <span class="field-name">${escapeHtml(key)}</span>
        <span class="field-type">${escapeHtml(describeValue(value))}</span>
      </summary>
      ${body}
    </details>`;
}

function renderValue(value) {
  if (value === null || value === undefined || value === "") {
    return `<div class="io-empty">empty</div>`;
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return renderPrimitive(value);
  }
  if (!Array.isArray(value) && typeof value === "object") {
    return `<div class="value-sections">${Object.entries(value)
      .map(([key, fieldValue]) => renderField(key, fieldValue))
      .join("")}</div>`;
  }
  return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function ioHasContent(value) {
  if (!value) return false;
  if (typeof value !== "object") return true;
  return Object.keys(value).length > 0;
}

function availableInspectorTabs(event, io) {
  const tabs = [
    { id: "summary", label: "Summary" },
    { id: "input", label: "Input" },
    { id: "output", label: "Output" },
  ];
  if (collectPromptMessages(event).length) tabs.push({ id: "prompt", label: "Prompt" });
  if (ioHasContent(io.meta)) tabs.push({ id: "meta", label: "Meta" });
  tabs.push({ id: "raw", label: "Raw" });
  return tabs;
}

function renderEventList(events) {
  if (!events?.length) return "";
  return `
    <div class="event-list">
      ${events
        .map(
          (event) => `
            <div class="event-list-row">
              <span>#${escapeHtml(event.index || "-")}</span>
              <span>${escapeHtml(event.kind || "event")}</span>
              <strong>${escapeHtml(event.label || event.event || "event")}</strong>
              ${event.ok === false ? `<em>failed</em>` : ""}
            </div>`
        )
        .join("")}
    </div>`;
}

function renderInspectorSummary(event, io, status) {
  const childEvents = event.events || [];
  const issueItems = childEvents.length ? childEvents.filter(eventHasIssue) : eventHasIssue(event) ? [event] : [];
  return `
    <div class="summary-grid">
      <section class="summary-card">
        <div class="io-title">节点状态</div>
        <div class="summary-line"><span>status</span><strong>${escapeHtml(status)}</strong></div>
        <div class="summary-line"><span>kind</span><strong>${escapeHtml(event.kind || "event")}</strong></div>
        <div class="summary-line"><span>events</span><strong>${escapeHtml(childEvents.length || 1)}</strong></div>
      </section>
      <section class="summary-card">
        <div class="io-title">关键判断</div>
        ${
          issueItems.length
            ? issueItems
                .map((item) => `<div class="issue-line">${escapeHtml(item.label || eventName(item))}: ${escapeHtml(eventIssueText(item) || "needs attention")}</div>`)
                .join("")
            : `<div class="io-preview-empty">没有失败或拦截信号。</div>`
        }
      </section>
    </div>
    <div class="io-preview-grid">
      ${renderIoPreview("输入预览", io.input)}
      ${renderIoPreview("输出预览", io.output)}
    </div>
    ${
      childEvents.length
        ? `<section class="io-card"><div class="io-title">包含的原始事件</div>${renderEventList(childEvents)}</section>`
        : ""
    }`;
}

function renderPromptTab(event) {
  const messages = collectPromptMessages(event);
  if (!messages.length) {
    return `<div class="empty">这个节点没有记录 LLM messages。</div>`;
  }
  return renderMessages(messages);
}

function renderInspectorTab(event, io, status, activeTab) {
  if (activeTab === "summary") return renderInspectorSummary(event, io, status);
  if (activeTab === "input") {
    return `<section class="io-card input-card single-card"><div class="io-title">输入</div>${renderValue(ioHasContent(io.input) ? io.input : "这个节点没有记录明确输入。")}</section>`;
  }
  if (activeTab === "output") {
    return `<section class="io-card output-card single-card"><div class="io-title">输出</div>${renderValue(ioHasContent(io.output) ? io.output : "这个节点没有记录明确输出。")}</section>`;
  }
  if (activeTab === "prompt") {
    return `<section class="io-card single-card"><div class="io-title">Prompt Messages</div>${renderPromptTab(event)}</section>`;
  }
  if (activeTab === "meta") {
    return `<section class="io-card meta-card single-card"><div class="io-title">元信息</div>${renderValue(io.meta)}</section>`;
  }
  return `<section class="io-card single-card"><div class="io-title">Raw JSON</div>${renderValue(event.rawEvents || event.raw || event)}</section>`;
}

function renderInspector(event) {
  if (!event) {
    $("eventInspector").innerHTML = `<div class="empty">选择一段链路查看原始数据。</div>`;
    return;
  }
  const io = event.io || {
    input: event.raw || event,
    output: {},
    meta: {},
  };
  const status = event.ok === false ? "failed" : event.ok === true ? "success" : event.kind || "event";
  const tabs = availableInspectorTabs(event, io);
  const activeTab = tabs.some((tab) => tab.id === state.inspectorTab) ? state.inspectorTab : "summary";
  $("eventInspector").innerHTML = `
    <div class="inspector-head">
      <div>
        <div class="section-title">Node Inspector</div>
        <h3>${escapeHtml(event.label || event.event || "event")}</h3>
      </div>
      <span class="badge ${escapeHtml(status)}">${escapeHtml(status)}</span>
    </div>
    <div class="inspector-meta">
      <span>#${escapeHtml(event.index || "-")}</span>
      <span>${escapeHtml(event.kind || "event")}</span>
      <span>${formatTime(event.ts)}</span>
      ${event.summary ? `<span>${escapeHtml(event.summary)}</span>` : ""}
    </div>
    <div class="inspector-tabs" role="tablist" aria-label="节点详情">
      ${tabs
        .map(
          (tab) => `<button class="inspector-tab ${tab.id === activeTab ? "active" : ""}" data-inspector-tab="${tab.id}" type="button">${escapeHtml(tab.label)}</button>`
        )
        .join("")}
    </div>
    <div class="inspector-body">${renderInspectorTab(event, io, status, activeTab)}</div>`;

  document.querySelectorAll("[data-inspector-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.inspectorTab = button.dataset.inspectorTab || "summary";
      renderInspector(event);
    });
  });
}

function renderEmptyDetail(message = "暂无可展示细节。") {
  $("detailHeader").innerHTML = `<h2 class="detail-title">没有选中的运行</h2><div class="detail-subtitle">${escapeHtml(message)}</div>`;
  $("flowView").innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
  $("eventInspector").innerHTML = "";
}

function setModeButtons() {
  $("showRunsBtn").classList.toggle("active", state.mode === "runs");
  $("showArchBtn").classList.toggle("active", state.mode === "architecture");
}

$("refreshBtn").addEventListener("click", () => refresh().catch((error) => renderEmptyDetail(error.message)));
$("showRunsBtn").addEventListener("click", () => {
  state.mode = "runs";
  setModeButtons();
  renderAll();
});
$("showArchBtn").addEventListener("click", () => {
  state.mode = "architecture";
  state.selectedRunId = null;
  setModeButtons();
  renderArchitecture();
});
document.querySelectorAll("[data-range]").forEach((button) => {
  button.addEventListener("click", () => {
    state.timeRange = button.dataset.range || "24h";
    state.selectedRunId = null;
    document.querySelectorAll("[data-range]").forEach((item) => item.classList.toggle("active", item === button));
    renderAll();
  });
});
document.querySelectorAll("[data-status]").forEach((button) => {
  button.addEventListener("click", () => {
    state.statusFilter = button.dataset.status || "all";
    state.selectedRunId = null;
    document.querySelectorAll("[data-status]").forEach((item) => item.classList.toggle("active", item === button));
    renderAll();
  });
});

refresh().catch((error) => {
  $("lastUpdated").textContent = "load failed";
  renderEmptyDetail(error.message);
});
