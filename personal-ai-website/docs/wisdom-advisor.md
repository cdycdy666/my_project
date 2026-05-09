# 沟通与处事锦囊顾问

这是一个先在本地跑通的 MVP，用来把“录音转写 + 文档摘录 + 手动心得”沉淀成一个可提问的小顾问。

## 当前能力

- 粘贴 BOS 录音链接，自动转写并写入知识库
- 在站内录入新的知识条目
- 批量导入 `7.得到锦囊` 目录里的 `.doc` 文件
- 批量导入 `7.得到锦囊` 目录里的扫描版 `.pdf` 文件
- 把正文自动拆成多个可检索片段
- 提问时先做本地检索，再返回建议、动作和注意事项
- 展示本次回答引用到的资料来源

## 资料存放

知识库文件在：

`data/wisdom-advisor/knowledge-base.json`

你可以通过页面录入，也可以直接编辑这个 JSON。

## 和百度云录音的衔接方式

当前版本已经把“知识顾问”和 `interview-audio-pipeline` 接起来了：

1. 在顾问页粘贴一个可访问的 BOS 签名链接
2. 网站会调用 `interview-audio-pipeline` 的 `/api/run`
3. 转写结果会自动拆分并写进 `knowledge-base.json`

## 运行前提

- `personal-ai-website/.env.local` 里要能访问转写服务：
  - `INTERVIEW_PIPELINE_BASE_URL=http://127.0.0.1:8787`
- `interview-audio-pipeline/.env` 里要配置好至少一种转写方式：
  - `TRANSCRIPTION_PROVIDER=local_whisper`
  - 或 `qianfan`
  - 或 `doubao_miaoji`
- 如果你用 BOS 私有文件，录音链接需要是可下载的签名 URL

## 当前限制

- 自动入库目前默认把完整转写文本直接入库，还没有做“只抽高质量金句”的精筛
- 如果转写 provider 选 `local_whisper`，服务端会先下载 BOS 链接再本地转写，因此速度取决于网络和本机性能
- 如果录音很长，建议先用 5 到 20 分钟的小样验证整条链路
- 当前 `.pdf` 批量导入依赖百度文档解析，默认读取 `interview-audio-pipeline/.env` 里的 `BAIDU_API_KEY`，如果没有会回退到 `QIANFAN_BEARER_TOKEN`

## 批量导入得到锦囊

如果你的资料目录就在仓库根目录下的 `7.得到锦囊`，可以直接运行：

```bash
cd personal-ai-website
npm run import:jinnang:doc
```

如果你只想先试导入前 20 份，可以运行：

```bash
cd personal-ai-website
node scripts/import-jinnang-docs.mjs ../7.得到锦囊 20
```

脚本会做这些事：

- 只处理 `.doc`
- 自动去掉像 `(1)`、`(2)` 这类重复副本
- 同标题如果已经在知识库里，就跳过
- 用 `textutil` 抽正文后写入 `data/wisdom-advisor/knowledge-base.json`

## 批量导入得到锦囊 PDF

如果你已经在 `interview-audio-pipeline/.env` 里配置了 `QIANFAN_BEARER_TOKEN` 或 `BAIDU_API_KEY`，可以运行：

```bash
cd personal-ai-website
npm run import:jinnang:pdf
```

如果你只想先试导入前 3 份，可以运行：

```bash
cd personal-ai-website
node scripts/import-jinnang-pdfs.mjs ../7.得到锦囊 3
```

脚本会做这些事：

- 只处理 `.pdf`
- 自动去掉像 `(1)`、`(2)` 这类重复副本
- 使用百度文档解析把扫描版 PDF 转成 Markdown
- 清洗广告、作者头衔、重复提问句后写入 `data/wisdom-advisor/knowledge-base.json`

后续如果你要继续做，可以再加：

- 百度云/BOS 链接直导入
- 音频自动转写后直接入库
- 接入真正的大模型生成更细腻的回答
