# quantkit

ローカルで動く**マルチアセット投資リサーチ・プラットフォーム**。無料データのみ・
Jupyter 主体・インタラクティブ可視化・HTML レポートを志向し、**信号研究・モデル比較・
頑健なバックテスト**を重視する。**ライブ取引はしない**(リサーチ専用)。

> **状態: 全マイルストーン完了**。データ → リサーチ(features / **6信号ファミリ** / labels)→
> 評価エンジン(walk-forward backtest)→ **モデル Tier0-4**(baseline/linear/tree/MLP/時系列+Chronos
> アダプタ)→ ポートフォリオ → **基軸通貨 FX 換算** → 可視化/HTML → **日本税(NISA・配当)**。
> データは **全コネクタ実装済**(米/JP株・crypto・米/JPマクロ・金利・ファンダ SEC EDGAR/EDINET)。
> 無キーソースは**ライブ実証済**(SEC EDGAR / yfinance / Binance / US Treasury、`QUANTKIT_LIVE=1`)。
> NB 01–13 全実走・**128 tests**(+7 live、既定スキップ)。残るは鍵が要るソースのライブ確認のみ。

## 設計原則(リゴール)

- **look-ahead をしない**。マクロ指標は **release_date 前に使えない**(`quantkit.macro.store.as_of`)。
- **point-in-time と latest-vintage を分離**(改定値での未来漏れを防ぐ)。
- **silent forward-fill をしない**。欠損は明示し、品質診断で警告する(自動修復しない)。
- スキーマ正規化・メタデータ保持・レート制限・エラーログ・欠損レポート。
- 無料データのみ。複雑なモデルは必ず単純ベースラインと比較し、失敗した戦略も提示する。

## 構造

```
quantkit/
  configs/   data_sources / universe / tax_japan / model_config / backtest_config (.yaml)
  data/      raw interim point_in_time processed external   (gitignore)
  notebooks/ 01..13     (すべて実走)
  src/quantkit/   data/ macro/ features/ signals/ labels/ backtest/ models/ portfolio/ tax/ visualization/ utils/
             ← すべて実装済み
  fundamentals は data/fundamentals.py(SEC EDGAR、point-in-time by filing date)
  tests/
```

パッケージ名は `quantkit`(`src/quantkit`)。総称名のトップレベル化を避け namespace 衝突を防ぐ。

## セットアップ

ワークスペース(`~/projects`)の uv メンバー。ルートで:

```bash
uv sync --all-packages          # もしくは: uv pip install -e quantkit
cp quantkit/.env.example quantkit/.env  # キーを記入
```

無料 API キー(任意、用途別):
- `FRED_API_KEY` — 米/日マクロ・金利(<https://fred.stlouisfed.org/>)
- `JQUANTS_REFRESH_TOKEN` — 日本株 OHLCV / `ESTAT_APP_ID` — 日本マクロ(無料登録)
- `SEC_USER_AGENT` — SEC EDGAR ファンダ取得用の連絡先(SEC の規約で必須、キーは不要)
- `BLS_API_KEY`(任意)/ `BEA_API_KEY` / `CENSUS_API_KEY` — 米政府統計 / `EDINET_API_KEY` — JP 開示
- `COINGECKO_API_KEY` — CoinGecko は無料 **demo キー**必須化(無ければ 401)
- Stooq / US Treasury / Binance は**キー不要**(crypto は full OHLCV の Binance 推奨)。

## 使い方

```python
from quantkit.data import get_prices, price_panel          # Stooq 主・yfinance フォールバック
spy = get_prices("SPY", "2015-01-01")                 # FetchResult(data, quality, ...)
print(spy.quality.summary())

from quantkit.macro import FredConnector, as_of, latest    # point-in-time マクロ
f = FredConnector().fetch("us_cpi", "2015-01-01", point_in_time=True)  # ALFRED vintages
print(as_of(f, "2020-03-01").tail())                  # 2020-03-01 時点で見えた CPI のみ
print(latest(f).tail())                               # 最新改定値(ダッシュボード用)
```

```python
# リサーチ層(Phase 2a): causal な特徴量・共通スキーマの信号・forward ラベル
from quantkit import features as F, signals as S
from quantkit.labels import forward_return, label_available_date

panel = price_panel(results)                           # dates × assets(前埋めなし)
mom = F.momentum(panel, lookback=252, skip=21)         # feature[t] は t 以前のみに依存

sig = S.momentum_signal(panel)                         # 横断標準化された Signal
w = S.long_short_quantile(sig.lag(1).score, 0.2)       # lag してから使う(同足の先読み回避)
y = forward_return(panel, horizon=21)                  # ラベルは設計上「未来」
avail = label_available_date(panel.index, 21)          # 各ラベルが分かる日(embargo 用)
```

```python
# 評価層(Phase 2b-1): walk-forward バックテスト(リーク無し・コスト・ベースライン比較)
from quantkit import backtest as B

rets = panel.pct_change(fill_method=None)              # 前埋めしない
held = B.rebalanced(w, "ME")                           # 月次で保持(ターンオーバー抑制)
res = B.run_backtest(held, rets, cost_model=B.CostModel(5, 2), lag=1)  # weights を lag
print(B.summary(res, periods=252))                     # Sharpe/DD/turnover/cost...

base = B.buy_and_hold(rets)                            # 等加重ベンチ代理
print(B.compare({"strategy": res, "equal_weight": base}))   # 必ずベースラインと並べる
folds = B.walk_forward(panel.index, train=252, test=63, horizon=21, embargo=5)  # purge+embargo
```

```python
# モデル層(Phase 2b-2): 共通 fit/predict・fold ごとに学習し OOS 予測
from quantkit import models as MD

feats = {"mom": F.momentum(panel), "z": F.rolling_zscore(panel, 20)}
X, y = MD.make_design(feats, forward_return(panel, 5))      # (date, asset) スタック・前埋めなし
pred = MD.walk_forward_predict(lambda: MD.ridge(), X, y, folds)   # 各 fold で fresh に学習(OOS)
pred_panel = MD.predictions_to_panel(pred)                  # → dates × assets に戻す
# Tier0 baselines: MD.ZeroModel/MeanModel/PersistenceModel — 複雑モデルはこれを OOS で超える必要
```

```python
# ポートフォリオ構築(Phase 2b-3): 制約付き最適化で weight を作る(素朴な quantile を置換)
from quantkit import portfolio as PF

cons = PF.Constraints.from_config(load_config("backtest_config"))   # gross/name cap/long-only…
w = PF.build_weights(rets, method="risk_parity", constraints=cons,  # equal/inverse_vol/
                     lookback=63, rebalance="ME")                   # risk_parity/min_variance/mean_variance
res = B.run_backtest(w, rets, cost_model=B.CostModel(5, 2), lag=1)  # 同じエンジンで評価
```

```python
# 日本税(Phase 2b-3): after-tax リターン・課税口座 vs NISA
from quantkit import tax as TX

taxable = TX.TaxConfig.from_config(load_config("tax_japan"))  # 譲渡益 20.315% 等(仮定)
TX.annual_after_tax(res.returns, taxable)                     # 年次 gross→after-tax(損失繰越)
print(TX.compare_accounts(res.returns, taxable))             # pre-tax vs 課税 vs NISA(非課税)
```

```python
# 可視化 & レポート(Phase 2b-3): Plotly 図 + オフライン自己完結 HTML
from quantkit import visualization as V

results = {"strategy": res, "equal_weight": base}
V.equity_curves(results).show()                            # ノートブックで対話的に
V.strategy_report(                                         # 単一 HTML(plotly.js inline・CDN 不要)
    results, "reports/strategy_report.html",
    title="My strategy vs baseline", ic=ic_series, cost_sweep=sweep_df,
)
```

ノートブック: `01_data_download_and_validation` → `02_asset_universe_builder`
→ `03_macro_data_pipeline`(point-in-time)→ `04_feature_engineering`(causal 特徴量+因果性の実証)
→ `05_signal_research_baselines`(共通信号スキーマ・合成・L/S spread の診断)
→ `06_factor_backtest`(walk-forward・コスト・ベースライン比較・コスト感応度)
→ `07_machine_learning_models`(Tier0-2・OOS 予測・IC・ベースライン比較)
→ `08_deep_learning_models`(Tier3 MLP を同一 walk で比較)
→ `09_time_series_foundation_models`(Tier4 古典予測器 + 基盤モデルの任意アダプタ)
→ `10_portfolio_construction`(制約付き最適化・risk parity 等リスク寄与の確認)
→ `11_tax_aware_backtest`(after-tax・課税口座 vs NISA・損失繰越)
→ `12_interactive_dashboard`(Plotly 図群)→ `13_final_strategy_report`(オフライン HTML 出力)。

## データソース(無料)

すべて実装済み(★=無キーでライブ実証済 / 鍵が要るものはオフライン fixture テストでパーサ検証):

| 種別 | 主 | 補助 |
|---|---|---|
| 株価 OHLCV(米/グローバル) | Stooq → ★yfinance(自動フォールバック) | |
| 株価 OHLCV(日本) | J-Quants(要 refresh token) | |
| crypto | ★Binance(full OHLCV, 無キー) | CoinGecko(価格のみ, 要 demo キー) |
| 米マクロ・金利 | FRED/ALFRED、★US Treasury | BLS(任意キー)/ BEA・Census(要キー) |
| 日マクロ | e-Stat(要 app id)、FRED(JP系列) | BoJ / MoF(無キー CSV) |
| ファンダ | ★SEC EDGAR(companyfacts, point-in-time) | EDINET(要キー, 書類 discovery) |

## テスト

```bash
uv run pytest quantkit/tests -q          # 128 passed, 7 skipped(ネット不要)
QUANTKIT_LIVE=1 uv run pytest quantkit/tests/test_live.py -q   # 実 API スモーク
```

リゴール不変条件を検証: **as_of が release_date 超の値を返さない**、point-in-time と latest の分離、
**silent ffill していない**、因果性(`func(x[:k])==func(x)[:k]`)、リーク無し fold、OOS recovery、
品質診断が欠損/ギャップ/重複を検出、コネクタ正規化。**ライブテスト**(`QUANTKIT_LIVE=1`、既定スキップ)は
無キーソース(SEC EDGAR/yfinance/Binance/US Treasury)を実 API で検証(鍵が要るものは鍵がある時のみ)。

## データ制限の警告(重要)

- 個別株ユニバースの**サバイバーシップバイアス**(現存銘柄を手選び)。
- **無料データの品質限界**(欠損・調整差・遅延)。Stooq の adjusted close は近似。
- **ソース可用性**: Stooq は環境によって JavaScript ボット検証ウォールを返し CSV を取得できない
  ことがある。その場合 `get_prices(source="auto")` は自動で **yfinance にフォールバック**する
  (警告を出す)。これはプラットフォームが明示する「無料データの可用性リスク」の実例。
- **マクロは改定される**。point-in-time vintage が無いソースは release_date が推定
  (`vintage_available=False`)。
- **FX/通貨換算**: `quantkit.data.to_base_currency` で基軸通貨へ換算(前埋め無し)。取引所カレンダー差は
  `price_panel` の union 日付・欠損 NaN で扱う。
- **ソース可用性は変わる**(ライブで判明): CoinGecko は無料 API が demo キー必須化(401)、Stooq は
  JS ウォール。無キー crypto は Binance(full OHLCV)を推奨。
- **鍵が要るソースはライブ未検証**: J-Quants/e-Stat/FRED/BEA/Census/EDINET は実 API 契約に実装し
  **オフライン fixture でパーサのみ検証**(鍵を入れた実取得は要確認)。EDINET は書類 discovery まで
  (XBRL からの財務数値抽出は次段)。BoJ/MoF の CSV 書式は変わり得る(URL/列はパラメータ化)。
- 取引コスト・税・スリッページは**仮定**であり config 化(`configs/`)。
- **過学習リスク**: 全標本でのパラメータ最適化をしない・複雑モデルは必ずベースラインと比較・
  失敗戦略も提示(walk-forward + purge/embargo + `compare` で担保)。
- **税モデルは年次 mark-to-market 近似**(長期保有では実際の実現課税よりドラッグ過大)。NISA の
  円建て枠・外国源泉税は未モデル。投資助言ではない。

## ロードマップ

- **Phase 1(完了)** — データ層:コネクタ共通 IF・キャッシュ・品質診断・point-in-time マクロ。
- **Phase 2a(完了)** — リサーチ層:**causal な特徴量**(`quantkit.features`)・**共通スキーマの信号**
  (`quantkit.signals`、**全6ファミリ** trend/value/quality/carry/risk/macro)・**forward ラベル**
  (`quantkit.labels`、embargo 用の `label_available_date`)。NB 04–05 実走。
- **Phase 2b-1(完了)** — 評価エンジン:**walk-forward バックテスト**(`quantkit.backtest`、
  purge+embargo の分割・ターンオーバー課金のコストモデル・lag した weights・指標・
  ベースライン/ベンチ比較)。NB 06 実走。
- **Phase 2b-2(完了)** — モデル(`quantkit.models`):共通 fit/predict、**Tier0 ベースライン**
  (zero/mean/persistence)・**Tier1 linear**(ridge/lasso/elastic_net)・**Tier2 tree**
  (random_forest/gradient_boosting)・**Tier3 neural**(`mlp`)・**Tier4 時系列**(seasonal-naive /
  AR + 基盤モデルの import-gated アダプタ)。`make_design` で (date,asset) 設計行列、
  `walk_forward_predict` で fold ごとに学習し OOS 予測 → 評価エンジンへ。NB 07–09 実走。
- **Phase 2b-3a(完了)** — 可視化 & レポート(`quantkit.visualization`):統一テーマの Plotly 図群
  (equity/drawdown/指標表/分布/rolling Sharpe/IC/コスト感応度)+ **オフライン自己完結 HTML**
  (`strategy_report`、plotly.js を inline 埋め込み)。NB 12–13 実走。
- **Phase 2b-3b(完了)** — ポートフォリオ構築(`quantkit.portfolio`):equal / inverse-vol /
  risk parity(等リスク寄与, SLSQP)/ min-variance / mean-variance、**制約射影**(water-filling で
  gross 上限・名柄上限・long-only・目標 vol)、`build_weights` で causal な月次保持パネル。NB 10 実走。
- **Phase 2b-3c(完了)** — 日本税(`quantkit.tax`):年次 mark-to-market の譲渡益課税 + **配当課税** +
  3年損失繰越、課税口座 vs **NISA**(非課税)の after-tax 比較、`compare_accounts`。NB 11 実走。
- **Phase 2c(完了)** — 広さの拡充:全6信号ファミリ・モデル Tier3-4・配当課税、
  **全データコネクタ**(J-Quants / e-Stat / SEC EDGAR / BoJ / MoF / BLS / BEA / Census / EDINET、
  スタブ無し)、**基軸通貨 FX 換算**(`to_base_currency`)、**Chronos アダプタ**(`load_foundation`、
  monkeypatch で配線検証)、**ライブ実証**(無キーソースを実 API で、`QUANTKIT_LIVE=1`)。
- **任意の後続(検証/深掘り)** — 鍵が要るソースのライブ確認(キー入手後)、EDINET の XBRL から
  財務数値抽出、BoJ/MoF の実 CSV 書式追従、Chronos の GPU 実行。いずれも契約・配線は確定済み。

リサーチ専用。投資助言ではない。
