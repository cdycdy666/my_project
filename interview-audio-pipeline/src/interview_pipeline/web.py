from __future__ import annotations

import cgi
import json
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .pipeline import execute_pipeline


def serve_web_app(*, host: str = "127.0.0.1", port: int = 8787, env_file: str = ".env") -> None:
    server = ThreadingHTTPServer((host, port), _build_handler(env_file))
    print(f"Interview pipeline web app running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _build_handler(env_file: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route == "/":
                self._send_html(INDEX_HTML)
                return
            if route == "/api/health":
                self._send_json({"ok": True, "service": "interview-pipeline-web"})
                return
            self.send_error(404, "Not Found")

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route != "/api/run":
                self.send_error(404, "Not Found")
                return

            started_at = time.monotonic()
            temp_path: Path | None = None
            try:
                payload = self._parse_request_body()
                upload = payload.get("upload")
                if upload:
                    temp_path = _persist_upload(upload)

                outcome = execute_pipeline(
                    env_file=env_file,
                    audio_file=str(temp_path) if temp_path else _clean_text(payload.get("audio_file")),
                    audio_url=_clean_text(payload.get("audio_url")),
                    candidate=_clean_text(payload.get("candidate")),
                    role=_clean_text(payload.get("role")),
                    round_name=_clean_text(payload.get("round")),
                    interview_date_text=_clean_text(payload.get("date")),
                    write_to_notion=_to_bool(payload.get("write_to_notion"), default=True),
                    include_mock_review=_to_bool(payload.get("include_mock_review"), default=True),
                )
                elapsed_seconds = round(time.monotonic() - started_at, 2)
                self._send_json(
                    {
                        "ok": True,
                        "elapsed_seconds": elapsed_seconds,
                        "interview": {
                            "title": outcome.interview.record_title(),
                            "role": outcome.interview.role,
                            "round": outcome.interview.round,
                            "date": outcome.interview.interview_date.isoformat(),
                            "audio_url": outcome.interview.audio_url,
                        },
                        "result": {
                            "task_id": outcome.result.task_id,
                            "status": outcome.result.status,
                            "summary": outcome.assessment.summary,
                            "recommendation": outcome.assessment.recommendation,
                        },
                        "notion": {
                            "page_id": outcome.notion_page["id"],
                            "page_url": outcome.notion_page["url"],
                        }
                        if outcome.notion_page
                        else None,
                        "page_markdown": outcome.page_markdown,
                        "review_markdown": outcome.review_markdown,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                self._send_json(
                    {
                        "ok": False,
                        "error": str(exc),
                    },
                    status=500,
                )
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _parse_request_body(self) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("application/json"):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw else {}
                return parsed if isinstance(parsed, dict) else {}

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": content_type,
                },
            )
            payload: dict[str, Any] = {}
            for key in form.keys():
                field = form[key]
                if isinstance(field, list):
                    field = field[0]
                if getattr(field, "filename", None):
                    payload[key] = {
                        "filename": field.filename,
                        "body": field.file.read(),
                    }
                else:
                    payload[key] = field.value
            return payload

        def _send_html(self, body: str, *, status: int = 200) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(self, body: dict[str, Any], *, status: int = 200) -> None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def _persist_upload(upload: dict[str, Any]) -> Path:
    filename = str(upload.get("filename") or "interview_audio")
    suffix = Path(filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(prefix="interview-pipeline-", suffix=suffix, delete=False) as handle:
        handle.write(upload.get("body", b""))
        return Path(handle.name)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Interview Relay</title>
  <style>
    :root {
      --ink: #161211;
      --paper: #f4ecdf;
      --card: rgba(255, 250, 242, 0.9);
      --signal: #d9472f;
      --signal-soft: rgba(217, 71, 47, 0.14);
      --shadow: 0 24px 80px rgba(13, 9, 8, 0.18);
      --line: rgba(22, 18, 17, 0.14);
      --muted: rgba(22, 18, 17, 0.62);
      --mono: "SF Mono", "IBM Plex Mono", "Menlo", monospace;
      --display: "Baskerville", "Iowan Old Style", "Palatino Linotype", serif;
      --body: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--body);
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 15%, rgba(217, 71, 47, 0.18), transparent 24%),
        radial-gradient(circle at 82% 18%, rgba(255, 212, 121, 0.14), transparent 20%),
        linear-gradient(135deg, #1e1816 0%, #241d1a 42%, #e6dacb 42%, #f4ecdf 100%);
      overflow-x: hidden;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.14;
      background-image:
        linear-gradient(rgba(0, 0, 0, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 0, 0, 0.06) 1px, transparent 1px);
      background-size: 22px 22px;
      mix-blend-mode: multiply;
    }

    .shell {
      width: min(1240px, calc(100vw - 32px));
      margin: 24px auto 48px;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 24px;
    }

    .hero,
    .panel {
      position: relative;
      border-radius: 28px;
      overflow: hidden;
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }

    .hero {
      min-height: 720px;
      padding: 34px;
      background:
        linear-gradient(155deg, rgba(28, 22, 20, 0.94), rgba(28, 22, 20, 0.82)),
        linear-gradient(180deg, rgba(255,255,255,0.04), transparent);
      color: #f8efe5;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 82% 12%, rgba(217, 71, 47, 0.26), transparent 18%),
        radial-gradient(circle at 20% 74%, rgba(255, 255, 255, 0.08), transparent 20%);
      pointer-events: none;
    }

    .panel {
      background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(247, 238, 227, 0.92));
      padding: 28px;
      min-height: 720px;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 9px 14px;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 999px;
      letter-spacing: 0.18em;
      font: 600 11px/1 var(--mono);
      text-transform: uppercase;
      color: rgba(248, 239, 229, 0.78);
      background: rgba(255,255,255,0.04);
    }

    .eyebrow::before {
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: #8cff9c;
      box-shadow: 0 0 18px rgba(140, 255, 156, 0.7);
    }

    h1 {
      margin: 22px 0 12px;
      font: 400 clamp(56px, 8vw, 92px)/0.92 var(--display);
      letter-spacing: -0.04em;
    }

    .lead {
      width: min(560px, 100%);
      color: rgba(248, 239, 229, 0.8);
      font-size: 17px;
      line-height: 1.75;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 28px 0 34px;
    }

    .metric {
      padding: 18px 18px 16px;
      border-radius: 20px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
    }

    .metric small,
    .panel small,
    .meta-label {
      display: block;
      font: 600 11px/1.2 var(--mono);
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: rgba(248, 239, 229, 0.56);
    }

    .metric strong {
      display: block;
      margin-top: 10px;
      font: 400 28px/1 var(--display);
      color: #fff2e6;
    }

    .grid-card {
      display: grid;
      gap: 18px;
      grid-template-columns: 1.2fr 0.8fr;
      align-items: stretch;
      margin-top: 26px;
    }

    .console,
    .sticker {
      border-radius: 24px;
      padding: 20px;
      position: relative;
      overflow: hidden;
    }

    .console {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.08);
    }

    .console pre {
      margin: 0;
      white-space: pre-wrap;
      font: 500 12px/1.8 var(--mono);
      color: rgba(248, 239, 229, 0.92);
    }

    .sticker {
      background: linear-gradient(180deg, #f5dfb8, #f0c585);
      color: #24170f;
      transform: rotate(-4deg);
      box-shadow: 0 18px 30px rgba(0,0,0,0.18);
    }

    .sticker h2 {
      margin: 10px 0 8px;
      font: 400 36px/1 var(--display);
    }

    .panel h2 {
      margin: 0 0 8px;
      font: 400 40px/0.98 var(--display);
      letter-spacing: -0.03em;
    }

    .panel .intro {
      margin: 0 0 22px;
      color: var(--muted);
      line-height: 1.7;
    }

    .dropzone {
      position: relative;
      padding: 22px;
      border-radius: 22px;
      border: 1.5px dashed rgba(22, 18, 17, 0.26);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.52)),
        linear-gradient(135deg, rgba(217, 71, 47, 0.08), transparent);
      transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
      cursor: pointer;
    }

    .dropzone:hover,
    .dropzone.is-dragover {
      transform: translateY(-2px);
      border-color: rgba(217, 71, 47, 0.52);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.88), rgba(255,255,255,0.66)),
        linear-gradient(135deg, rgba(217, 71, 47, 0.12), transparent);
    }

    .dropzone input {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }

    .dropzone strong {
      display: block;
      font: 500 24px/1.1 var(--display);
      margin-bottom: 8px;
    }

    .dropzone p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }

    .file-pill {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
      padding: 10px 14px;
      border-radius: 999px;
      background: var(--signal-soft);
      font: 600 12px/1 var(--mono);
      color: #8a2f20;
    }

    .stack {
      display: grid;
      gap: 16px;
      margin-top: 18px;
    }

    .field-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .field {
      display: grid;
      gap: 8px;
    }

    .field.full {
      grid-column: 1 / -1;
    }

    label {
      font: 700 11px/1 var(--mono);
      letter-spacing: 0.13em;
      text-transform: uppercase;
      color: var(--muted);
    }

    input[type="text"],
    input[type="date"],
    input[type="url"] {
      width: 100%;
      border: 1px solid rgba(22, 18, 17, 0.12);
      border-radius: 16px;
      padding: 14px 16px;
      font: 500 15px/1.3 var(--body);
      color: var(--ink);
      background: rgba(255,255,255,0.8);
      outline: none;
      transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
    }

    input:focus {
      border-color: rgba(217, 71, 47, 0.52);
      box-shadow: 0 0 0 4px rgba(217, 71, 47, 0.08);
      transform: translateY(-1px);
    }

    .toggles {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }

    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 18px;
      border: 1px solid rgba(22, 18, 17, 0.1);
      background: rgba(255,255,255,0.72);
      font: 600 12px/1 var(--mono);
      color: var(--ink);
    }

    .toggle input {
      accent-color: var(--signal);
    }

    .actions {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 10px;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 15px 24px;
      background: linear-gradient(135deg, #1d1816, #3a271f);
      color: #fff4ea;
      font: 700 12px/1 var(--mono);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      cursor: pointer;
      transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
      box-shadow: 0 18px 30px rgba(22, 18, 17, 0.22);
    }

    button:hover:not(:disabled) {
      transform: translateY(-2px);
    }

    button:disabled {
      opacity: 0.58;
      cursor: wait;
    }

    .ghost {
      background: transparent;
      color: var(--ink);
      border: 1px solid rgba(22, 18, 17, 0.12);
      box-shadow: none;
    }

    .status {
      margin-top: 24px;
      padding: 20px;
      border-radius: 22px;
      background: rgba(22, 18, 17, 0.05);
      border: 1px solid rgba(22, 18, 17, 0.08);
    }

    .status-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
    }

    .status strong {
      font: 500 24px/1 var(--display);
    }

    .status p {
      margin: 12px 0 0;
      color: var(--muted);
      line-height: 1.65;
    }

    .result-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-top: 18px;
    }

    .result-card {
      padding: 18px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(22, 18, 17, 0.08);
    }

    .result-card pre {
      margin: 10px 0 0;
      max-height: 240px;
      overflow: auto;
      white-space: pre-wrap;
      font: 500 12px/1.7 var(--mono);
      color: #4d4039;
    }

    a {
      color: #9b3220;
    }

    @media (max-width: 1080px) {
      .shell {
        grid-template-columns: 1fr;
      }
      .hero,
      .panel {
        min-height: auto;
      }
    }

    @media (max-width: 720px) {
      .field-grid,
      .result-grid,
      .metrics,
      .grid-card {
        grid-template-columns: 1fr;
      }
      h1 {
        font-size: 54px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">Interview Relay</span>
      <h1>把录音<br/>直接拽进来。</h1>
      <p class="lead">这是一个给个人复盘用的本地工作台。你不用再回到命令行逐个填参数，只要拖进音频，系统就会自动补齐轮次、日期、上传、转写、整理，再决定要不要写进 Notion。</p>
      <div class="metrics">
        <div class="metric">
          <small>Input Mode</small>
          <strong>Drag · Drop · Run</strong>
        </div>
        <div class="metric">
          <small>Output Stack</small>
          <strong>Summary + Transcript</strong>
        </div>
        <div class="metric">
          <small>Writing Target</small>
          <strong>Notion Review DB</strong>
        </div>
      </div>
      <div class="grid-card">
        <div class="console">
          <small>Default Flow</small>
          <pre>local audio → BOS → Doubao Miaoji → assessment → Notion</pre>
        </div>
        <aside class="sticker">
          <small>Designed for</small>
          <h2>One-person review loop</h2>
          <p>更少参数，更少心智负担，保留完整逐字稿和训练式复盘。</p>
        </aside>
      </div>
    </section>

    <section class="panel">
      <small>Local Web Console</small>
      <h2>Upload & Launch</h2>
      <p class="intro">默认优先使用上传文件。轮次和日期会尽量从文件名自动推断，例如 <code>字节一面_0325.m4a</code> 会自动识别成 <code>一面</code> 和 <code>2026-03-25</code>。</p>

      <form id="run-form" class="stack">
        <label class="dropzone" id="dropzone">
          <input id="audio-file" name="audio_file" type="file" accept=".m4a,.mp3,.wav,.aac,.flac,.ogg,.mp4,.mov" />
          <strong>拖进录音，或者点击选择文件</strong>
          <p>推荐直接丢本地面试录音。浏览器会先把文件发给本地服务，再由 BOS 与豆包妙记继续处理。</p>
          <div class="file-pill" id="file-pill" hidden>尚未选择文件</div>
        </label>

        <div class="field full">
          <label for="audio-url">或者填一个远程 URL</label>
          <input id="audio-url" name="audio_url" type="url" placeholder="https://example.com/interview.m4a" />
        </div>

        <div class="field-grid">
          <div class="field">
            <label for="role">岗位</label>
            <input id="role" name="role" type="text" placeholder="不填则默认 待补充" />
          </div>
          <div class="field">
            <label for="round">轮次</label>
            <input id="round" name="round" type="text" placeholder="例如 一面 / 二面 / 终面" />
          </div>
          <div class="field">
            <label for="date">日期</label>
            <input id="date" name="date" type="date" />
          </div>
          <div class="field">
            <label for="candidate">名字（可选）</label>
            <input id="candidate" name="candidate" type="text" placeholder="个人复盘可不填" />
          </div>
        </div>

        <div class="toggles">
          <label class="toggle"><input type="checkbox" id="write-to-notion" name="write_to_notion" checked />写入 Notion</label>
          <label class="toggle"><input type="checkbox" id="include-mock-review" name="include_mock_review" checked />附带模拟面试复盘</label>
        </div>

        <div class="actions">
          <button id="submit-btn" type="submit">Start Review Run</button>
          <button id="reset-btn" class="ghost" type="button">Reset</button>
          <span class="meta-label" id="timer">Idle</span>
        </div>
      </form>

      <section class="status" id="status-card">
        <div class="status-head">
          <strong id="status-title">等待新的录音</strong>
          <small id="status-tag">Idle</small>
        </div>
        <p id="status-body">提交后这里会显示本次运行的状态、耗时、Notion 页面链接，以及结构化摘要预览。</p>
        <div class="result-grid" id="result-grid" hidden>
          <article class="result-card">
            <small>Summary</small>
            <pre id="summary-output"></pre>
          </article>
          <article class="result-card">
            <small>Run Info</small>
            <pre id="meta-output"></pre>
          </article>
          <article class="result-card">
            <small>Structured Page Draft</small>
            <pre id="page-output"></pre>
          </article>
          <article class="result-card">
            <small>Mock Review Draft</small>
            <pre id="review-output"></pre>
          </article>
        </div>
      </section>
    </section>
  </main>

  <script>
    const form = document.getElementById("run-form");
    const fileInput = document.getElementById("audio-file");
    const filePill = document.getElementById("file-pill");
    const dropzone = document.getElementById("dropzone");
    const submitBtn = document.getElementById("submit-btn");
    const resetBtn = document.getElementById("reset-btn");
    const timer = document.getElementById("timer");
    const statusTitle = document.getElementById("status-title");
    const statusTag = document.getElementById("status-tag");
    const statusBody = document.getElementById("status-body");
    const resultGrid = document.getElementById("result-grid");
    const summaryOutput = document.getElementById("summary-output");
    const metaOutput = document.getElementById("meta-output");
    const pageOutput = document.getElementById("page-output");
    const reviewOutput = document.getElementById("review-output");

    let timerHandle = null;
    let startedAt = null;

    function setTimerState(text) {
      timer.textContent = text;
    }

    function startTimer() {
      startedAt = Date.now();
      timerHandle = window.setInterval(() => {
        const seconds = ((Date.now() - startedAt) / 1000).toFixed(1);
        setTimerState(`${seconds}s`);
      }, 100);
    }

    function stopTimer() {
      if (timerHandle) {
        window.clearInterval(timerHandle);
        timerHandle = null;
      }
    }

    function setBusy(isBusy) {
      submitBtn.disabled = isBusy;
      fileInput.disabled = isBusy;
      document.getElementById("audio-url").disabled = isBusy;
      document.getElementById("role").disabled = isBusy;
      document.getElementById("round").disabled = isBusy;
      document.getElementById("date").disabled = isBusy;
      document.getElementById("candidate").disabled = isBusy;
      document.getElementById("write-to-notion").disabled = isBusy;
      document.getElementById("include-mock-review").disabled = isBusy;
      submitBtn.textContent = isBusy ? "Running..." : "Start Review Run";
    }

    function updateFilePill() {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        filePill.hidden = true;
        return;
      }
      filePill.hidden = false;
      filePill.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
    }

    fileInput.addEventListener("change", updateFilePill);

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      const files = event.dataTransfer.files;
      if (files && files.length) {
        fileInput.files = files;
        updateFilePill();
      }
    });

    resetBtn.addEventListener("click", () => {
      form.reset();
      updateFilePill();
      resultGrid.hidden = true;
      statusTitle.textContent = "等待新的录音";
      statusTag.textContent = "Idle";
      statusBody.textContent = "提交后这里会显示本次运行的状态、耗时、Notion 页面链接，以及结构化摘要预览。";
      stopTimer();
      setTimerState("Idle");
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const hasFile = fileInput.files && fileInput.files.length > 0;
      const audioUrl = document.getElementById("audio-url").value.trim();
      if (!hasFile && !audioUrl) {
        statusTitle.textContent = "缺少输入";
        statusTag.textContent = "Error";
        statusBody.textContent = "请至少上传一个本地音频文件，或者填写一个远程录音 URL。";
        return;
      }

      const formData = new FormData();
      if (hasFile) {
        formData.append("upload", fileInput.files[0]);
      }
      if (audioUrl) formData.append("audio_url", audioUrl);
      formData.append("role", document.getElementById("role").value.trim());
      formData.append("round", document.getElementById("round").value.trim());
      formData.append("date", document.getElementById("date").value.trim());
      formData.append("candidate", document.getElementById("candidate").value.trim());
      if (document.getElementById("write-to-notion").checked) formData.append("write_to_notion", "true");
      if (document.getElementById("include-mock-review").checked) formData.append("include_mock_review", "true");

      setBusy(true);
      statusTitle.textContent = "正在处理录音";
      statusTag.textContent = "Running";
      statusBody.textContent = "已进入本地处理流水线：上传、转写、结构化整理、Notion 写入会依次完成。较长录音通常需要 2 到 4 分钟。";
      resultGrid.hidden = true;
      startTimer();
      setTimerState("0.0s");

      try {
        const response = await fetch("/api/run", {
          method: "POST",
          body: formData,
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "请求失败");
        }

        stopTimer();
        setBusy(false);
        setTimerState(`${payload.elapsed_seconds}s total`);
        statusTitle.textContent = payload.interview.title;
        statusTag.textContent = payload.notion ? "Written to Notion" : "Preview Ready";

        const notionLine = payload.notion
          ? `Notion: ${payload.notion.page_url}`
          : "Notion: skipped";
        statusBody.innerHTML = `本次处理已完成。<br/>${notionLine}`;

        summaryOutput.textContent = payload.result.summary || "暂无摘要";
        metaOutput.textContent = [
          `Status: ${payload.result.status}`,
          `Task ID: ${payload.result.task_id}`,
          `Date: ${payload.interview.date}`,
          `Round: ${payload.interview.round}`,
          `Role: ${payload.interview.role}`,
          `Elapsed: ${payload.elapsed_seconds}s`,
        ].join("\\n");
        pageOutput.textContent = payload.page_markdown;
        reviewOutput.textContent = payload.review_markdown;
        resultGrid.hidden = false;
      } catch (error) {
        stopTimer();
        setBusy(false);
        setTimerState("Failed");
        statusTitle.textContent = "处理失败";
        statusTag.textContent = "Error";
        statusBody.textContent = error.message || String(error);
      }
    });
  </script>
</body>
</html>
"""
