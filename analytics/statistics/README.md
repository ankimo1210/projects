# 統計的推測の風景 — 不確実性を測り、判断する言語

> シリーズ索引: [analytics 教材一覧](../README.md)

確率論の基礎から頻度論の統計的推測までを、直感 → 図 → 最小限の数式 → Python 実装 →
実験 → 演習 の順で学ぶ Jupyter Book ベースの教科書。ベイズ側は姉妹本
[`analytics/bayesian`](../bayesian/) に分けてあり、本書 11 章が両者の橋渡しになる。

- 対象: Python の基礎と微積の初歩を知っている読者
- データはすべて合成・seed 固定。**データの外部ダウンロードはゼロ**
- 本文は日本語、コードとコメントは英語、LaTeX 内に日本語を入れない
- インタラクティブは **ライブカーネル不要の Plotly スライダー** が主役。
  `ipywidgets` は補助で、無くても全章が読める

## 本書を貫く 3 原則

1. **確率は長期頻度で定義する** — だから信頼区間は「真値が入る確率」ではない(07 章)
2. **すべての主張はシミュレーションで検算する** — 被覆確率も第 1 種の誤り率も実測する(07・08 章)
3. **モデルは仮定の束であり、診断せずに使わない**(09・10 章)

## 章構成

### 第Ⅰ部 確率論 — 基準を作る

| Notebook | 内容 | 実行時間 | 状態 |
|---|---|---|---|
| `00_overview` | 全体地図。同じデータから 2 人が違う結論を出す理由 | 6.4 s | ✅ |
| `01_probability_foundations` | 条件付き確率・独立・モンティホール・偽陽性パラドクス | 6.4 s | ✅ |
| `02_random_variables_expectation` | 期待値の線形性 vs 分散の加法性・Jensen・条件付き期待値 | 3.4 s | ✅ |
| `03_distributions_zoo` | 分布の関係図・ポアソン極限・指数型分布族・十分統計量 | 3.4 s | ✅ |
| `04_limit_theorems` | 大数の法則・中心極限定理・収束の 3 種・デルタ法 | 4.8 s | ✅ |
| `05_stochastic_processes` | ランダムウォーク・マルコフ連鎖・エルゴード性・ポアソン過程 | 3.9 s | ✅ |

### 第Ⅱ部 統計的推測 — 基準を使って判断する

| Notebook | 内容 | 状態 |
|---|---|---|
| `06_estimation_mle` | 推定量の性質・MLE・Fisher 情報・Cramér–Rao・漸近正規性 | 予定 |
| `07_confidence_intervals_bootstrap` | 区間推定の正しい読み方・被覆確率の実測・ブートストラップ | 予定 |
| `08_hypothesis_testing` | 検定の構造・p 値の誤解・検出力・多重比較・p-hacking | 予定 |
| `09_regression_inference` | 回帰係数の分布・残差診断・頑健標準誤差 | 予定 |
| `10_glm` | 指数型分布族から GLM へ・IRLS 自前実装 | 予定 |
| `11_frequentist_vs_bayes` | 同じデータを両流儀で解いて比べる橋渡し章 | 予定 |

### 付録

| Notebook | 内容 | 状態 |
|---|---|---|
| `12_capstone_three_lenses` | 頻度論／ベイズ／機械学習の 3 視点で同一データを解く | 予定 |
| `13_exercise_solutions` | 01–11 章 演習の解答 | 予定 |

第Ⅰ部の実測値: **6 章・140 セル・インタラクティブ図 8 点・
核心コールアウト 6・実社会コールアウト 6・全章の再実行が合計 28.3 秒**。

## 共通コード

[`src/stats_textbook/`](src/stats_textbook/) にまとめてある。依存は一方向で、逆参照は無い。

| モジュール | 責務 |
|---|---|
| `datasets` | 合成データ生成器と `SAMPLERS` レジストリ(全て seed 固定) |
| `distributions` | 分布の関係グラフ・指数型分布族の 4 部品・二項/ポアソンの TV 距離 |
| `processes` | ランダムウォーク・`MarkovChain`・ポアソン過程 |
| `simulation` | モンテカルロ実験ハーネス(被覆確率・棄却率・標本分布) |
| `plotting/` | Plotly 図の純関数。`core`(共通スライダー)と `probability`(01–05 章) |
| `widgets` | `plotting` の薄い ipywidgets ラッパ。ライブカーネル用 |

第Ⅱ部で `estimation` / `intervals` / `testing` / `regression` / `glm` と
`plotting/inference` / `plotting/regression` が加わる。

## 環境構築

### 単体で使う場合(自己完結)

```bash
cd analytics/statistics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### workspace の root .venv を使う場合

本プロジェクトは uv workspace のメンバーに登録済み
(root `pyproject.toml` の `members` と `testpaths`)。

```bash
cd ~/projects
PYTHONPATH=analytics/statistics/src uv run --no-sync jupyter lab analytics/statistics/notebooks/
```

### git worktree で作業する場合(注意)

**worktree の中で `uv run` を使ってはいけない。** worktree には `.venv` が無いため、
`uv` が新しい仮想環境を作り始める。root の `.venv` の python を直接呼ぶこと。

```bash
/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q
```

同じ理由で、root の `.venv` の editable install は他の教材のソースを
**main ツリー側から** 読む。並行セッションがそちらを編集していると、
本書と無関係なテストが落ちて見える。検証は `analytics/statistics/tests` に限定するか、
`PYTHONPATH` で worktree 側のソースを明示的に指す。

## Notebook の再生成

Notebook は **生成物** である。JSON を手編集せず、`tools/build_nbNN.py` を直す。

```bash
cd analytics/statistics
PYTHONPATH=src python tools/build_notebooks.py           # セルを再生成
PYTHONPATH=src python tools/build_notebooks.py --check   # 一時ディレクトリに dry-run

cd ~/projects                                            # 出力を埋める
for nb in analytics/statistics/notebooks/*.ipynb; do
  PYTHONPATH=analytics/statistics/src uv run --no-sync \
    jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

出力込みでコミットしてあり、Jupyter Book のビルド時には再実行しない
(`book/_config.yml` の `execute_notebooks: "off"`)。

図はビン集計済みの値だけを埋め込む。`go.Histogram` に生データを渡すと
1 章が 2.8 MB まで膨らんだため、`clt_convergence` は自前でビンを取って
`go.Bar` を描いている(見た目は同じで 155 KB)。

## Jupyter Book のビルド

```bash
cd ~/projects
uv run --no-sync jupyter-book build analytics/statistics/book/
# 出力: analytics/statistics/book/_build/html/index.html
```

`book/notebooks` は `../notebooks` への symlink。`require.js` を読み込むことで、
静的 HTML でも Plotly のスライダーが動く。

なお図の描画には **閲覧時に plotly.js を CDN から取得する**。
「外部ダウンロード依存ゼロ」はデータについての主張であって、
描画ライブラリは `notebook_connected` レンダラ経由で CDN から来る(シリーズ共通)。

ビルド時に出る `skipping unknown output mime type:
application/vnd.plotly.v1+json` は無害である。MyST-NB が Plotly 独自の mime を
飛ばしても、同じ出力に入っている `text/html` 表現が使われて図は描画される。

## テスト

```bash
cd ~/projects
uv run --no-sync pytest analytics/statistics/tests -q
```

第Ⅰ部完了時点で **57 passed**(smoke 1・nbkit 4・datasets 8・distributions 8・
processes 10・simulation 7・plotting 14・widgets 5)。

テストの方針:

- **数値は閉形式と照合する** — 二状態連鎖の定常分布、指数型分布族の対数密度を
  `scipy` と 1e-12 で突き合わせる、Le Cam の $np^2$ 上界
- **モンテカルロの主張はモンテカルロ誤差込みで判定する** — t 信頼区間の被覆が
  自身の 95% 区間に 0.95 を含むか。`sqrt(n)` を `n` と書き間違えた区間は 0.42 で捕まる
- **図は純関数として検査する** — トレース数・フレーム数・軸ラベル。描画自体はクライアント側
- **設計上の約束もテストで守る** — `widgets` が図を自作していないか、
  アニメーション図がスライダー配線を手書きしていないかを、ソースを走査して確認する

## CJK 約物と太字の地雷

CommonMark は `**` が開くか閉じるかを **両隣の文字** から決め、CJK の約物は
punctuation として扱われる。日本語として自然な次の 2 形が、警告も出さずに壊れる。

| 書き方 | 何が起きるか | 直し方 |
|---|---|---|
| `**「信頼区間」**は難しい` | 閉じ `**` の直前が約物・直後が文字 → 閉じられない | 閉じた後に空白を入れる |
| `各章には**「核心」**を置いた` | 開き `**` の直前が文字・直後が約物 → 開けない | 括弧を強調の外へ: `「**核心**」` |

`nbkit.md` が各行をレンダリングして強調が実際に生成されたかを確認し、
駄目なら例外を投げる。**片側だけを見る正規表現では検出できない** —
正しい `**実測する**。` を誤検出し、上の 2 形は素通りする。
