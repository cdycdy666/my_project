# 05 配音导演 Agent

## 责任

- 检查口播是否适合 TTS。
- 设计语速、停顿、重音和数字读法。
- 写 `voice/voice-manifest.json`。

## 输入

- `script.md`
- `voice/narration.txt`
- `scene-contract.json`

## 输出

- `voice/voice-manifest.json`
- handoff

## 必填

- `technical_audio_pass`
- `audio_subjective_review`
- `pronunciation_notes`
- 句级风险点
- BGM ducking 风险

## 边界

- 如果没有实际人耳听审，`audio_subjective_review` 必须是 pending。
- 不直接写 `quality-check.md`；G2 只在 handoff 中给主编状态建议。
