# 機械学習の実践 — 正しく問題を定式化し、検証し、解釈する

Jupyter Notebook ベースの **古典的機械学習 + 実務ワークフロー** の教科書。
モデルの呼び出し方ではなく、**問題を正しく定式化し・リークを避け・指標を選び・検証し・解釈し・
再現可能なパイプラインを組む** ことを、直感 → 最小限の数式 → scikit-learn 実装 → 可視化 → 実験 → 演習
の順で学ぶ。ディープラーニングは姉妹本 [`analytics/neural_net`](../neural_net/) に分けてある。

- 対象: Python の基礎・統計の基礎・線形代数の基礎を知っている読者
- 方針: scikit-learn 同梱データかローカル生成の合成データのみ使用。ノート PC で全 Notebook が走る。乱数 seed 固定
- 本文は日本語、コードとコメントは英語、LaTeX 内に日本語を入れない
- インタラクティブは **静的 HTML でも動く Plotly スライダー** を主役にし、ipywidgets はライブカーネル用の補助

## 章構成(本編 10 + 付録 4)

| Notebook | 内容 | 状態 |
|---|---|---|
| `01_machine_learning_overview` | 全体像・汎化・未学習/過学習・バイアス-バリアンス・決定境界 | ✅ |
| `02_data_preprocessing_and_features` | 欠損・外れ値・スケール・エンコード・**リーク**・ColumnTransformer | ✅ |
| `03_linear_models` | OLS・多項式・Ridge/Lasso/ElasticNet・ロジスティック回帰・係数解釈 | ✅ |
| `04_model_evaluation_and_validation` | 指標・混同行列・ROC/PR・閾値・較正・交差検証・**リークで CV が嘘になる** | ✅ |
| `05_tree_based_models` | 決定木・不純度・RF(バギング)・勾配ブースティング・重要度 | ✅ |
| `06_svm_and_kernel_methods` | 最大マージン・サポートベクトル・ソフトマージン C・カーネル・RBF gamma | ✅ |
| `07_unsupervised_learning` | k-means・GMM・階層クラスタ・PCA・t-SNE/UMAP・異常検知 | ✅ |
| `08_time_series_ml` | 時間順・ラグ/ローリング特徴・TimeSeriesSplit・ウォークフォワード・ドリフト | ✅ |
| `09_model_interpretability` | 係数・permutation 重要度・PDP/ICE・相関≠因果・反実仮想・SHAP(任意) | ✅ |
| `10_practical_ml_pipeline` | Pipeline・GridSearch/RandomizedSearch・ネスト CV・保存/推論・ドリフト監視・誤差分析 | ✅ |
| `13_imbalanced_learning` | 付録: 不均衡データ — class_weight・リサンプリング・SMOTE・PR-AUC/balanced acc・較正の崩れ | ✅ |
| `14_feature_selection` | 付録: 特徴量選択 — filter/wrapper/embedded・CV 内選択(リーク防止)・選択の安定性 | ✅ |
| `11_capstone_four_lenses` | 付録: 同一回帰を ML/線形代数/ベイズ/勾配降下の4視点で解き同一リッジ解に一致＋モデル選択早見表 | ✅ |
| `12_exercise_solutions` | 付録: 01〜10 章 演習の解答 | ✅ |

共通コードは [`src/ml_textbook/`](src/ml_textbook/) にまとめている
(`datasets` / `preprocessing` / `plotting` / `widgets` / `metrics` / `validation` / `models` /
`interpretation` / `pipelines`)。

## 本書を貫く 3 つの原則

1. **汎化が目的**: 訓練精度ではなくテスト/交差検証で測る(01・04)。
2. **リークを避ける**: 前処理・特徴選択はすべて `Pipeline` の中で、訓練側だけで fit する(02・04・08)。
3. **解釈はモデルの説明であって因果ではない**(09)。

## 環境構築

### 単体で使う場合(推奨・自己完結)

```bash
cd analytics/machine_learning
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
# 任意の追加機能(seaborn / UMAP / SHAP):
pip install -e ".[extras]"
```

`seaborn` / `umap-learn` / `shap` は **任意依存** で、無くても全 Notebook が走る
(07 章の UMAP と 09 章の SHAP は、入っていれば自動で使い、無ければスキップする)。

### この workspace の root .venv を使う場合

本プロジェクトはまだ uv workspace のメンバーに追加していない(他プロジェクトと同時編集中のため)。
root の `.venv` には必要パッケージ(numpy / pandas / scikit-learn / plotly / ipywidgets …)が揃っているので、
`PYTHONPATH` を通せばそのまま使える:

```bash
cd ~/projects
PYTHONPATH=analytics/machine_learning/src uv run --no-sync jupyter lab analytics/machine_learning/notebooks/
```

workspace のメンバーにする場合は、root の `pyproject.toml` の
`[tool.uv.workspace] members` と `[tool.pytest.ini_options] testpaths` に
`analytics/machine_learning` を追加する(`_docs/` または下記「workspace への統合」を参照)。

## JupyterLab の起動

```bash
cd analytics/machine_learning
jupyter lab notebooks/          # 単体 venv の場合
```

`notebooks/` から起動すれば、各 Notebook 冒頭のセルが `../src` を自動で `sys.path` に追加するので
`import ml_textbook` がそのまま通る。

## Notebook の実行(出力の再生成)

各 Notebook は上から順に実行できる(乱数 seed 固定、CPU 実行で各数十秒〜2 分以内)。
出力込みでコミットしてあり、Jupyter Book ビルド時には再実行しない。

Notebook は `tools/`(共有 `nbkit` + 各章ビルダ)から決定論的に再生成できる。
`tools/build_notebooks.py` がセルを書き出し、その後 `nbconvert` で実行して出力を埋める:

```bash
cd analytics/machine_learning
PYTHONPATH=src python tools/build_notebooks.py        # セルを再生成(--check で temp 出力に dry-run)
# 出力を埋める(再実行):
cd ~/projects
for nb in analytics/machine_learning/notebooks/*.ipynb; do
  PYTHONPATH=analytics/machine_learning/src uv run --no-sync \
    jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

最も重いのは 07(t-SNE)で約 15 秒、10(GridSearch)で約 1 分。
データはすべて scikit-learn 同梱かローカル生成で、California Housing のみ初回に一度だけ
scikit-learn が自動取得・キャッシュする(以後オフライン)。

## Jupyter Book のビルド

```bash
cd ~/projects
uv run --no-sync jupyter-book build analytics/machine_learning/book/
# 出力: analytics/machine_learning/book/_build/html/index.html
```

`book/notebooks` は `../notebooks` への symlink。`book/_config.yml` で `execute_notebooks: "off"`
(コミット済み出力をそのまま使う)、require.js により Plotly スライダーが静的 HTML でも描画される。

## テスト

```bash
cd ~/projects
PYTHONPATH=analytics/machine_learning/src uv run --no-sync pytest analytics/machine_learning/tests -q
```

`datasets`(shape/再現性/Titanic シグナル)・`metrics`(scikit-learn と一致検証)・
`validation`(fold の分割・時系列の前後関係・リーク検出)・`preprocessing`(ColumnTransformer・スケール)・
`models`(ファクトリ・GD 線形回帰が OLS に収束)・`plotting` / `widgets`(スモーク)・
`interpretation` / `pipelines`(保存/再読込・ネスト CV)をカバー(52 本)。

## 推論サービス (serve/)

10 章で保存した `Pipeline` を実エンドポイントから叩くデモ(FastAPI サービス + CLI)。
生の乗客データ(欠損・カテゴリ可)をそのまま投げると、前処理ごと同梱された `Pipeline` が推論する。

```bash
cd analytics/machine_learning
PYTHONPATH=src python -m serve.train            # serve/model.joblib を生成
PYTHONPATH=src uvicorn serve.app:app --reload   # http://127.0.0.1:8000/docs
PYTHONPATH=src python -m serve.cli --pclass 1 --sex female --fare 100 --embarked C
```

依存は任意: `pip install -e ".[serve]"`(fastapi / uvicorn)。`serve/` はライブラリには含めず、プロジェクト直下から実行する。

## データ方針(bring your own data)

`src/ml_textbook/datasets.py` のローダ/ジェネレータを差し替えれば、自分のデータで全章を再利用できる。
表データは `make_titanic_like_dataset` を自分の DataFrame に、時系列は
`make_time_series_*` を自分の系列に置き換えるだけ。外部ダウンロードは California Housing の初回のみ。

## 関連教材

姉妹教材(同じ Jupyter Book 流儀の analytics シリーズ):

- [`analytics/linear_algebra`](../linear_algebra/) — 線形代数。本書 07 章の PCA は、その「行列分解・SVD・PCA」と地続き。
- [`analytics/neural_net`](../neural_net/) — ニューラルネット。本書の正則化・勾配降下・評価の考え方はそのまま深層学習へ続く。
- [`analytics/bayesian`](../bayesian/) — ベイズ推定。本書の正則化は事前分布、確率較正はベイズ的予測分布の話につながる。
- [`analytics/report`](../report/) — 3 教材の代表可視化を束ねるオフライン統合ポータル。
