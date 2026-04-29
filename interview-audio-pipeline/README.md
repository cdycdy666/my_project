# Interview Audio Pipeline

把“面试录音处理”做成一条独立、可复用的自动化链路：

`本地音频 / 录音 URL -> 转写 -> 结构化面评 -> Notion 面试库`

## 当前 MVP 能力

- 输入单条录音及基础元数据
- 默认使用本地 `faster-whisper` 做转写
- 保留可选的百度千帆 `media-insight` provider
- 支持火山引擎 `豆包语音妙记` provider
- 支持直接传入录音 URL
- 支持本地音频先上传到 BOS，再生成临时可下载 URL 作为留档链接
- 规范化提取转写、摘要、要点、篇章结果
- 生成面试专用结构化输出
- 转写完成后创建一条 Notion 复盘记录
- 把完整内容写进 Notion 页面正文

## 目录结构

```text
.
├── .env.example
├── pyproject.toml
├── README.md
└── src/interview_pipeline
    ├── cli.py
    ├── config.py
    ├── formatter.py
    ├── http.py
    ├── mcp_client.py
    ├── models.py
    ├── notion_client.py
    └── qianfan_media_insight.py
```

## 环境准备

1. 使用 Python 3.9+
2. 复制 `.env.example` 为 `.env`
3. 填入：
   - `TRANSCRIPTION_PROVIDER`
   - `QIANFAN_BEARER_TOKEN`
   - `NOTION_TOKEN`
   - `NOTION_DATABASE_ID`
   - 各个 `NOTION_PROP_*` 字段名
   - 如果值外面带了单引号或双引号，当前版本会自动去掉

安装方式：

```bash
python3 -m pip install -e .
```

如果你准备使用本地文件上传 BOS，这一步会一并安装官方 `bce-python-sdk`。

## 使用方式

`--candidate` 现在是可选项。如果不传，程序会默认用音频文件名，或 `日期_轮次` 生成一个中性标题，适合个人复盘场景。

`--role / --round / --date` 也都可以省略：

- `round` 会优先从文件名里识别，比如 `一面 / 二面 / 三面 / 终面 / HR面`
- `date` 会优先从文件名里的 `0325 / 0410` 这类片段推断为当年日期
- 推不出来时，会回退成 `待补充` 或当天日期

所以最省事的用法已经可以变成只传一个音频文件：

```bash
interview-pipeline run \
  --audio-file "/path/to/字节一面_0325.m4a" \
  --dry-run
```

如果你想更像产品一点，而不是一直在命令行里跑参数，也可以直接启动本地前端：

```bash
interview-pipeline web
```

然后打开 [http://127.0.0.1:8787](http://127.0.0.1:8787)。

这个前端支持：

- 直接拖拽本地音频文件
- 自动推断日期和轮次
- 可选写入 Notion
- 处理完成后直接展示摘要、结构化页面草稿和模拟复盘草稿

如果你走本地转写，最常用的是：

```bash
interview-pipeline run \
  --audio-file "/path/to/interview.m4a" \
  --role "后端工程师" \
  --round "一面" \
  --date "2026-04-25" \
  --dry-run
```

如果你切回千帆 provider，再先检查千帆 MCP 暴露了哪些工具，以及当前程序会自动选哪几个：

```bash
interview-pipeline inspect-mcp
```

再检查 Notion 面试库字段是否真的和 `.env` 里的映射一致：

```bash
interview-pipeline inspect-notion
```

如果你准备走本地文件上传 BOS，可以先单独测试上传：

```bash
interview-pipeline upload-bos \
  --audio-file "/path/to/interview.mp3"
```

确认配置都没问题后，再做一次不写 Notion 的演练。`--dry-run` 不要求 Notion 配置：

```bash
interview-pipeline run \
  --audio-url "https://example.com/interview.mp3" \
  --role "后端工程师" \
  --round "一面" \
  --date "2026-04-25" \
  --dry-run
```

也可以直接传本地文件：

```bash
interview-pipeline run \
  --audio-file "/path/to/interview.mp3" \
  --role "后端工程师" \
  --round "一面" \
  --date "2026-04-25" \
  --dry-run
```

确认无误后，去掉 `--dry-run` 即可真正写入 Notion：

```bash
interview-pipeline run \
  --audio-url "https://example.com/interview.mp3" \
  --role "后端工程师" \
  --round "一面" \
  --date "2026-04-25"
```

## 配置说明

### 转写 Provider

项目现在支持两种转写方式：

- `TRANSCRIPTION_PROVIDER=local_whisper`
- `TRANSCRIPTION_PROVIDER=qianfan`
- `TRANSCRIPTION_PROVIDER=doubao_miaoji`

默认值是 `local_whisper`。

推荐：

- 如果你要稳定可用的个人复盘工具，优先用 `local_whisper`
- 如果你后面确认千帆权限和配额都稳定，再切回 `qianfan`
- 如果你后面切到火山引擎 `豆包语音妙记`，推荐模块组合是：
  - `语音转写`
  - `全文总结`
  - `章节总结`
  - `问答提取`

这套组合最贴近“面试复盘”场景：

- `全文总结` 适合直接写入 Notion 的 `摘要`
- `章节总结` 适合恢复一场面试的结构
- `问答提取` 适合回看关键追问与回答质量

### Local Whisper

本地转写依赖 `faster-whisper`，默认配置：

- `LOCAL_WHISPER_MODEL=small`
- `LOCAL_WHISPER_DEVICE=auto`
- `LOCAL_WHISPER_COMPUTE_TYPE=auto`
- `LOCAL_WHISPER_LANGUAGE=zh`
- `LOCAL_WHISPER_BEAM_SIZE=5`
- `LOCAL_WHISPER_VAD_FILTER=true`

说明：

- `local_whisper` 当前要求传 `--audio-file`
- 如果同时配置了 BOS，程序会把本地录音上传到 BOS，方便在 Notion 里保留可点击链接
- 本地转写阶段不依赖千帆权限，也不会受千帆工具限流影响

### 千帆 MCP

项目直接对接 Streamable HTTP MCP，不依赖百度网盘“简单听记”页面。

默认配置：

- `QIANFAN_MCP_URL=https://qianfan.baidubce.com/v2/tools/media-insight/mcp`
- `QIANFAN_MCP_PROTOCOL_VERSION=2025-06-18`

工具发现策略：

- 优先使用 `QIANFAN_CREATE_TOOL` / `QIANFAN_STATUS_TOOL` / `QIANFAN_RESULT_TOOL`
- 未配置时，会根据 `tools/list` 返回的名称和描述做关键字匹配
- 如果当前环境存在公司代理、系统代理或 `HTTP_PROXY` / `HTTPS_PROXY`，可通过 `QIANFAN_DISABLE_PROXY=true` 让千帆请求直连

因为不同 MCP 服务端的工具名和字段名可能略有不同，第一版做了两层兜底：

- 任务提交时自动寻找 `url` / `audio_url` / `media_url` / `file_url` 等字段
- 结果解析时递归提取 `task_id` / `status` / `summary` / `transcript` / `segments` 等常见键

如果千帆端的真实工具名与当前启发式不一致，请把它们显式写进 `.env`。

`inspect-mcp` 会输出：

- MCP 返回的全部工具
- 每个工具的 `input_schema`
- 当前自动选中的 `create/status/result` 工具

### 豆包语音妙记

项目支持把火山引擎 `豆包语音妙记` 作为新的主转写 provider。当前接入方式基于官方文档中公开的：

- 提交接口：`POST https://openspeech.bytedance.com/api/v3/auc/lark/submit`
- 查询接口：`POST https://openspeech.bytedance.com/api/v3/auc/lark/query`
- 资源 ID：`volc.lark.minutes`

建议配置：

- `TRANSCRIPTION_PROVIDER=doubao_miaoji`
- `DOUBAO_MIAOJI_API_KEY`
- `DOUBAO_MIAOJI_APP_KEY`
- `DOUBAO_MIAOJI_ACCESS_KEY`
- `DOUBAO_MIAOJI_RESOURCE_ID=volc.lark.minutes`

推荐模块组合：

- `DOUBAO_MIAOJI_AUDIO_TRANSCRIPTION_ENABLE=true`
- `DOUBAO_MIAOJI_SUMMARIZATION_ENABLE=true`
- `DOUBAO_MIAOJI_SUMMARIZATION_TYPES=summary`
- `DOUBAO_MIAOJI_CHAPTER_ENABLE=true`
- `DOUBAO_MIAOJI_INFORMATION_EXTRACTION_ENABLE=true`
- `DOUBAO_MIAOJI_INFORMATION_EXTRACTION_TYPES=question_answer`

说明：

- 这套组合最贴近“个人面试复盘”场景
- `AllActivate=false` 时按具体能力组合计费，更适合作为 MVP 起步
- 新版控制台优先使用 `DOUBAO_MIAOJI_API_KEY`，旧版控制台再使用 `DOUBAO_MIAOJI_APP_KEY + DOUBAO_MIAOJI_ACCESS_KEY`
- provider 当前默认走 `audio_url`，因此推荐搭配 BOS 使用
- 你的原始文件如果是 `.m4a`，建议先转成 `wav` 或 `mp3` 再交给火山链路，以降低格式兼容风险

### BOS

如果你传的是本地文件而不是 URL，项目会先上传到 BOS，再生成一个带时效的下载链接，用于 Notion 留档或千帆拉取。

需要的配置如下：

- `BOS_ACCESS_KEY_ID`
- `BOS_SECRET_ACCESS_KEY`
- `BOS_BUCKET`
- `BOS_ENDPOINT`
- `BOS_OBJECT_PREFIX`
- `BOS_SIGNED_URL_EXPIRES`
- `BOS_MULTIPART_THRESHOLD_MB`
- `BOS_MULTIPART_CHUNK_MB`

默认行为：

- `BOS_ENDPOINT=bj.bcebos.com`
- `BOS_OBJECT_PREFIX=interview-audio`
- `BOS_SIGNED_URL_EXPIRES=86400`
- `BOS_MULTIPART_THRESHOLD_MB=8`
- `BOS_MULTIPART_CHUNK_MB=5`
- `BOS_DISABLE_PROXY=true`

说明：

- 这版 BOS 上传已经切到官方 `bce-python-sdk`
- 当前使用官方 SDK 上传和签名 URL 能力，适合 MVP 阶段的单条录音处理
- 默认会在文件大于 8MB 时自动切到 multipart 上传
- 预签名 URL 默认有效期 24 小时，适合交给千帆拉取
- 如果你希望 Notion 里的录音链接长期可点开，需要调整有效期策略或改成公开读方案

### Notion

第一版采用 Notion REST API，默认版本是 `2022-06-28`，便于直接写入既有 database。

这版定位是“个人复盘沉淀”，不是流程管理工具，所以默认只在处理完成后创建记录。
如果你的库里保留了 `处理状态` 字段，程序会默认写入 `DEFAULT_STATUS_DONE`，当前建议值是 `完成`。

建议数据库字段至少包含：

- 候选人
- 岗位
- 面试日期
- 轮次
- 处理状态
- 录音链接
- 转写链接
- 结论
- 标签
- 摘要

页面正文会写入：

- AI纪要
- 结构化面评
- 篇章规整
- 完整转写

`inspect-notion` 会输出：

- 数据库标题和 URL
- 当前全部属性及类型
- `.env` 中每个 `NOTION_PROP_*` 是否存在、实际类型是什么

## 输出设计

结构化面评当前字段：

- 候选人
- 岗位
- 面试日期
- 轮次
- 摘要
- 亮点
- 风险点
- 待确认问题
- 结论建议
- 完整转写正文

当前“面评整理”是一个偏保守的 MVP：

- 优先复用 media-insight 的摘要、要点、篇章结果
- 对缺失字段提供默认兜底文案
- `结论` 会自动收敛到 `强推 / 推荐 / 待定 / 不推荐` 其中之一，默认偏保守

这保证首版可落地，但不会假装替代人工面试判断。

## 风险与约束

- `local_whisper` 当前更适合单条录音处理，不是批量高并发方案
- 如果传本地文件并希望在 Notion 里保留可访问链接，建议配置 BOS
- 网盘分享链接未必是真直链，建议使用对象存储签名 URL
- 千帆 provider 仍受平台权限、计费和限流影响
- 面试录音涉及隐私，建议使用短时效授权链接
- Bearer Token、AK/SK 和 Notion Token 只能通过配置注入，不要硬编码

## 下一步建议

- 先用 `local_whisper` 跑通一条真实录音
- 再运行 `inspect-notion`
- 如果走本地文件留档，再运行一次 `upload-bos`
- 确认 Notion 库字段类型和命名完全匹配
- 后续再补更强的摘要/面评逻辑，或把千帆保留成备选 provider
