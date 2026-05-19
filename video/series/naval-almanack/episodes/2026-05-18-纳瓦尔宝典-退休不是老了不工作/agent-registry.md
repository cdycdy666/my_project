# Agent Registry

这份文件由主编总控维护，用于记录本条视频实际启动过的子 Agent，避免只看到昵称但丢失 UUID，导致 G5/G6 无法完整关闭后台任务。

| agent_id | nickname | role | task | status | close_time | notes |
| --- | --- | --- | --- | --- | --- | --- |
| 019e3a67-3b3b-77a1-b493-70c762227d49 | Erdos | 01 / 02 内容侧 | 选题研究与 brief | closed | 2026-05-18 | 关闭时已不在当前运行列表，返回 not found，视为已关闭 |
| 019e3a6a-7388-74c0-8a61-a7fc532c2b79 | Gibbs | 03 脚本 | `script.md`、`voice/narration.txt`、`scene-contract.json` | closed | 2026-05-18 | 关闭时已不在当前运行列表，返回 not found，视为已关闭 |
| 019e3a71-ba57-79c0-8496-b699a02d0e9f | Archimedes | 04 视觉 | `shot-list.md`、`hyperframes/content.js` | closed | 2026-05-18 | 关闭时已不在当前运行列表，返回 not found，视为已关闭 |
| 019e3a71-baa6-7e02-890a-c9799af6173e | Locke | 05 配音 | `voice/voice-manifest.json` | closed | 2026-05-18 | 关闭时已不在当前运行列表，返回 not found，视为已关闭 |
| 019e3a86-5df2-76a2-ba08-2fc84b3232ec | Curie | 08 装配 | `assembly-check.md` 及返工复核 | closed | 2026-05-18 | 已成功 close；后续重试返回 not found |
| 019e3a95-60a5-77a3-a530-be7662a1429e | Bohr | 06 视频评审 | `review.md`、G4 独立评审 | closed | 2026-05-18 | 已成功 close；后续重试返回 not found |
| 019e3a9a-8e5b-7630-8674-bf613e90da9e | Feynman | 07 发布复盘 | `publish-retrospective.md` | closed | 2026-05-18 | 已成功 close；后续重试返回 not found |
| 019e36d6-6211-7d30-8199-3d4ebceff5c9 | Pauli | legacy worker | 更早一轮遗留后台任务 | closed | 2026-05-18 | UI 显示为后台任务；通过本地 session 记录找回 UUID 后关闭，previous_status 为 pending_init |

## 使用规则

- 每次 `spawn_agent` 返回后，主编总控必须立刻登记 `agent_id`、`nickname`、角色和任务。
- 每次 `close_agent` 成功后，主编总控必须把 `status` 改为 `closed`，并记录关闭时间。
- 如果某个 Agent 需要保留，必须写清楚保留原因和预计后续用途。
- G5/G6 收口时，主编总控必须按本表逐个关闭不再需要的 Agent，不能只依赖聊天上下文记忆。
