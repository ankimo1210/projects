# johnhull Coverage Roadmap — Hull 11e (37 chapters)

Spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

| # | Volume | Chapters | Status |
|---|--------|----------|--------|
| — | `notebooks/bsm_chapter15.ipynb` | 15 | done |
| — | `interest_rate_models/ir_models.ipynb` | 31, 32, 33 | done |
| 1 | `volumes/01_foundations` | 13, 14 | done |
| 2 | `volumes/02_options_basics` | 10, 11, 12, 17, 18 | done |
| 3 | `volumes/03_greeks` | 19 | done |
| 4 | `volumes/04_futures_forwards_rates` | 2, 3, 4, 5, 6 | done |
| 5 | `volumes/05_vol_smile_estimation` | 20, 23 | done |
| 6 | `volumes/06_numerical_methods` | 21, 27 | done |
| 7 | `volumes/07_swaps` | 7, 34 | done |
| 8 | `volumes/08_risk_var` | 22 | done |
| 9 | `volumes/09_credit_xva` | 9, 24, 25 | done |
| 10 | `volumes/10_exotics_martingales` | 26, 28 | done |
| 11 | `volumes/11_ir_derivatives_market` | 29, 30 | done |
| 12 | `volumes/12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | done |

Shared module: `johnhull/hullkit` (uv workspace member) — bsm, trees, mc, nbplot, payoffs, hedging, rates, volatility, fd, swaps, risk, credit, exotics, ir_options.

**Status (2026-06-08): all 14 rows done → Hull 11e all 37 chapters covered.**

## 可視化 & 深掘り(A1–A4) — 完了 (2026-06-14)

全5巻(13–17)が build スクリプト生成・nbconvert 実行済み・book/portal 登録済み。
hullkit に 10 新モジュール(sde/heston/fourier/sabr/mc_advanced/fd_advanced/aad/xva/copula/plotly_viz)、
ポータル **30 図/7 テーマ**(`make hull-report`)、Jupyter Book 20 ページ(`make hull-book`)。全テスト緑。
追加可視化(深掘り外の既存 hullkit 関数): ガンマ曲面・ストップロス vs デルタ・二項木格子・GARCH(クラスタリング/期間構造)・Merton 構造模型・分散投資・イールドカーブ・債券コンベクシティ・スワップ par・バリア・アジアン。

Hull の射程の先(同じクオンツ系で Hull が浅い領域)を深掘りしつつ、既存 + 新規の全コンテンツを
インタラクティブ可視化する取り組み。すべて johnhull 内で完結。

- **可視化基盤**: `hullkit.plotly_viz`(既存の bsm/trees/hedging/risk/credit をラップする `plotly_*` ビルダー)。
- **HTML/ポータル**: `johnhull/report`(jinja2 + plotly, オフライン自己完結) → `make hull-report`。
  `johnhull/book`(全ボリュームを束ねる Jupyter Book) → `make hull-book`。

| # | Volume | テーマ(Hull の先) | Status |
|---|--------|------|--------|
| P1 | 既存全14ノートの可視化 | `plotly_viz` 6 図 + ポータル疎通(offline test 緑) | done |
| 13 | `volumes/13_stochastic_calculus` | A1 確率解析(伊藤・Girsanov・Feynman-Kac) | **done**(21セル・実行済・book登録) |
| 14 | `volumes/14_stoch_vol_fourier` | A2 確率ボラ & Fourier(Heston/SABR/COS) | **done**(19セル・実行済・book登録) |
| 15 | `volumes/15_advanced_numerics` | A3 高度な数値(分散減少/QMC/LSM/CN/AAD) | **done**(15セル・実行済・book登録) |
| 16 | `volumes/16_xva_credit` | A4 XVA/信用(EE/PFE/CVA/コピュラ) | **done**(15セル・実行済・book登録) |
| 17 | `volumes/17_capstone` | Heston×Fourier → Greeks → CVA 一気通貫 | **done**(12セル・実行済・book登録) |
