#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR="$ROOT_DIR/personal-ai-website"

cd "$PROJECT_DIR"

if [ ! -d node_modules ]; then
  echo "Installing website dependencies..."
  npm install
fi

exec npm run dev -- --hostname 127.0.0.1 --port 3000
