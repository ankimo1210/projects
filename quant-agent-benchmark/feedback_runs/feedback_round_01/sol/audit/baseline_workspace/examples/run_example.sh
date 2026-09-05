#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 /absolute/path/to/market_observations.csv" >&2
  exit 2
fi

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONPATH="$PROJECT_DIR/src" "$PROJECT_DIR/.venv/bin/python" -m quantcurve.cli run \
  --market-data "$1" \
  --output-dir "$PROJECT_DIR/outputs" \
  --valuation-date 2026-01-15 \
  --report-path "$PROJECT_DIR/reports/research_report.html" \
  --config "$PROJECT_DIR/configs/default.json"
