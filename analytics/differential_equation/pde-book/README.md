# 偏微分方程式の風景 — 空間と時間の中の場の言語

Jupyter Notebook ベースの **偏微分方程式 (PDE)** 教科書プロジェクト。
PDE を「空間と時間の中で、場がどう変化するかを記述する言語」として、
図・可視化・Python 実験から概念の本質を掴むことを目指す。

> **微分方程式は、変化・流れ・場を記述するための言語である。**

冒頭に **大学初等の微分積分(前提編)** を置き、`微分積分 → ODE → PDE → 応用` という流れで読む設計。
姉妹教材 [`ode-book`](../ode-book/) を読んでから本書に進むと、空間方向の微分が自然に入る。

- 対象読者: 大学 1〜2 年生 / 学び直しの社会人 / 物理・金融・画像・ML に応用したい読者
- 方針: 定義から始めない。**現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展**
- 各章は **Basic(最低限)/ Applied(実装・応用)/ Advanced(証明・発展)** の 3 層構成

## 章構成

| Notebook | 内容 |
|---|---|
| `00_calculus_foundations` | **前提編**: 関数・極限・微分・積分・多変数微分(偏微分/勾配/Hessian)・多重積分・DE への接続 |
| `01_overview` | PDE の全体像 — 場とは何か、ODE との違い、時間発展問題と境界値問題、初期/境界条件 |
| `02_transport_heat_wave` | 移流・熱・波動 — 拡散と伝播の違い、時空間ヒートマップ |
| `03_laplace_poisson_boundary_value` | Laplace・Poisson・Dirichlet/Neumann・調和関数・平均値性 |
| `04_fourier_series_and_transform` | Fourier 級数/変換・周波数・Gibbs・熱方程式との接続 |
| `05_separation_of_variables` | 変数分離・固有関数・熱/波動の解析解・線形代数との接続 |
| `06_numerical_pde_fdm` | 有限差分法・陽/陰解法・安定性・CFL 条件・数値拡散 |
| `07_applications_physics_finance_ml` | 2D 熱伝導・Black-Scholes・画像拡散・拡散モデル |
| `08_exercise_solutions` | 付録: 全章 Exercises の解答(数式 + 数値検証) |

共通関数は `src/pde_book/` にまとめている
(`calculus.py` / `grids.py` / `solvers.py` / `plotting.py` / `widgets.py` /
`interactive.py`(Plotly スライダー)/ `datasets.py`)。`solvers` には陽/陰 FTCS に加え
**Crank-Nicolson**・**Neumann 境界(保存形)**・**非線形 Burgers** も含む。Poisson は疎行列の
Kronecker 和で組んだ 5 点ステンシルをベクトル化して直接解。

## 環境構築

### この workspace 内で使う場合(推奨)

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

（登録方法は下記「workspace への登録」参照。)

### 単体で使う場合

```bash
cd analytics/differential_equation/pde-book
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

各 Notebook の最初のセルは、`pde_book` が未インストールでも `src/` を自動で探して読み込む。

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/differential_equation/pde-book/notebooks/
```

## Notebook の実行

各 Notebook は上から順に実行できる(乱数は seed 固定)。全 Notebook を一括再実行:

```bash
cd ~/projects/analytics/differential_equation/pde-book
for nb in notebooks/0*.ipynb; do
  uv run jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

ipywidgets を使うセルは JupyterLab 上でのみ動く(静的 HTML では前後の説明文と静的図で意味が分かる)。

## Jupyter Book のビルド

Notebook は出力込みでコミットされており、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/differential_equation/pde-book
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects && uv run pytest analytics/differential_equation/pde-book/tests -q   # 登録済みの場合

cd ~/projects                                                                       # 未登録でも:
PYTHONPATH=analytics/differential_equation/pde-book/src \
  uv run --no-sync python -m pytest analytics/differential_equation/pde-book/tests -q
```

`grids`(格子・安定性数)、`solvers`(熱/移流/波動/Poisson を解析解と照合、不安定スキームの破綻も検証)、
`calculus`(数値/記号微積分)をテストしている。

## workspace への登録(任意)

ルート `pyproject.toml` の `[tool.uv.workspace] members` と
`[tool.pytest.ini_options] testpaths` に
`analytics/differential_equation/pde-book`(および `.../tests`)を追記する。

## 今後追加すべき内容

- Robin 境界条件と非長方形領域、有限要素法 (FEM) の入口
- 2 次元の波動・移流、反応拡散(Turing パターン)・KdV ソリトン
- スペクトル法(FFT ベース)の実装
- スコアベース拡散モデルの逆過程(現状は前向き拡散の概念図のみ)

済: 全章演習解答(`08`)、Plotly インタラクティブ(`interactive`: Fourier 項数・熱 `r`・CFL `C`・
Black-Scholes 3D 曲面)、**Crank-Nicolson**・**Neumann(保存形)**・**非線形 Burgers** ソルバ、
Poisson のベクトル化、property-based テスト(hypothesis)。

## 関連教材

- [`../ode-book`](../ode-book/) — 常微分方程式(時間方向)。先に読むと前提が揃う。
- [`../../linear_algebra`](../../linear_algebra/) — 固有値・対角化は変数分離(05 章)と同じ構造。
