#!/usr/bin/env bash
# market-viz 起動スクリプト
# Usage: ./start.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Market Viz ==="
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:3000"
echo "Docs     → http://localhost:8000/docs"
echo ""

# Backend
(cd "$ROOT" && uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# Frontend
(cd "$ROOT/frontend" && pnpm dev --port 3000) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'stopped'" EXIT INT TERM
wait
