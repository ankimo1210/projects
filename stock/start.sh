#!/bin/bash
# stockkit 起動スクリプト
cd "$(dirname "$0")"
uv run python app/app.py
