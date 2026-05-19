角色：06 视频评审 Agent

输入：
- 系列 SOP：`multi-agent-sop.md`
- 质量标准：`quality-standard.md`
- 角色定义：`agent-roles/06-video-reviewer.md`
- 本集上游：`content-review.md`、`brief.md`、`script.md`、`scene-contract.json`、`shot-list.md`、`assembly-check.md`、`voice/voice-manifest.json`、`hyperframes/content.js`
- 成片：`exports/naval-retirement-audit-v1-final.mp4`
- 抽帧：`review-frames/01-hero.png` 到 `review-frames/07-outro.png`
- 补充查看：`cover/cover-v1.png`

输出：
- 已写入：`review.md`
- 已写入：`agent-handoffs/06-video-reviewer.md`

评分：
- 总分：9.0 / 10
- G4 建议：条件通过。结构、视觉和技术参数达标；未完成人耳听审，发布前必须完整看听。
- `technical_audio_pass`: pass
- `audio_subjective_review`: pending

关键判断：
- 结构链路成立：hook、reframe、proof、contrast、diagnosis、action/memory line 均能服务“今天不再被明天绑架”这一核心判断。
- S02 旧模板残留复核通过：抽帧显示 `TODAY COMPLETE / TIME DEBT CLEARED`，`rg` 未在 `hyperframes/` 中检出旧 `HALF / LEVERAGE / SELL / BUILD / VALUE CHAIN / sell-build` 语义。
- 行动卡中文自然：`删掉 / 定价 / 委托 / 重新谈边界`可读、可理解，不阻塞发布。
- 字幕/主体遮挡复核通过：关键帧中底部字幕未遮挡主标题、案例卡、诊断卡、行动卡或记忆句。
- `scene_energy` 匹配：S01/S05 高能诊断，S02-S04 中高能反转和证据，S06 降能收束，整体合理。

风险：
- 本 Agent 未实际人耳听音频，不能确认音色真人感、BGM ducking、停顿落点或转场追尾听感。
- 第 39 句动作词密集，仍是发布前人工听审最高优先级。
- S04->S05、S05->S06、action->outro 的字幕时间轴间隔约 60ms，视觉逻辑成立，但听感可能需要局部留白。
- 记忆句第 42-43 句需要确认不被 +18% 语速或 BGM 推成口号。

必改/可选：
- 必改：无新的结构、视觉或技术必改项。
- 发布前必须：人工完整看听成片，确认 `audio_subjective_review`，重点听第 39 句、S04->S05、S05->S06、action->outro 和记忆句。
- 可选：S06 第三行动行后续可拆成四个小标签，增强截图感。
- 可选：S03/S04 后续可升级为更真实的日历、消息和会议组件，进一步降低模板卡片感。

下一位 agent 需要注意：
- 主编总控不要把本次评审写成“音频主观听审通过”；只能写 pending，直到人工完整看听完成。
- G5 发布资产、Notion 同步和发布复盘仍由主编总控确认，本 Agent 不替代 G5。
- 如果人工听审发现第 39 句连读，建议只做 S06 单句补丁或增加 break，不建议重做全片。
- 如果转场听感追尾，优先局部增加 250-400ms 留白并同步字幕/时间轴。

生命周期建议：关闭。G4 评审与交接已落档；除非主编总控要求返工复审，否则不需要保留本 Agent 上下文。

是否通过当前闸口：建议 G4 条件通过，进入发布前人工完整看听与 G5 准备；不得在 `audio_subjective_review` 仍为 pending 时声称已完成主观音频确认。
