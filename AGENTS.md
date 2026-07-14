# My Project Agent Guide

这是给 Codex/Claude/其他编码智能体看的根目录操作手册。目标是防止多个个人自动化项目混在一起，降低每次接手时的上下文成本。

## 总原则

- 根目录统一配置文件是 `/Users/chendingyu/my_project/.env`，不要把真实密钥提交到 Git。
- 不要混用不同飞书/如流机器人。先确认用户当前说的是哪个项目，再改代码或查日志。
- 服务器主要是 `root@123.57.229.149`，长期服务通常部署在 `/opt/<project-name>`。
- 本地仓库有很多未提交改动，提交时只 stage 当前任务相关文件。
- 运行或部署前优先看对应项目 `README.md`。
- 如果涉及飞书机器人配置，优先参考 `skills/feishu-bot-configuration/SKILL.md`。
- 如果涉及“聊天机器人 + 定时任务 + LLM + 文件沉淀”，优先参考 `skills/lightweight-bot-automation/SKILL.md`。

## AGENTS.md 更新原则

- 只记录跨项目协作时稳定、反复会用到、容易搞混或可能造成损失的信息。
- 优先写项目边界、部署位置、关键数据流、常用排查入口和提交/部署习惯。
- 不写临时过程、一次性实验、单次 trace 结论或过细实现细节。
- 详细架构、prompt 设计和运行说明放到各项目自己的 `README.md` 或项目文档里。
- 新增长期项目、项目职责变化、部署路径变化、核心数据流变化、踩过且可能复发的坑时，再更新本文件。
- 不写真实密钥、token、cookie、私人日志原文等敏感内容。

## 核心项目

### 1. Obsidian 个人处境知识库

目录：

```text
personal-kb/
```

用途：

- 沉淀每天遇到的问题、处理过程、判断、判断依据、结果反馈和经验。
- 给其他 Agent 提供“用户当前处境”的长期上下文。

关键目录：

```text
personal-kb/10-daily/
personal-kb/90-context/
personal-kb/templates/
```

边界：

- 它是知识库，不是服务代码。
- 其他项目可以读取它作为上下文，但不要随意写入，除非任务明确要求写 daily note 或更新 context。

常看文件：

```text
personal-kb/README.md
personal-kb/90-context/
```

### 2. 飞书 -> Obsidian 自动记录服务

目录：

```text
feishu-obsidian-capture/
```

服务器部署：

```text
/opt/feishu-obsidian-capture
```

用途：

- 飞书机器人接收日常零散记录。
- 即时给一点 LLM 反馈。
- 晚上定时拉取/整理当天飞书记录。
- 写入 `personal-kb/10-daily/YYYY/YYYY-MM-DD.md`。
- 为原始记录写入 `record_id/session_id`，并在晚间整理后自动生成当天 `90-context/memory-index/*.json`。

当前设计：

- 常驻监听：接收飞书消息、保存原始记录、即时反馈。
- 定时任务：早晨提醒、晚间整理、必要时补跑前一天。
- 记忆链：完整原文保存在 inbox/daily note，轻量索引保存事件与 `source_pages/source_record_ids`，供其他 Agent 按需回读。
- 服务端是主要运行环境，本地主要用于开发和备份。

重要边界：

- 这个项目负责“记录和整理处境”。
- 不负责读书推荐。
- 不负责沟通教练分析。
- 不要和 `feishu-reading-agent` 共用飞书 App 配置。

常用检查：

```bash
ssh root@123.57.229.149 "systemctl status feishu-obsidian-capture.service --no-pager"
ssh root@123.57.229.149 "tail -n 80 /opt/feishu-obsidian-capture/logs/service.err.log"
```

### 3. 如流 / OpenClaw 沟通教练

主目录：

```text
openclaw-infoflow-coach/
```

运行数据目录：

```text
openclaw-infoflow-logs/
openclaw-infoflow-advice/
```

用途：

- OpenClaw 接入如流机器人。
- 导出指定如流群聊记录。
- 重点分析 `chendingyu` 和 `linbeike` 的沟通。
- 每天 20:00 分析过去 24 小时，并把建议发回指定如流群。

当前目标群：

```text
12829093
```

核心脚本：

```text
openclaw-infoflow-coach/scripts/export_openclaw_infoflow_logs.py
openclaw-infoflow-coach/scripts/analyze_openclaw_infoflow_communication.py
openclaw-infoflow-coach/scripts/nightly_openclaw_infoflow_coach.sh
```

参考资料：

```text
openclaw-infoflow-coach/feishu-communication-coach/reference-notes/
openclaw-infoflow-coach/feishu-communication-coach/references/
```

重要边界：

- 这是“沟通建议/关系互动复盘”项目，不是 Obsidian 记录服务。
- 只分析指定群和重点对象，不要默认导出所有如流群。
- `openclaw-infoflow-logs/` 和 `openclaw-infoflow-advice/` 是运行数据，是否提交要谨慎。

常用命令：

```bash
cd /Users/chendingyu/my_project/openclaw-infoflow-coach
python3 scripts/export_openclaw_infoflow_logs.py --date "$(date +%F)" --window-hours 24
python3 scripts/analyze_openclaw_infoflow_communication.py --date "$(date +%F)" --group-id "12829093" --focus-user "chendingyu" --focus-user "linbeike"
```

### 4. 飞书阅读智能体

目录：

```text
feishu-reading-agent/
```

服务器部署：

```text
/opt/feishu-reading-agent
```

用途：

- 独立飞书读书机器人。
- 读取 `personal-kb` 作为个人处境上下文。
- 调用微信读书 skill/API 获取书架、搜索、目录、热门划线、公开点评、个人划线/想法。
- 给出低门槛、处境驱动的阅读建议。

当前推荐流程：

```text
用户消息
  -> Personal Memory Researcher 规划历史检索 query
  -> BM25 + Embedding 检索 memory-index
  -> RRF 融合后按 Page-ID/record-ID 回读原文
  -> 必要时补查一轮，形成处境摘要和证据
  -> 默认不读取微信读书书架
  -> LLM 生成 material_queries
  -> 微信读书验证
  -> 根据 source_pages 回读少量 daily note 原文片段
  -> LLM 做 evidence_aware_material_scoring
  -> LLM 服从打分结果生成最终回复
  -> final_reply_material_check 校验是否引入未验证材料
  -> 如有未验证材料，再补查并重写最终回复
  -> 最终飞书回复
```

关键约束：

- 推荐范围不局限书架。
- 默认不推荐整本书，而是推荐 10-20 分钟的阅读动作。
- 具体章节必须先经微信读书目录验证。
- 微信读书不提供全文；目录只能证明位置存在。
- 热门划线、公开点评、个人笔记只是片段证据。
- 最终回复必须服从候选材料打分结果；默认只输出 1 个方案。
- 默认不读取微信读书书架，除非用户明确要求从书架里推荐或检查书架。
- 它只读 `personal-kb`，不写 daily note。
- 读取 schema v2 memory-index 时，会先用轻量事件摘要定位，再按 `source_record_ids` 精确回读对应飞书原文；旧索引仍按整页回读兼容。
- 个人记忆检索由 `personal-memory-researcher` 提供；向量接口失败时降级为 BM25 + Page-ID，不应阻断机器人回复。

常用命令：

```bash
cd /Users/chendingyu/my_project/feishu-reading-agent
./.venv/bin/python scripts/check_weread.py
./.venv/bin/python scripts/chat_once.py 推荐阅读
```

服务器检查：

```bash
ssh root@123.57.229.149 "systemctl is-active feishu-reading-agent.service"
ssh root@123.57.229.149 "tail -n 80 /opt/feishu-reading-agent/logs/traces/$(date +%F).jsonl"
```

重要边界：

- 不修改 `feishu-obsidian-capture`。
- 不写入 `personal-kb`。
- 不把 `WEREAD_API_KEY`、飞书 secret、模型 key、`state.json`、`.env` 提交到 Git。

### 4a. Personal Memory Researcher

目录：

```text
personal-memory-researcher/
```

用途：

- 只读检索 `personal-kb/90-context/memory-index/`。
- 同时使用本地 BM25、Embedding 语义检索和 Page-ID/record-ID 原文回读。
- 对检索证据做最多两轮的规划与充分性反思，输出可追溯的记忆摘要和原文证据。
- 当前由 `feishu-reading-agent` 调用，后续其他 Agent 可以复用，不直接生成业务回复。

重要边界：

- 不写 `personal-kb`；Embedding 缓存保存在调用方的 `data/` 目录。
- Embedding 只发送 memory-index 轻量事件文本，不直接向量化整篇 daily note/inbox；Page-ID 原文回读在本地完成。
- Embedding 失败必须保留 BM25 + Page-ID 降级链路。
- trace 应保留 query、BM25/Embedding 命中、融合排序和回读证据，但不能记录 API Key。

### 5. 飞书播客 / 论文学习陪练

目录：

```text
feishu-podcast-guide/
```

服务器部署：

```text
/opt/feishu-podcast-guide
```

用途：

- 独立飞书播客学习机器人，机器人名建议为 `研几`。
- 以「AI可可AI生活」RSS 和 Agent/RL 学习路径为材料入口。
- 帮用户选择该听哪几集、给听前抓手、做听后复盘和项目映射。
- 论文模式支持 arXiv 搜索、PDF 解析缓存和技术细节拆解。
- 每日 08:30 可主动推送 1 集，并按主题轮换征询。

重要边界：

- 播客侧不读取音频全文，不做二次长摘要。
- 论文侧第一版只支持 arXiv；PDF 缓存是运行数据，不提交 Git。
- 不读取或写入 `personal-kb`，不要和 `feishu-reading-agent` 混用。
- 改动 LLM planner、工具循环、论文检索或证据门后，要查看 `logs/traces/*.jsonl`。

常用检查：

```bash
ssh root@123.57.229.149 "systemctl status feishu-podcast-guide.service --no-pager"
ssh root@123.57.229.149 "systemctl list-timers --all | grep feishu-podcast-guide"
ssh root@123.57.229.149 "tail -n 80 /opt/feishu-podcast-guide/logs/traces/$(date +%F).jsonl"
```

### 6. Agent Monitor Dashboard

目录：

```text
agent-monitor/
```

服务器部署：

```text
/opt/agent-monitor
```

用途：

- 只读监控 `feishu-obsidian-capture`、`feishu-reading-agent`、`feishu-podcast-guide` 三个服务器 Agent。
- 聚合 systemd service / timer 状态、trace JSONL 和最近日志。
- 用 Web Dashboard 展示单次运行的数据流：输入、planner、LLM、工具调用、证据门和最终回复。

重要边界：

- 这是观测台，不是业务 Agent。
- 不写入三个业务项目，不读取 `.env`，不展示真实密钥。
- 默认只监听 `127.0.0.1:8769`，通过 SSH 隧道访问，不直接公网暴露。
- `feishu-obsidian-capture` 目前没有结构化 trace，第一版只能展示服务健康和普通日志事件。

常用检查：

```bash
ssh root@123.57.229.149 "systemctl status agent-monitor.service --no-pager"
ssh root@123.57.229.149 "curl -s http://127.0.0.1:8769/api/health"
ssh -L 8769:127.0.0.1:8769 root@123.57.229.149
```

## 不要混淆的项目关系

```text
personal-kb
  -> 被 feishu-obsidian-capture 写入
  -> 被 personal-memory-researcher 只读检索

personal-memory-researcher
  -> BM25 + Embedding 检索 memory-index
  -> Page-ID/record-ID 回读 personal-kb 原文
  -> 被 feishu-reading-agent 调用

feishu-obsidian-capture
  -> 飞书记录机器人
  -> 写 Obsidian daily note

feishu-reading-agent
  -> 飞书读书机器人
  -> 读 personal-kb + 微信读书
  -> 不写 Obsidian

feishu-podcast-guide
  -> 飞书播客/论文学习陪练
  -> 读播客 RSS + arXiv
  -> 不写 personal-kb

agent-monitor
  -> 只读 feishu-obsidian-capture / feishu-reading-agent / feishu-podcast-guide
  -> 展示 systemd 状态、trace 和日志
  -> 不参与业务回复

openclaw-infoflow-coach
  -> 如流/OpenClaw 沟通教练
  -> 导出群聊并分析 chendingyu / linbeike
  -> 和飞书记录机器人无关
```

## Git 和部署习惯

- 根仓库远端是 GitHub private：`cdycdy666/my_project`。
- 提交前先看：

```bash
git -C /Users/chendingyu/my_project status --short
```

- 只提交当前任务相关文件。不要顺手提交 `.env`、日志、运行状态、私人资料。
- 服务部署到服务器后，至少做三件事：

```bash
python -m py_compile ...
systemctl restart <service>
systemctl is-active <service>
```

- 如果改了飞书机器人长连接服务，要用真实飞书消息或项目自带脚本验证一次。
- 如果改了 LLM prompt 或检索逻辑，要查看 trace，而不是只看最终回复。

## 常见排查路径

飞书机器人没回复：

1. 查服务是否 active。
2. 查是否收到事件。
3. 查是否被 `message_id` 去重。
4. 查 LLM 调用是否卡住。
5. 查发送消息接口是否成功。

重复回复：

1. 查是否有多个 listener 进程。
2. 查同一个 `message_id` 是否出现多次。
3. 查是否先去重再启动慢任务。

阅读推荐质量问题：

1. 查 trace 里的 `material_queries`。
2. 查 `verified_materials_loaded` 里的微信读书命中是否合理。
3. 查 `personal_evidence_context_loaded` 是否回读到了相关 daily note 原文片段。
4. 查 `evidence_aware_material_scoring` 是否只基于已验证材料打分，并选出合理 primary。
5. 查 `final_reply_material_check` 是否通过，最终回复是否遵守 `should_output_count` 和证据等级。

沟通教练质量问题：

1. 确认分析窗口是过去 24 小时，不是自然日。
2. 确认只分析群 `12829093`。
3. 确认重点对象是 `chendingyu` 和 `linbeike`。
4. 确认参考资料优先使用原则卡片，再使用完整参考库。
