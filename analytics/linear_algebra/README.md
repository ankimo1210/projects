# 線形代数の風景 — 空間・情報・変換の言語

Jupyter Notebook ベースの線形代数教科書プロジェクト。
線形代数を「空間・情報・変換・保存量を見るための言語」として、
図・可視化・Python 実験から概念の本質を掴むことを目指す。

- 対象: 大学 1〜2 年生 / 学び直しの社会人 / ML・物理・金融に関心のある読者
- 方針: 定義から始めない。具体的な問題・図・直感 → 定義・計算・定理の順に進む
- 各章は Basic(最低限)/ Applied(Python 実装・応用)/ Advanced(証明・発展)の 3 層構成

## 章構成

| Notebook | 内容 |
|---|---|
| `00_overview` | 全体像・この教材の読み方・環境準備 |
| `01_vectors_matrices_geometry` | ベクトル・行列・行列積・グリッド変形・行列式の直感 |
| `02_linear_systems_rank_basis` | 連立一次方程式・掃き出し法・ランク・基底・核と像 |
| `03_linear_maps_determinants_eigen` | 線形写像・基底変換・行列式・固有値・対角化 |
| `04_inner_products_projection_least_squares` | 内積・直交性・正射影・Gram-Schmidt・最小二乗・リッジ |
| `05_matrix_decompositions_svd_pca` | LU/QR/Cholesky・スペクトル定理・SVD・画像圧縮・PCA・白色化 |
| `06_numerical_linear_algebra_optimization` | 浮動小数点誤差・条件数・solve vs inv・CG・勾配降下・Newton |
| `07_applications_graph_markov_finance_quantum` | Markov 連鎖・PageRank・スペクトルクラスタリング・金融 PCA・量子入門 |
| `09_iterative_methods_preconditioning` | 付録: Jacobi・Gauss-Seidel・GMRES・前処理 |
| `10_complex_spaces_jordan_form` | 付録: 複素ベクトル空間・Unitary・複素固有値・Jordan 標準形 |
| `11_kronecker_tensors_matrix_calculus` | 付録: クロネッカー積・vec・テンソル・行列微分 |
| `12_capstone_three_lenses` | キャップストーン: 1つの回帰を3冊の視点で(正規方程式・SVD・リッジ) |
| `08_exercise_solutions` | 付録: 全演習(01〜07、計42問)の解答 |

共通関数は `src/la_book/` にまとめている
(`plotting.py` / `widgets.py` / `algebra.py` / `decompositions.py` / `datasets.py`)。

## 環境構築

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace のメンバーになっているので:

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

### 単体で使う場合

```bash
cd analytics/linear_algebra
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/linear_algebra/notebooks/
```

## Notebook の実行

各 Notebook は上から順に実行できる(乱数は seed 固定)。
全 Notebook を一括再実行するには:

```bash
cd ~/projects/analytics/linear_algebra
for nb in notebooks/0*.ipynb; do
  uv run jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

ipywidgets を使うセルは JupyterLab 上でのみ動く(静的 HTML では代替の静的図を参照)。

## Jupyter Book のビルド

Notebook は出力込みでコミットされており、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。
`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/linear_algebra
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects
uv run pytest analytics/linear_algebra/tests -q
```

## データの差し替え(bring your own data)

外部ダウンロードに依存しないのが原則(既定はすべて seed 固定の合成データ)。
実データで試したいときは `la_book.datasets.load_yield_curves(path="your.csv")` のように
フックへパスを渡すだけで、07 章の金利カーブ PCA を実データで再現できる。

## 関連教材

姉妹教材(同じ Jupyter Book 流儀の analytics シリーズ):

- [`analytics/neural_net`](../neural_net/) — ニューラルネット。
  本書の 05 章(SVD・低ランク近似・PCA)は、その 08 章(オートエンコーダ)・10 章(LoRA)に接続する。
- [`analytics/bayesian`](../bayesian/) — ベイズ推定。
  本書の内積・正射影・行列分解は、ベイズ線形回帰や共分散の固有値分解の土台になる。
- [`analytics/report`](../report/) — **統合インタラクティブポータル**。3教材の代表可視化を
  オフラインで束ねるショーケース(`make report`)。本書の SVD スペクトル・低ランク近似・固有方向の
  スライダーもここで一望できる。

## 今後追加すべき内容

