# Quant Research Data Science — 数理・実装・検証をつなぐ教科書

> シリーズ索引: [analytics 教材一覧](../README.md)

クオンツリサーチとデータサイエンスを、数式を読むだけでもライブラリを呼ぶだけでもなく、
**仮定を定める → 安定に実装する → 診断する → 主張の限界を説明する**という一連の研究作業として
学ぶための日本語 HTML 教科書プロジェクトです。

現在は Stage 1（B1〜B4）と Stage 2（B5〜B10）、全40週・60 Notebookを実装しています。
座学教科書としての完成範囲はB1〜B11の44週で、現在は40/44週（91%）です。原典のStage 3と
Capstoneは成果物・データ要件が異なるためplaceholderとし、設計・実装・完成率の分母に含めません。
60週版の原案をそのまま詰め込まず、各週を `core`（必修）と
`advanced`（発展）に分けています。正規化した学習仕様の source of truth は
[`curriculum_map.yml`](curriculum_map.yml) です。

## 到達点

現在のStage 1–2D修了時に、学習者が次の判断を自力で行えることを目標にします。

- 問題の構造と数値条件から、分解法・推定法・最適化法を選ぶ。
- 統計誤差、数値誤差、Monte Carlo 誤差、離散化誤差、モデル誤差を区別する。
- 予測・関連・市場反応・因果効果を混同せず、推定対象（estimand）を先に定める。
- solver status や p 値だけでなく、残差、被覆率、頑健性、経済的有意性を診断する。
- seed、入力、設定、環境、評価手順を残し、研究結果を再現可能にする。

## 教材設計の原則

1. **Core / Advanced の二層構成**
   Core は週7〜8時間で到達すべき内容、Advanced は前提が整った読者向けの発展課題です。
2. **直感 → 導出 → 最小実装 → ライブラリ比較 → 失敗例**
   各章は正解例だけでなく、壊れる条件と診断方法まで扱います。
3. **方法検証と実証分析でデータの役割を分ける**
   解析解との照合、edge case、Monte Carlo、単体テストには seed 固定の合成fixtureを使います。
   Stage 2以降の実証Block Projectは取得・利用条件を確認した実データを既定とし、取得できない
   市場データを都合のよい合成系列で代替しません。
4. **金融上の対象を曖昧にしない**
   ゼロ金利を回帰する教育モードと、債券キャッシュフローを割り引いて価格を合わせる
   債券モードを分離します。coupon を入力しながら yield を直接回帰する混成仕様にはしません。
5. **研究上の主張を限定する**
   BOJ 発表前後の価格反応を測る金融イベントスタディと、DiD 等の因果イベントスタディを
   区別し、識別仮定なしに「政策の因果効果」とは呼びません。

## Stage 1–2D の構成

| Block | Weeks | 主題 | ブロック成果物 |
|---|---:|---|---|
| B1 | 1〜4 | 数値線形代数・PCA・曲線推定 | JGB Curve Fitter v0 |
| B2 | 5〜8 | 確率・martingale・SDE・Monte Carlo | 再利用可能な Monte Carlo ライブラリ |
| B3 | 9〜12 | 推定・頑健推論・因果推論の基礎 | BOJ Announcement Study with Honest Inference |
| B4 | 13〜16 | 凸最適化・アルゴリズム・研究ソフトウェア | 制約付き Curve Fitter（発展: portfolio optimizer） |
| B5 | 17〜20 | baseline・正則化・分類・時系列validation | Daily Treasury Curve Forecasting Baseline |
| B6 | 21〜24 | tree・kernel/GP・clustering・shift下評価 | Treasury Forecast Model Tournament |
| B7 | 25〜28 | stationarity・VAR・state space・volatility | Dynamic Treasury Curve Forecasting Audit |
| B8 | 29〜32 | Bayesian推論・階層model・HMM・MCMC診断 | Treasury Predictive Uncertainty and Latent-State Audit |
| B9 | 33〜36 | deep learning・sequence model・attention・financial NLP | SEC Filing Text & Fundamentals Forecast |
| B10 | 37〜40 | scientific computing・PIT data system・experiment infrastructure | Reproducible B9 Research Package |

B2 の Girsanov・importance sampling・Brownian bridge、B4 の ADMM 等は Advanced に置き、
Core の理解と検証を犠牲にしない順序にしています。B4 では制約付き最適化への自然な入口として、
ADMM より先に projected gradient を扱います。

Stage 1のJGB-like curveとBOJ announcementの既定データは、数値・推論・最適化の契約を
検証する合成fixtureです。実JGB市場やBOJ政策についての実証結果ではありません。

B5–B8は公式U.S. Treasury daily par yield curveの固定snapshotを使います。transaction price、
executable quote、zero rate、intraday dataではないため、予測誤差と分布シフトは分析しても、
取引収益・流動性・政策因果効果は主張しません。

B9はM6で取得・監査したSEC Company Facts、Submissions、previous primary filing documentを使います。
教材Notebookにはdevelopment-onlyの実データ由来fixtureだけを同梱し、raw/normalized filing、CIK、
accession、contact情報、locked outer rowは含めません。fixtureはalgorithmと漏洩契約の検証用であり、
full candidate tournamentのnominee選定には使いません。

## 評価と Placement-out

各 block は、導出ノート、ライブラリ任せにしない実装とテスト、baseline・頑健性を含む実験、
2〜4ページの技術メモの4成果物で評価します。配点は数学25、実装・テスト30、実験設計30、
説明・メモ15で、合格点は75/100です。読了だけでは修了とせず、必須Exit Criteriaも満たします。

事前診断が強い場合、B1は4週から2週へ、B2は確率の基礎、B4は凸最適化の基礎、
B5は線形modelの基礎を圧縮できます。B3は全4週、B6はshift下の共通評価を必修とします。
Placement-outは学習速度だけを変え、成果物、採点、再現性・検証要件を
免除しません。診断項目と判定規約は [`curriculum_map.yml`](curriculum_map.yml) がsource of truthです。

## 実装済み Notebook

| Notebook | 内容 |
|---|---|
| `00_overview` | 教材の読み方、診断、評価規約、B1 の研究フロー |
| `01_week1_least_squares` | ベクトル空間、射影、OLS/WLS、ランク欠損 |
| `02_week2_numerical_stability` | 条件数、誤差、QR/SVD、solver 比較 |
| `03_week3_svd_pca_yield_curve` | SVD、PCA、金利変化の level/slope/curvature |
| `04_week4_regularization_curve_fitting` | Ridge、基底展開、平滑化、Nelson–Siegel |
| `05_b1_project_jgb_curve_fitter` | JGB Curve Fitter v0 と総合診断 |
| `06_b2_overview` | 確率システム、情報、simulation誤差の見取り図 |
| `07_week5_conditional_probability` | 条件付き分布、多変量Gaussian、相関乱数 |
| `08_week6_convergence_heavy_tails` | 収束概念、極限定理、被覆率、重い裾 |
| `09_week7_markov_martingales` | Markov連鎖、filtration、martingale、停止時刻 |
| `10_week8_brownian_monte_carlo` | Brownian motion、Itô、Euler–Maruyama、分散削減 |
| `11_b2_project_monte_carlo_library` | 再利用可能なMonte Carloライブラリと総合診断 |
| `12_b3_overview` | 推定対象、識別、推論、主張の境界を結ぶB3研究フロー |
| `13_week9_likelihood_estimands` | 尤度、MLE、有限標本挙動、model misspecification |
| `14_week10_testing_resampling` | 検定、bootstrap、permutation、多重比較 |
| `15_week11_robust_inference` | HC・HAC・cluster robust covarianceと守備範囲 |
| `16_week12_causal_event_study` | potential outcomes、DAG、DiD、event studyの境界 |
| `17_b3_project_boj_announcement_study` | 合成BOJ発表データによるhonest inference総合演習 |
| `18_b4_overview` | 凸性、双対性、algorithm、数値契約を結ぶB4研究フロー |
| `19_week13_convex_modeling` | LP・QP・SOCP、DCP境界、scaling、feasibility |
| `20_week14_duality_kkt_sensitivity` | Lagrangian、KKT residual、duality gap、shadow price |
| `21_week15_optimization_algorithms` | GD、Newton、BFGS、projected・proximal gradient |
| `22_week16_research_software` | 計算量、gradient audit、test、benchmark、provenance |
| `23_b4_project_constrained_curve_fitter` | discount-factor QPによる制約付きCurve Fitter |
| `24_b5_overview` | 実データ契約、予測時点、baseline、locked testを結ぶB5研究フロー |
| `25_week17_learning_baselines` | Treasury snapshot品質監査、予測問題、単純baseline |
| `26_week18_regularized_models` | Ridge、lasso、elastic net、training-only標準化 |
| `27_week19_classification_calibration` | 方向分類、Brier score、reliability、確率calibration |
| `28_week20_validation_pipelines` | expanding validation、purging、leakage失敗例 |
| `29_b5_project_treasury_baseline_pipeline` | Daily Treasury Curve Forecasting Baseline |
| `30_b6_overview` | 非線形model、uncertainty、shift、共通tournament規約 |
| `31_week21_trees_boosting` | regression stump、gradient boosting、予測的重要度 |
| `32_week22_kernels_gaussian_processes` | kernel ridge、GP posterior、計算量とcoverage |
| `33_week23_unsupervised_regimes` | k-means、cluster stability、記述的regime |
| `34_week24_evaluation_under_shift` | nested temporal validation、drift、conformal境界 |
| `35_b6_project_treasury_model_tournament` | 共通outer testによるTreasury model tournament |
| `36_b7_overview` | publication horizon、動学予測、filtered情報集合のB7研究フロー |
| `37_week25_stationarity_arima` | stationarity、ACF/PACF、DF diagnostic、AR baseline |
| `38_week26_var_cointegration` | NS factor VAR、Granger、IRF、cointegration境界 |
| `39_week27_state_space_dns` | Kalman filter/smoother、missing data、Dynamic Nelson–Siegel |
| `40_week28_volatility_breaks` | GARCH、volatility proxy、methodology break |
| `41_b7_project_dynamic_treasury_curve` | 5公表日先Dynamic Treasury Curve Forecasting Audit |
| `42_b8_overview` | prior・predictive・latent-state uncertaintyのB8研究フロー |
| `43_week29_bayesian_foundations` | 共役Bayes、prior predictive、Bayesian regression |
| `44_week30_hierarchical_models` | partial pooling、tenor hierarchy、WAIC境界 |
| `45_week31_graphical_latent_hmm` | graphical model、Gaussian HMM、EM、label監査 |
| `46_week32_mcmc_approximate_inference` | MH、ESS、split-R-hat、近似推論の境界 |
| `47_b8_project_treasury_regime_uncertainty` | 同一targetのBayesian/HMM predictive audit |
| `48_b9_overview` | deep learning、SEC information set、同一budget比較のB9研究フロー |
| `49_week33_neural_networks_backprop` | MLP、backpropagation、gradient audit、Adam |
| `50_week34_sequence_models` | LSTM、causal TCN、effective context、linear probe |
| `51_week35_attention_transformers` | scaled self-attention、mask、position、transformer境界 |
| `52_week36_financial_nlp_multimodal` | training-only TF–IDF、sparse ridge、modality ablation |
| `53_b9_project_sec_filing_forecast` | SEC Filing Text & Fundamentals Forecast evidence gate |
| `54_b10_overview` | correctness、performance、PIT data、lineageを結ぶB10研究フロー |
| `55_week37_performance_numerical_computing` | vectorization、benchmark、reduction order、acceleration境界 |
| `56_week38_research_software_engineering` | package API、test portfolio、config・data・code hash |
| `57_week39_data_systems_pit` | bitemporal record、pandas/SQLite PIT join、schema evolution |
| `58_week40_experiment_infrastructure` | immutable run registry、drift、batch lineage、rollback |
| `59_b10_project_reproducible_research_package` | development-only B9 pipelineの再現可能package化 |

## ディレクトリ

```text
analytics/quant_research/
├── curriculum_map.yml       # Stage 1–2D の正規化された学習仕様
├── book/                    # Jupyter Book 設定と静的 HTML の入口
├── notebooks/               # 実行済み教材 Notebook
├── tools/                   # Notebook 生成・検証スクリプト
├── src/quant_textbook/      # 共通の数値・データ・評価関数
└── tests/                   # 数値契約と再現性のテスト
```

`book/notebooks` は `../notebooks` へのシンボリックリンクです。Notebook の出力は生成時に
確定し、HTML ビルド時には再実行しません。

## 環境構築

Python はリポジトリルートの uv workspace を共有します。プロジェクト配下に別の仮想環境を
作らないでください。

```bash
cd ~/projects
uv sync --all-packages
```

JupyterLab を起動するには:

```bash
cd ~/projects
uv run jupyter lab analytics/quant_research/notebooks/
```

## Notebook の再生成

教材 Notebook は決定論的な生成スクリプトから作ります。生成後は上から順に実行でき、乱数を使う
実験は seed または `numpy.random.Generator` を明示します。

```bash
cd ~/projects
uv run --no-sync python analytics/quant_research/tools/build_notebooks.py --check
uv run --no-sync python analytics/quant_research/tools/build_notebooks.py
uv run --no-sync jupyter nbconvert --to notebook --execute --inplace \
  analytics/quant_research/notebooks/*.ipynb \
  --ExecutePreprocessor.timeout=300
```

WSL で `Permissions assignment failed for secure file` が出る場合は、Windows 側の一時
ディレクトリではなく Linux 側を Jupyter の runtime に指定します。

```bash
mkdir -p /tmp/quant-textbook-jupyter-runtime
chmod 700 /tmp/quant-textbook-jupyter-runtime
TMPDIR=/tmp JUPYTER_RUNTIME_DIR=/tmp/quant-textbook-jupyter-runtime \
  uv run --no-sync jupyter nbconvert --to notebook --execute --inplace \
  analytics/quant_research/notebooks/*.ipynb \
  --ExecutePreprocessor.timeout=300
```

## HTML のビルド

```bash
cd ~/projects
uv run --no-sync jupyter-book build analytics/quant_research/book/
# 出力: analytics/quant_research/book/_build/html/index.html
```

Notebook の表・数式・文章は静的 HTML に含まれます。Plotly の対話図は現在
`cdn.plot.ly` から JavaScript を読むため、閲覧時にネットワーク接続が必要です。

## 検証方針

- Notebook の生成結果が同一入力から再現できること。
- OLS・PCA・曲線推定・確率simulation・AR/VAR・Kalman・共役Bayes・HMMの自作実装が、
  解析解または既知真値fixtureと許容誤差内で一致すること。
- 残差、直交性、条件数、rank、solver disagreement を数値で検査すること。
- 時系列を使う章では、時点 \(t\) より後の情報を fit に使わないこと。
- 実データ章ではsource、retrieval、hash、grain、unit、availability、methodology breakを保存すること。
- final testをmodel選択から隔離し、単純baselineを超えない場合はno model selectedを許容すること。
- Monte Carlo誤差と時間離散化誤差を分離し、独立streamとseed再現性を検査すること。
- HTML のリンク、数式、Plotly 図、狭い画面での表を確認すること。

## B1 Curve Fitter のデータ契約

教材では次の二つを明示的に分離します。

### 1. 教育用ゼロカーブモード

- 入力: 満期、観測ゼロ金利
- 推定対象: 金利曲線
- 用途: 基底、条件数、正則化、補間の比較

### 2. 債券価格モード

- 入力: 評価時点を原点とするcash-flow時刻、クーポン・元本、dirty price、任意のbid–ask情報
- 推定対象: 割引関数を通じたモデル価格
- 基本式: \(P_i=\sum_j C_{ij}D(t_{ij})\)
- 評価: pricing RMSE、bid–ask weighted RMSE、leave-one-bond-out error、安定性

実際の JGB データを使うadapterでは、決済日、日付規約、経過利息、初回・最終クーポン、欠損、timestamp、
ライセンスを別途検証します。この MVP は実務価格ライブラリではありません。

## B2 Monte Carlo の実行契約

- 乱数を消費する関数は、呼び出し側が作った numpy.random.Generator を必ず受け取る。
- 並列streamは SeedSequence から生成し、root seed・論理task ID・child割当を保存する。
- pathは (n_paths, n_times) とし、path生成、payoff、discount、区間推定を別の責務にする。
- confidence intervalはsampling uncertaintyだけを表し、時間離散化biasやmodel riskを含めない。
- antitheticはpairを1観測単位として扱い、control variateは既知のcontrol期待値を明記する。
- Advancedのimportance samplingはraw-weight ESSだけでなく、nonzero contributionと寄与集中も診断する。

## B3 推論とイベントスタディの主張契約

- データを見る前にestimand、sampling unit、primary analysisを記述する。
- optimizerの収束、モデル仮定、有限標本coverageを別々に診断する。
- covariance estimatorはheteroskedasticity、時系列依存、cluster構造に合わせて選ぶ。
- robust standard errorはomitted-variable biasや不適切なcounterfactualを修正しない。
- BOJ演習の既定データはtimezone付きの合成データで、主張はannouncement responseに限定する。
- event windowの変更、placebo、negative control、多重比較補正はprimary analysisと分けて報告する。
- 実データadapterではBOJ公式文書の公開timestamp、精度、重複ニュース、利用条件を別途検証する。

## B4 最適化と制約付き曲線の数値契約

- 問題のconvexityとsolver statusを分離し、目的関数・domain・制約から凸性を先に示す。
- QPは $Gx\le h$ の符号規約を固定し、primal feasibility、dual feasibility、stationarity、
  complementarityをsolverとは独立に再計算する。
- SciPyにDCP checkerや汎用SOCP certificateがあるとはみなさず、対応範囲外を`unknown`として残す。
- B4 Projectはcash-flow node上のdiscount factorを変数にする価格空間QPとし、
  Nelson–Siegel decayの同時推定という非凸問題と混同しない。
- discount factorの単調減少は非負forward rateを仮定する任意制約であり、負金利regimeでは強制しない。
- optimizerの停止はgradient mappingと制約残差で判定し、reference optimumがある実験では
  objective gapを事後評価として併記する。
- correctness test、performance benchmark、environment metadataを分離して保存する。

## B5–B8 Treasury実データの研究契約

- 固定snapshotは2015-01-02–2025-12-31の2,750公表日、3m・2y・5y・10y・30yを使う。
- 値はpercent単位のconstant-maturity par yieldであり、zero rateやtransaction rateではない。
- 予測時点はday-\(t\)公式curve公表後、targetは次のTreasury公表日の10年yield変化（bp）とする。
- 2021-12-06の公式methodology changeを既知breakとして保持する。
- scaler、feature transform、hyperparameterはtraining/validationだけで決め、final 20% testを保護する。
- 採用にはzero-change RMSEを1%以上改善し、MAEも悪化しない教材用gateを使う。これは経済的
  materialityではなく、価格・position・costのないデータからPnLを主張しない。
- XML parserは実テナー列だけを列挙し、`BC_30YEARDISPLAY=0.00`だけの休場日phantom rowを除外する。
- 詳細な品質監査と結果は
  [Stage 2A / B5–B6実装ノート](docs/updates/2026-08-10-stage-2a-b5-b6.md)に残す。

### B7/B8の追加契約

- B7/B8は同じsnapshotとouter-test開始日（2023-10-23）を使い、新しい都合のよい合成market seriesを作らない。
- B7 primaryは5 Treasury公表日先の5-tenor curve。1/20公表日はsecondaryで、calendar dayへ読み替えない。
- forecast originではKalman/HMMのfiltered state probabilityだけを使い、smoothed resultはretrospective diagnosticに限定する。
- B8のBayesian regressionはposterior predictive、HMM EMはpoint-estimated parameter下のconditional predictiveとして区別する。
- locked testではB7/B8の候補modelがrandom walkのpoint RMSEを上回らず、no model selectedを結論とする。
- 結果と数値は[Stage 2B / B7–B8実装ノート](docs/updates/2026-08-10-stage-2b-b7-b8.md)に残す。

## B9 のデータ契約と教材実装

- 2007–2025 Treasury拡張版は別manifestの
  Advanced historical robustnessに限定する。
- M6 の historical SEC cohort は実データ gate を通過した。2016年Q1の exact `10-K` を seed とする
  300 CIKのうち、cache integrity を通った261 CIKから、fixed-anchor cohort 164 CIK、valid panel
  4,631行 / 163 CIKを得た。strict company × time holdout は413行 / 38 CIK / 183 availability dates、
  対応するtraining partitionは2,195行 / 102 CIK / 534 availability datesであり、
  $n\ge200$ とtraining非空のgateを通過した。
- B9 v1 Coreは現在のFrames APIを過去へ遡及適用しない。`us-gaap/Assets/USD` の
  `2015-12-31` anchor factを `2016-04-01` 以下のavailabilityで選び、anchor後の観測だけを使う
  固定PIT cohortとする。dynamic historical universeはAdvancedへ分離する。
- Company Factsの`accn`はSubmissionsの`recent`だけでなく`filings.files`の全archiveへ結合する。
  acceptance metadataが未解決なら失敗とし、`filed`単独へfallbackしない。
- acceptanceDateTimeのtimezoneを保持し、`America/New_York`の日付と`filingDate`の遅い方の
  次の米国連邦営業日から利用可能とする。size floorは**anchor時点** Assets
  $\ge 100\,\mathrm{M}$ であり、各行の前四半期Assetsへ再適用しない。
- B9のprimary metricはMAE、secondaryはmedAE、RMSEはreferenceとし、zero / pooled drift /
  seasonal / company expanding meanをbaseline ladderへ含める。inner validationで4本中の最小MAEを
  1%以上改善し、medAEとcompany-macro MAEも各metricのbaseline最小値を悪化させないことを候補gateとする。
  primary baselineは固定tie-breakでouter前にfreezeし、outer outcomeから比較相手を選び直さない。
- `sec_pit.py`、`sec_panel.py`、batch対応の`fetch_sec_b9_cache.py`、
  `build_b9_panel.py`、`audit_sec_b9_panel.py`は、cache→PIT panel→derived artifactの完全性、
  grain、欠損、split、baselineを検証する再現部品である。raw SEC cacheはrepository外に置く。
- このgateはB9のmodel選定・企業一般への実証結論ではない。calendar-date anchorに適合する
  deterministic feasibility cohortであり、candidate set、feature availability、locked evaluationは
  [B9 pre-analysis specification](docs/plans/2026-08-11-b9-preanalysis.md)で固定した。
- B9 Coreはnumeric-only、TF-IDF、NumPy MLP / LSTM / TCN / small self-attention、text+numericを
  同じdevelopment partitionで比較する。pretrained embeddingとencoder fine-tuningはAdvancedに置く。
- candidate family、feature manifest、seed、code commitを固定してからouter testを一度だけ開く。
  採用gateを満たさない場合は`no_model_selected`を正式結果とする。
- 実測値、未解決リスク、再現部品は
  [SEC B9 baseline gate follow-up](docs/updates/2026-08-11-sec-baseline-gate.md)に固定する。
- Week 33–36とProjectの6 Notebook、NumPy MLP/backprop、LSTM/TCN/attention forward、
  training-only hashed TF–IDF、sparse ridge、実SEC由来fixtureを実装した。fixtureはinner train 192行・
  inner validation 64行のみで、locked outerは未開封である。
- full 2,195-row candidate search、company-cluster bootstrap、nominee manifest、outer一回評価は別の
  empirical milestoneとして未実行である。現時点の正式decisionは`no_model_selected`とする。

## B10 research systemの実装契約

- correctness gateをperformance benchmarkより先に置き、timingはwarm-up後のmedianとIQRで報告する。
- reduction orderと並列chunkの再現性を監査し、共有machine上の速度へ普遍的な合否thresholdを置かない。
- Notebook、pure API、I/O adapter、configuration、test、registryの責務を分離する。
- observation、release、revision、availability、decisionの5時点を保持し、pandasとSQLiteの独立実装で
  future revisionを除外する。
- experiment runはconfig、data、code、metrics、artifactのcontent hashへ結び、同じrun IDを上書きしない。
- immutable run evidenceとmutable promotion pointerを分け、development runをproductionへpromoteしない。
- driftは事前固定したreference binとthresholdで診断するが、それだけでautomatic rollbackしない。
- Coreは標準library SQLiteと既存dependencyで完結する。DuckDB、Arrow、Parquet、JIT、GPUは
  Advancedの導入判断・interface境界であり、この版でのproduction実装を主張しない。
- B9 locked outerは開かず、Project終了時のproduction pointerは`None`である。
- 実装と検証結果は
  [Stage 2D / B10実装ノート](docs/updates/2026-08-11-stage-2d-b10.md)に残す。

## 現在の範囲

- 実装済み: Phase 0、Stage 1 / B1–B4、Stage 1評価・placement追補、Stage 2 / B5–B10、
  B9 M6 real-data gate・pre-analysis contract・Week 33–36 / Project教材、B10 research system教材
- 後続: B11 Week 41–44と、別milestoneのB9 full locked model tournament。B9のfiling provenance、
  4,631 primary documents取得、visible-text正規化、raw / normalized integrity監査、教材feature pipelineは完了した
- Placeholder（対象外）: Stage 3 / Research Apprenticeship、Capstone

## 更新ノート

- [2026-08-10 — Stage 1 / B4実装完了](docs/updates/2026-08-10-stage-1-b4.md)
- [2026-08-10 — Stage 1整合性フォローアップとStage 2実データ優先計画](docs/plans/2026-08-10-stage-2-real-data-first.md)
- [2026-08-10 — Stage 2A / B5–B6実装・データ品質ノート](docs/updates/2026-08-10-stage-2a-b5-b6.md)
- [2026-08-10 — Stage 2 Data Feasibility follow-up](docs/updates/2026-08-10-stage-2-data-feasibility-follow-up.md)
- [2026-08-10 — Stage 2B / B7–B8実装・予測結果ノート](docs/updates/2026-08-10-stage-2b-b7-b8.md)
- [2026-08-11 — SEC B9 baseline gate follow-up](docs/updates/2026-08-11-sec-baseline-gate.md)
- [2026-08-11 — B9 filing provenance and retrieval gate](docs/updates/2026-08-11-b9-filing-provenance.md)
- [2026-08-11 — Stage 2C / B9教材実装](docs/updates/2026-08-11-stage-2c-b9.md)
- [2026-08-11 — Stage 2D / B10教材実装](docs/updates/2026-08-11-stage-2d-b10.md)
- [2026-08-11 — Opus alignment follow-up](docs/updates/2026-08-11-opus-alignment-follow-up.md)
