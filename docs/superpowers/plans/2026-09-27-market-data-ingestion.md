# Market Data Ingestion and Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 未確定足の不具合を修正し、明示取得→不変snapshot→価格/マクロの時点別保存→オフライン読取を接続する。

**Architecture:** 既存の不変契約を維持し、価格選択には除外理由を返す API を追加する。取得器は通信・日足時刻解決・正規化を分離し、DuckDB の transaction と content hash で snapshot と行を結び付ける。CLI の fetch のみが通信し、query は保存済みの版だけを使う。

**Tech Stack:** Python 3.12、uv、pandas、DuckDB、yfinance、pytest。DuckDB/yfinance は既存 workspace 依存。取引所カレンダーの新規依存 exchange-calendars は本人の回答待ちで、承認されるまで追加しない。

**Spec:** [統合仕様](../specs/2026-09-27-market-research-design.md) §5、Q01–Q08。これは工程3bの価格取得・保存部分。外部マクロ/財務取得器の移植（ALFRED/ESRI/MoF/SEC/e-Stat）は別の実装単位として STATUS に残す。

## Global Constraints

- 口座情報、旧DB、個人watchlistを読まない。共有main、定時タスク、portfolio-analyzerを変更しない。
- Gitに入れるfixtureは合成のみ。live/cacheの既定値は cwd に依存しない WSL の Git 管理外領域。
- UTC日時、provider・市場ID・調整方式・通貨・契約版を保存し、後日訂正は追記する。
- 取得失敗に credential・URLクエリ・response bodyを出さない。401/403・429・5xx・空応答・schemaを区別。
- 旧入口の切替・アーカイブ・データ移管は今回実施しない。新規 production 依存の回答は経過時間で代替しない。

## Review Focus

- 前日確定足と14:00 JSTの当日未確定足が同居しても、前日を読め、当日を除外理由付きで追跡できる。
- 未確定snapshotを翌日に読むだけで確定足へ昇格させない。後の確定revisionを別観測として保存する。
- 同じ価格symbolの市場・provider・通貨・調整方式が違うと保存先と問い合わせが分離される。
- 同時刻・同revisionの異なる値は衝突し、途中失敗・再試行で部分保存を完成扱いしない。
- 休日・短縮取引・DST・429と長いRetry-Afterを、通常取引日や成功応答へ置き換えない。

### Task 1: Partial bars and auditable selection

**Files:** Modify `market-research/src/market_research/contracts.py`, `prices.py`; tests `test_contracts.py`, `test_prices.py`.

**Interfaces:** `price_view_as_of(bars, decision_at, adjustment=None) -> PriceView(bars, exclusions)`; `PriceExclusion(bar, reason)`。既存 `select_bars_as_of` は tuple 戻り値を保ち除外件数をログに残す。

- [x] 次の回帰を追加し、pytestで失敗を確認する。
```python
partial = replace(final, is_final=False, available_at=intraday, observed_at=intraday)
view = price_view_as_of([previous, partial], intraday)
assert view.bars == (previous,)
assert view.exclusions[0].reason == "non_final"
assert not price_view_as_of([partial], tomorrow).bars
```
- [x] Run: `uv run --no-sync pytest market-research/tests/test_prices.py market-research/tests/test_contracts.py -q`。Expected: 新規API欠如または未確定時刻のValueErrorでFAIL。
- [x] 確定足だけに `available_at >= bar_end` を要求。未確定足は足開始前の観測を拒否。選択時に未確定を除外し構造化理由を返す。既存の重複/競合/調整方式エラーは維持。
- [x] 同コマンドを実行。Expected: PASS。ruff/pre-commitを通し `fix(market-research): retain and audit unfinished bars` とコミット。

### Task 2: Immutable snapshot and transactional PIT store

**Files:** Create `market-research/src/market_research/storage.py`, `tests/test_storage.py`; modify member `pyproject.toml`, workspace `uv.lock`.

**Interfaces:** `CacheKey(provider,dataset,identity,interval,currency,adjustment,schema_version=1)`; `ResearchStore(root)`; `save(key, raw, observed_at, prices=(), macro=(), complete=True, cursor=None) -> Snapshot`; `latest_snapshot(key, now, max_age, allow_stale=False)`; `price_view(instrument_id,provider,when,adjustment)`; `macro_view(indicator,when,source)`。

- [x] 一時フォルダで不変性、同じ入力の冪等性、後日revision、provider差、UTC、同revision競合、transaction rollback、hash破損、partial snapshot拒否をテストする。
```python
first = store.save(key, b"v1", observed_at=t1, prices=(original,))
assert store.save(key, b"v1", observed_at=t1, prices=(original,)).snapshot_id == first.snapshot_id
store.save(key, b"v2", observed_at=t2, prices=(revision,))
assert store.price_view("XTKS:7203", "yfinance", t1, "raw").bars == (original,)
```
- [x] Run: `uv run --no-sync pytest market-research/tests/test_storage.py -q`。Expected: モジュール未作成でFAIL。
- [x] DuckDBを既存workspace版から追加。rawはSHA256パスで不変保存、manifestと各行は単一transaction。重複キーの内容が違う場合rollback。保存前後のhash一致を確認し、再開cursorとcompleteをmanifestへ保存。
- [x] 同コマンドおよび既存suite。Expected: PASS。`feat(market-research): persist immutable snapshots and PIT rows` とコミット。

### Task 3: Price fetchers with bounded transport and session timing

**Files:** Create `market-research/src/market_research/fetch.py`, `calendars.py`, `providers.py`; tests `test_fetch.py`, `test_providers.py`, `test_calendars.py`。

**Interfaces:** `HttpClient.get(url,params,headers) -> bytes`; `FetchError.category`; `PriceRequest(instrument,provider_symbol,start,end)`; `fetch_prices(provider,request,...) -> PriceBatch(raw,bars,observed_at,complete)`; `daily_timings(labels,instrument,observed_at)`。

- [x] 注入したtransportに401/403/429/5xx/timeout/空bodyを返させ、試行回数・Retry-After・secret非露出をテスト。J-Quants V2分页終端と上限、Binance開いた日足、yfinance MultiIndex、Stooq unknown adjustmentをfixtureで確認。
```python
with pytest.raises(FetchError, match="authentication"):
    client.get("https://example.test", params={"api_key": "secret"})
assert "secret" not in captured_error
```
- [x] Run: `uv run --no-sync pytest market-research/tests/test_fetch.py market-research/tests/test_providers.py market-research/tests/test_calendars.py -q`。Expected: 未実装でFAIL。
- [x] HTTPは最大3回、timeout10秒。Retry-Afterが待機上限を超えたら早く再送せず失敗。価格の調整方法をsourceごとに保持。日米株カレンダーは承認済み依存または明示スケジュールで解決、cryptoはUTC24時間、FXは確認できない日足を確定扱いしない。
- [x] 同コマンドと全member suite。Expected: PASS。`feat(market-research): fetch prices with explicit timing and provenance` とコミット。

### Task 4: Explicit fetch and offline query workflow

**Files:** Modify `cli.py`, README、STATUS、整理計画; create `ingestion.py`, `tests/test_ingestion.py`。

**Interfaces:** `ingest_prices(store,provider,request,allow_stale=False) -> IngestResult(snapshot,view,stale,error)`; CLI `fetch-prices`, `prices`, `snapshots`。

- [x] 合成transportの取得→保存→process再起動相当の再open→as-of読取、失敗時の明示stale fallback、キャッシュだけの読取で通信なしをテスト。
```python
result = ingest_prices(store, "stooq", request)
assert not result.stale
assert query_after_reopen == result.view.bars
```
- [x] Run: `uv run --no-sync pytest market-research/tests/test_ingestion.py -q`。Expected: 未実装でFAIL。
- [x] 既定rootを `~/.local/share/market-research` に固定。queryでは通信しない。stdoutのJSONに品質・除外件数・stale・raw hashを含める。ドキュメントでfixture成功とlive疎通を分け、既知不具合の解消と工程3bの残件を記録。
- [x] member suite、ruff、pre-commit、相対リンク、CLI smoke。キー不要の公開価格を小範囲で明示取得し、失敗もsourceごとに記録。Expected: テストPASS、live成否は事実どおり。
- [x] `feat(market-research): expose explicit fetch and offline queries` とコミット。

## 仕上げ

- [x] 独立review後、重要指摘を修正し検証。

2026-09-27、ブランチ `codex/market-data-stage3b` で本計画の価格取得・保存部分を実装済み。
工程3b全体は外部マクロ/財務の移植などが残る。
実装コミット: `71d42e9e` / `0effe339` / `7ba1f567` / `d3f65c28`、および後続のレビュー修正。
[レビュー記録](../../../market-research/docs/STAGE3B_REVIEW.md)と
[現在の進捗](../../../market-research/docs/STATUS.md)を参照。
レビュー用ブランチをpushし、mainへの取込みはレビュー後に行う。
