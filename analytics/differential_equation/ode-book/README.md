# 常微分方程式の風景 — 変化・流れ・場の言語

Jupyter Notebook ベースの **常微分方程式 (ODE)** 教科書プロジェクト。
ODE を「状態が時間とともにどう変わるかを記述する言語」として、
図・可視化・Python 実験から概念の本質を掴むことを目指す。

> **微分方程式は、変化・流れ・場を記述するための言語である。**

冒頭に **大学初等の微分積分(前提編)** を置き、`微分積分 → ODE → PDE → 応用` という流れで読む設計。
姉妹教材 [`pde-book`](../pde-book/) と対になる。

- 対象読者: 大学 1〜2 年生 / 学び直しの社会人 / 物理・生物・金融・ML に応用したい読者
- 方針: 定義から始めない。**現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展**
- 各章は **Basic(最低限)/ Applied(実装・応用)/ Advanced(証明・発展)** の 3 層構成

## 章構成

| Notebook | 内容 |
|---|---|
| `00_calculus_foundations` | **前提編**: 関数・極限・微分・積分・多変数微分(偏微分/勾配/Hessian)・多重積分・DE への接続 |
| `01_overview` | ODE の全体像 — 状態・時間・変化率、解析解と数値解、方向場 |
| `02_first_order_odes` | 一階 ODE・変数分離・線形一階・ロジスティック・方向場・初期条件 |
| `03_linear_odes_and_systems` | 高階線形・連立 ODE・行列形式・固有値・調和/減衰/強制振動 |
| `04_phase_plane_and_stability` | 相図・固定点・線形化・固有値分類(node/saddle/spiral/center)・ヌルクライン |
| `05_nonlinear_dynamics` | Lotka-Volterra・SIR・分岐(pitchfork)・カオスの入口(Lorenz) |
| `06_numerical_methods` | Euler/Heun/RK4・誤差と収束次数・安定性・stiff・`solve_ivp` |
| `07_applications_physics_biology_finance` | 物理(共振)・生物(SIR)・金融(OU/Vasicek)・ML(Neural ODE)・制御 |
| `09_boundary_value_sde_control` | 発展: 境界値問題/射撃法・固有値問題・SDE(Euler-Maruyama)・LQR/極配置・ODE 学習 |
| `08_exercise_solutions` | 付録: 全章 Exercises の解答(数式 + 数値検証) |

共通関数は `src/ode_book/` にまとめている
(`calculus.py` / `solvers.py` / `systems.py` / `plotting.py` / `widgets.py` /
`interactive.py`(Plotly スライダー)/ `datasets.py`)。インタラクティブ図は静的 HTML でも動作する
Plotly 版(`interactive`)と、JupyterLab 専用の ipywidgets 版(`widgets`)の 2 系統。

## 環境構築

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace のメンバーに登録すると:

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

（登録方法はリポジトリルート `pyproject.toml` の `[tool.uv.workspace] members` と
`[tool.pytest.ini_options] testpaths` に本プロジェクトのパスを追記する。下記「workspace への登録」参照。）

### 単体で使う場合

```bash
cd analytics/differential_equation/ode-book
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

各 Notebook の最初のセルは、`ode_book` が未インストールでも `src/` を自動で探して読み込むので、
clone してそのまま実行できる。

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/differential_equation/ode-book/notebooks/
```

## Notebook の実行

各 Notebook は上から順に実行できる(乱数は seed 固定)。全 Notebook を一括再実行:

```bash
cd ~/projects/analytics/differential_equation/ode-book
for nb in notebooks/0*.ipynb; do
  uv run jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

ipywidgets を使うセルは JupyterLab 上でのみ動く(静的 HTML では前後の説明文と静的図で意味が分かる)。

## Jupyter Book のビルド

Notebook は出力込みでコミットされており、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/differential_equation/ode-book
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
# workspace に登録済みなら
cd ~/projects && uv run pytest analytics/differential_equation/ode-book/tests -q

# 未登録でも src を通せば実行できる
cd ~/projects
PYTHONPATH=analytics/differential_equation/ode-book/src \
  uv run --no-sync python -m pytest analytics/differential_equation/ode-book/tests -q
```

`solvers`(精度・収束次数)、`systems`(平衡点・保存量・固定点分類)、`calculus`(数値/記号微積分)を
手計算値・解析解と照合している。

## workspace への登録(任意)

ルート `pyproject.toml` に以下を追記すると `make install` / `make test` に統合される:

```toml
# [tool.uv.workspace] members に追加
"analytics/differential_equation/ode-book",
"analytics/differential_equation/pde-book",

# [tool.pytest.ini_options] testpaths に追加
"analytics/differential_equation/ode-book/tests",
"analytics/differential_equation/pde-book/tests",
```

## 今後追加すべき内容

- Neural ODE を小さな実ニューラルネット + 随伴法で学習(現状は線形場の最小二乗フィット)
- 非線形 BVP のコレクション(`solve_bvp` 比較)
- ハミルトン系のシンプレクティック積分

済: 全章演習解答(`08`)、発展章(`09`: BVP/射撃法・固有値・SDE・LQR/極配置・ODE 学習)、
trace-determinant 図、Plotly インタラクティブ(`interactive`: ロジスティック `r`・Euler ステップ数・Lorenz 3D)、
property-based テスト(hypothesis)。

## 関連教材

- [`../pde-book`](../pde-book/) — 偏微分方程式(空間 + 時間)。本書の数値解法・固有値の話が直接つながる。
- [`../../linear_algebra`](../../linear_algebra/) — 固有値・対角化は 03/04 章の土台。
