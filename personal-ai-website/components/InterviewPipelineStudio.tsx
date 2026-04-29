"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type InterviewResult = {
  ok: boolean;
  error?: string;
  elapsed_seconds?: number;
  interview?: {
    title: string;
    role: string;
    round: string;
    date: string;
    audio_url?: string;
  };
  result?: {
    task_id: string;
    status: string;
    summary: string;
    recommendation: string;
  };
  notion?: {
    page_id: string;
    page_url: string;
  } | null;
  page_markdown?: string;
  review_markdown?: string;
};

type HealthState = {
  loading: boolean;
  ok: boolean;
  message: string;
};

export function InterviewPipelineStudio() {
  const [health, setHealth] = useState<HealthState>({
    loading: true,
    ok: false,
    message: "正在检查面试复盘服务...",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InterviewResult | null>(null);
  const [fileName, setFileName] = useState("尚未选择文件");

  useEffect(() => {
    void fetch("/api/interview-pipeline/health")
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || "服务暂时不可用");
        }
        setHealth({
          loading: false,
          ok: true,
          message: "面试复盘服务已连接",
        });
      })
      .catch((fetchError: Error) => {
        setHealth({
          loading: false,
          ok: false,
          message: fetchError.message,
        });
      });
  }, []);

  const healthTone = useMemo(
    () => (health.loading ? "is-pending" : health.ok ? "is-ok" : "is-error"),
    [health]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData(event.currentTarget);
      const response = await fetch("/api/interview-pipeline/run", {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as InterviewResult;
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "处理失败，请检查服务配置。");
      }
      setResult(payload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "提交失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="tool-shell">
      <section className="tool-hero">
        <div>
          <p className="eyebrow">Integrated Workflow</p>
          <h1>面试复盘工作台</h1>
          <p className="tool-intro">
            直接在个人网站里发起录音处理，把转写、摘要、结构化面评和 Notion 草稿汇成同一个结果页。
          </p>
        </div>
        <div className={`service-chip ${healthTone}`}>{health.message}</div>
      </section>

      <div className="tool-layout">
        <form
          className="tool-panel"
          onSubmit={handleSubmit}
        >
          <div className="panel-heading">
            <h2>发起一次复盘</h2>
            <p>支持上传本地音频或直接填写音频 URL。</p>
          </div>

          <div className="field-grid">
            <label className="field">
              <span>候选人 / 标题</span>
              <input name="candidate" placeholder="可留空，系统会自动推断标题" />
            </label>
            <label className="field">
              <span>岗位</span>
              <input name="role" placeholder="例如：后端工程师" />
            </label>
            <label className="field">
              <span>轮次</span>
              <input name="round" placeholder="例如：一面 / 二面 / 终面" />
            </label>
            <label className="field">
              <span>日期</span>
              <input name="date" type="date" />
            </label>
          </div>

          <label className="field">
            <span>音频 URL</span>
            <input name="audio_url" placeholder="https://example.com/interview.m4a" />
          </label>

          <label className="upload-field">
            <input
              name="upload"
              type="file"
              accept="audio/*,.m4a,.mp3,.wav,.aac"
              onChange={(event) => setFileName(event.target.files?.[0]?.name || "尚未选择文件")}
            />
            <span className="upload-label">上传本地录音</span>
            <span className="upload-meta">{fileName}</span>
          </label>

          <div className="toggle-row">
            <label className="check-field">
              <input defaultChecked name="write_to_notion" type="checkbox" value="true" />
              <span>写入 Notion</span>
            </label>
            <label className="check-field">
              <input defaultChecked name="include_mock_review" type="checkbox" value="true" />
              <span>生成模拟复盘草稿</span>
            </label>
          </div>

          <button className="primary-button" disabled={isSubmitting || !health.ok} type="submit">
            {isSubmitting ? "处理中..." : "开始处理"}
          </button>
          {error ? <p className="error-text">{error}</p> : null}
        </form>

        <section className="tool-panel result-panel">
          <div className="panel-heading">
            <h2>处理结果</h2>
            <p>这里会返回摘要、推荐动作，以及可直接带走的文档草稿。</p>
          </div>

          {result ? (
            <div className="result-stack">
              <div className="result-summary">
                <div>
                  <p className="micro-label">标题</p>
                  <strong>{result.interview?.title}</strong>
                </div>
                <div>
                  <p className="micro-label">耗时</p>
                  <strong>{result.elapsed_seconds}s</strong>
                </div>
                <div>
                  <p className="micro-label">状态</p>
                  <strong>{result.result?.status}</strong>
                </div>
              </div>

              <article className="insight-card">
                <p className="micro-label">摘要</p>
                <p>{result.result?.summary}</p>
              </article>

              <article className="insight-card">
                <p className="micro-label">建议</p>
                <p>{result.result?.recommendation}</p>
              </article>

              {result.notion?.page_url ? (
                <a
                  className="secondary-link"
                  href={result.notion.page_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  打开 Notion 复盘页
                </a>
              ) : null}

              {result.page_markdown ? (
                <article className="markdown-card">
                  <p className="micro-label">页面草稿</p>
                  <pre>{result.page_markdown}</pre>
                </article>
              ) : null}

              {result.review_markdown ? (
                <article className="markdown-card">
                  <p className="micro-label">模拟复盘</p>
                  <pre>{result.review_markdown}</pre>
                </article>
              ) : null}
            </div>
          ) : (
            <div className="empty-tool-state">
              <p>提交录音后，这里会展示摘要、结构化草稿和 Notion 链接。</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

