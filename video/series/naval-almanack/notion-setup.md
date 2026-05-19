# Notion Setup

这份说明用于把《纳瓦尔宝典》系列视频管理到一个清晰的 `Notion` 工作区里。

目标不是把视频生产搬进 `Notion`，而是把管理层理顺：

- 本地目录负责工程文件、配音、字幕、成片
- `Notion` 负责选题、状态、排期、发布和复盘

## 推荐工作区结构

建议在 `Notion` 里建立一个顶层页面：

`Naval Almanack Series`

下面放 4 个核心数据库：

1. `选题库`
2. `视频台账`
3. `素材引用库`
4. `发布复盘库`

当前已创建：

- `选题库`：https://www.notion.so/d224f5ed8769460dbb0d511a08da8501
- `视频台账`：https://www.notion.so/86e2b3bccef24420bf1460ed79d8de99
- `发布复盘库`：https://www.notion.so/4e995f70ea8e4bbd971a85b769eac7d0
- `素材引用库`：https://www.notion.so/552b798dce1c42309003d8d71eddd5ea

同时建议保留 2 个固定说明页：

- `生产文档同步 SOP`：https://www.notion.so/36332f4915ee8134b7e6cdbc61dedb8b
- `多 Agent 协作 SOP`：https://www.notion.so/36332f4915ee81728144defb5ba1f2b6
- `Agent 角色库`：https://www.notion.so/f51b4ba07ff64014844f8e46f6572d2f

## 1. 选题库

这个库负责管理“以后要做什么”。

### 建议字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 主题 | Title | 例如：赚钱不是靠出卖时间，而是靠杠杆 |
| 核心原则 | Select | 长期主义 / 杠杆 / 幸福 / 判断力 / 欲望 等 |
| 系列 | Select | Naval Almanack |
| 优先级 | Select | 高 / 中 / 低 |
| 状态 | Status | 待研究 / 待写稿 / 制作中 / 已发布 / 搁置 |
| 一句话观点 | Text | 这一条最短的核心表达 |
| 开头钩子 | Text | 前 3 秒钩子 |
| 目标受众 | Multi-select | 职场人 / 创作者 / 创业者 / 开发者 |
| 预估时长 | Number | 建议写秒数，例如 60 |
| 参考章节 | Text | 对应书中章节或相关摘录 |
| 关联视频 | Relation -> 视频台账 | 这个主题最终做成了哪条视频 |
| 备注 | Text | 补充思路 |

### 推荐视图

- `看板-按状态`
- `列表-高优先级`
- `表格-按核心原则分组`

## 2. 视频台账

这个库负责管理“已经开始做的具体视频项目”。

每条视频页面正文必须固定包含五个生产文档章节：

1. `Content Material Card`
2. `Content Review`
3. `Brief`
4. `Script Lab`
5. `Script`
6. `Scene Contract`
7. `Visual Component Map`
8. `Shot List`
9. `Assembly Check`

本地对应文件为：

- `content-material-card.md`
- `content-review.md`
- `brief.md`
- `script-lab.md`
- `script.md`
- `scene-contract.json`
- `visual-component-map.md`
- `shot-list.md`
- `assembly-check.md`

进入配音和画面制作前，必须先把这些生产文档同步到对应 `视频台账` 页面。成片迭代后，如果文档发生变化，也必须重新同步。

### 建议字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 视频标题 | Title | 例如：纳瓦尔宝典-杠杆 |
| 系列 | Select | Naval Almanack |
| 主题 | Relation -> 选题库 | 对应哪个选题 |
| 状态 | Status | 文案中 / 配音中 / 渲染中 / 待发布 / 已发布 |
| 项目目录 | URL 或 Text | 本地项目绝对路径 |
| 成片路径 | URL 或 Text | 最终 mp4 路径 |
| 无声版路径 | URL 或 Text | visual 版路径 |
| 配音版本 | Select | Yunxi / Xiaoxiao / 真人 / 其他 |
| 字幕文件 | URL 或 Text | `.vtt` 路径 |
| 时长 | Number | 秒 |
| 封面状态 | Select | 未做 / 已做 |
| 发布时间 | Date | 实际发布时间 |
| 发布平台 | Multi-select | 抖音 / 视频号 / 小红书 / B站 |
| 评审状态 | Select | 未评审 / 已评审 / 已修改 / 通过 |
| 评审评分 | Number | 1-10 分 |
| 最大亮点 | Text | 这一版最值得保留的点 |
| 主要问题 | Text | 影响质量的关键问题 |
| 必改建议 | Text | 最多 3 条必改项 |
| 下一版修改指令 | Text | 可直接交给生成流程执行的修改指令 |
| 复审结论 | Text | 修改后是否通过 |
| 评审日期 | Date | 最近一次评审日期 |
| 负责人 | Person 或 Text | 默认写你自己 |
| 最近更新 | Date | 方便排序 |
| 备注 | Text | 当前问题、下一步 |

### 推荐视图

- `看板-按制作状态`
- `表格-按最近更新排序`
- `日历-按发布时间`
- `列表-待发布`
- `表格-待评审`

### 视频评审官

建议把评审作为固定工序，放在第一版成片之后、发布之前。

评审角色不是泛泛夸或吐槽，而是同时扮演：

- 短视频导演
- 目标观众
- 内容编辑

每次评审输出：

- `总体评分`
- `最大亮点`
- `主要问题`
- `必改建议`
- `可选优化`
- `下一版修改指令`

通过标准：默认 9 分以上可以进入待发布；低于 9 分至少做一轮修改。若音频技术检查未通过，即使总分够高，也优先改配音或口播停顿。主观听感未实际听审时标记为 `pending`，不作为系统自动阻塞项。

## 3. 素材引用库

这个库负责沉淀内容燃料，避免每次重新找观点、金句和案例。

### 建议字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 素材标题 | Title | 例如：AI 时代，通用技能先变便宜 |
| 类型 | Select | 纳瓦尔原文 / 金句 / 案例 / 反例 / 观众问题 / 行业现象 |
| 核心原则 | Select | 长期主义 / 杠杆 / 具体知识 / 判断力 / 幸福 等 |
| 原文摘录 | Text | 原文或系列改编表达 |
| 出处 | Text | 书、文章、评论、当前视频迭代等 |
| 可改编角度 | Text | 这条素材可以怎么转成视频判断 |
| 适合选题 | Text | 适合延展成哪些主题 |
| 使用状态 | Select | 未使用 / 已入选题 / 已制作 / 暂缓 |
| 优先级 | Select | 高 / 中 / 低 |
| 关联视频 | Relation -> 视频台账 | 已经在哪些视频里使用 |
| 备注 | Text | 版本、来源、注意事项 |

### 推荐视图

- `按原则素材`
- `表格-全部素材`
- `高优先级素材`

## 4. 发布复盘库

这个库负责管理“发完之后学到了什么”。

### 建议字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 复盘标题 | Title | 例如：杠杆这条为什么完播更高 |
| 视频 | Relation -> 视频台账 | 对应哪条视频 |
| 发布时间 | Date | 手填实际发布时间 |
| 平台 | Select | 抖音 / 视频号 / 小红书 / B站 |
| 播放量 | Number | 可选 |
| 完播率 | Number | 可选 |
| 点赞率 | Number | 可选 |
| 收藏率 | Number | 可选 |
| 评论数 | Number | 可选 |
| 高价值评论 | Text | 值得保留的评论、疑问、反驳 |
| 评论关键词 | Multi-select | 钩子强 / 封面强 / 配音问题 / 节奏慢 / 内容共鸣 / 争议点 |
| 表现判断 | Select | 爆款潜力 / 正常 / 需重做钩子 / 需重做内容 |
| 下一步动作 | Text | 下一次怎么改 |
| 是否生成新选题 | Checkbox | 是否从评论或数据反推新选题 |

### 推荐视图

- `按状态复盘`
- `表格-全部复盘`
- `按平台筛选`

## 数据库关系建议

关系尽量保持简单：

- `选题库` 1 对多 `视频台账`
- `视频台账` 1 对多 `发布复盘库`
- `素材引用库` 多对多 `视频台账`

这样能回答几个关键问题：

- 哪些选题已经做了，哪些还没做
- 每条视频对应的工程目录和最终成片在哪
- 哪类素材被反复复用
- 哪种主题和钩子效果最好

## 推荐状态流

建议把 `视频台账` 的状态统一成下面这组：

1. `待立项`
2. `写文案`
3. `做画面`
4. `生成配音`
5. `渲染导出`
6. `待发布`
7. `已发布`
8. `待复盘`
9. `已归档`

这样你在 `Notion` 看板里一眼就能知道每条卡在哪一步。

## 多 Agent 协作关系

建议用“主编总控 + 专业 Agent”的轻量模式：

| Agent | Notion 落点 | 本地落点 |
| --- | --- | --- |
| 选题研究 Agent | `选题库`、视频页面 `Content Review` | `content-review.md` |
| 内容主编 Agent | 视频页面 `Brief` | `brief.md` |
| 脚本 Agent | 视频页面 `Script Lab`、`Script`、`Scene Contract` | `script-lab.md`、`script.md`、`voice/narration.txt`、`scene-contract.json` |
| 视觉导演 Agent | 视频页面 `Visual Component Map`、`Shot List` | `visual-component-map.md`、`shot-list.md`、`hyperframes/content.js` |
| 配音导演 Agent | `视频台账` 配音字段建议 | `voice/`、`voice/voice-manifest.json` |
| 装配剪辑 Agent | 视频页面 `Assembly Check` | `assembly-check.md` |
| 视频评审 Agent | `视频台账` 评审字段 | `review.md` |
| 发布复盘 Agent | `发布复盘库`、`素材引用库` | 发布后记录 |
| 主编总控 G5 | `视频台账`、视频页面、`选题库`、`发布复盘库` | `quality-check.md`、`notion-sync-receipt.md` |
| 主编总控 G6 | `Agent 角色库`、`多 Agent 协作 SOP` | `agent-retrospective.md` |

每次 Agent 完成阶段性工作，都应该在本地 `agent-handoffs/` 目录保存一份交接记录。

`quality-check.md` 和 Notion 同步状态只由主编总控写入。其他 Agent 不判断“已同步”或“已过闸”，只在 handoff 里提交状态建议。

每条视频完成后固定进入 G6：主编总控基于所有交接记录和评审结果生成 `agent-retrospective.md`。如果发现高确定性、可复用、能提升后续质量或降低返工的改进点，再更新 Agent 定义或 SOP；如果没有发现，就明确记录“本轮无高确定性迭代项”，不为了形式感强行修改。

## 本地目录与 Notion 的对应关系

建议统一约定：

- `项目目录` 字段：指向 `episodes/某条视频`
- `成片路径` 字段：指向 `exports/naval-template-final.mp4` 或具体成片名
- `字幕文件` 字段：指向 `subtitles/*.vtt`
- `配音版本` 字段：只记录最终采用的声音

也就是说，`Notion` 不代替文件系统，它只做索引。

## 最小可用版本

如果你不想一开始建太多库，先建这 2 个就够用：

1. `选题库`
2. `视频台账`

等你发出 5-10 条以后，再补 `素材库` 和 `复盘库`。

## 当前系列建议先录入的两条

先把这两条录进去：

- `2026-05-16-纳瓦尔宝典-长期主义复利原则`
- `2026-05-17-纳瓦尔宝典-杠杆`

对应本地目录都在：

`/Users/chendingyu/my_project/video/series/naval-almanack/episodes/`
