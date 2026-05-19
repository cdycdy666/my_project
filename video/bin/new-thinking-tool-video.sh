#!/bin/zsh

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: ./bin/new-thinking-tool-video.sh <选题名>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERIES_DIR="$ROOT_DIR/series/practical-thinking-tools"
EPISODES_DIR="$SERIES_DIR/episodes"
COMMON_TEMPLATES_DIR="$ROOT_DIR/templates"
BASE_TEMPLATE_DIR="$COMMON_TEMPLATES_DIR/naval-short"
DATE_STR="$(date +%F)"
RAW_TITLE="$*"
SLUG="$(printf '%s' "$RAW_TITLE" | sed -E 's#[/\\]+#-#g; s/[[:space:]]+/-/g; s/^-+|-+$//g')"
PROJECT_DIR="$EPISODES_DIR/$DATE_STR-$SLUG"

if [[ -z "$SLUG" ]]; then
  echo "错误: 选题名不能为空。"
  exit 1
fi

if [[ ! -d "$BASE_TEMPLATE_DIR" ]]; then
  echo "错误: 基础模板目录不存在: $BASE_TEMPLATE_DIR"
  exit 1
fi

if [[ -e "$PROJECT_DIR" ]]; then
  echo "错误: 项目已存在: $PROJECT_DIR"
  exit 1
fi

mkdir -p \
  "$EPISODES_DIR" \
  "$PROJECT_DIR/assets" \
  "$PROJECT_DIR/voice" \
  "$PROJECT_DIR/subtitles" \
  "$PROJECT_DIR/edit" \
  "$PROJECT_DIR/edit/frames" \
  "$PROJECT_DIR/exports" \
  "$PROJECT_DIR/preview" \
  "$PROJECT_DIR/publish" \
  "$PROJECT_DIR/cover" \
  "$PROJECT_DIR/hyperframes" \
  "$PROJECT_DIR/agent-handoffs"

cp "$SERIES_DIR/brief-template.md" "$PROJECT_DIR/brief.md"
cp "$SERIES_DIR/content-review-template.md" "$PROJECT_DIR/content-review.md"
cp "$COMMON_TEMPLATES_DIR/content-material-card.md" "$PROJECT_DIR/content-material-card.md"
cp "$SERIES_DIR/quality-check-template.md" "$PROJECT_DIR/quality-check.md"
cp "$COMMON_TEMPLATES_DIR/script.md" "$PROJECT_DIR/script.md"
cp "$SERIES_DIR/script-lab-template.md" "$PROJECT_DIR/script-lab.md"
cp "$COMMON_TEMPLATES_DIR/shot-list.md" "$PROJECT_DIR/shot-list.md"
cp "$COMMON_TEMPLATES_DIR/visual-component-map.md" "$PROJECT_DIR/visual-component-map.md"
cp "$COMMON_TEMPLATES_DIR/publish-checklist.md" "$PROJECT_DIR/publish-checklist.md"
cp "$COMMON_TEMPLATES_DIR/agent-registry.md" "$PROJECT_DIR/agent-registry.md"
cp "$COMMON_TEMPLATES_DIR/agent-handoffs/agent-handoff.md" "$PROJECT_DIR/agent-handoffs/agent-handoff-template.md"
cp "$SERIES_DIR/scene-contract-template.json" "$PROJECT_DIR/scene-contract.json"
cp "$SERIES_DIR/assembly-check-template.md" "$PROJECT_DIR/assembly-check.md"
cp "$SERIES_DIR/review-template.md" "$PROJECT_DIR/review.md"
cp "$SERIES_DIR/notion-sync-receipt-template.md" "$PROJECT_DIR/notion-sync-receipt.md"

cp "$BASE_TEMPLATE_DIR/hyperframes/index.html" "$PROJECT_DIR/hyperframes/index.html"
cp "$BASE_TEMPLATE_DIR/hyperframes/content.js" "$PROJECT_DIR/hyperframes/content.js"
cp "$BASE_TEMPLATE_DIR/voice/narration.txt" "$PROJECT_DIR/voice/narration.txt"

perl -0pi -e 's/Naval Almanack Short/Practical Thinking Tool Short/g; s/naval-video-template/thinking-tool-template/g' "$PROJECT_DIR/hyperframes/index.html"
perl -0pi -e 's/NAVAL ALMANACK/PRACTICAL THINKING TOOLS/g; s/NAVAL PRINCIPLE/THINKING TOOL/g; s/THE NAVAL PRINCIPLE/THINKING TOOL/g; s/把纳瓦尔原则改写成一句现实判断/把思维工具改写成一个现实动作/g; s/不要做书摘，要解决一个当下焦虑。/不要讲概念百科，要解决一个真实场景。/g' "$PROJECT_DIR/hyperframes/content.js"

cat > "$PROJECT_DIR/template-guide.md" <<EOF
# 实用思维工具短视频模板

这个项目使用已验证的认知类短视频 HyperFrames 基底，但内容目标改为《实用思维工具》。

## 推荐结构

1. 冲突场景：观众现在卡在哪里
2. 工具一句话：这个工具替他换掉哪个旧判断
3. 错误用法：这个工具最容易被怎么用错
4. 正确演示：在一个具体场景里怎么用
5. 本周动作：今天或本周能做哪一步
6. 记忆句：让观众能转述

## 必须先完成

- content-material-card.md
- content-review.md
- brief.md
- script-lab.md
- script.md
- scene-contract.json
- visual-component-map.md
- shot-list.md
EOF

cat > "$PROJECT_DIR/README.md" <<EOF
# $RAW_TITLE

- 创建日期: $DATE_STR
- 项目目录: $PROJECT_DIR
- 系列目录: $SERIES_DIR
- 模板类型: 实用思维工具 3 分钟内知识短视频

## 推荐顺序

1. 先确认 ../../content-system/source-manifest.json 和 ../../content-system/course-source-index.md 已更新
2. 从课程源索引选择 1 个主正课源，问答只作辅助
3. 从 ../../content-system/content-material-library.md 选择工具卡，必要时补 content-material-card.md
4. 再写 content-review，内容评分低于 9.0 不进入制作
5. 写 brief，确认这条视频解决哪个具体场景
6. 先做 script-lab.md，验证 5 个钩子、3 个案例角度、误用风险、记忆句和留存任务
7. 再写 script、voice/narration.txt 和 scene-contract.json
8. 先写 visual-component-map.md，再写 shot-list.md 和 hyperframes/content.js
9. 先生成 30 秒试音，写 voice/voice-manifest.json
10. 渲染后检查 preview/contact-sheet-visual.jpg 和 preview/contact-sheet-final.jpg
11. 完成 assembly-check.md 后进入 review.md
12. G4 只能确认 technical-cut；评分、发布包装和人工完整看听都通过后才是 publish-cut
13. G5 由主编生成 notion-sync-receipt.md
14. G6 写 agent-retrospective.md，并关闭不再需要的 Agent
EOF

echo "已创建实用思维工具视频项目:"
echo "$PROJECT_DIR"
echo
echo "下一步建议:"
echo "1. 从 content-system/content-material-library.md 选择工具卡"
echo "2. 完成 content-review.md、brief.md、script-lab.md"
echo "3. 再进入 script.md、scene-contract.json 和 visual-component-map.md"
