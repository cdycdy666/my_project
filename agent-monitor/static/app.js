const state = {
  summary: null,
  architecture: null,
  runs: [],
  selectedAgent: "",
  selectedRunId: null,
  mode: "runs",
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
                <div class="run-title">${escapeHtml(run.title || run.trace_id)}</div>
                <span class="badge ${escapeHtml(run.status)}">${escapeHtml(statusText(run.status))}</span>
              </div>
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
  $("detailHeader").innerHTML = `
    <h2 class="detail-title">${escapeHtml(detail.agent_name)} · ${escapeHtml(detail.flow)}</h2>
    <div class="detail-subtitle">
      ${escapeHtml(detail.trace_id)} · ${formatTime(detail.started_at)} · ${formatDuration(detail.duration_ms)}
      · Events ${counters.events ?? 0} · LLM ${counters.llm ?? 0} · Tool ${counters.tools ?? 0} · Gate ${counters.gate_failures ?? 0}/${counters.gates ?? 0}
    </div>`;
  renderFlow(detail.events || [], false);
  renderInspector((detail.events || [])[state.selectedEventIndex] || (detail.events || [])[0]);
}

function renderArchitecture() {
  const agents = (state.architecture?.agents || []).filter((agent) => !state.selectedAgent || agent.id === state.selectedAgent);
  $("detailHeader").innerHTML = `
    <h2 class="detail-title">架构视图</h2>
    <div class="detail-subtitle">静态结构用于理解边界；点击运行记录可以切回真实执行轨迹。</div>`;
  const nodes = agents.flatMap((agent) =>
    (agent.nodes || []).map((node, index) => ({
      index: index + 1,
      kind: node.kind,
      label: `${agent.name}: ${node.label}`,
      summary: agent.role,
      raw: node,
    }))
  );
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
            </button>`;
        })
        .join("")}</div>`
    : `<div class="empty">没有可视化事件。</div>`;

  document.querySelectorAll(".flow-node").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedEventIndex = Number(node.dataset.index || 0);
      renderFlow(events, isArchitecture);
      renderInspector(events[state.selectedEventIndex]);
    });
  });
}

function renderInspector(event) {
  if (!event) {
    $("eventInspector").innerHTML = `<div class="empty">选择一段链路查看原始数据。</div>`;
    return;
  }
  $("eventInspector").innerHTML = `<pre>${escapeHtml(JSON.stringify(event.raw || event, null, 2))}</pre>`;
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
