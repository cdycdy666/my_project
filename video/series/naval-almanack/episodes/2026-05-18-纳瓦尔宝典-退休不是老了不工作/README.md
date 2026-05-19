# 纳瓦尔宝典-退休不是老了不工作

- 创建日期: 2026-05-18
- 项目目录: /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-退休不是老了不工作
- 系列目录: /Users/chendingyu/my_project/video/series/naval-almanack
- 模板类型: 纳瓦尔宝典 3 分钟内知识短视频

## 推荐顺序

1. 先从 `../../content-system/content-material-library.md` 选择原料卡，必要时补 `content-material-card.md`
2. 再写 `content-review.md`，内容评分低于 9.0 不进入制作
3. 更新 `quality-check.md` 的 G0 和 G1，确认选题与文案过闸口
4. 再写 `brief.md`，确认这条视频解决哪个当下焦虑
5. 先做 `script-lab.md`，验证 5 个钩子、3 个案例角度、反驳桥、记忆句和留存任务
6. 再写 `script.md`、`voice/narration.txt` 和 `scene-contract.json`，脚本自评分低于 90 不进入制作
7. 先写 `visual-component-map.md`，为每个 scene 选择主组件
8. 基于 `scene-contract.json` 和 `visual-component-map.md` 写 `shot-list.md`
9. 先生成 30 秒试音，写 `voice/voice-manifest.json`，`technical_audio_pass` 未通过不全片生成
10. 打开 `hyperframes/content.js`，把屏幕文字、字幕和场景时长改成这一条的版本
11. 运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-退休不是老了不工作" 先出无声画面版
12. 完成 15-30 秒样片或等价片段抽检，写 `assembly-check.md`
13. 抽帧检查开头、原则、案例、结尾
14. 生成全片配音后，再运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-退休不是老了不工作" voice/你的配音文件
15. 写 `review.md`，成片评分低于 9.0 不发布
16. 补封面、发布资产、Notion 台账和 `notion-sync-receipt.md`
17. 写 `agent-retrospective.md`，并关闭不再需要的 Agent
18. 核对 `agent-registry.md`，确保所有不再需要的 Agent 都已关闭

## 模板文件

- quality-check.md: 本条视频的质量闸口
- content-material-card.md: 本条视频实际采用的内容原料卡
- script-lab.md: 正式脚本前的钩子、案例、记忆句和留存实验
- visual-component-map.md: 正式分镜前的视觉组件选择
- agent-registry.md: 本条视频实际启动过的 Agent 台账，用于 G5/G6 清理后台任务
- agent-handoffs/: 多 Agent 交接记录
- scene-contract.json: 脚本、视觉、配音和装配协议
- assembly-check.md: G3.5 装配剪辑检查
- review.md: G4 成片评审
- notion-sync-receipt.md: G5 Notion 同步唯一回执
- hyperframes/index.html: 通用画面模板
- hyperframes/content.js: 本条视频的核心配置
- voice/narration.txt: 旁白文案
- template-guide.md: 模板使用说明

## 本轮最终产出

- 最终成片：`exports/naval-retirement-audit-v1-final.mp4`
- 无声版：`exports/naval-retirement-audit-v1-visual.mp4`
- 配音：`voice/narration-yunxi-scene-v2.mp3`
- 字幕：`subtitles/narration-yunxi-scene-v2.vtt`
- 封面：`cover/cover-v1.png`
- 关键帧：`review-frames/01-hero.png` 到 `review-frames/07-outro.png`
- 旧版归档：`../../archive/2026-05-18-纳瓦尔宝典-退休不是老了不工作__old-before-clean-regeneration`
