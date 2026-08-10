# Quant Research Data Science — 数理・実装・検証をつなぐ教科書

> シリーズ索引: [analytics 教材一覧](../README.md)

クオンツリサーチとデータサイエンスを、数式を読むだけでもライブラリを呼ぶだけでもなく、
**仮定を定める → 安定に実装する → 診断する → 主張の限界を説明する**という一連の研究作業として
学ぶための日本語 HTML 教科書プロジェクトです。

現在は Stage 1（B1〜B4、全16週）を縦切り MVP として実装しています。60週版の原案を
そのまま詰め込まず、各週を `core`（必修）と
`advanced`（発展）に分けています。正規化した学習仕様の source of truth は
[`curriculum_map.yml`](curriculum_map.yml) です。

## 到達点

Stage 1 の修了時に、学習者が次の判断を自力で行えることを目標にします。

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
3. **データなしでも再現可能**
   既定の演習は seed 固定の合成データで完結します。外部データは任意アダプターとして追加します。
4. **金融上の対象を曖昧にしない**
   ゼロ金利を回帰する教育モードと、債券キャッシュフローを割り引いて価格を合わせる
   債券モードを分離します。coupon を入力しながら yield を直接回帰する混成仕様にはしません。
5. **研究上の主張を限定する**
   BOJ 発表前後の価格反応を測る金融イベントスタディと、DiD 等の因果イベントスタディを
   区別し、識別仮定なしに「政策の因果効果」とは呼びません。

## Stage 1 の構成

| Block | Weeks | 主題 | ブロック成果物 |
|---|---:|---|---|
| B1 | 1〜4 | 数値線形代数・PCA・曲線推定 | JGB Curve Fitter v0 |
| B2 | 5〜8 | 確率・martingale・SDE・Monte Carlo | 再利用可能な Monte Carlo ライブラリ |
| B3 | 9〜12 | 推定・頑健推論・因果推論の基礎 | BOJ Announcement Study with Honest Inference |
| B4 | 13〜16 | 凸最適化・アルゴリズム・研究ソフトウェア | 制約付き Curve Fitter（発展: portfolio optimizer） |

B2 の Girsanov・importance sampling・Brownian bridge、B4 の ADMM 等は Advanced に置き、
Core の理解と検証を犠牲にしない順序にしています。B4 では制約付き最適化への自然な入口として、
ADMM より先に projected gradient を扱います。

## 評価と Placement-out

各 block は、導出ノート、ライブラリ任せにしない実装とテスト、baseline・頑健性を含む実験、
2〜4ページの技術メモの4成果物で評価します。配点は数学25、実装・テスト30、実験設計30、
説明・メモ15で、合格点は75/100です。読了だけでは修了とせず、必須Exit Criteriaも満たします。

事前診断が強い場合、B1は4週から2週へ、B2は確率の基礎、B4は凸最適化の基礎を圧縮できます。
B3は全4週を必修とします。Placement-outは学習速度だけを変え、成果物、採点、再現性・検証要件を
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

## ディレクトリ

```text
analytics/quant_research/
├── curriculum_map.yml       # Stage 1 の正規化された学習仕様
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
- OLS・PCA・曲線推定・確率simulationの自作実装が解析解または NumPy / SciPy と許容誤差内で一致すること。
- 残差、直交性、条件数、rank、solver disagreement を数値で検査すること。
- 時系列を使う章では、時点 \(t\) より後の情報を fit に使わないこと。
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

## 現在の範囲

- 実装済み: Phase 0（設計・骨格）と Stage 1 / B1–B4 MVP
- 後続: Stage 2（B5〜B11）、Research Apprenticeship
