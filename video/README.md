# Video Workflow

这个目录用于搭建一条轻量但可扩展的短视频工作流，目标是把“灵感 -> 脚本 -> 拍摄/素材 -> 剪辑 -> 发布”拆成稳定步骤。

## 目录结构

```text
video
├── assets/                # 通用素材库：B-roll、字体、封面元素、音效
├── bin/
│   ├── new-short.sh       # 新建通用短视频项目
│   ├── new-naval-video.sh # 新建纳瓦尔知识短视频项目
│   ├── new-thinking-tool-video.sh # 新建实用思维工具短视频项目
│   └── render-naval-video.sh # 渲染纳瓦尔模板视频
├── inbox/                 # 临时收集区：灵感、链接、待整理素材
├── output/                # 聚合导出区：最终成片、封面、字幕包
├── projects/              # 每条视频一个独立项目目录
├── series/                # 系列化内容的专用目录
└── templates/             # brief / script / shot list / publish checklist 模板
```

## 推荐节奏

1. 把零散想法先丢进 `inbox/`
2. 运行 `./bin/new-short.sh 选题名` 新建项目
3. 先写 `brief.md`，确认目标观众、核心观点、预期时长
4. 再写 `script.md` 和 `shot-list.md`
5. 素材和配音分别放到项目目录内的 `assets/`、`voice/`
6. 剪完后把成片放到 `exports/`，最终发布物同步到 `output/`

## 快速开始

```bash
cd /Users/chendingyu/my_project/video
./bin/new-short.sh AI 面试复盘 3 个表达误区
```

如果你要持续做《纳瓦尔宝典》内容，直接用专用脚手架：

```bash
cd /Users/chendingyu/my_project/video
./bin/new-naval-video.sh 纳瓦尔宝典-长期主义
./bin/render-naval-video.sh /Users/chendingyu/my_project/video/series/naval-almanack/episodes/2026-05-16-纳瓦尔宝典-长期主义
```

如果你要做《实用思维工具》内容，使用独立系列脚手架：

```bash
cd /Users/chendingyu/my_project/video
./bin/new-thinking-tool-video.sh 二阶思维-别只问马上会怎样
./bin/render-thinking-tool-video.sh /Users/chendingyu/my_project/video/series/practical-thinking-tools/episodes/2026-05-18-二阶思维-别只问马上会怎样
```

系列内容建议统一放在：

```text
video/series/naval-almanack
├── README.md
├── series-backlog.md
├── episodes/
└── shared-assets/
```

《实用思维工具》系列放在：

```text
video/series/practical-thinking-tools
├── README.md
├── series-backlog.md
├── content-system/
├── agent-roles/
├── episodes/
└── shared-assets/
```

脚本会生成类似下面的结构：

```text
projects/2026-04-30-AI-面试复盘-3-个表达误区
├── assets/
├── brief.md
├── edit/
├── exports/
├── publish/
├── publish-checklist.md
├── script.md
├── shot-list.md
├── subtitles/
└── voice/
```

## 后续可以继续补的能力

- 增加 `ffmpeg` 批处理脚本：横转竖、压缩、抽帧、混音
- 增加字幕自动化：Whisper / Doubao / 剪映导入格式
- 增加封面生成模板：统一标题样式和品牌资产
- 增加发布台账：记录平台、发布时间、数据表现、复盘结论
- 为纳瓦尔模板增加 `content.js -> narration/vtt` 的半自动同步
