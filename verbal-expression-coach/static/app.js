const form = document.querySelector("#practice-form");
const submitButton = document.querySelector("#submit-button");
const formStatus = document.querySelector("#form-status");
const historyList = document.querySelector("#history-list");
const historyCount = document.querySelector("#history-count");
const emptyState = document.querySelector("#empty-state");
const report = document.querySelector("#report");
const studioStatus = document.querySelector("#studio-status");
const liveDot = document.querySelector("#live-dot");
const reportDot = document.querySelector("#report-dot");

const reportTitle = document.querySelector("#report-title");
const reportStatus = document.querySelector("#report-status");
const reportLiveStatus = document.querySelector("#report-live-status");
const totalScore = document.querySelector("#total-score");
const confidenceBadge = document.querySelector("#confidence-badge");
const provisionalBadge = document.querySelector("#provisional-badge");
const overallComment = document.querySelector("#overall-comment");
const coachMessage = document.querySelector("#coach-message");
const scoreGrid = document.querySelector("#score-grid");
const strengths = document.querySelector("#strengths");
const issues = document.querySelector("#issues");
const nextTask = document.querySelector("#next-task");
const rewriteList = document.querySelector("#rewrite-list");
const pipelineNotes = document.querySelector("#pipeline-notes");

const referenceMetaTitle = document.querySelector("#reference-meta-title");
const referenceMetaSize = document.querySelector("#reference-meta-size");
const attemptMetaTitle = document.querySelector("#attempt-meta-title");
const attemptMetaSize = document.querySelector("#attempt-meta-size");

const referenceInput = document.querySelector("#reference-input");
const attemptInput = document.querySelector("#attempt-input");
const referenceFileName = document.querySelector("#reference-file-name");
const attemptFileName = document.querySelector("#attempt-file-name");

const scoreLabels = {
  content_fidelity: "内容还原",
  structure_clarity: "结构清晰",
  language_naturalness: "语言自然",
  conciseness: "表达简洁",
  delivery_rhythm: "节奏表现",
  visual_presence: "镜头状态",
};

let activePoller = null;
let activePracticeId = null;

referenceInput.addEventListener("change", () => {
  referenceFileName.textContent = referenceInput.files[0]?.name || "尚未选择文件";
});

attemptInput.addEventListener("change", () => {
  attemptFileName.textContent = attemptInput.files[0]?.name || "尚未选择文件";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  formStatus.textContent = "正在上传视频并创建练习...";
  setStudioTone("正在创建新练习", true);

  try {
    const formData = new FormData(form);
    const response = await fetch("/api/practices", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "创建练习失败");
    }

    const created = await response.json();
    activePracticeId = created.id;
    form.reset();
    referenceFileName.textContent = "尚未选择文件";
    attemptFileName.textContent = "尚未选择文件";
    formStatus.textContent = "练习已创建，正在生成本轮分析...";
    startPolling(created.id);
    await loadHistory();
  } catch (error) {
    formStatus.textContent = error.message;
    setStudioTone("创建失败", false);
  } finally {
    submitButton.disabled = false;
  }
});

async function loadHistory() {
  const response = await fetch("/api/practices");
  const items = await response.json();

  historyCount.textContent = `${items.length} 条练习`;

  if (!items.length) {
    historyList.innerHTML = `<p class="microcopy">还没有练习记录。</p>`;
    return;
  }

  historyList.innerHTML = "";
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-item";
    button.dataset.id = item.id;
    if (item.id === activePracticeId) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <p><strong>${escapeHtml(item.title)}</strong></p>
      <p class="microcopy">状态：${formatStatus(item.status)} · 更新时间：${formatDate(item.updated_at)}</p>
    `;
    button.addEventListener("click", () => {
      stopPolling();
      activePracticeId = item.id;
      updateHistorySelection();
      renderPractice(item.id);
    });
    historyList.appendChild(button);
  });
}

async function renderPractice(id) {
  const response = await fetch(`/api/practices/${id}`);
  if (!response.ok) {
    return;
  }

  const practice = await response.json();
  activePracticeId = practice.id;
  updateHistorySelection();

  emptyState.classList.add("hidden");
  report.classList.remove("hidden");

  reportTitle.textContent = practice.title;
  reportStatus.textContent = `${formatStatus(practice.status)} · 更新于 ${formatDate(practice.updated_at)}`;
  reportLiveStatus.textContent = getReportLiveStatus(practice.status, Boolean(practice.analysis));
  reportDot.classList.toggle("pulse", practice.status === "processing" || practice.status === "queued");

  if (practice.status === "failed") {
    totalScore.textContent = "--";
    confidenceBadge.textContent = "可信度 --";
    provisionalBadge.classList.add("hidden");
    overallComment.textContent = practice.error_message
      ? `分析任务失败：${practice.error_message}`
      : "分析任务失败，请稍后重试。";
    coachMessage.textContent = "这轮没有成功生成报告。建议检查视频文件或后端分析链路后重新提交。";
    referenceMetaTitle.textContent = practice.reference_filename;
    referenceMetaSize.textContent = "文件已上传";
    attemptMetaTitle.textContent = practice.attempt_filename;
    attemptMetaSize.textContent = "文件已上传";
    scoreGrid.innerHTML = "";
    strengths.innerHTML = "";
    issues.innerHTML = `
      <article class="issue-card">
        <div class="issue-meta">
          <span class="badge">system</span>
          <span class="badge high">failed</span>
        </div>
        <h4>本轮分析未完成</h4>
        <p>${escapeHtml(practice.error_message || "后台没有返回更多错误信息。")}</p>
        <p><strong>建议：</strong>检查视频格式是否受支持，或确认分析服务是否正常。</p>
      </article>
    `;
    nextTask.innerHTML = `
      <strong>重新提交分析</strong>
      <p>先确认输入文件可用，再重新发起这一轮练习。</p>
      <p>如果这个错误持续出现，优先检查后端分析日志。</p>
    `;
    rewriteList.innerHTML = "";
    pipelineNotes.innerHTML = `<li>失败态已中断当前轮询，界面保留输入文件信息与错误说明。</li>`;
    setStudioTone("分析失败", false);
    return;
  }

  if (!practice.analysis) {
    totalScore.textContent = "--";
    confidenceBadge.textContent = "可信度 --";
    provisionalBadge.classList.add("hidden");
    overallComment.textContent = "分析任务还在处理中，请稍后查看。";
    coachMessage.textContent = "等这轮报告出来后，这里会显示教练式提醒。";
    referenceMetaTitle.textContent = practice.reference_filename;
    referenceMetaSize.textContent = "文件已上传";
    attemptMetaTitle.textContent = practice.attempt_filename;
    attemptMetaSize.textContent = "文件已上传";
    scoreGrid.innerHTML = "";
    strengths.innerHTML = "";
    issues.innerHTML = "";
    nextTask.innerHTML = "";
    rewriteList.innerHTML = "";
    pipelineNotes.innerHTML = "";
    setStudioTone("分析进行中", true);
    return;
  }

  totalScore.textContent = practice.analysis.summary.total_score;
  confidenceBadge.textContent = `可信度 ${Math.round(practice.analysis.summary.confidence * 100)}%`;
  provisionalBadge.classList.toggle("hidden", !practice.analysis.summary.provisional);
  overallComment.textContent = practice.analysis.summary.overall_comment;
  coachMessage.textContent = practice.analysis.coach_message;

  referenceMetaTitle.textContent = practice.analysis.reference_video.filename;
  referenceMetaSize.textContent = `${practice.analysis.reference_video.size_mb} MB · ${practice.analysis.reference_video.suffix}`;
  attemptMetaTitle.textContent = practice.analysis.attempt_video.filename;
  attemptMetaSize.textContent = `${practice.analysis.attempt_video.size_mb} MB · ${practice.analysis.attempt_video.suffix}`;

  scoreGrid.innerHTML = Object.entries(practice.analysis.scores)
    .map(
      ([key, value]) => `
        <article class="score-item">
          <p class="microcopy">${scoreLabels[key] || key}</p>
          <strong>${value}</strong>
          <div class="score-line" style="--score:${value}">
            <span></span>
          </div>
        </article>
      `
    )
    .join("");

  strengths.innerHTML = practice.analysis.strengths
    .map(
      (item) => `
        <article class="strength-card">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.evidence)}</p>
        </article>
      `
    )
    .join("");

  issues.innerHTML = practice.analysis.top_issues
    .map(
      (issue) => `
        <article class="issue-card">
          <div class="issue-meta">
            <span class="badge">${escapeHtml(issue.dimension)}</span>
            <span class="badge ${escapeHtml(issue.severity)}">${escapeHtml(issue.severity)}</span>
          </div>
          <h4>${escapeHtml(issue.title)}</h4>
          <p>${escapeHtml(issue.why_it_matters)}</p>
          <p><strong>改法：</strong>${escapeHtml(issue.fix)}</p>
        </article>
      `
    )
    .join("");

  nextTask.innerHTML = `
    <strong>${escapeHtml(practice.analysis.next_task.focus)}</strong>
    <p>${escapeHtml(practice.analysis.next_task.instruction)}</p>
    <p>${escapeHtml(practice.analysis.next_task.drill)}</p>
  `;

  rewriteList.innerHTML = practice.analysis.rewrite_suggestions
    .map(
      (item) => `
        <article class="rewrite-card">
          <strong>原表达</strong>
          <p>${escapeHtml(item.original_attempt)}</p>
          <strong>建议版本</strong>
          <p>${escapeHtml(item.suggested_version)}</p>
        </article>
      `
    )
    .join("");

  pipelineNotes.innerHTML = practice.analysis.pipeline_notes
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");

  setStudioTone("报告已更新", false);
}

function startPolling(id) {
  stopPolling();

  renderPractice(id);
  activePoller = setInterval(async () => {
    const response = await fetch(`/api/practices/${id}`);
    if (!response.ok) {
      return;
    }

    const practice = await response.json();
    if (activePracticeId === id) {
      await renderPractice(id);
    }
    if (practice.status === "done" || practice.status === "failed") {
      stopPolling();
      formStatus.textContent =
        practice.status === "done" ? "分析完成，这轮报告已经就绪。" : "分析失败，请查看错误后重试。";
      setStudioTone(practice.status === "done" ? "系统待命" : "分析失败", false);
      await loadHistory();
    }
  }, 2000);
}

function stopPolling() {
  if (activePoller) {
    clearInterval(activePoller);
    activePoller = null;
  }
}

function setStudioTone(message, pulsing) {
  studioStatus.textContent = message;
  liveDot.classList.toggle("pulse", pulsing);
}

function updateHistorySelection() {
  historyList.querySelectorAll(".history-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.id === activePracticeId);
  });
}

function formatStatus(value) {
  return (
    {
      queued: "排队中",
      processing: "分析中",
      done: "已完成",
      failed: "失败",
    }[value] || value
  );
}

function getReportLiveStatus(status, hasAnalysis) {
  if (status === "failed") {
    return "分析失败";
  }
  if (hasAnalysis) {
    return "报告已生成";
  }
  return "分析任务处理中";
}

function formatDate(value) {
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

loadHistory();
