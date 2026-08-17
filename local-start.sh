#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$PROJECT_DIR/.run"
API_PORT="${RESUME_API_PORT:-8020}"
WEB_PORT="${RESUME_WEB_PORT:-3008}"
API_URL="http://127.0.0.1:${API_PORT}"
WEB_URL="http://127.0.0.1:${WEB_PORT}"

is_running() {
  local pid_file="$1"
  test -f "$pid_file" && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

port_is_busy() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_url() {
  local url="$1"
  local attempts=30
  while (( attempts > 0 )); do
    if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 1
  done
  return 1
}

mkdir -p "$RUN_DIR"

if is_running "$RUN_DIR/api.pid" || is_running "$RUN_DIR/web.pid"; then
  echo "Resume Screening Agent is already running."
  echo "Dashboard: $WEB_URL"
  echo "API docs:  $API_URL/docs"
  exit 0
fi

if port_is_busy "$API_PORT"; then
  echo "API port $API_PORT is already in use. Set RESUME_API_PORT to another port." >&2
  exit 1
fi
if port_is_busy "$WEB_PORT"; then
  echo "Web port $WEB_PORT is already in use. Set RESUME_WEB_PORT to another port." >&2
  exit 1
fi

if test ! -x "$PROJECT_DIR/.venv/bin/python" || ! "$PROJECT_DIR/.venv/bin/python" -c "import uvicorn" >/dev/null 2>&1; then
  echo "Python dependencies are missing. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
if test ! -d "$PROJECT_DIR/frontend/node_modules"; then
  echo "Frontend dependencies are missing. Run: cd frontend && npm install" >&2
  exit 1
fi

cd "$PROJECT_DIR"
DATABASE_URL="${DATABASE_URL:-sqlite:///$PROJECT_DIR/resume_screening.db}" \
UPLOAD_DIR="${UPLOAD_DIR:-$PROJECT_DIR/storage/uploads}" \
CORS_ORIGINS="$WEB_URL" \
nohup "$PROJECT_DIR/.venv/bin/python" -m uvicorn backend.main:app \
  --host 127.0.0.1 --port "$API_PORT" >"$RUN_DIR/api.log" 2>&1 &
echo "$!" >"$RUN_DIR/api.pid"

cd "$PROJECT_DIR/frontend"
NEXT_PUBLIC_API_URL="$API_URL" \
nohup npm run dev -- --hostname 127.0.0.1 --port "$WEB_PORT" >"$RUN_DIR/web.log" 2>&1 &
echo "$!" >"$RUN_DIR/web.pid"

if ! wait_for_url "$API_URL/health"; then
  echo "API failed to start. See $RUN_DIR/api.log" >&2
  "$PROJECT_DIR/local-stop.sh" >/dev/null 2>&1 || true
  exit 1
fi
if ! wait_for_url "$WEB_URL"; then
  echo "Dashboard failed to start. See $RUN_DIR/web.log" >&2
  "$PROJECT_DIR/local-stop.sh" >/dev/null 2>&1 || true
  exit 1
fi

echo "Resume Screening Agent is running."
echo "Dashboard: $WEB_URL"
echo "API docs:  $API_URL/docs"
echo "Logs:      $RUN_DIR"
echo "Stop with: $PROJECT_DIR/local-stop.sh"
