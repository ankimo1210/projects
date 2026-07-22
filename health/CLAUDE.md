# health — Claude Code Guide

Google Health APIを使う個人向けダッシュボード。応答は日本語、code/identifier/commitは英語。

- `src/health/`がcore（endpoints → auth/client → store → sync → inventory）、
  `app/`は薄いStreamlit UI。viewからAPI/IO契約を実装しない。
- `endpoints.py`の14-entry `CATALOG`が実装metricのsingle source of truth。
  API shapeは`.superpowers/sdd/health-google-api-contracts.md`に従う。
- `dailyRollUp`は1 payload、`reconcile`は全pageを取得してからparseする。途中pageを
  保存済みとして扱わない。
- raw pages、typed rows、watermarkは`Store.replace_chunk()`でchunk単位に原子的置換する。
  upstream deletionやempty responseでも、成功したchunkは古い行を正しく消す。
- sync runはHealth APIへの物理sendを最大200件に制限する。429とhard capでは完了chunk
  だけを残して再開可能にする。engineへsleep/自動retryを追加しない（paceと401 retryはclient責務）。
- testsはfake HTTPとcommitted fixtureだけを使う。live Google Health APIを自動テストで
  呼ばず、実アカウント確認は`health/scripts/probe_datatypes.py`で行う。
- `data/`と`.env`はprivateかつgitignored。token、probe payload、実健康データをcommitしない。
- workspace rootで`uv run --no-sync pytest health/tests`を実行する。UI用の架空DBは
  `seed_demo.py --db-path <temporary path>`で作り、実`health/data/`を上書きしない。
