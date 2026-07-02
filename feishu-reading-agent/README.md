# Feishu Reading Agent

一个独立的飞书读书智能体。它读取 `personal-kb` 里的个人处境作为重要参考，再结合微信读书书架等阅读线索，给出更贴近当前状态的低门槛阅读动作、陪读问题和读后沉淀提示。

推荐范围不局限于微信读书书架。书架只是判断用户已有兴趣和可立即打开阅读内容的线索；如果书架外有更合适的书、文章、概念或阅读主题，智能体也可以推荐，并明确标注“书架外”。

默认推荐单位不是“一整本书”，而是一个轻量阅读动作：一章、一节、一段、一个概念、一个关键词搜索，或者一个 10-20 分钟的问题式阅读任务。即使推荐书架外的书，也要尽量精确到章节、小节、概念或可搜索短语，不能只丢一个书名。

涉及具体书名和章节位置时，智能体会先用微信读书搜索和目录接口做验证。能查到目录时，才推荐具体章节或小节；查不到时，不编造章节号，只推荐可搜索关键词或概念。

微信读书 skill 当前不提供整章正文或全文读取接口。智能体会额外尝试读取热门划线、公开点评、你的个人划线和想法作为片段证据，并在推荐里标注依据，例如“目录已验证”“热门划线佐证”“公开点评佐证”“你的划线/想法佐证”或“正文未验证，仅建议关键词搜索”。目录只能证明位置存在，不能证明章节内容已经被完整阅读。

飞书回复默认使用手机友好的纯文本格式：先给一句结论，再给“读什么 / 怎么读 / 为什么现在 / 依据 / 读后回收”。回复会避免 Markdown 加粗、复杂标题和表格，便于在飞书里快速扫读。

它和 `feishu-obsidian-capture` 是两个项目：

- `feishu-obsidian-capture`：记录处境，整理进 Obsidian。
- `feishu-reading-agent`：读取处境，结合微信读书做阅读对话。

它只读 `personal-kb`，不写入 daily note。除手动触发外，服务器上可以配置每周六定时主动发送一次读书建议。

## 配置

本项目读取统一配置文件：

```text
/Users/chendingyu/my_project/.env
```

新增读书机器人相关配置：

```env
READING_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
READING_FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
READING_FEISHU_VERIFICATION_TOKEN=
READING_FEISHU_ENCRYPT_KEY=

READING_PERSONAL_KB_DIR=/Users/chendingyu/my_project/personal-kb
WEREAD_API_KEY=wrk-...

READING_LLM_API_KEY=sk-...
READING_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
READING_LLM_MODEL=qwen-plus

READING_TRACE_LOG_ENABLED=true
READING_TRACE_LOG_DIR=/Users/chendingyu/my_project/feishu-reading-agent/logs/traces
```

如果不配置 `READING_LLM_*`，会复用根 `.env` 里的 `LLM_*`。

`READING_TRACE_LOG_ENABLED` 默认开启。追踪日志不会记录 API Key，会记录每次回复的 `trace_id`、用户消息、模型调用摘要、微信读书接口摘要、检索结果、证据上下文预览和最终回复，方便后续改进检索与提示词。

## 本地安装

```bash
cd /Users/chendingyu/my_project/feishu-reading-agent
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## 手动检查微信读书

```bash
./.venv/bin/python scripts/check_weread.py
```

成功后会显示 gateway 可用接口数量和书架摘要。

## 本地问一次

不启动飞书机器人，直接在终端模拟一次对话：

```bash
./.venv/bin/python scripts/chat_once.py 推荐阅读
```

也可以问：

```bash
./.venv/bin/python scripts/chat_once.py 这本书适合我现在读吗：掌控谈话
./.venv/bin/python scripts/chat_once.py 读完了：我意识到谈判里先标注对方情绪很重要
./.venv/bin/python scripts/chat_once.py 书架
```

## 启动飞书机器人

先在飞书开放平台创建一个新的自建应用机器人，不复用 Obsidian Capture 的应用。权限和事件配置可以参考旧机器人：

- 启用机器人能力。
- 开启长连接事件订阅。
- 订阅 `im.message.receive_v1`。
- 添加接收消息相关权限。
- 发布应用。

然后本地启动：

```bash
./.venv/bin/python run.py
```

在飞书里给新机器人发送：

```text
绑定
```

之后可发送：

```text
推荐阅读
换一本
书架
这本书适合我现在读吗：掌控谈话
读完了：……
```

## 每周六定时推荐

服务器部署后，可以用 cron 每周六主动发送一次读书建议。默认建议时间是周六上午 9:30：

```cron
30 9 * * 6 root cd /opt/feishu-reading-agent && flock -n /tmp/feishu-reading-agent-weekly.lock .venv/bin/python scripts/send_once.py 推荐阅读 >> /opt/feishu-reading-agent/logs/weekly.log 2>&1
```

这个任务会发送到最近一次给机器人发过消息、或发送过“绑定”的飞书会话。首次使用前，需要先在飞书里给机器人发一次：

```text
绑定
```

## 交互追踪日志

每次读书回复都会写入一组 JSONL 追踪事件：

```text
logs/traces/YYYY-MM-DD.jsonl
```

服务器部署后默认在：

```text
/opt/feishu-reading-agent/logs/traces/YYYY-MM-DD.jsonl
```

可以这样查看最近一次推荐的链路：

```bash
tail -n 80 /opt/feishu-reading-agent/logs/traces/$(date +%F).jsonl
```

初期为了分析检索词、证据链和回复质量，`logs/traces/*.jsonl` 可以提交到 private GitHub。它不包含 API Key，但会包含用户消息、检索词、证据上下文预览和最终回复，后续如果觉得敏感或量变大，可以再改为只在服务器保留。

每行都有同一个 `trace_id`，可以串起：

- `reply_start`：收到的用户消息
- `llm_request` / `llm_response`：模型调用类型、模型名、输入长度、耗时
- `material_queries`：模型生成的微信读书检索词
- `weread_request` / `weread_response`：微信读书接口、参数摘要、返回摘要、耗时
- `material_search_results`：每个 query 命中的书
- `verified_materials_context`：最终给模型的证据上下文预览
- `final_reply`：最终发给飞书的回复

## 当前边界

- 不修改 `personal-kb`。
- 不修改 `feishu-obsidian-capture`。
- 不把微信读书 key、飞书 secret 或模型 key 提交到 Git。
- 不提交 `state.json`、`.venv/`、`*.log` 或 `.env`。
- 部署模板在 `deploy/` 目录；真实配置仍以服务器 `/etc/systemd/system/feishu-reading-agent.service`、`/etc/cron.d/feishu-reading-agent` 和 `/opt/.env` 为准。
- 服务器部署后建议使用 `/opt/feishu-reading-agent`，并读取 `/opt/.env`。
