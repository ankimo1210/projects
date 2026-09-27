# stockkit テスト整備 — 設計

- **日付**: 2026-06-01
- **対象**: `stock/` (stockkit)
- **状態**: 設計（承認待ち）

## 背景

`stock/tests/` にテストソースが存在せず、`__pycache__` に削除済み
`test_earnings` / `conftest` のバイトコードだけが残っている。ワークスペースの
Definition of Done（全テスト通過・新挙動には落ちるテスト）に対して未達。
本作業で **決定論コアの回帰テスト基盤**を新設し、`make test` を緑にする。

## ゴール

1. 外部APIに触れない純粋ロジックを回帰テストで固める。
2. yfinance依存の分析関数も、プロバイダ呼び出しをmonkeypatchして実ネットワーク無しでテストする。
3. pytest基盤（`conftest.py` + `pyproject.toml` 設定）を整備する。
4. `__version__` の不整合（0.1.0 → 0.4.0）を解消する。

## 方針：ハイブリッド検証（承認済み: 案C）

- **コア数式**は既知の小さい系列に対する**手計算リファレンス値**で厳密検証
  （CLAUDE.md DoD「手計算/参照値と照合」に直結）。
- **構造・境界・no-lookahead 等の性質**は**不変条件**で堅牢化（リファクタ耐性）。
- 浮動小数比較は `pytest.approx` / `numpy.testing.assert_allclose` を用いる。

## スコープ

### 対象モジュールと検証内容

#### 1. 純粋ロジック（ネットワーク非依存）

| モジュール | 関数 | 検証内容 |
|---|---|---|
| `data/symbols` | `normalize_symbol`, `is_japanese` | 4桁→`.T`、大文字化、前後空白除去、`AAPL`/`BRK-B`素通り、`7203.T`/`.JP`の `is_japanese=True`、`AAPL`は`False` |
| `analysis/technical` | `sma`, `ema`, `rsi`, `macd`, `bollinger`, `atr`, `returns`, `add_indicators`, `signal_golden_cross` | 手計算値一致（SMAは単純平均、RSIは既知系列）。先頭NaN本数（`sma(20)`→19個）、出力列名（`macd`/`signal`/`hist`等）、index一致。`add_indicators`は期待列が全て付与。`signal_golden_cross`はクロス時に+1/-1 |
| `analysis/backtest` | `run`, `signal_sma_cross`, `signal_rsi_reversion`, `signal_macd_cross`, `signal_donchian`, `_metrics` | 合成価格でequity手計算一致。**no-lookahead**（当日シグナル→翌日約定: positionは1barシフト）。flatシグナル→equity一定・trades空。手数料/スリッページで建玉日にコスト控除。`metrics`キー存在と `max_drawdown<=0`、`bars==len` |
| `analysis/portfolio` | `daily_returns`, `cumulative_returns`, `annualized_return`, `annualized_vol`, `sharpe`, `max_drawdown`, `correlation`, `weighted_portfolio` | 既知2銘柄パネルで数値検証。`weighted_portfolio`のweight正規化（合計1、Noneで等加重）、`max_drawdown<=0`、相関対角=1 |
| `analysis/fundamental` | `yoy_growth` | yfinance由来の降順index→昇順pct_change。空DataFrame/欠損行で空Series（削除された `test_earnings` の実質復活） |
| `analysis/screener` | rule factory: `pe_below`, `roe_above`, `dividend_yield_above`, `above_sma`, `rsi_between` | snap/pricesに対する真偽判定。`None`値・空pricesで安全にFalse。閾値境界 |
| `data/cache` | `upsert_prices`→`read_prices`, `upsert_macro`→`read_macro`, `latest_cached_date`, `latest_macro_date`, start/end フィルタ | 一時DuckDBへの読み書き往復一致。`INSERT OR REPLACE`の冪等性（同一PK再投入で重複しない・値更新）。空入力で0行 |

#### 2. yfinance依存（プロバイダをmonkeypatchしてテスト）

| モジュール | 関数 | モック対象（**lookup側**を patch） |
|---|---|---|
| `analysis/portfolio` | `price_panel` | `stockkit.analysis.portfolio.get_prices` をフィクスチャ価格で差し替え。wideパネル組み立て・空銘柄スキップ・全空で空DataFrame |
| `analysis/fundamental` | `snapshot`, `snapshot_df`, `revenue_growth_history`, `net_income_history` | `stockkit.analysis.fundamental.get_info` / `get_financials`。`_INFO_FIELDS`マッピング（候補fallback順、欠損→None）、財務行のソート |
| `analysis/screener` | `screen` | `stockkit.analysis.screener.fundamental.snapshot` と `stockkit.analysis.screener.get_prices`。ルール合致行のみ返す・例外時False・全不一致で空DataFrame |

> **重要（CLAUDE.md gotcha）**: これらは `from ... import get_prices` 等で取り込まれているため、
> 定義元（`yfinance_provider`）ではなく**参照される名前空間側**を monkeypatch する。

### スコープ外（今回やらない）

- raw プロバイダ層（`yfinance_provider` / `fred_provider` / `estat_provider` /
  `jquants_provider` / `stooq_provider`）の**HTTPレスポンス解析**テスト → 別フェーズ。
- `data.get_prices` / `get_macro` のキャッシュ往復オーケストレーション → 別フェーズ。
- `analysis/basket`（shares outstanding取得の並列処理を含む重い経路）→ 別フェーズ。
- Dash ページ / Flask API / AI chat（`app/`）→ 別フェーズ。

## テスト基盤

### ディレクトリ

```
stock/tests/
  __init__.py
  conftest.py
  test_symbols.py
  test_technical.py
  test_backtest.py
  test_portfolio.py
  test_fundamental.py        # yoy_growth + mocked snapshot系
  test_screener.py
  test_cache.py
```

### `conftest.py` の要点

- **cache用一時DB fixture（gotcha対応）**: `cache._DEFAULT_DIR` は**import時に確定する
  モジュール定数**であり、`STOCKKIT_DATA_DIR` 環境変数を後から設定しても効かない。
  そのため fixture で `monkeypatch.setattr(cache, "_DEFAULT_DIR", tmp_path)` により
  直接差し替える。
- **共通フィクスチャ**: 合成OHLCV DataFrame（決まった日付index・既知の値）を生成する
  ヘルパー、2銘柄の価格パネル、yfinance風 info dict / financials DataFrame。

### `pyproject.toml` 追加

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "network: tests that require live network access (deselected by default)",
]
```

`pytest>=8.3` は既に dev 依存に存在。`network` マーカーは将来のプロバイダテスト用に
予約のみ（今回は未使用）。

## バージョン修正（Q3）

- `src/stockkit/__init__.py`: `__version__ = "0.1.0"` → `"0.4.0"`
- `pyproject.toml`: `version = "0.1.0"` → `"0.4.0"`
- （CHANGELOG最新は 0.4.0 のため両者を一致させる。本テスト作業とは独立した小コミット）

## 検証 / Definition of Done

1. `cd ~/projects && uv run --no-sync pytest stock/tests -v` が全green。実出力を1-3行引用して報告。
2. ワークスペース全体 `make test` が green（既存他プロジェクトを壊していない）。
3. `make lint` が green（新規テストが ruff を通る）。
4. `yoy_growth` テストは現コードで通り、降順→昇順ソートを削った改変で**落ちる**ことを確認（回帰性の担保）。

## 想定リスク / 留意点

- yfinance依存関数のテストは「現状の実装挙動の固定」になりがち。手計算で意味の確認できる
  入出力（フィールドマッピング、ソート方向）に絞り、過剰な固定化は避ける。
- DuckDBの一時DBはテスト毎に破棄（`tmp_path`）。並列実行でも衝突しない。
