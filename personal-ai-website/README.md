# Personal AI Tools Website

一个 Next.js 中文个人网站，用来汇总个人 AI 工具、学习笔记、阶段总结和资源收藏。

## 本地预览

```bash
npm install
npm run dev
```

默认地址是 `http://localhost:3000`。

如果你要在个人网站里直接调用另外两个工具，还需要在 `personal-ai-website` 下配置环境变量：

```bash
cp .env.example .env.local
```

默认本地地址：

- `INTERVIEW_PIPELINE_BASE_URL=http://127.0.0.1:8787`
- `VERBAL_COACH_BASE_URL=http://127.0.0.1:8000`

## 内容维护

首版内容集中在 `data/site.ts`：

- `tools`: AI 工具卡片
- `notes`: 学习笔记与阶段总结
- `resources`: 资源收藏

需求文档在 `docs/personal-website-prd.md`。

## 部署建议

推荐使用 Vercel 部署：

- GitHub 仓库：`cdycdy666/my_project`
- Vercel Root Directory：`personal-ai-website`
- Framework Preset：`Next.js`

如果走腾讯云轻量应用服务器，当前项目也已经准备好容器化部署：

1. 在服务器上安装 `git`、`docker` 和 `docker compose`
2. 拉取项目后进入 `personal-ai-website`
3. 复制环境变量模板

```bash
cp .env.runtime.example .env.runtime
```

4. 按实际情况填写 `.env.runtime`
5. 构建并启动

```bash
docker compose up -d --build
```

默认会把容器内的 `3000` 端口映射到宿主机 `80` 端口。
