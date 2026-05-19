# 纳瓦尔短视频模板

这个模板适合做《纳瓦尔宝典》风格的认知类短视频，建议时长控制在 85-105 秒，超过 110 秒必须说明原因。

## 开工前硬规则

- 先按多 Agent SOP 完成 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`。
- `content-material-card.md` 必须引用内容原料库，或补写新的原料卡。
- `script-lab.md` 必须先验证 5 个钩子、3 个案例角度、2 个反驳桥、3 句记忆句和留存检查。
- `script.md` 必须有 3 个开头钩子、逐句连续性自检、口语自然度自检和脚本自评分。
- `scene-contract.json` 必须使用 v1.2 字段，视觉、配音、装配都要消费同一份协议。
- `visual-component-map.md` 必须先选择主组件，再进入 `shot-list.md`。
- `quality-check.md` 只由主编总控写，其他 Agent 只写 handoff。
- Notion 同步只看 `notion-sync-receipt.md`。

## 主要修改位置

1. `content-material-card.md` / `brief.md` / `script-lab.md` / `script.md` / `scene-contract.json`
   明确本条讲哪条原则、给谁看、最终想让观众记住什么，以及每个 scene 的能量和留存任务。
2. `visual-component-map.md` / `shot-list.md` / `hyperframes/content.js`
   改屏幕上的标题、卡片、对照段、结尾文案、字幕和各段时长。
3. `voice/narration.txt`
   改成最终口播稿，再生成试音和全片配音。

## 目录说明

- `hyperframes/index.html`
  通用画面模板。通常不需要频繁改结构。
- `hyperframes/content.js`
  当前视频的内容配置。以后每一条主要改这里。
- `voice/narration.txt`
  当前视频的旁白稿。

## 推荐流程

1. 新建项目
   `./bin/new-naval-video.sh 纳瓦尔宝典-主题`
2. 写内容协议
   先完成 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`voice/narration.txt` 和 `scene-contract.json`
3. 配画面与试音
   基于 `scene-contract.json` 先写 `visual-component-map.md`，再写 `shot-list.md`、改 `hyperframes/content.js`、生成 30 秒试音
4. 先渲无声版并抽检
   `./bin/render-naval-video.sh /绝对路径/到/项目目录`
5. 写装配检查
   完成 15-30 秒样片或等价片段抽检，写 `assembly-check.md`
6. 封装成片
   `./bin/render-naval-video.sh /绝对路径/到/项目目录 voice/配音文件.mp3`
7. 评审与收口
   写 `review.md`、`notion-sync-receipt.md`、`agent-retrospective.md`，关闭不再需要的 Agent

## 内容结构建议

适合纳瓦尔内容的 5 段式：

1. 钩子：一句反常识问题或判断
2. 原则：纳瓦尔核心原则的最短表达
3. 展开：3 个解释卡片
4. 对照：短期 vs 长期，努力 vs 杠杆，运气 vs 系统
5. 收束：一句能被记住的话

## 配音建议

- 如果追求最真实，优先真人录音
- 如果用 TTS，先生成 1-2 句样音再决定整段
- 最终旁白最好和画面总时长差不超过 2-3 秒
