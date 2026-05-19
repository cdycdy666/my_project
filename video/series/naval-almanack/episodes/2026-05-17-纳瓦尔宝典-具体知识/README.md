# 纳瓦尔宝典-具体知识

- 创建日期: 2026-05-17
- 项目目录: /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-具体知识
- 系列目录: /Users/chendingyu/my_project/video/series/naval-almanack
- 模板类型: 纳瓦尔宝典 3 分钟内知识短视频

## 推荐顺序

1. 先写 content-review，判断这个选题值不值得进入制作
2. 再写 brief，确认这条视频讲哪条原则、帮谁建立什么认知
3. 再写 script，把钩子、展开、收束和 CTA 写清楚
4. 打开 hyperframes/content.js，把屏幕文字、字幕和场景时长改成这一条的版本
5. 打开 voice/narration.txt，整理最终口播文案
6. 运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-具体知识" 先出无声画面版
7. 生成配音后，再运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-17-纳瓦尔宝典-具体知识" voice/你的配音文件

## 模板文件

- hyperframes/index.html: 通用画面模板
- hyperframes/content.js: 本条视频的核心配置
- voice/narration.txt: 旁白文案
- template-guide.md: 模板使用说明

## 当前 v4 产物

- 最终成片: `exports/naval-specific-knowledge-v4-final.mp4`
- 无声画面版: `exports/naval-specific-knowledge-v4-visual.mp4`
- Yunxi 配音: `voice/narration-yunxi-v4.mp3`
- 字幕源文件: `subtitles/narration-yunxi-v4.vtt`
- 封面 PNG: `cover/cover-v4.png`
- 封面生成脚本: `cover/render_cover.py`
- 评审: `review.md`
- 发布资产: `publish-assets.md`

## 版本记录

- v4: 强化 AI 时代语境，加入系列标识、进度线、烧录字幕和独立封面，作为当前推荐发布版。
- v3: 内容优先样片，已通过初评，保留作对照。
