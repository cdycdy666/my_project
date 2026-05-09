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

如果走腾讯云轻量应用服务器，当前已经验证通过的是 `Node.js + pm2` 路线：

1. 服务器上安装 `git`、`node`、`npm` 和 `pm2`
2. 拉取项目后进入 `personal-ai-website`
3. 复制环境变量模板

```bash
cp .env.example .env.local
```

4. 按实际情况填写 `.env.local`
5. 首次启动

```bash
npm ci
npm run build
PORT=3000 pm2 start npm --name personal-ai-website --cwd /home/ubuntu/my_project/personal-ai-website -- run start
pm2 save
```

6. 后续更新可以直接执行部署脚本

```bash
cd /home/ubuntu/my_project/personal-ai-website
bash scripts/deploy-tencent.sh
```

默认会在宿主机 `3000` 端口启动服务。

### 腾讯云 Nginx 反代

如果你希望把访问地址从 `http://IP:3000/...` 收成标准网站地址 `http://IP/...`，可以在服务器上给 `pm2 + Next.js` 前面加一层 `nginx`。

1. 安装 `nginx`

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

2. 把仓库里的模板拷到 `sites-available`

```bash
sudo cp deploy/nginx/personal-ai-website.conf /etc/nginx/sites-available/personal-ai-website
```

3. 启用站点

```bash
sudo ln -sf /etc/nginx/sites-available/personal-ai-website /etc/nginx/sites-enabled/personal-ai-website
```

4. 如有默认站点，先移除

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

5. 检查配置并重载

```bash
sudo nginx -t
sudo systemctl reload nginx
```

6. 防火墙放行 `80` 端口后，即可直接访问

```text
http://服务器公网IP/tools/wisdom-advisor
```

这套配置会把外部 `80` 端口的请求转发到本机 `127.0.0.1:3000`，也就是当前 `pm2` 跑起来的 Next.js 服务。
