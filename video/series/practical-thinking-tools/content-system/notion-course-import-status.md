# Notion 课程源库导入状态

## Notion 目标

- Database: 课程源库｜现代思维工具100讲
- URL: https://www.notion.so/c2bc08c80ef346f5b39be78ebc9e0e78
- Data source: `collection://9307c4ca-9c75-4aff-a851-fbf6b81394b1`

## 本地准备状态

- [x] 已扫描原始目录：`/Users/chendingyu/my_project/万维钢·现代思维工具100讲`
- [x] 已生成机器索引：`source-manifest.json`
- [x] 已生成人工索引：`course-source-index.md`
- [x] 已完整抽取 55 个 PDF 到 `extracted-lessons/`
- [x] 已生成抽取报告：`extracted-lessons/_extraction-report.json`
- [x] 已生成 Obsidian vault：`../obsidian-vault`
- [x] 已生成 Obsidian MOC：`../obsidian-vault/99-moc/MOC-现代思维工具100讲.md`
- [x] 已生成 Notion 轻量索引：`../obsidian-vault/notion-light-index.json`

## Notion 写入状态

- [x] 已创建课程源库数据库
- [x] 已将课程源库 schema 调整为轻量索引模式：摘要、状态、Obsidian 路径、Obsidian URI
- [x] 已验证写入前 5 条轻量索引记录
- [x] 55 条轻量索引记录全部写入
- [x] 55 条完整抽取文本不再写入 Notion，统一保存在 Obsidian vault
- [ ] 首批 P0 候选完成结构化整理

## 已写入 Notion 的元数据记录

- `MTT-001` ~ `MTT-055` 已全部写入 Notion 课程源库。
- 每条记录均包含：标题、Source ID、课程序号、类型、推荐用途、导入状态、页数、文本字数、音频状态、PDF/音频路径、优先级、视频候选标记、Obsidian 路径、Obsidian URI、摘要、全文存储位置。
- 完整正文仍以 Obsidian vault 为唯一正文存储，Notion 只作为索引、摘要、状态和链接层。

## 下一步

1. 对 P0 候选课进行结构化整理，提炼工具卡和视频角度。
2. 从 Notion 课程源库进入选题筛选，用 Obsidian 链接回查完整原文。
3. 新视频制作时，优先使用 `Priority = P0/P1` 且 `Video Candidate = Yes` 的课程源。

## 为什么分批

55 条轻量索引已按批次写入完成。后续如果追加新课程源，仍建议继续分批写入，便于校验 Obsidian 链接和 Notion 字段一致性。
