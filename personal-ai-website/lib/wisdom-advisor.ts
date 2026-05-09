import { randomUUID } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export type KnowledgeSourceType = "录音转写" | "文档摘录" | "手动笔记";

export type KnowledgeSource = {
  id: string;
  title: string;
  sourceType: KnowledgeSourceType;
  summary: string;
  tags: string[];
  createdAt: string;
  passages: string[];
};

type KnowledgeBase = {
  sources: KnowledgeSource[];
};

export type AdviceEvidence = {
  sourceId: string;
  sourceTitle: string;
  sourceType: KnowledgeSourceType;
  excerpt: string;
  score: number;
  tags: string[];
};

export type AdviceResult = {
  situation: string;
  summary: string;
  principles: string[];
  actions: string[];
  pitfalls: string[];
  evidence: AdviceEvidence[];
  relatedSources: Array<{
    id: string;
    title: string;
    sourceType: KnowledgeSourceType;
    summary: string;
    tags: string[];
  }>;
};

type Playbook = {
  label: string;
  keywords: string[];
  summaryLead: string;
  principles: string[];
  actions: string[];
  pitfalls: string[];
};

type RankedEvidence = {
  source: KnowledgeSource;
  excerpt: string;
  score: number;
};

type ModelAdvicePayload = {
  situation?: unknown;
  summary?: unknown;
  principles?: unknown;
  actions?: unknown;
  pitfalls?: unknown;
};

const KNOWLEDGE_BASE_PATH = path.join(process.cwd(), "data", "wisdom-advisor", "knowledge-base.json");
const DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
const DEFAULT_QWEN_MODEL = "qwen-plus";

const PLAYBOOKS: Playbook[] = [
  {
    label: "机会争取",
    keywords: ["谈薪", "薪资", "薪酬", "涨薪", "offer", "跳槽", "晋升", "总包", "包裹", "争取"],
    summaryLead: "这类场景的关键，不是逞强抬价，而是把你的价值和对方能接受的成交条件说清楚。",
    principles: ["先想清楚目标区间、底线和退让空间", "谈薪讲的是价值依据，不是情绪和胆量", "现金谈不动时，也要一起看级别、奖金和成长空间"],
    actions: ["先准备市场行情、过往成绩和岗位匹配度这三类证据", "开口时先表达对机会的认可，再给出你的预期区间", "如果对方压价，先问清是预算限制、职级限制，还是评估顾虑"],
    pitfalls: ["不要一上来就报出自己的最低接受价", "不要只说我觉得自己值更多，却拿不出依据", "不要把谈薪谈成情绪对抗，重点是找成交条件"],
  },
  {
    label: "冲突缓和",
    keywords: ["吵", "矛盾", "冲突", "误会", "情绪", "生气", "怼", "争执", "冷战"],
    summaryLead: "这类场景最重要的不是立刻分输赢，而是先把关系和沟通通道保住。",
    principles: ["先降温，再讨论事实", "把评价换成观察，把指责换成请求", "先回到共同目标，再谈谁该怎么改"],
    actions: ["先停一下，别在最上头的时候发关键消息", "用两三句事实复盘发生了什么，再说影响", "把你的下一步请求说具体，比如时间、动作和结果"],
    pitfalls: ["不要一开始就给对方下定义", "不要把旧账全部翻出来", "不要只发泄情绪却不提出可执行下一步"],
  },
  {
    label: "边界表达",
    keywords: ["拒绝", "边界", "麻烦", "求我", "不想", "推掉", "不好意思", "答应", "占用"],
    summaryLead: "重点不是把话说得多圆，而是清楚、体面、尽早地表达边界。",
    principles: ["边界清楚比表面和气更重要", "拒绝的是这件事，不是否定这个人", "越早说明，越容易保护关系"],
    actions: ["先表达理解或感谢，再给出明确结论", "说明你的真实限制，不展开过多辩解", "如果合适，给一个可行替代方案或下次窗口"],
    pitfalls: ["不要用拖延代替拒绝", "不要给自己做不到的模糊承诺", "不要因为怕尴尬就把成本都留给自己"],
  },
  {
    label: "协作推进",
    keywords: ["同事", "合作", "推进", "项目", "交付", "老板", "领导", "需求", "协作", "卡住", "预期"],
    summaryLead: "做事卡住时，往往先要补的是预期管理，而不是单纯更努力。",
    principles: ["先对齐目标、边界、节奏和拍板人", "关键节点主动同步，不要闷头等结果", "问题越早暴露，代价越低"],
    actions: ["把目标、截止时间、责任人和完成标准重新说清楚", "把当前阻塞点和需要的支持列成清单", "同步时给出选项，不只抛问题"],
    pitfalls: ["不要默认别人和你理解一致", "不要等到临门一脚才暴露风险", "不要只埋头做事却不管理认知"],
  },
  {
    label: "关系经营",
    keywords: ["朋友", "伴侣", "家人", "关系", "信任", "在意", "误解", "亲密", "相处"],
    summaryLead: "关系问题很多不是靠一次说服解决，而是靠持续建立信任账户。",
    principles: ["先保连接，再谈分歧", "平时多存信任，冲突时才有缓冲", "让对方感受到被尊重，比一时赢过对方更重要"],
    actions: ["先确认对方在意什么，再表达你的真实感受", "补上平时缺少的回应、感谢和交代", "谈分歧时把目标放在修复理解，而不是证明谁更有道理"],
    pitfalls: ["不要只在出问题时才沟通", "不要把沉默当成成熟", "不要为了赢一句话输掉后续合作空间"],
  },
  {
    label: "自我判断",
    keywords: ["纠结", "选择", "决定", "要不要", "担心", "犹豫", "判断", "怎么选"],
    summaryLead: "遇到难决策时，先把事实、情绪和真正代价拆开，答案会更清楚。",
    principles: ["分清你怕的是什么，想要的是什么", "短期舒服和长期价值不要混在一起", "把问题从抽象判断落到具体代价"],
    actions: ["先列清楚你已知的事实和未知风险", "问自己一年后回看，哪种选择更值得承担", "为决定设置复盘点，而不是一次性赌到底"],
    pitfalls: ["不要只被当下情绪推着走", "不要把不决定当成没有成本", "不要因为怕错就一直停在原地"],
  },
];

export async function loadKnowledgeBase(): Promise<KnowledgeBase> {
  const raw = await readFile(KNOWLEDGE_BASE_PATH, "utf-8");
  const parsed = JSON.parse(raw) as KnowledgeBase;
  return {
    sources: Array.isArray(parsed.sources) ? parsed.sources : [],
  };
}

export async function listKnowledgeSummary() {
  const knowledgeBase = await loadKnowledgeBase();
  const tags = [...new Set(knowledgeBase.sources.flatMap((source) => source.tags))].sort((a, b) =>
    a.localeCompare(b, "zh-CN")
  );

  return {
    totalSources: knowledgeBase.sources.length,
    totalPassages: knowledgeBase.sources.reduce((sum, source) => sum + source.passages.length, 0),
    tags,
    sources: knowledgeBase.sources
      .slice()
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
      .map((source) => ({
        id: source.id,
        title: source.title,
        sourceType: source.sourceType,
        summary: source.summary,
        tags: source.tags,
        createdAt: source.createdAt,
        passageCount: source.passages.length,
      })),
  };
}

export async function getKnowledgeSourceDetail(sourceId: string) {
  const normalized = sourceId.trim();
  if (!normalized) {
    throw new Error("资料 ID 不能为空。");
  }

  const knowledgeBase = await loadKnowledgeBase();
  const source = knowledgeBase.sources.find((item) => item.id === normalized);
  if (!source) {
    throw new Error("没有找到对应资料。");
  }

  return {
    id: source.id,
    title: source.title,
    sourceType: source.sourceType,
    summary: source.summary,
    tags: source.tags,
    createdAt: source.createdAt,
    passages: source.passages,
  };
}

export async function appendKnowledgeSource(input: {
  title: string;
  sourceType: KnowledgeSourceType;
  summary: string;
  tags: string[];
  content: string;
}) {
  const title = input.title.trim();
  const summary = input.summary.trim();
  const passages = splitIntoPassages(input.content);
  if (!title) {
    throw new Error("标题不能为空。");
  }
  if (!summary) {
    throw new Error("摘要不能为空。");
  }
  if (!passages.length) {
    throw new Error("至少要有一段有效内容。");
  }

  const knowledgeBase = await loadKnowledgeBase();
  const source: KnowledgeSource = {
    id: randomUUID(),
    title,
    sourceType: input.sourceType,
    summary,
    tags: normalizeTags(input.tags),
    createdAt: new Date().toISOString(),
    passages,
  };

  knowledgeBase.sources.unshift(source);
  await writeFile(KNOWLEDGE_BASE_PATH, JSON.stringify(knowledgeBase, null, 2) + "\n", "utf-8");
  return source;
}

export async function hasKnowledgeSourceWithTitle(title: string) {
  const normalized = title.trim();
  if (!normalized) {
    return false;
  }
  const knowledgeBase = await loadKnowledgeBase();
  return knowledgeBase.sources.some((source) => source.title.trim() === normalized);
}

export async function buildAdvice(question: string, context = ""): Promise<AdviceResult> {
  const trimmedQuestion = question.trim();
  if (!trimmedQuestion) {
    throw new Error("问题不能为空。");
  }

  const knowledgeBase = await loadKnowledgeBase();
  const playbook = choosePlaybook(`${trimmedQuestion}\n${context}`);
  const ranked = rankEvidence(knowledgeBase.sources, `${trimmedQuestion}\n${context}`);
  const evidence = pickEvidence(ranked, 6);
  const visibleEvidence = evidence.slice(0, 3);
  const relatedSources = uniqueBySource(evidence).map((item) => ({
    id: item.source.id,
    title: item.source.title,
    sourceType: item.source.sourceType,
    summary: item.source.summary,
    tags: item.source.tags,
  }));
  const fallbackNotes = relatedSources
    .map((source) => source.summary)
    .filter((summary) => !isQuestionLikeText(summary))
    .slice(0, 2);
  const fallbackActionEvidence = visibleEvidence
    .map((item) => item.excerpt)
    .filter((excerpt) => !isQuestionLikeText(excerpt) && excerpt.length <= 64 && !excerpt.includes("http") && !excerpt.includes("www."));

  const modelAdvice = await generateAdviceWithModel({
    question: trimmedQuestion,
    context,
    playbook,
    evidence,
  }).catch(() => null);

  if (modelAdvice) {
    return {
      situation: modelAdvice.situation,
      summary: modelAdvice.summary,
      principles:
        modelAdvice.principles.length > 0
          ? modelAdvice.principles
          : dedupeStrings([...playbook.principles, ...fallbackNotes]).slice(0, 4),
      actions:
        modelAdvice.actions.length > 0
          ? modelAdvice.actions
          : dedupeStrings([...playbook.actions, ...fallbackActionEvidence.map((item) => toActionFromEvidence(item))]).slice(0, 4),
      pitfalls:
        modelAdvice.pitfalls.length > 0
          ? modelAdvice.pitfalls
          : dedupeStrings([...playbook.pitfalls, ...fallbackActionEvidence.map((item) => toPitfallFromEvidence(item))]).slice(0, 4),
      evidence: visibleEvidence.map((item) => ({
        sourceId: item.source.id,
        sourceTitle: item.source.title,
        sourceType: item.source.sourceType,
        excerpt: item.excerpt,
        score: Number(item.score.toFixed(2)),
        tags: item.source.tags,
      })),
      relatedSources,
    };
  }

  return {
    situation: playbook.label,
    summary: buildSummary(playbook, visibleEvidence),
    principles: dedupeStrings([...playbook.principles, ...fallbackNotes]).slice(0, 4),
    actions: dedupeStrings([...playbook.actions, ...fallbackActionEvidence.map((item) => toActionFromEvidence(item))]).slice(0, 4),
    pitfalls: dedupeStrings([...playbook.pitfalls, ...fallbackActionEvidence.map((item) => toPitfallFromEvidence(item))]).slice(0, 4),
    evidence: visibleEvidence.map((item) => ({
      sourceId: item.source.id,
      sourceTitle: item.source.title,
      sourceType: item.source.sourceType,
      excerpt: item.excerpt,
      score: Number(item.score.toFixed(2)),
      tags: item.source.tags,
    })),
    relatedSources,
  };
}

async function generateAdviceWithModel(input: {
  question: string;
  context: string;
  playbook: Playbook;
  evidence: RankedEvidence[];
}): Promise<AdviceResult | null> {
  const apiKey = process.env.DASHSCOPE_API_KEY?.trim();
  if (!apiKey) {
    return null;
  }

  const model = process.env.WISDOM_ADVISOR_MODEL?.trim() || DEFAULT_QWEN_MODEL;
  const baseUrl = process.env.DASHSCOPE_BASE_URL?.trim() || DEFAULT_QWEN_BASE_URL;
  const endpoint = `${baseUrl.replace(/\/$/, "")}/chat/completions`;

  const evidenceText = input.evidence
    .map(
      (item, index) =>
        `证据${index + 1}\n标题：${item.source.title}\n摘要：${item.source.summary}\n标签：${item.source.tags.join("、")}\n片段：${cleanModelExcerpt(item.excerpt)}`
    )
    .join("\n\n");

  const systemPrompt = [
    "你是一个成熟、克制、见过很多真实场景的中文沟通与处事顾问。",
    "你的任务不是讲道理，也不是空泛安慰，而是基于给定证据做判断、定分寸、给动作。",
    "优先吸收证据中的有效经验，再做适度综合，不要编造证据里完全没有的事实。",
    "表达风格要像真人顾问：稳、具体、不端着，不要像教科书，也不要复读用户问题。",
    "如果证据已经明显指向一个策略，要直接说重点，不要先铺很多空话。",
    "principles 要写成判断，不要写成口号；actions 要写成此刻就能执行的动作；pitfalls 要写成最容易把事情搞坏的处理方式。",
    "输出必须是 JSON 对象，不要输出 Markdown 代码块，不要加解释。",
    "JSON 结构必须包含：situation, summary, principles, actions, pitfalls。",
    "situation 要写成一句简短的场景判断，尽量控制在 10 到 22 个字。",
    "principles/actions/pitfalls 都必须是 3 到 4 条中文短句数组，每条尽量 14 到 30 个字。",
    "summary 用 2 到 3 句中文，先判断局面，再指出最关键的应对方向，读起来要像顾问在当面说话。",
  ].join(" ");

  const userPrompt = [
    `用户问题：${input.question}`,
    input.context ? `补充背景：${input.context}` : "补充背景：无",
    `规则预判场景：${input.playbook.label}`,
    `规则预判原则：${input.playbook.principles.join("；")}`,
    "请综合以下检索证据，给出更像真人顾问的回答：",
    evidenceText || "暂无高相关证据，请基于问题谨慎作答。",
    "注意：不要出现“先沟通再表达”这类空泛套话；不要重复标题；如果用户问题里有明显顾虑，要正面回应那个顾虑。",
    '只返回 JSON，例如：{"situation":"...","summary":"...","principles":["..."],"actions":["..."],"pitfalls":["..."]}',
  ].join("\n\n");

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      temperature: 0.55,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      response_format: { type: "json_object" },
    }),
  });

  if (!response.ok) {
    throw new Error(`Qwen request failed with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as {
    choices?: Array<{
      message?: {
        content?: string;
      };
    }>;
  };

  const rawContent = payload.choices?.[0]?.message?.content?.trim();
  if (!rawContent) {
    throw new Error("Qwen returned empty content.");
  }

  const parsed = safeParseJson(rawContent) as ModelAdvicePayload | null;
  if (!parsed) {
    throw new Error("Qwen returned non-JSON advice.");
  }

  return normalizeModelAdvice(parsed, input.playbook.label);
}

function choosePlaybook(text: string): Playbook {
  const normalized = normalizeText(text);
  let winner = PLAYBOOKS[PLAYBOOKS.length - 1];
  let winnerScore = -1;

  for (const playbook of PLAYBOOKS) {
    const score = playbook.keywords.reduce((sum, keyword) => sum + (normalized.includes(keyword) ? 1 : 0), 0);
    if (score > winnerScore) {
      winner = playbook;
      winnerScore = score;
    }
  }

  return winner;
}

function rankEvidence(sources: KnowledgeSource[], text: string) {
  return sources
    .flatMap((source) =>
      source.passages.map((excerpt) => ({
        source,
        excerpt,
        score: scorePassage(source, excerpt, text),
      }))
    )
    .filter((item) => item.score > 0.08)
    .sort((left, right) => right.score - left.score);
}

function pickEvidence(items: RankedEvidence[], limit: number) {
  const picked: RankedEvidence[] = [];
  const seenSourceIds = new Set<string>();
  const topScore = items[0]?.score ?? 0;
  const softFloor = Math.max(0.14, topScore * 0.58);

  for (const item of items) {
    if (seenSourceIds.has(item.source.id)) {
      continue;
    }
    if (picked.length >= 3 && item.score < softFloor) {
      continue;
    }
    if (picked.length >= 2 && isQuestionLikeText(item.excerpt)) {
      continue;
    }
    seenSourceIds.add(item.source.id);
    picked.push({
      ...item,
      excerpt: cleanDisplayExcerpt(item.excerpt),
    });
    if (picked.length >= limit) {
      break;
    }
  }

  return picked;
}

function scorePassage(source: KnowledgeSource, excerpt: string, text: string) {
  const questionTokens = buildSignals(text);
  const sourceTokens = buildSignals(`${source.title}\n${source.summary}\n${source.tags.join(" ")}\n${excerpt}`);
  const overlap = [...questionTokens].filter((token) => sourceTokens.has(token));
  const overlapScore = overlap.length / Math.max(questionTokens.size, 1);
  const titleBoost = overlap.some((token) => normalizeText(source.title).includes(token)) ? 0.16 : 0;
  const tagBoost = overlap.some((token) => source.tags.some((tag) => normalizeText(tag).includes(token))) ? 0.12 : 0;
  return overlapScore + titleBoost + tagBoost;
}

function buildSignals(text: string) {
  const normalized = normalizeText(text);
  const signals = new Set<string>();
  const latinTokens = normalized.match(/[a-z0-9]{2,}/g) ?? [];

  for (const token of latinTokens) {
    signals.add(token);
  }

  for (let index = 0; index < normalized.length - 1; index += 1) {
    const pair = normalized.slice(index, index + 2);
    if (/[\u4e00-\u9fff]{2}/.test(pair)) {
      signals.add(pair);
    }
  }

  return signals;
}

function normalizeText(value: string) {
  return value.toLowerCase().replace(/[\s，。、“”"'‘’！？!?,.；;：:（）()\[\]【】\-_/]+/g, "");
}

function splitIntoPassages(content: string) {
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

      const passages: string[] = [];
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

function normalizeTags(tags: string[]) {
  return [...new Set(tags.map((tag) => tag.trim()).filter(Boolean))].slice(0, 8);
}

function dedupeStrings(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const normalized = value.trim();
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.push(normalized);
  }
  return result;
}

function uniqueBySource(items: Array<{ source: KnowledgeSource; excerpt: string; score: number }>) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.source.id)) {
      return false;
    }
    seen.add(item.source.id);
    return true;
  });
}

function buildSummary(playbook: Playbook, evidence: Array<{ source: KnowledgeSource; excerpt: string; score: number }>) {
  if (!evidence.length) {
    return `${playbook.summaryLead} 先按“目标、事实、边界、下一步”这条线整理你的表达，再回来判断细节。`;
  }
  const leadEvidence = evidence.find((item) => !isQuestionLikeText(item.excerpt)) ?? evidence[0];
  return `${playbook.summaryLead} 现有资料里最贴近你这次处境的提醒是：${cleanDisplayExcerpt(leadEvidence.excerpt)}`;
}

function toActionFromEvidence(excerpt: string) {
  if (excerpt.includes("先") || excerpt.includes("不要")) {
    return excerpt;
  }
  return `把这条提醒落到动作上：${excerpt}`;
}

function toPitfallFromEvidence(excerpt: string) {
  if (excerpt.includes("不要")) {
    return excerpt;
  }
  if (excerpt.includes("不是")) {
    return `别把问题处理成：${excerpt}`;
  }
  return `别忽略这条信号：${excerpt}`;
}

function normalizeModelAdvice(payload: ModelAdvicePayload, fallbackSituation: string): AdviceResult {
  return {
    situation: normalizeSentence(payload.situation, fallbackSituation),
    summary: normalizeSentence(payload.summary, "先按事实、边界和下一步来整理你的表达。"),
    principles: normalizeList(payload.principles, 4),
    actions: normalizeList(payload.actions, 4),
    pitfalls: normalizeList(payload.pitfalls, 4),
    evidence: [],
    relatedSources: [],
  };
}

function normalizeSentence(value: unknown, fallback: string) {
  if (typeof value !== "string") {
    return fallback;
  }
  const cleaned = value.trim();
  return cleaned || fallback;
}

function normalizeList(value: unknown, limit: number) {
  if (!Array.isArray(value)) {
    return [];
  }
  return dedupeStrings(
    value
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter(Boolean)
  ).slice(0, limit);
}

function safeParseJson(value: string) {
  try {
    return JSON.parse(value);
  } catch {
    const fenced = value.match(/\{[\s\S]*\}/);
    if (!fenced) {
      return null;
    }
    try {
      return JSON.parse(fenced[0]);
    } catch {
      return null;
    }
  }
}

function cleanDisplayExcerpt(value: string) {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= 120) {
    return compact;
  }
  return `${compact.slice(0, 118).trim()}…`;
}

function cleanModelExcerpt(value: string) {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= 180) {
    return compact;
  }
  return `${compact.slice(0, 176).trim()}…`;
}

function isQuestionLikeText(value: string) {
  const compact = value.replace(/\s+/g, " ").trim();
  return /怎么办[？?]?$/.test(compact) || /该怎么/.test(compact) || /要不要/.test(compact);
}
