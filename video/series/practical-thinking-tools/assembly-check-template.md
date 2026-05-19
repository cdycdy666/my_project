# Assembly Check

## 输入

- `script.md`
- `scene-contract.json`
- `visual-component-map.md`
- `shot-list.md`
- `hyperframes/content.js`
- `hyperframes/index.html`
- `voice/voice-manifest.json`
- `preview/contact-sheet-visual.jpg`
- `preview/contact-sheet-final.jpg`
- `preview/ffprobe-final.json`
- `exports/*final*.mp4`

## 结论

- G3.5 状态建议：
- 是否允许进入 G4：
- 剩余 pending 项：

## 技术核验

- `npx hyperframes lint`：
- `npx hyperframes inspect`：
- 视觉版 ffprobe：
- 最终版 ffprobe：
- 音轨状态：
- 联系表文件：

## 联系表与首尾检查

| 检查项 | 结论 | 需要修复 |
| --- | --- | --- |
| 首 5 秒是否同时有钩子、字幕、画面动作 |  |  |
| 工具首次出现是否足够早 |  |  |
| 中段是否有连续低信息空帧 |  |  |
| 尾 15 秒是否保留记忆句、行动问题或评论引导 |  |  |
| 结尾是否存在长时间纯氛围背景 |  |  |

## 检查项

| Scene | 主工具步骤 | 主视觉组件 | 字幕 | 镜头切点 | 停顿 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| S01 |  |  |  |  |  |  |

## 必查风险

- 工具解释像定义，不像演示。
- 视觉组件没有服务当前工具步骤。
- 行动卡太大或太抽象。
- 联系表显示某一段只有背景、没有信息推进。
- 片尾最后 10-15 秒没有承接记忆句或行动引导。
- BGM 压住关键动作句。
- 未实际听审时，把 `audio_subjective_review` 写成 confirmed。
