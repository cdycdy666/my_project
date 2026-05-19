# 多 Agent 协作 SOP

这套协作方式的目标不是把流程复杂化，而是让每个关键质量点都有专门角色负责，并且所有交接都落到文件和 Notion。

## 核心原则

- 一个主编总控，多个专业 agent 分工。
- 每个 agent 只对自己的交付物负责，不越权修改其他阶段结论。
- 所有 agent 输出必须落到本地 Markdown，并由主编总控统一同步到 Notion。
- 任何阶段低于质量线，都回到上一阶段重写，不允许“先做出来看看”。
- 最终是否发布只由主编总控决定。
- 自动迭代不是强制改动；如果没有发现高确定性改进点，只记录“本轮无需修改”。
- `quality-check.md` 是主编总控专属状态源，其他 Agent 不直接写入。
- Notion 同步状态只由主编总控在 G5 写入同步回执，其他 Agent 不判断“已同步”。
- 每个 Agent 都必须有生命周期管理：任务完成、交接落档且后续不再依赖其上下文时，由主编总控关闭，避免占用 Agent 上限。
- 内容原料库、脚本实验室、视觉组件库是三类固定生产资产：新视频必须先消费资产，再进入正式脚本和画面制作。

## 角色列表

| 角色 | 角色文件 | 负责什么 | 主要输出 | 过闸标准 |
| --- | --- | --- | --- | --- |
| 主编总控 | `agent-roles/00-orchestrator.md` | 串联流程、裁决取舍、维护系列一致性 | `quality-check.md`、`notion-sync-receipt.md` | 所有 G0-G6 闸口通过 |
| 选题研究 Agent | `agent-roles/01-topic-researcher.md` | 找选题、判断痛点、提炼反直觉观点 | `content-review.md`、`content-material-card.md` | 内容评分 >= 9.0 |
| 内容主编 Agent | `agent-roles/02-content-editor.md` | 压缩观点、明确受众、避免书摘化 | `brief.md` | 只讲一个核心判断 |
| 脚本 Agent | `agent-roles/03-scriptwriter.md` | 打磨钩子、案例、口播、留存结构、逐句连续性和行动建议 | `script-lab.md`、`script.md`、`scene-contract.json` | 实验分 >= 90、口播自然、脚本自评分 >= 90 |
| 视觉导演 Agent | `agent-roles/04-visual-director.md` | 把脚本转成画面结构和节奏 | `visual-component-map.md`、`shot-list.md`、`hyperframes/content.js` | 组件映射清楚，不是纯文字 PPT |
| 配音导演 Agent | `agent-roles/05-voice-director.md` | 检查口播技术质量、停顿和音色风险 | `voice/voice-manifest.json`、试音结论 | `technical_audio_pass` |
| 装配剪辑 Agent | `agent-roles/08-assembly-editor.md` | 检查音频、字幕、镜头、停顿、转场是否装成顺畅体验 | `assembly-check.md` | 样片和节奏装配通过 |
| 视频评审 Agent | `agent-roles/06-video-reviewer.md` | 独立评审成片，提出必改建议 | `review.md` | 成片评分 >= 9.0 |
| 发布复盘 Agent | `agent-roles/07-publishing-analyst.md` | 发布后看数据和评论，反推新选题 | Notion `发布复盘库`、`publish-retrospective.md` | 有下一步动作 |

## 标准执行顺序

1. 主编总控从 Notion `选题库`、`素材引用库` 或本地 `content-system/content-material-library.md` 选择候选主题。
2. 选题研究 Agent 引用或补写内容原料卡，并写 `content-review.md`。
3. 主编总控检查 G0：没有合格原料卡或内容评分低于 9.0 停止。
4. 内容主编 Agent 写 `brief.md`，把原料卡压缩成一个核心判断。
5. 脚本 Agent 先写 `script-lab.md`，完成钩子、案例、反驳、记忆句和留存实验。
6. 脚本 Agent 再写 `script.md`、`voice/narration.txt` 和 `scene-contract.json`。
7. 主编总控检查 G1：`script-lab.md` 和 `scene-contract.json` 都通过后，才进入画面和配音。
8. 视觉导演 Agent 先写 `visual-component-map.md`，为每个 scene 选择主组件。
9. 视觉导演 Agent 基于 `scene-contract.json` 和 `visual-component-map.md` 写 `shot-list.md`。
10. 配音导演 Agent 生成并评估 30 秒试音，写 `voice/voice-manifest.json` 和 handoff。
11. 主编总控把生产文档同步到 Notion 视频页面；同步状态只由主编记录。
12. 视觉导演 Agent 完成 HyperFrames 画面。
13. 主编总控渲染 15-30 秒样片或等价片段抽检，优先覆盖 hook、原则或案例切换。
14. 装配剪辑 Agent 写 `assembly-check.md`，检查切点、落字、停顿、转场、BGM 风险和节奏舒适度。
15. 主编总控渲染无声版、抽帧、跑 lint / inspect。
16. 配音导演 Agent 确认全片配音技术状态。
17. 主编总控渲染最终成片并跑 ffprobe。
18. 视频评审 Agent 写 `review.md`，同时检查脚本实验和组件映射是否在成片中兑现。
19. 主编总控按评审建议修改，必要时回到脚本、视觉、配音或装配阶段。
20. 主编总控完成 G5 发布资产、Notion 同步和 `notion-sync-receipt.md`。
21. 发布复盘 Agent 在发布后更新 Notion `发布复盘库`，并把高价值评论回流到内容原料库。
22. 主编总控生成 `agent-retrospective.md`，复盘各 Agent 输入、输出和评分。
23. 主编总控判断是否进入 G6 自动迭代：只有发现明确、可复用、高确定性的改进点，才更新 Agent 定义、评分标准或 SOP。

## 可并行的任务

- 选题研究 Agent 可以和素材引用整理并行。
- 内容主编 Agent 完成 brief 后，脚本 Agent 可以写 `script-lab.md`；视觉导演 Agent 只能基于 brief 草拟视觉母题，不能写最终分镜。
- `script-lab.md` 和 `scene-contract.json` 通过后，视觉导演 Agent 可以写 `visual-component-map.md`，配音导演 Agent 可以准备试音策略。
- `scene-contract.json` 通过后，视觉导演 Agent 和配音导演 Agent 可以并行推进。
- 视觉画面、配音技术检查和样片准备完成后，装配剪辑 Agent 可以独立做 G3.5 检查。
- 成片渲染后，视频评审 Agent 可以评审，发布复盘 Agent 可以提前准备复盘记录模板。

## 不建议并行的任务

- `content-review.md` 未过 9.0 前，不进入脚本和画面。
- `content-material-card.md` 或内容原料库引用未完成前，不进入 G0。
- `script-lab.md` 未过 90 分前，不写最终 `script.md`。
- `scene-contract.json` 未通过前，不写最终 `shot-list.md`。
- `visual-component-map.md` 未完成前，不写最终 `shot-list.md`。
- `script.md` 未定稿前，不生成全片配音。
- `shot-list.md` 未过审前，不大规模写 HyperFrames 动画。
- `assembly-check.md` 未通过前，不进入最终成片评审。
- 视频评审未通过前，不进入待发布。

## 状态所有权

- `quality-check.md` 只允许主编总控写入，是 G0-G6 的唯一状态源。
- 其他 Agent 只能写自己的交付物、`agent-handoffs/` 记录或独立评估文件。
- 其他 Agent 如果发现某个闸口风险，只在 handoff 中提出“状态变更建议”，由主编决定是否写入 `quality-check.md`。
- Notion 同步状态只看 `notion-sync-receipt.md` 和主编写入的 G5 记录，不看各 Agent handoff 中的描述。
- `review.md` 可以判断成片质量，但不能替代 G5 发布资产和 Notion 同步确认。

## Agent 生命周期管理

主编总控负责管理 Agent 的创建、复用和关闭，避免因为历史 Agent 未关闭导致新任务无法启动。

- 创建前先检查是否已有同角色、同项目、同上下文的 Agent 可复用；能复用就用 `send_input`，不要重复创建。
- 每次 `spawn_agent` 返回后，主编总控必须立刻登记到 `agent-registry.md`，至少包含 `agent_id`、nickname、角色、任务和初始状态；不能只依赖聊天上下文记忆。
- Agent 完成交付后，必须先确认输出已写入对应文件或 `agent-handoffs/`，再判断是否关闭。
- 如果后续流程不再依赖该 Agent 的上下文，主编总控应立即关闭该 Agent，并回填 `agent-registry.md` 的关闭状态。
- 如果同一 Agent 还要参与返工复审或下一轮迭代，可以暂时保留，但必须在 `agent-retrospective.md` 里说明保留原因。
- G5 / G6 收口时必须按 `agent-registry.md` 做一次 Agent 清理：关闭所有不再需要的子 Agent，只保留用户明确要求继续跟进的长期 Agent。
- 不允许把 Agent 长期开着当“备用记忆”；长期知识必须落到本地文件和 Notion，而不是留在 Agent 会话里。
- 如果遇到 Agent 数量上限，优先关闭已交付、已落档、无后续依赖的 Agent，再考虑创建新 Agent。

## Agent 交接格式

每次 agent 完成工作，都要在 `agent-handoffs/` 下写一份交接记录：

```text
角色：
输入：
输出：
关键判断：
风险：
下一位 agent 需要注意：
生命周期建议：关闭 / 保留，保留原因：
是否通过当前闸口：
```

## 本轮新增硬检查

- 新项目开工后先确认 HyperFrames 模板版本；如果仍是旧模板，必须先升级到当前 v4 系列结构。
- 新项目开工后先确认内容原料卡、`script-lab.md` 和 `visual-component-map.md` 三份前置资产已进入流程。
- G1 不只检查最终脚本，也检查 `script-lab.md` 中被舍弃方案是否更强；如果更强，退回脚本 Agent 重新选择。
- G3 不只检查分镜，也检查视觉组件是否来自组件库、是否承载案例场景、是否有低成本降级方案。
- G3 必须搜索旧模板残留文案、旧集数、旧主题英文和旧案例语义；发现残留不允许过闸。
- 配音完成后检查音频时长、`content.js` 时长、`index.html` 时长；不一致时先修正，再渲染。
- 配音导演和视频评审如果没有实际听音频，必须写清评估边界，不能把技术检测当成主观听审。
- G2 和 G4 的音频结论拆成 `technical_audio_pass` 与 `audio_subjective_review`；系统未实际听音频时，主观听感只能标记为 `pending`。
- G3.5 必须有样片或等价片段抽检，并写入 `assembly-check.md`。
- G4 只负责成片是否可发布；G5 的 Notion 同步、发布资产和复盘记录必须由主编总控确认后再勾选。
- G4 通过后立即创建发布复盘库“待发布”记录，发布后再回填平台数据。
- 发布复盘的高价值评论、误解和反驳必须回流到内容原料库，作为下一轮选题燃料。
- G5 必须生成 `notion-sync-receipt.md`，记录视频台账、视频页面、选题库、发布复盘库和生产文档同步情况。
- G5 / G6 收口时必须清理不再需要的 Agent，避免下次制作触发 Agent 上限。
- G6 必须区分“复盘记录”和“系统修改”：记录每次都做，修改只在确有必要时做。
- 如果本轮没有发现值得固化的改进，`agent-retrospective.md` 需要写明“本轮无高确定性迭代项，保持现有 Agent 定义和 SOP”。

## Scene Contract

`scene-contract.json` 是脚本、视觉和配音之间的结构化协议，由脚本 Agent 生成，主编总控检查，视觉导演和配音导演共同消费。

每个 scene 至少包含：

- `scene_id`
- `narration_text`
- `expected_duration`
- `key_numbers`
- `visual_goal`
- `emphasis_words`
- `subtitle_priority`
- `voice_notes`
- `scene_energy`
- `retention_goal`
- `viewer_state_before`
- `viewer_state_after`
- `visual_proof`
- `screen_text`
- `continuity_notes`

它的作用是让并行协作从“凭理解对齐”升级成“按协议对齐”。视觉导演不得只靠自由理解脚本写最终分镜。

`scene_energy` 使用 1-5 分：5 是强冲突或强诊断，3 是解释和承接，1-2 是过渡和留白。

`retention_goal` 用来说明这一段的留存任务，例如：拉住人、建立信任、给证据、让人截图、制造记忆点、促评论。

## 失败模式责任

- 选题研究 Agent：防止选题变成书摘、泛鸡汤或没有平台第一眼冲突。
- 内容主编 Agent：防止内容发散成多主题，防止原料卡被机械复制，防止观众旧判断没有被替换。
- 脚本 Agent：防止跳过脚本实验室，防止口播写成文章，防止每个 scene 能量一样重，防止无铺垫的时间跳跃、数字跳跃、结果跳跃或概念跳跃。
- 视觉导演 Agent：防止跳过组件映射，防止画面变成 PPT，防止单屏信息过载或高成本不可复用。
- 配音导演 Agent：防止机器播报、数字重音丢失、中英混排停顿别扭和 BGM 压口播。
- 装配剪辑 Agent：防止脚本、视觉、配音各自没问题但拼在一起不顺。
- 视频评审 Agent：防止未验证的事项被当成通过。
- 发布复盘 Agent：防止复盘只停留在数据汇总，没有回流为下一条内容燃料。

## G6 Agent 复盘与自动迭代

每条视频完成后必须做一次 Agent 复盘，但不强制修改系统。

G6 输入：

- 本轮所有 `agent-handoffs/*.md`
- `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`
- `quality-check.md`、`assembly-check.md`、`review.md`
- `notion-sync-receipt.md`
- Notion `视频台账` 和 `发布复盘库`

G6 输出：

- `agent-retrospective.md`
- 可选更新：`agent-roles/*.md`
- 可选更新：`multi-agent-sop.md`、`quality-standard.md`
- 可选同步：Notion `Agent 角色库`、`多 Agent 协作 SOP`

允许更新 Agent 定义或 SOP 的条件：

- 该问题实际影响了成片质量、流程稳定性或发布判断。
- 该问题不是一次性偶发，而是未来视频也可能复现。
- 能写成明确检查项、评分项、交接要求或禁止事项。
- 修改不会让流程明显变重，或者增加的成本低于它减少的返工。

不允许更新的情况：

- 只是个人审美偏好，无法稳定复用。
- 本轮没有出现实际问题，只是为了显得“有迭代”。
- 改动会让 Agent 职责边界变模糊。
- 没有证据说明修改能提升后续视频质量。

G6 通过标准：

- 已完成 `agent-retrospective.md`。
- 已明确写出“需要修改”或“无需修改”。
- 如果修改了 Agent 定义或 SOP，已同步到 Notion。
- 如果没有修改，也已记录原因，不能空过。

## Notion 固定落点

- `选题库`：选题研究结论、内容评分、是否进入制作。
- `视频台账`：生产文档、成片路径、评审结论、发布状态。
- `素材引用库`：原文、金句、案例、观众问题。
- `发布复盘库`：发布数据、评论洞察、下一步动作。
- `Agent 角色库`：G6 后的角色定义、评分标准和新增硬检查。

## 硬性停止条件

- 内容评分低于 9.0。
- 没有具体人物和场景案例。
- 口播读起来像文章。
- 音频技术检查未通过，或主编发布前看听时判断配音明显不真实。
- 非主编总控直接改写 `quality-check.md` 或 Notion 同步状态。
- `npx hyperframes lint` 或 `inspect` 有未处理问题。
- 成片评审低于 9.0。
- G5 未生成 `notion-sync-receipt.md`。
- 上一条视频没有完成 G6 复盘，就直接开始下一条正式制作。
