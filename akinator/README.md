# akinator

ローカルで動くアキネーター風の推測ゲーム。固定の決定木ではなく、回答に応じて候補の確率を更新します。
Wikidata からの取得機能がありますが、同梱の処理済みデータは手作りのオフライン seed 35件です
（`scripts/seed_data.py`、ID は `seed_*`）。ライブ取得したデータとは区別してください。

## 実行

```bash
cd ~/projects && make install            # once, installs workspace .venv
# 任意: Wikidata から再取得（外部通信あり。同梱 seed のままでも起動可能）:
uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py --refresh
uv run --no-sync python akinator/scripts/build_questions.py
# serve
uv run --no-sync uvicorn app.main:app --app-dir akinator --reload --port 8100
# tests
uv run --no-sync pytest akinator/tests -v
```

Open http://localhost:8100/ to play. `/debug/{game_id}` shows engine internals.
