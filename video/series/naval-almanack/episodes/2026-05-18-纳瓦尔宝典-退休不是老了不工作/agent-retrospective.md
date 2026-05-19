# Agent 复盘与自动迭代

## 基本信息

- 视频：纳瓦尔宝典 - 退休不是老了不工作
- 复盘日期：2026-05-18
- 本地目录：`/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-退休不是老了不工作`
- SOP 版本：最新多 Agent SOP，含 G3.5 装配剪辑 Agent、G4 独立评审、G5 Notion 回执、G6 自动迭代。
- 总结论：本轮多 Agent 系统正确运行，成片 G4 条件通过，G5 Notion 同步完成。需要做两项轻量系统修改：显式固化角色文件名，避免发布复盘 Agent 调度时引用错误路径；新增 `agent-registry.md`，避免只看到后台昵称却丢失 UUID。

## 本轮 Agent 输入输出

| Agent | 输入 | 输出 | 评分 / 结论 |
| --- | --- | --- | --- |
| 01 选题研究 | 主题、质量标准、SOP | `content-review.md`、`agent-handoffs/01-topic-researcher.md` | 9.1 / 10，G0 通过 |
| 02 内容主编 | `content-review.md`、SOP | `brief.md`、`agent-handoffs/02-content-editor.md` | 只讲一个核心判断，G1 可进入脚本 |
| 03 脚本 | `content-review.md`、`brief.md`、脚本角色定义 | `script.md`、`voice/narration.txt`、`scene-contract.json`、handoff | 96 / 100，已修正旧版“三个月后”突兀跳跃 |
| 04 视觉导演 | `scene-contract.json`、`script.md` | `shot-list.md`、`hyperframes/content.js`、handoff | G3 通过；旧模板残留由装配 Agent 后续抓出并局部修正 |
| 05 配音导演 | `scene-contract.json`、`voice/narration.txt`、TTS 结果 | `voice/voice-manifest.json`、handoff | `technical_audio_pass=pass`，`audio_subjective_review=pending` |
| 08 装配剪辑 | 成片、抽帧、脚本、视觉、配音 manifest | `assembly-check.md`、handoff | 初检暂缓，通过独立抓出 S02 旧模板残留；返工后 G3.5 条件通过 |
| 06 视频评审 | 成片、抽帧、全套生产文档 | `review.md`、handoff | 9.0 / 10，G4 条件通过 |
| 07 发布复盘 | `publish-assets.md`、`review.md`、质量状态 | `publish-retrospective.md`、handoff | 已创建待发布复盘记录，不虚构平台数据 |
| 主编总控 | 全部交付物和评审结论 | `quality-check.md`、`notion-sync-receipt.md`、本文件 | G5 完成，G6 记录并完成轻量迭代 |

## 关键发现

- 有效发现 1：08 装配剪辑 Agent 抓出了 S02 原则卡 `HALF VALUE CHAIN = HALF LEVERAGE` 旧模板残留，说明 G3.5 独立装配闸口是必要的。
- 有效发现 2：06 视频评审 Agent 没有把未实际听过的音频写成 confirmed，音频主观听感保持 pending，符合 SOP。
- 有效发现 3：07 发布复盘 Agent 发现调度提示里引用了不存在的 `agent-roles/07-publish-retrospective.md`，实际文件是 `agent-roles/07-publishing-analyst.md`。
- 有效发现 4：界面显示一个遗留后台 worker `Pauli`，主线程最初只有昵称没有 UUID；通过本地 session 记录找回 `019e36d6-6211-7d30-8199-3d4ebceff5c9` 后关闭，previous_status 为 `pending_init`。
- 有效发现 5：所有子 Agent 完成交付后均已关闭，未继续占用 Agent 上限。

## 系统修改判断

需要修改。

原因：角色文件名引用错误和后台 Agent UUID 丢失都不是一次性审美偏好，而是未来每次启动多 Agent 协作都可能复现的流程稳定性问题。修改方式很轻，不增加制作成本，只把角色文件名和 Agent 台账要求显式写进 SOP、角色索引和新项目模板。

## 已完成的系统修改

- 已更新 `multi-agent-sop.md`：角色列表新增“角色文件”列，明确 07 发布复盘 Agent 对应 `agent-roles/07-publishing-analyst.md`，08 装配剪辑 Agent 对应 `agent-roles/08-assembly-editor.md`。
- 已更新 `multi-agent-sop.md`：Agent 生命周期管理新增 `agent-registry.md` 登记要求，G5/G6 必须按台账关闭后台 Agent。
- 已更新 `agent-roles/README.md`：将“角色顺序”改为“角色文件索引”，并说明执行顺序以 `multi-agent-sop.md` 为准，08 在 G3.5 先于 06 启动，07 在 G4 后创建待发布复盘记录。
- 已新增当前项目 `agent-registry.md`：补齐本轮所有 Agent 和遗留 `Pauli` 的关闭状态。
- 已新增模板 `video/templates/agent-registry.md`，并更新 `bin/new-naval-video.sh`，未来新项目自动带 Agent 台账。
- 已同步 Notion `多 Agent 协作 SOP` 页面。
- 已同步 Notion `07 发布复盘 Agent` 页面。

## 下一轮建议

- 继续保留 G3.5 装配 Agent，它本轮实际抓到了主编和视觉阶段漏掉的旧模板残留。
- 下一条视频调度 Agent 时，提示词必须引用 `multi-agent-sop.md` 中的角色文件表，不再凭记忆写角色路径；每次 `spawn_agent` 返回后必须立刻写入 `agent-registry.md`。
- 发布前人工看听仍由用户完成；如果第 39 句连读，优先只做 S06 单句补丁或增加 break，不回退整条配音。
- 后续若追求更高完播率，可优先升级 S03/S04 的日历、消息和会议块组件，让案例段更像真实界面，而不是模板卡片。

## G6 结论

- 已生成 `agent-retrospective.md`。
- 已覆盖各 Agent 的输入、输出、评分、问题和下一轮建议。
- 已明确：本轮需要轻量修改，并已完成。
- 已同步到 Notion。
