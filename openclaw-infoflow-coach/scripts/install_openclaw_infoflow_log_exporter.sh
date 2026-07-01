#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT_PATH="${ROOT}/scripts/nightly_openclaw_infoflow_coach.sh"
PLIST_PATH="$HOME/Library/LaunchAgents/com.chendingyu.openclaw-infoflow-communication-coach.plist"
OLD_PLIST_PATH="$HOME/Library/LaunchAgents/com.chendingyu.openclaw-infoflow-log-exporter.plist"
LOG_DIR="$HOME/Library/Logs"

mkdir -p "$(dirname "$PLIST_PATH")" "$LOG_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.chendingyu.openclaw-infoflow-communication-coach</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPT_PATH}</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>20</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/openclaw-infoflow-communication-coach.out.log</string>

  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/openclaw-infoflow-communication-coach.err.log</string>
</dict>
</plist>
PLIST

chmod 600 "$PLIST_PATH"
chmod +x "$SCRIPT_PATH"
launchctl bootout "gui/$(id -u)" "$OLD_PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$OLD_PLIST_PATH"
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

echo "Installed LaunchAgent: $PLIST_PATH"
echo "Exports to: ${ROOT}/openclaw-infoflow-logs/YYYY-MM-DD.md"
echo "Advice to: ${ROOT}/openclaw-infoflow-advice/YYYY-MM-DD.md"
echo "Schedule: every day at 20:00 local time"
