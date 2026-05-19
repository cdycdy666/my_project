#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR="$ROOT_DIR/verbal-expression-coach"

cd "$PROJECT_DIR"

exec python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
