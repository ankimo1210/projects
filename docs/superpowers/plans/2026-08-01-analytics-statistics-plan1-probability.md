# analytics/statistics Plan 1 — 足場・確率論のコア・第Ⅰ部 6 章 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** analytics シリーズ 8 冊目『統計的推測の風景』の足場を作り、確率論のコア実装（`datasets` / `distributions` / `processes` / `simulation` / `plotting` / `widgets`）と第Ⅰ部 6 章（NB 00–05）を完成させる。

**Architecture:** `src/stats_textbook/` に純関数中心のライブラリを置き、ノートブックは `tools/build_nbNN.py` から決定論的に生成する（`fourier`・`machine_learning` と同方式）。計算は計算モジュール、描画は `plotting/`（データ → `go.Figure` の純関数）に分離し、`widgets` は `plotting` の薄い ipywidgets ラッパ。依存は一方向 `datasets` → `distributions` → `processes` / `simulation` → `plotting` → `widgets`。

**Tech Stack:** Python 3.12・numpy・scipy・sympy・pandas・plotly・ipywidgets・nbformat・jupyter-book・pytest

## Global Constraints

設計書 `docs/superpowers/specs/2026-08-01-analytics-statistics-design.md` の全体要件。**全タスクの要求に暗黙的に含まれる。**

- 本文は日本語、コード・コメント・識別子は英語、**LaTeX 内に日本語を入れない**
- 乱数は **seed 固定で再現可能**、**外部ダウンロード依存ゼロ**（データは全て合成）
- 可視化の主役は **静的 HTML でも動く Plotly**（`go.Figure` に `sliders` を焼き込む）。`ipywidgets` はライブカーネル用の補助で、無くても全章が読める
- `plotting` は**純関数**（データ → `go.Figure`）。計算は計算モジュール側に置く
- モジュール依存は**一方向**。逆参照を作らない
- ノートブックの JSON は**手編集しない**。`tools/build_nbNN.py` が唯一の正本
- ノートブックは**出力込みでコミット**。Jupyter Book ビルド時は再実行しない（`execute_notebooks: "off"`）
- ~~MyST admonition 内で約物に隣接する太字を書かない~~ — **撤回済み（Task 8 で実測）**。markdown-it は該当する綴りをすべて `<strong>` として描画し、既存 3 書の admonition 56 行が同じ形を使って正常にビルドされている。`nbkit` の `check_typography` は撤去した
- 全 14 章の再実行が合計 **5 分以内**（Plan 1 の範囲では NB 00–05 で 2 分以内）
- コールアウトは 💡 **核心**（class: tip）と 🌍 **実社会**（class: note）の 2 種、章あたり各 1–2 個
- 新規依存は `statsmodels>=0.14` のみ（宣言は Task 1、使用は Plan 2 の M5）

## 実行環境（重要 — 最初に読むこと）

作業ディレクトリは **git worktree** `/home/kazumasa/projects/.claude/worktrees/analytics-statistics`（ブランチ `worktree-analytics-statistics`）。

```bash
# このプランで使う Python。以後 $PY と書く。
PY=/home/kazumasa/projects/.venv/bin/python
```

- **`uv run` を worktree 内で使ってはいけない。** worktree に `.venv` が無いため `uv` が新しい仮想環境を作り始める（実測済み）。root の `.venv` の python を直接叩くこと
- テストは `$PY -m pytest analytics/statistics/tests -q` で走る。`tests/conftest.py` が `src/` を `sys.path` に入れるので、`pip install -e` は不要
- ノートブック実行は `PYTHONPATH=analytics/statistics/src $PY -m jupyter nbconvert ...`
- Jupyter Book ビルドは `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
- **既知の落とし穴**: root の `.venv` の editable install は `la_book` 等を **main ツリー側**（`/home/kazumasa/projects/analytics/...`）から読む。`analytics/linear_algebra` のテストが落ちても本プランとは無関係（並行セッションが編集中）。本プランの検証は必ず `analytics/statistics/tests` に限定して行う

## File Structure

| ファイル | 責務 | Task |
|---|---|---|
| `analytics/statistics/pyproject.toml` | パッケージ定義（`stats-book`）と依存 | 1 |
| `analytics/statistics/requirements.txt` | 単体 venv 用の依存 | 1 |
| `analytics/statistics/README.md` | 章表・3 原則・実行手順 | 1・14 |
| `analytics/statistics/tests/conftest.py` | `src/` を `sys.path` に入れる | 1 |
| `analytics/statistics/tools/nbkit.py` | `md` / `code` / `write` / `build` ＋ 約物チェック | 1 |
| `analytics/statistics/tools/build_notebooks.py` | 全章ビルドのドライバ（`--check` で dry-run） | 1・8–13 |
| `analytics/statistics/book/_config.yml` `_toc.yml` | Jupyter Book 設定 | 1・8–13 |
| `src/stats_textbook/datasets.py` | 合成データ生成器（全て seed 固定） | 2 |
| `src/stats_textbook/distributions.py` | 分布の関係・指数型分布族 | 3 |
| `src/stats_textbook/processes.py` | ランダムウォーク・マルコフ連鎖・ポアソン過程 | 4 |
| `src/stats_textbook/simulation.py` | モンテカルロ実験ハーネス | 5 |
| `src/stats_textbook/plotting/core.py` | 汎用スライダー helper | 6 |
| `src/stats_textbook/plotting/probability.py` | 01–05 章の図 | 6 |
| `src/stats_textbook/widgets.py` | ipywidgets ラッパ（ライブ用の補助） | 7 |
| `tools/build_nb00.py` … `build_nb05.py` | 各章のセル定義（唯一の正本） | 8–13 |
| root `pyproject.toml` / `Makefile` | workspace 登録・`books` ターゲット | 1 |

`plotting/inference.py` と `plotting/regression.py` は Plan 2 で作る。Plan 1 では `plotting/__init__.py` が `core` と `probability` のみ再エクスポートする。

---

### Task 1: 足場（M0）

**Files:**
- Create: `analytics/statistics/pyproject.toml`
- Create: `analytics/statistics/requirements.txt`
- Create: `analytics/statistics/README.md`
- Create: `analytics/statistics/src/stats_textbook/__init__.py`
- Create: `analytics/statistics/tools/nbkit.py`
- Create: `analytics/statistics/tools/build_notebooks.py`
- Create: `analytics/statistics/book/_config.yml`
- Create: `analytics/statistics/book/_toc.yml`
- Create: `analytics/statistics/book/notebooks` （`../notebooks` への symlink）
- Create: `analytics/statistics/notebooks/00_overview.ipynb` （front matter のみ。Task 8 で本文を足す）
- Test: `analytics/statistics/tests/conftest.py`
- Test: `analytics/statistics/tests/test_smoke.py`
- Modify: `pyproject.toml`（`[tool.uv.workspace] members` と `[tool.pytest.ini_options] testpaths`）
- Modify: `Makefile`（`books` ターゲット）

**Interfaces:**
- Consumes: なし
- Produces: `stats_textbook.__version__: str`、`tools/nbkit.py` の `md(text) -> NotebookNode` / `code(src) -> NotebookNode` / `write(cells, path) -> str` / `build(cells, path, preamble=True) -> str` / `check_typography(text) -> list[str]`

- [ ] **Step 1: ディレクトリと `__init__.py` を作る**

```bash
cd /home/kazumasa/projects/.claude/worktrees/analytics-statistics
mkdir -p analytics/statistics/{src/stats_textbook,tests,tools,notebooks,book}
```

`analytics/statistics/src/stats_textbook/__init__.py`:

```python
"""統計的推測の風景 — 確率論と頻度論統計の教科書 (analytics series).

Modules are layered one-way:
``datasets`` -> ``distributions`` -> ``processes`` / ``simulation``
-> ``plotting`` -> ``widgets``. Nothing imports backwards.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
```

- [ ] **Step 2: 失敗する smoke テストを書く**

`analytics/statistics/tests/conftest.py`:

```python
"""Make ``stats_textbook`` importable before the project is pip-installed.

The package lives under ``src/``. Prepending it to ``sys.path`` keeps the
tests (and notebooks launched from this directory) working in a bare
checkout. Harmless once the project is installed into the workspace venv.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

`analytics/statistics/tests/test_smoke.py`:

```python
"""The scaffold is wired: the package imports and declares a version."""

import stats_textbook


def test_package_imports_and_has_version():
    assert isinstance(stats_textbook.__version__, str)
    assert stats_textbook.__version__.count(".") == 2
```

- [ ] **Step 3: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q`
Expected: PASS（Step 1 で `__init__.py` を先に作ったため）。**もし FAIL するなら** `conftest.py` のパス解決が誤っている。`parents[1]` が `analytics/statistics` を指すことを確認する。

> このタスクは足場なので TDD の赤→緑サイクルが 1 往復しかない。以降の Task 2 以降は必ず「赤を見てから緑にする」。

- [ ] **Step 4: `pyproject.toml` を書く**

`analytics/statistics/pyproject.toml`:

```toml
[project]
name = "stats-book"
version = "0.1.0"
description = "Jupyter-Book statistics textbook (Japanese): probability and frequentist inference, simulation-verified"
requires-python = ">=3.12"
dependencies = [
    "numpy>=2.0",
    "scipy>=1.13",
    "sympy>=1.12",
    "matplotlib>=3.9",
    "plotly>=5.22",
    "ipywidgets>=8.1",
    "pandas>=2.2",
    "statsmodels>=0.14",
    "jupyterlab>=4.2",
    "jupyter-book>=1.0,<2",
    "ipykernel>=6.29",
    "nbformat>=5.10",
    "nbclient>=0.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/stats_textbook"]
```

`analytics/statistics/requirements.txt`:

```
numpy>=2.0
scipy>=1.13
sympy>=1.12
matplotlib>=3.9
plotly>=5.22
ipywidgets>=8.1
pandas>=2.2
statsmodels>=0.14
jupyterlab>=4.2
jupyter-book>=1.0,<2
ipykernel>=6.29
nbformat>=5.10
nbclient>=0.10
```

> `statsmodels` は Plan 2（M5）まで **import されない**。宣言だけ先に置く。root の `.venv` には未インストールだが、`--no-sync` 運用なので Plan 1 の検証には影響しない。

- [ ] **Step 5: `nbkit.py` を書く**

`analytics/statistics/tools/nbkit.py`:

```python
"""Tiny helpers for building notebooks programmatically with nbformat.

Used by ``build_notebooks.py`` and the per-notebook ``build_nbNN.py`` modules.
Keeping the notebooks under version control as *generated* artifacts means we
can regenerate them deterministically (seeds fixed) instead of hand-editing JSON.

Mirrors the sibling analytics books' ``nbkit`` (``md`` / ``code`` / ``write`` /
``build``) and adds ``check_typography``: MyST admonitions render bold text
incorrectly when the ``**`` sits directly against a CJK bracket, which the
linear_algebra book hit in practice.
"""

from __future__ import annotations

import re

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

# Prepended as the first code cell: make ``stats_textbook`` importable whether
# or not the project has been pip-installed, by walking up to the dir holding
# src/stats_textbook.
PREAMBLE = """
import sys, pathlib
_here = pathlib.Path.cwd().resolve()
for _p in [_here, *_here.parents]:
    if (_p / "src" / "stats_textbook").exists():
        sys.path.insert(0, str(_p / "src"))
        break
""".strip()

# ``**`` immediately preceded or followed by a CJK bracket / punctuation mark.
_CJK_PUNCT = "「」『』（）【】、。・"
_BAD_BOLD = re.compile(rf"\*\*[{_CJK_PUNCT}]|[{_CJK_PUNCT}]\*\*(?!\S)")


def check_typography(text: str) -> list[str]:
    """Return the offending lines where bold markers touch CJK punctuation."""
    return [line for line in text.splitlines() if _BAD_BOLD.search(line)]


def md(text: str):
    """A markdown cell (leading/trailing blank lines trimmed)."""
    body = text.strip("\n")
    offenders = check_typography(body)
    if offenders:
        raise ValueError(
            "bold marker touches CJK punctuation (MyST renders this wrong):\n  "
            + "\n  ".join(offenders)
        )
    return new_markdown_cell(body)


def code(src: str):
    """A code cell (leading/trailing blank lines trimmed)."""
    return new_code_cell(src.strip("\n"))


def _metadata() -> dict:
    return {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }


def write(cells, path: str):
    """Assemble cells into a v4 notebook and write it to ``path`` (no preamble)."""
    nb = new_notebook(cells=list(cells))
    nb["metadata"] = _metadata()
    nbformat.write(nb, path)
    return path


def build(cells, path: str, preamble: bool = True):
    """Write a notebook, prepending the import-path preamble by default."""
    all_cells = ([new_code_cell(PREAMBLE)] if preamble else []) + list(cells)
    write(all_cells, path)
    print(f"wrote {path} ({len(all_cells)} cells)")
    return path
```

- [ ] **Step 6: `nbkit` の約物チェックにテストを書く**

`analytics/statistics/tests/test_nbkit.py`:

```python
"""The notebook builder rejects the CJK-punctuation bold trap."""

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nbkit  # noqa: E402


def test_check_typography_flags_bold_against_cjk_bracket():
    assert nbkit.check_typography("**「信頼区間」** は難しい")
    assert nbkit.check_typography("難しいのは「信頼区間」**だ**") == []


def test_md_raises_on_bad_bold():
    with pytest.raises(ValueError, match="CJK punctuation"):
        nbkit.md("**「これはダメ」**")


def test_md_accepts_clean_bold():
    cell = nbkit.md("信頼区間は **長期頻度** の性質である")
    assert cell.cell_type == "markdown"
```

> `_BAD_BOLD` の `(?!\S)` が肝。検出したいのは強調の**内側**が約物に接する場合（`**「信頼区間」**`）だけで、`「信頼区間」**だ**` のように約物の外側で強調が始まる書き方は正しい。後者では `」**` の直後に `だ` が来るので `(?!\S)` が効いて除外される。前者の末尾 `」**` は行末（または空白）なので検出される。

- [ ] **Step 7: テストを走らせる**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q`
Expected: PASS 4 件（smoke 1 ＋ nbkit 3）。落ちたら Step 6 の注記に従って `_BAD_BOLD` を確認する。

- [ ] **Step 7b: README の骨子を書く**

`analytics/statistics/README.md`（Task 14 で実測値を入れて完成させる。ここでは構成だけ置く）:

```markdown
# 統計的推測の風景 — 不確実性を測り、判断する言語

> シリーズ索引: [analytics 教材一覧](../README.md)

確率論の基礎から頻度論の統計的推測までを、直感 → 図 → 最小限の数式 → Python 実装 →
実験 → 演習 の順で学ぶ Jupyter Book ベースの教科書。ベイズ側は姉妹本
[`analytics/bayesian`](../bayesian/) に分けてある。

- 対象: Python の基礎と微積の初歩を知っている読者
- 方針: データはすべて合成・seed 固定。外部ダウンロード依存ゼロ
- 本文は日本語、コードとコメントは英語、LaTeX 内に日本語を入れない
- インタラクティブは静的 HTML でも動く Plotly スライダーが主役

## 本書を貫く 3 原則

1. **確率は長期頻度で定義する** — だから信頼区間は「真値が入る確率」ではない（07 章）
2. **すべての主張はシミュレーションで検算する** — 被覆確率も第 1 種の誤り率も実測する（07・08 章）
3. **モデルは仮定の束であり、診断せずに使わない**（09・10 章）

## 章構成

（Task 14 で全 14 章の表と実測実行時間を入れる）

## 環境構築

（Task 14 で単体 venv / workspace / worktree の 3 通りを書く）
```

- [ ] **Step 8: `build_notebooks.py` と Jupyter Book 設定を書く**

`analytics/statistics/tools/build_notebooks.py`:

```python
"""Regenerate all textbook notebooks from their builder modules.

    PYTHONPATH=src python tools/build_notebooks.py            # write notebooks/*.ipynb
    PYTHONPATH=src python tools/build_notebooks.py --check     # dry-run into a temp dir

Each ``build_nbNN.py`` exposes a ``cells`` list; this driver writes them via
``nbkit.build`` (which adds the import preamble). Notebooks are committed WITH
outputs, so after regenerating you must execute them (see README).
"""

from __future__ import annotations

import importlib
import pathlib
import sys
import tempfile

TOOLS = pathlib.Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

# (builder module, output notebook stem) in book order.
# Plan 1 fills 00-05; Plan 2 and 3 append 06-13.
NOTEBOOKS = [
    ("build_nb00", "00_overview"),
    ("build_nb01", "01_probability_foundations"),
    ("build_nb02", "02_random_variables_expectation"),
    ("build_nb03", "03_distributions_zoo"),
    ("build_nb04", "04_limit_theorems"),
    ("build_nb05", "05_stochastic_processes"),
]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    import nbkit

    out_dir = pathlib.Path(tempfile.mkdtemp(prefix="stats_nb_")) if check else (PROJECT / "notebooks")
    for mod_name, stem in NOTEBOOKS:
        mod = importlib.import_module(mod_name)
        nbkit.build(mod.cells, str(out_dir / f"{stem}.ipynb"))
    print(f"\n{'checked' if check else 'wrote'} {len(NOTEBOOKS)} notebooks -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

> **重要**: `NOTEBOOKS` は Task 8 で `build_nb00` だけを残し、Task 9–13 で 1 行ずつ有効化していく。Task 1 の時点では `build_nb00` 以外のモジュールが存在しないので、**Task 1 では `NOTEBOOKS` を `[("build_nb00", "00_overview")]` の 1 行だけにしておく**（上のリストは最終形で、Task 13 完了時にこうなる）。

`analytics/statistics/book/_config.yml`:

```yaml
title: 統計的推測の風景 — 不確実性を測り、判断する言語
author: Kazumasa
language: ja
only_build_toc_files: true

execute:
  # Notebooks are committed with their outputs already executed
  # (see README). Keep the book build fast and deterministic.
  execute_notebooks: "off"

sphinx:
  config:
    # require.js is needed so Plotly figures embedded by nbconvert render
    # in the static HTML (the documented Jupyter Book + Plotly setup).
    html_js_files:
      - https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js

repository:
  url: https://github.com/ankimo1210/projects
  path_to_book: analytics/statistics

html:
  use_issues_button: false
  use_repository_button: false
```

`analytics/statistics/book/_toc.yml`（Task 1 の時点では `root` のみ。Task 9–13 で `chapters` に 1 行ずつ足す）:

```yaml
# Table of contents for jupyter-book.
# `notebooks/` here is a symlink to ../notebooks (Jupyter Book requires all
# content below the book root).
format: jb-book
root: notebooks/00_overview
```

```bash
cd analytics/statistics/book && ln -s ../notebooks notebooks && cd -
```

- [ ] **Step 9: front matter だけの `00_overview.ipynb` を作る**

`analytics/statistics/tools/build_nb00.py`（Task 8 で本文を足すが、ここでは本を成立させる最小の front matter）:

```python
"""Builder for notebook 00 — Overview (front matter; extended in Task 8)."""

from nbkit import md

cells = [
    md(r"""
# 統計的推測の風景 — 不確実性を測り、判断する言語

> 各章は 直感 → 図 → 最小限の数式 → Python 実装 → 実験 → 演習 の順。
> 本文は日本語、コードは英語、数式に日本語を入れない。

## 本書を貫く 3 原則

1. **確率は長期頻度で定義する** — だから信頼区間は「真値が入る確率」ではない（07 章）
2. **すべての主張はシミュレーションで検算する** — 被覆確率も第 1 種の誤り率も実測する（07・08 章）
3. **モデルは仮定の束であり、診断せずに使わない**（09・10 章）
"""),
]
```

```bash
cd analytics/statistics && PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py && cd -
```

Expected: `wrote .../notebooks/00_overview.ipynb (2 cells)`

- [ ] **Step 10: Jupyter Book がビルドできることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
Expected: `Finished generating HTML for book.`・`analytics/statistics/book/_build/html/index.html` が生成される

- [ ] **Step 11: workspace と Makefile に登録する**

root `pyproject.toml` の `[tool.uv.workspace] members` に `"analytics/machine_learning",` の直後へ追加:

```toml
    "analytics/machine_learning",
    "analytics/statistics",
```

root `pyproject.toml` の `[tool.pytest.ini_options] testpaths` に `"analytics/machine_learning/tests",` の直後へ追加:

```toml
    "analytics/machine_learning/tests",
    "analytics/statistics/tests",
```

root `Makefile` の `books:` ターゲット、`machine_learning` の行の直後へ追加:

```make
	uv run --no-sync jupyter-book build analytics/machine_learning/book/
	uv run --no-sync jupyter-book build analytics/statistics/book/
```

- [ ] **Step 12: 登録後に analytics 全体が壊れていないことを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests analytics/bayesian/tests analytics/machine_learning/tests -q`
Expected: PASS（statistics 4 ＋ bayesian 55 ＋ machine_learning 59 = 118 件前後）

> **なぜこの確認が要るか**: ディレクトリ名 `statistics` は標準ライブラリのモジュール名と同名。pytest 9 の importlib モードは `analytics/statistics/tests/conftest.py` を `analytics.statistics.tests.conftest` として import するので、合成される名前空間はトップレベルの `statistics` ではなく `analytics.statistics` であり、標準ライブラリを覆わない **はず**。ここで実測して確認する。もし `statistics` 由来の ImportError が出たら、root の `conftest.py`（`/home/kazumasa/projects/.claude/worktrees/analytics-statistics/conftest.py`）のコメントに記録されている手当てと同じ方針で対処し、何が起きたかを README に残すこと。

- [ ] **Step 13: `.gitignore` を確認して commit**

```bash
grep -n "_build\|__pycache__" .gitignore | head
```

`analytics/statistics/book/_build/` が無視されていなければ `.gitignore` に `analytics/statistics/book/_build/` を追加する。

```bash
git add analytics/statistics pyproject.toml Makefile .gitignore
git commit -m "feat(statistics): scaffold the statistics textbook

Adds the 8th analytics book as an empty but buildable shell: package,
tests wired through conftest, the nbkit notebook builder, Jupyter Book
config, and workspace/Makefile registration.

nbkit gains check_typography -- MyST renders bold wrongly when ** sits
against a CJK bracket, which linear_algebra hit in practice, so the
builder now refuses to emit such a cell instead of leaving it to be
found by eye at review time.

statsmodels is declared but unused until M5."
```

---

### Task 2: `datasets.py` — 合成データ生成器

**Files:**
- Create: `analytics/statistics/src/stats_textbook/datasets.py`
- Test: `analytics/statistics/tests/test_datasets.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `coin_flips(n: int, p: float = 0.5, seed: int = 0) -> np.ndarray`（dtype int、値 0/1）
  - `disease_test_counts(n: int, prevalence: float, sensitivity: float, specificity: float, seed: int = 0) -> dict[str, int]`（キー `"tp"` `"fp"` `"fn"` `"tn"`）
  - `normal_sample(n: int, mu: float = 0.0, sigma: float = 1.0, seed: int = 0) -> np.ndarray`
  - `exponential_sample(n: int, rate: float = 1.0, seed: int = 0) -> np.ndarray`
  - `bivariate_normal(n: int, rho: float, seed: int = 0) -> tuple[np.ndarray, np.ndarray]`
  - `heavy_tailed_sample(n: int, kind: str = "cauchy", seed: int = 0) -> np.ndarray`（`kind` は `"cauchy"` / `"pareto"`）
  - `SAMPLERS: dict[str, Callable[[int, np.random.Generator], np.ndarray]]`（名前 → `(n, rng) -> sample`。04 章の CLT 図と Task 5 の `simulation` が使う）

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_datasets.py`:

```python
"""Synthetic data generators: shapes, determinism, and stated parameters."""

import numpy as np
import pytest
from stats_textbook import datasets


def test_coin_flips_are_binary_and_deterministic():
    a = datasets.coin_flips(200, p=0.7, seed=3)
    b = datasets.coin_flips(200, p=0.7, seed=3)
    assert a.shape == (200,)
    assert set(np.unique(a)) <= {0, 1}
    np.testing.assert_array_equal(a, b)
    # 200 draws at p=0.7 sit within 4 sd of 140 with overwhelming probability.
    assert abs(a.sum() - 140) < 4 * np.sqrt(200 * 0.7 * 0.3)


def test_disease_test_counts_partition_the_population():
    counts = datasets.disease_test_counts(
        100_000, prevalence=0.01, sensitivity=0.99, specificity=0.95, seed=0
    )
    assert set(counts) == {"tp", "fp", "fn", "tn"}
    assert sum(counts.values()) == 100_000
    # The paradox this feeds (NB01): false positives swamp true positives.
    assert counts["fp"] > counts["tp"]


def test_normal_sample_matches_its_parameters():
    x = datasets.normal_sample(50_000, mu=3.0, sigma=2.0, seed=1)
    assert abs(x.mean() - 3.0) < 0.05
    assert abs(x.std(ddof=1) - 2.0) < 0.05


def test_exponential_sample_has_mean_one_over_rate():
    x = datasets.exponential_sample(50_000, rate=4.0, seed=1)
    assert (x > 0).all()
    assert abs(x.mean() - 0.25) < 0.01


def test_bivariate_normal_reproduces_the_requested_correlation():
    x, y = datasets.bivariate_normal(50_000, rho=-0.6, seed=2)
    assert x.shape == y.shape == (50_000,)
    assert abs(np.corrcoef(x, y)[0, 1] + 0.6) < 0.02


def test_heavy_tailed_sample_has_no_stable_mean():
    x = datasets.heavy_tailed_sample(20_000, kind="cauchy", seed=5)
    running = np.cumsum(x) / np.arange(1, x.size + 1)
    # A Cauchy running mean keeps wandering; a normal one would settle.
    assert np.std(running[1000:]) > 0.1


def test_heavy_tailed_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        datasets.heavy_tailed_sample(10, kind="gumbel")


def test_samplers_registry_is_callable_and_deterministic():
    assert {"normal", "uniform", "exponential", "cauchy"} <= set(datasets.SAMPLERS)
    for name, fn in datasets.SAMPLERS.items():
        a = fn(64, np.random.default_rng(0))
        b = fn(64, np.random.default_rng(0))
        assert a.shape == (64,), name
        np.testing.assert_array_equal(a, b)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_datasets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.datasets'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/datasets.py`:

```python
"""Synthetic data generators for the textbook.

Everything is generated locally from a seeded ``numpy`` Generator: the book
must run offline and reproduce byte-identical figures. No dataset is ever
downloaded.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

__all__ = [
    "SAMPLERS",
    "bivariate_normal",
    "coin_flips",
    "disease_test_counts",
    "exponential_sample",
    "heavy_tailed_sample",
    "normal_sample",
]


def coin_flips(n: int, p: float = 0.5, seed: int = 0) -> np.ndarray:
    """``n`` Bernoulli(p) draws as 0/1 integers."""
    rng = np.random.default_rng(seed)
    return (rng.random(n) < p).astype(int)


def disease_test_counts(
    n: int, prevalence: float, sensitivity: float, specificity: float, seed: int = 0
) -> dict[str, int]:
    """Simulate a screening programme and return the 2x2 confusion counts.

    Feeds NB01's false-positive paradox: at low prevalence the false
    positives outnumber the true positives even for an accurate test.
    """
    rng = np.random.default_rng(seed)
    diseased = rng.random(n) < prevalence
    positive = np.where(
        diseased, rng.random(n) < sensitivity, rng.random(n) > specificity
    )
    return {
        "tp": int(np.sum(diseased & positive)),
        "fn": int(np.sum(diseased & ~positive)),
        "fp": int(np.sum(~diseased & positive)),
        "tn": int(np.sum(~diseased & ~positive)),
    }


def normal_sample(n: int, mu: float = 0.0, sigma: float = 1.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(mu, sigma, n)


def exponential_sample(n: int, rate: float = 1.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.exponential(1.0 / rate, n)


def bivariate_normal(n: int, rho: float, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Standard bivariate normal with correlation ``rho`` (Cholesky construction)."""
    if not -1.0 < rho < 1.0:
        raise ValueError(f"rho must lie strictly inside (-1, 1); got {rho}")
    rng = np.random.default_rng(seed)
    z1, z2 = rng.normal(size=(2, n))
    return z1, rho * z1 + np.sqrt(1.0 - rho**2) * z2


def heavy_tailed_sample(n: int, kind: str = "cauchy", seed: int = 0) -> np.ndarray:
    """A sample with no finite mean (``cauchy``) or no finite variance (``pareto``)."""
    rng = np.random.default_rng(seed)
    if kind == "cauchy":
        return rng.standard_cauchy(n)
    if kind == "pareto":
        # alpha = 1.5: mean exists, variance does not.
        return rng.pareto(1.5, n) + 1.0
    raise ValueError(f"unknown kind {kind!r}; expected 'cauchy' or 'pareto'")


# name -> (n, rng) -> sample. Used by the CLT figure (NB04) and by
# ``simulation`` (Task 5), both of which own their own Generator.
SAMPLERS: dict[str, Callable[[int, np.random.Generator], np.ndarray]] = {
    "normal": lambda n, rng: rng.normal(0.0, 1.0, n),
    "uniform": lambda n, rng: rng.uniform(-np.sqrt(3.0), np.sqrt(3.0), n),
    "exponential": lambda n, rng: rng.exponential(1.0, n) - 1.0,
    "cauchy": lambda n, rng: rng.standard_cauchy(n),
}
```

> `uniform` と `exponential` は平均 0・分散 1 に揃えてある（CLT の収束速度を素性の違いだけで比べるため）。`cauchy` だけは正規化できない — それがこの章の主張。

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_datasets.py -q`
Expected: PASS 8 件

- [ ] **Step 5: lint を通す**

Run: `/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format --check analytics/statistics`
Expected: 両方 PASS。format が落ちたら `ruff format analytics/statistics` で直す。

- [ ] **Step 6: commit**

```bash
git add analytics/statistics/src/stats_textbook/datasets.py analytics/statistics/tests/test_datasets.py
git commit -m "feat(statistics): synthetic data generators

All samples come from a seeded Generator so the book reproduces offline.
The SAMPLERS registry normalises uniform and exponential to mean 0 and
variance 1 so NB04 can compare CLT convergence speed on shape alone --
cauchy is deliberately left unnormalised, which is that chapter's point."
```

---

### Task 3: `distributions.py` — 分布の関係と指数型分布族

**Files:**
- Create: `analytics/statistics/src/stats_textbook/distributions.py`
- Test: `analytics/statistics/tests/test_distributions.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `Relation` — frozen dataclass、フィールド `source: str` / `target: str` / `condition: str`
  - `RELATIONS: tuple[Relation, ...]`
  - `relation_layout() -> dict[str, tuple[float, float]]`（ノード名 → 座標。Task 6 の関係図が使う）
  - `ExponentialFamily` — frozen dataclass、フィールド `name: str` / `natural_param: Callable[[float], float]` / `sufficient_stat: Callable[[np.ndarray], np.ndarray]` / `log_partition: Callable[[float], float]` / `log_base_measure: Callable[[np.ndarray], np.ndarray]`
  - `EXPONENTIAL_FAMILIES: dict[str, ExponentialFamily]`（キー `"bernoulli"` `"poisson"` `"normal_unit_var"` `"exponential"`）
  - `exponential_family_logpdf(family: ExponentialFamily, theta: float, x: np.ndarray) -> np.ndarray`
  - `binomial_poisson_tv_distance(n: int, p: float) -> float`

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_distributions.py`:

```python
"""Exponential-family algebra checked against scipy's closed forms."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import distributions as dist


def test_relations_are_well_formed_and_laid_out():
    names = {r.source for r in dist.RELATIONS} | {r.target for r in dist.RELATIONS}
    layout = dist.relation_layout()
    assert names <= set(layout), "every node in RELATIONS needs a position"
    assert all(r.condition for r in dist.RELATIONS), "every edge states its condition"
    # The three limits the chapter is built around.
    pairs = {(r.source, r.target) for r in dist.RELATIONS}
    assert ("binomial", "poisson") in pairs
    assert ("binomial", "normal") in pairs
    assert ("normal", "chi2") in pairs


def test_bernoulli_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["bernoulli"]
    x = np.array([0, 1, 1, 0, 1])
    got = dist.exponential_family_logpdf(family, 0.3, x)
    want = stats.bernoulli.logpmf(x, 0.3)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_poisson_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["poisson"]
    x = np.array([0, 1, 4, 9])
    got = dist.exponential_family_logpdf(family, 2.5, x)
    want = stats.poisson.logpmf(x, 2.5)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_normal_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["normal_unit_var"]
    x = np.array([-1.5, 0.0, 0.7, 2.2])
    got = dist.exponential_family_logpdf(family, 0.4, x)
    want = stats.norm.logpdf(x, loc=0.4, scale=1.0)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_exponential_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["exponential"]
    x = np.array([0.2, 1.0, 3.3])
    got = dist.exponential_family_logpdf(family, 1.7, x)
    want = stats.expon.logpdf(x, scale=1.0 / 1.7)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_sufficient_statistic_is_the_sample_sum_for_all_four():
    x = np.array([0.5, 1.5, 2.0])
    for name, family in dist.EXPONENTIAL_FAMILIES.items():
        t = family.sufficient_stat(x)
        assert t.shape == x.shape, name


def test_binomial_poisson_distance_shrinks_as_p_shrinks():
    far = dist.binomial_poisson_tv_distance(20, 0.5)
    near = dist.binomial_poisson_tv_distance(20, 0.02)
    assert 0.0 <= near < far <= 1.0
    # Le Cam's bound: the total-variation distance is at most n * p^2.
    assert near <= 20 * 0.02**2 + 1e-12


def test_binomial_poisson_distance_rejects_bad_p():
    with pytest.raises(ValueError, match="p"):
        dist.binomial_poisson_tv_distance(10, 1.5)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_distributions.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.distributions'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/distributions.py`:

```python
"""How the standard distributions relate, and the exponential family that
explains why so many of them share the same estimation machinery.

The exponential-family objects here are deliberately written as the four
callables in the definition

    log p(x | theta) = eta(theta) * T(x) - A(eta(theta)) + log h(x)

so the notebook can print each piece separately and check the sum against
``scipy``. The point of NB03 is that the pieces are the interesting part.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import special, stats

__all__ = [
    "EXPONENTIAL_FAMILIES",
    "RELATIONS",
    "ExponentialFamily",
    "Relation",
    "binomial_poisson_tv_distance",
    "exponential_family_logpdf",
    "relation_layout",
]


@dataclass(frozen=True)
class Relation:
    """A directed limit or transformation between two distributions."""

    source: str
    target: str
    condition: str


RELATIONS: tuple[Relation, ...] = (
    Relation("bernoulli", "binomial", "n 回の独立和"),
    Relation("binomial", "poisson", "n -> inf, p -> 0, np = lambda 一定"),
    Relation("binomial", "normal", "n -> inf, p 固定 (de Moivre-Laplace)"),
    Relation("poisson", "normal", "lambda -> inf"),
    Relation("exponential", "gamma", "k 個の独立和"),
    Relation("gamma", "chi2", "k = df/2, scale = 2"),
    Relation("normal", "chi2", "標準正規の二乗和"),
    Relation("normal", "t", "正規 / sqrt(chi2/df)"),
    Relation("chi2", "f", "独立な chi2 の比"),
    Relation("t", "normal", "df -> inf"),
)


def relation_layout() -> dict[str, tuple[float, float]]:
    """Fixed positions for the relation graph (NB03's map of the territory)."""
    return {
        "bernoulli": (0.0, 2.0),
        "binomial": (1.0, 2.0),
        "poisson": (2.0, 2.6),
        "normal": (3.0, 1.6),
        "exponential": (0.0, 0.0),
        "gamma": (1.0, 0.0),
        "chi2": (2.2, 0.4),
        "t": (3.6, 0.6),
        "f": (3.2, -0.6),
    }


@dataclass(frozen=True)
class ExponentialFamily:
    """log p(x | theta) = eta(theta) T(x) - A(eta) + log h(x)."""

    name: str
    natural_param: Callable[[float], float]
    sufficient_stat: Callable[[np.ndarray], np.ndarray]
    log_partition: Callable[[float], float]
    log_base_measure: Callable[[np.ndarray], np.ndarray]


def exponential_family_logpdf(
    family: ExponentialFamily, theta: float, x: np.ndarray
) -> np.ndarray:
    """Evaluate the family's log density by assembling its four pieces."""
    x = np.asarray(x, dtype=float)
    eta = family.natural_param(theta)
    return (
        eta * family.sufficient_stat(x)
        - family.log_partition(eta)
        + family.log_base_measure(x)
    )


EXPONENTIAL_FAMILIES: dict[str, ExponentialFamily] = {
    # p in (0, 1): eta = logit(p), A(eta) = log(1 + e^eta), h(x) = 1.
    "bernoulli": ExponentialFamily(
        name="bernoulli",
        natural_param=lambda p: math.log(p / (1.0 - p)),
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: float(np.logaddexp(0.0, eta)),
        log_base_measure=lambda x: np.zeros_like(x),
    ),
    # lambda > 0: eta = log(lambda), A(eta) = e^eta, h(x) = 1 / x!.
    "poisson": ExponentialFamily(
        name="poisson",
        natural_param=math.log,
        sufficient_stat=lambda x: x,
        log_partition=math.exp,
        log_base_measure=lambda x: -special.gammaln(x + 1.0),
    ),
    # sigma = 1: eta = mu, A(eta) = eta^2 / 2, h(x) = exp(-x^2/2)/sqrt(2 pi).
    "normal_unit_var": ExponentialFamily(
        name="normal_unit_var",
        natural_param=float,
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: 0.5 * eta**2,
        log_base_measure=lambda x: -0.5 * x**2 - 0.5 * math.log(2.0 * math.pi),
    ),
    # rate > 0: eta = -rate, A(eta) = -log(-eta), h(x) = 1 on x >= 0.
    "exponential": ExponentialFamily(
        name="exponential",
        natural_param=lambda rate: -rate,
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: -math.log(-eta),
        log_base_measure=lambda x: np.zeros_like(x),
    ),
}


def binomial_poisson_tv_distance(n: int, p: float) -> float:
    """Total-variation distance between Binomial(n, p) and Poisson(np).

    Bounded above by ``n * p**2`` (Le Cam), which is why the Poisson limit
    is a good approximation exactly when p is small.
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must lie in [0, 1]; got {p}")
    k = np.arange(0, n + 1)
    binom = stats.binom.pmf(k, n, p)
    pois = stats.poisson.pmf(k, n * p)
    # Poisson has mass above n; the half-sum form accounts for it via the
    # tail that binom assigns zero to.
    tail = 1.0 - stats.poisson.cdf(n, n * p)
    return float(0.5 * (np.abs(binom - pois).sum() + tail))
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_distributions.py -q`
Expected: PASS 8 件

> `test_binomial_poisson_distance_shrinks_as_p_shrinks` の Le Cam 上界のアサーションは、上の `tail` の足し方で満たされるはず。もし僅かに超えて落ちる場合は、実装ではなくテストの許容を `+ 1e-12` から `* (1 + 1e-9)` に緩めるのではなく、**まず `tail` の二重計上を疑う**こと（`binom` は k > n に質量を持たないので `tail` は 1 回だけ足す）。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/distributions.py analytics/statistics/tests/test_distributions.py
git commit -m "feat(statistics): distribution relations and the exponential family

The four families are stored as the four callables of the definition
rather than as a finished log-density, so NB03 can print eta, T, A and h
separately and show that the sum reproduces scipy exactly. That
decomposition is what makes sufficiency and conjugacy legible later.

binomial_poisson_tv_distance is checked against Le Cam's n*p^2 bound,
which is the quantitative form of 'the Poisson limit works when p is
small'."
```

---

### Task 4: `processes.py` — ランダムウォーク・マルコフ連鎖・ポアソン過程

**Files:**
- Create: `analytics/statistics/src/stats_textbook/processes.py`
- Test: `analytics/statistics/tests/test_processes.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `random_walk(n_steps: int, n_paths: int = 1, step: str = "rademacher", seed: int = 0) -> np.ndarray`（形 `(n_paths, n_steps + 1)`、先頭列は 0）
  - `MarkovChain` — frozen dataclass、フィールド `P: np.ndarray` / `states: tuple[str, ...] | None = None`、メソッド `distribution_after(n: int, p0: np.ndarray) -> np.ndarray` / `stationary() -> np.ndarray` / `simulate(n_steps: int, x0: int = 0, seed: int = 0) -> np.ndarray` / `is_irreducible() -> bool` / `period() -> int`
  - `poisson_process(rate: float, t_max: float, seed: int = 0) -> np.ndarray`（イベント時刻の昇順配列）
  - `poisson_counts(rate: float, t_max: float, n_reps: int, seed: int = 0) -> np.ndarray`（各反復のイベント数）

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_processes.py`:

```python
"""Random walks, Markov chains, and the Poisson process."""

import numpy as np
import pytest
from stats_textbook import processes as proc

# A two-state chain with a known stationary distribution: pi = (b, a)/(a+b)
# for P = [[1-a, a], [b, 1-b]].
TWO_STATE = np.array([[0.9, 0.1], [0.2, 0.8]])
# Deterministic 2-cycle: irreducible but periodic with period 2.
CYCLE = np.array([[0.0, 1.0], [1.0, 0.0]])
# Two closed classes: not irreducible.
REDUCIBLE = np.array([[1.0, 0.0], [0.0, 1.0]])


def test_random_walk_shape_starts_at_zero_and_is_deterministic():
    a = proc.random_walk(50, n_paths=7, seed=1)
    b = proc.random_walk(50, n_paths=7, seed=1)
    assert a.shape == (7, 51)
    assert (a[:, 0] == 0).all()
    np.testing.assert_array_equal(a, b)


def test_rademacher_walk_moves_by_exactly_one_each_step():
    paths = proc.random_walk(200, n_paths=3, step="rademacher", seed=2)
    assert set(np.unique(np.diff(paths, axis=1))) == {-1.0, 1.0}


def test_random_walk_rejects_unknown_step():
    with pytest.raises(ValueError, match="step"):
        proc.random_walk(10, step="levy")


def test_markov_chain_rejects_rows_that_are_not_distributions():
    with pytest.raises(ValueError, match="rows"):
        proc.MarkovChain(np.array([[0.5, 0.2], [0.3, 0.7]]))


def test_stationary_matches_the_closed_form():
    chain = proc.MarkovChain(TWO_STATE)
    pi = chain.stationary()
    np.testing.assert_allclose(pi, [2 / 3, 1 / 3], rtol=1e-10)
    # Stationarity is the defining property.
    np.testing.assert_allclose(pi @ TWO_STATE, pi, rtol=1e-10)


def test_distribution_after_converges_to_the_stationary_law():
    chain = proc.MarkovChain(TWO_STATE)
    p = chain.distribution_after(200, np.array([1.0, 0.0]))
    np.testing.assert_allclose(p, chain.stationary(), atol=1e-8)


def test_simulate_visits_states_in_stationary_proportion():
    chain = proc.MarkovChain(TWO_STATE)
    path = chain.simulate(50_000, x0=0, seed=4)
    assert path.shape == (50_001,)
    visited = np.bincount(path, minlength=2) / path.size
    np.testing.assert_allclose(visited, chain.stationary(), atol=0.02)


def test_irreducibility_and_period():
    assert proc.MarkovChain(TWO_STATE).is_irreducible()
    assert proc.MarkovChain(TWO_STATE).period() == 1
    assert proc.MarkovChain(CYCLE).is_irreducible()
    assert proc.MarkovChain(CYCLE).period() == 2
    assert not proc.MarkovChain(REDUCIBLE).is_irreducible()


def test_poisson_process_times_are_sorted_and_inside_the_window():
    t = proc.poisson_process(rate=5.0, t_max=10.0, seed=0)
    assert (np.diff(t) > 0).all()
    assert t[-1] <= 10.0


def test_poisson_counts_have_mean_and_variance_equal_to_rate_times_time():
    counts = proc.poisson_counts(rate=3.0, t_max=4.0, n_reps=20_000, seed=0)
    assert counts.shape == (20_000,)
    assert abs(counts.mean() - 12.0) < 0.15
    # The Poisson signature: variance equals the mean.
    assert abs(counts.var() - 12.0) < 0.4
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_processes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.processes'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/processes.py`:

```python
"""Probability on a time axis: random walks, Markov chains, Poisson processes.

The one chapter of the book that leaves the i.i.d. world. Kept deliberately
small -- the aim is to make 'the future depends on the present only' concrete,
not to build a stochastic-process library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

__all__ = ["MarkovChain", "poisson_counts", "poisson_process", "random_walk"]

_STEPS = ("rademacher", "normal")


def random_walk(
    n_steps: int, n_paths: int = 1, step: str = "rademacher", seed: int = 0
) -> np.ndarray:
    """``n_paths`` walks of ``n_steps`` increments, each starting at 0.

    Returns shape ``(n_paths, n_steps + 1)`` so column 0 is the common origin.
    """
    if step not in _STEPS:
        raise ValueError(f"unknown step {step!r}; expected one of {_STEPS}")
    rng = np.random.default_rng(seed)
    if step == "rademacher":
        increments = rng.choice([-1.0, 1.0], size=(n_paths, n_steps))
    else:
        increments = rng.normal(0.0, 1.0, size=(n_paths, n_steps))
    return np.concatenate(
        [np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)], axis=1
    )


@dataclass(frozen=True)
class MarkovChain:
    """A finite, time-homogeneous Markov chain given by its transition matrix."""

    P: np.ndarray
    states: tuple[str, ...] | None = field(default=None)

    def __post_init__(self) -> None:
        P = np.asarray(self.P, dtype=float)
        if P.ndim != 2 or P.shape[0] != P.shape[1]:
            raise ValueError(f"P must be square; got shape {P.shape}")
        if (P < 0).any() or not np.allclose(P.sum(axis=1), 1.0):
            raise ValueError("P rows must be probability distributions (>= 0, summing to 1)")
        object.__setattr__(self, "P", P)

    @property
    def n_states(self) -> int:
        return self.P.shape[0]

    def distribution_after(self, n: int, p0: np.ndarray) -> np.ndarray:
        """The law of the chain after ``n`` steps started from ``p0``."""
        p = np.asarray(p0, dtype=float)
        if not math.isclose(p.sum(), 1.0, abs_tol=1e-9):
            raise ValueError("p0 must sum to 1")
        return p @ np.linalg.matrix_power(self.P, n)

    def stationary(self) -> np.ndarray:
        """The left eigenvector of P with eigenvalue 1, normalised to sum to 1."""
        values, vectors = np.linalg.eig(self.P.T)
        idx = int(np.argmin(np.abs(values - 1.0)))
        pi = np.real(vectors[:, idx])
        return pi / pi.sum()

    def simulate(self, n_steps: int, x0: int = 0, seed: int = 0) -> np.ndarray:
        """One trajectory of state indices, length ``n_steps + 1``."""
        rng = np.random.default_rng(seed)
        path = np.empty(n_steps + 1, dtype=int)
        path[0] = x0
        cdf = np.cumsum(self.P, axis=1)
        u = rng.random(n_steps)
        for t in range(n_steps):
            path[t + 1] = int(np.searchsorted(cdf[path[t]], u[t]))
        return path

    def _reachability(self) -> np.ndarray:
        """Boolean matrix: can state i reach state j in any number of steps."""
        n = self.n_states
        reach = (self.P > 0) | np.eye(n, dtype=bool)
        # Transitive closure: n-1 squarings suffice for an n-state chain.
        for _ in range(int(math.ceil(math.log2(max(n, 2))))):
            reach = reach @ reach
        return reach

    def is_irreducible(self) -> bool:
        return bool(self._reachability().all())

    def period(self) -> int:
        """The gcd of the return times of state 0 (common to all states when
        the chain is irreducible)."""
        n = self.n_states
        power = np.eye(n)
        period = 0
        for k in range(1, 2 * n + 1):
            power = power @ self.P
            if power[0, 0] > 1e-12:
                period = math.gcd(period, k)
                if period == 1:
                    return 1
        return period if period else 0


def poisson_process(rate: float, t_max: float, seed: int = 0) -> np.ndarray:
    """Event times of a homogeneous Poisson process on ``[0, t_max]``.

    Built from exponential gaps, which is the construction the chapter uses
    to explain why the counts end up Poisson.
    """
    if rate <= 0:
        raise ValueError(f"rate must be positive; got {rate}")
    rng = np.random.default_rng(seed)
    times: list[float] = []
    t = 0.0
    while True:
        t += rng.exponential(1.0 / rate)
        if t > t_max:
            break
        times.append(t)
    return np.asarray(times)


def poisson_counts(rate: float, t_max: float, n_reps: int, seed: int = 0) -> np.ndarray:
    """Event counts over ``n_reps`` independent windows of length ``t_max``."""
    rng = np.random.default_rng(seed)
    return rng.poisson(rate * t_max, n_reps)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_processes.py -q`
Expected: PASS 10 件

> `period()` の実装で `REDUCIBLE`（単位行列）は `P[0,0] = 1 > 0` なので周期 1 を返す。テストは `REDUCIBLE` の周期を主張していないので問題ないが、可約な連鎖に対する `period()` の値には意味がないことを docstring が明示していることを確認すること。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/processes.py analytics/statistics/tests/test_processes.py
git commit -m "feat(statistics): random walks, Markov chains, Poisson processes

poisson_process is built from exponential gaps rather than by drawing a
Poisson count and scattering points, because the gap construction is what
NB05 uses to explain where the Poisson count comes from. poisson_counts
draws directly -- it only ever feeds the mean-equals-variance check.

The stationary distribution comes from the left eigenvector, and the
tests pin it against the closed form for a two-state chain as well as
against its own defining property pi P = pi."
```

---

### Task 5: `simulation.py` — モンテカルロ実験ハーネス

**Files:**
- Create: `analytics/statistics/src/stats_textbook/simulation.py`
- Test: `analytics/statistics/tests/test_simulation.py`

**Interfaces:**
- Consumes: `stats_textbook.datasets.SAMPLERS`（テストでのみ使用）
- Produces:
  - `MonteCarloResult` — frozen dataclass、フィールド `estimate: float` / `se: float` / `n_reps: int`、メソッド `ci95() -> tuple[float, float]`
  - `sampling_distribution(statistic: Callable[[np.ndarray], float], sampler: Sampler, n: int, n_reps: int, seed: int = 0) -> np.ndarray`
  - `coverage_probability(sampler: Sampler, interval_fn: Callable[[np.ndarray], tuple[float, float]], truth: float, n: int, n_reps: int, seed: int = 0) -> MonteCarloResult`
  - `rejection_rate(sampler: Sampler, pvalue_fn: Callable[[np.ndarray], float], alpha: float, n: int, n_reps: int, seed: int = 0) -> MonteCarloResult`
  - 型エイリアス `Sampler = Callable[[int, np.random.Generator], np.ndarray]`

> **この 3 関数が本書の第 2 原則の実体。** 07 章の被覆確率も 08 章の第 1 種の誤り率も、すべてここを通す。Plan 2 の M3 はこのモジュールを **拡張せずそのまま使う**。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_simulation.py`:

```python
"""The Monte-Carlo harness that every 'we checked it by simulation' claim uses."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import simulation as sim


def normal_sampler(n, rng):
    return rng.normal(0.0, 1.0, n)


def t_interval(sample):
    """The textbook 95% t interval for a normal mean."""
    n = sample.size
    half = stats.t.ppf(0.975, n - 1) * sample.std(ddof=1) / np.sqrt(n)
    return float(sample.mean() - half), float(sample.mean() + half)


def broken_interval(sample):
    """Uses the normal quantile and divides by n instead of sqrt(n)."""
    half = 1.96 * sample.std(ddof=1) / sample.size
    return float(sample.mean() - half), float(sample.mean() + half)


def t_test_pvalue(sample):
    return float(stats.ttest_1samp(sample, 0.0).pvalue)


def test_monte_carlo_result_reports_a_sensible_interval():
    r = sim.MonteCarloResult(estimate=0.95, se=0.01, n_reps=500)
    lo, hi = r.ci95()
    assert lo < 0.95 < hi
    assert abs((hi - lo) - 2 * 1.96 * 0.01) < 1e-12


def test_sampling_distribution_shape_and_determinism():
    a = sim.sampling_distribution(np.mean, normal_sampler, n=25, n_reps=400, seed=7)
    b = sim.sampling_distribution(np.mean, normal_sampler, n=25, n_reps=400, seed=7)
    assert a.shape == (400,)
    np.testing.assert_array_equal(a, b)
    # The sample mean of 25 standard normals has sd 0.2.
    assert abs(a.std(ddof=1) - 0.2) < 0.03


def test_coverage_of_the_t_interval_is_the_nominal_95_percent():
    r = sim.coverage_probability(
        normal_sampler, t_interval, truth=0.0, n=12, n_reps=4000, seed=1
    )
    assert r.n_reps == 4000
    lo, hi = r.ci95()
    assert lo <= 0.95 <= hi, f"nominal 95% fell outside the Monte-Carlo CI {(lo, hi)}"


def test_coverage_detects_a_broken_interval():
    r = sim.coverage_probability(
        normal_sampler, broken_interval, truth=0.0, n=12, n_reps=4000, seed=1
    )
    # Dividing by n instead of sqrt(n) makes the interval far too narrow.
    assert r.estimate < 0.6


def test_rejection_rate_under_the_null_is_alpha():
    r = sim.rejection_rate(
        normal_sampler, t_test_pvalue, alpha=0.05, n=20, n_reps=4000, seed=2
    )
    lo, hi = r.ci95()
    assert lo <= 0.05 <= hi, f"nominal alpha fell outside the Monte-Carlo CI {(lo, hi)}"


def test_rejection_rate_rises_with_a_real_effect():
    def shifted(n, rng):
        return rng.normal(0.8, 1.0, n)

    r = sim.rejection_rate(shifted, t_test_pvalue, alpha=0.05, n=20, n_reps=2000, seed=3)
    # Power at n=20, effect 0.8 sd is well above alpha.
    assert r.estimate > 0.8


def test_rejection_rate_rejects_bad_alpha():
    with pytest.raises(ValueError, match="alpha"):
        sim.rejection_rate(normal_sampler, t_test_pvalue, alpha=1.5, n=10, n_reps=10)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_simulation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.simulation'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/simulation.py`:

```python
"""The Monte-Carlo harness behind the book's second principle:
every claim is checked by simulation.

A confidence interval that claims 95% coverage, a test that claims a 5%
type-I error rate -- both are statements about long-run frequencies, and
both are measured here rather than asserted. The three entry points share
one shape: draw many samples from a known truth, apply the procedure, and
report the proportion with a Monte-Carlo standard error attached, so the
reader can tell a real discrepancy from simulation noise.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

__all__ = [
    "MonteCarloResult",
    "Sampler",
    "coverage_probability",
    "rejection_rate",
    "sampling_distribution",
]

# A sampler owns no randomness of its own: it receives the harness's Generator
# so a single seed reproduces the whole experiment.
Sampler = Callable[[int, np.random.Generator], np.ndarray]


@dataclass(frozen=True)
class MonteCarloResult:
    """A simulated proportion with its Monte-Carlo standard error."""

    estimate: float
    se: float
    n_reps: int

    def ci95(self) -> tuple[float, float]:
        """The 95% Monte-Carlo interval for the estimated proportion.

        This is the uncertainty in *our simulation*, not in the procedure
        being studied. Widening it means running more repetitions.
        """
        half = 1.96 * self.se
        return self.estimate - half, self.estimate + half


def _proportion_result(hits: np.ndarray, n_reps: int) -> MonteCarloResult:
    p = float(np.mean(hits))
    return MonteCarloResult(
        estimate=p, se=math.sqrt(max(p * (1.0 - p), 0.0) / n_reps), n_reps=n_reps
    )


def sampling_distribution(
    statistic: Callable[[np.ndarray], float],
    sampler: Sampler,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> np.ndarray:
    """``n_reps`` draws of ``statistic`` computed on fresh samples of size ``n``."""
    rng = np.random.default_rng(seed)
    return np.array([float(statistic(sampler(n, rng))) for _ in range(n_reps)])


def coverage_probability(
    sampler: Sampler,
    interval_fn: Callable[[np.ndarray], tuple[float, float]],
    truth: float,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> MonteCarloResult:
    """The proportion of intervals that actually contain ``truth``.

    A 95% interval whose measured coverage is 0.72 is not a 95% interval,
    however confidently it was derived.
    """
    rng = np.random.default_rng(seed)
    hits = np.empty(n_reps, dtype=bool)
    for i in range(n_reps):
        lo, hi = interval_fn(sampler(n, rng))
        hits[i] = lo <= truth <= hi
    return _proportion_result(hits, n_reps)


def rejection_rate(
    sampler: Sampler,
    pvalue_fn: Callable[[np.ndarray], float],
    alpha: float,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> MonteCarloResult:
    """The proportion of samples on which the test rejects at level ``alpha``.

    Under a null-generating sampler this measures the type-I error rate;
    under an alternative it measures power. Same function, same code path --
    which is the point NB08 makes about what a test actually is.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly inside (0, 1); got {alpha}")
    rng = np.random.default_rng(seed)
    rejects = np.empty(n_reps, dtype=bool)
    for i in range(n_reps):
        rejects[i] = pvalue_fn(sampler(n, rng)) < alpha
    return _proportion_result(rejects, n_reps)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_simulation.py -q`
Expected: PASS 7 件

> `test_coverage_of_the_t_interval_is_the_nominal_95_percent` は 4000 反復で MC 標準誤差が約 0.0034、95% 区間の幅が約 ±0.0067。真の被覆は正確に 0.95 なので通るはずだが、**seed によっては境界に来る**。落ちた場合は seed を変えるのではなく `n_reps` を 10000 に上げること（主張の方が正しく、精度が足りないだけ）。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/simulation.py analytics/statistics/tests/test_simulation.py
git commit -m "feat(statistics): the Monte-Carlo harness

Coverage and rejection rate share one shape: draw from a known truth,
apply the procedure, report the proportion with a Monte-Carlo standard
error attached. The error bar matters -- without it a reader cannot tell
a broken interval from simulation noise, which is exactly the confusion
NB07 is trying to remove.

Samplers take the harness's Generator rather than owning a seed, so one
seed reproduces an entire experiment. Tests pin both directions: the t
interval covers at its nominal rate, and an interval that divides by n
instead of sqrt(n) is caught at 0.6."
```

---

### Task 6: `plotting/` — 確率論の図

**Files:**
- Create: `analytics/statistics/src/stats_textbook/plotting/__init__.py`
- Create: `analytics/statistics/src/stats_textbook/plotting/core.py`
- Create: `analytics/statistics/src/stats_textbook/plotting/probability.py`
- Test: `analytics/statistics/tests/test_plotting.py`

**Interfaces:**
- Consumes: `distributions.RELATIONS` / `relation_layout()` / `binomial_poisson_tv_distance`、`processes.MarkovChain`、`datasets.SAMPLERS`、`simulation.sampling_distribution`
- Produces（全て `plotly.graph_objects.Figure` を返す純関数。`plotting/__init__.py` が全て再エクスポート）:
  - `core.frame_slider(frames: list[go.Frame], slider_name: str) -> Figure` — **全アニメーション図の共通入口**。呼び出し側はフレームだけ作る
  - `core.curve_slider(x, frames, slider_name="step", title=None, yaxis_title=None) -> Figure` — `frames: list[tuple[str, list[tuple[str, Sequence[float], str | None]]]]`。線グラフ用の薄いラッパで、Plan 2 の尤度曲線・検出力曲線が使う
  - `core.apply_defaults(fig, title=None, xaxis_title=None, yaxis_title=None) -> Figure`
  - `probability.ppv_slider(prevalences, sensitivity, specificity) -> Figure`
  - `probability.joint_marginal_heatmap(x, y, bins=30) -> Figure`
  - `probability.poisson_limit_slider(n_values, lam, k_max=15) -> Figure`
  - `probability.relation_graph() -> Figure`
  - `probability.clt_convergence(sampler_names, ns, n_reps=2000, seed=0) -> Figure`
  - `probability.random_walk_paths(paths, n_show=30) -> Figure`
  - `probability.markov_convergence_slider(chain, p0, n_steps=30) -> Figure`

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_plotting.py`:

```python
"""Plotly figure helpers: structure only -- rendering is client-side."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import datasets, plotting
from stats_textbook.processes import MarkovChain

TWO_STATE = np.array([[0.9, 0.1], [0.2, 0.8]])


def test_frame_slider_wires_one_step_per_frame():
    frames = [go.Frame(data=[go.Bar(x=["a"], y=[i])], name=str(i)) for i in range(4)]
    fig = plotting.frame_slider(frames, "n")
    assert len(fig.frames) == 4
    labels = [s["label"] for s in fig.layout.sliders[0].steps]
    assert labels == ["0", "1", "2", "3"]
    assert fig.layout.sliders[0].currentvalue.prefix == "n = "


def test_every_animated_figure_goes_through_frame_slider():
    """No figure may hand-roll its slider -- the wiring lives in one place."""
    import inspect

    from stats_textbook.plotting import probability

    src = inspect.getsource(probability)
    assert '"method": "animate"' not in src, "build frames and call frame_slider instead"


def test_curve_slider_builds_one_frame_per_step():
    x = np.linspace(0, 1, 20)
    frames = [("a", [("y", x**1, None)]), ("b", [("y", x**2, "dash"), ("z", x, None)])]
    fig = plotting.curve_slider(x, frames, slider_name="n")
    assert isinstance(fig, go.Figure)
    assert len(fig.frames) == 2
    assert len(fig.layout.sliders[0].steps) == 2
    assert len(fig.frames[1].data) == 2


def test_ppv_slider_shows_ppv_collapsing_at_low_prevalence():
    fig = plotting.ppv_slider([0.001, 0.01, 0.1, 0.5], sensitivity=0.99, specificity=0.95)
    assert len(fig.frames) == 4
    # The headline number must be legible from the figure's own data.
    assert fig.layout.yaxis.title.text is not None


def test_joint_marginal_heatmap_has_a_heatmap_and_two_margins():
    x, y = datasets.bivariate_normal(2000, rho=0.7, seed=0)
    fig = plotting.joint_marginal_heatmap(x, y, bins=20)
    kinds = [tr.type for tr in fig.data]
    assert "heatmap" in kinds
    assert kinds.count("bar") == 2, "one marginal per axis"


def test_poisson_limit_slider_frames_match_the_n_values():
    fig = plotting.poisson_limit_slider([5, 20, 100], lam=2.0, k_max=12)
    assert len(fig.frames) == 3
    # Binomial pmf and the Poisson limit are drawn together in every frame.
    assert len(fig.frames[0].data) == 2


def test_relation_graph_draws_every_edge_and_labels_every_node():
    fig = plotting.relation_graph()
    from stats_textbook import distributions as dist

    node_trace = [tr for tr in fig.data if tr.mode and "text" in tr.mode]
    assert node_trace, "nodes must carry text labels"
    assert len(node_trace[0].text) == len(dist.relation_layout())


def test_clt_convergence_has_one_frame_per_sample_size():
    fig = plotting.clt_convergence(["normal", "exponential", "cauchy"], ns=[1, 5, 30], n_reps=400)
    assert len(fig.frames) == 3
    # One histogram per sampler in each frame.
    assert len(fig.frames[0].data) == 3


def test_clt_convergence_is_deterministic():
    a = plotting.clt_convergence(["exponential"], ns=[2, 8], n_reps=300, seed=11)
    b = plotting.clt_convergence(["exponential"], ns=[2, 8], n_reps=300, seed=11)
    np.testing.assert_array_equal(a.frames[-1].data[0].x, b.frames[-1].data[0].x)


def test_random_walk_paths_caps_the_number_drawn():
    from stats_textbook.processes import random_walk

    paths = random_walk(100, n_paths=200, seed=0)
    fig = plotting.random_walk_paths(paths, n_show=12)
    assert len(fig.data) <= 13, "12 paths plus at most one envelope trace"


def test_markov_convergence_slider_ends_at_the_stationary_law():
    chain = MarkovChain(TWO_STATE)
    fig = plotting.markov_convergence_slider(chain, p0=np.array([1.0, 0.0]), n_steps=40)
    assert len(fig.frames) == 41
    final = np.asarray(fig.frames[-1].data[0].y, dtype=float)
    np.testing.assert_allclose(final, chain.stationary(), atol=1e-6)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.plotting'`

- [ ] **Step 3: `core.py` を実装する**

`analytics/statistics/src/stats_textbook/plotting/core.py`:

```python
"""Shared Plotly scaffolding.

Every figure in this book must animate inside a *static* HTML page, so the
frames and slider steps are baked into the figure object rather than driven
by a live kernel. ipywidgets is a convenience layer on top (see ``widgets``),
never a requirement.
"""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go

__all__ = ["apply_defaults", "curve_slider", "frame_slider"]

Curve = tuple[str, Sequence[float], str | None]
Frame = tuple[str, list[Curve]]


def apply_defaults(
    fig: go.Figure,
    title: str | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """One house style for size, margins, and axis titles."""
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        width=760,
        height=460,
        margin={"l": 60, "r": 30, "t": 60 if title else 30, "b": 50},
        template="plotly_white",
    )
    return fig


def frame_slider(frames: list[go.Frame], slider_name: str) -> go.Figure:
    """Assemble pre-built frames into a figure with a slider over them.

    Every animated figure in the book funnels through here so the slider
    wiring exists once. Callers build the frames -- what varies between
    figures is the marks, not the animation machinery.
    """
    fig = go.Figure(data=frames[0].data, frames=frames)
    fig.update_layout(
        sliders=[
            {
                "steps": [
                    {
                        "args": [
                            [f.name],
                            {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
                        ],
                        "label": f.name,
                        "method": "animate",
                    }
                    for f in frames
                ],
                "currentvalue": {"prefix": f"{slider_name} = "},
            }
        ]
    )
    return fig


def _traces(x: Sequence[float], curves: list[Curve]) -> list[go.Scatter]:
    return [
        go.Scatter(
            x=list(x),
            y=list(y),
            mode="lines",
            name=name,
            line={"dash": dash} if dash else None,
        )
        for name, y, dash in curves
    ]


def curve_slider(
    x: Sequence[float],
    frames: list[Frame],
    slider_name: str = "step",
    title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """A line plot with a slider stepping through ``frames``.

    ``frames`` is a list of ``(label, curves)``; each ``curves`` entry is
    ``(name, y, dash_or_None)`` over the shared ``x`` grid.

    Part I's figures are bars and histograms and so build their frames
    directly; this line-oriented wrapper is what Plan 2's likelihood and
    power curves use.
    """
    built = [go.Frame(data=_traces(x, curves), name=str(lab)) for lab, curves in frames]
    return apply_defaults(
        frame_slider(built, slider_name), title=title, yaxis_title=yaxis_title
    )
```

- [ ] **Step 4: `probability.py` を実装する**

`analytics/statistics/src/stats_textbook/plotting/probability.py`:

```python
"""Figures for Part I (chapters 01-05).

Each function is a pure map from data to a ``go.Figure``: no globals, no
file writes, no randomness except through an explicit seed. That is what
makes them testable and what keeps the computation in the computation
modules where it belongs.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go
from scipy import stats

from .. import datasets, distributions, simulation
from ..processes import MarkovChain
from .core import apply_defaults, frame_slider

__all__ = [
    "clt_convergence",
    "joint_marginal_heatmap",
    "markov_convergence_slider",
    "poisson_limit_slider",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
]


def ppv_slider(
    prevalences: Sequence[float], sensitivity: float, specificity: float
) -> go.Figure:
    """Positive predictive value as prevalence varies (NB01's headline).

    An accurate test is still mostly wrong when the disease is rare -- the
    figure makes the collapse visible rather than arguing for it.
    """
    labels = ["真陽性", "偽陽性"]
    frames = []
    for prev in prevalences:
        tp = prev * sensitivity
        fp = (1.0 - prev) * (1.0 - specificity)
        ppv = tp / (tp + fp)
        frames.append(
            go.Frame(
                data=[go.Bar(x=labels, y=[tp, fp], text=[f"PPV = {ppv:.1%}", ""])],
                name=f"{prev:.3f}",
            )
        )
    return apply_defaults(
        frame_slider(frames, "有病率"),
        title="陽性者の内訳 — 有病率が下がると偽陽性が真陽性を飲み込む",
        yaxis_title="母集団に占める割合",
    )


def joint_marginal_heatmap(x: np.ndarray, y: np.ndarray, bins: int = 30) -> go.Figure:
    """A joint density with both marginals -- NB02's picture of marginalisation."""
    counts, xedges, yedges = np.histogram2d(x, y, bins=bins, density=True)
    xc = 0.5 * (xedges[:-1] + xedges[1:])
    yc = 0.5 * (yedges[:-1] + yedges[1:])
    fig = go.Figure(
        data=[
            go.Heatmap(z=counts.T, x=xc, y=yc, colorscale="Blues", showscale=False),
            go.Bar(x=xc, y=counts.sum(axis=1), name="x の周辺分布", yaxis="y2", opacity=0.5),
            go.Bar(x=yc, y=counts.sum(axis=0), name="y の周辺分布", xaxis="x2", opacity=0.5),
        ]
    )
    fig.update_layout(
        xaxis={"domain": [0.0, 0.78]},
        yaxis={"domain": [0.0, 0.78]},
        xaxis2={"domain": [0.82, 1.0]},
        yaxis2={"domain": [0.82, 1.0]},
    )
    return apply_defaults(fig, title="同時分布と 2 つの周辺分布", xaxis_title="x", yaxis_title="y")


def poisson_limit_slider(
    n_values: Sequence[int], lam: float, k_max: int = 15
) -> go.Figure:
    """Binomial(n, lam/n) closing on Poisson(lam) as n grows (NB03)."""
    k = np.arange(0, k_max + 1)
    pois = stats.poisson.pmf(k, lam)
    frames = []
    for n in n_values:
        p = lam / n
        tv = distributions.binomial_poisson_tv_distance(int(n), float(p))
        frames.append(
            go.Frame(
                data=[
                    go.Bar(x=k, y=stats.binom.pmf(k, n, p), name=f"Binomial(n={n}, p={p:.4f})"),
                    go.Scatter(
                        x=k,
                        y=pois,
                        mode="lines+markers",
                        name=f"Poisson({lam}) — TV 距離 {tv:.4f}",
                    ),
                ],
                name=str(n),
            )
        )
    return apply_defaults(
        frame_slider(frames, "n"), title="ポアソン極限", xaxis_title="k", yaxis_title="確率"
    )


def relation_graph() -> go.Figure:
    """The map of Part I: which distribution turns into which, and when."""
    layout = distributions.relation_layout()
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    label_x, label_y, label_text = [], [], []
    for rel in distributions.RELATIONS:
        x0, y0 = layout[rel.source]
        x1, y1 = layout[rel.target]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        label_x.append(0.5 * (x0 + x1))
        label_y.append(0.5 * (y0 + y1))
        label_text.append(rel.condition)
    names = list(layout)
    fig = go.Figure(
        data=[
            go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"color": "#bbb"}, hoverinfo="skip"),
            go.Scatter(
                x=label_x,
                y=label_y,
                mode="markers",
                marker={"size": 6, "color": "#bbb"},
                text=label_text,
                hoverinfo="text",
                showlegend=False,
            ),
            go.Scatter(
                x=[layout[n][0] for n in names],
                y=[layout[n][1] for n in names],
                mode="markers+text",
                text=names,
                textposition="top center",
                marker={"size": 22, "color": "#4C78A8"},
                showlegend=False,
            ),
        ]
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_defaults(fig, title="分布の関係図 — 辺にカーソルを乗せると条件が出る")


def clt_convergence(
    sampler_names: Sequence[str], ns: Sequence[int], n_reps: int = 2000, seed: int = 0
) -> go.Figure:
    """The book's flagship figure: sample means going normal -- except Cauchy.

    Each frame is one sample size; each trace is one underlying law. The
    Cauchy histogram never narrows, which is the whole argument for why the
    CLT needs a finite variance.
    """
    frames = []
    for n in ns:
        traces = []
        for name in sampler_names:
            sampler = datasets.SAMPLERS[name]
            means = simulation.sampling_distribution(np.mean, sampler, n=int(n), n_reps=n_reps, seed=seed)
            # Standardise by the CLT's own prediction so a match is a match at
            # every n. Cauchy has no sd to standardise by -- it stays wide.
            traces.append(
                go.Histogram(
                    x=means * np.sqrt(n),
                    name=name,
                    opacity=0.55,
                    nbinsx=60,
                    histnorm="probability density",
                )
            )
        frames.append(go.Frame(data=traces, name=str(n)))
    fig = frame_slider(frames, "n")
    fig.update_layout(barmode="overlay", xaxis_range=[-5, 5])
    return apply_defaults(
        fig,
        title="標本平均の分布 — sqrt(n) で標準化したもの",
        xaxis_title="sqrt(n) * 標本平均",
        yaxis_title="密度",
    )


def random_walk_paths(paths: np.ndarray, n_show: int = 30) -> go.Figure:
    """Sample paths with a sqrt(t) envelope (NB05)."""
    paths = np.asarray(paths, dtype=float)
    t = np.arange(paths.shape[1])
    fig = go.Figure(
        data=[
            go.Scatter(x=t, y=path, mode="lines", line={"width": 1}, showlegend=False)
            for path in paths[:n_show]
        ]
    )
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([t, t[::-1]]),
            y=np.concatenate([np.sqrt(t), -np.sqrt(t)[::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.15)",
            line={"width": 0},
            name="±sqrt(t)",
        )
    )
    return apply_defaults(fig, title="ランダムウォーク", xaxis_title="ステップ", yaxis_title="位置")


def markov_convergence_slider(
    chain: MarkovChain, p0: np.ndarray, n_steps: int = 30
) -> go.Figure:
    """The chain's law forgetting where it started (NB05)."""
    labels = list(chain.states) if chain.states else [str(i) for i in range(chain.n_states)]
    pi = chain.stationary()
    frames = []
    for n in range(n_steps + 1):
        p = chain.distribution_after(n, p0)
        frames.append(
            go.Frame(
                data=[
                    go.Bar(x=labels, y=p, name="n ステップ後"),
                    go.Scatter(x=labels, y=pi, mode="markers", marker={"size": 12}, name="定常分布"),
                ],
                name=str(n),
            )
        )
    fig = frame_slider(frames, "ステップ数")
    fig.update_layout(yaxis_range=[0, 1])
    return apply_defaults(fig, title="マルコフ連鎖の分布が定常分布に落ち着く", yaxis_title="確率")
```

`analytics/statistics/src/stats_textbook/plotting/__init__.py`:

```python
"""Plotly figure helpers, grouped by the chapters they serve.

``probability`` covers Part I (01-05). ``inference`` and ``regression``
arrive with Plan 2. Consumers import from this package, not the submodules,
so the split stays an implementation detail.
"""

from .core import apply_defaults, curve_slider, frame_slider
from .probability import (
    clt_convergence,
    joint_marginal_heatmap,
    markov_convergence_slider,
    poisson_limit_slider,
    ppv_slider,
    random_walk_paths,
    relation_graph,
)

__all__ = [
    "apply_defaults",
    "clt_convergence",
    "curve_slider",
    "frame_slider",
    "joint_marginal_heatmap",
    "markov_convergence_slider",
    "poisson_limit_slider",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
]
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting.py -q`
Expected: PASS 11 件

> `test_random_walk_paths_caps_the_number_drawn` は「12 本＋包絡線 1 本 = 13」を上限に見る。実装は `n_show` 本の Scatter に包絡線 1 本を足すので 13 本ちょうど。

- [ ] **Step 6: 図が本当にインタラクティブに出力されるか目視確認する**

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
from stats_textbook import plotting
fig = plotting.clt_convergence(["normal", "exponential", "cauchy"], ns=[1, 2, 5, 30], n_reps=1500)
fig.write_html("/tmp/clt_check.html", include_plotlyjs="cdn")
print("frames:", len(fig.frames), "slider steps:", len(fig.layout.sliders[0].steps))
PY
```

Expected: `frames: 4 slider steps: 4`。`/tmp/clt_check.html` をブラウザで開き、**スライダーを動かすと normal と exponential のヒストグラムが正規形に寄り、cauchy だけが寄らない**ことを確認する。これが本書の看板図なので、ここは必ず目で見ること。

- [ ] **Step 7: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/plotting analytics/statistics/tests/test_plotting.py
git commit -m "feat(statistics): Plotly figures for Part I

Frames and slider steps are baked into the figure object so every figure
animates inside a static HTML page with no live kernel -- ipywidgets is
a convenience layer, never a requirement.

clt_convergence standardises the sample means by sqrt(n), the CLT's own
prediction, so a match reads as a match at every sample size and the
Cauchy histogram's refusal to narrow is unmistakable. That contrast is
the chapter's argument for why finite variance is a hypothesis and not
a technicality."
```

---

### Task 7: `widgets.py` — ライブカーネル用の補助

**Files:**
- Create: `analytics/statistics/src/stats_textbook/widgets.py`
- Test: `analytics/statistics/tests/test_widgets.py`

**Interfaces:**
- Consumes: `plotting.ppv_slider` / `plotting.clt_convergence` / `plotting.markov_convergence_slider`
- Produces:
  - `ppv_widget(sensitivity: float = 0.99, specificity: float = 0.95)` → `ipywidgets.VBox`
  - `clt_widget(sampler_names: Sequence[str] = ("normal", "exponential", "cauchy"))` → `ipywidgets.VBox`
  - `markov_widget(P: np.ndarray)` → `ipywidgets.VBox`

> `widgets` は **`plotting` の薄いラッパに徹する。** 図の中身を再実装してはいけない（同じ図が 2 箇所にあると必ず食い違う）。各 widget はスライダーの値を受けて対応する `plotting` 関数を呼び直すだけ。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_widgets.py`:

```python
"""ipywidgets wrappers: they construct, and they delegate to plotting."""

import numpy as np
from stats_textbook import widgets


def test_ppv_widget_constructs_with_a_slider_and_a_figure():
    box = widgets.ppv_widget()
    kinds = [type(child).__name__ for child in box.children]
    assert any("Slider" in k for k in kinds)
    assert any("FigureWidget" in k or "Output" in k for k in kinds)


def test_clt_widget_constructs():
    box = widgets.clt_widget(sampler_names=("normal", "cauchy"))
    assert len(box.children) >= 2


def test_markov_widget_constructs():
    box = widgets.markov_widget(np.array([[0.9, 0.1], [0.2, 0.8]]))
    assert len(box.children) >= 2


def test_widgets_do_not_reimplement_figures():
    """Every widget must go through ``plotting`` -- no private figure code."""
    import inspect

    src = inspect.getsource(widgets)
    assert "go.Figure(" not in src, "widgets must delegate to plotting, not build figures"
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_widgets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.widgets'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/widgets.py`:

```python
"""ipywidgets wrappers for readers running a live kernel.

Strictly a convenience layer: every widget re-calls the corresponding
``plotting`` function and swaps the figure in. The book must read the same
without a kernel, so nothing here may own figure construction -- duplicated
figures drift apart, and the static HTML would be the one that goes stale.
"""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as ipw
import numpy as np

from . import plotting
from .processes import MarkovChain

__all__ = ["clt_widget", "markov_widget", "ppv_widget"]


def _panel(control: ipw.Widget, render) -> ipw.VBox:
    """Wire ``control`` to an output area redrawn by ``render(value)``."""
    out = ipw.Output()

    def _redraw(change) -> None:
        out.clear_output(wait=True)
        with out:
            render(change["new"]).show()

    control.observe(_redraw, names="value")
    with out:
        render(control.value).show()
    return ipw.VBox([control, out])


def ppv_widget(sensitivity: float = 0.99, specificity: float = 0.95) -> ipw.VBox:
    """Drag prevalence and watch the positive predictive value collapse."""
    slider = ipw.FloatLogSlider(
        value=0.01, base=10, min=-4, max=-0.3, step=0.1, description="有病率"
    )
    return _panel(slider, lambda prev: plotting.ppv_slider([prev], sensitivity, specificity))


def clt_widget(
    sampler_names: Sequence[str] = ("normal", "exponential", "cauchy"),
) -> ipw.VBox:
    """Drag the sample size through the central limit theorem."""
    slider = ipw.IntSlider(value=5, min=1, max=200, step=1, description="n")
    return _panel(
        slider, lambda n: plotting.clt_convergence(list(sampler_names), ns=[n], n_reps=1500)
    )


def markov_widget(P: np.ndarray) -> ipw.VBox:
    """Drag the step count and watch the chain forget its start."""
    chain = MarkovChain(np.asarray(P, dtype=float))
    p0 = np.zeros(chain.n_states)
    p0[0] = 1.0
    slider = ipw.IntSlider(value=0, min=0, max=60, step=1, description="ステップ")
    return _panel(slider, lambda n: plotting.markov_convergence_slider(chain, p0, n_steps=max(n, 1)))
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_widgets.py -q`
Expected: PASS 4 件

> `test_ppv_widget_constructs_with_a_slider_and_a_figure` は `VBox` の直下に `Slider` と `Output` があることを見る。`_panel` はまさにその 2 つを返すので通る。

- [ ] **Step 5: M1 の全テストを走らせる**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q`
Expected: PASS 52 件（smoke 1・nbkit 3・datasets 8・distributions 8・processes 10・simulation 7・plotting 11・widgets 4 = 52）。**設計書の M1 目標「~20 本」を上回るが、これは `plotting` と `widgets` が M1 に含まれるため。**実測値を次の commit メッセージに記録すること。

- [ ] **Step 6: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/widgets.py analytics/statistics/tests/test_widgets.py
git commit -m "feat(statistics): ipywidgets wrappers, and a test that they stay thin

Each widget re-calls a plotting function and swaps the figure in. A test
greps the module for go.Figure( and fails if it appears: the moment a
widget builds its own figure, the live version and the static HTML start
drifting, and the static one is what most readers see.

M1 complete -- 52 tests green."
```

---

## M2 — 第Ⅰ部のノートブック（Task 8–13）の共通ルール

以下は Task 8–13 の**すべて**に適用される。各タスクで繰り返さない。

**セル構成**: 各 `build_nbNN.py` は `from nbkit import code, md` して `cells: list` を定義するだけ。`nbkit.build` が import preamble を先頭に付ける。

**各章の標準セットアップセル**（章タイトルの直後に必ず置く）:

```python
code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import datasets, distributions, plotting, processes, simulation

RANDOM_SEED = 0
print("setup ok")
""")
```

**章の節構成**（Global Constraints の再掲ではなく、ここが唯一の詳細指定）:
1. 導入（数式なし。具体的な問い or 誤解から）
2. 直感と図（`plotting` の関数を呼ぶ）
3. 定式化（最小限の数式。定義と主張を分ける）
4. 実装（`stats_textbook` を呼ぶ。ロジックをノートに書かない）
5. 実験（`simulation` で主張を検算する）
6. 落とし穴
7. 演習 3–5 問（解答は Plan 3 の 13 章。**この時点では問題だけ書く**）

**コールアウトの書式**（約物に接する太字を書かないこと。`nbkit.md` が弾く）:

````
```{admonition} 核心 — ひとことで
:class: tip
（1–3 行）
```
````

````
```{admonition} 実社会では
:class: note
（1–3 行）
```
````

**各タスクの検証手順**（毎回同じ）:

```bash
cd analytics/statistics
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py --check   # 生成が通るか
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py           # 本番出力
cd -
time PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python -m jupyter \
  nbconvert --to notebook --execute --inplace analytics/statistics/notebooks/NN_*.ipynb
```

実行時間を計測し、**1 章あたり 20 秒**を超えたら反復数を下げる（第Ⅰ部 6 章で合計 2 分以内が予算）。

`book/_toc.yml` の `chapters:` に当該章を 1 行足し、`tools/build_notebooks.py` の `NOTEBOOKS` に 1 行足す。

---

### Task 8: NB00 — 全体地図

**Files:**
- Modify: `analytics/statistics/tools/build_nb00.py`（Task 1 の front matter を本文に拡張）
- Modify: `analytics/statistics/notebooks/00_overview.ipynb`（生成物）

**Interfaces:**
- Consumes: `plotting.relation_graph`
- Produces: なし（以降の章はこの章に依存しない）

- [ ] **Step 1: `build_nb00.py` を書き直す**

`cells` を次の順で構成する。

1. `md` — Task 1 の front matter（書名・3 原則）をそのまま残す
2. `md` — **「なぜ同じデータから 2 人が違う結論を出すのか」**。硬貨を 10 回投げて 8 回表が出たとき、「偏っている」と言う人と「まだ何も言えない」と言う人が両方正しくありうる、という導入。数式なし、3–5 段落
3. 標準セットアップセル
4. `code` — その導入を数値で見せる:

```python
code("""
flips = datasets.coin_flips(10, p=0.5, seed=4)
print("観測:", flips, "-> 表", flips.sum(), "回")

# 公正な硬貨でも 8 回以上表が出ることは珍しくない。
reps = simulation.sampling_distribution(
    np.sum, lambda n, rng: (rng.random(n) < 0.5).astype(int), n=10, n_reps=20_000, seed=0
)
print(f"公正な硬貨で 8 回以上表: {(reps >= 8).mean():.3f}")
""")
```

5. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
データが「珍しい」かどうかは、データだけでは決まらない。
何と比べて珍しいのか、という基準をこちらが持ち込んで初めて決まる。
本書の第Ⅰ部はその基準を作る道具、第Ⅱ部はそれを使って判断する方法である。
```
````

6. `md` — 本書の地図。第Ⅰ部（01–05）と第Ⅱ部（06–11）の章一覧を表で示し、各章が何を与え何に依存するかを 1 行ずつ書く
7. `code` — 分布の関係図で「第Ⅰ部で作る地図」を先に見せる:

```python
code("""
plotting.relation_graph()
""")
```

8. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
医療の承認、A/B テストの採否、工場の出荷判定 — いずれも
「観測された差が偶然の範囲か」を決める手続きに支えられている。
その手続きが何を保証し、何を保証しないのかを読めるようになるのが本書の目的である。
```
````

9. `md` — 読み方（章の標準構成・記号の約束・実行環境）

- [ ] **Step 2: 生成して実行し、時間を測る**

上の「各タスクの検証手順」を `00_overview.ipynb` に対して実行する。
Expected: 実行 5 秒以内。`(reps >= 8).mean()` は 0.05–0.06 程度。

- [ ] **Step 3: 本がビルドできることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
Expected: `Finished generating HTML for book.`

`_build/html/index.html` をブラウザで開き、**関係図が表示されカーソルで辺の条件が出る**ことを目視確認する。

- [ ] **Step 4: commit**

```bash
git add analytics/statistics/tools/build_nb00.py analytics/statistics/notebooks/00_overview.ipynb
git commit -m "docs(statistics): NB00 overview

Opens on the question the whole book answers: why two people can read the
same 8-heads-in-10 and disagree without either being wrong. The answer --
that 'surprising' needs a reference distribution we supply -- is measured
in the first code cell rather than asserted."
```

---

### Task 9: NB01 — 確率の土台

**Files:**
- Create: `analytics/statistics/tools/build_nb01.py`
- Create: `analytics/statistics/notebooks/01_probability_foundations.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`（`NOTEBOOKS` に 1 行）
- Modify: `analytics/statistics/book/_toc.yml`（`chapters` に 1 行）

**Interfaces:**
- Consumes: `datasets.disease_test_counts`、`datasets.coin_flips`、`plotting.ppv_slider`、`simulation.sampling_distribution`
- Produces: なし

- [ ] **Step 1: `build_nb01.py` を書く**

`cells`:

1. `md` — タイトル `# 01. 確率の土台 — 条件付き確率が直感を裏切るとき` ＋ 「この章で分かること」箇条書き 5 点（標本空間と事象／独立の定義は直感より狭いこと／条件付き確率と乗法定理／ベイズの定理を計算道具として／検査の偽陽性パラドクス）
2. 標準セットアップセル
3. `md` — §1 標本空間・事象・確率の公理（コルモゴロフの 3 公理。定義と主張を分けて最小限に）
4. `md` — §2 条件付き確率と独立。$P(A \mid B) = P(A \cap B)/P(B)$。独立は「$P(A \mid B) = P(A)$」であって「無関係に見える」ではない
5. `code` — 独立でない例を数値で:

```python
code("""
# 2 つのサイコロの和。「和が偶数」と「1 個目が偶数」は独立か。
rng = np.random.default_rng(RANDOM_SEED)
d1, d2 = rng.integers(1, 7, 100_000), rng.integers(1, 7, 100_000)
even_sum, even_first = (d1 + d2) % 2 == 0, d1 % 2 == 0
p_a, p_b = even_sum.mean(), even_first.mean()
p_ab = (even_sum & even_first).mean()
print(f"P(A) = {p_a:.4f}  P(B) = {p_b:.4f}  P(A and B) = {p_ab:.4f}")
print(f"P(A) * P(B) = {p_a * p_b:.4f}  -> 独立" if abs(p_ab - p_a * p_b) < 0.01 else "-> 従属")
""")
```

6. `md` — §3 モンティ・ホール。図なしで乗法定理から導く
7. `code` — モンティ・ホールをシミュレーションで:

```python
code("""
def monty_hall(n_games, switch, seed=0):
    rng = np.random.default_rng(seed)
    car = rng.integers(0, 3, n_games)
    pick = rng.integers(0, 3, n_games)
    # 司会は「選ばれておらず車でもない」扉を開ける。switch なら残りの扉へ。
    return float(np.mean(car != pick)) if switch else float(np.mean(car == pick))

print(f"変えない: {monty_hall(100_000, switch=False):.4f}  (理論 1/3 = {1/3:.4f})")
print(f"変える  : {monty_hall(100_000, switch=True):.4f}  (理論 2/3 = {2/3:.4f})")
""")
```

8. `md` — §4 ベイズの定理。$P(H \mid D) = P(D \mid H)P(H)/P(D)$ を**計算道具として**導入し、11 章の流儀論とは切り離すことを明言する
9. `md` — §5 検査の偽陽性パラドクス。感度 99%・特異度 95%・有病率 0.1% の設定を提示
10. `code` — 数を数えて見せる:

```python
code("""
counts = datasets.disease_test_counts(
    1_000_000, prevalence=0.001, sensitivity=0.99, specificity=0.95, seed=RANDOM_SEED
)
ppv = counts["tp"] / (counts["tp"] + counts["fp"])
print(counts)
print(f"陽性のうち本当に病気なのは {ppv:.2%}")
""")
```

11. `code` — 有病率スライダー（この章の看板図）:

```python
code("""
plotting.ppv_slider([0.0005, 0.001, 0.005, 0.02, 0.1, 0.5], sensitivity=0.99, specificity=0.95)
""")
```

12. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
検査の性能（感度・特異度）だけでは、陽性者が病気である確率は決まらない。
有病率という事前の情報が必ず要る。
稀な病気では、優秀な検査でも陽性者の大半が健康な人になる。
```
````

13. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
空港のセキュリティ、クレジットカードの不正検知、迷惑メールのフィルタ。
いずれも探している対象が稀なので、同じ算術に支配される。
誤検知を減らす努力は、精度を上げる努力と同じくらい重要になる。
```
````

14. `md` — §6 落とし穴（$P(A \mid B)$ と $P(B \mid A)$ の取り違え＝検察官の誤謬／「独立」を仮定で置く危険）
15. `md` — §7 演習 4 問（(1) 3 枚のカード問題 (2) 感度と特異度のどちらを上げるべきか有病率別に (3) 2 回続けて陽性なら PPV はどうなるか (4) 独立の定義を使って「無相関だが従属」な例を作る）

- [ ] **Step 2: `NOTEBOOKS` と `_toc.yml` に登録する**

`tools/build_notebooks.py` の `NOTEBOOKS` に追加:

```python
    ("build_nb01", "01_probability_foundations"),
```

`book/_toc.yml`:

```yaml
format: jb-book
root: notebooks/00_overview
chapters:
  - file: notebooks/01_probability_foundations
```

- [ ] **Step 3: 生成・実行・時間計測**

共通の検証手順を実行する。
Expected: 実行 10 秒以内。PPV は 1.9% 前後（感度 0.99・特異度 0.95・有病率 0.001 の理論値 1.94%）。モンティ・ホールは 0.333 / 0.667。

- [ ] **Step 4: 本をビルドして目視確認**

Run: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
`_build/html/notebooks/01_probability_foundations.html` を開き、**PPV スライダーが動くこと**と**コールアウトの太字が崩れていないこと**を確認する。

- [ ] **Step 5: commit**

```bash
git add analytics/statistics/tools/build_nb01.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/01_probability_foundations.ipynb
git commit -m "docs(statistics): NB01 foundations of probability

The false-positive paradox is shown by counting a simulated million-person
screening programme before any formula appears, then the prevalence slider
lets the reader watch the positive predictive value collapse. Bayes'
theorem enters here purely as arithmetic -- the question of what it means
to put a prior on a hypothesis is deferred to NB11."
```

---

### Task 10: NB02 — 確率変数と期待値

**Files:**
- Create: `analytics/statistics/tools/build_nb02.py`
- Create: `analytics/statistics/notebooks/02_random_variables_expectation.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `datasets.bivariate_normal`、`datasets.normal_sample`、`plotting.joint_marginal_heatmap`、`simulation.sampling_distribution`
- Produces: なし

- [ ] **Step 1: `build_nb02.py` を書く**

`cells`:

1. `md` — タイトル `# 02. 確率変数と期待値 — 分布を数値に潰す` ＋「この章で分かること」5 点（確率変数は関数であること／期待値の線形性は独立を要らないこと／分散は要ること／変数変換とヤコビアン／条件付き期待値が最良予測子であること）
2. 標準セットアップセル
3. `md` — §1 確率変数は標本空間から実数への関数。離散と連続、pmf と pdf、cdf
4. `md` — §2 期待値と分散。$E[aX + bY] = aE[X] + bE[Y]$ は**独立でなくても成り立つ**が、$\mathrm{Var}(X + Y) = \mathrm{Var}(X) + \mathrm{Var}(Y)$ は共分散が 0 のときだけ
5. `code` — その非対称性を数値で:

```python
code("""
x, y = datasets.bivariate_normal(200_000, rho=0.8, seed=RANDOM_SEED)
print(f"E[x + y]      = {(x + y).mean():+.4f}   E[x] + E[y] = {x.mean() + y.mean():+.4f}")
print(f"Var(x + y)    = {(x + y).var():.4f}")
print(f"Var(x)+Var(y) = {x.var() + y.var():.4f}   (差は 2*Cov = {2 * np.cov(x, y)[0, 1]:.4f})")
""")
```

6. `md` — §3 同時分布と周辺化。周辺分布は同時分布を一方向に潰したもの
7. `code` — 同時分布と周辺分布の図:

```python
code("""
x, y = datasets.bivariate_normal(20_000, rho=0.7, seed=1)
plotting.joint_marginal_heatmap(x, y, bins=40)
""")
```

8. `md` — §4 共分散と相関。相関 0 は独立を意味しない
9. `code` — 無相関だが従属な例:

```python
code("""
rng = np.random.default_rng(2)
u = rng.uniform(-1, 1, 100_000)
v = u**2                       # v は u に完全に決まるのに...
print(f"corr(u, v) = {np.corrcoef(u, v)[0, 1]:+.4f}  -> ほぼ 0")
print(f"E[v | u > 0.9] = {v[u > 0.9].mean():.3f}   E[v] = {v.mean():.3f}  -> 明らかに従属")
""")
```

10. `md` — §5 変数変換。$Y = g(X)$ の密度とヤコビアン。$E[g(X)] \neq g(E[X])$（イェンセン）
11. `code` — イェンセンの不等式を数値で:

```python
code("""
s = datasets.normal_sample(200_000, mu=2.0, sigma=1.0, seed=3)
print(f"E[exp(X)] = {np.exp(s).mean():.4f}   exp(E[X]) = {np.exp(s.mean()):.4f}")
print("凸関数では E[g(X)] >= g(E[X]) （Jensen）")
""")
```

12. `md` — §6 条件付き期待値。$E[Y \mid X]$ が二乗誤差を最小にする予測子であること（証明はスケッチ）
13. `code` — 最良予測子であることを実験で:

```python
code("""
x, y = datasets.bivariate_normal(200_000, rho=0.7, seed=4)
best = 0.7 * x                                  # 二変量正規なら E[y|x] = rho * x
for name, pred in [("E[y|x] = 0.7x", best), ("y の平均", np.zeros_like(y)), ("0.4x", 0.4 * x)]:
    print(f"{name:16s} MSE = {np.mean((y - pred) ** 2):.4f}")
""")
```

14. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
期待値の線形性は無条件に成り立つが、分散の加法性は共分散がゼロのときだけ成り立つ。
この非対称性が、独立性の仮定がどこで効いてくるかを決めている。
```
````

15. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
ポートフォリオの分散投資は、分散の加法性が崩れることを利益に変える操作である。
相関が低い資産を混ぜると合計の分散が個々の和より小さくなる。
2008 年に多くの資産の相関が同時に上がったとき、この前提が壊れた。
```
````

16. `md` — §7 落とし穴（相関 0 と独立の混同／$E[g(X)]$ と $g(E[X])$ の混同／裾の重い分布で標本平均を鵜呑みにする）
17. `md` — §8 演習 4 問（(1) $\mathrm{Var}(X - Y)$ を共分散で書く (2) 対数正規で $E[\exp X]$ を手計算し数値と照合 (3) 相関 0 だが従属な例をもう 1 つ作る (4) $E[Y \mid X]$ が二乗誤差最小であることを示す）

- [ ] **Step 2: 登録・生成・実行・時間計測・本ビルド・目視**

Task 9 の Step 2–4 と同じ手順。`NOTEBOOKS` と `_toc.yml` に `02_random_variables_expectation` を足す。
Expected: 実行 15 秒以内。`corr(u, v)` はほぼ 0、`E[v | u > 0.9]` は 0.9 前後で `E[v]` の 0.33 より明確に大きい。

- [ ] **Step 3: commit**

```bash
git add analytics/statistics/tools/build_nb02.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/02_random_variables_expectation.ipynb
git commit -m "docs(statistics): NB02 random variables and expectation

Built around one asymmetry: expectation is linear unconditionally, variance
is additive only when the covariance vanishes. That is where the
independence assumption earns its keep, and the chapter measures both sides
rather than stating them.

Conditional expectation arrives as the minimiser of squared error, checked
by racing it against two worse predictors."
```

---

### Task 11: NB03 — 分布の動物園

**Files:**
- Create: `analytics/statistics/tools/build_nb03.py`
- Create: `analytics/statistics/notebooks/03_distributions_zoo.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `distributions.RELATIONS` / `EXPONENTIAL_FAMILIES` / `exponential_family_logpdf` / `binomial_poisson_tv_distance`、`plotting.relation_graph` / `poisson_limit_slider`
- Produces: なし

- [ ] **Step 1: `build_nb03.py` を書く**

`cells`:

1. `md` — タイトル `# 03. 分布の動物園 — 覚えるのではなく、つながりを見る` ＋「この章で分かること」5 点（主要分布は独立した暗記項目ではないこと／二項からポアソンと正規への 2 つの極限／t・F・カイ二乗が正規からどう生まれるか／指数型分布族という共通の骨格／十分統計量がデータを要約する意味）
2. 標準セットアップセル
3. `md` — §1 地図を先に見る。「分布を 20 個覚える」のではなく「4–5 個の関係を覚える」
4. `code` — 関係図:

```python
code("""
plotting.relation_graph()
""")
```

5. `md` — §2 二項分布の 2 つの極限。$n \to \infty$ で $p$ を固定すれば正規、$np = \lambda$ を固定すれば ポアソン。**どちらに向かうかは $p$ の振る舞いが決める**
6. `code` — ポアソン極限のスライダー（この章の看板図）:

```python
code("""
plotting.poisson_limit_slider([5, 10, 25, 50, 100, 400], lam=2.0, k_max=12)
""")
```

7. `code` — Le Cam の上界で「近さ」を数値化:

```python
code("""
print(f"{'n':>6} {'p':>10} {'TV 距離':>12} {'上界 n p^2':>12}")
for n in [5, 10, 25, 50, 100, 400]:
    p = 2.0 / n
    print(f"{n:6d} {p:10.4f} {distributions.binomial_poisson_tv_distance(n, p):12.5f} {n * p**2:12.5f}")
""")
```

8. `md` — §3 正規から生まれる 3 つ。$\chi^2$（標準正規の二乗和）、$t$（正規 / $\sqrt{\chi^2/\nu}$）、$F$（$\chi^2$ の比）。**この 3 つは第Ⅱ部の検定で毎回出てくる**ので、ここで由来を押さえる
9. `code` — 定義どおり作って scipy と一致させる:

```python
code("""
from scipy import stats
rng = np.random.default_rng(RANDOM_SEED)
df = 5
z = rng.normal(size=(200_000, df))
chi2_built = (z**2).sum(axis=1)
t_built = rng.normal(size=200_000) / np.sqrt(chi2_built / df)
for name, built, ref in [
    ("chi2", chi2_built, stats.chi2(df)),
    ("t", t_built, stats.t(df)),
]:
    q = [0.05, 0.25, 0.5, 0.75, 0.95]
    print(f"{name}: 実測分位点 {np.quantile(built, q).round(3)}")
    print(f"{name}: 理論分位点 {ref.ppf(q).round(3)}")
""")
```

10. `md` — §4 指数型分布族。$\log p(x \mid \theta) = \eta(\theta) T(x) - A(\eta) + \log h(x)$。4 つの部品の意味を 1 つずつ
11. `code` — 部品を分解して表示し、和が scipy と一致することを確認:

```python
code("""
from scipy import stats
family = distributions.EXPONENTIAL_FAMILIES["poisson"]
x = np.array([0, 1, 2, 5])
eta = family.natural_param(2.5)
print(f"eta(theta) = {eta:.4f}   A(eta) = {family.log_partition(eta):.4f}")
print(f"T(x)       = {family.sufficient_stat(x)}")
print(f"log h(x)   = {family.log_base_measure(x).round(4)}")
print(f"組み立て   = {distributions.exponential_family_logpdf(family, 2.5, x).round(6)}")
print(f"scipy      = {stats.poisson.logpmf(x, 2.5).round(6)}")
""")
```

12. `md` — §5 十分統計量。$T(x)$ が分かればデータの残りは $\theta$ について何も語らない。ポアソンなら和、正規（分散既知）なら和。**06 章の MLE がなぜ $T$ だけの関数になるかの伏線**
13. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
指数型分布族に属する分布は、データを十分統計量 $T(x)$ に潰しても情報が失われない。
だから推定も検定も $T$ の関数として書ける。
分布ごとに別々の理論を作らずに済むのは、この共通の骨格のおかげである。
```
````

14. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
ログ集計で「合計と件数だけ保存し、生ログは捨てる」運用は、
裏で十分統計量の性質に頼っている。
ポアソンや正規を仮定してよい量なら、その 2 つで推定は完全に再現できる。
仮定が崩れる量では、この節約は情報の損失になる。
```
````

15. `md` — §6 落とし穴（正規近似を $p$ が極端なときに使う／$t$ 分布の自由度を取り違える／指数型でない分布（一様分布の端点など）に同じ理屈を持ち込む）
16. `md` — §7 演習 4 問（(1) 幾何分布を指数型の形に書く (2) $n p^2$ の上界がいつ効かなくなるか調べる (3) $F$ 分布を定義どおり作って scipy と照合 (4) 一様分布 $U(0,\theta)$ が指数型でないことを示す）

- [ ] **Step 2: 登録・生成・実行・時間計測・本ビルド・目視**

共通の検証手順。Expected: 実行 20 秒以内（$\chi^2$/$t$ の 200,000 サンプル生成が主）。
`exponential_family_logpdf` の出力が `stats.poisson.logpmf` と小数 6 桁まで一致すること、ポアソン極限スライダーが動くことを目視確認する。

- [ ] **Step 3: commit**

```bash
git add analytics/statistics/tools/build_nb03.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/03_distributions_zoo.ipynb
git commit -m "docs(statistics): NB03 the zoo of distributions

Refuses the memorisation framing: the relation graph comes first, and the
distributions are introduced as its nodes. chi2, t and F are built from
standard normals by hand and matched against scipy's quantiles, so the
machinery of Part II arrives already explained.

The exponential family is printed as its four separate pieces before the
sum is checked against scipy, which is what makes sufficiency legible when
NB06 needs it."
```

---

### Task 12: NB04 — 極限定理

**Files:**
- Create: `analytics/statistics/tools/build_nb04.py`
- Create: `analytics/statistics/notebooks/04_limit_theorems.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `datasets.SAMPLERS` / `heavy_tailed_sample`、`plotting.clt_convergence`、`simulation.sampling_distribution`
- Produces: なし

> **本書の看板章。** 04 章の CLT 対比図は report ポータルのギャラリーにも出す（Plan 3 の M7）。ここの図の品質は他章より高い基準で見ること。

- [ ] **Step 1: `build_nb04.py` を書く**

`cells`:

1. `md` — タイトル `# 04. 極限定理 — なぜ正規分布はどこにでも現れるのか` ＋「この章で分かること」5 点（大数の法則が保証すること／中心極限定理が保証すること／収束の 3 種類の区別／デルタ法／CLT が効かない分布があること）
2. 標準セットアップセル
3. `md` — §1 大数の法則。標本平均が真の平均に近づく。**弱法則と強法則の違いは収束の種類の違い**であることだけ述べ、詳細は §3 へ送る
4. `code` — 走る平均が落ち着く様子:

```python
code("""
rng = np.random.default_rng(RANDOM_SEED)
x = rng.exponential(1.0, 20_000)
running = np.cumsum(x) / np.arange(1, x.size + 1)
for n in [10, 100, 1_000, 10_000, 20_000]:
    print(f"n = {n:6d}: 標本平均 = {running[n - 1]:.4f}  (真値 1.0)")
""")
```

5. `md` — §2 中心極限定理。標本平均の**ゆらぎ**を $\sqrt{n}$ で拡大すると正規分布に収束する。LLN が「どこへ行くか」、CLT が「どうぶれるか」を言う
6. `code` — 看板図:

```python
code("""
plotting.clt_convergence(["normal", "uniform", "exponential", "cauchy"], ns=[1, 2, 5, 15, 50, 200], n_reps=4000)
""")
```

7. `md` — 図の読み方。正規・一様・指数はどれも平均 0・分散 1 に揃えてあるので、**収束の速さの違いは分布の形（歪度）だけによる**。コーシーだけが寄らない
8. `code` — コーシーがなぜ寄らないかを走る平均で:

```python
code("""
c = datasets.heavy_tailed_sample(20_000, kind="cauchy", seed=1)
running_c = np.cumsum(c) / np.arange(1, c.size + 1)
print("コーシーの走る平均（落ち着かない）:")
for n in [10, 100, 1_000, 10_000, 20_000]:
    print(f"  n = {n:6d}: {running_c[n - 1]:+.4f}")
print(f"最大の跳び幅: {np.abs(np.diff(running_c)).max():.2f}")
""")
```

9. `md` — §3 収束の 3 種類。概収束・確率収束・分布収束を、含意の向き（概収束 ⇒ 確率収束 ⇒ 分布収束）とともに定義する。**どれも「近づく」だが近づき方が違う**
10. `code` — 分布収束するが確率収束しない例:

```python
code("""
rng = np.random.default_rng(2)
z = rng.normal(size=100_000)
xn, yn = z, -z                     # yn は各 n で xn と同分布だが...
print(f"xn と yn は同分布: 平均 {xn.mean():+.4f} / {yn.mean():+.4f}, 分散 {xn.var():.4f} / {yn.var():.4f}")
print(f"しかし |xn - yn| の平均 = {np.abs(xn - yn).mean():.4f}  -> 確率収束はしない")
""")
```

11. `md` — §4 デルタ法。$\sqrt{n}(\hat\theta - \theta) \to N(0, \sigma^2)$ なら $\sqrt{n}(g(\hat\theta) - g(\theta)) \to N(0, g'(\theta)^2\sigma^2)$。**06 章の漸近正規性をそのまま使い回すための道具**
12. `code` — デルタ法を実験で検算:

```python
code("""
# g(p) = log(p / (1-p)) （ロジット）。p_hat の漸近分散は p(1-p)/n。
p, n = 0.3, 400
def sampler(m, rng):
    return (rng.random(m) < p).astype(float)

logits = simulation.sampling_distribution(
    lambda s: np.log(s.mean() / (1 - s.mean())), sampler, n=n, n_reps=20_000, seed=3
)
theory_sd = np.sqrt(1.0 / (n * p * (1 - p)))     # g'(p)^2 * p(1-p)/n を整理した形
print(f"実測 sd = {logits.std(ddof=1):.5f}   デルタ法の予測 = {theory_sd:.5f}")
""")
```

13. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
中心極限定理は分散が有限であることを要求する。
これは技術的な但し書きではなく、定理が成り立つかどうかの分かれ目である。
コーシー分布の標本平均は、何個平均しても 1 個のときと同じ分布のままになる。
```
````

14. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
金融の損益、保険の支払額、ネットワークの遅延には裾の重い分布が現れる。
標本平均と正規近似で安全側の見積もりをしたつもりが、
実際には最悪ケースを大幅に過小評価していることがある。
裾の重さを先に確かめる習慣が要る。
```
````

15. `md` — §5 落とし穴（$n$ が 30 あれば正規、という経験則の危うさ／歪んだ分布では必要な $n$ がずっと大きいこと／分散が無い分布に標準誤差を計算してしまうこと）
16. `md` — §6 演習 5 問（(1) 歪んだ分布で「十分な $n$」を実験で決める (2) パレート $\alpha = 1.5$ で CLT が効くか確かめる (3) デルタ法で $\sqrt{\hat p}$ の漸近分散を出す (4) 概収束と確率収束の違う例を作る (5) 走る平均の跳びからコーシーを検出する簡単な手続きを設計する）

- [ ] **Step 2: 登録・生成・実行・時間計測**

共通の検証手順。**この章が第Ⅰ部で最も重い**（`clt_convergence` が 4 サンプラー × 6 サンプルサイズ × 4000 反復）。
Expected: 実行 45 秒以内。**超えたら `n_reps` を 4000 → 2500 に下げる**（図の見え方は変わらない）。デルタ法の実測 sd と予測は小数 3 桁で一致するはず。

- [ ] **Step 3: 本をビルドして看板図を目視確認**

Run: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`

`_build/html/notebooks/04_limit_theorems.html` を開き、次を確認する。これは report ポータルに出す図なので基準を上げる。

- スライダーが $n = 1, 2, 5, 15, 50, 200$ を動く
- $n$ を上げると normal・uniform・exponential の 3 本が重なって正規形に寄る
- cauchy だけが寄らず、横に広がったまま残る
- 凡例で 4 本が区別できる

- [ ] **Step 4: commit**

```bash
git add analytics/statistics/tools/build_nb04.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/04_limit_theorems.ipynb
git commit -m "docs(statistics): NB04 limit theorems -- the book's flagship chapter

Normal, uniform and exponential are all normalised to mean 0 and variance
1, so the visible difference in convergence speed is attributable to shape
alone. Cauchy is left in as the control that never converges: its sample
mean has the same distribution at n=200 as at n=1.

That contrast is the chapter's argument that finite variance is a
hypothesis with teeth, not a technical aside -- and it is the figure that
goes into the analytics portal."
```

---

### Task 13: NB05 — 確率過程

**Files:**
- Create: `analytics/statistics/tools/build_nb05.py`
- Create: `analytics/statistics/notebooks/05_stochastic_processes.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `processes.random_walk` / `MarkovChain` / `poisson_process` / `poisson_counts`、`plotting.random_walk_paths` / `markov_convergence_slider`
- Produces: なし

- [ ] **Step 1: `build_nb05.py` を書く**

`cells`:

1. `md` — タイトル `# 05. 確率過程 — 時間軸の上の確率` ＋「この章で分かること」5 点（i.i.d. の世界を離れるとは何か／ランダムウォークの $\sqrt{t}$ スケーリング／マルコフ性という「記憶の無さ」／定常分布とエルゴード性／ポアソン過程が指数間隔から生まれること）
2. 標準セットアップセル
3. `md` — §1 i.i.d. を離れる。これまでの章は「独立に同じ分布から何度も引く」設定だった。時間軸が入ると何が変わるか
4. `code` — ランダムウォークの経路:

```python
code("""
paths = processes.random_walk(500, n_paths=200, step="rademacher", seed=RANDOM_SEED)
plotting.random_walk_paths(paths, n_show=25)
""")
```

5. `code` — $\sqrt{t}$ スケーリングを数値で:

```python
code("""
paths = processes.random_walk(2_000, n_paths=5_000, seed=1)
for t in [10, 100, 500, 2_000]:
    print(f"t = {t:5d}: 位置の sd = {paths[:, t].std():7.3f}   sqrt(t) = {np.sqrt(t):7.3f}")
""")
```

6. `md` — §2 マルコフ性。「未来は現在だけに依る」。遷移行列 $P$ の定義と $n$ ステップ後の分布 $p_0 P^n$
7. `code` — 天気の 2 状態連鎖を定義し、$n$ ステップ後の分布を追う:

```python
code("""
P = np.array([[0.9, 0.1], [0.5, 0.5]])          # 晴れ -> 晴れ 0.9、雨 -> 晴れ 0.5
chain = processes.MarkovChain(P, states=("sunny", "rainy"))
p0 = np.array([1.0, 0.0])
for n in [0, 1, 2, 5, 20]:
    print(f"n = {n:3d}: {chain.distribution_after(n, p0).round(4)}")
print(f"定常分布   : {chain.stationary().round(4)}")
""")
```

8. `code` — 収束のスライダー:

```python
code("""
plotting.markov_convergence_slider(chain, p0=np.array([1.0, 0.0]), n_steps=30)
""")
```

9. `md` — §3 定常分布とエルゴード性。既約かつ非周期なら、どこから始めても同じ分布に落ち着き、**1 本の長い経路の時間平均が定常分布に一致する**。これが MCMC（`bayesian` 書 07 章）の土台
10. `code` — 時間平均と定常分布が一致することを確認:

```python
code("""
path = chain.simulate(200_000, x0=0, seed=2)
visited = np.bincount(path, minlength=2) / path.size
print(f"1 本の経路の時間平均: {visited.round(4)}")
print(f"定常分布            : {chain.stationary().round(4)}")
print(f"既約: {chain.is_irreducible()}   周期: {chain.period()}")
""")
```

11. `code` — 周期的な連鎖では時間平均は一致しても分布は収束しないことを示す:

```python
code("""
cycle = processes.MarkovChain(np.array([[0.0, 1.0], [1.0, 0.0]]))
print(f"周期 = {cycle.period()}")
for n in [0, 1, 2, 3]:
    print(f"  n = {n}: {cycle.distribution_after(n, np.array([1.0, 0.0])).round(3)}")
print("分布は振動し続ける（非周期性が必要な理由）")
""")
```

12. `md` — §4 ポアソン過程。指数分布の間隔で事象が起きると、区間内の件数がポアソン分布になる
13. `code` — 間隔から作って件数を確認:

```python
code("""
times = processes.poisson_process(rate=3.0, t_max=20.0, seed=3)
gaps = np.diff(np.concatenate([[0.0], times]))
print(f"件数 = {times.size}   期待 = {3.0 * 20.0}")
print(f"間隔の平均 = {gaps.mean():.4f}   期待 = {1/3:.4f}")

counts = processes.poisson_counts(rate=3.0, t_max=4.0, n_reps=50_000, seed=4)
print(f"件数の平均 = {counts.mean():.3f}   分散 = {counts.var():.3f}   （どちらも 12 のはず）")
""")
```

14. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
既約で非周期なマルコフ連鎖は、出発点を忘れて定常分布に落ち着く。
さらに、1 本の長い経路の時間平均が定常分布の期待値に一致する。
この 2 つがあるから、目的の分布を定常分布に持つ連鎖を作れば標本が得られる。
それが MCMC である。
```
````

15. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
コールセンターの待ち行列、ウェブサーバへのリクエスト、放射性崩壊。
いずれもポアソン過程が第一近似になる。
ただし現実の到着は時間帯で強度が変わるので、
一様なポアソン過程を当てはめる前に定常性を疑う必要がある。
```
````

16. `md` — §5 落とし穴（マルコフ性を確かめずに仮定する／周期性を見落として「収束しない」と誤解する／到着強度が時間変化する系に一様ポアソンを当てる）
17. `md` — §6 演習 4 問（(1) 3 状態の連鎖で定常分布を手計算し数値と照合 (2) 可約な連鎖で `stationary()` が何を返すか調べ、なぜ意味が無いか説明する (3) $\sqrt{t}$ スケーリングを正規増分でも確認する (4) 時間変化する強度のポアソン過程を作り、一様当てはめがどう失敗するか見る）

- [ ] **Step 2: 登録・生成・実行・時間計測・本ビルド・目視**

共通の検証手順。Expected: 実行 25 秒以内（`chain.simulate(200_000)` が Python ループなので最も重い。**超えたら 200,000 → 100,000 に下げる**）。
時間平均と定常分布が小数 2 桁で一致すること、収束スライダーが動くことを確認する。

- [ ] **Step 3: commit**

```bash
git add analytics/statistics/tools/build_nb05.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/05_stochastic_processes.ipynb
git commit -m "docs(statistics): NB05 stochastic processes

One chapter, three objects, and an explicit destination: the ergodic
theorem is presented as the thing that makes MCMC possible, linking
forward to the bayesian book rather than sitting as an isolated result.

The periodic 2-cycle is included precisely because its distribution never
settles -- aperiodicity is a hypothesis the reader can watch fail."
```

---

### Task 14: M2 の仕上げ — README・全章実行・予算確認

**Files:**
- Modify: `analytics/statistics/README.md`
- Modify: `analytics/statistics/notebooks/*.ipynb`（全章の再実行）

**Interfaces:**
- Consumes: Task 1–13 の全成果
- Produces: なし（Plan 2 の起点となる実測値を記録する）

- [ ] **Step 1: README を完成させる**

`analytics/statistics/README.md` を次の構成で書く（`machine_learning/README.md` を書式の手本にする）。

- 書名と 1 段落の紹介、シリーズ索引へのリンク `> シリーズ索引: [analytics 教材一覧](../README.md)`
- 対象読者・方針（seed 固定・外部 DL 無し・日本語本文/英語コード・LaTeX に日本語を入れない・静的 HTML で動く Plotly）
- **章構成の表**。全 14 章を列挙し、Plan 1 で完成した 00–05 に ✅、06–13 に 予定 を付ける
- 本書を貫く 3 原則（設計書と同文）
- 環境構築（単体 venv と workspace の両方）
- **worktree での実行方法**（`uv run` を使わず root の `.venv` の python を直接叩くこと。理由付き）
- Notebook の再生成手順（`tools/build_notebooks.py` → `nbconvert`）
- Jupyter Book のビルド手順
- テストの走らせ方と**実測テスト数**
- **各章の実測実行時間の表**（Step 2 で測る）

- [ ] **Step 2: 全章を頭から再実行し、時間を測る**

```bash
cd analytics/statistics
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py
cd -
for nb in analytics/statistics/notebooks/*.ipynb; do
  echo "=== $nb"
  /usr/bin/time -f "  %e s" PYTHONPATH=analytics/statistics/src \
    /home/kazumasa/projects/.venv/bin/python -m jupyter nbconvert \
    --to notebook --execute --inplace "$nb" 2>&1 | tail -2
done
```

Expected: 6 章の合計が **120 秒以内**。超えた章は README の表に実測値を書いたうえで、その章の Step で指定した反復数の下げ方を適用して測り直す。

> **予算を超えたまま次に進んではいけない。** 第Ⅱ部は第Ⅰ部より重い章（07 のブートストラップ・08 の FDR）を含むので、ここで 2 分を使い切ると全 14 章 5 分の予算が守れない。

- [ ] **Step 3: 全テストと lint を通す**

```bash
/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics
/home/kazumasa/projects/.venv/bin/ruff format --check analytics/statistics
```

Expected: 全て PASS。テスト数を記録する。

- [ ] **Step 4: 他の本を壊していないことを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/bayesian/tests analytics/machine_learning/tests analytics/neural_net/tests analytics/report/tests -q`
Expected: PASS。`analytics/linear_algebra` は並行セッションの編集中なので**このリストに入れない**（実行環境の節を参照）。

- [ ] **Step 5: 本を通しでビルドして全章を目視確認**

```bash
rm -rf analytics/statistics/book/_build
/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/
```

`_build/html/index.html` から 6 章すべてを開き、次を確認する。

- 全 5 つのインタラクティブ図（PPV・同時分布・ポアソン極限・CLT・マルコフ収束）がスライダーで動く
- 関係図のホバーが出る
- コールアウトが 💡/🌍 の 2 種で正しく描画され、**太字が崩れていない**
- 数式に日本語が入っていない

- [ ] **Step 6: 実測値を README に書き、commit**

Step 2–3 の実測値（章ごとの実行時間・テスト数・インタラクティブ図の点数・コールアウト数）を README の表に反映する。**目標値ではなく実測値を書くこと。**

```bash
git add analytics/statistics/README.md analytics/statistics/notebooks
git commit -m "docs(statistics): complete Part I -- README with measured numbers

Records what the six chapters actually cost rather than what they were
budgeted: per-chapter execution time, test count, figure count, callout
count. Plan 2 starts from these numbers, and the remaining 3-minute
notebook budget for Part II is what is left after them.

Also documents the worktree gotcha: uv run builds a fresh venv here, so
the root .venv python has to be invoked directly."
```

- [ ] **Step 7: Plan 1 完了の記録**

`docs/superpowers/specs/2026-08-01-analytics-statistics-design.md` の §10 実装プランの分割の表に、Plan 1 の実測結果を 1 行追記する（テスト数・NB 実行時間・図の点数）。設計書は Plan 2 の前提になるので、**目標のままにせず実測で更新する。**

```bash
git add docs/superpowers/specs/2026-08-01-analytics-statistics-design.md
git commit -m "docs(analytics): record Plan 1's measured results in the spec

Plan 2 is written against these numbers, so the spec carries what was
measured rather than what was planned."
```

---

## Plan 1 完了時の状態

| 項目 | 予定 |
|---|---|
| ソースモジュール | `datasets` `distributions` `processes` `simulation` `plotting/{core,probability}` `widgets` |
| テスト | 52 本前後（実測を README と設計書に記録） |
| Notebook | 00–05 の 6 章、出力込みでコミット |
| インタラクティブ図 | 5 点（PPV・同時分布・ポアソン極限・CLT・マルコフ収束）＋関係図 |
| コールアウト | 核心 6・実社会 6（章あたり各 1） |
| 本のビルド | `jupyter-book build` が 6 章の HTML を生成 |
| workspace | root `pyproject.toml` の members と testpaths、`Makefile` の `books` に登録済み |

**Plan 1 では触らないもの**: `estimation` `intervals` `testing` `regression` `glm` `plotting/{inference,regression}`（Plan 2）、NB 06–13（Plan 2・3）、report ポータル統合（Plan 3）、`statsmodels` の実使用（Plan 2）。
