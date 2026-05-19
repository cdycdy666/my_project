# 系统升级记录 2026-05-18

## 升级目标

把《纳瓦尔宝典》系列从“每条视频靠单次 Agent 表现”升级为“可持续复用的高质量生产系统”。

本轮重点不是再增加角色，而是补齐三类能长期提升质量的资产：

- 内容原料库：提高选题和观点质量。
- 脚本实验室：提高前 3 秒、案例、留存和口播质量。
- 视觉组件库：提高画面一致性、制作效率和系列辨识度。

## 已完成

- 新增 `content-system/content-material-library.md`。
- 新增 `content-system/script-lab-system.md`。
- 新增 `content-system/visual-component-library.md`。
- 新增视频模板 `content-material-card.md`、`script-lab.md`、`visual-component-map.md`。
- 更新 `bin/new-naval-video.sh`，新视频会自动带上三份新模板。
- 更新 `quality-standard.md`，把原料卡、脚本实验室、视觉组件映射纳入 G0/G1/G3/G5。
- 更新 `multi-agent-sop.md`，把三类资产写进标准执行顺序和硬检查。
- 更新 00/01/02/03/04/06/07/08 Agent 定义。
- 更新 `notion-setup.md` 和系列 `README.md`。
- 为“退休不是老了不工作”补齐 `content-material-card.md`、`script-lab.md`、`visual-component-map.md`，作为新流程标准样例。
- 去掉 `naval-short` 通用 `index.html` 里的旧主题硬编码文案，改为由 `content.js` 注入集数、主题、原则卡 footer 和 mock 面板文本。
- 去掉 `naval-short/hyperframes/content.js` 里的旧视频样例内容，改成中性占位，避免新视频从模板继承“学会销售学会构建”的残留。
- 更新 `notion-sync-receipt-template.md`、`assembly-check-template.md`、`template-guide.md` 和 G5 同步清单，确保三份新前置资产、`voice-manifest.json`、`assembly-check.md` 都进入固定流程。
- 补齐非主编 Agent 的边界规则：所有非 00 Agent 都只能在 handoff 中提交状态建议，不直接写 `quality-check.md` 或 Notion 同步状态。
- 已同步 Notion：内容原料库 v1、脚本实验室 v1、视觉组件库 v1、多 Agent SOP v1.2、质量标准 v1.2、相关 Agent 定义和退休视频页面。

## 质量提升点

- G0 不再只看“选题是否好”，而是必须有可复用原料卡。
- G1 不再直接写最终稿，而是先做低成本脚本实验。
- G3 不再直接写分镜，而是先用组件映射控制画面语言和信息负载。
- G4 不只看成片是否顺，还要检查脚本实验和视觉组件是否在成片中兑现。
- G6 发布复盘不只汇总数据，还要把高价值评论、误解和反驳回流到内容原料库。
- 通用 HyperFrames 模板不再把某一条旧视频的主题硬编码在 `index.html` 里，降低旧文案污染新视频的概率。
- `quality-check.md` 的所有权进一步收紧为主编总控专属汇总文件，降低多个 Agent 同时写状态导致真相漂移的概率。

## 后续建议

- 连续制作 3 条新视频后，复盘哪些原料卡、钩子类型和视觉组件最有效。
- 把表现好的封面标题和前 3 秒钩子沉淀成独立的标题/钩子库。
- 等发布数据回来后，建立“高表现组件”标记，指导视觉导演优先复用。
