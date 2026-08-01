# analytics/statistics — 確率統計 Jupyter Book 教科書 設計書

- 日付: 2026-08-01
- 対象: `/home/kazumasa/projects/analytics/statistics`（新規）
- 位置づけ: analytics 教科書シリーズの 8 冊目

## 1. 動機

analytics シリーズは線形代数・ニューラルネット・ベイズ・フーリエ・ラプラス・微分方程式
（ODE/PDE）・機械学習の 7 書を揃えているが、**確率論と頻度論統計の教科書がない**。
統計を扱うのは `bayesian`（ベイズ側のみ）と `machine_learning` NB04（予測性能の検証）
に限られ、以下が欠けている。

- 確率論そのもの（確率変数・期待値・極限定理）
- 頻度論の推定論（最尤・十分統計量・Fisher 情報・Cramér–Rao）
- 仮説検定（Neyman–Pearson・p 値の解釈・多重比較・検出力）
- 信頼区間・ブートストラップ・順列検定
- GLM
- 頻度論とベイズの体系的な対比

本書はこの穴を 1 冊で埋める。

## 2. スコープ

### 含めるもの

確率論の基礎から頻度論の推測まで。理論の上限は **漸近論**（Fisher 情報・Cramér–Rao 下限・
MLE の漸近正規性）とし、証明はスケッチに留めてシミュレーションで「見せる」。
確率過程は 1 章だけ含める（ランダムウォーク・マルコフ連鎖・ポアソン過程）。

### 含めないもの（YAGNI）

因果推論（DID/IV/傾向スコア）、生存時間解析、実験計画法、測度論の厳密な展開、
時系列 ARIMA。将来の別書、または `machine_learning` NB08 が近い領域を扱う。

### 既存書との境界

| 既存書 | 重なり | 扱い |
|---|---|---|
| `bayesian` NB02（確率分布とシミュレーション） | 分布の基礎 | 本書 03 章を正本として厚く書く。`bayesian` NB02 はベイズ用の最小限なので共存 |
| `bayesian` 全体 | 推論の流儀 | 本書 11 章を「橋渡し章」とし、同一データを両流儀で解いて対比。深入りは `bayesian` へリンク |
| `machine_learning` NB04（評価と検証） | 検証 | ML は予測性能、本書は推測（母数の不確実性）。12 章キャップストーンで接続 |
| `linear_algebra` NB07 | マルコフ連鎖 | LA は線形代数の応用、本書 05 章は確率過程としての定常分布・エルゴード性 |
| `rough_volatility` | 確率過程 | ラボであり教科書ではない。本書は入門の 1 章のみ |

## 3. 書誌

- 書名: **統計的推測の風景 — 不確実性を測り、判断する言語**
- ディレクトリ: `analytics/statistics`
- パッケージ: `stats-book` / `import stats_textbook`
- 対象読者: Python の基礎と高校数学＋微積の初歩を知っている読者
- 全 14 Notebook（本編 12 ＋ 付録 2）

## 4. 章構成

### 第Ⅰ部 確率論

| NB | 内容 | インタラクティブの核 |
|---|---|---|
| `00_overview` | 全体地図。「同じデータから 2 人が違う結論を出すのはなぜか」で動機づけ。Ⅰ部→Ⅱ部の依存図 | 章依存グラフ |
| `01_probability_foundations` | 標本空間・事象・条件付き確率・独立・ベイズの定理（道具として）・Monty Hall・検査の偽陽性パラドクス | 有病率スライダーで PPV が崩れる図 |
| `02_random_variables_expectation` | 離散/連続・期待値・分散・変数変換・同時分布・共分散・条件付き期待値（最良予測子としての E[Y\|X]） | 同時分布ヒートマップ＋周辺化 |
| `03_distributions_zoo` | 主要分布の関係図（二項→ポアソン→正規、指数↔ガンマ↔χ²、t/F の由来）・指数型分布族と十分統計量 | パラメータスライダーで分布が別分布に遷移 |
| `04_limit_theorems` | 大数の法則・CLT・収束の 3 種（概収束/確率収束/分布収束）の区別・デルタ法・CLT が効かない例（Cauchy・重い裾） | n スライダーで標本平均分布が正規に寄る／Cauchy では寄らない対比 |
| `05_stochastic_processes` | ランダムウォーク・マルコフ連鎖（定常分布・エルゴード性）・ポアソン過程・待ち行列の直感 | 遷移行列スライダーで定常分布が動く |

### 第Ⅱ部 統計的推測

| NB | 内容 | インタラクティブの核 |
|---|---|---|
| `06_estimation_mle` | 推定量の性質（不偏・一致・有効）・モーメント法・MLE・尤度曲面・Fisher 情報・Cramér–Rao 下限・漸近正規性 | 尤度曲面上の MLE ＋ 標本サイズと分散の CRLB 到達 |
| `07_confidence_intervals_bootstrap` | 信頼区間の正しい解釈（被覆確率をシミュレーションで実測）・ピボット法・ブートストラップ（percentile/BCa）・順列検定 | 100 本の区間を描き「95 本が真値を含む」を見せる |
| `08_hypothesis_testing` | 検定の構造・第 1 種/第 2 種・Neyman–Pearson 補題・p 値の誤解 4 種・検出力と必要標本サイズ・多重比較（Bonferroni/BH-FDR）・p-hacking の実演 | α/効果量/n スライダーで検出力曲線、FDR シミュレーション |
| `09_regression_inference` | 線形回帰を推測として見る（係数の分布・t 検定・F 検定）・残差診断・不均一分散と頑健標準誤差・多重共線性 | 残差プロットの病理カタログ（切り替え式） |
| `10_glm` | 指数型分布族→GLM の統一・リンク関数・IRLS を自前実装して statsmodels と一致させる・ロジスティック/ポアソン回帰・逸脱度・過分散 | リンク関数の切り替えで当てはめが変わる |
| `11_frequentist_vs_bayes` | 橋渡し章。同一データを両流儀で解き、信頼区間 vs 信用区間・p 値 vs ベイズ因子を並べる。事前分布が効く/効かない領域 | 標本サイズスライダーで事後分布が MLE に収束 |

### 付録

| NB | 内容 |
|---|---|
| `12_capstone_three_lenses` | 1 つのデータセットを頻度論／ベイズ／機械学習の 3 視点で解き、答えが一致する所と割れる所を明示 |
| `13_exercise_solutions` | 01–11 章の演習解答 |

### 本書を貫く 3 原則

1. **確率は長期頻度で定義する** — だから信頼区間は「真値が入る確率」ではない（07）
2. **すべての主張はシミュレーションで検算する** — 被覆確率も第 1 種の誤り率も実測する（07・08）
3. **モデルは仮定の束であり、診断せずに使わない**（09・10）

## 5. パッケージ構成

```
analytics/statistics/
├── README.md                 # シリーズ流儀の書式（章表・3 原則・実行手順）
├── pyproject.toml            # name = "stats-book"、hatchling、packages = ["src/stats_textbook"]
├── requirements.txt          # 単体 venv 用（workspace 非依存で走る）
├── src/stats_textbook/
│   ├── __init__.py
│   ├── datasets.py           # 合成データ生成器（全て seed 固定・外部 DL 無し）
│   ├── distributions.py      # 分布の関係図・指数型分布族の共通表現
│   ├── processes.py          # ランダムウォーク・マルコフ連鎖・ポアソン過程
│   ├── estimation.py         # MLE ソルバ・Fisher 情報（解析＆数値）・CRLB
│   ├── intervals.py          # ピボット/ブートストラップ(percentile・BCa)/順列
│   ├── testing.py            # 検定統計量・検出力計算・多重比較補正
│   ├── regression.py         # OLS 推測・頑健 SE(HC0–HC3)・診断量
│   ├── glm.py                # IRLS 自前実装（binomial/poisson）・逸脱度
│   ├── simulation.py         # 被覆確率・第 1 種の誤り率などのモンテカルロ実験ハーネス
│   ├── plotting/             # Plotly 図（純関数）
│   │   ├── __init__.py       # 再エクスポート（呼び出し側は from stats_textbook.plotting import ...）
│   │   ├── probability.py    # 01–05 章
│   │   ├── inference.py      # 06–08 章
│   │   └── regression.py     # 09–11 章
│   └── widgets.py            # ipywidgets 版（ライブカーネル用の補助）
├── tools/
│   ├── nbkit.py              # 既存書からコピー（md/code/write/build、PREAMBLE のみ改名）
│   ├── build_nb00.py … build_nb13.py
│   └── build_notebooks.py    # 全章ビルド（--check で dry-run）
├── notebooks/                # 出力込みでコミット（生成物だが版管理する）
├── tests/
│   ├── test_distributions.py  test_processes.py   test_estimation.py
│   ├── test_intervals.py      test_testing.py     test_regression.py
│   ├── test_glm.py            test_simulation.py  test_plotting.py  test_widgets.py
└── book/
    ├── _config.yml           # execute_notebooks: "off"、require.js で Plotly
    ├── _toc.yml
    └── notebooks -> ../notebooks   （symlink）
```

### モジュール分割の原則

- 依存は一方向: `distributions` → `estimation` → `intervals`/`testing` → `regression` → `glm`。逆参照なし
- `simulation` は実験ハーネスの末端。`(推定手続き, 真値, n, 反復数) → 実測被覆率/誤り率` という単一の型に揃え、07・08 章の主張がすべて同じ関数で検算される
- `plotting` は純関数（データ → `go.Figure`）に限定し、計算は各計算モジュール側に置く
- `plotting` は既存書で 500–750 行に膨らむため、最初から章ブロック単位のパッケージに分割する
- `widgets` は `plotting` の薄いラッパ。ライブカーネル専用で、静的 HTML の主役は Plotly スライダー

## 6. ノートブックの規約

### 1 章の標準構造

```
# 章タイトル
> 一文の要約（この章で読者が獲得する「見方」）

1. 導入      — 具体的な問い/誤解から入る（数式なし）
2. 直感と図   — Plotly のインタラクティブ図で現象を見せる
3. 定式化    — 最小限の数式。定義と主張を分ける
4. 実装      — stats_textbook のコードを呼ぶ（中身は src 側）
5. 実験      — シミュレーションで主張を検算する（第 2 原則）
6. 落とし穴   — 典型的な誤用と、それが数値でどう現れるか
7. 演習      — 3–5 問。解答は 13 章
```

### コールアウト

`linear_algebra` で基準化された MyST admonition を踏襲する。

- 💡 **核心**（class: tip）— 章あたり 1–2 個。「その章で 1 つだけ覚えるならこれ」
- 🌍 **実社会**（class: note）— 章あたり 1–2 個。医療診断・A/B テスト・品質管理・金融リスク

目標: 核心 ~18・実社会 ~16（`neural_net` 13/12、`bayesian` 13/11 と同水準か少し厚め）。

> MyST admonition 内の太字は CJK 約物で崩れる既知の地雷がある（`linear_algebra` で遭遇）。
> 約物に隣接する強調を避ける規約を `nbkit` の `--check` ルールで担保する。

### インタラクティブ図

- 主役は静的 HTML でも動く Plotly（`go.Figure` に `sliders`/`updatemenus` を焼き込む）
- `ipywidgets` はライブ用の補助のみ。無くても全章が読める
- 目標 16–20 点（`linear_algebra` 24・`neural_net` 16・`bayesian` 15）
- 看板図: (1) 04 章の CLT 対比、(2) 07 章の信頼区間 100 本、(3) 08 章の p-hacking 実演

### 言語

本文は日本語、コード・コメント・識別子は英語、LaTeX 内に日本語を入れない（シリーズ共通）。

### 生成パイプライン

`fourier`・`machine_learning` と同じ決定論的生成方式。

```bash
cd analytics/statistics
PYTHONPATH=src python tools/build_notebooks.py          # セル生成（--check で dry-run）
cd ~/projects                                            # 出力を埋める
for nb in analytics/statistics/notebooks/*.ipynb; do
  PYTHONPATH=analytics/statistics/src uv run --no-sync \
    jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

- ノートブックの JSON は手編集しない。`tools/build_nbNN.py` が唯一の正本
- 出力込みでコミット。Jupyter Book ビルド時は再実行しない
- 乱数は全て seed 固定。外部ダウンロード依存ゼロ（データは全て合成）
- 実行時間の予算: 全 14 章の再実行が合計 5 分以内

## 7. テスト方針

- **数値の正しさは既知の閉形式と照合**: 正規分布の Fisher 情報 = n/σ²、二項の MLE = 標本比率、
  χ² の分位点は `scipy.stats` と一致
- **自前 IRLS は statsmodels と係数・標準誤差で一致することをテスト**（10 章の主張そのもの）
- **モンテカルロの主張は緩い許容誤差でテスト**: 名目 95% 区間の実測被覆が seed 固定で 93–97% に入る
- **図は純関数テスト**: `go.Figure` が返る・トレース数・軸ラベル
- 想定テスト数 55–65 本（`bayesian` 55・`machine_learning` 59 と同水準）

## 8. 依存

`statsmodels>=0.14` を新規追加（GLM・多重比較・頑健 SE の照合先）。
教育用のコア（MLE・ブートストラップ・検定・IRLS）は自前実装し「中身を見せる」二本立てとする。
`sympy` は 06 章の Fisher 情報の解析導出で使う。他はシリーズ共通
（numpy / scipy / matplotlib / plotly / ipywidgets / pandas / scikit-learn / jupyter-book 系）。

## 9. workspace / ポータル統合

### root pyproject.toml

```toml
[tool.uv.workspace]
members = [ ..., "analytics/machine_learning", "analytics/statistics", ... ]

[tool.pytest.ini_options]
testpaths = [ ..., "analytics/statistics/tests", ... ]
```

`machine_learning` の前例に倣い、初回は `uv pip install -e --no-deps` で入れ、
`uv sync` は他プロジェクトへの影響を確認してから実行する。
`uv.lock` の差分が `statsmodels` とその依存に限定されることを確認してから commit する。

### root Makefile

`books` ターゲットに 1 行追加（既存の各書と同形式）。`make test` / `make lint` は
`testpaths` 登録で自動的に拾われる。

### report ポータル

`analytics/report/` のギャラリー入りとする。

- `report_builder/figures.py` に代表図を 2 点追加 — 07 章の信頼区間 100 本、04 章の CLT 対比
- 横断キャップストーン整合テストに統計書を追加（既存テストと同形式）

## 10. 実装順序

コードが先、ノートブックが後。各段階で `make test` が緑であることを確認する。

| # | 内容 | 完了条件 |
|---|---|---|
| **M0** | 足場 — ディレクトリ・pyproject・requirements・nbkit・book/_config・_toc・README 骨子・workspace 登録 | `uv run pytest analytics/statistics/tests` が通る・`jupyter-book build` が空の本を作れる |
| **M1** | 確率論のコア — `datasets` / `distributions` / `processes` / `simulation` ＋ `plotting/probability` | テスト ~20 本が緑 |
| **M2** | NB 00–05 生成（第Ⅰ部 6 章） | 全章が nbconvert で実行完了・図が静的 HTML で動く |
| **M3** | 推測のコア — `estimation` / `intervals` / `testing` ＋ `plotting/inference` | テスト ~25 本追加（CRLB・被覆確率・検出力の検算含む） |
| **M4** | NB 06–08 生成（推定・区間・検定） | 07 の被覆図と 08 の p-hacking 実演が動く |
| **M5** | 回帰と GLM — `regression` / `glm` ＋ `plotting/regression`、NB 09–10 | IRLS が statsmodels と一致するテストが緑 |
| **M6** | 橋渡し・キャップストーン・演習解答 — NB 11–13 | ベイズ書・ML 書へのリンクが正しい |
| **M7** | 仕上げ — README 完成・コールアウト数の点検・report ポータル統合・Makefile・全書ビルド | `make test` / `make lint` / `make books` / `make report` が全て緑 |

M1→M2、M3→M4 は依存するが、**M1 と M3 は独立**なので並行実装が可能（サブエージェント実行時の分割点）。

## 11. リスクと対策

| リスク | 対策 |
|---|---|
| モンテカルロのテストが確率的に落ちる | seed 完全固定＋許容幅を実測分布の ±3σ で設定。反復数はテストでは小さく、ノートブックでは大きく |
| `statsmodels` 追加が他プロジェクトのロックを壊す | `uv.lock` 差分を確認してから commit。壊れる場合は M5 の IRLS 一致テストを `pytest.importorskip` にして依存を任意化する |
| 全 14 章の実行時間が膨らむ | M2/M4 の各章で実行時間を計測し、合計 5 分の予算を超えたら反復数を削る |
| MyST 約物地雷で本文が崩れる | `nbkit` に約物隣接の強調を検出する `--check` ルールを入れる |
