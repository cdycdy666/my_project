# Agent Registry

这份文件由主编总控维护，用于记录本条视频实际启动过的子 Agent，避免只看到昵称但丢失 UUID，导致 G5/G6 无法完整关闭后台任务。

| agent_id | nickname | role | task | status | close_time | notes |
| --- | --- | --- | --- | --- | --- | --- |
| 019e3b58-3b85-7ce1-a9e2-66bd4b678d4c | Dalton | 独立脚本审查 Agent | 审查 G1 文案、scene contract 与工具一致性 | closed | 2026-05-18 21:55 CST | 输出见 `agent-handoffs/03-script-reviewer.md` |
| 019e3b58-3c0a-7082-89f9-a5e3e9426fca | Linnaeus | 独立装配/视觉审查 Agent | 审查 G3/G3.5 视觉装配、旧主题残留与音频风险 | closed | 2026-05-18 21:55 CST | 输出见 `agent-handoffs/08-assembly-visual-reviewer.md` |

## 使用规则

- 每次 `spawn_agent` 返回后，主编总控必须立刻登记 `agent_id`、`nickname`、角色和任务。
- 每次 `close_agent` 成功后，主编总控必须把 `status` 改为 `closed`，并记录关闭时间。
- 如果某个 Agent 需要保留，必须写清楚保留原因和预计后续用途。
- G5/G6 收口时，主编总控必须按本表逐个关闭不再需要的 Agent，不能只依赖聊天上下文记忆。
