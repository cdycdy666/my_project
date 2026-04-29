const tools = [
  {
    name: "面试复盘助手",
    status: "迭代中",
    description: "把面试录音、逐字稿和复盘要点整理成结构化总结，帮助后续训练和回看。",
    url: "#",
    accent: "#245c47",
  },
  {
    name: "个人知识问答",
    status: "规划中",
    description: "围绕自己的笔记、资料和项目记录做问答检索，优先服务个人学习场景。",
    url: "",
    accent: "#2b6f8f",
  },
  {
    name: "学习计划生成器",
    status: "实验中",
    description: "根据目标、时间和当前基础，生成阶段计划、每日任务和复盘问题。",
    url: "#",
    accent: "#c9852d",
  },
];

const notes = [
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

const resources = [
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

const toolGrid = document.querySelector("#toolGrid");
const noteList = document.querySelector("#noteList");
const filterBar = document.querySelector("#filterBar");
const resourceGrid = document.querySelector("#resourceGrid");

function safeLink(url, label) {
  if (!url) {
    return `<span class="card-link" aria-disabled="true">暂未公开</span>`;
  }

  return `<a class="card-link" href="${url}" target="_blank" rel="noreferrer">${label}</a>`;
}

function renderTools() {
  toolGrid.innerHTML = tools
    .map(
      (tool) => `
        <article class="tool-card" style="--accent: ${tool.accent}">
          <div class="card-top">
            <h3>${tool.name}</h3>
            <span class="status">${tool.status}</span>
          </div>
          <p class="card-copy">${tool.description}</p>
          ${safeLink(tool.url, "查看工具")}
        </article>
      `
    )
    .join("");
}

function renderNotes() {
  noteList.innerHTML = notes
    .map(
      (note) => `
        <article class="note-item">
          <time class="note-date">${note.date}</time>
          <div>
            <h3>${note.title}</h3>
            <p>${note.summary}</p>
            <div class="note-tags">
              ${note.tags.map((tag) => `<span>${tag}</span>`).join("")}
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderFilters(activeType = "全部") {
  const types = ["全部", ...new Set(resources.map((resource) => resource.type))];

  filterBar.innerHTML = types
    .map(
      (type) => `
        <button
          class="filter-button ${type === activeType ? "is-active" : ""}"
          type="button"
          data-type="${type}"
        >
          ${type}
        </button>
      `
    )
    .join("");
}

function renderResources(activeType = "全部") {
  const visibleResources =
    activeType === "全部"
      ? resources
      : resources.filter((resource) => resource.type === activeType);

  resourceGrid.innerHTML = visibleResources
    .map(
      (resource) => `
        <article class="resource-card" style="--resource-color: ${resource.color}">
          <span class="resource-type">${resource.type}</span>
          <h3>${resource.title}</h3>
          <p>${resource.reason}</p>
          <a class="card-link" href="${resource.url}" target="_blank" rel="noreferrer">打开资源</a>
        </article>
      `
    )
    .join("");
}

filterBar.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-type]");

  if (!button) {
    return;
  }

  const type = button.dataset.type;
  renderFilters(type);
  renderResources(type);
});

renderTools();
renderNotes();
renderFilters();
renderResources();
