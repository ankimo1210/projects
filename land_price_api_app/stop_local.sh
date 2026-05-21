#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/.streamlit.pid"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "stopped streamlit (pid=$PID)"
  else
    echo "pid file exists but process is not running"
  fi
  rm -f "$PID_FILE"
  exit 0
fi

if command -v fuser >/dev/null 2>&1; then
  if fuser 8501/tcp >/dev/null 2>&1; then
    fuser -k 8501/tcp >/dev/null 2>&1 || true
    echo "stopped process on port 8501"
    exit 0
  fi
fi

echo "no streamlit process found"
