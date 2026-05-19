# Practical Thinking Tools Series

这个目录专门管理《实用思维工具》系列短视频。

## 系列定位

《实用思维工具》不是讲概念百科，也不是做鸡汤金句，而是把一个可执行的思维工具讲成 3-5 分钟的具体场景解决方案。

每条视频必须回答四个问题：

- 观众现在卡在什么具体问题上？
- 这个工具替他换掉哪个旧判断？
- 它在现实场景里怎么用？
- 今天或本周能做的最小动作是什么？

## 目录约定

```text
practical-thinking-tools
├── README.md
├── notion-setup.md
├── quality-standard.md
├── multi-agent-sop.md
├── content-system/
├── agent-roles/
├── review-template.md
├── assembly-check-template.md
├── scene-contract-template.json
├── notion-sync-receipt-template.md
├── series-backlog.md
├── episodes/
└── shared-assets/
```

## 工作方式

1. 先用 `content-system/source-ingestion-workflow.md` 接入课程源。
2. 从 `content-system/course-source-index.md` 选择正课源，问答只作为辅助。
3. 把课程源转成 `content-system/content-material-library.md` 里的工具卡。
4. 新建一条：`./bin/new-thinking-tool-video.sh 主题名`
5. 从工具卡补齐 `content-material-card.md`。
6. 过 G0 选题闸口：没有真实场景、没有可执行动作、内容评分低于 9.0 不制作。
7. 完成 `content-review.md` 和 `brief.md`。
8. 先做 `script-lab.md`，验证钩子、案例、误用风险、记忆句和留存任务。
9. 再写正式 `script.md`、`voice/narration.txt` 和 `scene-contract.json`。
10. 先做 `visual-component-map.md`，再写 `shot-list.md`。
11. 配音只确认 `technical_audio_pass`，未实际人耳听审时 `audio_subjective_review` 必须保持 pending。
12. 渲染后必须检查 `preview/contact-sheet-visual.jpg` 和 `preview/contact-sheet-final.jpg`。
13. 完成 `assembly-check.md` 后进入成片评审。
14. G4 只能确认 `technical-cut`；综合评分、发布包装和人工完整看听都通过后才是 `publish-cut`。
15. G5 由主编总控生成 `notion-sync-receipt.md`，其他 Agent 不写同步状态。
16. G6 写 `agent-retrospective.md`，没有高确定性改进点时只记录不强行改 SOP。

## 多 Agent 协作

- 角色定义见 [agent-roles](/Users/chendingyu/my_project/video/series/practical-thinking-tools/agent-roles)
- Notion 主页面: https://www.notion.so/36432f4915ee81339b41c298c2f0501a
- 课程源接入见 [source-ingestion-workflow.md](/Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/source-ingestion-workflow.md)
- 课程源索引见 [course-source-index.md](/Users/chendingyu/my_project/video/series/practical-thinking-tools/content-system/course-source-index.md)
- Obsidian vault: [obsidian-vault](/Users/chendingyu/my_project/video/series/practical-thinking-tools/obsidian-vault)
- Obsidian MOC: [MOC-现代思维工具100讲.md](/Users/chendingyu/my_project/video/series/practical-thinking-tools/obsidian-vault/99-moc/MOC-现代思维工具100讲.md)
- 主编总控维护 `quality-check.md` 和 Notion 同步状态
- 其他 Agent 只在 handoff 中提交状态建议
- 每条视频结束后必须核对 `agent-registry.md`，关闭不再需要的后台 Agent

## 系列风格

- 内容气质：清醒、具体、可操作，不炫概念。
- 视觉气质：工具箱、白板、决策台、标注系统，避免“抽象商业 PPT”。
- 口播气质：像一个靠谱教练在帮你拆问题，不像课堂讲定义。
- 结构偏好：冲突场景 -> 工具一句话 -> 错误用法 -> 正确步骤 -> 本周动作。

## 当前状态

- 系列骨架已创建。
- 共享了《纳瓦尔宝典》已经验证过的多 Agent 生产线。
- 内容系统、选题池和质量标准已为“思维工具”单独拆分。
- 已接入 `/Users/chendingyu/my_project/万维钢·现代思维工具100讲`，生成 55 条课程源索引。
- 已生成 Obsidian vault，完整保存 55 篇 PDF 抽取全文。
