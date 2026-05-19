# 纳瓦尔短视频模板

这个模板适合做《纳瓦尔宝典》风格的认知类短视频，建议时长控制在 45-180 秒。

## 你只需要改 3 个地方

1. `brief.md` / `script.md`
   明确本条讲哪条原则、给谁看、最终想让观众记住什么。
2. `hyperframes/content.js`
   改屏幕上的标题、卡片、对照段、结尾文案和各段时长。
3. `voice/narration.txt`
   改成最终口播稿，再生成配音。

## 目录说明

- `hyperframes/index.html`
  通用画面模板。通常不需要频繁改结构。
- `hyperframes/content.js`
  当前视频的内容配置。以后每一条主要改这里。
- `voice/narration.txt`
  当前视频的旁白稿。

## 推荐流程

1. 新建项目
   `./bin/new-naval-video.sh 纳瓦尔宝典-主题`
2. 写文案
   先完成 `brief.md`、`script.md`、`voice/narration.txt`
3. 配画面
   改 `hyperframes/content.js`
4. 先渲无声版
   `./bin/render-naval-video.sh /绝对路径/到/项目目录`
5. 生成配音
   可以用你偏好的 TTS，也可以真人录音
6. 封装成片
   `./bin/render-naval-video.sh /绝对路径/到/项目目录 voice/配音文件.mp3`

## 内容结构建议

适合纳瓦尔内容的 5 段式：

1. 钩子：一句反常识问题或判断
2. 原则：纳瓦尔核心原则的最短表达
3. 展开：3 个解释卡片
4. 对照：短期 vs 长期，努力 vs 杠杆，运气 vs 系统
5. 收束：一句能被记住的话

## 配音建议

- 如果追求最真实，优先真人录音
- 如果用 TTS，先生成 1-2 句样音再决定整段
- 最终旁白最好和画面总时长差不超过 2-3 秒
