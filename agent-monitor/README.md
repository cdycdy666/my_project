# Agent Monitor

一个轻量 Web Dashboard，用来观察服务器上的个人 Agent 服务：

- `feishu-obsidian-capture`
- `feishu-reading-agent`
- `feishu-podcast-guide`

它只读 systemd 状态、timer、trace JSONL 和最近日志，不写入业务项目，也不接触真实密钥。

## 能看到什么

- 页面拆成 `总览 / 运行记录 / 架构视图 / 告警`，避免所有细节挤在一个屏幕里。
- 总览页只看服务状态、近期运行和需要留意的告警。
- 告警页单独集中展示错误级日志，不再挤占运行记录页。
- 三个服务是否 `active`。
- 最近运行记录、耗时、LLM 次数、工具次数、证据门通过/失败情况。
- 单次 trace 的执行链路：默认合并成语义步骤链，也可以切换到原始事件级 trace。
- 运行记录页可以收起步骤链，专心查看当前节点的输入、输出和原始数据。
- 点击任一链路节点后，可以查看该模块的结构化输入、输出、元信息和原始事件 JSON，类似 n8n 的节点执行详情。Inspector 会按字段拆开 `messages`、`request_payload`、`response_text`、`content`、`episodes`、`papers` 等内容，方便直接看每个模块吃进去什么、吐出来什么。新 trace 会尽量保留完整 LLM messages、模型回复、工具参数和工具结果。
- Inspector 支持 `Summary / Input / Output / Prompt / Meta / Raw` 标签页；LLM 节点会单独展示 prompt messages。
- Obsidian Capture 目前没有结构化 trace，所以第一版展示服务健康和最近日志事件。

## 本地运行

```bash
cd /Users/chendingyu/my_project/agent-monitor
python3 run.py
```

默认监听：

```text
http://127.0.0.1:8769
```

本地没有 `/opt/<project>` 时，页面会显示服务未知或无运行记录。可以通过环境变量改读取根目录：

```bash
AGENT_MONITOR_ROOT_PREFIX=/Users/chendingyu/my_project python3 run.py
```

## 服务器部署

部署目录：

```text
/opt/agent-monitor
```

systemd 模板：

```text
deploy/agent-monitor.service
```

推荐只监听 `127.0.0.1`，通过 SSH 隧道访问：

```bash
ssh -L 8769:127.0.0.1:8769 root@123.57.229.149
```

然后打开：

```text
http://127.0.0.1:8769
```

## 后续增强

- 给 `feishu-obsidian-capture` 增加结构化 trace。
- 增加按 `trace_id` 的耗时瀑布图。
- 聚合 token usage 和模型成本。
- 增加简单告警：服务不 active、最近任务失败、证据门连续失败。
