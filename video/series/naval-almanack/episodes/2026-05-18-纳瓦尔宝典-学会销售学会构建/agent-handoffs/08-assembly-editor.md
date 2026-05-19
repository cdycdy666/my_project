# 08 装配剪辑 Agent 交接

## 角色

08 装配剪辑 Agent

## 输入

- `scene-contract.json`
- `shot-list.md`
- `hyperframes/content.js`
- `voice/voice-manifest.json`
- `review-frames/01-hero.png` 到 `review-frames/08-final-question.png`
- `subtitles/narration-yunxi-v4.vtt`
- `quality-standard.md`

## 输出

- `assembly-check.md`
- G3.5 样片与装配闸口状态建议：通过

## 关键判断

- 本集的 `scene_energy` 梯度成立：S01 / S05 为 5，负责强冲突和强诊断；S03 / S04 为 4，负责案例证据；S02 / S06 为 3，负责解释和行动收束。
- `retention_goal` 已被画面和字幕承接：hook 用“两周产品 / 0 付费”拉住人，案例段用左右对照给证据，结尾用行动清单和记忆句方便截图。
- 样片等价抽检未发现硬性装配问题：没有明显音画错位、字幕抢拍、转场打断或 BGM 压口播风险。
- 第 35 句“时间、钱，或机会成本”仍是全片最需要字幕拆拍和 BGM ducking 的句子，但已在 `voice-manifest.json` 与 `assembly-check.md` 中标记。

## 风险

- 全片 105.216s，处在系列推荐时长上沿；如果发布后完播率偏弱，优先压缩 S03-S05 案例与诊断段 3-5 秒。
- S05 诊断段信息密度最高，如果后续加 BGM，必须避让关键判断句，不能推成广告感。
- 本轮为样片等价抽检，不替代发布前用户完整看听。

## 下一位 Agent 需要注意

- 视频评审 Agent 应把结构审和成片审分开，不要把 G3.5 的装配通过等同于最终发布通过。
- 主编总控在 G5 同步时需要把 `assembly-check.md` 写入 Notion 视频页面和 `notion-sync-receipt.md`。
- 发布复盘 Agent 需要观察 31-75 秒案例段是否掉点，验证 G3.5 的“可选压缩 3-5 秒”建议是否需要进入下一版。

## 是否通过当前闸口

通过。G3.5 样片与装配闸口通过，可进入 G4 成片评审。
