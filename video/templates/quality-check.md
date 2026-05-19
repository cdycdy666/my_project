# 质量闸口检查

这份文件用于判断本条视频能不能进入下一阶段。没有过闸口，不要用“先做出来看看”绕过去。

## G0 选题闸口

- [ ] 已引用 `../../content-system/content-material-library.md` 或填写 `content-material-card.md`
- [ ] 原料卡包含当下焦虑、默认误判、案例种子和行动落点
- [ ] 内容评分 >= 9.0
- [ ] 反常识程度为高
- [ ] 痛点强度为高
- [ ] 案例清晰度为高
- [ ] 观点锋利度为高
- [ ] Notion `是否进入制作` 已勾选

结论：

## G1 文案闸口

- [ ] 已完成 `script-lab.md`
- [ ] `script-lab.md` 完成 5 个钩子、3 个案例角度、2 个反驳桥和 3 句记忆句实验
- [ ] `script-lab.md` 总分 >= 90 / 100
- [ ] 前 3 秒有现实冲突
- [ ] 只讲一个核心判断
- [ ] 有 3 个开头钩子备选，并说明最终选择理由
- [ ] 有 `核心判断`、`观众旧判断 -> 新判断`、`情绪落点` 和 `不讲什么`
- [ ] 有清晰叙事骨架：hook、reframe、proof、diagnosis、action、memory line
- [ ] 有具体人物、场景和选择
- [ ] 有七天内可执行的行动
- [ ] 有一句能被转述的记忆句
- [ ] 逐句口播读起来像真人说话，不像书面文章
- [ ] 已完成逐句连续性自检
- [ ] 已完成口语自然度自检
- [ ] 已生成 `scene-contract.json`
- [ ] `scene-contract.json` 包含 `scene_energy`、`retention_goal`、`viewer_state_before`、`viewer_state_after`、`continuity_notes`
- [ ] 脚本自评分 >= 90 / 100，且没有红线问题

结论：

## G2 配音闸口

- [ ] 已生成 30 秒试音
- [ ] 已写入 `voice/voice-manifest.json`
- [ ] 已核对 `scene-contract.json` 与 `voice/narration.txt` 一致
- [ ] `technical_audio_pass` 为通过
- [ ] `audio_subjective_review` 已标记为 `confirmed` 或 `pending`
- [ ] 关键句前后有停顿
- [ ] 没有明显新闻腔、带货腔、短剧腔
- [ ] 未实际听音频时，没有把真实感预估写成已确认听感

试音结论：

## G3 画面闸口

- [ ] 已完成 `visual-component-map.md`
- [ ] 每个 scene 已选择主组件，且至少 3 个组件来自视觉组件库
- [ ] 至少 1 个组件承载案例场景，不是纯抽象卡片
- [ ] 已基于 `scene-contract.json` 写 `shot-list.md`
- [ ] 每个 scene 的主信息只有 1 个
- [ ] 数字证据同屏不超过 3 组重点
- [ ] handoff 已标注制作成本：低 / 中 / 高
- [ ] `npx hyperframes lint` 0 errors / 0 warnings
- [ ] `npx hyperframes inspect` 0 layout issues
- [ ] `hyperframes/content.js` 和 `hyperframes/index.html` 无旧主题残留文案
- [ ] 已抽帧检查开头、原则、案例、结尾
- [ ] 没有难看的标题断行
- [ ] 字幕没有遮挡主体
- [ ] 画面不是纯文字 PPT

抽帧记录：

## G3.5 样片与装配闸口

- [ ] 已产出 15-30 秒样片，或完成等价片段抽检
- [ ] 已生成 `assembly-check.md`
- [ ] 已检查每个 scene 的切点、落字、停顿、转场、BGM ducking 风险
- [ ] 已确认 `scene_energy` 和最终画面/配音节奏一致
- [ ] 已标出“脚本没问题、视觉没问题、配音没问题，但拼在一起不顺”的风险

装配结论：

## G4 成片闸口

- [ ] ffprobe 确认 1080x1920
- [ ] 音画时长匹配
- [ ] 视频评审评分 >= 9.0
- [ ] review 已分为结构审和成片审
- [ ] `technical_audio_pass` 为通过
- [ ] 如果没有实际听音频，`audio_subjective_review` 标记为 `pending`
- [ ] 必改建议已处理
- [ ] 复审通过

复审结论：

## G5 发布闸口

- [ ] 最终成片已归档
- [ ] 无声版已归档
- [ ] 字幕文件已归档
- [ ] 配音文件已归档
- [ ] 封面已独立制作
- [ ] 发布标题已确定
- [ ] 发布文案和标签已完成
- [ ] Notion 视频台账已更新
- [ ] Notion 视频页面已同步 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`、`assembly-check.md`
- [ ] 已生成 `notion-sync-receipt.md`
- [ ] 发布前人工完整看听一遍已保留在发布清单中

发布结论：

## Agent 交接记录

- [ ] 选题研究 Agent 已交接
- [ ] 内容主编 Agent 已交接
- [ ] 脚本 Agent 已交接
- [ ] 视觉导演 Agent 已交接
- [ ] 配音导演 Agent 已交接
- [ ] 装配剪辑 Agent 已交接
- [ ] 视频评审 Agent 已交接
- [ ] 发布复盘 Agent 已创建待复盘记录
- [ ] 不再需要的子 Agent 已关闭，保留项已说明原因

交接记录目录：`agent-handoffs/`

## G6 Agent 复盘与自动迭代闸口

- [ ] 已生成 `agent-retrospective.md`
- [ ] 已覆盖各 Agent 的输入、输出、评分、问题和下一轮建议
- [ ] 已明确“需要修改”或“无需修改”
- [ ] 如果修改了 Agent 定义或 SOP，已同步到 Notion
- [ ] 如果没有修改，已记录“本轮无高确定性迭代项，保持现有定义”
