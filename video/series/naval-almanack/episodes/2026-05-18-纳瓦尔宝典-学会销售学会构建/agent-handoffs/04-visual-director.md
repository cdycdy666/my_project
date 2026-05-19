# Agent 交接记录

- 视频：纳瓦尔宝典 - 学会销售学会构建
- 日期：2026-05-18
- 角色：04 视觉导演 Agent
- 当前阶段：G3 Visual Direction
- 输出文件：`shot-list.md`、`hyperframes/index.html`、`hyperframes/content.js`
- Notion 同步：未同步，按用户要求跳过。

## 输入

- 用户任务：把《纳瓦尔宝典-学会销售学会构建》的脚本转成 v4 级别视频画面结构，并改造 HyperFrames 工程。
- 写入范围：仅限 `shot-list.md`、`hyperframes/index.html`、`hyperframes/content.js`、`agent-handoffs/04-visual-director.md`。
- 必读规范：`agent-roles/04-visual-director.md`、`quality-standard.md`。
- 内容输入：当前集 `script.md`、`brief.md`、`agent-handoffs/03-scriptwriter.md`。
- 视觉标杆：`2026-05-17-纳瓦尔宝典-具体知识/hyperframes/index.html` 和 `content.js`。
- 用户指定系列要求：深色编辑部档案风、NAVAL ALMANACK 系列标识、顶部进度线、烧录字幕、案例场景、行动清单、结尾记忆句。

## 关键视觉判断

- 本集不是“销售技巧课”，而是一份“完整价值链能力诊断报告”。因此画面使用深色档案、产品后台、表单和订单证据，而不是明亮课程卡片或成交话术视觉。
- 开头保留现实冲突优先：第一屏大字为“两周产品 / 0 付费”，并配合 14 DAYS、17 VISITS、0 PAID 三张指标卡，直接建立时间成本和结果落差。
- 原则段把纳瓦尔原句放在冲突之后，视觉上用 SELL 与 BUILD 两张卡组成闭环，避免开头书摘感。
- 案例段是本集视觉核心。左栏“小林只会构建”先亮起，右栏“同事先卖问题”在 46.0s 后点亮，60.4s 再出现结论条，让长案例内部有明确状态变化。
- 第 35 句“谁正为它付出时间、钱，或机会成本”已拆为两条字幕，分别落在 78.2-80.4s 和 80.4-82.0s，帮助配音和观众阅读。
- 行动段做成可截图清单：列 10 人、联系 3 人、问上一次付出了什么；底部限制条强调“不新增功能、不买课、不重做作品集”。
- 结尾不喊口号，只保留记忆句和反问：“你做的东西，已经有人付出代价了吗？”

## 输出摘要

- `hyperframes/content.js`：已升级为本集 v4 数据源，composition id 为 `naval-sell-build-v4`，`meta.duration` 为 105.4s，`timing.outroEnd` 为 105.4s。
- `hyperframes/content.js`：字幕覆盖完整口播。为降低底部字幕跳动，第 41-44 句合并为一条限制条件字幕；第 45-47 句合并为一条记忆句字幕。
- `hyperframes/index.html`：从旧 72s 模板升级为第三条 v4 系列结构，包含 NAVAL ALMANACK chrome、顶部进度线、深色编辑部档案风、烧录字幕层、案例双栏和行动清单。
- `shot-list.md`：已按时间、画面、字幕/屏幕字、动效、风险拆出 7 段，并补充素材来源、关键帧抽检建议和风险处理。

## 自检

- 系列标识：通过。画面固定保留 `NAVAL ALMANACK`、`04 / SELL & BUILD`、英文主题 `LEARN TO SELL. LEARN TO BUILD.`。
- 时长一致性：通过。`index.html` 初始 `data-duration`、`content.js` 的 `meta.duration`、`timing.outroEnd` 均为 105.4s。
- 字幕覆盖：通过。所有 48 句口播均进入 captions；第 35 句已按要求拆成两段。
- 案例场景：通过。包含产品后台、AI 模型、评分图表、飞书表单、访谈、99 元人工诊断、10 单等可视化证据。
- 视觉状态变化：通过。主要切换点为 20.6s、31.1s、46.0s、60.4s、75.1s、82.2s、93.3s。
- 行动建议：通过。行动清单可截图，且没有课程广告式 CTA。
- 写入范围：通过。仅修改用户允许的 4 个文件。

## 需要主编注意

- 本版时长 105.4s，贴近当前 105.216s 配音，并基本落在系列 85-105s 推荐区间边缘。若主编压节奏，可优先压缩案例段 31.1-75.0s。
- 开头 hook 采用脚本最终选择“你做了两周产品，最后零个付费”，没有使用 brief 中的“你可能只是别人的产能”作为首屏。后者更适合封面或发布标题。
- “销售 + 构建”右栏需要评审确认不会被误读成销售课。画面文案已尽量指向“发现需求”和“验证代价”。

## 需要配音导演注意

- 第 4 句后、第 6 句后、第 9 句后、第 17 句后仍建议按脚本留停顿，画面已留出卡点。
- 第 35 句已拆成两段字幕，配音可读成“先问，谁正为它付出时间、钱。或者机会成本。”，更像真实口播。
- 第 41-44 句字幕合并为一句，配音仍可按四个短句读，中间有轻停顿即可。

## 需要视频评审注意

- 请重点抽检 42.0s 左栏和 56.0s 右栏的数字可读性，这是本集案例说服力核心。
- 请检查 80.5s 字幕是否遮挡诊断卡。如果 inspect 报告底部字幕风险，可优先把 caption layer 再下移或减小字号。
- 请检查结尾 97.4-105.2s 的反问是否停留过长；如果主编后续重配字幕节奏，可重新按音频时间轴细调 captions。

## 建议验证命令

```bash
cd /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-学会销售学会构建/hyperframes
npx hyperframes lint
npx hyperframes inspect --samples 15
```
