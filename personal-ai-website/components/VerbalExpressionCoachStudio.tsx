"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type PracticeStatus = "queued" | "processing" | "done" | "failed";

type PracticeSummary = {
  id: string;
  title: string;
  status: PracticeStatus;
  created_at: string;
  updated_at: string;
};

type PracticeDetail = PracticeSummary & {
  focus_note?: string | null;
  reference_filename: string;
  attempt_filename: string;
  error_message?: string | null;
  analysis?: {
    summary: {
      overall_comment: string;
      total_score: number;
      confidence: number;
      provisional: boolean;
    };
    scores: Record<string, number>;
    strengths: Array<{ title: string; evidence: string }>;
    top_issues: Array<{
      title: string;
      severity: string;
      dimension: string;
      why_it_matters: string;
      fix: string;
    }>;
    next_task: {
      focus: string;
      instruction: string;
      drill: string;
    };
    rewrite_suggestions: Array<{
      original_attempt: string;
      suggested_version: string;
    }>;
    coach_message: string;
    pipeline_notes: string[];
  } | null;
};

const scoreLabels: Record<string, string> = {
  content_fidelity: "内容还原",
  structure_clarity: "结构清晰",
  language_naturalness: "语言自然",
  conciseness: "表达简洁",
  delivery_rhythm: "节奏表现",
  visual_presence: "镜头状态",
};

export function VerbalExpressionCoachStudio() {
  const [healthMessage, setHealthMessage] = useState("正在检查表达教练服务...");
  const [serviceReady, setServiceReady] = useState(false);
  const [history, setHistory] = useState<PracticeSummary[]>([]);
  const [activePractice, setActivePractice] = useState<PracticeDetail | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [referenceName, setReferenceName] = useState("尚未选择文件");
  const [attemptName, setAttemptName] = useState("尚未选择文件");
  const poller = useRef<number | null>(null);

  async function loadHistory(selectId?: string) {
    const response = await fetch("/api/verbal-coach/practices", { cache: "no-store" });
    const payload = (await response.json()) as PracticeSummary[] | { error?: string };
    if (!response.ok || !Array.isArray(payload)) {
      throw new Error(Array.isArray(payload) ? "加载历史失败" : payload.error || "加载历史失败");
    }
    setHistory(payload);
    const targetId = selectId || activePractice?.id || payload[0]?.id;
    if (targetId) {
      void loadPractice(targetId);
    }
  }

  async function loadPractice(practiceId: string) {
    const response = await fetch(`/api/verbal-coach/practices/${practiceId}`, {
      cache: "no-store",
    });
    const payload = (await response.json()) as PracticeDetail | { error?: string };
    if (!response.ok || !("id" in payload) || !("status" in payload)) {
      throw new Error("获取练习详情失败");
    }
    const practice = payload as PracticeDetail;
    setActivePractice(practice);
    if (practice.status === "done" || practice.status === "failed") {
      stopPolling();
    }
  }

  function stopPolling() {
    if (poller.current) {
      window.clearInterval(poller.current);
      poller.current = null;
    }
  }

  function startPolling(practiceId: string) {
    stopPolling();
    poller.current = window.setInterval(() => {
      void loadPractice(practiceId).catch(() => undefined);
      void loadHistory().catch(() => undefined);
    }, 2000);
  }

  useEffect(() => {
    void fetch("/api/verbal-coach/health")
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || "服务暂时不可用");
        }
        setServiceReady(true);
        setHealthMessage("表达教练服务已连接");
        return loadHistory();
      })
      .catch((fetchError: Error) => {
        setServiceReady(false);
        setHealthMessage(fetchError.message);
      });

    return () => stopPolling();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const formData = new FormData(event.currentTarget);
      const response = await fetch("/api/verbal-coach/practices", {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as { id?: string; detail?: string; error?: string };
      if (!response.ok || !payload.id) {
        throw new Error(payload.detail || payload.error || "创建练习失败");
      }
      event.currentTarget.reset();
      setReferenceName("尚未选择文件");
      setAttemptName("尚未选择文件");
      await loadHistory(payload.id);
      startPolling(payload.id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建练习失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="tool-shell">
      <section className="tool-hero">
        <div>
          <p className="eyebrow">Integrated Practice</p>
          <h1>表达模仿教练</h1>
          <p className="tool-intro">
            在个人网站里直接创建模仿练习，上传目标视频和练习视频，统一查看分析历史、问题列表和下一轮训练任务。
          </p>
        </div>
        <div className={`service-chip ${serviceReady ? "is-ok" : "is-error"}`}>{healthMessage}</div>
      </section>

      <div className="tool-layout coach-layout">
        <section className="tool-panel">
          <div className="panel-heading">
            <h2>新建练习</h2>
            <p>这一版会直接调用现有 FastAPI 服务，分析结果仍沿用当前训练模型。</p>
          </div>

          <form className="stack-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>本轮标题</span>
              <input name="title" placeholder="例如：模仿一段产品介绍视频" required />
            </label>
            <label className="field">
              <span>训练重点</span>
              <textarea name="focus_note" placeholder="例如：语速更稳、句子更短、镜头状态更自然" rows={4} />
            </label>

            <label className="upload-field">
              <input
                accept="video/*,.mp4,.mov,.m4v,.webm"
                name="reference_video"
                required
                type="file"
                onChange={(event) => setReferenceName(event.target.files?.[0]?.name || "尚未选择文件")}
              />
              <span className="upload-label">目标视频</span>
              <span className="upload-meta">{referenceName}</span>
            </label>

            <label className="upload-field">
              <input
                accept="video/*,.mp4,.mov,.m4v,.webm"
                name="attempt_video"
                required
                type="file"
                onChange={(event) => setAttemptName(event.target.files?.[0]?.name || "尚未选择文件")}
              />
              <span className="upload-label">模仿视频</span>
              <span className="upload-meta">{attemptName}</span>
            </label>

            <button className="primary-button" disabled={!serviceReady || isSubmitting} type="submit">
              {isSubmitting ? "创建中..." : "开始练习"}
            </button>
            {error ? <p className="error-text">{error}</p> : null}
          </form>
        </section>

        <section className="tool-panel">
          <div className="panel-heading">
            <h2>历史与报告</h2>
            <p>{history.length ? `${history.length} 条练习记录` : "还没有练习记录"}</p>
          </div>

          <div className="coach-history">
            {history.map((item) => (
              <button
                className={item.id === activePractice?.id ? "history-row is-active" : "history-row"}
                key={item.id}
                type="button"
                onClick={() => {
                  stopPolling();
                  void loadPractice(item.id);
                }}
              >
                <strong>{item.title}</strong>
                <span>
                  {item.status} · {new Date(item.updated_at).toLocaleString("zh-CN")}
                </span>
              </button>
            ))}
          </div>

          {activePractice ? (
            <div className="report-stack">
              <div className="result-summary">
                <div>
                  <p className="micro-label">总分</p>
                  <strong>{activePractice.analysis?.summary.total_score ?? "--"}</strong>
                </div>
                <div>
                  <p className="micro-label">状态</p>
                  <strong>{activePractice.status}</strong>
                </div>
                <div>
                  <p className="micro-label">可信度</p>
                  <strong>
                    {activePractice.analysis
                      ? `${Math.round(activePractice.analysis.summary.confidence * 100)}%`
                      : "--"}
                  </strong>
                </div>
              </div>

              <article className="insight-card">
                <p className="micro-label">总评</p>
                <p>
                  {activePractice.analysis?.summary.overall_comment ||
                    activePractice.error_message ||
                    "分析仍在处理中。"}
                </p>
              </article>

              {activePractice.analysis ? (
                <>
                  <div className="score-board">
                    {Object.entries(activePractice.analysis.scores).map(([key, value]) => (
                      <article className="score-bar-card" key={key}>
                        <div className="score-bar-top">
                          <span>{scoreLabels[key] || key}</span>
                          <strong>{value}</strong>
                        </div>
                        <div className="score-bar-track">
                          <span style={{ width: `${value}%` }} />
                        </div>
                      </article>
                    ))}
                  </div>

                  <div className="split-columns">
                    <article className="insight-card">
                      <p className="micro-label">优势</p>
                      <ul className="insight-list">
                        {activePractice.analysis.strengths.map((item) => (
                          <li key={item.title}>
                            <strong>{item.title}</strong>
                            <span>{item.evidence}</span>
                          </li>
                        ))}
                      </ul>
                    </article>

                    <article className="insight-card">
                      <p className="micro-label">主要问题</p>
                      <ul className="insight-list">
                        {activePractice.analysis.top_issues.map((issue) => (
                          <li key={issue.title}>
                            <strong>{issue.title}</strong>
                            <span>{issue.fix}</span>
                          </li>
                        ))}
                      </ul>
                    </article>
                  </div>

                  <article className="insight-card">
                    <p className="micro-label">下一轮任务</p>
                    <p>{activePractice.analysis.next_task.focus}</p>
                    <p>{activePractice.analysis.next_task.instruction}</p>
                    <p>{activePractice.analysis.next_task.drill}</p>
                  </article>
                </>
              ) : null}
            </div>
          ) : (
            <div className="empty-tool-state">
              <p>创建一条练习后，这里会出现分析历史和详细报告。</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

