# Naval Almanack Series

这个目录专门管理《纳瓦尔宝典》系列短视频。

## 目录约定

```text
naval-almanack
├── README.md
├── notion-setup.md       # Notion 建库说明
├── quality-standard.md   # 系列质量标准和硬性闸口
├── multi-agent-sop.md    # 多 Agent 协作流程
├── content-system/       # 内容原料库、脚本实验室、视觉组件库
├── agent-roles/          # 每个 Agent 的职责、输入和输出
├── review-template.md    # 视频评审官模板
├── assembly-check-template.md
├── scene-contract-template.json
├── notion-sync-receipt-template.md
├── series-backlog.md     # 选题池、状态、备注
├── episodes/             # 每一条视频一个独立项目目录
└── shared-assets/        # 系列共用素材、封面元素、参考稿
```

## 工作方式

1. 新建一条
   `./bin/new-naval-video.sh 纳瓦尔宝典-主题`
2. 先从 `content-system/content-material-library.md` 选择原料卡，必要时补 `content-material-card.md`
3. 过 G0 选题闸口：没有合格原料卡或内容评分低于 9.0 不制作
4. 完成 `content-review.md` 和 `brief.md`
5. 先做 `script-lab.md`，验证钩子、案例、反驳、记忆句和留存，再写正式 `script.md`、`voice/narration.txt` 和 `scene-contract.json`
6. 先做 `visual-component-map.md`，再写 `shot-list.md`
7. 主编总控把生产文档同步到 Notion，其他 Agent 不写同步状态
8. 先做 30 秒配音试音，系统只确认 `technical_audio_pass`，主观听感未听时标记 pending
9. 基于 `scene-contract.json` 完成 `hyperframes/content.js` 和画面模板
10. 先出 15-30 秒样片或等价片段抽检，完成 `assembly-check.md`
11. 出无声版，并抽帧检查开头、原则、案例、结尾
12. 生成全片配音并封装最终版
13. 跑技术校验：lint、inspect、ffprobe
14. 用视频评审官模板评审，综合评分低于 9.0 不发布
15. 补齐封面、发布标题、发布文案，生成 `notion-sync-receipt.md` 后进入待发布
16. 生成 `agent-retrospective.md`，判断是否需要更新 Agent 定义或 SOP；没有高确定性改进点时，只记录不强行修改

## 多 Agent 协作

- 总流程见 [multi-agent-sop.md](/Users/chendingyu/my_project/video/series/naval-almanack/multi-agent-sop.md)
- 角色定义见 [agent-roles](/Users/chendingyu/my_project/video/series/naval-almanack/agent-roles)
- Notion SOP: https://www.notion.so/36332f4915ee81728144defb5ba1f2b6
- Notion Agent 角色库: https://www.notion.so/f51b4ba07ff64014844f8e46f6572d2f
- 新建视频时会自动创建 `agent-handoffs/` 目录，用来保存每个 Agent 的交接记录
- 主编总控负责最终裁决，其他 Agent 只对自己的交付物负责
- 每条视频结束后固定进入 G6 复盘：复盘一定做，系统修改只在确有必要时做
- `quality-check.md` 只由主编总控写，其他 Agent 通过 handoff 提出状态建议
- `08 装配剪辑 Agent` 负责 G3.5 样片与节奏装配，避免主编长期兜底剪辑体验

## 系统资产

- 内容原料库：[content-system/content-material-library.md](/Users/chendingyu/my_project/video/series/naval-almanack/content-system/content-material-library.md)
- 脚本实验室：[content-system/script-lab-system.md](/Users/chendingyu/my_project/video/series/naval-almanack/content-system/script-lab-system.md)
- 视觉组件库：[content-system/visual-component-library.md](/Users/chendingyu/my_project/video/series/naval-almanack/content-system/visual-component-library.md)
- Notion 内容原料库 v1：https://www.notion.so/36432f4915ee81c1af11d0276bce4a5b
- Notion 脚本实验室 v1：https://www.notion.so/36432f4915ee81a28024c4199a7078c1
- Notion 视觉组件库 v1：https://www.notion.so/36432f4915ee81578491f7afd5b9f48a

## 管理建议

- 本地目录管理工程文件和成片
- `Notion` 管理选题、进度、发布和复盘
- 建库说明见 [notion-setup.md](/Users/chendingyu/my_project/video/series/naval-almanack/notion-setup.md)
- 质量标准见 [quality-standard.md](/Users/chendingyu/my_project/video/series/naval-almanack/quality-standard.md)
- 多 Agent SOP 见 [multi-agent-sop.md](/Users/chendingyu/my_project/video/series/naval-almanack/multi-agent-sop.md)
- 评审标准见 [review-template.md](/Users/chendingyu/my_project/video/series/naval-almanack/review-template.md)
- 内容评审见 [content-review-template.md](/Users/chendingyu/my_project/video/series/naval-almanack/content-review-template.md)

## 生产文档同步规则

- 每条视频的 Notion `视频台账` 页面正文必须包含 `Content Material Card`、`Content Review`、`Brief`、`Script Lab`、`Script`、`Scene Contract`、`Visual Component Map`、`Shot List`、`Assembly Check` 九个章节。
- 本地生产文件仍然保留为工程落档：`content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`、`assembly-check.md`。
- 本地文档是制作源文件，Notion 页面是生产中枢；进入配音和画面制作前，必须先完成一次同步。
- 成片迭代后，如果生产文档有调整，必须重新同步到 Notion 页面。
- G5 必须生成 `notion-sync-receipt.md`，作为唯一同步回执。

## 当前已创建

- `2026-05-16-纳瓦尔宝典-长期主义复利原则`：v4 推荐发布版，9.1 / 10
- `2026-05-17-纳瓦尔宝典-杠杆`：v4 推荐发布版，9.1 / 10
- `2026-05-17-纳瓦尔宝典-具体知识`：v4 推荐发布版，9.2 / 10
- `2026-05-18-纳瓦尔宝典-学会销售学会构建`：v4 推荐发布版，9.1 / 10，多 Agent 全链路记录完成
- `2026-05-18-纳瓦尔宝典-退休不是老了不工作`：v1 推荐发布版，9.1 / 10，按最新 SOP 完成

## 当前系列资产

- 共 5 条视频，全部已进入当前质量线。
- 五条均已补齐最终成片、无声版、Yunxi 配音、字幕、独立封面、发布资产和评审记录。
- `shared-assets/render_series_cover.py` 是当前通用封面生成器，用于保持封面系统一致。
- Notion `视频台账` 和 `选题库` 已同步当前状态。
- Notion 已补齐 `发布复盘库` 和 `素材引用库`，用于发布后复盘和后续内容燃料沉淀。
- 多 Agent 角色定义已根据第四条视频实战复盘迭代，并同步到 Notion `Agent 角色库`。
- 2026-05-18 已新增内容原料库、脚本实验室和视觉组件库，并接入新建项目模板、SOP、质量标准、Notion 和最新退休视频样例。
