# Agent Roles

这个目录定义《纳瓦尔宝典》系列的多 Agent 协作角色。

## 使用方式

1. 主编总控先读 `00-orchestrator.md`。
2. 每个阶段只启用对应 Agent。
3. Agent 完成后，在视频项目的 `agent-handoffs/` 目录写交接记录。
4. 主编总控在 `agent-registry.md` 登记每个 Agent 的 id、nickname、角色、任务和关闭状态。
5. 主编总控读取交接记录后决定是否进入下一阶段。
6. G0 前先消费 `content-system/content-material-library.md` 或补写 `content-material-card.md`。
7. G1 前先完成 `script-lab.md`，再写正式 `script.md`。
8. G3 前先完成 `visual-component-map.md`，再写正式 `shot-list.md`。
9. `quality-check.md` 和 Notion 同步状态只由主编总控写入。
10. 脚本 Agent 必须产出 `scene-contract.json`，视觉导演和配音导演基于它协作。
11. 装配剪辑 Agent 在 G3.5 检查样片和节奏装配，避免主编总控长期兜底剪辑体验。
12. Agent 完成交付且后续不再需要其上下文时，主编总控必须关闭该 Agent，并回填 `agent-registry.md`，避免占用并发/数量上限。

## 角色文件索引

1. `00-orchestrator.md`：主编总控
2. `01-topic-researcher.md`：选题研究
3. `02-content-editor.md`：内容主编
4. `03-scriptwriter.md`：脚本
5. `04-visual-director.md`：视觉导演
6. `05-voice-director.md`：配音导演
7. `06-video-reviewer.md`：视频评审
8. `07-publishing-analyst.md`：发布复盘
9. `08-assembly-editor.md`：装配剪辑

执行顺序以 `multi-agent-sop.md` 为准：`08-assembly-editor.md` 在 G3.5 先于 `06-video-reviewer.md` 启动，`07-publishing-analyst.md` 在 G4 之后创建待发布复盘记录。
