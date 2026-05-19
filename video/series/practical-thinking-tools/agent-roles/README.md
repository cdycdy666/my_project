# Agent Roles

《实用思维工具》复用《纳瓦尔宝典》已经验证过的多 Agent 架构，但角色目标改为“把思维工具讲成现实场景里的可执行动作”。

## 角色列表

- 00 主编总控
- 01 工具研究 Agent
- 02 内容主编 Agent
- 03 脚本 Agent
- 04 视觉导演 Agent
- 05 配音导演 Agent
- 06 视频评审 Agent
- 07 发布复盘 Agent
- 08 装配剪辑 Agent

## 共同规则

- 只有 00 主编总控能写 `quality-check.md` 和 Notion 同步状态。
- 其他 Agent 只能在 handoff 中提交状态建议。
- 每个 Agent 都必须记录输入、输出、风险和下一步。
- 如果任务结束且后续不会继续使用，必须关闭 Agent，并写入 `agent-registry.md`。
