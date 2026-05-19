# my_project

这个仓库用于放多个独立小项目。

## 本地联调

统一启动整套联调环境：

```bash
./scripts/dev-stack.sh
```

如果你只想启动单个服务，也可以直接用：

```bash
./scripts/dev-personal-website.sh
./scripts/dev-interview-pipeline.sh
./scripts/dev-verbal-expression-coach.sh
```

## 当前项目

- [interview-audio-pipeline](./interview-audio-pipeline)
  面试录音自动化处理与 Notion 复盘工具，支持本地音频、BOS、豆包语音妙记、本地前端工作台。
- [personal-ai-website](./personal-ai-website)
  个人 AI 工具、学习笔记、阶段总结与资源收藏网站。
- [verbal-expression-coach](./verbal-expression-coach)
  表达模仿训练与教练反馈原型，支持视频上传、历史记录与结构化分析结果。
- [video](./video)
  短视频工作流目录，包含选题、脚本、镜头清单、素材整理和发布模板。
