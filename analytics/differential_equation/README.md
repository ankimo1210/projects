# 微分方程式 — 変化・流れ・場の言語

> シリーズ索引: [analytics 教材一覧](../README.md)

`analytics` シリーズの微分方程式プロジェクト。**常微分方程式 (ODE)** と
**偏微分方程式 (PDE)** の Jupyter Book に加え、**確率微分方程式 (SDE)** の
独立インタラクティブ Web 教科書を収める。

> **微分方程式は、変化・流れ・場を記述するための言語である。**

```text
microscope of change:  微分積分の基礎  →  ODE  →  PDE  →  応用
```

両書とも冒頭に **大学初等の微分積分(前提編 `00_calculus_foundations`)** を置き、
微分=変化率・積分=蓄積・偏微分=方向別の変化率・勾配=最も増える方向、という直感を作ってから
微分方程式へ進む構成。

## 3 つの教材

| プロジェクト | テーマ | 中心思想 |
|---|---|---|
| [`ode-book/`](ode-book/) | 常微分方程式 | 状態が **時間** とともにどう変わるか |
| [`pde-book/`](pde-book/) | 偏微分方程式 | **空間と時間** の中で、場がどう変化するか |
| [`sde-book/`](sde-book/) | 確率微分方程式 | **経路と分布** が不確実性の中でどう進化するか |

各プロジェクトは自分の `README.md` とテスト・ビルド設定を持つ standalone な教材。
ODE / PDE は Python + Jupyter Book、SDE は TypeScript + Canvas のブラウザ教材。詳しい使い方は各 README を参照。

## クイックスタート

```bash
# 単体で(例: ODE)
cd ode-book
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
uv run jupyter lab notebooks/        # もしくは: jupyter lab notebooks/

# Jupyter Book ビルド
jupyter-book build book/             # -> book/_build/html/index.html

# テスト(workspace 未登録でも)
PYTHONPATH=src python -m pytest tests -q
```

SDE 教材:

```bash
cd sde-book
npm ci
npm run dev
```

## ノートブックの再生成(任意)

ノートブックは出力込みでコミットしているが、`tools/` のビルドスクリプトで決定論的に再生成できる
(seed 固定)。`00_calculus_foundations` は両書共通のビルダーから生成される。

```bash
cd ..                                # analytics/differential_equation
python tools/build_calculus_notebook.py ode      # 00 章 (ODE 版)
python tools/build_calculus_notebook.py pde      # 00 章 (PDE 版)
python tools/build_ode_notebook.py all           # ODE 01..07
python tools/build_pde_notebook.py all           # PDE 01..07
python tools/build_ode_advanced_notebook.py      # ODE 09
python tools/build_pde_advanced_notebook.py      # PDE 09
python tools/build_ode_capstone_notebook.py      # ODE 10
python tools/build_capstone_notebook.py          # PDE 10
python tools/build_exercise_solutions_notebook.py  # ODE/PDE 08
# 生成後に: jupyter nbconvert --to notebook --execute --inplace <nb> で出力を埋め込む
```

## workspace への登録

ODE / PDE は既にルート `pyproject.toml` の `[tool.uv.workspace] members` と
`[tool.pytest.ini_options] testpaths` に登録済み。追記は不要で、リポジトリルートから

```bash
uv run --no-sync pytest analytics/differential_equation/ode-book/tests
uv run --no-sync pytest analytics/differential_equation/pde-book/tests
```

がそのまま動く。SDE は別ツールチェーン(npm)なので workspace の外にあり、
`make sde-check` から回る。
