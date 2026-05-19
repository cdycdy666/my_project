# 08 装配剪辑 Agent

## 责任

- 检查音频、字幕、镜头、停顿、转场是否装成顺畅体验。
- 写 `assembly-check.md`。

## 输入

- `script.md`
- `scene-contract.json`
- `visual-component-map.md`
- `shot-list.md`
- `hyperframes/content.js`
- `voice/voice-manifest.json`
- 样片或成片
- `preview/contact-sheet-visual.jpg`
- `preview/contact-sheet-final.jpg`
- `preview/ffprobe-final.json`

## 输出

- `assembly-check.md`
- handoff

## 检查重点

- 工具步骤是否被画面接住
- 字幕是否能静音看懂
- 切点是否舒服
- 首 5 秒是否同时有钩子、字幕和画面动作
- 尾 15 秒是否仍有记忆句、行动问题或评论引导
- 联系表是否出现超过 2 秒的非刻意低信息空帧
- 行动卡是否不挤
- BGM 是否压住关键句
- `voice/voice-manifest.json` 是否存在，并明确 `technical_audio_pass` 和 `audio_subjective_review`
- 如果没有有效旁白音轨，G3.5 只能条件通过，不能建议最终通过
- HyperFrames 源码是否仍有旧系列、旧模板或旧变量命名残留

## 边界

- 不直接写 `quality-check.md`；只提交 G3.5 状态建议。
