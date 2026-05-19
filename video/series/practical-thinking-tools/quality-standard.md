# 《实用思维工具》质量标准

## 总目标

每条视频不是让观众“知道一个工具”，而是让观众马上能用这个工具处理一个具体问题。

## 硬闸口

### G0 选题与原料

- `source-manifest.json` 和 `course-source-index.md` 已更新
- 已选择 1 个主课程源，问答或特别放送只能作为辅助源
- 至少引用 1 张内容原料卡，或补写 `content-material-card.md`
- 主题必须是一个明确思维工具
- 必须绑定一个具体高频场景
- 必须写清楚“观众默认误判”
- 必须完成从课程源到原创工具卡的二次转化，不能直接搬运课程原文
- 内容评分低于 9.0 不进入制作

### G1 脚本

- 必须完成 `script-lab.md`
- `script-lab.md` 必须包含 5 个钩子、3 个案例角度、2 个误用风险、3 句记忆句
- `script-lab.md` 总分必须 >= 90 / 100
- 逐句口播必须无突兀时间跳跃、无未经铺垫的新概念
- `scene-contract.json` 必须合法，且每个 scene 都有 `viewer_state_before` / `viewer_state_after`

### G2 配音

- 必须写入 `voice/voice-manifest.json`
- 必须标记 `technical_audio_pass`
- 必须标记 `audio_subjective_review`: `confirmed` 或 `pending`
- 系统未实际人耳听审时，不能把主观听感写成 confirmed

### G3 视觉

- 必须完成 `visual-component-map.md`
- 每个 scene 只能有一个主视觉任务
- 不能把工具视频做成定义 PPT
- 每个工具步骤必须有可视化动作或界面隐喻

### G3.5 装配

- 必须写 `assembly-check.md`
- 检查字幕、镜头、停顿、转场和行动卡是否顺
- 必须检查 `preview/contact-sheet-visual.jpg` 和 `preview/contact-sheet-final.jpg`
- 首 5 秒必须同时成立：钩子清楚、字幕可读、画面有动作
- 尾 15 秒必须保留记忆句、行动问题或评论引导，不能长时间只剩氛围背景
- 样片或等价片段抽检未通过，不进入最终成片评审

### G4 成片评审

- `review.md` 必须区分结构问题和成片问题
- 必须区分 `technical-cut` 和 `publish-cut`
- 综合评分低于 9.0 或发布可用性低于 9.0，不进入 G5
- 如果没有实际听音频，`audio_subjective_review` 必须保持 pending

### G5 发布与 Notion

- Notion 视频页面必须同步 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`、`assembly-check.md`
- 必须生成 `notion-sync-receipt.md`
- Notion 同步状态只由主编总控写

### G6 复盘

- 必须写 `agent-retrospective.md`
- 必须记录是否需要更新工具卡、脚本实验室或视觉组件库
- 如果没有发现确定性改进点，不强行修改 SOP

## 评分重点

| 维度 | 分值 | 说明 |
| --- | ---: | --- |
| 现实场景强度 | 20 | 是否击中具体问题，而不是抽象概念 |
| 工具解释清晰度 | 20 | 是否一句话能转述 |
| 案例可代入度 | 20 | 是否能看到自己 |
| 行动可执行性 | 20 | 今天或本周能不能做 |
| 成片体验 | 20 | 节奏、视觉、配音、字幕是否统一 |

## 成片状态定义

| 状态 | 含义 | 能否发布 |
| --- | --- | --- |
| `draft-cut` | 只验证方向，音画或结构仍未闭合 | 不能 |
| `technical-cut` | 音画、布局、时长、音轨技术通过，但发布包装或人工看听仍 pending | 不能 |
| `publish-cut` | 评分、必改项、发布包装、人工看听全部通过 | 可以 |
