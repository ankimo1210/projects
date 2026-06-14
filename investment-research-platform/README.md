# investment-research-platform (`irp`)

ローカルで動く**マルチアセット投資リサーチ・プラットフォーム**。無料データのみ・
Jupyter 主体・インタラクティブ可視化・HTML レポートを志向し、**信号研究・モデル比較・
頑健なバックテスト**を重視する。**ライブ取引はしない**(リサーチ専用)。

> **状態: Phase 1 — データ層**。現在はリポジトリ骨格 + configs + データ層
> (コネクタ共通インターフェース・キャッシュ・データ品質診断・**point-in-time マクロ**)まで。
> 特徴量・信号・モデル・バックテスト・税・ポートフォリオ・ダッシュボードは次フェーズ
> ([下記ロードマップ](#ロードマップ))。

## 設計原則(リゴール)

- **look-ahead をしない**。マクロ指標は **release_date 前に使えない**(`irp.macro.store.as_of`)。
- **point-in-time と latest-vintage を分離**(改定値での未来漏れを防ぐ)。
- **silent forward-fill をしない**。欠損は明示し、品質診断で警告する(自動修復しない)。
- スキーマ正規化・メタデータ保持・レート制限・エラーログ・欠損レポート。
- 無料データのみ。複雑なモデルは必ず単純ベースラインと比較(次フェーズ)。

## 構造

```
investment-research-platform/
  configs/   data_sources / universe / tax_japan / model_config / backtest_config (.yaml)
  data/      raw interim point_in_time processed external   (gitignore)
  notebooks/ 01..13     (01-03 実走、04-13 は次フェーズのスタブ)
  src/irp/   data/ macro/ utils/         ← Phase 1 実装済み
             features/ signals/ models/ backtest/ portfolio/ tax/ visualization/  ← スタブ
  tests/
```

パッケージ名は `irp`(`src/irp`)。総称名のトップレベル化を避け namespace 衝突を防ぐ。

## セットアップ

ワークスペース(`~/projects`)の uv メンバー。ルートで:

```bash
uv sync --all-packages          # もしくは: uv pip install -e investment-research-platform
cp investment-research-platform/.env.example investment-research-platform/.env  # キーを記入
```

無料 API キー(任意、MVP では FRED のみ実質必須):
- `FRED_API_KEY` — 米/日マクロ・金利(<https://fred.stlouisfed.org/>)
- `JQUANTS_REFRESH_TOKEN` / `ESTAT_APP_ID` — 日本株・日本マクロ(Phase 2)
- Stooq / US Treasury / CoinGecko / Binance は**キー不要**。

## 使い方(Phase 1)

```python
from irp.data import get_prices, price_panel          # Stooq 主・yfinance フォールバック
spy = get_prices("SPY", "2015-01-01")                 # FetchResult(data, quality, ...)
print(spy.quality.summary())

from irp.macro import FredConnector, as_of, latest    # point-in-time マクロ
f = FredConnector().fetch("us_cpi", "2015-01-01", point_in_time=True)  # ALFRED vintages
print(as_of(f, "2020-03-01").tail())                  # 2020-03-01 時点で見えた CPI のみ
print(latest(f).tail())                               # 最新改定値(ダッシュボード用)
```

ノートブック: `notebooks/01_data_download_and_validation` → `02_asset_universe_builder`
→ `03_macro_data_pipeline`(release-date / point-in-time の実演)。

## データソース(無料)

| 種別 | 主 | 補助 / 予定 |
|---|---|---|
| 株価 OHLCV | Stooq | yfinance(フォールバック・警告付き)、J-Quants(JP, Phase 2) |
| crypto | CoinGecko(価格)/ Binance(OHLCV) | |
| 米マクロ・金利 | FRED / ALFRED、US Treasury | BEA/BLS/Census(Phase 2) |
| 日マクロ | FRED(JP系列) | e-Stat / BoJ / MoF(Phase 2) |
| ファンダ | — | SEC EDGAR / EDINET(Phase 2) |

## テスト

```bash
uv run pytest investment-research-platform/tests -q   # ネット不要(モック/フィクスチャ)
```

リゴール不変条件を検証: **as_of が release_date 超の値を返さない**、point-in-time と latest の分離、
**silent ffill していない**、品質診断が欠損/ギャップ/重複を検出、キャッシュ往復、コネクタ正規化。

## データ制限の警告(重要)

- 個別株ユニバースの**サバイバーシップバイアス**(現存銘柄を手選び)。
- **無料データの品質限界**(欠損・調整差・遅延)。Stooq の adjusted close は近似。
- **ソース可用性**: Stooq は環境によって JavaScript ボット検証ウォールを返し CSV を取得できない
  ことがある。その場合 `get_prices(source="auto")` は自動で **yfinance にフォールバック**する
  (警告を出す)。これはプラットフォームが明示する「無料データの可用性リスク」の実例。
- **マクロは改定される**。point-in-time vintage が無いソースは release_date が推定
  (`vintage_available=False`)。
- **FX/通貨**・**取引所カレンダー差**の取り扱いはバックテスト層(Phase 2)で明示。
- 取引コスト・税・スリッページは**仮定**であり config 化(`configs/`)。
- **過学習リスク**: 全標本でのパラメータ最適化をしない・失敗戦略も提示(Phase 2 方針)。

## ロードマップ(Phase 2 以降)

特徴量 → 信号(trend/value/quality/carry/risk/macro、共通信号スキーマ)→ ラベル →
モデル(Tier0 ベースライン〜Tier4 時系列基盤モデル)→ walk-forward バックテスト
(コスト/スリッページ/税ドラッグ/ターンオーバー/ベンチ/ベースライン比較)→
日本税(NISA)→ ポートフォリオ構築 → Plotly ダッシュボード → NB 04-13 実走 → 最終 HTML レポート。

リサーチ専用。投資助言ではない。
