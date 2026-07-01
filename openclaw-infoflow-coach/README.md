# OpenClaw InfoFlow Coach

本仓库是如流群聊沟通教练的干净备份版。它把 OpenClaw 捕获到的如流群聊记录导出为 Markdown，再结合沟通原则卡片和参考资料，生成晚间沟通建议，并可发送回指定如流群。

## 当前目标

- 只分析指定如流群：`12829093`
- 重点关注：`chendingyu` 和 `linbeike`
- 白天由 OpenClaw 负责群聊接入和即时回复
- 晚上由脚本导出当天记录、调用大模型分析、保存建议并发回群

## 目录结构

```text
scripts/
  export_openclaw_infoflow_logs.py          # 从 OpenClaw 本地记录导出群聊 Markdown
  analyze_openclaw_infoflow_communication.py # 读取聊天记录和参考资料，生成沟通建议
  nightly_openclaw_infoflow_coach.sh        # 晚间总入口：导出 -> 分析 -> 发群
  install_openclaw_infoflow_log_exporter.sh # 安装 macOS LaunchAgent 定时任务

feishu-communication-coach/
  feishu_communication_coach/
    llm.py                                  # OpenAI-compatible 大模型调用封装
    references.py                           # 参考资料检索
  reference-notes/
    communication-principle-cards.md        # 人类可读原则卡片
    communication-principle-cards.json      # 结构化原则卡片
  references/
    README.md                               # 参考资料放置说明
```

## 不备份的内容

以下内容默认不提交：

- `.env`
- OpenClaw 配置里的密钥
- `openclaw-infoflow-logs/`
- `openclaw-infoflow-advice/`
- `feishu-communication-coach/references/` 中的完整书籍或私人资料

## 运行前提

本地需要已经安装并配置 OpenClaw，如流 channel 可以正常连接，并且本机存在：

```text
~/.openclaw/openclaw.json
~/.openclaw/plugins/infoflow-private/tasks/
~/.openclaw/agents/main/sessions/
/tmp/openclaw/
```

如果不希望脚本读取 `~/.openclaw/openclaw.json` 里的模型配置，可以复制 `.env.example` 为 `.env` 后填写 `LLM_*`。

## 手动导出当天记录

```bash
python3 scripts/export_openclaw_infoflow_logs.py --date "$(date +%F)"
```

输出：

```text
openclaw-infoflow-logs/YYYY-MM-DD.md
```

## 手动生成沟通建议

```bash
python3 scripts/analyze_openclaw_infoflow_communication.py \
  --date "$(date +%F)" \
  --group-id "12829093" \
  --focus-user "chendingyu" \
  --focus-user "linbeike"
```

输出：

```text
openclaw-infoflow-advice/YYYY-MM-DD.md
```

如果要同时发回如流群：

```bash
python3 scripts/analyze_openclaw_infoflow_communication.py \
  --date "$(date +%F)" \
  --group-id "12829093" \
  --focus-user "chendingyu" \
  --focus-user "linbeike" \
  --send-to-group
```

## 晚间定时任务

安装 LaunchAgent：

```bash
bash scripts/install_openclaw_infoflow_log_exporter.sh
```

当前默认每天 `20:00` 执行：

```text
scripts/nightly_openclaw_infoflow_coach.sh
```

## 核心分析逻辑

分析脚本会先构造重点聊天记录，只保留重点对象的发言；完整背景记录只作为上下文参考。

如果一天里有多个不相关话题，模型会先做话题分组，再挑 1-2 个最有沟通价值的话题深入分析，避免把一天的流水账平均点评。

沟通建议优先使用：

```text
feishu-communication-coach/reference-notes/communication-principle-cards.md
```

参考书库只作为补充材料：

```text
feishu-communication-coach/references/
```
