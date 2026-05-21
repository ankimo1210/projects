#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/.streamlit.pid"
WORKSPACE_DIR="$(cd "$ROOT_DIR/.." && pwd)"
LOG_DIR="${LAND_PRICE_LOG_DIR:-$WORKSPACE_DIR/_logs/app/land_price_api_app}"
LOG_FILE="${LAND_PRICE_STREAMLIT_LOG:-$LOG_DIR/streamlit.log}"
PORT="8501"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "streamlit is already running (pid=$OLD_PID)"
    echo "url: http://localhost:$PORT"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$ROOT_DIR"
mkdir -p "$LOG_DIR"
setsid .venv/bin/streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port "$PORT" \
  --server.headless true \
  >"$LOG_FILE" 2>&1 < /dev/null &
PID="$!"
echo "$PID" > "$PID_FILE"

echo "started streamlit (pid=$PID)"
echo "url: http://localhost:$PORT"
echo "log: $LOG_FILE"
