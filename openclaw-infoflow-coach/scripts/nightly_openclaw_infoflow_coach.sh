#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATE_LABEL="${1:-$(date +%F)}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

"${PYTHON_BIN}" "${ROOT}/scripts/export_openclaw_infoflow_logs.py" --date "${DATE_LABEL}"
"${PYTHON_BIN}" "${ROOT}/scripts/analyze_openclaw_infoflow_communication.py" \
  --date "${DATE_LABEL}" \
  --group-id "12829093" \
  --focus-user "chendingyu" \
  --focus-user "linbeike" \
  --send-to-group
