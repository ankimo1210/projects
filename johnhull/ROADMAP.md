# johnhull Coverage Roadmap — Hull 11e + Beyond Hull

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
当時のポータル **38 図/7 テーマ**(`make hull-report`)、Jupyter Book 20 ページ(`make hull-book`)。全テスト緑。
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

## Hull の先 A5–A8 — G8 release 完了 (2026-07-18)

Design: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`

G0 decision: financial teachers and hard validation belong to torch-free `hullkit`;
the Phase 2 PyTorch engine and checkpoints belong to `deep_hedge_price`; teaching,
book, and portal integration belong to `johnhull`. Projects exchange only versioned
JSON+NPZ reference artifacts. Phase 1 and Phase 2 config/checkpoint namespaces are
separate. No production dependency was added for G0/G1 core implementation.

| Gate | # | Volume / contract | Status |
|---|---:|---|---|
| G0 | — | owner / dependency / artifact contract | done |
| G1 | 18 | `volumes/18_ml_surrogates` | done |
| G2 | 19 | `volumes/19_inverse_surfaces` | done |
| G3 | 20 | `volumes/20_surface_dynamics` | done |
| G4 | 21 | `volumes/21_spx_vix` | done |
| G4 | 22 | `volumes/22_zero_dte` | done |
| G5 | 23 | `volumes/23_rfr_post_libor` | done |
| G6 | 24 | `volumes/24_crypto_market_structure` | done |
| G7 | 25 | `volumes/25_climate_energy` | done |
| G8 | — | full integration and tracked release | **done** |

表の `done` は巻別実装、integration gate、G8 tracked release の完了を表す。
各巻に validation report、fingerprinted JSON/NPZ、artifact-only notebook、book
symlinkがあり、各巻の `integration_and_reproducibility` gate は PASS。これは
**model performance の承認ではない**。`release_manifest.json` の現行契約は portal
**70 図/11 テーマ**、Jupyter Book 28 ページ。G8 で fresh artifact/notebook/
report/book/test/lint を再検証し、最終結果と model risk を `johnhull/VALIDATION.md`
に固定した。strict tracked gate と専用 branch への remote push も完了した。
research track は既定無効・core gate 非依存のままとする。

## Inflation-linked rates and JGBi — Phase 1–7 (2026-07-19)

Design plan: `docs/superpowers/plans/2026-07-19-johnhull-inflation-jgbi.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 26 | `volumes/26_inflation_jgbi` | inflation-linked rates and JGBi (beyond Hull ch.25) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | Shared nominal/real curve helpers | done |
| 2 | Hull–White 1F curve fit, exact transition, bond option, Jamshidian swaption | done |
| 3 | CPI lag/interpolation/rebasing, deterministic seasonality, ZCIS, YoY | done |
| 4 | JGBi tenth-day reference index, rounding, cash flow, settlement, real yield | done |
| 5 | Jarrow–Yildirim nominal/real numeraires and payment-forward measures | done |
| 6 | JGBi redemption-only deflation floor, analytic/MC value and risk | done |
| 7 | `volumes/26_inflation_jgbi` reproducible artifact-only notebook | done |

Phase 7 の `done` は synthetic-offline の integration/reproducibility gate を表し、
市場較正、production valuation、model performance の承認ではない。Portal、Jupyter
Book、full tracked release への登録は Phase 8 以降へ明示的に繰り延べる。

## Advanced VaR/ES risk desk — Phase 1–6 (2026-07-20)

Design plan: `docs/superpowers/plans/2026-07-20-johnhull-vol27-risk-desk.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 27 | `volumes/27_risk_desk` | advanced daily VaR/ES risk desk (beyond Hull ch.22) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | VaR backtesting: Kupiec POF, Christoffersen ind/CC, quantified Basel traffic light | done |
| 2 | Filtered historical simulation and EVT/GPD peaks-over-threshold tail VaR/ES | done |
| 3 | Euler risk decomposition: marginal/component/incremental VaR and simulation ES | done |
| 4 | P&L explain: factor exposures, delta-gamma-vega attribution, limits, desk report | done |
| 5 | `volumes/27_risk_desk` reference, `_volume27` acceptance, artifact-only notebook | done |
| 6 | Portal `risk_management` page, Jupyter Book page, full tracked release | done |

Phase 5 の `done` は synthetic-offline の integration/reproducibility gate（`_volume27`
の 11 恒等式チェックと byte 再現性）を表し、市場較正・model performance の承認ではない。
Phase 6 の portal 図（`var_traffic_light`・`fhs_vs_hs_coverage`・`gpd_tail_fit`・
`risk_allocation_bars`）、`risk_management` book page、Jupyter Book 登録、full tracked
release は明示的に繰り延べる。

FRTB IMA（liquidity-horizon ES 集約、stressed ES scaling、NMRF、P&L attribution
eligibility test、IMA/SA 資本比較）は **vol 28 候補**として scope 外に記録する。
