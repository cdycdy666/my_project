# 纳瓦尔宝典-杠杆

- 创建日期: 2026-05-17
- 项目目录: /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-杠杆
- 系列目录: /Users/chendingyu/my_project/video/series/naval-almanack
- 模板类型: 纳瓦尔宝典 3 分钟内知识短视频

## 推荐顺序

1. 先写 content-review 或 brief，判断这条原则是否值得进入制作
2. 再写 script，把现实冲突、杠杆分类、具体案例和行动建议写清楚
3. 打开 hyperframes/content.js，把屏幕文字、字幕和场景时长改成这一条的版本
4. 打开 voice/narration.txt，整理最终口播文案
5. 运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-杠杆" 先出无声画面版
6. 生成配音后，再运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-杠杆" voice/你的配音文件
7. 抽帧复看开头、案例、行动建议，再补齐封面和发布资产

## 当前 v4 产物

- 最终成片: `exports/naval-leverage-v4-final.mp4`
- 无声画面版: `exports/naval-leverage-v4-visual.mp4`
- Yunxi 配音: `voice/narration-yunxi-v4.mp3`
- 字幕源文件: `subtitles/narration-yunxi-v4.vtt`
- 封面 PNG: `cover/cover-v4.png`
- 评审: `review.md`
- 发布资产: `publish-assets.md`
- 质量闸口: `quality-check.md`

## 质量状态

- 当前版本: v4 推荐发布版
- 评审评分: 9.1 / 10
- 技术校验: `npx hyperframes lint` 0 errors / 0 warnings；`npx hyperframes inspect --samples 16` 0 layout issues
- 成片规格: h264, 1080x1920, 89.200 秒
- 音频规格: aac, 24000 Hz, mono, 89.173 秒
- Notion 状态: 视频台账已更新为待发布，选题库已同步 v4 结论

## 版本记录

- v4: 强化“努力需要放大器”的现实冲突，加入普通人可启动的杠杆案例、系列标识、进度线、烧录字幕和独立封面，作为当前推荐发布版。
- v2: 加入许可杠杆 / 无许可杠杆对比，解决首版分类不够清晰的问题。
- v1: 完成首版视觉样片和 Yunxi 配音。
