#!/bin/zsh

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: ./bin/new-short.sh <选题名>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECTS_DIR="$ROOT_DIR/projects"
TEMPLATE_DIR="$ROOT_DIR/templates"
DATE_STR="$(date +%F)"
RAW_TITLE="$*"
SLUG="$(printf '%s' "$RAW_TITLE" | sed -E 's#[/\\]+#-#g; s/[[:space:]]+/-/g; s/^-+|-+$//g')"
PROJECT_DIR="$PROJECTS_DIR/$DATE_STR-$SLUG"

if [[ -z "$SLUG" ]]; then
  echo "错误: 选题名不能为空。"
  exit 1
fi

if [[ -e "$PROJECT_DIR" ]]; then
  echo "错误: 项目已存在: $PROJECT_DIR"
  exit 1
fi

mkdir -p \
  "$PROJECT_DIR/assets" \
  "$PROJECT_DIR/voice" \
  "$PROJECT_DIR/subtitles" \
  "$PROJECT_DIR/edit" \
  "$PROJECT_DIR/exports" \
  "$PROJECT_DIR/publish"

cp "$TEMPLATE_DIR/brief.md" "$PROJECT_DIR/brief.md"
cp "$TEMPLATE_DIR/script.md" "$PROJECT_DIR/script.md"
cp "$TEMPLATE_DIR/shot-list.md" "$PROJECT_DIR/shot-list.md"
cp "$TEMPLATE_DIR/publish-checklist.md" "$PROJECT_DIR/publish-checklist.md"

cat > "$PROJECT_DIR/README.md" <<EOF
# $RAW_TITLE

- 创建日期: $DATE_STR
- 项目目录: $PROJECT_DIR

## 建议顺序

1. 先写 brief，确认这条视频到底帮谁解决什么问题
2. 再写 script，把开头 3 秒、主体结构、结尾 CTA 写清楚
3. 拍摄或整理素材，统一放到 assets / voice / subtitles
4. 剪辑工程文件放到 edit
5. 导出成片放到 exports
6. 发布前逐项检查 publish-checklist
EOF

echo "已创建短视频项目:"
echo "$PROJECT_DIR"
echo
echo "下一步建议:"
echo "1. 打开 brief.md，先定目标用户和核心观点"
echo "2. 打开 script.md，把前 3 秒钩子先写出来"
