# Feishu Podcast Guide

一个第一版很轻量的飞书大模型学习陪练机器人，专门使用「AI可可AI生活」作为学习材料入口。

推荐飞书机器人名称：`研几`。

这个名字的好处是足够直白：它不是播客摘要器，也不是资料搬运工，而是陪你选择材料、主动回忆、复盘理解、迁移到项目。

它不主打“再总结一遍播客”。这档播客本身已经是论文和 AI 信息的总结，再二次总结很容易变成更短但更浅的内容。这个机器人的价值是：

- 帮你从大量单集中找到该听哪几集。
- 告诉你每集听的时候抓什么问题。
- 你听完后，用追问检查是否真的掌握。
- 把听到的内容映射到飞书机器人、Agent、RL、后训练等项目决策里。

它以完整 RSS 作为主索引：

- `https://feed.xyzfm.space/wl9t7httkfd3`
- 默认缓存到 `/Users/chendingyu/my_project/feishu-podcast-guide/data/aikeke_feed_latest.xml`

已经整理好的两个 Markdown 清单只作为路线标注和排序辅助，不再作为全集范围：

- `/Users/chendingyu/my_project/output/podcast-index/aikeke-ai-life/agent_learning_path.md`
- `/Users/chendingyu/my_project/output/podcast-index/aikeke-ai-life/rl_learning_path.md`

RSS 会自动更新：默认启动时和收到消息前检查一次，如果本地 RSS 超过 12 小时，会自动刷新并重载索引。第一版不读音频全文，不做转写，只做「路线推荐、听前抓手、听后复盘、项目映射」。

论文模式第一版支持 arXiv：当用户问论文、技术细节、方法、实验、ablation 或给出 arXiv 链接时，Agent 会检索 arXiv、下载 PDF、解析前几页正文并缓存。它不做论文向量库；PDF 解析失败时只基于 arXiv 摘要和元信息回答。

## 当前 Agent 架构

现在已经从“硬编码分流 + 一次检索 + 可选 LLM 包装”改成一版受限工具循环：

```text
用户消息
  -> 帮助 / 状态等简单命令直接回复
  -> 读取 chat_id 最近对话历史
  -> LLM planner 选择下一步工具
  -> 工具返回 RSS / arXiv 证据
  -> planner 可继续换关键词、取单集详情、读学习路径、检索/读取论文或刷新 RSS
  -> LLM 基于本轮工具证据生成回复
  -> 程序证据门校验标题 / 链接必须来自本轮工具结果
  -> 通过后回复飞书，并保存轻量会话历史
```

第一版工具集：

- `search_episodes(query, limit)`：按关键词检索 RSS 单集。
- `get_episode_detail(id/url/title)`：读取单集详情、路线标注和 RSS 简介。
- `list_learning_path(topic)`：读取 Agent / RL 第一轮学习路径。
- `refresh_rss()`：用户明确要求刷新时手动刷新 RSS。
- `search_papers(query, limit)`：按英文技术关键词检索 arXiv 论文。
- `fetch_paper(identifier/url/title)`：下载 arXiv PDF，解析前几页正文并缓存。

边界：

- `帮助`、`状态`、`索引` 仍然直接回复，不浪费模型调用。
- LLM 不可用时会退回旧的本地检索和模板回复。
- 证据门是程序化的：最终回复里出现的播客标题、论文标题或链接，必须来自本轮工具结果。
- 会话历史按 `chat_id` 存在 `state.json`，只用于最近几轮复盘接续，不写入 `personal-kb`。
- Agent loop trace 写入 `logs/traces/YYYY-MM-DD.jsonl`，用于排查 planner 动作、工具结果和证据门失败原因。
- 当前仍不读取音频全文，不做二次长摘要；论文模式只读 arXiv 元信息和已解析 PDF 摘录。

## 能问什么

```text
帮助
Agent 从哪几集开始听？
介绍一下 RAG / Deep Research 相关的几集
强化学习和 GRPO 相关的播客有哪些？
推荐 5 集适合做飞书 Agent 项目的
单一智能体的力量 这集应该怎么听？
我听完 RAG-Gym 了，我的理解是搜索 + 推理 + 过程监督
我想把 Agent 播客内容落到飞书机器人项目里，第一版怎么做？
最近 Agent 落地相关有哪些值得读的论文？
帮我读这篇论文：https://arxiv.org/abs/2305.16291
```

## 本地调试

```bash
cd /Users/chendingyu/my_project/feishu-podcast-guide
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/refresh_rss.py
PODCAST_LLM_ENABLED=false ./.venv/bin/python scripts/chat_once.py "Agent 从哪几集开始听？"
```

`PODCAST_LLM_ENABLED=false` 会只使用本地检索和模板回复，适合先验证知识库是否加载成功。配置 `PODCAST_LLM_*` 后，可以让模型基于检索结果生成更自然的导览回复。

建议本地先试这三类问题：

```bash
PODCAST_LLM_ENABLED=false ./.venv/bin/python scripts/chat_once.py "Agent 从哪几集开始听？"
PODCAST_LLM_ENABLED=false ./.venv/bin/python scripts/chat_once.py "我听完 RAG-Gym 了，我的理解是搜索 + 推理 + 过程监督"
PODCAST_LLM_ENABLED=false ./.venv/bin/python scripts/chat_once.py "我想把 Agent 播客内容落到飞书机器人项目里，第一版怎么做？"
```

## 接入飞书

在飞书开放平台创建自建应用，并启用机器人能力。第一版使用飞书官方 SDK 的长连接事件订阅，不需要公网回调地址。

需要配置：

```env
PODCAST_BOT_DISPLAY_NAME=研几
PODCAST_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
PODCAST_FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PODCAST_FEISHU_VERIFICATION_TOKEN=
PODCAST_FEISHU_ENCRYPT_KEY=

PODCAST_RSS_URL=https://feed.xyzfm.space/wl9t7httkfd3
PODCAST_RSS_PATH=/Users/chendingyu/my_project/feishu-podcast-guide/data/aikeke_feed_latest.xml
PODCAST_RSS_AUTO_REFRESH=true
PODCAST_RSS_MAX_AGE_HOURS=12

PODCAST_PAPER_CACHE_PATH=/Users/chendingyu/my_project/feishu-podcast-guide/data/papers
PODCAST_PAPER_MAX_PAGES=8
PODCAST_PAPER_MAX_CHARS=18000
```

飞书侧需要：

- 应用名称建议填：`研几`。
- 应用描述可以填：`基于播客和论文清单的大模型技术学习陪练，帮助选择材料、复盘理解、映射到项目。`
- 开启机器人能力。
- 开启长连接事件订阅。
- 订阅 `im.message.receive_v1`。
- 添加接收消息、发送消息相关权限。
- 发布应用。

启动：

```bash
cd /Users/chendingyu/my_project/feishu-podcast-guide
./.venv/bin/python scripts/check_config.py
./.venv/bin/python run.py
```

然后在飞书里给机器人发送：

```text
帮助
```

## 当前边界

- 以这档播客完整 RSS 为检索范围，已整理清单只作为学习路线辅助。
- 不读取音频全文，所以不能保证覆盖每集的完整细节。
- 论文模式会读 arXiv 摘要和可解析 PDF 摘录，但不保证覆盖论文全文所有细节；需要精读时仍建议打开原文。
- 不写 Notion，也不做二次长摘要推送。
- 有每日单集主动推送 + 主题轮换征询（见下节），但推送内容仍是「单集 + 听前抓手」，不做长摘要。
- 推荐结果优先服务你的学习目标：RL、Agent、项目落地、大模型后训练。

## 每日一集推荐 + 主题轮换

第一版之外新增的定时能力。默认关闭，需显式开启：

```env
PODCAST_DAILY_RECO_ENABLED=true
PODCAST_DAILY_THEME_ROTATE_COUNT=7   # 推够 N 集后征询是否换主题
PODCAST_DAILY_PUSH_TIME=08:30        # 给外部 timer/cron 用，代码不自调度
PODCAST_DAILY_RECENT_WINDOW=60       # 动态候选主题扫描的最近集数
```

交互设计：

- 每天推 1 集（当前主题里没推过的），附一句听前抓手。
- 推够 `ROTATE_COUNT` 集后追一条征询消息，给出「从最近 RSS 动态抽出的、够料的候选主题」。
- 你回复：序号选候选 / 直接说想聚焦的主题 / 回复「继续」留在当前主题。
- 若不回复：**继续照推当前主题**，每再推 3 集补提醒一次，不会默默替你换主题。
- 任意时刻发「换主题」可立即触发同一套征询。
- 动态候选是关键词桶聚类（`THEME_BUCKETS`），不是语义聚类，覆盖不到没枚举的新说法。

运行数据（当前主题、已推集 id、pending 状态等）存在本项目 `state.json` 的 `daily_reco` 块，**不写 `personal-kb`**。推送目标默认用最近一次与机器人对话的 `chat_id`。

本地干跑（真实飞书发送前先验证闭环）：

```bash
cd /Users/chendingyu/my_project/feishu-podcast-guide
PODCAST_DAILY_RECO_ENABLED=true ./.venv/bin/python scripts/run_daily_reco.py
```

定时触发用 systemd timer 或 cron（对应 08:30），指向 `scripts/run_daily_reco.py`。脚本自带按 `last_push_date` 幂等，当天重复触发不会重推。

飞书官方文档入口：

- [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
- [事件订阅](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case)
- [tenant_access_token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)
