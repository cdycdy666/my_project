import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const sourceDir = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.resolve(process.cwd(), "..", "7.得到锦囊");
const limit = Number.parseInt(process.argv[3] || "0", 10);
const knowledgeBasePath = path.resolve(process.cwd(), "data", "wisdom-advisor", "knowledge-base.json");

async function main() {
  const knowledgeBase = await loadKnowledgeBase();
  const existingTitles = new Set(knowledgeBase.sources.map((source) => source.title.trim()));
  const existingContentKeys = new Set(knowledgeBase.sources.map((source) => normalizeContentKey(source.passages || [])));

  const entries = await readdir(sourceDir, { withFileTypes: true });
  const docFiles = entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".doc"))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right, "zh-CN"));

  const groupedByCanonicalTitle = new Map();
  for (const fileName of docFiles) {
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

  const canonicalTitles = [...groupedByCanonicalTitle.keys()].sort((left, right) => left.localeCompare(right, "zh-CN"));

  for (const canonicalTitle of canonicalTitles) {
    if (limit > 0 && imported >= limit) {
      break;
    }

    const fileGroup = groupedByCanonicalTitle.get(canonicalTitle) || [];
    skippedDuplicateFile += Math.max(0, fileGroup.length - 1);

    if (existingTitles.has(canonicalTitle)) {
      skippedExistingKnowledge += 1;
      continue;
    }

    const fileName = pickPreferredFile(fileGroup);
    const absolutePath = path.join(sourceDir, fileName);
    try {
      const content = await extractDocText(absolutePath);
      const cleanedContent = cleanupContent(content);
      if (!cleanedContent) {
        failed += 1;
        console.warn(`Skipped empty content: ${fileName}`);
        continue;
      }

       const contentKey = normalizeContentKey(splitIntoPassages(cleanedContent));
       if (existingContentKeys.has(contentKey)) {
        skippedDuplicateContent += 1;
        continue;
      }

      const source = {
        id: randomUUID(),
        title: canonicalTitle,
        sourceType: "文档摘录",
        summary: buildSummary(cleanedContent),
        tags: inferTags(canonicalTitle, cleanedContent),
        createdAt: new Date().toISOString(),
        passages: splitIntoPassages(cleanedContent),
      };
      knowledgeBase.sources.unshift(source);
      existingTitles.add(canonicalTitle);
      existingContentKeys.add(contentKey);
      imported += 1;
      console.log(`Imported: ${canonicalTitle}`);
    } catch (error) {
      failed += 1;
      console.warn(`Failed: ${fileName}`);
      console.warn(error instanceof Error ? error.message : String(error));
    }
  }

  await writeFile(knowledgeBasePath, JSON.stringify(knowledgeBase, null, 2) + "\n", "utf-8");

  console.log("");
  console.log(
    JSON.stringify(
      {
        sourceDir,
        totalDocFiles: docFiles.length,
        uniqueCanonicalTitles: canonicalTitles.length,
        imported,
        skippedDuplicateFile,
        skippedExistingKnowledge,
        skippedDuplicateContent,
        failed,
      },
      null,
      2
    )
  );
}

async function loadKnowledgeBase() {
  const raw = await readFile(knowledgeBasePath, "utf-8");
  const parsed = JSON.parse(raw);
  return {
    sources: Array.isArray(parsed.sources) ? parsed.sources : [],
  };
}

async function extractDocText(filePath) {
  const { stdout } = await execFileAsync("textutil", ["-convert", "txt", "-stdout", filePath], {
    maxBuffer: 8 * 1024 * 1024,
  });
  return stdout;
}

function cleanupTitle(fileName) {
  return fileName
    .replace(/\.doc$/i, "")
    .replace(/\(\d+\)$/u, "")
    .replace(/_?\d{14}(?:\(\d+\))?$/u, "")
    .trim();
}

function normalizeDuplicateKey(title) {
  return title.replace(/\s+/g, "").trim();
}

function pickPreferredFile(fileNames) {
  return [...fileNames].sort((left, right) => scoreFileName(left) - scoreFileName(right) || left.localeCompare(right, "zh-CN"))[0];
}

function scoreFileName(fileName) {
  let score = 0;
  if (/\(\d+\)\.doc$/i.test(fileName)) {
    score += 10;
  }
  if (/_\d{14}/.test(fileName)) {
    score += 2;
  }
  return score;
}

function cleanupContent(raw) {
  return raw
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line, index, list) => {
      if (!line) {
        return false;
      }
      if (index > 0 && line === list[index - 1]) {
        return false;
      }
      if (/^\d+人已看$/u.test(line)) {
        return false;
      }
      if (/^.+ 的锦囊$/u.test(line)) {
        return false;
      }
      if (/^\d{4}-\d{2}-\d{2}$/u.test(line)) {
        return false;
      }
      if (/^(哲学博士|武汉大学|副教授|作者|主讲人|讲师)/u.test(line)) {
        return false;
      }
      return true;
    })
    .join("\n\n")
    .trim();
}

function buildSummary(content) {
  const firstParagraph = content.split(/\n{2,}/)[0]?.trim() || "";
  return firstParagraph.slice(0, 90) || "得到锦囊文档导入";
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

await main();
