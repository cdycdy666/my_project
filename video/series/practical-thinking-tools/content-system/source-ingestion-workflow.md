# 课程源接入流程

## 目标

把 `/Users/chendingyu/my_project/万维钢·现代思维工具100讲` 变成《实用思维工具》系列的稳定上游，而不是每次临时翻 PDF。

这套流程只把课程内容作为原料，不把课程原文直接搬进短视频。每条视频都必须完成二次转化：工具卡、真实场景、错误用法、本周动作和原创口播。

## 当前源结构

- 来源目录：`/Users/chendingyu/my_project/万维钢·现代思维工具100讲`
- 文件形态：PDF + MP3
- 当前清点：55 个 PDF，54 个音频文件
- PDF 页数范围：约 9-22 页
- 抽取状态：PDF 可直接抽文本，适合作为主摄取来源
- 音频用途：用于必要时核对语气、节奏和补充信息，不作为第一摄取入口

## 四层结构

### L0 Raw Source

原始课程文件保持在原目录，不复制到视频系列目录。

职责：

- 保留 PDF 和 MP3 原始路径
- 不改名、不移动、不二次压缩
- 只读使用

### L1 Source Index

由脚本生成课程索引：

```bash
cd /Users/chendingyu/my_project/video
/Users/chendingyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./bin/index-thinking-tool-source.py \
  --source-dir /Users/chendingyu/my_project/万维钢·现代思维工具100讲 \
  --out-dir /Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system
```

输出：

- `content-system/source-manifest.json`
- `content-system/course-source-index.md`

索引只保存元数据，不保存课程全文。

### L1.5 Full Text Extraction

先把每讲 PDF 的完整抽取文本保存成本地 Markdown，作为 Obsidian vault 的上游：

```bash
cd /Users/chendingyu/my_project/video
/Users/chendingyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./bin/extract-thinking-tool-pdfs.py \
  --manifest /Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/source-manifest.json \
  --out-dir /Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/extracted-lessons
```

输出：

- `content-system/extracted-lessons/MTT-xxx-标题.md`
- `content-system/extracted-lessons/_extraction-report.json`

### L1.6 Obsidian Vault

完整正文统一进入 Obsidian，而不是写入 Notion：

```bash
cd /Users/chendingyu/my_project/video
/Users/chendingyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./bin/build-thinking-tool-obsidian-vault.py \
  --manifest /Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/source-manifest.json \
  --extraction-report /Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/extracted-lessons/_extraction-report.json \
  --vault-dir /Users/chendingyu/my_project/video/series/practical-thinking-tools/obsidian-vault \
  --vault-name "Practical Thinking Tools"
```

输出：

- `obsidian-vault/00-source-fulltext/`：55 篇完整课程笔记
- `obsidian-vault/99-moc/MOC-现代思维工具100讲.md`
- `obsidian-vault/_templates/`
- `obsidian-vault/notion-light-index.json`

### L1.7 Notion Course Source Database

Notion 课程源库：

- URL: https://www.notion.so/c2bc08c80ef346f5b39be78ebc9e0e78
- Data source: `collection://9307c4ca-9c75-4aff-a851-fbf6b81394b1`

数据库属性负责检索和生产状态；Notion 不保存完整正文，只保存摘要、状态、Obsidian 路径和 Obsidian URI。

### L2 Tool Card Bank

从正课中提炼可复用工具卡，写入：

- `content-system/content-material-library.md`

每张工具卡必须包含：

- 工具名
- 一句话解释
- 最适合的视频场景
- 观众默认误判
- 常见错误用法
- 当周最小动作
- 视觉隐喻
- 来源 ID

问答和特别放送优先作为补充材料，用来增强反驳、误用风险和观众疑问。

### L3 Episode Production

每条视频只引用 1 个主工具卡，最多 1 个辅助源。

进入视频制作前，必须完成：

- `content-material-card.md`
- `content-review.md`
- `brief.md`
- `script-lab.md`

再进入正式脚本、视觉、配音和评审。

## 推荐 Agent 分工

- 01 工具研究 Agent：读取 `source-manifest.json` 和课程 PDF，产出工具卡与 `content-review.md`
- 02 内容主编 Agent：把工具转成单集判断和现实场景
- 03 脚本 Agent：禁止复述课程，必须做原创视频化改写
- 06 视频评审 Agent：检查是否过度搬运原文，是否真的可执行

## 入库优先级

优先选择具备以下特征的课程：

- 名称本身就是工具或模型
- 能解释一个高频现实问题
- 能给出三步以内的使用动作
- 容易可视化
- 不需要大量背景知识

第一批建议优先：

- `13 WOOP：从生活的默认设置中觉醒`
- `15 认知解耦：三步调节负面情绪`
- `20 探索与利用：怎样继续做个年轻人`
- `25 贝叶斯先验：判断是主观的，但可以更科学一点`
- `26 信息价值：怎样区分沙子和金子`
- `31 状态杠杆：你不是不努力，你是没做在点子上`
- `36 超级预测：给不确定性命名，给自己打分`
- `37 OODA 环：不是反应快，而是换脑快`
- `38 认知负荷理论：因为文具多，所以是差生`
- `39 ICAP 框架：最高效的学习方法`

## 质量红线

- 不把完整课程原文塞进 Notion 正文；完整内容以 Obsidian 为准。
- 不直接照搬课程标题当视频标题。
- 不直接摘录大段课程原文。
- 不把 10 分钟课程压缩成 90 秒摘要。
- 不做“万维钢说”式背书视频。
- 必须转化为“观众遇到 X 时，可以先做 Y”的实用工具视频。

## 已知清洗问题

- 第 07 讲 PDF 和 MP3 文件名存在空格差异，索引脚本会自动归并。
- 文件名中部分带有防断更水印，索引脚本会自动清洗。
- 正课、问答和特别放送会分类型标记，避免问答被误当主选题。
