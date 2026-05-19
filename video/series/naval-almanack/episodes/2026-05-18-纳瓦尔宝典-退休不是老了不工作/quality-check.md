# 质量闸口检查

这份文件用于判断本条视频能不能进入下一阶段。没有过闸口，不要用“先做出来看看”绕过去。

## G0 选题闸口

- [x] 已引用 `../../content-system/content-material-library.md` 或填写 `content-material-card.md`
- [x] 原料卡包含当下焦虑、默认误判、案例种子和行动落点
- [x] 内容评分 >= 9.0
- [x] 反常识程度为高
- [x] 痛点强度为高
- [x] 案例清晰度为高
- [x] 观点锋利度为高
- [x] Notion `是否进入制作` 已勾选

结论：通过。01 选题研究 Agent 评分 9.1 / 10，四项核心维度均为高。本轮已补齐 `content-material-card.md`，将 M-RETIRE-001 作为主原料卡，M-TIME-BOUNDARY-001 作为辅助原料卡。

## G1 文案闸口

- [x] 已完成 `script-lab.md`
- [x] `script-lab.md` 完成 5 个钩子、3 个案例角度、2 个反驳桥和 3 句记忆句实验
- [x] `script-lab.md` 总分 >= 90 / 100
- [x] 前 3 秒有现实冲突
- [x] 只讲一个核心判断
- [x] 有 3 个开头钩子备选，并说明最终选择理由
- [x] 有 `核心判断`、`观众旧判断 -> 新判断`、`情绪落点` 和 `不讲什么`
- [x] 有清晰叙事骨架：hook、reframe、proof、diagnosis、action、memory line
- [x] 有具体人物、场景和选择
- [x] 有七天内可执行的行动
- [x] 有一句能被转述的记忆句
- [x] 逐句口播读起来像真人说话，不像书面文章
- [x] 已完成逐句连续性自检
- [x] 已完成口语自然度自检
- [x] 已生成 `scene-contract.json`
- [x] `scene-contract.json` 包含 `scene_energy`、`retention_goal`、`viewer_state_before`、`viewer_state_after`、`continuity_notes`
- [x] 脚本自评分 >= 90 / 100，且没有红线问题

结论：通过。`script-lab.md` 实验评分 97 / 100，最终选择反误判型钩子和阿宁 + 时间账单对照结构。03 脚本 Agent 自评分 96 / 100；主编复核确认 `scene-contract.json` v1.2 合法、6 个 scene 合计 100 秒、44 句口播，`voice/narration.txt` 与 scene 口播完全一致。

## G2 配音闸口

- [x] 已生成 30 秒试音
- [x] 已写入 `voice/voice-manifest.json`
- [x] 已核对 `scene-contract.json` 与 `voice/narration.txt` 一致
- [x] `technical_audio_pass` 为通过
- [x] `audio_subjective_review` 已标记为 `confirmed` 或 `pending`
- [x] 关键句前后有停顿
- [x] 没有明显新闻腔、带货腔、短剧腔
- [x] 未实际听音频时，没有把真实感预估写成已确认听感

试音结论：通过技术 G2。逐句试音 `voice/narration-yunxi-trial.mp3` 暴露停顿叠加导致偏长；scene 分段 v1 `112.240s` 超过 110s 硬线已弃用；最终采用 v2 `voice/narration-yunxi-scene-v2.mp3`，Yunxi `+18%`，时长 `100.788s`，mp3 / 24000 Hz / mono。`technical_audio_pass: pass`，`audio_subjective_review: pending`，发布前人工看听重点关注第 39 句是否连读。

## G3 画面闸口

- [x] 已完成 `visual-component-map.md`
- [x] 每个 scene 已选择主组件，且至少 3 个组件来自视觉组件库
- [x] 至少 1 个组件承载案例场景，不是纯抽象卡片
- [x] 已基于 `scene-contract.json` 写 `shot-list.md`
- [x] 每个 scene 的主信息只有 1 个
- [x] 数字证据同屏不超过 3 组重点
- [x] handoff 已标注制作成本：低 / 中 / 高
- [x] `npx hyperframes lint` 0 errors / 0 warnings
- [x] `npx hyperframes inspect` 0 layout issues
- [x] 已抽帧检查开头、原则、案例、结尾
- [x] 没有难看的标题断行
- [x] 字幕没有遮挡主体
- [x] 画面不是纯文字 PPT

抽帧记录：视觉 Agent 已完成 `visual-component-map.md`、`shot-list.md` 与 `hyperframes/content.js`。本条采用 C-COVER-CONTRAST、C-BEFORE-AFTER、C-CALENDAR-DEBT、C-MESSAGE-PRESSURE、C-TIME-BILL、C-CHOICE-LOCK、C-DIAGNOSIS-STAMP、C-AUDIT-CARD、C-MEMORY-LINE 等组件，S03/S04 承载案例场景。主编总控修正 `index.html` 旧模板硬编码后复跑 `npx hyperframes lint .` 为 0 errors / 0 warnings，`npx hyperframes inspect . --samples 15 --at 1.8,16,35,61.5,84.5,96.8` 为 0 layout issues。

## G3.5 样片与装配闸口

- [x] 已产出 15-30 秒样片，或完成等价片段抽检
- [x] 已生成 `assembly-check.md`
- [x] 已检查每个 scene 的切点、落字、停顿、转场、BGM ducking 风险
- [x] 已确认 `scene_energy` 和最终画面/配音节奏一致
- [x] 已标出“脚本没问题、视觉没问题、配音没问题，但拼在一起不顺”的风险

装配结论：条件通过。08 装配剪辑 Agent 初检发现 S02 原则卡旧模板残留；主编局部修正并重渲染后，08 Agent 二次复核确认旧残留解除、lint / inspect / ffprobe 正常、S06 行动卡不挤。剩余 pending 项只有发布前人工听审第 39 句和关键转场听感。

## G4 成片闸口

- [x] ffprobe 确认 1080x1920
- [x] 音画时长匹配
- [x] 视频评审评分 >= 9.0
- [x] review 已分为结构审和成片审
- [x] `technical_audio_pass` 为通过
- [x] 如果没有实际听音频，`audio_subjective_review` 标记为 `pending`
- [x] 必改建议已处理
- [x] 复审通过

复审结论：条件通过。06 视频评审 Agent 独立评分 9.0 / 10，确认结构、视觉、字幕和技术参数达标；无新的结构、视觉或技术必改项。`audio_subjective_review` 保持 `pending`，发布前必须人工完整看听，重点确认第 39 句、记忆句落点和 S04->S05、S05->S06、action->outro 转场听感。

## G5 发布闸口

- [x] 最终成片已归档
- [x] 无声版已归档
- [x] 字幕文件已归档
- [x] 配音文件已归档
- [x] 封面已独立制作
- [x] 发布标题已确定
- [x] 发布文案和标签已完成
- [x] Notion 视频台账已更新
- [x] Notion 视频页面已同步 `content-material-card.md`、`content-review.md`、`brief.md`、`script-lab.md`、`script.md`、`scene-contract.json`、`visual-component-map.md`、`shot-list.md`、`assembly-check.md`
- [x] 已生成 `notion-sync-receipt.md`
- [x] 发布前人工完整看听一遍已保留在发布清单中

发布结论：G5 主流程已完成。本轮系统升级后已补齐本地 `content-material-card.md`、`script-lab.md`、`visual-component-map.md`，并已追加同步到本条 Notion 视频页面和 `notion-sync-receipt.md`。

## Agent 交接记录

- [x] 选题研究 Agent 已交接
- [x] 内容主编 Agent 已交接
- [x] 脚本 Agent 已交接
- [x] 视觉导演 Agent 已交接
- [x] 配音导演 Agent 已交接
- [x] 装配剪辑 Agent 已交接
- [x] 视频评审 Agent 已交接
- [x] 发布复盘 Agent 已创建待复盘记录
- [x] 不再需要的子 Agent 已关闭，保留项已说明原因

交接记录目录：`agent-handoffs/`

## G6 Agent 复盘与自动迭代闸口

- [x] 已生成 `agent-retrospective.md`
- [x] 已覆盖各 Agent 的输入、输出、评分、问题和下一轮建议
- [x] 已明确“需要修改”或“无需修改”
- [x] 如果修改了 Agent 定义或 SOP，已同步到 Notion
- [x] 已记录未修改项：除角色文件口径外，其余 Agent 定义保持现有定义

G6 结论：通过。本轮发现两个可复用流程问题：发布复盘 Agent 的调度提示曾引用不存在的角色文件名；界面残留的 `Pauli` 后台任务暴露出缺少 `agent_id` 台账。已更新 `multi-agent-sop.md`、`agent-roles/README.md`、`bin/new-naval-video.sh`，新增 `agent-registry.md` 模板和本项目台账，并同步到 Notion。其余 Agent 定义无需强行修改。
