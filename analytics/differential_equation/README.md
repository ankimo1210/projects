# 微分方程式 — 変化・流れ・場の言語

`analytics` シリーズの微分方程式プロジェクト。**常微分方程式 (ODE)** と
**偏微分方程式 (PDE)** を、それぞれ独立した Jupyter Book 教科書として収める。

> **微分方程式は、変化・流れ・場を記述するための言語である。**

```text
microscope of change:  微分積分の基礎  →  ODE  →  PDE  →  応用
```

両書とも冒頭に **大学初等の微分積分(前提編 `00_calculus_foundations`)** を置き、
微分=変化率・積分=蓄積・偏微分=方向別の変化率・勾配=最も増える方向、という直感を作ってから
微分方程式へ進む構成。

## 2 つの教材

| プロジェクト | テーマ | 中心思想 |
|---|---|---|
| [`ode-book/`](ode-book/) | 常微分方程式 | 状態が **時間** とともにどう変わるか |
| [`pde-book/`](pde-book/) | 偏微分方程式 | **空間と時間** の中で、場がどう変化するか |

各プロジェクトは自分の `README.md` / `pyproject.toml` / `src/` / `tests/` / `book/` を持つ
standalone なパッケージ。詳しい使い方は各 README を参照。

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

## ノートブックの再生成(任意)

ノートブックは出力込みでコミットしているが、`tools/` のビルドスクリプトで決定論的に再生成できる
(seed 固定)。`00_calculus_foundations` は両書共通のビルダーから生成される。

```bash
cd ..                                # analytics/differential_equation
python tools/build_calculus_notebook.py ode      # 00 章 (ODE 版)
python tools/build_calculus_notebook.py pde      # 00 章 (PDE 版)
python tools/build_ode_notebook.py all           # ODE 01..07
python tools/build_pde_notebook.py all           # PDE 01..07
# 生成後に: jupyter nbconvert --to notebook --execute --inplace <nb> で出力を埋め込む
```

## workspace への登録(任意)

uv workspace(リポジトリルート `~/projects`)に取り込む場合、ルート `pyproject.toml` に追記:

```toml
# [tool.uv.workspace] members
"analytics/differential_equation/ode-book",
"analytics/differential_equation/pde-book",

# [tool.pytest.ini_options] testpaths
"analytics/differential_equation/ode-book/tests",
"analytics/differential_equation/pde-book/tests",
```
