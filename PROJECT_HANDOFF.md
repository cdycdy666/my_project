# Project Handoff

更新时间：2026-05-13

这份文档是给“切账号后重新接手当前工作”的速读版。

## 1. 仓库是什么

这是一个多项目工作区，不是单一应用仓库。根目录 [`README.md`](/Users/chendingyu/my_project/README.md) 已经补成了统一入口。

当前包含 4 条主线：

- `interview-audio-pipeline`
  面试录音自动化处理链路。输入本地音频或 URL，输出转写、结构化面评，并可写入 Notion。
- `personal-ai-website`
  Next.js 中文个人网站，用来承载 AI 工具、笔记、资源，以及另外两个工具的入口。
- `verbal-expression-coach`
  表达模仿训练 MVP。上传视频，保存历史记录，生成结构化分析结果。
- `video`
  短视频工作流目录，不是在线服务，更像内容生产 SOP 和素材组织系统。

## 2. 当前最重要的项目

当前最像“主线开发中”的是 `interview-audio-pipeline`，原因：

- 最近唯一明确修改过的业务代码都在这个子项目里
- 根目录联调脚本也是围绕它和另外两个服务串起来的
- 它已经具备较完整的输入、处理、输出闭环

建议重新接手时，先读这几个文件：

1. [`interview-audio-pipeline/README.md`](/Users/chendingyu/my_project/interview-audio-pipeline/README.md)
2. [`interview-audio-pipeline/src/interview_pipeline/cli.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/cli.py)
3. [`interview-audio-pipeline/src/interview_pipeline/pipeline.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/pipeline.py)
4. [`interview-audio-pipeline/src/interview_pipeline/config.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/config.py)
5. [`interview-audio-pipeline/src/interview_pipeline/web.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/web.py)

## 3. interview-audio-pipeline 在做什么

目标是把这条链路产品化：

`本地音频 / 录音 URL -> 转写 -> 结构化面评 -> Notion 复盘页`

当前能力：

- 支持 3 种转写 provider
  - `local_whisper`
  - `qianfan`
  - `doubao_miaoji`
- 支持本地音频文件输入
- 支持音频 URL 输入
- 如果配置了 BOS，可把本地文件上传后生成可访问链接
- 自动推断面试日期和轮次
- 生成结构化总结、亮点、风险点、待确认问题、建议结论
- 生成 Notion 页面正文 markdown
- 可选追加“模拟面试复盘”内容
- 支持 CLI
- 支持一个本地 Web 工作台

核心模块分工：

- `cli.py`
  CLI 入口，暴露 `run / inspect-mcp / inspect-notion / upload-bos / web`
- `pipeline.py`
  总编排层，负责拼接配置、元数据推断、转写、结构化输出、Notion 写入
- `config.py`
  读取 `.env`，组装 provider / BOS / Notion 配置
- `formatter.py`
  把转写结果加工成“AI纪要 + 结构化面评 + 模拟复盘”
- `web.py`
  内置轻量 HTTP 服务，支持上传文件、调用流水线并返回结果
- `notion_client.py`
  写入 Notion 数据库和页面正文
- `local_whisper.py` / `qianfan_media_insight.py` / `doubao_miaoji.py`
  各 provider 的具体实现

## 4. 最近未提交的关键改动

当前分支：`main`

目前有未提交修改，主要是这 4 部分：

### A. 根目录 README 增加统一联调说明

涉及文件：

- [`README.md`](/Users/chendingyu/my_project/README.md)

新增内容：

- `./scripts/dev-stack.sh`
- `./scripts/dev-personal-website.sh`
- `./scripts/dev-interview-pipeline.sh`
- `./scripts/dev-verbal-expression-coach.sh`
- 新增 `video` 目录说明

### B. interview-audio-pipeline 支持 “local_whisper 处理音频 URL”

涉及文件：

- [`interview-audio-pipeline/src/interview_pipeline/pipeline.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/pipeline.py)

这次改动前：

- `TRANSCRIPTION_PROVIDER=local_whisper` 时必须传 `audio_file`

这次改动后：

- 如果只传 `audio_url`，会先把远程音频下载到临时文件
- 再调用本地 whisper 转写
- 转写完成后自动删除临时文件

这意味着：

- `local_whisper` 不再只适合“本地文件上传”场景
- 也能覆盖“已经有公网 URL，但仍想走本地 whisper”的场景

### C. CLI dry-run 与 Web API 都开始回传 `transcript_text`

涉及文件：

- [`interview-audio-pipeline/src/interview_pipeline/cli.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/cli.py)
- [`interview-audio-pipeline/src/interview_pipeline/web.py`](/Users/chendingyu/my_project/interview-audio-pipeline/src/interview_pipeline/web.py)

新增效果：

- `interview-pipeline run --dry-run` 的 JSON 输出里会包含完整转写文本
- Web 端 `/api/run` 的返回结果里也会包含完整转写文本

意义：

- 前端或后续上层应用可以直接展示完整转写
- 不用再只拿摘要和 recommendation

### D. 新增本地联调脚本和视频工作流目录

涉及目录：

- [`scripts`](/Users/chendingyu/my_project/scripts)
- [`video`](/Users/chendingyu/my_project/video)

其中：

- `scripts/` 用于一键拉起三个本地服务
- `video/` 更偏内容生产，不是服务端应用

## 5. 当前工作区状态

根据 `git status --short`，当前有这些重要变更：

- 已修改：
  - `README.md`
  - `interview-audio-pipeline/src/interview_pipeline/cli.py`
  - `interview-audio-pipeline/src/interview_pipeline/pipeline.py`
  - `interview-audio-pipeline/src/interview_pipeline/web.py`
- 未跟踪：
  - `scripts/`
  - `video/`
  - `7.得到锦囊/`
  - `D08ktLBptioJkJANeJaiYF.zip`
  - `personal-ai-website-deploy.tar.gz`
  - `personal-ai-website/scripts/deploy-tencent.sh`

注意：

- 这些未跟踪内容里，`scripts/` 和 `video/` 看起来是有意新增的工作区内容
- 其余 zip / tar.gz 更像临时产物或部署包，后续要不要纳入版本控制需要再判断

## 6. 三个可运行服务怎么启动

统一启动：

```bash
cd /Users/chendingyu/my_project
./scripts/dev-stack.sh
```

单独启动：

```bash
./scripts/dev-personal-website.sh
./scripts/dev-interview-pipeline.sh
./scripts/dev-verbal-expression-coach.sh
```

默认本地地址：

- `personal-ai-website`: `http://127.0.0.1:3000`
- `interview-audio-pipeline`: `http://127.0.0.1:8787`
- `verbal-expression-coach`: `http://127.0.0.1:8000`

## 7. 其他子项目一句话说明

### personal-ai-website

技术栈：

- Next.js 16
- React 19
- TypeScript

定位：

- 个人 AI 站点
- 可作为另外两个工具的统一门户
- 文档和内容维护集中在 `data/`、`docs/`、`lib/`

优先阅读：

- [`personal-ai-website/README.md`](/Users/chendingyu/my_project/personal-ai-website/README.md)
- [`personal-ai-website/package.json`](/Users/chendingyu/my_project/personal-ai-website/package.json)
- [`personal-ai-website/docs/personal-website-prd.md`](/Users/chendingyu/my_project/personal-ai-website/docs/personal-website-prd.md)
- [`personal-ai-website/lib/wisdom-advisor.ts`](/Users/chendingyu/my_project/personal-ai-website/lib/wisdom-advisor.ts)

### verbal-expression-coach

技术栈：

- FastAPI / Uvicorn
- SQLite

定位：

- 视频表达模仿训练 MVP
- 当前分析逻辑还是占位版，后续应该补 ASR、特征提取、多模态分析

优先阅读：

- [`verbal-expression-coach/README.md`](/Users/chendingyu/my_project/verbal-expression-coach/README.md)
- [`verbal-expression-coach/app/main.py`](/Users/chendingyu/my_project/verbal-expression-coach/app/main.py)
- [`verbal-expression-coach/app/analyzer.py`](/Users/chendingyu/my_project/verbal-expression-coach/app/analyzer.py)

### video

定位：

- 一个短视频制作工作流目录
- 不是在线产品，而是模板、素材、项目管理结构

优先阅读：

- [`video/README.md`](/Users/chendingyu/my_project/video/README.md)

## 8. 下次继续时的推荐顺序

如果切到新账号后回来，建议按这个顺序恢复上下文：

1. 先看这份 [`PROJECT_HANDOFF.md`](/Users/chendingyu/my_project/PROJECT_HANDOFF.md)
2. 再看根目录 [`README.md`](/Users/chendingyu/my_project/README.md)
3. 把 `interview-audio-pipeline/README.md` 通读一遍
4. 看 `pipeline.py` 里最新的 URL 下载逻辑
5. 看 `cli.py` 和 `web.py` 里新增的 `transcript_text` 输出
6. 如果需要联调，再运行 `./scripts/dev-stack.sh`

## 9. 我对当前阶段的判断

这个工作区现在不是“从零开始”，而是已经形成了一个小型产品矩阵：

- 一个内容门户：`personal-ai-website`
- 一个较完整的音频处理工具：`interview-audio-pipeline`
- 一个训练型原型：`verbal-expression-coach`
- 一个内容生产工作流：`video`

其中成熟度最高、最值得优先继续推进的，仍然是 `interview-audio-pipeline`。

如果只能记住一句话：

当前主线是“把面试录音处理做成稳定可复用的本地工具和轻量产品”，最新进展是“本地 whisper 已经开始支持 URL 输入，CLI/Web 也补上了完整转写输出”。
