# 纳瓦尔宝典-学会销售学会构建

- 创建日期: 2026-05-18
- 项目目录: /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-学会销售学会构建
- 系列目录: /Users/chendingyu/my_project/video/series/naval-almanack
- 模板类型: 纳瓦尔宝典 3 分钟内知识短视频

## 推荐顺序

1. 先写 content-review，内容评分低于 9.0 不进入制作
2. 更新 quality-check 的 G0 和 G1，确认选题与文案过闸口
3. 再写 brief，确认这条视频解决哪个当下焦虑
4. 再写 script，把钩子、案例、行动建议和配音标注写清楚
5. 写 scene-contract，确认脚本、视觉和配音共享同一份结构化协议
6. 写 shot-list，确认不是纯文字 PPT
7. 主编总控把生产文档同步到 Notion 视频页面
8. 先生成 30 秒试音，系统确认 technical_audio_pass，主观听感未听时标记 pending
9. 打开 hyperframes/content.js，把屏幕文字、字幕和场景时长改成这一条的版本
10. 运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-学会销售学会构建" 先出无声画面版
11. 抽帧检查开头、原则、案例、结尾
12. 生成全片配音后，再运行 ./bin/render-naval-video.sh "/Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-18-纳瓦尔宝典-学会销售学会构建" voice/你的配音文件
13. 补封面、发布资产、Notion 台账和 notion-sync-receipt，成片评分低于 9.0 不发布

## 模板文件

- quality-check.md: 本条视频的质量闸口
- scene-contract.json: 脚本、视觉和配音之间的结构化协议
- assembly-check.md: 装配剪辑检查
- notion-sync-receipt.md: G5 Notion 同步唯一回执
- agent-handoffs/: 多 Agent 交接记录
- hyperframes/index.html: 通用画面模板
- hyperframes/content.js: 本条视频的核心配置
- voice/narration.txt: 旁白文案
- template-guide.md: 模板使用说明

## 当前 v4 产物

- 最终成片: `exports/naval-sell-build-v4-final.mp4`
- 无声画面版: `exports/naval-sell-build-v4-visual.mp4`
- Yunxi 配音: `voice/narration-yunxi-v4.mp3`
- 字幕源文件: `subtitles/narration-yunxi-v4.vtt`
- 封面 PNG: `cover/cover-v4.png`
- 发布资产: `publish-assets.md`
- Scene Contract: `scene-contract.json`
- 装配剪辑检查: `assembly-check.md`
- Notion 同步回执: `notion-sync-receipt.md`
- 成片评审: `review.md`
- 多 Agent 复盘: `agent-retrospective.md`
- Notion 视频页面: https://www.notion.so/36332f4915ee81cd93fcd2fcf9122984
- Notion 发布复盘记录: https://www.notion.so/36332f4915ee81ad8e7ac7eb63634f64

## 版本记录

- v4: 多 Agent 全链路制作版，完成选题、brief、脚本、视觉、配音、评审、Notion 同步和角色迭代；综合评分 9.1 / 10。
