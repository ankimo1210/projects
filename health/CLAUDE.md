# health — Claude Code Guide

Google Health APIを使う個人向けダッシュボード。応答は日本語、code/identifier/commitは英語。

- `src/health/`がcore（endpoints → auth/client → store → sync → inventory）、
  `app/`は薄いStreamlit UI。viewからAPI/IO契約を実装しない。
- `endpoints.py`の14-entry `CATALOG`が実装metricのsingle source of truth。
  API shapeは`.superpowers/sdd/health-google-api-contracts.md`に従う。
- `dailyRollUp`は1 payload、`reconcile`は全pageを取得してからparseする。途中pageを
  保存済みとして扱わない。
- raw pages、typed rows、watermarkは`Store.replace_chunk()`でchunk単位に原子的置換する。
  chunk境界は`CHUNK_EPOCH`と`max_range_days`だけで決まるカレンダー整列（`aligned_chunk`）。
  同じ暦日は常に同じchunk keyになるので、再取得はraw pageを置換し重複を残さない。
  `start`/`end`は整列chunk key（raw_jsonの同一性）、`covered_start`/`covered_end`は
  `[floor, today]`へクリップした後に実際に再取得した範囲で、両者はしばしば異なる。
  raw_json以外の3つのtyped-row DELETE（daily_series/intraday/sleep_sessions）は必ず
  `covered_start`/`covered_end`を使うこと――chunk keyまで広げると、そのchunkでは
  取得していない既同期日を消してしまう（実装中に発見・修正した不具合なので徹底する）。
- sync runはまず全metricの直近`RECENT_WINDOW_DAYS`を取得し（forward pass）、残予算で
  `backfilled_from`から古い方向へ1 chunkずつラウンドロビンする（history pass）。
  `sync_state`は`last_synced_date`（前方）と`backfilled_from`（後方）の両端を持つ。
  `replace_chunk()`の`status`/`watermark`は`None`なら「そのcolumnは変更しない」という
  意味（SQL上は真のNULLになり`coalesce()`が既存値を残す）。forward chunkは常に実際に
  到達した日を書くので、中断したrunは取りこぼしなくそこから再開する。history chunkは
  status/watermarkに`None`を渡してこの2列を保つ。`backfill_from`はこの規則の対象外――
  `None`は`start`に置き換わったうえで`least(既存値, start)`により`backfilled_from`へ
  反映されるので、無変更ではなく常に後方へだけ伸びる。物理sendは最大200件（UIで可変）。
  ApiError/PayloadErrorはmetric単位で隔離し`SyncReport.failures`へ記録して続行するが、
  そのmetricはhistory passも含めrun全体から除外される（失敗したpassの残りchunkだけでは
  ない）。AuthError/429/hard capはrun全体を止める。engineへsleep/自動retryを追加しない
  （paceと401 retryはclient責務）。
- testsはfake HTTPとcommitted fixtureだけを使う。live Google Health APIを自動テストで
  呼ばず、実アカウント確認は`health/scripts/probe_datatypes.py`で行う。
- `data/`と`.env`はprivateかつgitignored。token、probe payload、実健康データをcommitしない。
- workspace rootで`uv run --no-sync pytest health/tests`を実行する。UI用の架空DBは
  `seed_demo.py --db-path <temporary path>`で作り、実`health/data/`を上書きしない。
