#!/bin/zsh

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: ./bin/new-naval-video.sh <选题名>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERIES_DIR="$ROOT_DIR/series/naval-almanack"
EPISODES_DIR="$SERIES_DIR/episodes"
COMMON_TEMPLATES_DIR="$ROOT_DIR/templates"
NAVAL_TEMPLATE_DIR="$COMMON_TEMPLATES_DIR/naval-short"
DATE_STR="$(date +%F)"
RAW_TITLE="$*"
SLUG="$(printf '%s' "$RAW_TITLE" | sed -E 's#[/\\]+#-#g; s/[[:space:]]+/-/g; s/^-+|-+$//g')"
PROJECT_DIR="$EPISODES_DIR/$DATE_STR-$SLUG"

if [[ -z "$SLUG" ]]; then
  echo "错误: 选题名不能为空。"
  exit 1
fi

if [[ ! -d "$NAVAL_TEMPLATE_DIR" ]]; then
  echo "错误: 模板目录不存在: $NAVAL_TEMPLATE_DIR"
  exit 1
fi

if [[ -e "$PROJECT_DIR" ]]; then
  echo "错误: 项目已存在: $PROJECT_DIR"
  exit 1
fi

mkdir -p \
  "$SERIES_DIR" \
  "$EPISODES_DIR" \
  "$PROJECT_DIR/assets" \
  "$PROJECT_DIR/voice" \
  "$PROJECT_DIR/subtitles" \
  "$PROJECT_DIR/edit" \
  "$PROJECT_DIR/edit/frames" \
  "$PROJECT_DIR/exports" \
  "$PROJECT_DIR/publish" \
  "$PROJECT_DIR/cover" \
  "$PROJECT_DIR/hyperframes" \
  "$PROJECT_DIR/agent-handoffs"

cp "$COMMON_TEMPLATES_DIR/brief.md" "$PROJECT_DIR/brief.md"
cp "$COMMON_TEMPLATES_DIR/content-review.md" "$PROJECT_DIR/content-review.md"
cp "$COMMON_TEMPLATES_DIR/content-material-card.md" "$PROJECT_DIR/content-material-card.md"
cp "$COMMON_TEMPLATES_DIR/quality-check.md" "$PROJECT_DIR/quality-check.md"
cp "$COMMON_TEMPLATES_DIR/script.md" "$PROJECT_DIR/script.md"
cp "$COMMON_TEMPLATES_DIR/script-lab.md" "$PROJECT_DIR/script-lab.md"
cp "$COMMON_TEMPLATES_DIR/shot-list.md" "$PROJECT_DIR/shot-list.md"
cp "$COMMON_TEMPLATES_DIR/visual-component-map.md" "$PROJECT_DIR/visual-component-map.md"
cp "$COMMON_TEMPLATES_DIR/publish-checklist.md" "$PROJECT_DIR/publish-checklist.md"
cp "$COMMON_TEMPLATES_DIR/agent-registry.md" "$PROJECT_DIR/agent-registry.md"
cp "$COMMON_TEMPLATES_DIR/agent-handoffs/agent-handoff.md" "$PROJECT_DIR/agent-handoffs/agent-handoff-template.md"
cp "$SERIES_DIR/scene-contract-template.json" "$PROJECT_DIR/scene-contract.json"
cp "$SERIES_DIR/assembly-check-template.md" "$PROJECT_DIR/assembly-check.md"
cp "$SERIES_DIR/review-template.md" "$PROJECT_DIR/review.md"
cp "$SERIES_DIR/notion-sync-receipt-template.md" "$PROJECT_DIR/notion-sync-receipt.md"

cp "$NAVAL_TEMPLATE_DIR/hyperframes/index.html" "$PROJECT_DIR/hyperframes/index.html"
cp "$NAVAL_TEMPLATE_DIR/hyperframes/content.js" "$PROJECT_DIR/hyperframes/content.js"
cp "$NAVAL_TEMPLATE_DIR/voice/narration.txt" "$PROJECT_DIR/voice/narration.txt"
cp "$NAVAL_TEMPLATE_DIR/README.md" "$PROJECT_DIR/template-guide.md"

cat > "$PROJECT_DIR/README.md" <<EOF
# $RAW_TITLE

- 创建日期: $DATE_STR
- 项目目录: $PROJECT_DIR
- 系列目录: $SERIES_DIR
- 模板类型: 纳瓦尔宝典 3 分钟内知识短视频

## 推荐顺序

1. 先从 ../../content-system/content-material-library.md 选择原料卡，必要时补 content-material-card.md
2. 再写 content-review，内容评分低于 9.0 不进入制作
3. 更新 quality-check 的 G0 和 G1，确认选题与文案过闸口
4. 再写 brief，确认这条视频解决哪个当下焦虑
5. 先做 script-lab.md，验证 5 个钩子、3 个案例角度、反驳桥、记忆句和留存任务
6. 再写 script、voice/narration.txt 和 scene-contract.json，脚本自评分低于 90 不进入制作
7. 先写 visual-component-map.md，为每个 scene 选择主组件
8. 基于 scene-contract.json 和 visual-component-map.md 写 shot-list，确认不是纯文字 PPT
9. 先生成 30 秒试音，写 voice/voice-manifest.json，technical_audio_pass 未通过不全片生成
10. 打开 hyperframes/content.js，把屏幕文字、字幕和场景时长改成这一条的版本
11. 运行 ./bin/render-naval-video.sh "$PROJECT_DIR" 先出无声画面版
12. 完成 15-30 秒样片或等价片段抽检，写 assembly-check.md
13. 抽帧检查开头、原则、案例、结尾
14. 生成全片配音后，再运行 ./bin/render-naval-video.sh "$PROJECT_DIR" voice/你的配音文件
15. 写 review.md，成片评分低于 9.0 不发布
16. 补封面、发布资产、Notion 台账和 notion-sync-receipt.md
17. 写 agent-retrospective.md，并关闭不再需要的 Agent
18. 核对 agent-registry.md，确保所有不再需要的 Agent 都已关闭

## 模板文件

- quality-check.md: 本条视频的质量闸口
- content-material-card.md: 本条视频实际采用的内容原料卡
- script-lab.md: 正式脚本前的钩子、案例、记忆句和留存实验
- visual-component-map.md: 正式分镜前的视觉组件选择
- agent-registry.md: 本条视频实际启动过的 Agent 台账，用于 G5/G6 清理后台任务
- agent-handoffs/: 多 Agent 交接记录
- scene-contract.json: 脚本、视觉、配音和装配协议
- assembly-check.md: G3.5 装配剪辑检查
- review.md: G4 成片评审
- notion-sync-receipt.md: G5 Notion 同步唯一回执
- hyperframes/index.html: 通用画面模板
- hyperframes/content.js: 本条视频的核心配置
- voice/narration.txt: 旁白文案
- template-guide.md: 模板使用说明
EOF

echo "已创建纳瓦尔视频项目:"
echo "$PROJECT_DIR"
echo
echo "下一步建议:"
echo "1. 先从 ../../content-system/content-material-library.md 选原料卡，必要时补 content-material-card.md"
echo "2. 打开 quality-check.md，逐个通过 G0-G6 质量闸口"
echo "3. 打开 content-review.md 和 brief.md，确认这一条解决哪个当下焦虑"
echo "4. 先完成 script-lab.md，再写 script.md 与 scene-contract.json"
echo "5. 先完成 visual-component-map.md，再写 shot-list.md"
echo "6. 补齐 scene-contract.json，再让视觉和配音按协议并行"
echo "7. 先做 30 秒试音，并记录 technical_audio_pass / audio_subjective_review"
echo "8. 打开 hyperframes/content.js，替换成这一条的标题、字幕、卡片和结尾"
echo "9. G5 由主编生成 notion-sync-receipt.md，G6 写 agent-retrospective.md 并清理 Agent"
