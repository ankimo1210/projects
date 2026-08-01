# analytics/statistics Plan 3 — 橋渡し・キャップストーン・演習解答・ポータル統合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 『統計的推測の風景』を完成させる。NB11（頻度論とベイズの橋渡し）・NB12（3 視点キャップストーン）・NB13（演習解答）を書き、analytics の report ポータルに統合する。

**Architecture:** NB11 のベイズ側は `bayes_textbook` を import せず**本書内に最小実装を持つ**（analytics の各書は互いに import しない規約）。NB12 は他 4 書と**同一の合成データ生成器**を持ち、`analytics/report/tests/test_capstone_consistency.py` が 5 書の数値一致を検証する。ポータルには代表図 2 点を出す。

**Tech Stack:** Python 3.12・numpy・scipy・statsmodels・plotly・jinja2・nbformat・jupyter-book・pytest

## Global Constraints

設計書 `docs/superpowers/specs/2026-08-01-analytics-statistics-design.md` の全体要件。**全タスクの要求に暗黙的に含まれる。**

- 本文は日本語、コード・コメント・識別子は英語、**LaTeX 内に日本語を入れない**
- 乱数は **seed 固定で再現可能**、**データの外部ダウンロード依存ゼロ**（全て合成）
- 可視化の主役は **静的 HTML でも動く Plotly**。`ipywidgets` は補助
- `plotting` は**純関数**（データ → `go.Figure`）。計算は計算モジュール側
- モジュール依存は**一方向**。**他の analytics 書を import しない**
- ノートブックの JSON は手編集しない。`tools/build_nbNN.py` が唯一の正本
- ノートブックは出力込みでコミット。ビルド時は再実行しない
- コールアウトは 💡 **核心**（class: tip）と 🌍 **実社会**（class: note）、章あたり各 1–2 個
- `regression` と `glm` は **numpy だけで書く**。`statsmodels` は照合先としてのみ

## Plan 2 から引き継ぐ実測値と規約

| 項目 | 実測 |
|---|---|
| テスト | **142**（全て緑） |
| NB00–10 の再実行 | 52.7 秒 |
| **NB11–13 に使える残予算** | **247 秒 / 3 章** |
| Notebook 総サイズ | 1.58 MB |
| 最も重い章 | NB07 の 13.8 秒 |

**破ると既存テストが落ちる規約**

- アニメーション図は `plotting.core.frame_slider(frames: list[go.Frame], slider_name: str) -> go.Figure` を通す
- `widgets` は図を自作しない・`.show()` を呼ばない
- **図に生データを埋め込まない**。`np.histogram` で集計して `go.Bar` を描く
- **`tools/build_notebooks.py` は章番号を引数に取る**。`python tools/build_notebooks.py 11` のように使う。
  引数なしだと全章を再生成し、**全章の出力が消える**
- `nbkit.md` はレンダリングして太字の生成を検査する。CJK 約物に接する太字は例外になる

## 実行環境（最初に読むこと）

worktree `/home/kazumasa/projects/.claude/worktrees/analytics-statistics-plan3`（ブランチ `worktree-analytics-statistics-plan3`、`origin/main` の `5d85c822` から分岐）。

```bash
PY=/home/kazumasa/projects/.venv/bin/python      # 以後 $PY
```

- **worktree 内で `uv run` を使わない**（`.venv` が無く uv が新しい環境を作る）
- テスト: `$PY -m pytest analytics/statistics/tests -q`
- **ポータルのテストは別**: `$PY -m pytest analytics/report/tests -q`。
  こちらは **5 書すべての src を import する**ので `PYTHONPATH` に全部並べる必要がある（Task 7 参照）
- lint: `ruff check analytics/statistics` と `ruff format --check analytics/statistics`
- 本のビルド: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
- ポータルのビルド: `cd analytics/report && PYTHONPATH=. $PY -m report_builder.build`

## File Structure

| ファイル | 責務 | Task |
|---|---|---|
| `src/stats_textbook/datasets.py`（修正） | `make_capstone_dataset` を追加（他 4 書と同一実装） | 1 |
| `src/stats_textbook/bridge.py` | NB11 のベイズ側。共役事後分布・信用区間・ベイズ因子 | 2 |
| `src/stats_textbook/plotting/bridge.py` | NB11–12 の図 | 3 |
| `tools/build_nb11.py` | NB11 頻度論とベイズ | 4 |
| `tools/build_nb12.py` | NB12 キャップストーン | 5 |
| `tools/build_nb13.py` | NB13 演習解答 | 6 |
| `analytics/report/report_builder/figures.py`（修正） | `BOOKS` に statistics、代表図 2 点 | 7 |
| `analytics/report/tests/test_capstone_consistency.py`（修正） | 5 書目を追加 | 7 |
| `README.md` / 設計書 | 実測値の記録 | 8 |

---

### Task 1: `make_capstone_dataset` — 他 4 書と同一のデータ

**Files:**
- Modify: `analytics/statistics/src/stats_textbook/datasets.py`
- Test: `analytics/statistics/tests/test_datasets.py`（追記）

**Interfaces:**
- Consumes: なし
- Produces: `make_capstone_dataset(n: int = 40, x_range=(-3.0, 3.0), noise: float = 0.35, seed: int = 0) -> tuple[np.ndarray, np.ndarray]`

> **他の 4 書（`la_book` / `nn_textbook` / `bayes_textbook` / `ml_textbook`）と実装を 1 文字も違えないこと。**
> 生成順序が違うだけで別のデータになり、ポータルの横断テストが落ちる。
> 参照実装は `analytics/linear_algebra/src/la_book/datasets.py:168-180`。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_datasets.py` の末尾に追記:

```python
def test_capstone_dataset_matches_the_sibling_books_byte_for_byte():
    """The cross-book capstone only works if all five books generate the
    same numbers. Reproduced here rather than imported: analytics books do
    not depend on each other."""
    x, y = datasets.make_capstone_dataset(seed=0)
    assert x.shape == y.shape == (40,)
    assert np.all(np.diff(x) >= 0), "x must be sorted"
    # Pinned from the shared generator (la_book/datasets.py).
    assert abs(x[0] - (-2.9838)) < 1e-4, x[0]
    assert abs(x[-1] - 2.9827) < 1e-4, x[-1]
    # f(x) = sin(1.5 x) + 0.3 x with noise 0.35.
    f = np.sin(1.5 * x) + 0.3 * x
    assert abs((y - f).std(ddof=1) - 0.35) < 0.08


def test_capstone_dataset_is_deterministic():
    a = datasets.make_capstone_dataset(seed=0)
    b = datasets.make_capstone_dataset(seed=0)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_datasets.py -q`
Expected: FAIL — `AttributeError: module 'stats_textbook.datasets' has no attribute 'make_capstone_dataset'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/datasets.py` の `__all__` に `"make_capstone_dataset"` を足し、末尾に追加:

```python
def make_capstone_dataset(
    n: int = 40, x_range=(-3.0, 3.0), noise: float = 0.35, seed: int = 0
):
    """Shared 1-D regression data for the cross-book capstone (three lenses).

    The SAME generator is defined identically in all five analytics books so
    each can solve the same problem from its own lens without importing the
    others. True curve f(x) = sin(1.5 x) + 0.3 x, with Gaussian noise. Returns
    (x, y) as float64 arrays sorted by x.

    Do not "improve" this function. Any change to the draw order produces
    different numbers and breaks analytics/report's cross-book consistency
    test, which is the only thing making the capstone's claim checkable.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(x_range[0], x_range[1], n))
    f = np.sin(1.5 * x) + 0.3 * x
    y = f + noise * rng.standard_normal(n)
    return x, y
```

- [ ] **Step 4: 他書と本当に一致することを直接確かめる**

```bash
PYTHONPATH=analytics/statistics/src:analytics/linear_algebra/src:analytics/bayesian/src:analytics/neural_net/src:analytics/machine_learning/src \
/home/kazumasa/projects/.venv/bin/python - <<'PY'
import numpy as np
from stats_textbook.datasets import make_capstone_dataset as st
from la_book.datasets import make_capstone_dataset as la
from bayes_textbook.simulation import make_capstone_dataset as by
from nn_textbook.datasets import make_capstone_dataset as nn
from ml_textbook.datasets import make_capstone_dataset as ml
ref = la(seed=0)
for name, fn in [("stats", st), ("bayes", by), ("nn", nn), ("ml", ml)]:
    for a, b in zip(ref, fn(seed=0), strict=True):
        np.testing.assert_array_equal(a, b)
    print(f"{name}: identical to la_book")
PY
```

Expected: 4 行すべて `identical to la_book`

- [ ] **Step 5: テスト・lint・commit**

```bash
/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_datasets.py -q
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/datasets.py analytics/statistics/tests/test_datasets.py
git commit -m "feat(statistics): join the cross-book capstone dataset

The generator is copied rather than imported because the analytics books
deliberately do not depend on each other; the cost of that choice is that
five copies have to stay identical, which is exactly what the report
tree's consistency test exists to enforce.

The docstring says not to improve it. Any change to the draw order
silently produces different data and takes the capstone's central claim
-- that these are the same numbers seen through different lenses -- with
it."
```

---

### Task 2: `bridge.py` — ベイズ側の最小実装

**Files:**
- Create: `analytics/statistics/src/stats_textbook/bridge.py`
- Test: `analytics/statistics/tests/test_bridge.py`

**Interfaces:**
- Consumes: `intervals.Interval`（`lo` / `hi` / `contains` / `width` / iterable）
- Produces:
  - `beta_binomial_posterior(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5)` → `scipy.stats` の frozen beta 分布
  - `credible_interval(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5, level: float = 0.95) -> Interval`
  - `posterior_mean(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5) -> float`
  - `bayes_factor_proportion(k: int, n: int, p0: float = 0.5, prior_a: float = 1.0, prior_b: float = 1.0) -> float`（$H_1$ 対 $H_0$ の周辺尤度比）
  - `PRIORS: dict[str, tuple[float, float]]` — `"jeffreys"` `(0.5, 0.5)` / `"uniform"` `(1.0, 1.0)` / `"strong_high"` `(20.0, 5.0)`

> **`bayes_textbook` を import しないこと。** analytics の各書は互いに独立している。
> 共役ベータ二項は 20 行で書けるので、本書内に持つ方が依存を増やすより安い。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_bridge.py`:

```python
"""The Bayesian side of NB11, implemented here so the book stays standalone."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import bridge
from stats_textbook import simulation as sim


def test_posterior_is_the_conjugate_beta():
    post = bridge.beta_binomial_posterior(8, 10, prior_a=1.0, prior_b=1.0)
    # Beta(1 + 8, 1 + 2)
    assert abs(post.args[0] - 9.0) < 1e-12
    assert abs(post.args[1] - 3.0) < 1e-12


def test_posterior_mean_is_a_weighted_average_of_prior_and_data():
    k, n, a, b = 7, 10, 20.0, 5.0
    got = bridge.posterior_mean(k, n, a, b)
    assert abs(got - (a + k) / (a + b + n)) < 1e-12
    # It sits between the prior mean and the MLE.
    prior_mean, mle = a / (a + b), k / n
    assert min(prior_mean, mle) <= got <= max(prior_mean, mle)


def test_prior_influence_vanishes_as_n_grows():
    """Measured: a strong Beta(20, 5) prior pulls the estimate 0.167 away
    from the MLE at n=5 and 0.0002 away at n=10000."""
    gaps = []
    for n in [5, 100, 10_000]:
        k = int(0.7 * n)
        gaps.append(abs(bridge.posterior_mean(k, n, 20.0, 5.0) - k / n))
    assert gaps[0] > 0.15
    assert gaps[-1] < 0.001
    assert gaps[0] > gaps[1] > gaps[2]


def test_credible_interval_stays_inside_the_unit_interval():
    """The headline contrast of NB11. A Wald interval does not have to."""
    ci = bridge.credible_interval(8, 10)
    assert 0.0 <= ci.lo < ci.hi <= 1.0

    from stats_textbook import intervals as iv

    p_hat = 0.8
    wald = iv.wald_interval(p_hat, np.sqrt(p_hat * (1 - p_hat) / 10))
    assert wald.hi > 1.0, "the Wald interval leaves the parameter space here"


def test_credible_interval_narrows_with_more_data():
    widths = [bridge.credible_interval(int(0.8 * n), n).width() for n in [10, 100, 1000]]
    assert widths[0] > widths[1] > widths[2]
    # 1/sqrt(n) shrinkage: ten times the data, about a third the width.
    assert 2.5 < widths[0] / widths[1] < 4.0


def test_credible_interval_has_decent_frequentist_coverage():
    """Measured: at p=0.1, n=20 the Jeffreys interval covers 0.957 where
    the Wald interval manages 0.881. The Bayesian answer wins on the
    frequentist's own criterion."""
    p, n = 0.1, 20

    def sampler(m, rng):
        return (rng.random(m) < p).astype(float)

    jeff = sim.coverage_probability(
        sampler, lambda s: tuple(bridge.credible_interval(int(s.sum()), s.size)),
        truth=p, n=n, n_reps=8000, seed=0,
    )
    assert jeff.estimate > 0.93, jeff.estimate


def test_bayes_factor_favours_the_alternative_when_data_is_extreme():
    weak = bridge.bayes_factor_proportion(6, 10, p0=0.5)
    strong = bridge.bayes_factor_proportion(90, 100, p0=0.5)
    assert weak < 1.5, "6 of 10 is not evidence"
    assert strong > 100, "90 of 100 is"


def test_bayes_factor_of_a_fair_looking_sample_favours_the_null():
    assert bridge.bayes_factor_proportion(50, 100, p0=0.5) < 1.0


def test_priors_registry_has_the_three_the_chapter_uses():
    assert set(bridge.PRIORS) == {"jeffreys", "uniform", "strong_high"}
    assert bridge.PRIORS["jeffreys"] == (0.5, 0.5)


def test_rejects_impossible_counts():
    with pytest.raises(ValueError, match="k"):
        bridge.credible_interval(11, 10)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_bridge.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.bridge'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/bridge.py`:

```python
"""The Bayesian side of chapter 11, kept inside this book.

NB11 compares two procedures on the same data, so it needs a working
Bayesian analysis. Importing ``bayes_textbook`` would be the obvious
route and is deliberately not taken: the analytics books do not depend on
each other, and a conjugate beta-binomial is twenty lines.

Scope is exactly what the comparison needs -- one model, three priors, an
interval and a Bayes factor. Anything more belongs in the sibling book.
"""

from __future__ import annotations

import math

from scipy import special, stats

from .intervals import Interval

__all__ = [
    "PRIORS",
    "bayes_factor_proportion",
    "beta_binomial_posterior",
    "credible_interval",
    "posterior_mean",
]

# The three priors NB11 contrasts. Jeffreys is the "let the data speak"
# default; strong_high has a mean of 0.8 and the weight of 25 observations.
PRIORS: dict[str, tuple[float, float]] = {
    "jeffreys": (0.5, 0.5),
    "uniform": (1.0, 1.0),
    "strong_high": (20.0, 5.0),
}


def _check(k: int, n: int) -> None:
    if not 0 <= k <= n:
        raise ValueError(f"k must satisfy 0 <= k <= n; got k={k}, n={n}")


def beta_binomial_posterior(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5):
    """Posterior for a proportion after ``k`` successes in ``n`` trials.

    Conjugacy makes this exact: Beta(a, b) prior, Binomial likelihood, and
    the posterior is Beta(a + k, b + n - k). The prior's parameters read as
    pseudo-counts, which is what makes "how much data is this prior worth"
    a question with a number for an answer.
    """
    _check(k, n)
    return stats.beta(prior_a + k, prior_b + n - k)


def posterior_mean(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5) -> float:
    """(a + k) / (a + b + n) -- a weighted average of prior mean and MLE."""
    _check(k, n)
    return (prior_a + k) / (prior_a + prior_b + n)


def credible_interval(
    k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5, level: float = 0.95
) -> Interval:
    """Equal-tailed posterior interval.

    Unlike a Wald interval this cannot leave [0, 1]: it is built from
    quantiles of a distribution that lives there. NB11 uses that as the
    concrete difference between the two kinds of interval.
    """
    post = beta_binomial_posterior(k, n, prior_a, prior_b)
    lo, hi = post.ppf([(1.0 - level) / 2.0, 1.0 - (1.0 - level) / 2.0])
    return Interval(float(lo), float(hi))


def bayes_factor_proportion(
    k: int, n: int, p0: float = 0.5, prior_a: float = 1.0, prior_b: float = 1.0
) -> float:
    """Marginal likelihood of H1 (p ~ Beta) over H0 (p = p0).

    Under H0 the likelihood is just Binomial(n, p0) at k. Under H1 the
    proportion is integrated out, which conjugacy does in closed form via
    the Beta function. The ratio answers "how much more likely is this
    data under a free p than under p0", which is a different question from
    the p-value's "how extreme is this data if p = p0".
    """
    _check(k, n)
    # Both marginal likelihoods carry the binomial coefficient. It cancels in
    # the ratio -- but only if it appears on both sides. stats.binom.logpmf
    # includes it, so the Beta-function form for H1 needs it added back
    # explicitly; omitting it silently scales every Bayes factor by C(n, k),
    # which at n=100 is a factor of 1e29.
    log_coef = (
        special.gammaln(n + 1) - special.gammaln(k + 1) - special.gammaln(n - k + 1)
    )
    log_h0 = stats.binom.logpmf(k, n, p0)
    log_h1 = (
        log_coef
        + special.betaln(prior_a + k, prior_b + n - k)
        - special.betaln(prior_a, prior_b)
    )
    return float(math.exp(log_h1 - log_h0))
```

> **測定済みの値**（一様事前 $\mathrm{Beta}(1,1)$、$p_0 = 0.5$）:
> `bf(6, 10) = 0.4433`、`bf(50, 100) = 0.1244`、`bf(90, 100) = 7.25e14`。
> 二項係数を落とすと `bf(90, 100)` が 41.9 になる（正しい値の 1.7e13 分の 1）。

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_bridge.py -q`
Expected: PASS 10 件。**`test_bayes_factor_*` が落ちるはず**なので、Step 3 の注記に従って
$H_1$ 側に二項係数を足して直す。直したうえで、$k=50, n=100$ で BF < 1、$k=90, n=100$ で BF > 100 になることを確認する。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/bridge.py analytics/statistics/tests/test_bridge.py
git commit -m "feat(statistics): the Bayesian side of the bridge chapter

Conjugate beta-binomial, three priors, a credible interval and a Bayes
factor -- exactly what NB11's comparison needs and nothing else.
bayes_textbook is not imported: the analytics books stay independent, and
this is twenty lines.

The interval test carries the chapter's sharpest fact. A Jeffreys
credible interval covers 0.957 at p=0.1, n=20 where the Wald interval
manages 0.881, so the Bayesian answer wins on the frequentist's own
criterion. The framing 'which side is right' does not survive that."
```

---

### Task 3: `plotting/bridge.py` — 11–12 章の図

**Files:**
- Create: `analytics/statistics/src/stats_textbook/plotting/bridge.py`
- Modify: `analytics/statistics/src/stats_textbook/plotting/__init__.py`
- Test: `analytics/statistics/tests/test_plotting_bridge.py`

**Interfaces:**
- Consumes: `bridge.*`、`intervals.wald_interval` / `t_interval`、`regression.ols`、`simulation.coverage_probability`、`plotting.core.apply_defaults` / `frame_slider`
- Produces（`plotting/__init__.py` から再エクスポート）:
  - `interval_comparison(cases: Sequence[tuple[int, int]]) -> Figure` — `(k, n)` の列に対して Wald と信用区間を並べる
  - `prior_influence(ns: Sequence[int], p_true: float = 0.7) -> Figure` — 事前分布 3 種の事後平均が MLE に寄る
  - `posterior_slider(k_of_n: Sequence[tuple[int, int]], prior: str = "jeffreys") -> Figure` — データが増えて事後が尖る
  - `capstone_three_lenses(degree: int = 5, lam: float = 1.0, seed: int = 0) -> Figure` — **NB12 の看板図**

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_plotting_bridge.py`:

```python
"""Figures for chapters 11-12."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_interval_comparison_shows_both_kinds():
    fig = plotting.interval_comparison([(8, 10), (80, 100)])
    names = [tr.name for tr in fig.data if tr.name]
    assert any("信頼区間" in n for n in names)
    assert any("信用区間" in n for n in names)


def test_interval_comparison_marks_the_excursion_past_one():
    """At k=8, n=10 the Wald interval runs past 1.0 and the figure must
    not quietly clip it -- that excursion is the chapter's point."""
    fig = plotting.interval_comparison([(8, 10)])
    xs = [v for tr in fig.data for v in (tr.x or []) if v is not None]
    assert max(float(v) for v in xs) > 1.0


def test_prior_influence_curves_converge():
    fig = plotting.prior_influence(ns=[5, 50, 500, 5000], p_true=0.7)
    for tr in fig.data:
        if tr.name and "MLE" not in tr.name:
            y = np.asarray(tr.y, dtype=float)
            assert abs(y[-1] - 0.7) < abs(y[0] - 0.7), f"{tr.name} does not converge"


def test_posterior_slider_has_one_frame_per_dataset():
    fig = plotting.posterior_slider([(4, 5), (40, 50), (400, 500)])
    assert len(fig.frames) == 3


def test_capstone_three_lenses_draws_data_and_three_fits():
    fig = plotting.capstone_three_lenses()
    names = [tr.name for tr in fig.data if tr.name]
    assert any("観測" in n for n in names)
    assert any("頻度論" in n for n in names)
    assert any("ベイズ" in n for n in names)
    assert any("機械学習" in n for n in names)


def test_bridge_figures_go_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import bridge as bp

    assert '"method": "animate"' not in inspect.getsource(bp)


def test_bridge_figures_ship_counts_not_raw_samples():
    import inspect

    from stats_textbook.plotting import bridge as bp

    assert "go.Histogram(" not in inspect.getsource(bp)


def test_all_bridge_figures_are_plotly_figures():
    figs = [
        plotting.interval_comparison([(8, 10), (80, 100)]),
        plotting.prior_influence(ns=[5, 50]),
        plotting.posterior_slider([(4, 5), (40, 50)]),
        plotting.capstone_three_lenses(),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting_bridge.py -q`
Expected: FAIL — `AttributeError: module 'stats_textbook.plotting' has no attribute 'interval_comparison'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/plotting/bridge.py`:

```python
"""Figures for chapters 11-12.

``capstone_three_lenses`` is the book's closing figure: one dataset, three
procedures, drawn together so the places they agree and the places they
part are both visible at once.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go

from .. import bridge, datasets, intervals, regression
from .core import apply_defaults, frame_slider

__all__ = [
    "capstone_three_lenses",
    "interval_comparison",
    "posterior_slider",
    "prior_influence",
]


def capstone_features(x: np.ndarray, degree: int = 5) -> np.ndarray:
    """Polynomial design matrix with standardised non-constant columns.

    Identical to the one analytics/report's cross-book test uses. Kept
    here so NB12 and that test cannot drift apart.
    """
    x = np.asarray(x, dtype=float)
    X = np.vander(x, degree + 1, increasing=True)
    Xs = X.copy()
    Xs[:, 1:] = (X[:, 1:] - X[:, 1:].mean(0)) / X[:, 1:].std(0)
    return Xs


def interval_comparison(cases: Sequence[tuple[int, int]]) -> go.Figure:
    """Wald confidence interval against a Jeffreys credible interval (NB11)."""
    labels, wald_x, wald_y, cred_x, cred_y = [], [], [], [], []
    for row, (k, n) in enumerate(cases):
        labels.append(f"{k}/{n}")
        p_hat = k / n
        w = intervals.wald_interval(p_hat, float(np.sqrt(p_hat * (1 - p_hat) / n)))
        c = bridge.credible_interval(k, n)
        wald_x.extend([w.lo, w.hi, None])
        wald_y.extend([row + 0.12, row + 0.12, None])
        cred_x.extend([c.lo, c.hi, None])
        cred_y.extend([row - 0.12, row - 0.12, None])
    fig = go.Figure(
        data=[
            go.Scatter(
                x=wald_x, y=wald_y, mode="lines", line={"width": 6}, name="Wald 信頼区間"
            ),
            go.Scatter(
                x=cred_x, y=cred_y, mode="lines", line={"width": 6}, name="Jeffreys 信用区間"
            ),
        ]
    )
    fig.add_vline(x=1.0, line={"color": "crimson", "dash": "dot"})
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(labels))), ticktext=labels)
    return apply_defaults(
        fig,
        title="同じデータ、2 種類の区間 — 赤い破線が母数の上限 1.0",
        xaxis_title="比率 p",
        yaxis_title="観測(成功/試行)",
    )


def prior_influence(ns: Sequence[int], p_true: float = 0.7) -> go.Figure:
    """Posterior means from three priors converging on the MLE (NB11)."""
    ns = list(ns)
    labels = {
        "jeffreys": "Jeffreys 事前 Beta(0.5, 0.5)",
        "uniform": "一様事前 Beta(1, 1)",
        "strong_high": "強い事前 Beta(20, 5)(平均 0.8)",
    }
    traces = [
        go.Scatter(
            x=ns,
            y=[bridge.posterior_mean(int(p_true * n), n, *bridge.PRIORS[key]) for n in ns],
            mode="lines+markers",
            name=labels[key],
        )
        for key in ["jeffreys", "uniform", "strong_high"]
    ]
    traces.append(
        go.Scatter(
            x=ns,
            y=[p_true] * len(ns),
            mode="lines",
            line={"color": "black", "dash": "dash"},
            name=f"MLE = {p_true}",
        )
    )
    fig = go.Figure(data=traces)
    fig.update_xaxes(type="log")
    return apply_defaults(
        fig,
        title="事前分布の影響はデータが増えると消える",
        xaxis_title="標本サイズ n(対数軸)",
        yaxis_title="事後平均",
    )


def posterior_slider(
    k_of_n: Sequence[tuple[int, int]], prior: str = "jeffreys"
) -> go.Figure:
    """The posterior tightening as data accumulates (NB11)."""
    a, b = bridge.PRIORS[prior]
    grid = np.linspace(0.0, 1.0, 400)
    frames = []
    for k, n in k_of_n:
        post = bridge.beta_binomial_posterior(k, n, a, b)
        ci = bridge.credible_interval(k, n, a, b)
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(
                        x=grid,
                        y=post.pdf(grid),
                        mode="lines",
                        fill="tozeroy",
                        name=f"事後分布 95% 区間 [{ci.lo:.3f}, {ci.hi:.3f}]",
                    )
                ],
                name=f"{k}/{n}",
            )
        )
    fig = frame_slider(frames, "観測")
    return apply_defaults(
        fig, title=f"事後分布が尖っていく({prior} 事前)", xaxis_title="p", yaxis_title="密度"
    )


def capstone_three_lenses(degree: int = 5, lam: float = 1.0, seed: int = 0) -> go.Figure:
    """One dataset, three procedures (NB12).

    Frequentist least squares, the Bayesian posterior mean (which equals
    ridge with lambda = sigma^2 / sigma_w^2), and a cross-validated ridge
    standing in for the machine-learning lens.
    """
    x, y = datasets.make_capstone_dataset(seed=seed)
    phi = capstone_features(x, degree)
    grid = np.linspace(x.min(), x.max(), 300)
    phi_grid = np.vander(grid, degree + 1, increasing=True)
    raw = np.vander(x, degree + 1, increasing=True)
    phi_grid[:, 1:] = (phi_grid[:, 1:] - raw[:, 1:].mean(0)) / raw[:, 1:].std(0)

    w_ols = regression.ols(phi, y).params
    ridge = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
    w_cv = _cv_ridge(phi, y)

    fig = go.Figure(
        data=[
            go.Scatter(x=x, y=y, mode="markers", marker={"size": 7}, name="観測データ"),
            go.Scatter(
                x=grid,
                y=np.sin(1.5 * grid) + 0.3 * grid,
                mode="lines",
                line={"color": "black", "dash": "dot"},
                name="真の関数",
            ),
            go.Scatter(
                x=grid, y=phi_grid @ w_ols, mode="lines",
                name=f"頻度論(最小二乗、||w|| = {np.linalg.norm(w_ols):.2f})",
            ),
            go.Scatter(
                x=grid, y=phi_grid @ ridge, mode="lines",
                name=f"ベイズ(事後平均、||w|| = {np.linalg.norm(ridge):.2f})",
            ),
            go.Scatter(
                x=grid, y=phi_grid @ w_cv, mode="lines", line={"dash": "dash"},
                name=f"機械学習(交差検証リッジ、||w|| = {np.linalg.norm(w_cv):.2f})",
            ),
        ]
    )
    return apply_defaults(
        fig, title="1 つのデータ、3 つの視点", xaxis_title="x", yaxis_title="y"
    )


def _cv_ridge(phi: np.ndarray, y: np.ndarray, n_folds: int = 5) -> np.ndarray:
    """Ridge whose penalty is chosen by k-fold cross-validation."""
    lams = np.logspace(-4, 3, 40)
    n = y.size
    folds = np.arange(n) % n_folds
    errors = []
    for lam in lams:
        err = 0.0
        for f in range(n_folds):
            tr, te = folds != f, folds == f
            w = np.linalg.solve(
                phi[tr].T @ phi[tr] + lam * np.eye(phi.shape[1]), phi[tr].T @ y[tr]
            )
            err += float(((y[te] - phi[te] @ w) ** 2).sum())
        errors.append(err)
    best = lams[int(np.argmin(errors))]
    return np.linalg.solve(phi.T @ phi + best * np.eye(phi.shape[1]), phi.T @ y)
```

`plotting/__init__.py` に `bridge` の 4 関数を import して `__all__` に追加する
（既存の `core` / `probability` / `inference` / `regression` の行はそのまま）。

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/ -q`
Expected: 全て PASS

- [ ] **Step 5: 看板図を目視確認する**

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
from stats_textbook import plotting
S = "/tmp/claude-1000/-home-kazumasa-projects/28c66143-33d0-48c2-9656-a56508369cc3/scratchpad"
plotting.capstone_three_lenses().write_html(f"{S}/capstone_check.html", include_plotlyjs="cdn")
fig = plotting.interval_comparison([(8, 10), (80, 100), (800, 1000)])
fig.write_html(f"{S}/intervals_check.html", include_plotlyjs="cdn")
for tr in plotting.capstone_three_lenses().data:
    if tr.name: print(tr.name)
PY
```

Expected: 5 本のトレース名が出る。`||w||` は最小二乗が 7.40 前後、ベイズ（$\lambda = 1$）が 1.75 前後。
ブラウザで開き、**最小二乗が波打ち、ベイズと交差検証リッジが滑らか**であることを確認する。

- [ ] **Step 6: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/plotting analytics/statistics/tests/test_plotting_bridge.py
git commit -m "feat(statistics): figures for the bridge chapter and the capstone

interval_comparison draws the Wald interval running past 1.0 rather than
clipping it, and a test enforces that: an interval that leaves the
parameter space is the concrete difference the chapter is built on, and
a tidier figure would hide it.

capstone_three_lenses puts least squares, the Bayesian posterior mean and
a cross-validated ridge on one axis with their coefficient norms in the
legend -- 7.40 against 1.75 -- so the shrinkage is legible without
reading the code."
```

---

### Task 4: NB11 — 頻度論とベイズ

**Files:**
- Create: `analytics/statistics/tools/build_nb11.py`
- Create: `analytics/statistics/notebooks/11_frequentist_vs_bayes.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `bridge.*`、`intervals.wald_interval`、`plotting.interval_comparison` / `prior_influence` / `posterior_slider`、`simulation.coverage_probability`
- Produces: なし

**標準セットアップセル**（`bridge` を追加した版を使う）:

```python
code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    bridge, datasets, distributions, estimation, glm, intervals, plotting,
    processes, regression, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
""")
```

- [ ] **Step 1: `build_nb11.py` を書く**

`cells`:

1. `md` — タイトル `# 11. 頻度論とベイズ — 同じデータ、2 つの流儀` ＋ 一文要約「どちらが正しいかではなく、何を確率変数と見なすかが違う」＋「この章で分かること」5 点
2. 標準セットアップセル
3. `md` — §1 違いは 1 点に集約される。**頻度論は母数を定数と見なし、ベイズは確率変数と見なす。**
   ここから、信頼区間と信用区間の解釈の違い・事前分布の要否・p 値とベイズ因子の違いがすべて従う
4. `md` — §2 同じデータで両方を計算する。10 回中 8 回成功
5. `code` — 数値を並べる:

```python
code("""
k, n = 8, 10
p_hat = k / n

wald = intervals.wald_interval(p_hat, float(np.sqrt(p_hat * (1 - p_hat) / n)))
cred = bridge.credible_interval(k, n)                      # Jeffreys 事前

print(f"観測: {n} 回中 {k} 回成功   MLE = {p_hat:.4f}")
print(f"  頻度論 95% 信頼区間(Wald) = [{wald.lo:.4f}, {wald.hi:.4f}]")
print(f"  ベイズ 95% 信用区間        = [{cred.lo:.4f}, {cred.hi:.4f}]")
print(f"  ベイズ事後平均             = {bridge.posterior_mean(k, n):.4f}")
print(f"\\n信頼区間の上限が {wald.hi:.4f} -- 比率なのに 1 を超えている")
""")
```

6. `code` — 図:

```python
code("""
plotting.interval_comparison([(8, 10), (80, 100), (800, 1000)])
""")
```

7. `md` — §3 読み方の違い。
   - **信頼区間**: 「この手続きを繰り返すと 95% の区間が真値を含む」（07 章）。区間がランダム
   - **信用区間**: 「事後分布のもとで $p$ がこの範囲にある確率が 95%」。**母数の方がランダム**

   前者は $p$ について確率を語れない。後者は語れる。その代償が事前分布である
8. `md` — §4 事前分布は何をしているのか。共役ベータ二項では事前分布のパラメータが**疑似観測数**として読める。
   $\mathrm{Beta}(a, b)$ は「すでに $a$ 回成功・$b$ 回失敗を見た」に相当する
9. `code` — 事前分布の影響が消えていく（図と数値）:

```python
code("""
plotting.prior_influence(ns=[5, 20, 100, 1000, 10_000], p_true=0.7)
""")
```

```python
code("""
print(f"{'n':>7} {'MLE':>8} {'一様事前':>10} {'強い事前(平均0.8)':>18} {'強い事前との差':>16}")
for n in [5, 20, 100, 1000, 10_000]:
    k = int(0.7 * n)
    mle = k / n
    unif = bridge.posterior_mean(k, n, *bridge.PRIORS["uniform"])
    strong = bridge.posterior_mean(k, n, *bridge.PRIORS["strong_high"])
    print(f"{n:7d} {mle:8.4f} {unif:10.4f} {strong:18.4f} {abs(strong - mle):16.4f}")
print("\\n強い事前でも n = 10000 では MLE と 0.0002 しか違わない。")
print("事前分布が効くのはデータが少ないときだけである")
""")
```

10. `code` — 事後分布が尖る図:

```python
code("""
plotting.posterior_slider([(4, 5), (14, 20), (70, 100), (700, 1000)])
""")
```

11. `md` — §5 **信用区間は頻度論的被覆を持つか。** ここが本章で最も面白い。
    ベイズの区間を頻度論の基準（被覆率）で採点してみる
12. `code` — 実測（この章の看板）:

```python
code("""
def wald_from_counts(s):
    k, n = int(s.sum()), s.size
    p = k / n
    se = float(np.sqrt(max(p * (1 - p), 1e-12) / n))
    return tuple(intervals.wald_interval(p, se))

def credible_from_counts(s):
    return tuple(bridge.credible_interval(int(s.sum()), s.size))

print(f"{'真の p':>8} {'n':>5} {'Wald 信頼区間':>16} {'Jeffreys 信用区間':>20}")
for p in [0.1, 0.3, 0.5, 0.8]:
    for n in [20, 100]:
        sampler = lambda m, rng, _p=p: (rng.random(m) < _p).astype(float)
        cw = simulation.coverage_probability(
            sampler, wald_from_counts, truth=p, n=n, n_reps=8000, seed=0).estimate
        cj = simulation.coverage_probability(
            sampler, credible_from_counts, truth=p, n=n, n_reps=8000, seed=0).estimate
        print(f"{p:8.1f} {n:5d} {cw:16.4f} {cj:20.4f}")
print("\\n名目はどちらも 0.95。")
print("極端な p では、ベイズの区間の方が頻度論の基準でも優れている")
""")
```

13. `md` — 図の読み方。$p = 0.1$、$n = 20$ で Wald は 0.881、Jeffreys 信用区間は 0.957。
    **ベイズの答えが、頻度論の採点基準で勝っている。**
    「どちらが正しいか」という問いの立て方が成り立たないことが、これで分かる
14. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
頻度論とベイズの違いは、母数を定数と見なすか確率変数と見なすかの 1 点に尽きる。
そこから区間の解釈も事前分布の要否も従う。
そして極端な比率では、ベイズの信用区間の方が頻度論の被覆率でも優れている。
どちらが正しいかではなく、何を問いたいかで選ぶ。
```
````

15. `md` — §6 p 値とベイズ因子。前者は「$H_0$ のもとでこれほど極端なデータが出る確率」、
    後者は「$H_1$ と $H_0$ でデータの起こりやすさが何倍違うか」。**違う量である**
16. `code` — 並べて計算:

```python
code("""
from scipy import stats as sps

print(f"{'観測':>12} {'p 値(両側)':>12} {'ベイズ因子':>16} {'読み方':>12}")
for k, n in [(6, 10), (90, 100), (600, 1000)]:
    p_value = float(sps.binomtest(k, n, 0.5).pvalue)
    bf = bridge.bayes_factor_proportion(k, n, p0=0.5)
    verdict = "H1 支持" if bf > 3 else ("どちらとも" if bf > 1 / 3 else "H0 支持")
    print(f"{f'{k}/{n}':>12} {p_value:12.6f} {bf:16.4f} {verdict:>12}")
""")
```

18b. `md` — §6b **同じデータで逆の結論が出る。** 各 $n$ について、
p 値が 0.05 を切る最小の $k$ を取る。つまり「ぎりぎり有意」なデータを $n$ ごとに集める

18c. `code` — Jeffreys–Lindley のパラドックス（実測済み）:

```python
code("""
from scipy import stats as sps

print("各 n で「ぎりぎり有意」になるデータを取る:")
print(f"{'n':>9} {'k':>9} {'p_hat':>8} {'p 値':>9} {'ベイズ因子':>12} {'ベイズの判定':>14}")
for n in [100, 1_000, 10_000, 100_000, 1_000_000]:
    for k in range(n // 2, n):
        if float(sps.binomtest(k, n, 0.5).pvalue) < 0.05:
            break
    p_value = float(sps.binomtest(k, n, 0.5).pvalue)
    bf = bridge.bayes_factor_proportion(k, n, p0=0.5)
    verdict = "H1 支持" if bf > 3 else ("どちらとも" if bf > 1 / 3 else "H0 支持")
    print(f"{n:9d} {k:9d} {k / n:8.4f} {p_value:9.5f} {bf:12.4f} {verdict:>14}")
print("\\nどの行も p 値は 0.05 を切っている(頻度論は「有意」と言う)。")
print("しかしベイズ因子は n が増えるほど H0 に傾き、n = 10^6 では 116 倍 H0 有利になる。")
print("これが Jeffreys-Lindley のパラドックス。同じデータ、逆の結論である")
""")
```

17. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
医薬品の承認は頻度論の枠組みで動いている。第 1 種の誤りを規制当局が管理したいからである。
一方、A/B テストの逐次的な打ち切りや、データが少ない領域の意思決定ではベイズが実用的である。
事前分布を明示する義務が、逆に前提を議論の対象にできるという利点になる。
選択は哲学ではなく、誰が何を保証したいかで決まる。
```
````

18. `md` — §7 落とし穴（事前分布を「無情報」と呼んで責任を回避しない — パラメータ変換で無情報でなくなる／
    ベイズ因子は事前分布に敏感で、$H_1$ の事前を広げると自動的に $H_0$ が有利になる（Lindley のパラドクス）／
    信用区間を「95% の確率で真値が入る」と読むのは正しいが、その確率は事前分布に条件付いている）
19. `code` — Lindley のパラドクス:

```python
code("""
print("H1 の事前分布を広げるとベイズ因子が下がる(Lindley のパラドクス):")
print(f"{'H1 の事前':>22} {'ベイズ因子(60/100)':>22}")
for a, b, label in [(50, 50, "Beta(50,50) 狭い"), (5, 5, "Beta(5,5)"),
                    (1, 1, "Beta(1,1) 一様"), (0.1, 0.1, "Beta(0.1,0.1) 広い")]:
    bf = bridge.bayes_factor_proportion(60, 100, p0=0.5, prior_a=a, prior_b=b)
    print(f"{label:>22} {bf:22.4f}")
print("\\n同じデータでも H1 の事前を広げるほど H0 が有利になる。")
print("ベイズ因子を報告するときは事前分布も一緒に報告しなければ意味がない")
""")
```

20. `md` — §8 演習 4 問（(1) 一様事前と Jeffreys 事前で信用区間の被覆率を比較せよ
    (2) 事前分布が $p$ について無情報でも $\log\frac{p}{1-p}$ については無情報でないことを示せ
    (3) Wald 区間の代わりに Wilson 区間を使うと被覆率がどう変わるか測れ
    (4) ベイズ因子と p 値が逆の結論を出すデータを構成せよ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

`NOTEBOOKS` に `("build_nb11", "11_frequentist_vs_bayes")`、`_toc.yml` に 1 行追加してから:

```bash
cd analytics/statistics
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py 11
cd -
time PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python -m jupyter \
  nbconvert --to notebook --execute --inplace analytics/statistics/notebooks/11_frequentist_vs_bayes.ipynb
```

Expected: 実行 40 秒以内（§5 の被覆実験 8 通り × 8000 反復が最も重い。超えたら `n_reps` を 4000 に）。
実測の目安: $p=0.1, n=20$ で Wald 0.8809 / Jeffreys 0.9567、$p=0.8, n=20$ で 0.9156 / 0.9575。

出力に error と stderr が無いことを、Plan 2 と同じ点検スクリプトで確認する。

- [ ] **Step 3: 本をビルドして目視確認・commit**

```bash
git add analytics/statistics/tools/build_nb11.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/11_frequentist_vs_bayes.ipynb
git commit -m "docs(statistics): NB11 frequentist and Bayesian, side by side

Reduces the difference to one choice -- is the parameter a constant or a
random variable -- and derives the rest from it.

The chapter's sharpest measurement is the one that dissolves the
argument: scored on frequentist coverage, the Jeffreys credible interval
beats the Wald interval at extreme proportions, 0.957 against 0.881 at
p=0.1, n=20. A question phrased as 'which school is right' does not
survive that number.

Lindley's paradox closes the pitfalls: widening H1's prior monotonically
favours H0 on identical data, so a Bayes factor reported without its
prior is not a number anyone can read."
```

---

### Task 5: NB12 — 3 視点キャップストーン

**Files:**
- Create: `analytics/statistics/tools/build_nb12.py`
- Create: `analytics/statistics/notebooks/12_capstone_three_lenses.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `datasets.make_capstone_dataset`、`plotting.capstone_three_lenses`、`plotting.bridge.capstone_features`、`regression.ols`
- Produces: なし

> **実測済みの数値**（seed 0、$n=40$、degree 5、標準化済み）:
> 最小二乗の $\|w\| = 7.4037$、リッジ($\lambda=1$)の $\|w\| = 1.7542$、
> 最小二乗の $R^2 = 0.8413$、$\hat\sigma = 0.3772$（真のノイズ 0.35）、係数 6 本中 4 本が $p < 0.05$。
> **最小二乗 = リッジ($\lambda \to 0$)** が 3.4e-09、**リッジ($\lambda=1$) = ベイズ事後平均**が 7.8e-16 で一致。

- [ ] **Step 1: `build_nb12.py` を書く**

`cells`:

1. `md` — タイトル `# 12. キャップストーン — 1 つのデータ、3 つの視点` ＋ 一文要約「同じ回帰問題を頻度論・ベイズ・機械学習で解き、一致する所と割れる所を見る」
2. 標準セットアップセル（`bridge` を含む版）
3. `md` — §1 問題設定。$f(x) = \sin(1.5x) + 0.3x$ に正規ノイズ。40 点。5 次多項式で当てる。
   **このデータは analytics の 5 書すべてで同一**であり、各書が自分の道具で同じ問題を解いている
4. `code` — データと 3 つの当てはめ（看板図）:

```python
code("""
x, y = datasets.make_capstone_dataset(seed=0)
print(f"n = {x.size}   x in [{x.min():.3f}, {x.max():.3f}]   真の関数 f(x) = sin(1.5x) + 0.3x")
plotting.capstone_three_lenses()
""")
```

5. `md` — §2 **頻度論の視点**。母数は定数。最小二乗で点推定し、標準誤差と信頼区間を付ける
6. `code`:

```python
code("""
from stats_textbook.plotting.bridge import capstone_features

phi = capstone_features(x, degree=5)
fit = regression.ols(phi, y)
print(f"{'次数':>6} {'係数':>10} {'標準誤差':>10} {'t 値':>9} {'p 値':>11}")
for j in range(phi.shape[1]):
    print(f"{j:6d} {fit.params[j]:10.4f} {fit.se[j]:10.4f} "
          f"{fit.tvalues[j]:9.3f} {fit.pvalues[j]:11.4f}")
print(f"\\nR^2 = {fit.r_squared:.4f}   残差の sd = {np.sqrt(fit.sigma2):.4f}(真のノイズ 0.35)")
print(f"p < 0.05 の係数: {int((fit.pvalues < 0.05).sum())} / {fit.pvalues.size} 本")
print(f"係数ベクトルのノルム ||w|| = {np.linalg.norm(fit.params):.4f}")
""")
```

7. `md` — §3 **ベイズの視点**。母数に事前分布 $w \sim N(0, \sigma_w^2 I)$ を置く。
   事後平均は**リッジ回帰と厳密に一致する**（$\lambda = \sigma^2/\sigma_w^2$）
8. `code` — 一致を数値で:

```python
code("""
sigma, sigma_w = 1.0, 1.0
lam = sigma**2 / sigma_w**2

ridge = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
prec = phi.T @ phi / sigma**2 + np.eye(phi.shape[1]) / sigma_w**2
post_mean = np.linalg.solve(prec, phi.T @ y / sigma**2)

print(f"リッジ(lambda = {lam})   : {ridge.round(6)}")
print(f"ベイズ事後平均            : {post_mean.round(6)}")
print(f"最大差                    : {np.abs(ridge - post_mean).max():.2e}")
print(f"\\n||w||: 最小二乗 {np.linalg.norm(fit.params):.4f} -> ベイズ {np.linalg.norm(ridge):.4f}")
print("事前分布が係数を原点に引き寄せている。これが「正則化」の正体")
""")
```

9. `code` — 逆方向も確認（$\lambda \to 0$ で最小二乗に戻る）:

```python
code("""
print(f"{'lambda':>10} {'||w||':>10} {'最小二乗との最大差':>20}")
for lam_try in [1e-10, 1e-4, 0.01, 1.0, 100.0]:
    w = np.linalg.solve(phi.T @ phi + lam_try * np.eye(phi.shape[1]), phi.T @ y)
    print(f"{lam_try:10.0e} {np.linalg.norm(w):10.4f} {np.abs(w - fit.params).max():20.2e}")
print("\\nlambda -> 0 で最小二乗に戻る。頻度論は「事前分布を置かないベイズ」でもある")
""")
```

10. `md` — §4 **機械学習の視点**。母数の解釈には関心がなく、**未見のデータへの予測誤差**を最小にしたい。
    $\lambda$ は理屈ではなく交差検証で選ぶ
11. `code` — 交差検証:

```python
code("""
lams = np.logspace(-4, 3, 40)
folds = np.arange(x.size) % 5
cv_err = []
for lam_try in lams:
    err = 0.0
    for f in range(5):
        tr, te = folds != f, folds == f
        w = np.linalg.solve(phi[tr].T @ phi[tr] + lam_try * np.eye(phi.shape[1]), phi[tr].T @ y[tr])
        err += float(((y[te] - phi[te] @ w) ** 2).sum())
    cv_err.append(err / x.size)
best = lams[int(np.argmin(cv_err))]
w_cv = np.linalg.solve(phi.T @ phi + best * np.eye(phi.shape[1]), phi.T @ y)
print(f"交差検証が選んだ lambda = {best:.4f}   (CV MSE = {min(cv_err):.4f})")
print(f"||w|| = {np.linalg.norm(w_cv):.4f}")
print(f"\\n訓練データでの MSE: 最小二乗 {np.mean((y - phi @ fit.params) ** 2):.4f}"
      f" < CV リッジ {np.mean((y - phi @ w_cv) ** 2):.4f}")
print("訓練誤差では最小二乗が勝つ。それが過学習である")
""")
```

12. `md` — §5 **3 視点の突き合わせ**。何が一致し、何が割れるか
13. `code` — 表にまとめる:

```python
code("""
def true_mse(w):
    grid = np.linspace(x.min(), x.max(), 500)
    raw = np.vander(x, 6, increasing=True)
    pg = np.vander(grid, 6, increasing=True)
    pg[:, 1:] = (pg[:, 1:] - raw[:, 1:].mean(0)) / raw[:, 1:].std(0)
    return float(np.mean((np.sin(1.5 * grid) + 0.3 * grid - pg @ w) ** 2))

print(f"{'視点':>16} {'||w||':>9} {'訓練 MSE':>10} {'真の関数との MSE':>18}")
for label, w in [("頻度論(最小二乗)", fit.params), ("ベイズ(事後平均)", ridge),
                 ("機械学習(CV リッジ)", w_cv)]:
    print(f"{label:>16} {np.linalg.norm(w):9.4f} "
          f"{np.mean((y - phi @ w) ** 2):10.4f} {true_mse(w):18.4f}")
""")
```

14. `md` — 読み方。**一致する所**: ベイズ事後平均とリッジは同じ計算である。$\lambda \to 0$ で頻度論に戻る。
    **割れる所**: 訓練 MSE は最小二乗が最小だが、真の関数との距離では負ける。
    3 者は違う量を最小化しているので、違う答えを出すのが正しい
15. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
3 つの視点は同じ計算に別の意味を与えている。
リッジ回帰は、頻度論には正則化、ベイズには事前分布、機械学習には汎化のための道具に見える。
違う答えが出るのは、最小化している量が違うからであって、どれかが間違っているからではない。
```
````

16. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
同じモデルを組んでも、報告すべき数字は目的で変わる。
規制当局に出すなら係数の信頼区間、意思決定を支援するなら事後分布、
本番投入するなら交差検証の予測誤差である。
どれか 1 つだけを見て他を代用させると、答えられない問いに答えたことになる。
```
````

17. `md` — §6 姉妹本との接続。同じデータを `linear_algebra`（SVD と条件数）、`neural_net`（勾配降下）、
    `bayesian`（事後分布の全体）、`machine_learning`（モデル選択）が別の角度から扱っている。
    `analytics/report` の横断テストが 5 書の数値一致を保証している
18. `md` — §7 演習 3 問（(1) 次数を 12 に上げて 3 視点の差がどうなるか調べよ
    (2) $\sigma_w$ を変えて事後平均が最小二乗とリッジの間をどう動くか追え
    (3) 交差検証の分割数を変えて選ばれる $\lambda$ の安定性を測れ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

Expected: 実行 10 秒以内。§3 の一致は 1e-15 台、§2 の $R^2$ は 0.8413、
$\hat\sigma$ は 0.3772、有意な係数は 4/6 本。

- [ ] **Step 3: 本をビルドして目視確認・commit**

```bash
git add analytics/statistics/tools/build_nb12.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/12_capstone_three_lenses.ipynb
git commit -m "docs(statistics): NB12 capstone -- one dataset, three lenses

Shows the identity rather than asserting it: the Bayesian posterior mean
and ridge with lambda = sigma^2/sigma_w^2 agree to 7.8e-16, and ridge
returns to least squares as lambda goes to zero (3.4e-09 at 1e-10). The
same computation carries three different meanings.

Then shows where they part. Least squares wins on training MSE and loses
on distance to the true function, because the three procedures minimise
different quantities. Coefficient norms make it concrete: 7.40 for least
squares against 1.75 once a prior is in play."
```

---

### Task 6: NB13 — 演習解答

**Files:**
- Create: `analytics/statistics/tools/build_nb13.py`
- Create: `analytics/statistics/notebooks/13_exercise_solutions.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `stats_textbook` の全モジュール
- Produces: なし

> **各章の演習を実際に解くこと。** 問題を再掲して「解答は読者に任せる」と書くのは解答編ではない。
> 導出を求める問題には導出を、測定を求める問題にはコードと数値を置く。
> **実測済みの問題数**（01–10 章、Plan 2 完了時点）: 01–06 と 08 が各 5 問、07・09・10 が各 4 問で
> **計 47 問**。これに Task 4 の NB11（4 問）と Task 5 の NB12（3 問）を足して **54 問**になる。
> 各章の演習は対応する `tools/build_nbNN.py` の最後の `md` セルに書かれているので、そこから拾う。

- [ ] **Step 1: 各章の演習を機械的に抽出して確認する**

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
import json, pathlib, re
for nb in sorted(pathlib.Path("analytics/statistics/notebooks").glob("*.ipynb")):
    d = json.load(open(nb))
    for c in d["cells"]:
        if c["cell_type"] != "markdown":
            continue
        src = "".join(c["source"])
        if "## " in src and "演習" in src:
            items = re.findall(r"^\d+\.", src, flags=re.M)
            print(f"{nb.stem:<40} {len(items)} 問")
PY
```

Expected: 01–12 の各章について問題数が出る（00 と 13 に演習は無い）。
**この出力を数えて 54 問になることを確認してから解答を書く。**

- [ ] **Step 2: `build_nb13.py` を書く**

構成:

1. `md` — タイトル `# 13. 演習の解答` ＋ 「01–12 章の演習 54 問の解答。問題文を再掲したうえで、
   導出を求めるものには導出を、測定を求めるものには実行できるコードと数値を置いた」
   （**問題数は Step 1 の実測に合わせること。54 = 01–10 章の 47 ＋ NB11 の 4 ＋ NB12 の 3**）
2. 標準セットアップセル
3. 各章について `md`（`## 01 章 確率の土台` のような見出し）＋ 問題ごとに `md`（問題文と解答の説明）
   ＋ 必要なら `code`（数値の確認）

**解答の質の基準**（1 問ごとに満たすこと）:

- 問題文を 1 行で再掲する（読者が元の章に戻らずに読める）
- 導出問題は**式変形を書く**。「明らかである」で済ませない
- 測定問題は**実行できるコードと、その出力の読み方**を書く
- 「なぜそうなるか」を 1–2 文で添える。答えだけを置かない

**特に手を抜かないこと**（解答が本文より価値を持つ問題）:

- 01-1（公理から $P(A \cup B)$ を導く）: $A \cup B = A \cup (B \setminus A)$ と排反性から
- 04-3（デルタ法で $\sqrt{\hat p}$ の漸近分散）: $g'(p) = 1/(2\sqrt p)$ より $\frac{1-p}{4n}$。
  $p \to 0$ で近似が壊れる理由も書く
- 06-3（一様分布の MLE と Cramér–Rao）: $\hat\theta = \max_i X_i$、
  $\mathrm{Var} = \frac{n\theta^2}{(n+1)^2(n+2)} \sim \theta^2/n^2$ で下限 $\theta^2/n$ を**下回る**。
  台が母数に依存し正則条件が破れるため
- 08-1（$1-(1-\alpha)^m$）: 導出とシミュレーション。独立でない場合は上界になること
- 10-3（IRLS = Newton–Raphson）: 正準リンクではスコア $X^\top(y-\mu)$、
  ヘッセ $-X^\top W X$ になり、Newton の更新式が IRLS の重み付き最小二乗と一致する
- 11-2（$p$ について一様な事前はロジットについて一様でない）: ヤコビアン $\frac{dp}{d\eta} = p(1-p)$

- [ ] **Step 3: 登録・生成・実行・出力点検・時間計測**

Expected: 実行 30 秒以内。**解答のコードセルが 1 つも失敗しないこと**が最低条件である。

- [ ] **Step 4: 解答の網羅性を機械的に確認する**

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
import json, re
nb = json.load(open("analytics/statistics/notebooks/13_exercise_solutions.ipynb"))
src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
for ch in range(1, 13):
    n = len(re.findall(rf"^### {ch:02d}-\d+", src, flags=re.M))
    print(f"{ch:02d} 章: {n} 問")
print(f"\n合計 {len(re.findall(r'^### \d\d-\d+', src, flags=re.M))} 問")
PY
```

Expected: Step 1 で数えた問題数と一致する。**解答の見出しは `### NN-M` の形式に統一すること**
（この確認スクリプトが動くように）。

- [ ] **Step 5: 本をビルドして commit**

```bash
git add analytics/statistics/tools/build_nb13.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/13_exercise_solutions.ipynb
git commit -m "docs(statistics): NB13 exercise solutions

Every exercise from chapters 01-12 is answered, with the derivation
written out where the exercise asks for one and runnable code where it
asks for a measurement.

Two of them are worth more than the chapters that set them. The uniform
distribution's MLE beats the Cramer-Rao bound -- variance of order
theta^2/n^2 against a bound of theta^2/n -- because its support depends
on the parameter and the regularity conditions do not hold. And a prior
that is uniform in p is not uniform in the log-odds, which is the
concrete reason 'uninformative' is not a property a prior can have on
its own."
```

---

### Task 7: report ポータル統合

**Files:**
- Modify: `analytics/report/report_builder/figures.py`
- Modify: `analytics/report/tests/test_capstone_consistency.py`
- Modify: `analytics/report/tests/test_report_build.py`（ページ名の固定リスト 2 箇所）
- Modify: `analytics/report/README.md`（書名の一覧があれば）
- Install: `stats_textbook` を root の `.venv` へ editable install（Step 0）

**Interfaces:**
- Consumes: `stats_textbook.plotting.coverage_intervals` / `clt_convergence`、`stats_textbook.datasets.make_capstone_dataset`、`stats_textbook.regression.ols`
- Produces: なし

> **ポータルのテストは 5 書すべての src を import する。** 実行するときは:
> ```bash
> W=/home/kazumasa/projects/.claude/worktrees/analytics-statistics-plan3
> PYTHONPATH=$W/analytics/linear_algebra/src:$W/analytics/neural_net/src:$W/analytics/bayesian/src:$W/analytics/machine_learning/src:$W/analytics/statistics/src \
>   /home/kazumasa/projects/.venv/bin/python -m pytest analytics/report/tests -q
> ```

> **`stats_textbook` は root の `.venv` に editable install されていない**（他の 4 書は入っている）。
> ポータルは `PYTHONPATH=.` だけで動く前提なので、**このままでは `make report` が
> `ModuleNotFoundError: No module named 'stats_textbook'` で落ちる。**
> Step 0 でこれを直す。

- [ ] **Step 0: `stats_textbook` を editable install する**

```bash
cd /home/kazumasa/projects
/home/kazumasa/projects/.venv/bin/python -m pip install -e analytics/statistics --no-deps
/home/kazumasa/projects/.venv/bin/python -c "import stats_textbook; print(stats_textbook.__file__)"
```

Expected: main ツリー側（`/home/kazumasa/projects/analytics/statistics/src/stats_textbook/__init__.py`）を指す。
**`--no-deps` は必須**（`machine_learning` と同じ手順。付けないと依存解決が root の環境全体に及ぶ）。

> **注意**: editable install は **main ツリー側**を指す。worktree で編集した内容は
> `PYTHONPATH` で明示しない限り反映されない。Plan 1・2 で繰り返し踏んだ罠と同じ構造である。
> このタスクの検証では `PYTHONPATH` を先頭に置いて worktree 側を優先させること。

- [ ] **Step 1: 横断テストに 5 書目を足す（失敗する状態にする）**

`analytics/report/tests/test_capstone_consistency.py` を修正:

```python
from stats_textbook.datasets import make_capstone_dataset as st_data
from stats_textbook.regression import ols as st_ols
```

`test_four_books_share_identical_data` を改名・拡張:

```python
def test_five_books_share_identical_data():
    books = [la_data(seed=0), nn_data(seed=0), by_data(seed=0), ml_data(seed=0), st_data(seed=0)]
    ref = books[0]
    for other in books[1:]:
        for ref_arr, other_arr in zip(ref, other, strict=True):
            np.testing.assert_array_equal(ref_arr, other_arr)
```

新しいテストを追加:

```python
def test_the_frequentist_lens_is_ridge_at_zero_penalty():
    """statistics' capstone lens joins the other four at the limit.

    Least squares is what ridge becomes when the prior stops pulling, so
    the fifth book's answer has to be the lambda -> 0 end of the same
    family. Measured agreement: 3.4e-09 at lambda = 1e-10.
    """
    x, y = st_data(seed=0)
    phi = _features(x, degree=5)
    np.testing.assert_allclose(st_ols(phi, y).params, la_ridge(phi, y, 1e-10), atol=1e-7)


def test_shrinkage_is_visible_in_the_coefficient_norms():
    """The capstone's headline: a prior costs 7.40 of norm and buys stability."""
    x, y = st_data(seed=0)
    phi = _features(x, degree=5)
    norm_ols = float(np.linalg.norm(st_ols(phi, y).params))
    norm_ridge = float(np.linalg.norm(la_ridge(phi, y, 1.0)))
    assert 7.0 < norm_ols < 8.0, norm_ols
    assert 1.5 < norm_ridge < 2.0, norm_ridge
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: 上の `PYTHONPATH` 付きコマンド
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook'`（`PYTHONPATH` に足す前）か、
足した後は PASS するはず。**Task 1 が済んでいれば Step 1 のテストは通る。** 通らなければ
`make_capstone_dataset` の実装が他書とずれている。

- [ ] **Step 3: `figures.py` に statistics を登録する**

`BOOKS` に追加（`machine_learning` の後ろ）:

```python
    "statistics": BookMeta(
        key="statistics",
        title="統計的推測の風景",
        subtitle="不確実性を測り、判断する言語",
        accent="#ea580c",
        book_index="../../statistics/book/_build/html/index.html",
        nav="統計",
    ),
```

図のビルダを 2 つ追加（`FIGURES` リストの末尾）:

```python
def _st_coverage_intervals():
    from stats_textbook import plotting as stp

    return stp.coverage_intervals(n_intervals=100, n=12, truth=0.0, seed=0)


def _st_clt_convergence():
    from stats_textbook import plotting as stp

    return stp.clt_convergence(
        ["normal", "uniform", "exponential", "cauchy"], ns=[1, 2, 5, 15, 50, 200], n_reps=3000
    )
```

```python
    FigureSpec(
        "st_coverage_intervals",
        "statistics",
        "95% 信頼区間を 100 本引く",
        "「95%」は区間ではなく手続きの性質である。100 本引いて数えると、"
        "そのうち何本が真値を含んだかが見える。",
        _st_coverage_intervals,
        is_new=True,
        tags=("inference", "simulation"),
    ),
    FigureSpec(
        "st_clt_convergence",
        "statistics",
        "中心極限定理が効く分布、効かない分布",
        "標本平均を sqrt(n) で標準化すると正規分布に寄る。"
        "分散が存在しないコーシー分布だけは、いくら n を増やしても寄らない。",
        _st_clt_convergence,
        is_new=True,
        tags=("slider", "limit-theorem"),
    ),
```

- [ ] **Step 3b: ポータルの end-to-end テストに statistics のページを足す**

`analytics/report/tests/test_report_build.py` の `test_render_site_is_offline_and_complete` は、
**ページ名の固定リスト**をループして (a) ファイルの存在と (b) **外部 URL が漏れていないこと**を検査する。
`statistics` を両方のタプルに足さないと、新しいページだけがオフライン保証の検査から漏れる。

```python
    for name in (
        "index",
        "gallery",
        "integration",
        "linear_algebra",
        "neural_net",
        "bayesian",
        "laplace",
        "statistics",
    ):
```

**2 箇所ある**（存在確認のループと外部 URL 確認のループ）。両方直すこと。

なお `test_registry_covers_books` は `linear_algebra` / `neural_net` / `bayesian` / `laplace` に
「図が 5 点以上」を要求するが、statistics はそのリストに入っていないので 2 点で問題ない。
`len(FIGURES) >= 22` などの下界も、図を足す分には自動的に満たされる。

- [ ] **Step 4: ポータルをビルドして確認する**

```bash
cd analytics/report
PYTHONPATH=.:$W/analytics/linear_algebra/src:$W/analytics/neural_net/src:$W/analytics/bayesian/src:$W/analytics/machine_learning/src:$W/analytics/statistics/src \
  /home/kazumasa/projects/.venv/bin/python -m report_builder.build
cd -
ls analytics/report/site/
grep -c "統計的推測の風景" analytics/report/site/index.html
```

Expected: ビルド成功、`site/statistics.html` が生成される、`index.html` に書名が現れる。

- [ ] **Step 5: ポータルのテストを走らせる**

Run: Step 1 の `PYTHONPATH` 付き pytest コマンド
Expected: 全て PASS

- [ ] **Step 6: commit**

```bash
git add analytics/report
git commit -m "feat(report): the statistics book joins the portal

Two figures go into the gallery: the hundred confidence intervals, which
is the one figure a reader should take away from the book, and the CLT
contrast that shows Cauchy refusing to converge.

The cross-book consistency test now covers five books rather than four,
and gains two checks specific to the new lens: least squares must be the
lambda -> 0 end of the same ridge family the other books use (3.4e-09),
and the coefficient norms must show the shrinkage the capstone claims
(7.40 against 1.75). Without those, 'statistics agrees with the others'
would be a sentence in a README rather than something the suite enforces."
```

---

### Task 8: Plan 3 の仕上げ

**Files:**
- Modify: `analytics/statistics/README.md`
- Modify: `docs/superpowers/specs/2026-08-01-analytics-statistics-design.md`
- Modify: root `Makefile`（`report` ターゲットの `PYTHONPATH` に statistics が要るか確認）

- [ ] **Step 1: 全 14 章を頭から再実行し、章ごとの時間を測る**

```bash
cd analytics/statistics
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py
cd -
/home/kazumasa/projects/.venv/bin/python - <<'PY'
import subprocess, time, pathlib, os
env = dict(os.environ, PYTHONPATH="analytics/statistics/src")
PY_BIN = "/home/kazumasa/projects/.venv/bin/python"
total = 0.0
for nb in sorted(pathlib.Path("analytics/statistics/notebooks").glob("*.ipynb")):
    t0 = time.monotonic()
    r = subprocess.run([PY_BIN, "-m", "jupyter", "nbconvert", "--to", "notebook",
                        "--execute", "--inplace", str(nb)], env=env, capture_output=True)
    dt = time.monotonic() - t0
    assert r.returncode == 0, f"{nb.name}\n{r.stderr.decode()[-800:]}"
    total += dt
    print(f"{nb.name:<44} {dt:6.1f}s {nb.stat().st_size/1024:9.1f} KB")
print(f"{'合計':<44} {total:6.1f}s")
print(f"予算 300 秒に対して {'OK' if total < 300 else 'OVER'}")
PY
```

Expected: 14 章の合計が **300 秒以内**。

- [ ] **Step 2: 全テスト・lint・他書の非破壊確認**

```bash
/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics
/home/kazumasa/projects/.venv/bin/ruff format --check analytics/statistics
W=/home/kazumasa/projects/.claude/worktrees/analytics-statistics-plan3
PYTHONPATH=$W/analytics/linear_algebra/src:$W/analytics/neural_net/src:$W/analytics/bayesian/src:$W/analytics/machine_learning/src:$W/analytics/statistics/src \
  /home/kazumasa/projects/.venv/bin/python -m pytest analytics/ -q
```

Expected: すべて PASS。

- [ ] **Step 3: 本とポータルを通しでビルドし、HTML を走査する**

```bash
rm -rf analytics/statistics/book/_build
/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/
/home/kazumasa/projects/.venv/bin/python - <<'PY'
import re, html, pathlib
bad = 0
for f in sorted(pathlib.Path("analytics/statistics/book/_build/html/notebooks").glob("*.html")):
    s = f.read_text(encoding="utf-8")
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S)
    body = re.sub(r'<div class="highlight">.*?</div>', "", body, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "", body))
    hits = re.findall(r".{0,40}\*\*.{0,40}", text)
    if hits:
        bad += len(hits); print(f"{f.name}: {len(hits)}"); [print("   ", h.replace("\n"," ")) for h in hits[:3]]
print(f"literal ** in prose: {bad}")
PY
```

Expected: 14 章の HTML が生成され、`literal ** in prose: 0`。
`_build/html/index.html` から全 14 章を開き、新しい図（区間比較・事前分布の収束・事後分布・キャップストーン）が
動くこと、コールアウトが描画されていることを目視確認する。

- [ ] **Step 4: README を完成させる**

- 章構成の表で 11–13 を ✅ に変え、実測実行時間を入れる
- 実測値の段落を全 14 章のものに書き換える
- 共通コードの表に `bridge` と `plotting/bridge` を足す
- テスト数の内訳を実測値に更新する
- **「analytics ポータルとの統合」の節を新設**し、代表図 2 点と横断テストについて書く

- [ ] **Step 5: 設計書に Plan 3 の実測結果を記録し、本書の完成を宣言する**

§10 の表で Plan 3 を「完了」にし、Plan 1・2 と同形式の実測結果ブロックを足す。
さらに設計書の冒頭に **完成した旨と最終的な実測値**（章数・テスト数・図の点数・実行時間）を 1 段落で書く。

- [ ] **Step 6: commit**

```bash
git add analytics/statistics docs/ analytics/report
git commit -m "docs(statistics): the book is complete -- final measured numbers

Fourteen chapters, from the axioms of probability to a capstone that
solves one regression three ways. Records what the whole book costs to
rebuild rather than what it was budgeted, and what the portal now carries.

The spec's milestone table closes here: every plan it decomposed into is
done, and the numbers in it are measurements rather than targets."
```

---

## Plan 3 完了時の状態

| 項目 | 予定 |
|---|---|
| Notebook | **00–13 の全 14 章** |
| ソースモジュール | Plan 1–2 の 11 本 ＋ `bridge` ＋ `plotting/bridge` |
| テスト | 165 本前後（bridge 10・plotting_bridge 8・datasets +2・report +2） |
| インタラクティブ図 | 23 点前後 |
| コールアウト | 核心 13・実社会 13 |
| ポータル | `analytics/report` のギャラリーに 2 点、横断テストが 5 書に |

**本書の完成後に残る作業はない。** 設計書が定義した全 3 プランがここで閉じる。
