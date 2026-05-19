#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR="$ROOT_DIR/interview-audio-pipeline"

cd "$PROJECT_DIR"

exec env PYTHONPATH=src python3 -m interview_pipeline.cli web --host 127.0.0.1 --port 8787
