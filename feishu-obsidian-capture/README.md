# Feishu Obsidian Capture

本地飞书机器人每日整理任务读取统一配置文件：

```text
/Users/chendingyu/my_project/.env
```

不要把 `.env` 提交到 Git。子目录不再放真实密钥。

## 配置

在 `/Users/chendingyu/my_project/.env` 里维护飞书、Obsidian 和模型配置：

```env
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OBSIDIAN_VAULT_DIR=/Users/chendingyu/my_project/personal-kb
DAILY_MORNING_TIME=07:30
DAILY_SUMMARY_TIME=23:00
LLM_API_KEY=sk-...
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.7-max
```

## 手动运行

```bash
cd /Users/chendingyu/my_project/feishu-obsidian-capture
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/run_daily_summary.py
```

首次绑定 chat_id 时，可以临时运行长连接服务：

```bash
./.venv/bin/python run.py
```

然后在飞书里给机器人发送：

```text
绑定
```

常驻监听服务负责接收飞书消息、保存原始记录，并调用模型即时反馈。每天定时任务会拉取机器人单聊当天历史消息，写入原始 inbox：

```text
00-inbox/feishu/YYYY-MM-DD.md
```

即时反馈支持轻量“记录会话”：

- 对任务完成、判断、问题发现等记录，模型会判断是否缺少结果反馈、验证方式、判断依据或下一步。
- 如果需要补充，机器人会追问一个关键问题，并在 `state.json` 中保留当前 active session。
- 用户下一条回复如果是在回答追问，会作为同一记录会话的“用户补充”写入 inbox。
- 发送「完成」「先这样」可结束当前记录会话；发送「新记录：...」可强制开启新事件。
- 晚间整理时，AI 追问只作为上下文，不会被当作用户事实写入 daily note。
- 每条用户原文会带稳定的 `record_id`；同一轮追问与补充共享 `session_id`。

每天 `DAILY_SUMMARY_TIME` 会调用模型整理当天全部历史记录，并写入：

```text
10-daily/YYYY/YYYY-MM-DD.md
```

整理后的 daily note 包含：

- 今日概览
- 按事件/主题分组的复盘
- 每个事件下的发生了什么、处理、判断、判断依据、结果反馈、后续动作和值得沉淀
- 零散记录
- 给 AI 的长期上下文
- 原始记录

## GAM-lite 记忆链

晚间整理采用“轻量记忆 + 完整原文 + 按需回读”的方式：

```text
飞书原文（record_id/session_id）
  -> daily note 事件（隐藏 sources 引用）
  -> 90-context/memory-index/YYYY-MM-DD.json
  -> 其他 Agent 先查索引，再按 source_pages/source_record_ids 回读原文
```

`memory-index` 会在 daily note 写入后自动生成，并在同一次 Git commit/push 中备份。索引失败不会覆盖或删除已写入的 daily note，日志会保留失败原因。
事件来源使用 Obsidian HTML 注释保存；飞书“整理完成”消息会隐藏这些机器元数据，只展示可读正文。

手动补跑指定日期：

```bash
./.venv/bin/python scripts/run_daily_summary.py --date 2026-06-30
```

## 每日定时任务

安装 macOS 定时任务：

```bash
cd /Users/chendingyu/my_project/feishu-obsidian-capture
./.venv/bin/python scripts/install_launch_agent.py
```

该任务只会在对应时间点运行一次：

- `DAILY_MORNING_TIME`：读取最近 Obsidian 记录，生成飞书早晨提醒
- `DAILY_SUMMARY_TIME`：拉取当天飞书历史消息，整理并写入 Obsidian

Git 同步策略：

- 常驻监听服务启动时：`git pull` 一次
- 晚间整理写入后：`git add . && git commit && git push`
- 早间提醒和晚间整理开始前不再额外 `git pull`

早晨提醒任务会先检查前一天是否已经整理；如果前一天没有 daily note，也没有完成状态记录，会先补跑前一天的晚间整理，再发送当天早晨提醒。

日志位置：

```text
/Users/chendingyu/my_project/feishu-obsidian-capture/logs/
```
