# investment-research-platform (`irp`)

ローカルで動く**マルチアセット投資リサーチ・プラットフォーム**。無料データのみ・
Jupyter 主体・インタラクティブ可視化・HTML レポートを志向し、**信号研究・モデル比較・
頑健なバックテスト**を重視する。**ライブ取引はしない**(リサーチ専用)。

> **状態: Phase 2b-1 — 評価エンジン**。データ層(Phase 1)+ リサーチ層(Phase 2a:
> **causal 特徴量**・**共通スキーマ信号**・**forward ラベル**)に加え、**walk-forward
> バックテストエンジン**(purge+embargo・ターンオーバー課金・ベースライン/ベンチ比較・
> 指標)まで実装。モデル(Tier0-4)・税(NISA)・ポートフォリオ・ダッシュボードは次フェーズ
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
  notebooks/ 01..13     (01-06 実走、07-13 は次フェーズのスタブ)
  src/irp/   data/ macro/ features/ signals/ labels/ backtest/ utils/   ← 実装済み
             models/ portfolio/ tax/ visualization/  ← スタブ
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

## 使い方(Phase 1–2a)

```python
from irp.data import get_prices, price_panel          # Stooq 主・yfinance フォールバック
spy = get_prices("SPY", "2015-01-01")                 # FetchResult(data, quality, ...)
print(spy.quality.summary())

from irp.macro import FredConnector, as_of, latest    # point-in-time マクロ
f = FredConnector().fetch("us_cpi", "2015-01-01", point_in_time=True)  # ALFRED vintages
print(as_of(f, "2020-03-01").tail())                  # 2020-03-01 時点で見えた CPI のみ
print(latest(f).tail())                               # 最新改定値(ダッシュボード用)
```

```python
# リサーチ層(Phase 2a): causal な特徴量・共通スキーマの信号・forward ラベル
from irp import features as F, signals as S
from irp.labels import forward_return, label_available_date

panel = price_panel(results)                           # dates × assets(前埋めなし)
mom = F.momentum(panel, lookback=252, skip=21)         # feature[t] は t 以前のみに依存

sig = S.momentum_signal(panel)                         # 横断標準化された Signal
w = S.long_short_quantile(sig.lag(1).score, 0.2)       # lag してから使う(同足の先読み回避)
y = forward_return(panel, horizon=21)                  # ラベルは設計上「未来」
avail = label_available_date(panel.index, 21)          # 各ラベルが分かる日(embargo 用)
```

```python
# 評価層(Phase 2b-1): walk-forward バックテスト(リーク無し・コスト・ベースライン比較)
from irp import backtest as B

rets = panel.pct_change(fill_method=None)              # 前埋めしない
held = B.rebalanced(w, "ME")                           # 月次で保持(ターンオーバー抑制)
res = B.run_backtest(held, rets, cost_model=B.CostModel(5, 2), lag=1)  # weights を lag
print(B.summary(res, periods=252))                     # Sharpe/DD/turnover/cost...

base = B.buy_and_hold(rets)                            # 等加重ベンチ代理
print(B.compare({"strategy": res, "equal_weight": base}))   # 必ずベースラインと並べる
folds = B.walk_forward(panel.index, train=252, test=63, horizon=21, embargo=5)  # purge+embargo
```

ノートブック: `01_data_download_and_validation` → `02_asset_universe_builder`
→ `03_macro_data_pipeline`(point-in-time)→ `04_feature_engineering`(causal 特徴量+因果性の実証)
→ `05_signal_research_baselines`(共通信号スキーマ・合成・L/S spread の診断)
→ `06_factor_backtest`(walk-forward・コスト・ベースライン比較・コスト感応度)。

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

## ロードマップ

- **Phase 1(完了)** — データ層:コネクタ共通 IF・キャッシュ・品質診断・point-in-time マクロ。
- **Phase 2a(完了)** — リサーチ層:**causal な特徴量**(`irp.features`)・**共通スキーマの信号**
  (`irp.signals`、trend/risk/macro ベースライン+ value/quality/carry のデータ待ちスタブ)・
  **forward ラベル**(`irp.labels`、embargo 用の `label_available_date`)。NB 04–05 実走。
- **Phase 2b-1(完了)** — 評価エンジン:**walk-forward バックテスト**(`irp.backtest`、
  purge+embargo の分割・ターンオーバー課金のコストモデル・lag した weights・指標・
  ベースライン/ベンチ比較)。NB 06 実走。
- **Phase 2b-2(次)** — モデル(Tier0 ベースライン〜Tier4 時系列基盤モデル、fold ごとに学習し
  同じエンジン/コスト/ベースラインで評価)→ 日本税(NISA、after-tax ドラッグ)→ ポートフォリオ構築
  → Plotly ダッシュボード → NB 07–13 実走 → 最終 HTML レポート(失敗戦略も提示)。

リサーチ専用。投資助言ではない。
