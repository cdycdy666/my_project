#!/bin/zsh

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: ./bin/render-naval-video.sh <项目目录> [配音文件相对路径或绝对路径]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$1"
VOICE_ARG="${2:-}"
HYPERFRAMES_DIR="$PROJECT_DIR/hyperframes"
EXPORTS_DIR="$PROJECT_DIR/exports"
VISUAL_OUTPUT="$EXPORTS_DIR/naval-template-visual.mp4"
FINAL_OUTPUT="$EXPORTS_DIR/naval-template-final.mp4"
CONTENT_FILE="$HYPERFRAMES_DIR/content.js"
INDEX_FILE="$HYPERFRAMES_DIR/index.html"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "错误: 项目目录不存在: $PROJECT_DIR"
  exit 1
fi

if [[ ! -d "$HYPERFRAMES_DIR" ]]; then
  echo "错误: 缺少 hyperframes 目录: $HYPERFRAMES_DIR"
  exit 1
fi

mkdir -p "$EXPORTS_DIR"

if [[ -f "$CONTENT_FILE" && -f "$INDEX_FILE" ]]; then
  DURATION_VALUE="$(sed -nE 's/^[[:space:]]*duration:[[:space:]]*([0-9.]+),[[:space:]]*$/\1/p' "$CONTENT_FILE" | head -n 1)"
  if [[ -n "$DURATION_VALUE" ]]; then
    perl -0pi -e "s/data-duration=\"[0-9.]+\"/data-duration=\"$DURATION_VALUE\"/" "$INDEX_FILE"
  fi
fi

echo "==> Lint HyperFrames 工程"
(cd "$HYPERFRAMES_DIR" && npx hyperframes lint)

echo "==> Inspect HyperFrames 布局"
(cd "$HYPERFRAMES_DIR" && npx hyperframes inspect)

echo "==> 渲染画面版"
(cd "$HYPERFRAMES_DIR" && npx hyperframes render --quality standard --output "$VISUAL_OUTPUT")

if [[ -z "$VOICE_ARG" ]]; then
  echo
  echo "已输出画面版:"
  echo "$VISUAL_OUTPUT"
  echo "未提供配音文件，跳过音视频封装。"
  exit 0
fi

if [[ "$VOICE_ARG" = /* ]]; then
  VOICE_PATH="$VOICE_ARG"
else
  VOICE_PATH="$PROJECT_DIR/$VOICE_ARG"
fi

if [[ ! -f "$VOICE_PATH" ]]; then
  echo "错误: 配音文件不存在: $VOICE_PATH"
  exit 1
fi

echo "==> 封装音视频"
ffmpeg -y \
  -i "$VISUAL_OUTPUT" \
  -i "$VOICE_PATH" \
  -map 0:v:0 \
  -map 1:a:0 \
  -c:v copy \
  -c:a aac \
  -shortest \
  "$FINAL_OUTPUT"

echo
echo "已输出最终成片:"
echo "$FINAL_OUTPUT"
