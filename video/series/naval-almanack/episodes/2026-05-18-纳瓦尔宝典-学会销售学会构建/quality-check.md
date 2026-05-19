# 质量闸口检查

这份文件用于判断本条视频能不能进入下一阶段。没有过闸口，不要用“先做出来看看”绕过去。

G6 规则更新：`quality-check.md` 是主编总控专属汇总文件。其他 Agent 只提交 handoff 或独立评估，状态变更由主编写入本文件。

## G0 选题闸口

- [x] 内容评分 >= 9.0
- [x] 反常识程度为高
- [x] 痛点强度为高
- [x] 案例清晰度为高
- [x] 观点锋利度为高
- [x] Notion `是否进入制作` 已勾选

结论：通过。`content-review.md` 评分 9.1 / 10，反常识程度、痛点强度、案例清晰度、观点锋利度均为高；Notion 选题库已更新并保持 `是否进入制作` 为是。

## G1 文案闸口

- [x] 前 3 秒有现实冲突
- [x] 只讲一个核心判断
- [x] 有具体人物、场景和选择
- [x] 有七天内可执行的行动
- [x] 有一句能被转述的记忆句
- [x] 逐句口播读起来像真人说话，不像书面文章

结论：通过。脚本以“两周产品，0 付费”开场，只讲“能卖也能做，才拥有完整价值链”，保留小林案例、当天联系 3 个潜在用户的动作和“只会做，是产能；只会卖，是承诺；能卖也能做，才是资产”的记忆句。

## G2 配音闸口

- [x] 已生成 30 秒试音
- [x] 音色符合系列声纹：冷静、可信、有私人感
- [x] 关键句前后有停顿
- [x] 没有明显新闻腔、带货腔、短剧腔
- [x] `technical_audio_pass` 已通过
- [x] `audio_subjective_review` 已标记为 pending，未冒充人工听审

试音结论：

- 评估边界：本轮没有实际听音频，G2 结论基于 `script.md`、`voice/narration.txt`、两版 VTT 时间轴、`ffprobe` / `silencedetect` 技术检测、既有 Yunxi 系列标杆经验和主编提供的生成参数；G4 成片评审仍需人工抽听关键段。
- 试音文件：`voice/narration-yunxi-trial.mp3`，31.800s，`zh-CN-YunxiNeural`，rate `-4%`，字幕 `subtitles/narration-yunxi-trial.vtt`。试音覆盖第 1-12 句，包含“两周产品 / 零个付费”的现实冲突、“销售不是忽悠买单 / 构建不是躲起来做功能”的定义段，以及纳瓦尔原则句，足够判断本集声纹方向。
- 试音判断：通过。Yunxi 与本系列“知识型旁白，冷静、可信、轻微私人感”的方向一致；第 1-12 句短句密度高，`-4%` 试音更利于观察停顿和句意落点，没有从文本和时间轴上暴露带货腔、短剧反转腔或新闻播音腔风险。
- 最终配音：`voice/narration-yunxi-v4.mp3`，105.216s，`zh-CN-YunxiNeural`，rate `+8%`，24kHz mono，字幕 `subtitles/narration-yunxi-v4.vtt`。时长处于系列推荐 85-105s 的上沿附近，但未超过 110s。
- 停顿检测：`silencedetect` 在关键句附近检测到有效静音窗口，第 4 句约 0.793s、第 6 句约 0.787s、第 9 句约 0.729s、第 17 句约 0.672s、第 44 句约 0.789s。说明关键判断句后有停顿承接，但部分停顿长于 300-500ms 标准，视觉剪辑应利用卡片切换或数字证据补足节奏，避免拖慢。
- 配音真实感预估：8.7 / 10。该分数为“基于文本、TTS 时间轴和 Yunxi 标杆经验的可发布预估”，不是实际听感打分；`audio_subjective_review` 保持 pending。
- 风险：最终版 `+8%` 比试音快，若背景音乐或字幕动画过密，可能削弱“能力诊断”的私人感；第 35 句“先问，谁正为它付出时间、钱，或机会成本。”较长，视觉上建议拆成两拍；结尾记忆句需要保留停顿，不要被 BGM 推成口号感。
- G2 结论：技术通过。可进入 G3 视觉制作和 G4 成片评审；发布前人工完整看听由用户自然完成，不作为自动生产流程阻塞项。

## G3 画面闸口

- [x] `npx hyperframes lint` 0 errors / 0 warnings
- [x] `npx hyperframes inspect` 0 layout issues
- [x] 已抽帧检查开头、原则、案例、结尾
- [x] 没有难看的标题断行
- [x] 字幕没有遮挡主体
- [x] 画面不是纯文字 PPT

抽帧记录：主线程验证 `npx hyperframes lint` 0 errors / 0 warnings，`npx hyperframes inspect --samples 16` 0 layout issues；本轮复核 `review-frames/01-hero.png` 到 `08-final-question.png`，开头、原则、左右案例、诊断、行动清单和结尾问题均可读，字幕未遮挡主体。

## G3.5 样片与装配闸口

- [x] 已完成样片或等价片段抽检
- [x] 已生成 `assembly-check.md`
- [x] 已检查 scene 切点、字幕落字、停顿、转场、BGM / ducking 风险
- [x] 已确认 `scene_energy` 与画面/配音节奏一致

结论：通过。`assembly-check.md` 未发现硬性返工点；如果发布后完播率偏弱，优先压缩 S03-S05 案例与诊断段 3-5 秒。

## G4 成片闸口

- [x] ffprobe 确认 1080x1920
- [x] 音画时长匹配
- [x] 视频评审评分 >= 9.0
- [x] `technical_audio_pass` 已通过
- [x] `audio_subjective_review` 保持 pending，未写成主观听审通过
- [x] 必改建议已处理
- [x] 复审通过

复审结论：通过，可进入发布资产和 Notion 同步。成片综合评分 9.1 / 10；最终成片 H.264 1080x1920、30fps，video duration 105.200s，format duration 105.216s，AAC 24000 Hz mono 音频 duration 105.216s，音画匹配。无硬性必改，不需要返工。边界：本轮无法实际听音频，音频主观听感保持 pending，不替代发布前人工看听。

## G5 发布闸口

- [x] 最终成片已归档
- [x] 无声版已归档
- [x] 字幕文件已归档
- [x] 配音文件已归档
- [x] 封面已独立制作
- [x] 发布标题已确定
- [x] 发布文案和标签已完成
- [x] Notion 视频台账已更新
- [x] Notion 视频页面已同步 `content-review.md`、`brief.md`、`script.md`、`scene-contract.json`、`shot-list.md`、`assembly-check.md`
- [x] `notion-sync-receipt.md` 已生成
- [x] 发布清单保留“发布前人工完整看听一遍”

发布结论：G5 发布前资产完成。`publish-assets.md` 已包含标题、发布文案和标签，成片、无声版、字幕、配音、封面均已在本地归档；`notion-sync-receipt.md` 记录了视频台账、视频页面、选题库、发布复盘库、`assembly-check.md` 和生产文档同步状态。发布后仍需回填平台数据。

## Agent 交接记录

- [x] 选题研究 Agent 已交接
- [x] 内容主编 Agent 已交接
- [x] 脚本 Agent 已交接
- [x] 视觉导演 Agent 已交接
- [x] 配音导演 Agent 已交接
- [x] 装配剪辑 Agent 已交接
- [x] 视频评审 Agent 已交接
- [x] 发布复盘 Agent 已创建待复盘记录

交接记录目录：`agent-handoffs/`
