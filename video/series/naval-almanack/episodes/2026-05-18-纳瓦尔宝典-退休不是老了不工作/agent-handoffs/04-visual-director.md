# Agent 交接记录

角色：04 视觉导演 Agent

输入：

- `multi-agent-sop.md`
- `quality-standard.md`
- `agent-roles/04-visual-director.md`
- 本项目 `script.md`
- 本项目 `scene-contract.json` v1.2
- 本项目 `agent-handoffs/03-scriptwriter.md`
- 当前 HyperFrames 模板：`hyperframes/index.html` 与 `hyperframes/content.js`

输出：

- 已完成 `shot-list.md`，按 S01-S06 对齐 `scene-contract.json`，总时长 100 秒。
- 已完成 `hyperframes/content.js` 数据替换，保留模板可消费字段。
- `content.js` 中 `meta.duration` 为 `100`，`timing.outroEnd` 为 `100`。
- 已完成本交接记录。
- 未写入 `quality-check.md`，未写入 Notion 同步状态。

关键判断：

- 视觉主方向定为深色编辑部档案风，像一份“时间债务诊断报告”。
- 本片主判断保持为：真正的退休不是不工作，而是今天不再被明天绑架。
- S03/S04 是视觉成败核心，不能做成抽象金句卡，必须保留阿宁日历、周末消息、`23:00` 改方案、时间账单、会议块、`19:00` 后不可约和周五上午作品时间。
- `45 岁`和`60%`只作为阿宁误判的背景证据，不做成理财成功数字。
- 每个 scene 主信息只设 1 个；S03/S04 数字分阶段出现，避免同屏超过 3 组重点。
- 当前模板字段不足以独立表达全部日历/消息 UI，所以本轮只在 `content.js` 数据内尽量贴近“时间账单”语义，没有修改 `index.html`。

制作成本标注：

- S01：低。使用现有 hero、metric、caption 和深色档案底纹表达周日晚工作消息。
- S02：低。使用现有 principle card 和双卡结构表达旧判断到新判断。
- S03：中。使用 case board 左列承载阿宁案例证据，后续若允许改模板可升级成更像手机消息和日历的 UI。
- S04：中。使用 case board 右列承载时间账单、会议块删除、`19:00` 后不可约和周五上午作品时间。
- S05：低。使用 diagnosis cards 做诊断章。
- S06：低。使用 action list 和 outro memory card 做截图行动卡与记忆句。
- 全片无高成本镜头，不依赖实拍、复杂 3D 或新素材采集。

lint / inspect 建议：

- 已在项目 `hyperframes/` 目录执行 `npx hyperframes lint .`，结果为 0 errors / 0 warnings。
- 已执行 `npx hyperframes inspect . --samples 15 --at 1.8,16,35,61.5,84.5,96.8`，结果为 0 layout issues across 6 samples。
- 后续装配阶段建议继续用同一组时间点复看，覆盖开头、原则、阿宁案例、边界对照、行动卡和结尾记忆句。
- inspect 重点看：标题断行、字幕遮挡、case board 左右列信息拥挤、行动卡是否贴边、结尾记忆句是否完整可读。
- 由于本轮用户限定不能改 `index.html`，如果 lint 或 inspect 指向模板硬编码或布局问题，建议由主编决定是否开放下一轮模板微调。

风险：

- `hyperframes/index.html` 仍有硬编码模板文本，例如页面标题、顶部 `04 / SELL & BUILD`、主题 badge 和 mock panel 内部标签；本轮按用户范围没有修改，可能在抽检时造成主题错位。
- 当前 `content.js` 只能改数据，不能把 mock panel 真正换成手机消息、日历、会议块组件；S03/S04 的视觉证据已通过文字和流程项表达，但不是最理想的 UI 具象化。
- S03/S04 案例段信息密度高，装配时必须按 `shot-list.md` 的时间点抽检，避免看起来像数字清单。
- 行动句“删掉 / 定价 / 委托 / 重新谈边界”信息较密，配音和字幕需要拆拍，否则会挤。

主编总控收口：

- 视觉 Agent 完成后，主编总控已修正当前项目 `hyperframes/index.html` 的硬编码文本，替换为 `05 / RETIREMENT AUDIT`、`RETIREMENT IS NOT A DATE`、`time-debt.audit / retirement report`、`CALENDAR / WEEKEND`、`23:00` 和 `BOUNDARY SET`。
- 因此旧 `SELL & BUILD` 文案不再阻塞 G3；剩余风险仅为当前模板仍主要用数据项模拟日历、消息和会议块，具象程度不如专门重写组件。

下一位 agent 需要注意：

- 装配剪辑 Agent 必须确认 `content.js` 100 秒、音频时长和 `index.html` 最终 `data-duration` 是否一致。
- 优先抽检 35.0s、61.5s、84.5s 三个高风险帧。
- 如果后续允许改 `index.html`，优先处理硬编码系列标识与 mock 面板语义，不要新增海边、躺椅、金币、财富自由路线图。
- 不要把本片剪成 FIRE 或早退休攻略；所有视觉证据都应服务“今天被抵押 / 拿回边界”。

生命周期建议：关闭 / 保留，保留原因：

关闭。视觉方案、`content.js` 数据和交接均已落档；后续若 lint/inspect 或样片抽检发现具体问题，可由主编按文件重新派发返工，不需要继续占用当前 Agent 上下文。

是否通过当前闸口：

建议 G3 通过：视觉方案和数据配置已满足 `scene-contract.json` v1.2 的 100 秒结构、案例证据和信息负载要求；`npx hyperframes lint` 与关键时间点 `inspect` 均已通过。仍建议主编在样片或等价抽检中确认是否接受 `index.html` 仍有模板硬编码文本的风险。
