# 《实用思维工具》多 Agent SOP

## 角色

| 角色 | 文件 | 主要责任 | 主输出 |
| --- | --- | --- | --- |
| 主编总控 | `agent-roles/00-orchestrator.md` | 串联流程、维护质量闸口、管理 Notion 状态 | `quality-check.md`、`notion-sync-receipt.md` |
| 工具研究 Agent | `agent-roles/01-topic-researcher.md` | 选择工具、验证场景、定义误用风险 | `content-review.md`、`content-material-card.md` |
| 内容主编 Agent | `agent-roles/02-content-editor.md` | 把工具变成观众问题和单集判断 | `brief.md` |
| 脚本 Agent | `agent-roles/03-scriptwriter.md` | 设计钩子、案例、步骤和记忆句 | `script-lab.md`、`script.md`、`scene-contract.json` |
| 视觉导演 Agent | `agent-roles/04-visual-director.md` | 把工具步骤变成可视化组件 | `visual-component-map.md`、`shot-list.md` |
| 配音导演 Agent | `agent-roles/05-voice-director.md` | 检查口播和音频技术状态 | `voice/voice-manifest.json` |
| 视频评审 Agent | `agent-roles/06-video-reviewer.md` | 评审结构、成片和发布可用性 | `review.md` |
| 发布复盘 Agent | `agent-roles/07-publishing-analyst.md` | 把发布反馈回流到选题和工具库 | `publish-retrospective.md` |
| 装配剪辑 Agent | `agent-roles/08-assembly-editor.md` | 检查音画字幕和节奏装配 | `assembly-check.md` |

## 标准流程

0. 主编总控确认 `source-manifest.json` 和 `course-source-index.md` 已是最新。
1. 主编总控创建 episode 目录和 `agent-registry.md`
2. 工具研究 Agent 从课程源索引选择正课源，必要时读取 PDF 抽取工具卡
3. 工具研究 Agent 从内容原料库选工具卡，必要时补卡
4. 工具研究 Agent 写 `content-review.md`
5. 内容主编 Agent 写 `brief.md`
6. 脚本 Agent 先写 `script-lab.md`
7. 脚本 Agent 再写 `script.md`、`voice/narration.txt`、`scene-contract.json`
8. 主编总控检查 G1，通过后视觉和配音才进入制作
9. 视觉导演 Agent 先写 `visual-component-map.md`
10. 视觉导演 Agent 再写 `shot-list.md` 和 `hyperframes/content.js`
11. 配音导演 Agent 生成试音策略和 `voice/voice-manifest.json`
12. 主编总控跑 lint / inspect / render / ffprobe，并生成 `preview/contact-sheet-visual.jpg`
13. 有声封装后生成 `preview/contact-sheet-final.jpg` 和 `preview/ffprobe-final.json`
14. 装配剪辑 Agent 写 `assembly-check.md`，必须检查联系表、首 5 秒、尾 15 秒和低信息空帧
15. 视频评审 Agent 写 `review.md`，必须区分“技术成片可看”和“发布成片可发”
16. 如果 G4 未达到发布分，进入一次“发布前打磨回路”：只修必改项，不重开选题
17. 主编总控完成封面、标题、文案、标签和 `notion-sync-receipt.md`
18. 发布复盘 Agent 写 `publish-retrospective.md`
19. 主编总控写 `agent-retrospective.md`，并关闭不再需要的 Agent

## 并行边界

- `brief.md` 通过前，不写最终脚本和最终分镜。
- `script-lab.md` 通过前，不写最终 `script.md`。
- `scene-contract.json` 通过后，视觉和配音可以并行。
- `visual-component-map.md` 完成前，不写最终 `shot-list.md`。
- `assembly-check.md` 通过前，不进入最终评审。
- `review.md` 发布可用性低于 9.0 时，只允许标记“技术成片完成”，不能标记“发布完成”。

## 成片状态分层

- `draft-cut`：画面或音频其中一项未完成，只能内部看方向。
- `technical-cut`：音画封装、布局、时长、音轨都通过，但人耳听审、封面、标题或发布文案仍可 pending。
- `publish-cut`：综合评分 >= 9.0，必改项清零，发布包装完成，且发布前人工完整看听已完成。

如果只达到 `technical-cut`，`quality-check.md` 的 G4 可以写“技术通过”，但 G5 必须保持 pending。

## 状态所有权

- `quality-check.md` 只由主编总控写。
- Notion 同步状态只看 `notion-sync-receipt.md`。
- 其他 Agent 只在 handoff 中提交状态建议。
- 每个不再需要的 Agent 必须关闭，并记录到 `agent-registry.md`。

## 工具类视频特殊要求

- 课程源只能作为原料，不把课程原文直接压缩成短视频。
- 每条视频必须包含“错误用法”或“常见误解”。
- 每条视频必须给出一个可以当周执行的动作。
- 工具不能只被解释，必须被演示。
- 观众看完后应该能说出：“下次遇到 X，我先做 Y。”
- 成片结尾不能长时间只剩氛围背景；尾 15 秒必须保留记忆句、行动问题或评论引导之一。
