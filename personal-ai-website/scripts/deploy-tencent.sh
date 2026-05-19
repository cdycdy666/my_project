#!/usr/bin/env bash

set -euo pipefail

APP_NAME="${APP_NAME:-personal-ai-website}"
APP_DIR="${APP_DIR:-/home/ubuntu/my_project/personal-ai-website}"
PORT="${PORT:-3000}"
BRANCH="${BRANCH:-main}"

echo "==> Deploying ${APP_NAME} from ${APP_DIR}"

cd "${APP_DIR}"

echo "==> Syncing git branch ${BRANCH}"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

echo "==> Rebuilding Next.js app"
rm -rf .next
npm ci
npm run build

echo "==> Restarting pm2 process ${APP_NAME}"
if pm2 describe "${APP_NAME}" >/dev/null 2>&1; then
  pm2 delete "${APP_NAME}"
fi

PORT="${PORT}" pm2 start npm \
  --name "${APP_NAME}" \
  --cwd "${APP_DIR}" \
  -- run start

pm2 save
pm2 status "${APP_NAME}"
