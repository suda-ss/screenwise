#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$PROJECT_DIR/.run"
stopped=0

stop_process() {
  local name="$1"
  local pid_file="$2"
  if test ! -f "$pid_file"; then
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    local attempts=20
    while kill -0 "$pid" 2>/dev/null && (( attempts > 0 )); do
      sleep 0.25
      attempts=$((attempts - 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "$name did not stop gracefully (PID $pid)." >&2
      return 1
    fi
    echo "Stopped $name (PID $pid)."
    stopped=1
  fi
  rm -f "$pid_file"
}

stop_process "dashboard" "$RUN_DIR/web.pid"
stop_process "API" "$RUN_DIR/api.pid"

if (( stopped == 0 )); then
  echo "Resume Screening Agent is not running."
else
  echo "Resume Screening Agent stopped."
fi

