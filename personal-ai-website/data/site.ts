export type Tool = {
  name: string;
  status: string;
  description: string;
  url?: string;
  accent: string;
  cta?: string;
};

export type Note = {
  date: string;
  title: string;
  summary: string;
  tags: string[];
};

export type Resource = {
  title: string;
  type: "AI 工具" | "技术文章" | "课程" | "视频";
  reason: string;
  url: string;
  color: string;
};

export const tools: Tool[] = [
  {
    name: "面试复盘助手",
    status: "已接入",
    description: "上传面试录音或填写音频 URL，直接在个人网站里触发转写、摘要和 Notion 复盘草稿。",
    url: "/tools/interview-pipeline",
    accent: "#245c47",
    cta: "进入复盘工作台",
  },
  {
    name: "表达模仿教练",
    status: "已接入",
    description: "上传目标视频和模仿视频，在个人网站里统一管理练习历史、分析结果和下一轮训练任务。",
    url: "/tools/verbal-expression-coach",
    accent: "#2b6f8f",
    cta: "进入表达教练",
  },
  {
    name: "学习计划生成器",
    status: "实验中",
    description: "根据目标、时间和当前基础，生成阶段计划、每日任务和复盘问题。",
    url: "#",
    accent: "#c9852d",
    cta: "查看规划",
  },
];

export const notes: Note[] = [
  {
    date: "2026.04",
    title: "个人网站 MVP 阶段总结",
    summary: "先把工具、学习笔记和资源收藏放进同一个页面，降低持续记录的阻力。",
    tags: ["阶段总结", "个人网站"],
  },
  {
    date: "2026.04",
    title: "AI 工具开发路线",
    summary: "优先沉淀真实使用场景里的小工具，再逐步抽象成稳定的工作流。",
    tags: ["AI 工具", "路线规划"],
  },
  {
    date: "2026.04",
    title: "学习记录的最小结构",
    summary: "每条记录保留主题、阶段、收获和下一步，避免写成难维护的长文档。",
    tags: ["学习笔记", "复盘"],
  },
];

export const resources: Resource[] = [
  {
    title: "OpenAI Docs",
    type: "AI 工具",
    reason: "查询模型能力、API 用法和最新实践的基础入口。",
    url: "https://platform.openai.com/docs",
    color: "#245c47",
  },
  {
    title: "Anthropic Prompt Engineering",
    type: "技术文章",
    reason: "适合系统梳理提示词、评估和上下文设计。",
    url: "https://docs.anthropic.com/",
    color: "#2b6f8f",
  },
  {
    title: "Full Stack Open",
    type: "课程",
    reason: "覆盖现代 Web 开发、测试和后端基础的系统课程。",
    url: "https://fullstackopen.com/",
    color: "#c9852d",
  },
  {
    title: "Stanford CS25",
    type: "视频",
    reason: "围绕 Transformer 和大模型主题的公开讲座集合。",
    url: "https://web.stanford.edu/class/cs25/",
    color: "#d9604a",
  },
  {
    title: "MDN Web Docs",
    type: "技术文章",
    reason: "查 HTML、CSS、JavaScript 细节时最稳的参考之一。",
    url: "https://developer.mozilla.org/",
    color: "#2b6f8f",
  },
  {
    title: "Hugging Face",
    type: "AI 工具",
    reason: "模型、数据集和开源 AI 应用的高频入口。",
    url: "https://huggingface.co/",
    color: "#245c47",
  },
  {
    title: "DeepLearning.AI",
    type: "课程",
    reason: "适合补齐 AI 应用、机器学习和智能体方向的课程。",
    url: "https://www.deeplearning.ai/",
    color: "#c9852d",
  },
  {
    title: "Fireship",
    type: "视频",
    reason: "快速了解新技术和工程概念，适合做轻量扫盲。",
    url: "https://www.youtube.com/c/Fireship",
    color: "#d9604a",
  },
];

export const resourceTypes = ["全部", ...new Set(resources.map((resource) => resource.type))];
