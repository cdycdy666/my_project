#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

INTERVIEW_SCRIPT="$ROOT_DIR/scripts/dev-interview-pipeline.sh"
COACH_SCRIPT="$ROOT_DIR/scripts/dev-verbal-expression-coach.sh"
WEBSITE_SCRIPT="$ROOT_DIR/scripts/dev-personal-website.sh"

cleanup() {
  if [ -n "${INTERVIEW_PID:-}" ]; then
    kill "$INTERVIEW_PID" 2>/dev/null || true
  fi
  if [ -n "${COACH_PID:-}" ]; then
    kill "$COACH_PID" 2>/dev/null || true
  fi
  if [ -n "${WEBSITE_PID:-}" ]; then
    kill "$WEBSITE_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting interview-audio-pipeline on http://127.0.0.1:8787"
"$INTERVIEW_SCRIPT" &
INTERVIEW_PID=$!

echo "Starting verbal-expression-coach on http://127.0.0.1:8000"
"$COACH_SCRIPT" &
COACH_PID=$!

echo "Starting personal-ai-website on http://127.0.0.1:3000"
"$WEBSITE_SCRIPT" &
WEBSITE_PID=$!

echo ""
echo "Local stack is starting:"
echo "  personal-ai-website       http://127.0.0.1:3000"
echo "  interview-audio-pipeline  http://127.0.0.1:8787"
echo "  verbal-expression-coach   http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop all three services."

wait
