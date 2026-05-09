import { randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

const sourceDir = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.resolve(process.cwd(), "..", "7.得到锦囊");
const limit = Number.parseInt(process.argv[3] || "0", 10);
const knowledgeBasePath = path.resolve(process.cwd(), "data", "wisdom-advisor", "knowledge-base.json");
const envPath = path.resolve(process.cwd(), "..", "interview-audio-pipeline", ".env");
const reportDir = path.resolve(process.cwd(), "data", "wisdom-advisor", "import-reports");
const failureReportPath = path.join(reportDir, "jinnang-pdf-failures.json");

const SUBMIT_TASK_URL = "https://aip.baidubce.com/rest/2.0/brain/online/v2/parser/task";
const QUERY_TASK_URL = "https://aip.baidubce.com/rest/2.0/brain/online/v2/parser/task/query";
const DEFAULT_MAX_ATTEMPTS = 45;
const DEFAULT_INITIAL_QUERY_DELAY_MS = 8000;
const DEFAULT_INTERVAL_MS = 8000;
const DEFAULT_SUBMIT_RETRIES = 6;
const DEFAULT_QUERY_RETRIES = 6;
const DEFAULT_INTER_FILE_DELAY_MS = 4000;
const DEFAULT_RATE_LIMIT_BACKOFF_MS = 12_000;
const DEFAULT_QUOTA_BACKOFF_MS = 60_000;
const MAX_CONSECUTIVE_QUOTA_ERRORS = 5;

async function main() {
  const env = await loadEnvFile(envPath);
  const apiKey = env.BAIDU_API_KEY || env.QIANFAN_BEARER_TOKEN || "";
  if (!apiKey) {
    throw new Error("Missing BAIDU_API_KEY or QIANFAN_BEARER_TOKEN in interview-audio-pipeline/.env");
  }

  if (toBoolean(env.QIANFAN_DISABLE_PROXY, true)) {
    clearProxyEnv();
  }

  const settings = {
    maxAttempts: getPositiveInt(env.JINNANG_PDF_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
    initialQueryDelayMs: getPositiveInt(env.JINNANG_PDF_INITIAL_QUERY_DELAY_MS, DEFAULT_INITIAL_QUERY_DELAY_MS),
    pollIntervalMs: getPositiveInt(env.JINNANG_PDF_POLL_INTERVAL_MS, DEFAULT_INTERVAL_MS),
    submitRetries: getPositiveInt(env.JINNANG_PDF_SUBMIT_RETRIES, DEFAULT_SUBMIT_RETRIES),
    queryRetries: getPositiveInt(env.JINNANG_PDF_QUERY_RETRIES, DEFAULT_QUERY_RETRIES),
    interFileDelayMs: getPositiveInt(env.JINNANG_PDF_INTER_FILE_DELAY_MS, DEFAULT_INTER_FILE_DELAY_MS),
    rateLimitBackoffMs: getPositiveInt(env.JINNANG_PDF_RATE_LIMIT_BACKOFF_MS, DEFAULT_RATE_LIMIT_BACKOFF_MS),
    quotaBackoffMs: getPositiveInt(env.JINNANG_PDF_QUOTA_BACKOFF_MS, DEFAULT_QUOTA_BACKOFF_MS),
  };

  const knowledgeBase = await loadKnowledgeBase();
  const existingTitles = new Set(knowledgeBase.sources.map((source) => source.title.trim()));
  const existingContentKeys = new Set(knowledgeBase.sources.map((source) => normalizeContentKey(source.passages || [])));

  const entries = await readdir(sourceDir, { withFileTypes: true });
  const pdfFiles = entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".pdf"))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right, "zh-CN"));

  const groupedByCanonicalTitle = new Map();
  for (const fileName of pdfFiles) {
    const canonicalTitle = cleanupTitle(fileName);
    const group = groupedByCanonicalTitle.get(canonicalTitle) || [];
    group.push(fileName);
    groupedByCanonicalTitle.set(canonicalTitle, group);
  }

  let imported = 0;
  let skippedDuplicateFile = 0;
  let skippedExistingKnowledge = 0;
  let skippedDuplicateContent = 0;
  let failed = 0;
  let abortedDueToQuota = false;
  let consecutiveQuotaErrors = 0;
  const failureRecords = [];

  const canonicalTitles = [...groupedByCanonicalTitle.keys()].sort((left, right) => left.localeCompare(right, "zh-CN"));

  for (const canonicalTitle of canonicalTitles) {
    if (abortedDueToQuota) {
      break;
    }
    if (limit > 0 && imported >= limit) {
      break;
    }

    const fileGroup = groupedByCanonicalTitle.get(canonicalTitle) || [];
    skippedDuplicateFile += Math.max(0, fileGroup.length - 1);

    if (existingTitles.has(canonicalTitle)) {
      skippedExistingKnowledge += 1;
      continue;
    }

    const fileName = pickPreferredFile(fileGroup, "pdf");
    const absolutePath = path.join(sourceDir, fileName);

    try {
      await sleep(settings.interFileDelayMs);
      const markdown = await parsePdfDocument(apiKey, absolutePath, fileName, settings);
      const cleanedContent = cleanupContent(markdown);
      if (!cleanedContent) {
        failed += 1;
        failureRecords.push(buildFailureRecord(canonicalTitle, fileName, "empty_content", "Parsed content is empty after cleanup."));
        console.warn(`Skipped empty content: ${fileName}`);
        continue;
      }

      const passages = splitIntoPassages(cleanedContent);
      const contentKey = normalizeContentKey(passages);
      if (existingContentKeys.has(contentKey)) {
        skippedDuplicateContent += 1;
        continue;
      }

      const source = {
        id: randomUUID(),
        title: canonicalTitle,
        sourceType: "文档摘录",
        summary: buildSummary(canonicalTitle, cleanedContent),
        tags: inferTags(canonicalTitle, cleanedContent),
        createdAt: new Date().toISOString(),
        passages,
      };

      knowledgeBase.sources.unshift(source);
      existingTitles.add(canonicalTitle);
      existingContentKeys.add(contentKey);
      imported += 1;
      consecutiveQuotaErrors = 0;
      console.log(`Imported PDF: ${canonicalTitle}`);
    } catch (error) {
      failed += 1;
      const parsedError = normalizeBaiduError(error);
      failureRecords.push(buildFailureRecord(canonicalTitle, fileName, parsedError.type, parsedError.message));
      if (parsedError.type === "quota_limit") {
        consecutiveQuotaErrors += 1;
        if (consecutiveQuotaErrors >= MAX_CONSECUTIVE_QUOTA_ERRORS) {
          abortedDueToQuota = true;
          console.warn(`Stopping early after ${consecutiveQuotaErrors} consecutive quota-limit failures.`);
        }
      } else {
        consecutiveQuotaErrors = 0;
      }
      console.warn(`Failed PDF: ${fileName}`);
      console.warn(parsedError.message);
    }
  }

  await writeFile(knowledgeBasePath, JSON.stringify(knowledgeBase, null, 2) + "\n", "utf-8");
  await writeFailureReport({
    sourceDir,
    totalPdfFiles: pdfFiles.length,
    uniqueCanonicalTitles: canonicalTitles.length,
    imported,
    skippedDuplicateFile,
    skippedExistingKnowledge,
    skippedDuplicateContent,
    failed,
    abortedDueToQuota,
    failureReportPath,
    remainingCanonicalTitles: canonicalTitles.filter((title) => !existingTitles.has(title)),
    failures: failureRecords,
  });

  console.log("");
  console.log(
    JSON.stringify(
      {
        sourceDir,
        totalPdfFiles: pdfFiles.length,
        uniqueCanonicalTitles: canonicalTitles.length,
        imported,
        skippedDuplicateFile,
        skippedExistingKnowledge,
        skippedDuplicateContent,
        failed,
        abortedDueToQuota,
        failureReportPath,
      },
      null,
      2
    )
  );
}

async function parsePdfDocument(apiKey, filePath, fileName, settings) {
  const fileData = (await readFile(filePath)).toString("base64");
  const taskId = await submitTask(apiKey, fileData, fileName, settings);

  // The Baidu docs recommend waiting 5-10s after submission before polling.
  await sleep(settings.initialQueryDelayMs);
  const markdownUrl = await pollTask(apiKey, taskId, settings);
  const markdownResponse = await fetch(markdownUrl);
  if (!markdownResponse.ok) {
    throw new Error(`Download failed with HTTP ${markdownResponse.status}`);
  }
  return await markdownResponse.text();
}

async function submitTask(apiKey, fileData, fileName, settings) {
  for (let attempt = 1; attempt <= settings.submitRetries; attempt += 1) {
    try {
      const submitBody = new URLSearchParams({
        file_name: fileName,
        file_data: fileData,
        language_type: "CHN_ENG",
        recognize_formula: "false",
        analysis_chart: "false",
        angle_adjust: "true",
        parse_image_layout: "false",
        html_table_format: "true",
      });

      const submitResponse = await fetch(SUBMIT_TASK_URL, {
        method: "POST",
        headers: getHeaders(apiKey),
        body: submitBody,
      });
      if (!submitResponse.ok) {
        throw new Error(`Submit failed with HTTP ${submitResponse.status}`);
      }
      const submitResult = await submitResponse.json();
      if (submitResult.error_code && submitResult.error_code !== 0) {
        throw new Error(`Submit failed: ${submitResult.error_msg || "Unknown error"}`);
      }

      const taskId = submitResult.result?.task_id;
      if (!taskId) {
        throw new Error("No task_id returned from Baidu parser.");
      }

      return taskId;
    } catch (error) {
      await maybeRetry(error, attempt, settings.submitRetries, "submit", settings);
    }
  }

  throw new Error(`Submit failed after ${settings.submitRetries} attempts.`);
}

async function pollTask(apiKey, taskId, settings) {
  for (let attempt = 1; attempt <= settings.maxAttempts; attempt += 1) {
    const result = await queryTask(apiKey, taskId, settings);

    const taskResult = result.result || {};
    if (taskResult.status === "success" && taskResult.markdown_url) {
      return taskResult.markdown_url;
    }
    if (taskResult.status === "failed") {
      throw new Error(`Task failed: ${taskResult.task_error || "Unknown error"}`);
    }

    console.error(`[${attempt}/${settings.maxAttempts}] PDF task status: ${taskResult.status || "unknown"}...`);
    await sleep(settings.pollIntervalMs);
  }

  throw new Error(`Task timeout after ${settings.maxAttempts * (settings.pollIntervalMs / 1000)} seconds.`);
}

async function queryTask(apiKey, taskId, settings) {
  for (let attempt = 1; attempt <= settings.queryRetries; attempt += 1) {
    try {
      const body = new URLSearchParams({ task_id: taskId });
      const response = await fetch(QUERY_TASK_URL, {
        method: "POST",
        headers: getHeaders(apiKey),
        body,
      });
      if (!response.ok) {
        throw new Error(`Query failed with HTTP ${response.status}`);
      }
      const result = await response.json();
      if (result.error_code && result.error_code !== 0) {
        throw new Error(`Query failed: ${result.error_msg || "Unknown error"}`);
      }

      return result;
    } catch (error) {
      await maybeRetry(error, attempt, settings.queryRetries, "query", settings);
    }
  }

  throw new Error(`Query failed after ${settings.queryRetries} attempts.`);
}

async function loadKnowledgeBase() {
  const raw = await readFile(knowledgeBasePath, "utf-8");
  const parsed = JSON.parse(raw);
  return {
    sources: Array.isArray(parsed.sources) ? parsed.sources : [],
  };
}

async function writeFailureReport(report) {
  await mkdir(reportDir, { recursive: true });
  await writeFile(failureReportPath, JSON.stringify(report, null, 2) + "\n", "utf-8");
}

async function loadEnvFile(filePath) {
  const result = {};
  const raw = await readFile(filePath, "utf-8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const [key, ...rest] = trimmed.split("=");
    result[key.trim()] = normalizeEnvValue(rest.join("="));
  }
  return result;
}

function normalizeEnvValue(value) {
  const trimmed = value.trim();
  if (trimmed.length >= 2 && trimmed[0] === trimmed.at(-1) && [`"`, `'`].includes(trimmed[0])) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function getHeaders(apiKey) {
  return {
    Authorization: `Bearer ${apiKey}`,
    "X-Appbuilder-From": "codex",
    "Content-Type": "application/x-www-form-urlencoded",
  };
}

function cleanupTitle(fileName) {
  return fileName
    .replace(/\.pdf$/i, "")
    .replace(/\(\d+\)$/u, "")
    .replace(/_?\d{14}(?:\(\d+\))?$/u, "")
    .trim();
}

function pickPreferredFile(fileNames, extension) {
  const suffix = extension === "pdf" ? /\.pdf$/i : /\.doc$/i;
  return [...fileNames].sort((left, right) => scoreFileName(left, suffix) - scoreFileName(right, suffix) || left.localeCompare(right, "zh-CN"))[0];
}

function scoreFileName(fileName, suffixPattern) {
  let score = 0;
  if (new RegExp(String.raw`\(\d+\)${suffixPattern.source.replace("\\", "")}`, "i").test(fileName)) {
    score += 10;
  }
  if (/_\d{14}/.test(fileName)) {
    score += 2;
  }
  return score;
}

async function maybeRetry(error, attempt, maxAttempts, phase, settings) {
  const parsedError = normalizeBaiduError(error);
  const allowedAttempts = parsedError.type === "quota_limit" ? Math.min(maxAttempts, 3) : maxAttempts;
  if (!parsedError.retryable || attempt >= allowedAttempts) {
    throw new Error(parsedError.message);
  }

  const delayMs = getRetryDelayMs(parsedError.type, attempt, settings);
  console.warn(`[retry ${attempt}/${allowedAttempts}] ${phase} ${parsedError.type}, waiting ${Math.round(delayMs / 1000)}s`);
  await sleep(delayMs);
}

function normalizeBaiduError(error) {
  const message = error instanceof Error ? error.message : String(error);
  const normalized = message.toLowerCase();

  if (normalized.includes("quota exceed")) {
    return { type: "quota_limit", message, retryable: true };
  }
  if (normalized.includes("qps request limit reached") || normalized.includes("too many requests") || normalized.includes("http 429")) {
    return { type: "rate_limit", message, retryable: true };
  }
  if (
    normalized.includes("fetch failed") ||
    normalized.includes("timeout") ||
    normalized.includes("networkerror") ||
    normalized.includes("econnreset") ||
    normalized.includes("socket hang up") ||
    normalized.includes("http 500") ||
    normalized.includes("http 502") ||
    normalized.includes("http 503") ||
    normalized.includes("http 504")
  ) {
    return { type: "transient", message, retryable: true };
  }

  return { type: "fatal", message, retryable: false };
}

function getRetryDelayMs(type, attempt, settings) {
  if (type === "quota_limit") {
    return settings.quotaBackoffMs * attempt;
  }
  if (type === "rate_limit") {
    return settings.rateLimitBackoffMs * attempt;
  }
  return Math.max(settings.pollIntervalMs, 4000 * attempt);
}

function buildFailureRecord(canonicalTitle, fileName, type, message) {
  return {
    canonicalTitle,
    fileName,
    type,
    message,
    recordedAt: new Date().toISOString(),
  };
}

function cleanupContent(raw) {
  const blocks = raw
    .replace(/\r/g, "")
    .split(/\n{2,}/)
    .map((block) =>
      block
        .split("\n")
        .map((line) => stripMarkdownPrefix(line.trim()))
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim()
    )
    .map((block) =>
      block
        .replace(/\d+人已看/gu, "")
        .replace(/更多低价课程请加微信[^\s]*/giu, "")
        .replace(/\s+/g, " ")
        .trim()
    )
    .filter(Boolean);

  const cleanedBlocks = [];
  for (const block of blocks) {
    if (cleanedBlocks.at(-1) === block) {
      continue;
    }
    if (/^\d+人已看$/u.test(block)) {
      continue;
    }
    if (/^.+的锦囊$/u.test(block)) {
      continue;
    }
    if (/^\d{4}-\d{2}-\d{2}$/u.test(block)) {
      continue;
    }
    if (/^更多低价课程请加微信/i.test(block)) {
      continue;
    }
    if (
      /^(海银资本创始合伙人|得到课程|主理人|清华大学|爱丁堡大学|心理咨询师|职翼科技CEO|资深猎头|第二军医大学|博士|教授|副教授|创始人|合伙人|CEO|主讲人)/u.test(
        block
      )
    ) {
      continue;
    }
    if (isLikelyByline(block)) {
      continue;
    }
    cleanedBlocks.push(block);
  }

  return collapseQuestionRepeats(cleanedBlocks.join("\n\n").trim());
}

function stripMarkdownPrefix(line) {
  return line.replace(/^#+\s*/, "").trim();
}

function isLikelyByline(block) {
  if (block.length > 40) {
    return false;
  }
  return /(创始人|合伙人|CEO|作者|博士|教授|副教授|主理人|讲师|研究员|媒体人|记者|医生|律师|顾问|总监)$/u.test(block);
}

function collapseQuestionRepeats(content) {
  const paragraphs = content.split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
  const deduped = [];
  for (const paragraph of paragraphs) {
    if (deduped.at(-1) === paragraph) {
      continue;
    }
    deduped.push(paragraph);
  }
  return deduped.join("\n\n");
}

function buildSummary(title, content) {
  const paragraphs = content.split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
  const firstUseful = paragraphs.find((item) => item !== title) || title;
  return firstUseful.slice(0, 90) || "得到锦囊 PDF 导入";
}

function inferTags(title, content) {
  const text = `${title}\n${content}`;
  const tags = new Set(["得到锦囊"]);
  const rules = [
    ["沟通", ["聊天", "沟通", "表达", "说", "谈话", "关系"]],
    ["职场", ["领导", "同事", "职场", "老板", "客户", "升职"]],
    ["关系", ["朋友", "伴侣", "家人", "相处", "信任"]],
    ["决策", ["怎么办", "选择", "判断", "纠结"]],
    ["边界", ["拒绝", "压力", "教育人", "冒犯", "边界"]],
  ];

  for (const [tag, keywords] of rules) {
    if (keywords.some((keyword) => text.includes(keyword))) {
      tags.add(tag);
    }
  }

  return [...tags];
}

function splitIntoPassages(content) {
  return content
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .flatMap((paragraph) => {
      if (paragraph.length <= 120) {
        return [paragraph];
      }

      const segments = paragraph
        .split(/(?<=[。！？!?])/)
        .map((part) => part.trim())
        .filter(Boolean);

      const passages = [];
      let bucket = "";
      for (const segment of segments) {
        const next = bucket ? `${bucket}${segment}` : segment;
        if (next.length > 120 && bucket) {
          passages.push(bucket);
          bucket = segment;
        } else {
          bucket = next;
        }
      }
      if (bucket) {
        passages.push(bucket);
      }
      return passages;
    });
}

function normalizeContentKey(passages) {
  return passages
    .map((item) => item.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join("\n")
    .slice(0, 5000);
}

function clearProxyEnv() {
  for (const key of ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]) {
    delete process.env[key];
  }
}

function toBoolean(value, fallback) {
  if (value == null || value === "") {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function getPositiveInt(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

await main();
