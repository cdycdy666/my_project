# 质量闸口检查

这份文件只由主编总控维护，用于判断本条视频能不能进入下一阶段。没有过闸口，不要用“先做出来看看”绕过去。

## G0 工具选题闸口

- [x] `source-manifest.json` 和 `course-source-index.md` 已更新
- [x] 已选择 1 个主课程源，问答或特别放送只作为辅助源
- [x] 已引用 `../../content-system/content-material-library.md` 或填写 `content-material-card.md`
- [x] 原料卡包含工具、真实场景、默认误判、错误用法和第一步动作
- [x] 已完成从课程源到原创工具卡的二次转化，未直接搬运课程原文
- [x] 内容评分 >= 9.0
- [x] 场景真实强度为高
- [x] 工具一句话清晰
- [x] 案例清晰度为高
- [x] 行动可执行性为高
- [x] Notion 草稿索引页已创建

结论：G0 通过；Notion 已创建草稿索引页，完整 G5 同步待发布包装完成。

## G1 文案闸口

- [x] 已完成 `script-lab.md`
- [x] `script-lab.md` 完成 5 个钩子、3 个案例角度、2 个错误用法和 3 句记忆句实验
- [x] `script-lab.md` 总分 >= 90 / 100
- [x] 前 3 秒有真实困境或明确误判
- [x] 只讲一个思维工具
- [x] 有 `工具一句话`、`观众旧判断 -> 新判断`、`错误用法` 和 `本周动作`
- [x] 有清晰叙事骨架：hook、tool、wrong use、demo、action、memory line
- [x] 有具体人物、场景、动作和代价
- [x] 有七天内可执行的行动
- [x] 有一句能被转述的记忆句
- [x] 逐句口播读起来像真人说话，不像课程讲义
- [x] 已完成逐句连续性自检
- [x] 已生成 `scene-contract.json`
- [x] `scene-contract.json` 包含 `scene_energy`、`retention_goal`、`viewer_state_before`、`viewer_state_after`、`tool_step`、`wrong_use`
- [x] 脚本自评分 >= 90 / 100，且没有红线问题
- [x] 独立脚本审查已完成，必改项已处理

结论：G1 通过。独立脚本审查评分 91 / 100，已修复 `scene-contract.json` 对齐问题和“三问 / 三栏 / 4步”混用。

## G2 配音闸口

- [x] 已生成 30 秒以内短试音
- [x] 已写入 `voice/voice-manifest.json`
- [x] 已核对 `scene-contract.json` 与 `voice/narration.txt` 一致
- [x] `technical_audio_pass` 为通过
- [x] `audio_subjective_review` 已标记为 `confirmed` 或 `pending`
- [x] 关键句前后有停顿要求
- [x] 没有明显新闻腔、带货腔、短剧腔要求
- [x] 未实际听音频时，没有把真实感预估写成已确认听感

试音结论：短文本 Yunxi 可用；完整旁白已使用本地 Kokoro ONNX `zm_yunxi` 生成，未导出完整脚本到外部 TTS。技术音频通过，人耳听审 pending。

## G3 画面闸口

- [x] 已完成 `visual-component-map.md`
- [x] 每个 scene 已选择主组件，且至少 3 个组件来自视觉组件库
- [x] 至少 1 个组件演示工具步骤，不是纯抽象卡片
- [x] 已基于 `scene-contract.json` 写 `shot-list.md`
- [x] 每个 scene 的主信息只有 1 个
- [x] 工具步骤有动作或视觉隐喻承接
- [x] handoff 已标注制作成本：低 / 中 / 高
- [x] `npx hyperframes lint` 0 errors
- [ ] `npx hyperframes lint` 0 warnings
- [x] `npx hyperframes inspect` 0 layout issues
- [x] `hyperframes/content.js` 和 `hyperframes/index.html` 无旧主题残留文案
- [x] 已抽帧检查开头、工具卡、案例、行动卡、结尾
- [x] 没有难看的标题断行
- [x] 字幕没有遮挡主体
- [x] 画面不是纯文字 PPT

抽帧记录：`hyperframes inspect --samples 18` 为 0 layout issues；独立装配/视觉审查认为 G3 通过，评分 82 / 100。

维护性说明：`composition_file_too_large` 为源码维护 warning，不影响本轮画面，但下一轮建议拆分组件。

## G3.5 样片与装配闸口

- [x] 已产出 15-30 秒样片，或完成等价片段抽检
- [x] 已生成 `assembly-check.md`
- [x] 已检查每个 scene 的切点、落字、停顿、转场、BGM ducking 风险
- [x] 已确认 `scene_energy` 和最终画面节奏一致
- [x] 已标出“脚本没问题、视觉没问题、配音没问题，但拼在一起不顺”的风险
- [x] 已确认正式配音和视觉节奏一致
- [x] 已生成 `preview/contact-sheet-final.jpg` 和 `preview/ffprobe-final.json`
- [ ] 尾 15 秒没有低信息空背景

装配结论：技术装配通过；人工完整看听 pending；发布前需处理尾段低信息空背景。

## G4 成片闸口

- [x] ffprobe 确认 1080x1920
- [x] 音画时长匹配
- [ ] 视频评审评分 >= 9.0
- [x] 已检查最终版联系表
- [x] review 已分为结构审和成片审
- [x] `technical_audio_pass` 为通过
- [x] 如果没有实际听音频，`audio_subjective_review` 标记为 `pending`
- [x] 已处理本轮结构/视觉必改建议
- [ ] 发布前人工复审通过

复审结论：技术成片通过；发布前仍需人工完整看听、封面、发布包装，并修复尾段低信息空背景。

## G5 发布闸口

- [x] 最终成片已归档
- [x] 无声版已归档
- [ ] 字幕文件已归档
- [x] 配音文件已归档
- [ ] 封面已独立制作
- [ ] 发布标题已确定
- [ ] 发布文案和标签已完成
- [x] Notion 草稿索引页已创建
- [ ] Notion 视频页面已同步 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`、`assembly-check.md`
- [x] 已生成 `notion-sync-receipt.md`
- [x] 发布前人工完整看听一遍已保留在发布清单中

发布结论：G5 pending。

## Agent 交接记录

- [x] 工具研究 Agent 已交接
- [x] 内容主编 Agent 已交接
- [x] 脚本 Agent 已交接
- [x] 视觉导演 Agent 已交接
- [x] 配音导演 Agent 已交接
- [x] 装配剪辑 Agent 已交接
- [x] 视频评审 Agent 已交接
- [ ] 发布复盘 Agent 已创建待复盘记录
- [x] 不再需要的子 Agent 已关闭，保留项已说明原因

交接记录目录：`agent-handoffs/`

## G6 Agent 复盘与自动迭代闸口

- [x] 已生成 `agent-retrospective.md`
- [x] 已覆盖各 Agent 的输入、输出、评分、问题和下一轮建议
- [x] 已明确“需要修改”或“无需修改”
- [ ] 如果修改了 Agent 定义或 SOP，已同步到 Notion
