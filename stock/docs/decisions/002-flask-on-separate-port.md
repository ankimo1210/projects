# ADR 002: AIチャット用Flaskを別ポート (8051) で動かす

**Status**: Accepted
**Date**: 2026-05-17

## Context

Dash アプリ (port 8050) に AI チャットのバックエンド API を追加する必要がある。実装案：

1. **Dash の `app.server` (Flask) にルート追加** — 同一ポートで完結
2. **別 Flask アプリを port 8051 で起動** — 独立プロセス
3. **Dash の `background_callback` (Celery)** — 重量級

最初は (1) で実装したが問題が発生した。

## Decision

**(2) 別 Flask アプリを port 8051 で起動**。`app/api/server.py` で `threading.Thread` daemon として立ち上げ、Dash 起動と同時に動作。

## Rationale

### (1) で発生した問題
Dash 2.x は `callback_context` という `ContextVar` を持ち、Flask の `before_request` で各リクエスト毎にセットアップしている。プレーン Flask ルート（Dash callback 経由でない）でこの ContextVar にアクセスすると `LookupError` または `AttributeError` が発生。

ワークアラウンド（`before_request` で ContextVar を初期化）も試したが、Dash の内部実装に依存するため壊れやすい。

### (2) の利点
- **完全独立** — Dash のリクエスト処理に一切影響を与えない
- **同一プロセス内** — `threading.Thread` で起動するため別プロセス管理不要
- **クライアント側はHTTP越し** — 将来的にチャット機能を別サーバーに分離する場合も容易

### (3) を選ばなかった理由
- Celery + Redis のセットアップが重い
- 個人ツールとしては過剰

## Consequences

- **2 つのポート (8050, 8051) を消費** — 起動スクリプトで `lsof -ti:8050,8051` の確認が必要
- **Dash callback から HTTP 経由で内部 API を呼ぶ** — わずかなオーバーヘッドだがユーザー体感影響なし
- **デバッグ時にログが両サーバーから出る** — 区別が必要

## Code Reference

- `app/app.py` の `__main__` で `start_api(port=8051)` を呼んでいる
- `app/api/server.py` が独立 Flask アプリ
- `app/pages/chat.py` が `http://127.0.0.1:8051/api/chat` を叩く
