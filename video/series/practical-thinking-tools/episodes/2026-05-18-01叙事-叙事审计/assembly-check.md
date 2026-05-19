# Assembly Check

## 输入

- `script.md`
- `scene-contract.json`
- `visual-component-map.md`
- `shot-list.md`
- `hyperframes/content.js`
- `hyperframes/index.html`
- `voice/voice-manifest.json`
- `exports/narrative-audit-visual.mp4`
- `exports/narrative-audit-final.mp4`

## 结论

- G3.5 状态建议：技术装配通过，人耳听审 pending。
- 是否允许进入 G4：允许进入有声成片 G4 审查。
- 剩余 pending 项：发布前人工完整看听、封面、标题、发布文案。

## 技术核验

- `npx hyperframes lint`：0 errors，1 maintainability warning（`index.html` 过大，不影响画面但后续建议拆分组件）。
- `npx hyperframes inspect --samples 18`：0 layout issues。
- 视觉版 `ffprobe`：1080x1920，30fps，7380 frames，246.000000 sec。
- 旁白 `ffprobe`：PCM WAV，48000 Hz，stereo，245.983458 sec。
- 最终版 `ffprobe`：H.264 + AAC，1080x1920，30fps，245.983000 sec。
- `volumedetect`：mean_volume -24.0 dB，max_volume -2.7 dB，非空音轨。
- 当前视觉导出：`exports/narrative-audit-visual.mp4`。
- 当前有声导出：`exports/narrative-audit-final.mp4`。
- 最终版联系表：`preview/contact-sheet-final.jpg`。
- 最终版技术信息：`preview/ffprobe-final.json`。

## 联系表补充检查

| 检查项 | 结论 | 需要修复 |
| --- | --- | --- |
| 首 5 秒是否同时有钩子、字幕、画面动作 | 通过 | 无 |
| 工具首次出现是否足够早 | 条件通过 | 下一版可让“三栏审计”影子更早出现 |
| 中段是否有连续低信息空帧 | 通过 | 无 |
| 尾 15 秒是否保留记忆句、行动问题或评论引导 | 条件通过 | 230s 附近出现低信息空背景，发布前建议缩短或补信息 |
| 结尾是否存在长时间纯氛围背景 | 有风险 | 发布前打磨 |

## 检查项

| Scene | 主工具步骤 | 主视觉组件 | 字幕 | 镜头切点 | 停顿 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | 把“事实”和“故事”拆开 | Mistake Map | 主问题明确 | 从焦虑事实切入审计台 | 记忆句前已保留长停顿 | 开头真实感待人耳听审 |
| S02 | 给出叙事审计定义 | Tool Card | 单屏单概念 | 原理卡承接核心句 | “证据、解释、代价”需分拍 | 过快会显得像课程定义 |
| S03 | 林薇案例演示 | Cause Chain | 案例动作清楚 | 从会议、加班、改方向转入叙事 | 人物转折处要降速 | 案例若读太平会损失代入 |
| S04 | 三列表格审计 | Decision Log | 工具步骤最强 | 表格逐列落字 | 每列后轻停 | 信息密度最高，BGM 必须压低 |
| S05 | 七天动作 | Action Checklist | 行动可执行 | 从解释转行动 | “只做一件事”前后留白 | 别做成励志口号 |
| S06 | 记忆句与评论问题 | Memory Card | 收束有力 | 回到核心句 | 结尾问题前留空气感 | 需要人耳确认不过度煽情 |

## 必查风险

- 工具解释像定义，不像演示：已用林薇案例和三列表格压住抽象风险。
- 视觉组件没有服务当前工具步骤：已用 Mistake Map、Tool Card、Cause Chain、Decision Log、Action Checklist 对应每段动作。
- 行动卡太大或太抽象：行动限定为“选一个解释，重写一次叙事，再做一个边界动作”。
- BGM 压住关键动作句：本版未加 BGM，避免压住口播。
- 未实际听审时，把 `audio_subjective_review` 写成 confirmed：保持 pending。
