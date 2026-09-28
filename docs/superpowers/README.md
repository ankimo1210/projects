# 計画・仕様の索引

`docs/superpowers/` にある計画（plans）・仕様（specs）・レビュー（reviews）の一覧です。
プロジェクトごとに、最近更新のあったものから並べています。正本は各ファイルで、ここは探すための索引です。
ファイルを追加したら、この表にも1行足してください（specs は設計、plans は実装手順、reviews は第三者レビュー）。
どれも記録時点の内容で、現在の実装を保証しません。現状は各プロジェクトの README や STATUS を参照してください。

## workspace

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-28 | 仕様 | [次の統合候補の個別調査](specs/2026-09-28-next-consolidation-candidates.md) |
| 2026-09-27 | 計画 | [ワークスペース整理計画](plans/2026-09-27-workspace-cleanup.md) |

## market-research

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-28 | 計画 | [Market Research Stage 3d Portfolio Export Implementation Plan](plans/2026-09-28-market-research-stage3d-export.md) |
| 2026-09-27 | 仕様 | [工程3b: マクロ・財務データの時点別取得](specs/2026-09-27-market-macro-fundamentals-design.md) |
| 2026-09-27 | 仕様 | [market-research 統合仕様](specs/2026-09-27-market-research-design.md) |
| 2026-09-27 | 計画 | [Market Data Ingestion and Storage Implementation Plan](plans/2026-09-27-market-data-ingestion.md) |
| 2026-09-27 | 計画 | [工程3b: マクロ・財務取得の実装計画](plans/2026-09-27-market-macro-fundamentals.md) |
| 2026-09-27 | 計画 | [Market Research Analysis Inputs Implementation Plan](plans/2026-09-27-market-research-analysis-inputs.md) |
| 2026-09-27 | 計画 | [market-research Core Implementation Plan](plans/2026-09-27-market-research-core.md) |
| 2026-09-27 | 計画 | [Market Research Fundamentals and Baskets Implementation Plan](plans/2026-09-27-market-research-fundamentals-baskets.md) |
| 2026-09-27 | 計画 | [Market Research Saved Macro View Plan](plans/2026-09-27-market-research-macro-view.md) |
| 2026-09-27 | 計画 | [Market Research Overview and Quality Plan](plans/2026-09-27-market-research-overview-quality.md) |
| 2026-09-27 | 計画 | [Market Research Signals and Walk-Forward Plan](plans/2026-09-27-market-research-signals-walkforward.md) |
| 2026-09-27 | 計画 | [Market Research Virtual Portfolio Risk Plan](plans/2026-09-27-market-research-virtual-risk.md) |

## rates_volatility_model

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-27 | レビュー | [レビュー: `rates-vol-completion` ブランチ（rates_volatility_model 完成計画の実装）](reviews/2026-09-27-rates-vol-completion-review.md) |
| 2026-09-27 | 計画 | [rates_volatility_model Completion Implementation Plan](plans/2026-09-27-rates-volatility-model-completion.md) |

## portfolio-analyzer

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-15 | 仕様 | [portfolio-analyzer: 全口座合計の NAV／累計損益と日次リスクモニター — 設計](specs/2026-09-15-portfolio-analyzer-daily-risk-and-total-nav-design.md) |
| 2026-09-15 | 計画 | [Daily risk monitor + total NAV — Implementation Plan](plans/2026-09-15-portfolio-analyzer-daily-risk-and-total-nav.md) |

## johnhull

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-14 | 仕様 | [johnhull vol 28 — 信用商品評価デスク（Hull Ch.24–25 完全実装）設計](specs/2026-09-14-johnhull-vol28-credit-desk-design.md) |
| 2026-09-14 | 計画 | [johnhull vol 28 Credit Desk Implementation Plan](plans/2026-09-14-johnhull-vol28-credit-desk.md) |
| 2026-07-22 | 計画 | [JohnHull paper corpus v2 implementation plan](plans/2026-07-22-johnhull-paper-corpus-v2.md) |
| 2026-07-20 | 仕様 | [johnhull vol 27 — 日次リスク管理デスク（VaR/ES 発展編）設計](specs/2026-07-20-johnhull-vol27-risk-desk-design.md) |
| 2026-07-20 | 計画 | [JohnHull Vol 27 Risk Desk (Advanced VaR/ES) — Implementation Plan](plans/2026-07-20-johnhull-27-risk-desk.md) |
| 2026-07-20 | 計画 | [JohnHull Vol.26/27 フォローアップ項目](plans/2026-07-20-johnhull-vol27-follow-ups.md) |
| 2026-07-20 | 計画 | [JohnHull Vol.27 レビュー指摘修正計画](plans/2026-07-20-johnhull-vol27-review-fixes.md) |
| 2026-07-19 | 仕様 | [johnhull モデルライブラリ化 — MODEL_INDEX / CLAUDE.md / docstring 整備 設計](specs/2026-07-19-johnhull-model-library-index-design.md) |
| 2026-07-19 | 計画 | [JohnHull Inflation-Linked Rates & JGBi — Implementation Plan](plans/2026-07-19-johnhull-inflation-jgbi.md) |
| 2026-07-19 | 計画 | [johnhull Model-Library Index Implementation Plan](plans/2026-07-19-johnhull-model-library-index.md) |
| 2026-07-18 | 仕様 | [johnhull「Hull の先」A5–A8 実装設計](specs/2026-07-18-johnhull-beyond-hull-a5-design.md) |
| 2026-07-18 | 仕様 | [johnhull「Hull の先」拡張 — 提案ノート（レビュー・設計反映版）](specs/2026-07-18-johnhull-beyond-hull-options.md) |
| 2026-07-18 | 計画 | [johnhull「Hull の先」A5–A8 Implementation Plan](plans/2026-07-18-johnhull-beyond-hull-a5.md) |
| 2026-07-18 | 計画 | [johnhull G4–G7 Detailed Implementation Record](plans/2026-07-18-johnhull-beyond-hull-g4-g7.md) |
| 2026-06-08 | 仕様 | [johnhull 02_options_basics Design — Hull 11e Ch.10–12, 17, 18](specs/2026-06-08-johnhull-02-options-basics-design.md) |
| 2026-06-08 | 仕様 | [johnhull 03_greeks Design — Hull 11e Ch.19](specs/2026-06-08-johnhull-03-greeks-design.md) |
| 2026-06-08 | 仕様 | [johnhull 04_futures_forwards_rates Design — Hull 11e Ch.2–6](specs/2026-06-08-johnhull-04-futures-forwards-rates-design.md) |
| 2026-06-08 | 仕様 | [johnhull 05_vol_smile_estimation Design — Hull 11e Ch.20, 23](specs/2026-06-08-johnhull-05-vol-smile-estimation-design.md) |
| 2026-06-08 | 仕様 | [johnhull 06_numerical_methods Design — Hull 11e Ch.21, 27](specs/2026-06-08-johnhull-06-numerical-methods-design.md) |
| 2026-06-08 | 仕様 | [johnhull 07_swaps Design — Hull 11e Ch.7, 34](specs/2026-06-08-johnhull-07-swaps-design.md) |
| 2026-06-08 | 仕様 | [johnhull 08_risk_var Design — Hull 11e Ch.22](specs/2026-06-08-johnhull-08-risk-var-design.md) |
| 2026-06-08 | 仕様 | [johnhull 09_credit_xva Design — Hull 11e Ch.9, 24, 25](specs/2026-06-08-johnhull-09-credit-xva-design.md) |
| 2026-06-08 | 仕様 | [johnhull 10_exotics_martingales Design — Hull 11e Ch.26, 28](specs/2026-06-08-johnhull-10-exotics-martingales-design.md) |
| 2026-06-08 | 仕様 | [johnhull 11_ir_derivatives_market Design — Hull 11e Ch.29, 30](specs/2026-06-08-johnhull-11-ir-derivatives-market-design.md) |
| 2026-06-08 | 仕様 | [johnhull 12_qualitative_summary Design — Hull 11e Ch.1, 8, 16, 35, 36, 37](specs/2026-06-08-johnhull-12-qualitative-summary-design.md) |
| 2026-06-08 | 計画 | [johnhull 02_options_basics Implementation Plan](plans/2026-06-08-johnhull-02-options-basics.md) |
| 2026-06-08 | 計画 | [johnhull 03_greeks Implementation Plan](plans/2026-06-08-johnhull-03-greeks.md) |
| 2026-06-08 | 計画 | [johnhull 04_futures_forwards_rates Implementation Plan](plans/2026-06-08-johnhull-04-futures-forwards-rates.md) |
| 2026-06-08 | 計画 | [johnhull 05_vol_smile_estimation Implementation Plan](plans/2026-06-08-johnhull-05-vol-smile-estimation.md) |
| 2026-06-08 | 計画 | [johnhull 06_numerical_methods Implementation Plan](plans/2026-06-08-johnhull-06-numerical-methods.md) |
| 2026-06-08 | 計画 | [johnhull 07_swaps Implementation Plan](plans/2026-06-08-johnhull-07-swaps.md) |
| 2026-06-08 | 計画 | [johnhull 08_risk_var Implementation Plan](plans/2026-06-08-johnhull-08-risk-var.md) |
| 2026-06-08 | 計画 | [johnhull 09_credit_xva Implementation Plan](plans/2026-06-08-johnhull-09-credit-xva.md) |
| 2026-06-08 | 計画 | [johnhull 10_exotics_martingales Implementation Plan](plans/2026-06-08-johnhull-10-exotics-martingales.md) |
| 2026-06-08 | 計画 | [johnhull 11_ir_derivatives_market Implementation Plan](plans/2026-06-08-johnhull-11-ir-derivatives-market.md) |
| 2026-06-08 | 計画 | [johnhull 12_qualitative_summary Implementation Plan](plans/2026-06-08-johnhull-12-qualitative-summary.md) |
| 2026-06-07 | 仕様 | [johnhull Full Coverage Design — Hull 11e All-Chapter Notebooks](specs/2026-06-07-johnhull-full-coverage-design.md) |
| 2026-06-07 | 計画 | [johnhull 01_foundations Implementation Plan](plans/2026-06-07-johnhull-01-foundations.md) |

## JGB fair-mid

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-09 | 仕様 | [JGB全銘柄リアルタイム・フェアミッド推定モデル計画のレビュー（2022–2026年の研究・市場変化に照らして）](specs/2026-09-09-jgb-fair-mid-model-research-and-market-review.md) |
| 2026-09-09 | 仕様 | [日本国債フェアミッド推定モデル：v0.2総合レビューと発展ロードマップ](specs/2026-09-09-jgb-fair-mid-model-v0.2-review.md) |

## quantkit

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-07 | 計画 | [quantkit Model Rigor (Phase 1) Implementation Plan](plans/2026-09-07-quantkit-model-rigor-phase1.md) |
| 2026-09-06 | 仕様 | [quantkit モデル層強化 設計書 — 反証力 → 幅](specs/2026-09-06-quantkit-model-enhancement-design.md) |

## health

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-07 | 計画 | [Health Full Archive and Next.js Implementation Plan](plans/2026-09-07-health-full-archive-and-nextjs.md) |
| 2026-09-07 | 計画 | [Health: Probe Discovery + Headless CLI — Implementation Plan](plans/2026-09-07-health-probe-discovery-and-cli.md) |
| 2026-09-06 | 仕様 | [Health: Full Google Archive + Next.js Frontend — Design](specs/2026-09-06-health-full-archive-and-nextjs-design.md) |
| 2026-07-25 | 計画 | [Health: Review Fixes (Safety, Sync, UX, Insights) — Implementation Plan](plans/2026-07-25-health-review-fixes.md) |
| 2026-07-22 | 計画 | [Health: Google Health Migration Completion + UI Overhaul — Implementation Plan](plans/2026-07-22-health-google-migration-completion-and-ui.md) |
| 2026-07-20 | 仕様 | [Health: Fitbit Personal Dashboard — Design](specs/2026-07-20-health-fitbit-dashboard-design.md) |
| 2026-07-20 | 仕様 | [Health: Google Health API Migration — Revised Design](specs/2026-07-20-health-google-health-api-migration-design.md) |
| 2026-07-20 | 計画 | [Health: Fitbit Personal Dashboard Implementation Plan](plans/2026-07-20-health-fitbit-dashboard.md) |
| 2026-07-20 | 計画 | [Google Health API Migration — Corrected End-to-End Implementation Plan](plans/2026-07-20-health-google-migration-plan-a.md) |

## rates-ui-lab

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-09-06 | 計画 | [Rates UI Lab — Tremor Implementation Plan](plans/2026-09-06-rates-ui-lab-tremor.md) |

## macrokit

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-08-18 | 仕様 | [日本のGDP公表イベントと金利反応データセット 設計書](specs/2026-08-18-macrokit-gdp-release-study-design.md) |
| 2026-08-18 | 計画 | [JP GDP Release / Rate-Response Dataset Implementation Plan](plans/2026-08-18-macrokit-gdp-release-study.md) |
| 2026-08-17 | 仕様 | [macrokit — 日米マクロ経済指標のリサーチ基盤 設計書](specs/2026-08-17-macrokit-design.md) |
| 2026-08-17 | 計画 | [macrokit Foundation (Phase 1) Implementation Plan](plans/2026-08-17-macrokit-foundation.md) |

## analytics/statistics

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-08-01 | 仕様 | [analytics/statistics — 確率統計 Jupyter Book 教科書 設計書](specs/2026-08-01-analytics-statistics-design.md) |
| 2026-08-01 | 計画 | [analytics/statistics Plan 1 — 足場・確率論のコア・第Ⅰ部 6 章 Implementation Plan](plans/2026-08-01-analytics-statistics-plan1-probability.md) |
| 2026-08-01 | 計画 | [analytics/statistics Plan 2 — 推測のコア・第Ⅱ部 5 章・回帰と GLM Implementation Plan](plans/2026-08-01-analytics-statistics-plan2-inference.md) |
| 2026-08-01 | 計画 | [analytics/statistics Plan 3 — 橋渡し・キャップストーン・演習解答・ポータル統合 Implementation Plan](plans/2026-08-01-analytics-statistics-plan3-bridge.md) |

## cpp_algo_lab

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-07-18 | 計画 | [cpp_algo_lab Phase 3 (CPU Parallel Ladder) Implementation Plan](plans/2026-07-18-cpp-algo-lab-phase3.md) |
| 2026-07-18 | 計画 | [cpp_algo_lab Phase 4–5 (GPU Ladder and Final Documentation) Implementation Plan](plans/2026-07-18-cpp-algo-lab-phase4.md) |
| 2026-07-15 | 計画 | [cpp_algo_lab Phase 2 (String Search) Implementation Plan](plans/2026-07-15-cpp-algo-lab-phase2.md) |
| 2026-07-14 | 仕様 | [cpp_algo_lab 設計書](specs/2026-07-14-cpp-algo-lab-design.md) |
| 2026-07-14 | 計画 | [cpp_algo_lab Phase 1 (Foundation + Sorting) Implementation Plan](plans/2026-07-14-cpp-algo-lab-phase1.md) |

## autostock（退避済み）

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-06-09 | 仕様 | [autostock — Design Spec](specs/2026-06-09-autostock-design.md) |
| 2026-06-09 | 計画 | [autostock Implementation Plan](plans/2026-06-09-autostock.md) |

## csharp_calc

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-06-03 | 仕様 | [C# WinForms Calculator — Sample App Design](specs/2026-06-03-csharp-winforms-calculator-design.md) |
| 2026-06-03 | 計画 | [C# WinForms Calculator Implementation Plan](plans/2026-06-03-csharp-winforms-calculator.md) |

## akinator

| 日付 | 種別 | 文書 |
|---|---|---|
| 2026-06-01 | 仕様 | [Akinator MVP — Design](specs/2026-06-01-akinator-mvp-design.md) |
| 2026-06-01 | 計画 | [Akinator MVP Implementation Plan](plans/2026-06-01-akinator-mvp.md) |
