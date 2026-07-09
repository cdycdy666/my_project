const state = {
  summary: null,
  architecture: null,
  runs: [],
  selectedAgent: "",
  selectedRunId: null,
  mode: "runs",
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
  renderAgentFilter();
  renderAgents();
  renderMetrics();
  renderAlerts();
  renderRuns();
  if (state.mode === "architecture") {
    renderArchitecture();
  } else if (state.selectedRunId) {
    loadRunDetail(state.selectedRunId);
  } else if (state.runs[0]) {
    state.selectedRunId = state.runs[0].trace_id;
    loadRunDetail(state.selectedRunId);
  } else {
    renderEmptyDetail();
  }
}

function renderAgentFilter() {
  const select = $("agentFilter");
  const current = select.value || state.selectedAgent;
  select.innerHTML = `<option value="">All agents</option>${(state.summary?.agents || [])
    .map((agent) => `<option value="${agent.id}">${escapeHtml(agent.name)}</option>`)
    .join("")}`;
  select.value = current;
}

function renderAgents() {
  const agents = state.summary?.agents || [];
  $("agentList").innerHTML = agents
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

  document.querySelectorAll(".agent-card").forEach((card) => {
    card.addEventListener("click", async () => {
      state.selectedAgent = card.dataset.agent === state.selectedAgent ? "" : card.dataset.agent;
      state.selectedRunId = null;
      await refresh();
    });
  });
}

function renderMetrics() {
  const metrics = state.summary?.metrics || {};
  const rows = [
    ["Agents", metrics.agent_count ?? 0],
    ["Active services", metrics.active_services ?? 0],
    ["Recent runs", metrics.recent_runs ?? 0],
    ["Warnings", metrics.warning_runs ?? 0],
    ["Failures", metrics.failed_runs ?? 0],
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
  const alerts = (state.summary?.agents || [])
    .filter((agent) => !state.selectedAgent || agent.id === state.selectedAgent)
    .flatMap((agent) => (agent.recent_alerts || []).map((alert) => ({ ...alert, agentName: agent.name })))
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
    : `<div class="alert-item">最近没有错误级日志。</div>`;
}

function renderRuns() {
  const runs = state.runs;
  $("runList").innerHTML = runs.length
    ? runs
        .map((run) => {
          const counters = run.counters || {};
          const active = run.trace_id === state.selectedRunId ? "active" : "";
          return `
            <article class="run-row ${active}" data-run="${escapeHtml(run.trace_id)}">
              <div class="run-top">
                <div class="run-title">${escapeHtml(run.title || run.trace_id)}</div>
                <span class="badge ${escapeHtml(run.status)}">${escapeHtml(run.status)}</span>
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
    <h2 class="detail-title">Architecture Map</h2>
    <div class="detail-subtitle">静态结构用于理解边界；点击 Runs 可以切回真实执行轨迹。</div>`;
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
  $("detailHeader").innerHTML = `<h2 class="detail-title">No Run Selected</h2><div class="detail-subtitle">${escapeHtml(message)}</div>`;
  $("flowView").innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
  $("eventInspector").innerHTML = "";
}

function setModeButtons() {
  $("showRunsBtn").classList.toggle("active", state.mode === "runs");
  $("showArchBtn").classList.toggle("active", state.mode === "architecture");
}

$("refreshBtn").addEventListener("click", () => refresh().catch((error) => renderEmptyDetail(error.message)));
$("agentFilter").addEventListener("change", async (event) => {
  state.selectedAgent = event.target.value;
  state.selectedRunId = null;
  await refresh();
});
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

refresh().catch((error) => {
  $("lastUpdated").textContent = "load failed";
  renderEmptyDetail(error.message);
});
