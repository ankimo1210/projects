# analytics/statistics Plan 2 — 推測のコア・第Ⅱ部 5 章・回帰と GLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 『統計的推測の風景』の第Ⅱ部前半を完成させる。推定・区間・検定・回帰・GLM のコア実装（`estimation` / `intervals` / `testing` / `regression` / `glm`）と NB06–10 を書き、本書の第 2 原則「すべての主張はシミュレーションで検算する」を実際に果たす。

**Architecture:** Plan 1 で作った `simulation` の 3 関数（`sampling_distribution` / `coverage_probability` / `rejection_rate`）を**拡張せずそのまま使う**。新モジュールは推定手続きと区間・p 値を提供し、その正しさは `simulation` を通した実測で示す。回帰と GLM は自前実装し、`statsmodels` を**照合先**として使う（教育用に中身を見せ、実務用の道具の使い方も示す二本立て）。

**Tech Stack:** Python 3.12・numpy・scipy・statsmodels 0.14・plotly・nbformat・jupyter-book・pytest

## Global Constraints

設計書 `docs/superpowers/specs/2026-08-01-analytics-statistics-design.md` の全体要件。**全タスクの要求に暗黙的に含まれる。**

- 本文は日本語、コード・コメント・識別子は英語、**LaTeX 内に日本語を入れない**
- 乱数は **seed 固定で再現可能**、**外部ダウンロード依存ゼロ**（データは全て合成）
- 可視化の主役は **静的 HTML でも動く Plotly**。`ipywidgets` は補助で、無くても全章が読める
- `plotting` は**純関数**（データ → `go.Figure`）。計算は計算モジュール側に置く
- モジュール依存は**一方向**: `distributions` → `estimation` → `intervals`/`testing` → `regression` → `glm`
- ノートブックの JSON は**手編集しない**。`tools/build_nbNN.py` が唯一の正本
- ノートブックは**出力込みでコミット**。ビルド時は再実行しない
- **CJK 約物に接する太字を書かない**。`nbkit.md` がレンダリングして検査し、駄目なら例外を投げる
- コールアウトは 💡 **核心**（class: tip）と 🌍 **実社会**（class: note）、章あたり各 1–2 個
- 新規依存は `statsmodels>=0.14` のみ。**Plan 2 の Task 8 以降でのみ import する**

## Plan 1 から引き継ぐ実測値と制約

| 項目 | 実測 |
|---|---|
| 現在のテスト数 | **65**（全て緑） |
| NB00–05 の再実行 | 28.3 秒 |
| **NB06–13 に使える残予算** | **271 秒 / 8 章**（1 章あたり平均 34 秒） |
| Notebook 総サイズ | 947 KB |

**Plan 1 で確立した規約（破ると既存テストが落ちる）**

- アニメーション図は `plotting.core.frame_slider(frames: list[go.Frame], slider_name: str) -> go.Figure` を通す。手書きのスライダー配線は `test_every_animated_figure_goes_through_frame_slider` が弾く
- `widgets` は図を自作しない・`.show()` を呼ばない。`test_widgets_do_not_reimplement_figures` と `test_widgets_never_call_figure_show` が守っている
- **図に生データを埋め込まない**。`go.Histogram` に反復ごとの値を渡すと 1 章が 2.8 MB になった。`np.histogram` で集計して `go.Bar` を描く

## 実行環境（最初に読むこと）

作業ディレクトリは **git worktree** `/home/kazumasa/projects/.claude/worktrees/analytics-statistics-plan2`（ブランチ `worktree-analytics-statistics-plan2`、`origin/main` の `1ea59dd4` から分岐）。

```bash
PY=/home/kazumasa/projects/.venv/bin/python      # 以後 $PY と書く
```

- **worktree 内で `uv run` を使ってはいけない。** `.venv` が無いので uv が新しい仮想環境を作り始める
- テスト: `$PY -m pytest analytics/statistics/tests -q`
- lint: `/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics` と `ruff format --check analytics/statistics`
  （リポジトリ全体の `make lint` は**既定でレッド**。自分の是非は `analytics/statistics` に絞って見る）
- ノートブック実行: `PYTHONPATH=analytics/statistics/src $PY -m jupyter nbconvert --to notebook --execute --inplace <nb>`
- 本のビルド: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
- `statsmodels 0.14.6` と `patsy 1.0.2` は **root の `.venv` に導入済み**（他パッケージは変更していない）
- root の `.venv` の editable install は他教材のソースを **main ツリー側**から読む。並行セッションがそこを編集していると無関係なテストが落ちて見える。検証は `analytics/statistics/tests` に限定する

## File Structure

| ファイル | 責務 | Task |
|---|---|---|
| `src/stats_textbook/estimation.py` | 推定量・MLE・Fisher 情報・Cramér–Rao | 1 |
| `src/stats_textbook/intervals.py` | ピボット/ブートストラップ/順列 | 2 |
| `src/stats_textbook/testing.py` | 検定統計量・検出力・多重比較 | 3 |
| `src/stats_textbook/plotting/inference.py` | 06–08 章の図 | 4 |
| `tools/build_nb06.py` … `build_nb08.py` | NB06–08 | 5–7 |
| `src/stats_textbook/regression.py` | OLS 推測・頑健 SE・診断量 | 8 |
| `src/stats_textbook/glm.py` | IRLS 自前実装・逸脱度 | 9 |
| `src/stats_textbook/plotting/regression.py` | 09–10 章の図 | 10 |
| `tools/build_nb09.py` / `build_nb10.py` | NB09–10 | 11–12 |
| `README.md` / 設計書 | 実測値の記録 | 13 |

`plotting/__init__.py` は Task 4 と Task 10 で再エクスポートを追加する。
`tools/build_notebooks.py` の `NOTEBOOKS` と `book/_toc.yml` は各章タスクで 1 行ずつ増やす。

---

### Task 1: `estimation.py` — 推定量・MLE・Fisher 情報

**Files:**
- Create: `analytics/statistics/src/stats_textbook/estimation.py`
- Test: `analytics/statistics/tests/test_estimation.py`

**Interfaces:**
- Consumes: `distributions.EXPONENTIAL_FAMILIES`（キー `"bernoulli"` `"poisson"` `"normal_unit_var"` `"exponential"`）、`distributions.exponential_family_logpdf(family, theta, x) -> np.ndarray`
- Produces:
  - `MLEResult` — frozen dataclass、フィールド `estimate: float` / `se: float` / `loglik: float` / `n: int`
  - `mle(family_name: str, x: np.ndarray) -> MLEResult`
  - `log_likelihood(family_name: str, theta: float, x: np.ndarray) -> float`
  - `expected_fisher_information(family_name: str, theta: float, n: int = 1) -> float`
  - `observed_information(loglik: Callable[[float], float], theta: float, h: float = 1e-5) -> float`
  - `cramer_rao_bound(family_name: str, theta: float, n: int) -> float`
  - `method_of_moments(family_name: str, x: np.ndarray) -> float`

> **この章の要点は「期待情報」と「観測情報」の区別である。** 実測で確認済み: ポアソン $n=50$・真値 $\lambda=2.5$ のとき、真値での観測情報は 18.12 だが期待情報 $n/\lambda$ は 20.00 でずれる。**MLE で評価すると両者は完全に一致する**（18.12 対 18.12）。テストはこの一致を固定する。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_estimation.py`:

```python
"""Estimators, likelihood, and the two kinds of Fisher information."""

import numpy as np
import pytest
from stats_textbook import estimation as est


def test_bernoulli_mle_is_the_sample_proportion():
    x = np.array([1, 0, 1, 1, 0, 1, 1, 0])
    r = est.mle("bernoulli", x)
    assert r.n == 8
    assert abs(r.estimate - x.mean()) < 1e-9


def test_poisson_mle_is_the_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.poisson(3.5, 500)
    assert abs(est.mle("poisson", x).estimate - x.mean()) < 1e-9


def test_normal_mle_is_the_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(1.2, 1.0, 500)
    assert abs(est.mle("normal_unit_var", x).estimate - x.mean()) < 1e-9


def test_exponential_mle_is_the_reciprocal_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.exponential(1 / 2.5, 500)
    assert abs(est.mle("exponential", x).estimate - 1.0 / x.mean()) < 1e-9


def test_mle_maximises_the_log_likelihood():
    rng = np.random.default_rng(1)
    x = rng.poisson(4.0, 200)
    hat = est.mle("poisson", x).estimate
    best = est.log_likelihood("poisson", hat, x)
    for theta in [hat * 0.8, hat * 0.9, hat * 1.1, hat * 1.25]:
        assert est.log_likelihood("poisson", theta, x) < best


def test_expected_fisher_information_matches_the_closed_forms():
    # Bernoulli: n / (p(1-p)); Poisson: n / lambda.
    assert abs(est.expected_fisher_information("bernoulli", 0.3, 80) - 80 / 0.21) < 1e-9
    assert abs(est.expected_fisher_information("poisson", 2.5, 50) - 20.0) < 1e-9
    # Normal with unit variance: n.
    assert abs(est.expected_fisher_information("normal_unit_var", 1.7, 40) - 40.0) < 1e-9


def test_observed_and_expected_information_agree_at_the_mle_and_not_at_the_truth():
    """The chapter's point: which theta you evaluate at matters."""
    rng = np.random.default_rng(1)
    lam, n = 2.5, 50
    x = rng.poisson(lam, n)
    hat = est.mle("poisson", x).estimate

    def ll(theta):
        return est.log_likelihood("poisson", theta, x)

    at_mle = est.observed_information(ll, hat)
    assert abs(at_mle - est.expected_fisher_information("poisson", hat, n)) / at_mle < 1e-4
    # At the true parameter the two part company (the sample mean is not lambda).
    at_truth = est.observed_information(ll, lam)
    assert abs(at_truth - est.expected_fisher_information("poisson", lam, n)) > 1.0


def test_cramer_rao_bound_is_attained_by_the_mle_of_a_poisson_mean():
    """For an exponential family the MLE's asymptotic variance is the bound."""
    from stats_textbook import simulation as sim

    lam, n = 3.0, 200

    def sampler(m, rng):
        return rng.poisson(lam, m).astype(float)

    hats = sim.sampling_distribution(
        lambda s: est.mle("poisson", s).estimate, sampler, n=n, n_reps=4000, seed=2
    )
    bound = est.cramer_rao_bound("poisson", lam, n)
    assert abs(hats.var() / bound - 1.0) < 0.06, f"var {hats.var():.5f} vs bound {bound:.5f}"


def test_standard_error_uses_the_information_at_the_mle():
    rng = np.random.default_rng(3)
    x = rng.poisson(4.0, 250)
    r = est.mle("poisson", x)
    assert abs(r.se - np.sqrt(r.estimate / 250)) < 1e-9


def test_method_of_moments_agrees_with_the_mle_for_these_families():
    rng = np.random.default_rng(4)
    x = rng.poisson(3.0, 400)
    assert abs(est.method_of_moments("poisson", x) - est.mle("poisson", x).estimate) < 1e-9


def test_unknown_family_is_rejected():
    with pytest.raises(KeyError, match="cauchy"):
        est.mle("cauchy", np.array([1.0, 2.0]))
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_estimation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.estimation'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/estimation.py`:

```python
"""Point estimation: maximum likelihood, Fisher information, Cramer-Rao.

Written for the four exponential families of ``distributions``. Their MLEs
are available in closed form, which lets the notebook compare an analytic
answer against a numerical one and see them agree -- the numerical route is
what generalises, the closed form is what makes it checkable.

The module distinguishes *expected* Fisher information (an average over
hypothetical data at a given theta) from *observed* information (the
curvature of this sample's own log-likelihood). They coincide at the MLE
for these families and part company anywhere else, which is a distinction
NB06 makes concrete rather than glossing over.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .distributions import EXPONENTIAL_FAMILIES, exponential_family_logpdf

__all__ = [
    "MLEResult",
    "cramer_rao_bound",
    "expected_fisher_information",
    "log_likelihood",
    "method_of_moments",
    "mle",
    "observed_information",
]


@dataclass(frozen=True)
class MLEResult:
    """A maximum-likelihood estimate with its asymptotic standard error."""

    estimate: float
    se: float
    loglik: float
    n: int


def _check_family(name: str) -> None:
    if name not in EXPONENTIAL_FAMILIES:
        raise KeyError(
            f"unknown family {name!r}; expected one of {sorted(EXPONENTIAL_FAMILIES)}"
        )


def log_likelihood(family_name: str, theta: float, x: np.ndarray) -> float:
    """Total log-likelihood of ``x`` under the family at ``theta``."""
    _check_family(family_name)
    return float(
        exponential_family_logpdf(EXPONENTIAL_FAMILIES[family_name], theta, np.asarray(x)).sum()
    )


def method_of_moments(family_name: str, x: np.ndarray) -> float:
    """Match the first moment. For these four families this equals the MLE."""
    _check_family(family_name)
    m = float(np.mean(x))
    if family_name == "exponential":
        return 1.0 / m
    return m


def mle(family_name: str, x: np.ndarray) -> MLEResult:
    """The closed-form maximum-likelihood estimate.

    Every one of these families has the sample mean (or its reciprocal) as
    the MLE, because the sufficient statistic is the sum -- see NB03.
    """
    _check_family(family_name)
    x = np.asarray(x, dtype=float)
    theta_hat = method_of_moments(family_name, x)
    n = x.size
    info = expected_fisher_information(family_name, theta_hat, n)
    return MLEResult(
        estimate=theta_hat,
        se=1.0 / math.sqrt(info),
        loglik=log_likelihood(family_name, theta_hat, x),
        n=n,
    )


def expected_fisher_information(family_name: str, theta: float, n: int = 1) -> float:
    """I(theta) for one observation, times ``n``.

    Closed forms; each is the second derivative of the log-partition
    function pulled back to the original parameter.
    """
    _check_family(family_name)
    if family_name == "bernoulli":
        unit = 1.0 / (theta * (1.0 - theta))
    elif family_name == "poisson":
        unit = 1.0 / theta
    elif family_name == "normal_unit_var":
        unit = 1.0
    else:  # exponential, rate parameterisation
        unit = 1.0 / theta**2
    return n * unit


def observed_information(
    loglik: Callable[[float], float], theta: float, h: float = 1e-5
) -> float:
    """-d^2/dtheta^2 of this sample's log-likelihood, by central difference.

    This is what an estimator actually has access to: the curvature of the
    likelihood it was handed, not an average over data it never saw.
    """
    return -(loglik(theta + h) - 2.0 * loglik(theta) + loglik(theta - h)) / h**2


def cramer_rao_bound(family_name: str, theta: float, n: int) -> float:
    """The smallest variance any unbiased estimator of ``theta`` can have."""
    return 1.0 / expected_fisher_information(family_name, theta, n)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_estimation.py -q`
Expected: PASS 11 件

> `test_cramer_rao_bound_is_attained_by_the_mle_of_a_poisson_mean` は 4000 反復での分散比を 6% の許容で見る。落ちた場合は許容を緩めるのではなく **`n_reps` を 10000 に上げる**こと（主張は正しく、精度が足りないだけ）。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/estimation.py analytics/statistics/tests/test_estimation.py
git commit -m "feat(statistics): maximum likelihood and Fisher information

Separates expected from observed information rather than treating them as
one quantity. They agree at the MLE for these families and disagree at the
true parameter -- a Poisson sample of 50 at lambda 2.5 gives 18.12 observed
against 20.00 expected -- and a test pins both halves of that.

The Cramer-Rao bound is checked the book's way: simulate 4000 MLEs and
compare their variance to the bound rather than asserting attainment."
```

---

### Task 2: `intervals.py` — 区間推定とリサンプリング

**Files:**
- Create: `analytics/statistics/src/stats_textbook/intervals.py`
- Test: `analytics/statistics/tests/test_intervals.py`

**Interfaces:**
- Consumes: `estimation.MLEResult`（`test` でのみ）、`simulation.coverage_probability`
- Produces:
  - `Interval` — frozen dataclass、フィールド `lo: float` / `hi: float`、メソッド `contains(value: float) -> bool` / `width() -> float`
  - `t_interval(sample: np.ndarray, level: float = 0.95) -> Interval`
  - `wald_interval(estimate: float, se: float, level: float = 0.95) -> Interval`
  - `bootstrap_interval(sample: np.ndarray, statistic: Callable[[np.ndarray], float], method: str = "percentile", n_boot: int = 2000, level: float = 0.95, seed: int = 0) -> Interval`（`method` は `"percentile"` / `"bca"`）
  - `permutation_test(x: np.ndarray, y: np.ndarray, statistic: Callable[[np.ndarray, np.ndarray], float] | None = None, n_perm: int = 5000, seed: int = 0) -> float`（両側 p 値を返す）

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_intervals.py`:

```python
"""Interval estimation, and what "95%" is actually a claim about."""

import numpy as np
import pytest
from stats_textbook import intervals as iv
from stats_textbook import simulation as sim


def test_interval_reports_containment_and_width():
    i = iv.Interval(lo=-1.0, hi=2.0)
    assert i.contains(0.0) and not i.contains(3.0)
    assert abs(i.width() - 3.0) < 1e-12


def test_t_interval_matches_the_textbook_formula():
    from scipy import stats

    x = np.array([2.1, 1.8, 2.6, 2.0, 2.4, 1.9])
    got = iv.t_interval(x)
    half = stats.t.ppf(0.975, x.size - 1) * x.std(ddof=1) / np.sqrt(x.size)
    assert abs(got.lo - (x.mean() - half)) < 1e-12
    assert abs(got.hi - (x.mean() + half)) < 1e-12


def test_wald_interval_uses_the_normal_quantile():
    got = iv.wald_interval(estimate=10.0, se=2.0, level=0.95)
    assert abs(got.width() - 2 * 1.959963984540054 * 2.0) < 1e-9


def test_t_interval_covers_at_its_nominal_rate():
    def sampler(n, rng):
        return rng.normal(0.0, 1.0, n)

    r = sim.coverage_probability(
        sampler, lambda s: tuple(iv.t_interval(s)), truth=0.0, n=12, n_reps=4000, seed=1
    )
    lo, hi = r.ci95()
    assert lo <= 0.95 <= hi, f"nominal 95% outside the Monte-Carlo CI {(lo, hi)}"


def test_bootstrap_percentile_interval_covers_a_median():
    """The median has no simple standard error -- this is what bootstrap is for."""

    def sampler(n, rng):
        return rng.exponential(1.0, n)

    truth = float(np.log(2.0))  # median of Exponential(1)

    def interval(s):
        return tuple(iv.bootstrap_interval(s, np.median, method="percentile", n_boot=400, seed=0))

    r = sim.coverage_probability(sampler, interval, truth=truth, n=60, n_reps=400, seed=5)
    assert 0.88 <= r.estimate <= 0.99, f"coverage {r.estimate}"


def test_bca_beats_percentile_on_a_skewed_statistic():
    """BCa corrects for bias and skew; on a variance of skewed data it should
    not be worse than the plain percentile interval."""

    def sampler(n, rng):
        return rng.exponential(1.0, n)

    truth = 1.0  # variance of Exponential(1)
    out = {}
    for method in ["percentile", "bca"]:

        def interval(s, _m=method):
            return tuple(
                iv.bootstrap_interval(s, lambda a: a.var(ddof=1), method=_m, n_boot=400, seed=0)
            )

        out[method] = sim.coverage_probability(
            sampler, interval, truth=truth, n=40, n_reps=300, seed=6
        ).estimate
    assert out["bca"] >= out["percentile"] - 0.02, out


def test_bootstrap_rejects_an_unknown_method():
    with pytest.raises(ValueError, match="method"):
        iv.bootstrap_interval(np.arange(10.0), np.mean, method="studentized")


def test_bootstrap_is_deterministic():
    x = np.arange(1.0, 21.0)
    a = iv.bootstrap_interval(x, np.mean, n_boot=200, seed=7)
    b = iv.bootstrap_interval(x, np.mean, n_boot=200, seed=7)
    assert a == b


def test_permutation_test_finds_a_real_shift_and_not_a_fake_one():
    rng = np.random.default_rng(8)
    same_a, same_b = rng.normal(0, 1, 60), rng.normal(0, 1, 60)
    diff_a, diff_b = rng.normal(0, 1, 60), rng.normal(1.2, 1, 60)
    assert iv.permutation_test(same_a, same_b, n_perm=2000, seed=0) > 0.1
    assert iv.permutation_test(diff_a, diff_b, n_perm=2000, seed=0) < 0.01


def test_permutation_pvalue_is_uniform_under_the_null():
    """A valid p-value rejects at exactly alpha when nothing is going on."""

    def sampler(n, rng):
        return rng.normal(0.0, 1.0, 2 * n)

    def pvalue(s):
        half = s.size // 2
        return iv.permutation_test(s[:half], s[half:], n_perm=400, seed=0)

    r = sim.rejection_rate(sampler, pvalue, alpha=0.1, n=25, n_reps=600, seed=9)
    lo, hi = r.ci95()
    assert lo <= 0.10 <= hi, f"nominal alpha outside {(lo, hi)}"
```

> `Interval` を `tuple(...)` に渡せるようにするため、`Interval` は **iterable** でなければならない。`__iter__` を定義すること（`simulation.coverage_probability` は `(lo, hi)` のタプルを期待する）。

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_intervals.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.intervals'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/intervals.py`:

```python
"""Interval estimation -- and what the number in front of the % sign means.

A 95% interval is not a statement about this interval. It is a statement
about the procedure: repeat the experiment and 95% of the intervals it
produces will contain the truth. That claim is measurable, and NB07
measures it with ``simulation.coverage_probability`` rather than trusting
the derivation.

The bootstrap earns its place where no closed form exists (a median, a
ratio, a trimmed mean). BCa is included because the plain percentile
interval is visibly wrong on skewed statistics, and seeing the correction
work is more convincing than being told it exists.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "Interval",
    "bootstrap_interval",
    "permutation_test",
    "t_interval",
    "wald_interval",
]

_METHODS = ("percentile", "bca")


@dataclass(frozen=True)
class Interval:
    """A closed interval. Iterable so it can be unpacked as ``(lo, hi)``."""

    lo: float
    hi: float

    def __iter__(self) -> Iterator[float]:
        yield self.lo
        yield self.hi

    def contains(self, value: float) -> bool:
        return self.lo <= value <= self.hi

    def width(self) -> float:
        return self.hi - self.lo


def t_interval(sample: np.ndarray, level: float = 0.95) -> Interval:
    """The Student t interval for a mean, using the sample standard deviation."""
    sample = np.asarray(sample, dtype=float)
    n = sample.size
    half = stats.t.ppf(0.5 + level / 2.0, n - 1) * sample.std(ddof=1) / np.sqrt(n)
    return Interval(float(sample.mean() - half), float(sample.mean() + half))


def wald_interval(estimate: float, se: float, level: float = 0.95) -> Interval:
    """estimate +- z * se. Valid only when the estimator is near-normal."""
    z = stats.norm.ppf(0.5 + level / 2.0)
    return Interval(estimate - z * se, estimate + z * se)


def _resample(sample: np.ndarray, statistic, n_boot: int, rng) -> np.ndarray:
    idx = rng.integers(0, sample.size, size=(n_boot, sample.size))
    return np.array([float(statistic(sample[i])) for i in idx])


def bootstrap_interval(
    sample: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    method: str = "percentile",
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> Interval:
    """Resample the data to get an interval for any statistic.

    ``percentile`` takes the empirical quantiles of the bootstrap
    distribution. ``bca`` shifts them to correct for bias (is the statistic
    systematically off-centre?) and acceleration (does its variance change
    with the parameter?), which matters for skewed statistics.
    """
    if method not in _METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {_METHODS}")
    sample = np.asarray(sample, dtype=float)
    rng = np.random.default_rng(seed)
    boot = _resample(sample, statistic, n_boot, rng)
    alpha = 1.0 - level

    if method == "percentile":
        lo, hi = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
        return Interval(float(lo), float(hi))

    theta_hat = float(statistic(sample))
    # Bias correction: where the observed statistic sits in the bootstrap law.
    prop = float(np.mean(boot < theta_hat))
    prop = min(max(prop, 1.0 / (2 * n_boot)), 1.0 - 1.0 / (2 * n_boot))
    z0 = stats.norm.ppf(prop)
    # Acceleration from the jackknife's third moment.
    jack = np.array(
        [float(statistic(np.delete(sample, i))) for i in range(sample.size)]
    )
    d = jack.mean() - jack
    denom = 6.0 * (np.sum(d**2) ** 1.5)
    a = float(np.sum(d**3) / denom) if denom > 0 else 0.0

    def adjust(q: float) -> float:
        z = stats.norm.ppf(q)
        return float(stats.norm.cdf(z0 + (z0 + z) / (1.0 - a * (z0 + z))))

    lo, hi = np.quantile(boot, [adjust(alpha / 2.0), adjust(1.0 - alpha / 2.0)])
    return Interval(float(lo), float(hi))


def _mean_difference(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(x) - np.mean(y))


def permutation_test(
    x: np.ndarray,
    y: np.ndarray,
    statistic: Callable[[np.ndarray, np.ndarray], float] | None = None,
    n_perm: int = 5000,
    seed: int = 0,
) -> float:
    """Two-sided p-value from shuffling the group labels.

    Assumes only exchangeability under the null -- no distributional model
    at all, which is why it works where a t test's assumptions do not.
    """
    statistic = statistic or _mean_difference
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    observed = abs(statistic(x, y))
    pooled = np.concatenate([x, y])
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        if abs(statistic(pooled[: x.size], pooled[x.size :])) >= observed:
            count += 1
    # Add-one correction: a permutation p-value is never exactly zero.
    return (count + 1) / (n_perm + 1)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_intervals.py -q`
Expected: PASS 10 件。実行に 30–60 秒かかる（ブートストラップの被覆実験が重い）。

> `test_bca_beats_percentile_on_a_skewed_statistic` は「BCa が percentile より 2 ポイント以上悪くない」という緩い主張にしてある。**BCa が常に勝つとは限らない**ので、勝敗を断定する形に強めないこと。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/intervals.py analytics/statistics/tests/test_intervals.py
git commit -m "feat(statistics): confidence intervals, bootstrap, permutation

Interval is iterable so it drops straight into coverage_probability, which
is how every interval here is judged: the t interval must cover at its
nominal rate, and the bootstrap must cover a median that has no closed-form
standard error.

The permutation test is checked from the other direction too -- its
p-value must reject at exactly alpha under the null, which is the property
that makes a p-value a p-value."
```

---

### Task 3: `testing.py` — 検定・検出力・多重比較

**Files:**
- Create: `analytics/statistics/src/stats_textbook/testing.py`
- Test: `analytics/statistics/tests/test_testing.py`

**Interfaces:**
- Consumes: なし（`scipy.stats` のみ）
- Produces:
  - `TestResult` — frozen dataclass、フィールド `statistic: float` / `pvalue: float` / `df: float | None`
  - `t_test(sample: np.ndarray, mu0: float = 0.0) -> TestResult`
  - `two_sample_t_test(x: np.ndarray, y: np.ndarray, equal_var: bool = False) -> TestResult`
  - `power_t_test(effect: float, n: int, alpha: float = 0.05) -> float`（片標本、非心 t による厳密値）
  - `required_n(effect: float, alpha: float = 0.05, power: float = 0.8, n_max: int = 10_000) -> int`
  - `bonferroni(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray`（bool 配列）
  - `benjamini_hochberg(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray`（bool 配列）
  - `false_discovery_proportion(rejected: np.ndarray, is_null: np.ndarray) -> float`

> **多重比較の照合先は `statsmodels.stats.multitest.multipletests`。** 実測済みの参照値: p 値 `[0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]`、$\alpha = 0.05$ で **Bonferroni は 1 件、BH は 2 件**棄却する。
> ただし `testing.py` は `statsmodels` を **import しない**（依存の向きを保つ）。照合はテスト側で行う。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_testing.py`:

```python
"""Hypothesis tests: their size, their power, and what multiplicity does."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import simulation as sim
from stats_textbook import testing as tst

# Measured reference: Bonferroni rejects 1, BH rejects 2 at alpha = 0.05.
PVALS = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216])


def test_one_sample_t_test_matches_scipy():
    rng = np.random.default_rng(0)
    x = rng.normal(0.4, 1.0, 30)
    got = tst.t_test(x, mu0=0.0)
    ref = stats.ttest_1samp(x, 0.0)
    assert abs(got.statistic - ref.statistic) < 1e-12
    assert abs(got.pvalue - ref.pvalue) < 1e-12
    assert got.df == 29


def test_two_sample_welch_test_matches_scipy():
    rng = np.random.default_rng(1)
    x, y = rng.normal(0, 1, 25), rng.normal(0.8, 2.0, 40)
    got = tst.two_sample_t_test(x, y, equal_var=False)
    ref = stats.ttest_ind(x, y, equal_var=False)
    assert abs(got.statistic - ref.statistic) < 1e-12
    assert abs(got.pvalue - ref.pvalue) < 1e-12


def test_the_test_rejects_at_exactly_alpha_under_the_null():
    r = sim.rejection_rate(
        lambda n, rng: rng.normal(0.0, 1.0, n),
        lambda s: tst.t_test(s).pvalue,
        alpha=0.05,
        n=20,
        n_reps=4000,
        seed=2,
    )
    lo, hi = r.ci95()
    assert lo <= 0.05 <= hi, f"size {r.estimate} with CI {(lo, hi)}"


def test_analytic_power_matches_simulated_power():
    """The non-central t formula must agree with actually running the test."""
    effect, n = 0.6, 25
    analytic = tst.power_t_test(effect, n, alpha=0.05)
    simulated = sim.rejection_rate(
        lambda m, rng: rng.normal(effect, 1.0, m),
        lambda s: tst.t_test(s).pvalue,
        alpha=0.05,
        n=n,
        n_reps=4000,
        seed=3,
    )
    lo, hi = simulated.ci95()
    assert lo <= analytic <= hi, f"analytic {analytic:.4f} vs simulated {(lo, hi)}"


def test_power_rises_with_effect_and_sample_size():
    assert tst.power_t_test(0.2, 25) < tst.power_t_test(0.8, 25)
    assert tst.power_t_test(0.5, 10) < tst.power_t_test(0.5, 100)
    assert abs(tst.power_t_test(0.0, 50) - 0.05) < 1e-9, "at zero effect power is alpha"


def test_required_n_reaches_the_requested_power():
    # Measured: 34 for effect 0.5, 199 for 0.2, 15 for 0.8.
    n = tst.required_n(effect=0.5, alpha=0.05, power=0.8)
    assert n == 34, f"got {n}"
    assert tst.power_t_test(0.5, n) >= 0.8
    assert tst.power_t_test(0.5, n - 1) < 0.8, "must be the smallest such n"


def test_power_stays_finite_where_scipys_nct_overflows():
    """nct returns nan at large non-centrality; power there is 1, not nan."""
    for n in [500, 3000, 5000]:
        p = tst.power_t_test(0.5, n)
        assert np.isfinite(p) and p > 0.999, f"n={n} gave {p}"


def test_bonferroni_and_bh_match_statsmodels():
    from statsmodels.stats.multitest import multipletests

    for method, fn in [("bonferroni", tst.bonferroni), ("fdr_bh", tst.benjamini_hochberg)]:
        ref = multipletests(PVALS, alpha=0.05, method=method)[0]
        np.testing.assert_array_equal(fn(PVALS, alpha=0.05), ref)


def test_bh_rejects_more_than_bonferroni():
    assert tst.benjamini_hochberg(PVALS).sum() > tst.bonferroni(PVALS).sum()


def test_uncorrected_testing_produces_false_positives_in_bulk():
    """The p-hacking demonstration NB08 is built on."""
    rng = np.random.default_rng(4)
    n_tests = 200
    pvals = np.array([tst.t_test(rng.normal(0, 1, 30)).pvalue for _ in range(n_tests)])
    raw = (pvals < 0.05).sum()
    assert raw >= 5, "about 5% of pure noise should look significant"
    assert tst.bonferroni(pvals).sum() == 0
    assert tst.benjamini_hochberg(pvals).sum() == 0


def test_false_discovery_proportion_counts_only_true_nulls():
    rejected = np.array([True, True, True, False])
    is_null = np.array([True, False, False, True])
    assert abs(tst.false_discovery_proportion(rejected, is_null) - 1 / 3) < 1e-12
    assert tst.false_discovery_proportion(np.zeros(4, bool), is_null) == 0.0


def test_bh_controls_the_false_discovery_rate():
    """Average FDP over many experiments must stay under alpha."""
    rng = np.random.default_rng(5)
    fdps = []
    for _ in range(200):
        # 180 nulls, 20 real effects.
        null_p = rng.uniform(0, 1, 180)
        alt_p = np.array([tst.t_test(rng.normal(1.0, 1.0, 20)).pvalue for _ in range(20)])
        pvals = np.concatenate([null_p, alt_p])
        is_null = np.concatenate([np.ones(180, bool), np.zeros(20, bool)])
        fdps.append(tst.false_discovery_proportion(tst.benjamini_hochberg(pvals, 0.1), is_null))
    assert np.mean(fdps) <= 0.10 + 0.02, f"mean FDP {np.mean(fdps):.4f}"


def test_multiple_testing_rejects_bad_alpha():
    with pytest.raises(ValueError, match="alpha"):
        tst.benjamini_hochberg(PVALS, alpha=1.5)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_testing.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.testing'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/testing.py`:

```python
"""Hypothesis testing: size, power, and the price of asking many questions.

A test is a rule that maps data to reject/don't-reject. Everything the
theory says about it is a long-run frequency claim -- the type-I error
rate, the power -- and every one of them is measured here through
``simulation.rejection_rate`` rather than taken on faith.

Multiple testing gets its own section because the failure is quantitative,
not conceptual: run 200 tests on pure noise and about 10 come back
significant. Bonferroni and Benjamini-Hochberg are two different answers
to that, controlling two different things.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "TestResult",
    "benjamini_hochberg",
    "bonferroni",
    "false_discovery_proportion",
    "power_t_test",
    "required_n",
    "t_test",
    "two_sample_t_test",
]


@dataclass(frozen=True)
class TestResult:
    """A test statistic with its two-sided p-value."""

    statistic: float
    pvalue: float
    df: float | None = None


def t_test(sample: np.ndarray, mu0: float = 0.0) -> TestResult:
    """One-sample Student t test of ``mean == mu0``."""
    sample = np.asarray(sample, dtype=float)
    n = sample.size
    se = sample.std(ddof=1) / np.sqrt(n)
    t = (sample.mean() - mu0) / se
    return TestResult(float(t), float(2.0 * stats.t.sf(abs(t), n - 1)), float(n - 1))


def two_sample_t_test(x: np.ndarray, y: np.ndarray, equal_var: bool = False) -> TestResult:
    """Two-sample t test; Welch's version by default (unequal variances)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    nx, ny = x.size, y.size
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    if equal_var:
        pooled = ((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2)
        se = np.sqrt(pooled * (1.0 / nx + 1.0 / ny))
        df = float(nx + ny - 2)
    else:
        se = np.sqrt(vx / nx + vy / ny)
        df = float(
            (vx / nx + vy / ny) ** 2
            / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
        )
    t = (x.mean() - y.mean()) / se
    return TestResult(float(t), float(2.0 * stats.t.sf(abs(t), df)), df)


def power_t_test(effect: float, n: int, alpha: float = 0.05) -> float:
    """Probability of rejecting when the true standardised effect is ``effect``.

    Exact, via the non-central t distribution -- not the normal
    approximation, which is optimistic at small n.
    """
    crit = stats.t.ppf(1.0 - alpha / 2.0, n - 1)
    ncp = effect * math.sqrt(n)
    value = stats.nct.sf(crit, n - 1, ncp) + stats.nct.cdf(-crit, n - 1, ncp)
    if not math.isfinite(value):
        # scipy's nct overflows to nan at large non-centrality (measured: nan
        # at n=500 and n=3000 for effect 0.5). That is exactly the regime
        # where the normal approximation is accurate, so fall back to it --
        # leaving the nan in place made required_n's binary search walk past
        # the answer and return 5880 instead of 34.
        return float(stats.norm.cdf(ncp - stats.norm.ppf(1.0 - alpha / 2.0)))
    return float(value)


def required_n(
    effect: float, alpha: float = 0.05, power: float = 0.8, n_max: int = 10_000
) -> int:
    """Smallest n whose power reaches ``power``. Searched, not approximated."""
    lo, hi = 2, n_max
    if power_t_test(effect, hi, alpha) < power:
        raise ValueError(f"power {power} unreachable by n={n_max} at effect {effect}")
    while lo < hi:
        mid = (lo + hi) // 2
        if power_t_test(effect, mid, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly inside (0, 1); got {alpha}")


def bonferroni(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Control the probability of *any* false rejection (family-wise error).

    Conservative by construction: with 200 tests every p-value must beat
    0.00025 to survive.
    """
    _check_alpha(alpha)
    p = np.asarray(pvalues, dtype=float)
    return p <= alpha / p.size


def benjamini_hochberg(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Control the expected *proportion* of rejections that are false (FDR).

    A weaker guarantee than Bonferroni's and therefore a stronger test: it
    tolerates some false discoveries as long as they stay a small share of
    the discoveries made.
    """
    _check_alpha(alpha)
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    below = ranked <= alpha * np.arange(1, m + 1) / m
    rejected = np.zeros(m, dtype=bool)
    if below.any():
        # Reject everything up to the largest index that clears the line.
        cutoff = int(np.max(np.nonzero(below)[0]))
        rejected[order[: cutoff + 1]] = True
    return rejected


def false_discovery_proportion(rejected: np.ndarray, is_null: np.ndarray) -> float:
    """Share of the rejections that were true nulls. Zero if nothing rejected."""
    rejected = np.asarray(rejected, dtype=bool)
    if not rejected.any():
        return 0.0
    return float(np.sum(rejected & np.asarray(is_null, dtype=bool)) / rejected.sum())
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_testing.py -q`
Expected: PASS 13 件

> **`scipy.stats.nct` の nan に注意。** 実測で `effect=0.5` の場合、$n = 500, 3000, 5000$ で `nct` が nan を返す（$n = 1000, 2000$ では返さない — 単調ではない）。素朴に実装すると `required_n(0.5)` の二分探索が nan を踏んで **34 ではなく 5880** を返す。正規近似へのフォールバックを必ず入れること。`test_power_stays_finite_where_scipys_nct_overflows` がこれを固定する。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/testing.py analytics/statistics/tests/test_testing.py
git commit -m "feat(statistics): hypothesis tests, power, multiple comparisons

Power is computed exactly from the non-central t and then checked against
actually running the test 4000 times -- the analytic number has to land
inside the simulation's own confidence interval, which is a real
constraint rather than a smoke test.

Bonferroni and Benjamini-Hochberg are matched against statsmodels, and BH
is additionally held to the thing it actually promises: the mean false
discovery proportion over 200 experiments must stay under alpha.
testing.py itself imports no statsmodels -- the comparison lives in the
test, so the module's dependency direction stays clean."
```

---

### Task 4: `plotting/inference.py` — 06–08 章の図

**Files:**
- Create: `analytics/statistics/src/stats_textbook/plotting/inference.py`
- Modify: `analytics/statistics/src/stats_textbook/plotting/__init__.py`
- Test: `analytics/statistics/tests/test_plotting_inference.py`

**Interfaces:**
- Consumes: `plotting.core.apply_defaults` / `frame_slider` / `curve_slider`、`estimation.log_likelihood` / `mle` / `cramer_rao_bound`、`intervals.t_interval` / `Interval`、`testing.power_t_test` / `benjamini_hochberg` / `bonferroni`、`simulation.sampling_distribution`
- Produces（全て `go.Figure` を返す純関数。`plotting/__init__.py` から再エクスポート）:
  - `likelihood_curve(family_name: str, x: np.ndarray, grid: Sequence[float] | None = None) -> Figure`
  - `mle_sampling_distribution(family_name: str, theta: float, ns: Sequence[int], n_reps: int = 3000, seed: int = 0) -> Figure`
  - `coverage_intervals(n_intervals: int = 100, n: int = 12, truth: float = 0.0, seed: int = 0) -> Figure` — **本書の看板図の 1 つ**
  - `bootstrap_distribution(sample: np.ndarray, statistic, n_boot: int = 2000, seed: int = 0) -> Figure`
  - `power_curves(effects: Sequence[float], ns: Sequence[int], alpha: float = 0.05) -> Figure`
  - `phacking_demo(n_tests: int = 200, n: int = 30, seed: int = 0) -> Figure` — **看板図の 1 つ**

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_plotting_inference.py`:

```python
"""Figures for Part II chapters 06-08: structure only."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_likelihood_curve_peaks_at_the_mle():
    from stats_textbook import estimation as est

    rng = np.random.default_rng(0)
    x = rng.poisson(3.0, 100)
    fig = plotting.likelihood_curve("poisson", x)
    curve = fig.data[0]
    peak = float(np.asarray(curve.x)[int(np.argmax(np.asarray(curve.y)))])
    assert abs(peak - est.mle("poisson", x).estimate) < 0.05


def test_mle_sampling_distribution_has_one_frame_per_n():
    fig = plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 50, 200], n_reps=500)
    assert len(fig.frames) == 3
    assert fig.layout.sliders[0].currentvalue.prefix == "n = "


def test_coverage_intervals_draws_the_requested_count_and_marks_misses():
    fig = plotting.coverage_intervals(n_intervals=100, n=12, truth=0.0, seed=0)
    # One trace for hits, one for misses, one for the truth line.
    names = [tr.name for tr in fig.data if tr.name]
    assert any("含む" in n for n in names)
    assert any("外す" in n for n in names)
    # The title must state the measured hit count, not a nominal 95.
    assert "/100" in (fig.layout.title.text or "")


def test_coverage_intervals_hit_count_is_near_the_nominal_rate():
    fig = plotting.coverage_intervals(n_intervals=200, n=12, truth=0.0, seed=1)
    title = fig.layout.title.text
    hits = int(title.split("/")[0].split()[-1])
    assert 175 <= hits <= 199, f"got {hits}/200"


def test_bootstrap_distribution_marks_the_observed_statistic():
    rng = np.random.default_rng(2)
    fig = plotting.bootstrap_distribution(rng.exponential(1.0, 60), np.median, n_boot=400)
    assert any(tr.type == "bar" for tr in fig.data)
    assert len(fig.layout.shapes) >= 1, "the observed value needs a marker line"


def test_power_curves_are_monotone_in_n():
    fig = plotting.power_curves(effects=[0.2, 0.5, 0.8], ns=[10, 20, 40, 80], alpha=0.05)
    for tr in fig.data:
        y = np.asarray(tr.y, dtype=float)
        assert np.all(np.diff(y) >= -1e-9), f"{tr.name} is not increasing in n"


def test_phacking_demo_separates_raw_from_corrected():
    fig = plotting.phacking_demo(n_tests=200, n=30, seed=0)
    names = [tr.name for tr in fig.data if tr.name]
    assert len(names) >= 2
    assert any("補正なし" in n for n in names)


def test_every_inference_figure_goes_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import inference

    src = inspect.getsource(inference)
    assert '"method": "animate"' not in src, "build frames and call frame_slider instead"


def test_inference_figures_ship_counts_not_raw_samples():
    """Same rule as Part I: histograms would serialise every replicate."""
    import inspect

    from stats_textbook.plotting import inference

    assert "go.Histogram(" not in inspect.getsource(inference)


def test_all_inference_figures_are_plotly_figures():
    rng = np.random.default_rng(3)
    figs = [
        plotting.likelihood_curve("poisson", rng.poisson(3.0, 50)),
        plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 40], n_reps=300),
        plotting.coverage_intervals(n_intervals=30, n=10, seed=0),
        plotting.bootstrap_distribution(rng.exponential(1.0, 40), np.mean, n_boot=200),
        plotting.power_curves([0.5], [10, 20]),
        plotting.phacking_demo(n_tests=50, n=20, seed=0),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting_inference.py -q`
Expected: FAIL — `AttributeError: module 'stats_textbook.plotting' has no attribute 'likelihood_curve'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/plotting/inference.py`:

```python
"""Figures for Part II (chapters 06-08).

Same rules as ``probability``: pure functions from data to a ``go.Figure``,
frames assembled here and animated through ``core.frame_slider``, and bin
counts rather than raw samples in anything histogram-shaped.

``coverage_intervals`` is the chapter-07 flagship. It draws the intervals
themselves and states the *measured* hit count in the title, so the figure
reports what happened rather than what was promised.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import plotly.graph_objects as go

from .. import estimation, intervals, simulation, testing
from .core import apply_defaults, frame_slider

__all__ = [
    "bootstrap_distribution",
    "coverage_intervals",
    "likelihood_curve",
    "mle_sampling_distribution",
    "phacking_demo",
    "power_curves",
]

_BINS = 50


def _density_bars(values: np.ndarray, name: str, lo: float, hi: float) -> go.Bar:
    """Bin here so the figure carries counts, not every replicate."""
    edges = np.linspace(lo, hi, _BINS + 1)
    counts, _ = np.histogram(values, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]
    return go.Bar(
        x=centres, y=counts / (values.size * width), name=name, opacity=0.6, width=width
    )


def likelihood_curve(
    family_name: str, x: np.ndarray, grid: Sequence[float] | None = None
) -> go.Figure:
    """The log-likelihood as a function of theta, with the MLE marked (NB06)."""
    x = np.asarray(x, dtype=float)
    hat = estimation.mle(family_name, x)
    if grid is None:
        span = max(4.0 * hat.se, 0.1 * abs(hat.estimate))
        grid = np.linspace(hat.estimate - span, hat.estimate + span, 200)
    grid = np.asarray(grid, dtype=float)
    ll = np.array([estimation.log_likelihood(family_name, t, x) for t in grid])
    fig = go.Figure(
        data=[
            go.Scatter(x=grid, y=ll, mode="lines", name="対数尤度"),
            go.Scatter(
                x=[hat.estimate],
                y=[hat.loglik],
                mode="markers",
                marker={"size": 12, "color": "crimson"},
                name=f"MLE = {hat.estimate:.4f}",
            ),
        ]
    )
    return apply_defaults(
        fig,
        title=f"{family_name} の対数尤度 — 頂点が最尤推定量",
        xaxis_title="theta",
        yaxis_title="対数尤度",
    )


def mle_sampling_distribution(
    family_name: str, theta: float, ns: Sequence[int], n_reps: int = 3000, seed: int = 0
) -> go.Figure:
    """The MLE's own distribution tightening as n grows, against the CRLB (NB06)."""
    frames = []
    for n in ns:

        def sampler(m, rng, _f=family_name, _t=theta):
            if _f == "poisson":
                return rng.poisson(_t, m).astype(float)
            if _f == "bernoulli":
                return (rng.random(m) < _t).astype(float)
            if _f == "exponential":
                return rng.exponential(1.0 / _t, m)
            return rng.normal(_t, 1.0, m)

        hats = simulation.sampling_distribution(
            lambda s, _f=family_name: estimation.mle(_f, s).estimate,
            sampler,
            n=int(n),
            n_reps=n_reps,
            seed=seed,
        )
        sd = np.sqrt(estimation.cramer_rao_bound(family_name, theta, int(n)))
        lo, hi = theta - 4.0 * sd, theta + 4.0 * sd
        grid = np.linspace(lo, hi, 200)
        normal = np.exp(-0.5 * ((grid - theta) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        frames.append(
            go.Frame(
                data=[
                    _density_bars(hats, f"MLE の分布 (sd = {hats.std(ddof=1):.4f})", lo, hi),
                    go.Scatter(
                        x=grid,
                        y=normal,
                        mode="lines",
                        name=f"Cramer-Rao 下限 (sd = {sd:.4f})",
                    ),
                ],
                name=str(n),
            )
        )
    fig = frame_slider(frames, "n")
    return apply_defaults(
        fig,
        title="最尤推定量の標本分布は Cramer-Rao 下限に張り付く",
        xaxis_title="推定値",
        yaxis_title="密度",
    )


def coverage_intervals(
    n_intervals: int = 100, n: int = 12, truth: float = 0.0, seed: int = 0
) -> go.Figure:
    """Draw many 95% intervals and count how many contain the truth (NB07).

    The title carries the measured count. A reader who remembers one figure
    from this book should remember this one: 95% is a property of the
    procedure, visible only across repetitions.
    """
    rng = np.random.default_rng(seed)
    hit_x, hit_y, miss_x, miss_y = [], [], [], []
    for i in range(n_intervals):
        sample = rng.normal(truth, 1.0, n)
        interval = intervals.t_interval(sample)
        target = (hit_x, hit_y) if interval.contains(truth) else (miss_x, miss_y)
        target[0].extend([interval.lo, interval.hi, None])
        target[1].extend([i, i, None])
    hits = sum(1 for v in hit_y if v is not None) // 2
    fig = go.Figure(
        data=[
            go.Scatter(
                x=hit_x, y=hit_y, mode="lines", line={"color": "#4C78A8"}, name="真値を含む"
            ),
            go.Scatter(
                x=miss_x, y=miss_y, mode="lines", line={"color": "crimson"}, name="真値を外す"
            ),
        ]
    )
    fig.add_vline(x=truth, line={"color": "black", "dash": "dash"})
    return apply_defaults(
        fig,
        title=f"95% 信頼区間を {n_intervals} 本 — 真値を含んだのは {hits}/{n_intervals}",
        xaxis_title="値",
        yaxis_title="実験の番号",
    )


def bootstrap_distribution(
    sample: np.ndarray, statistic: Callable[[np.ndarray], float], n_boot: int = 2000, seed: int = 0
) -> go.Figure:
    """The resampling distribution of any statistic, with the observed value (NB07)."""
    sample = np.asarray(sample, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, sample.size, size=(n_boot, sample.size))
    boot = np.array([float(statistic(sample[i])) for i in idx])
    observed = float(statistic(sample))
    ci = intervals.bootstrap_interval(sample, statistic, n_boot=n_boot, seed=seed)
    lo, hi = boot.min(), boot.max()
    fig = go.Figure(data=[_density_bars(boot, "ブートストラップ分布", lo, hi)])
    fig.add_vline(x=observed, line={"color": "crimson"})
    fig.add_vrect(x0=ci.lo, x1=ci.hi, fillcolor="#4C78A8", opacity=0.12, line_width=0)
    return apply_defaults(
        fig,
        title=f"観測値 {observed:.4f}、95% 区間 [{ci.lo:.4f}, {ci.hi:.4f}]",
        xaxis_title="統計量",
        yaxis_title="密度",
    )


def power_curves(
    effects: Sequence[float], ns: Sequence[int], alpha: float = 0.05
) -> go.Figure:
    """Power against sample size, one curve per effect size (NB08)."""
    ns = list(ns)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=ns,
                y=[testing.power_t_test(e, n, alpha) for n in ns],
                mode="lines+markers",
                name=f"効果量 {e}",
            )
            for e in effects
        ]
    )
    fig.add_hline(y=0.8, line={"color": "grey", "dash": "dot"})
    fig.update_yaxes(range=[0, 1])
    return apply_defaults(
        fig,
        title=f"検出力曲線 (alpha = {alpha}、破線は慣習的な 0.8)",
        xaxis_title="標本サイズ n",
        yaxis_title="検出力",
    )


def phacking_demo(n_tests: int = 200, n: int = 30, seed: int = 0) -> go.Figure:
    """Run many tests on pure noise and count the "discoveries" (NB08)."""
    rng = np.random.default_rng(seed)
    pvals = np.array([testing.t_test(rng.normal(0.0, 1.0, n)).pvalue for _ in range(n_tests)])
    raw = int((pvals < 0.05).sum())
    bonf = int(testing.bonferroni(pvals).sum())
    bh = int(testing.benjamini_hochberg(pvals).sum())
    edges = np.linspace(0.0, 1.0, 21)
    counts, _ = np.histogram(pvals, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    fig = go.Figure(
        data=[
            go.Bar(x=centres, y=counts, width=0.05, name="p 値の分布(全て帰無仮説が真)"),
            go.Bar(
                x=[0.025],
                y=[raw],
                width=0.05,
                marker={"color": "crimson"},
                name=f"補正なしで有意 {raw} 件",
            ),
        ]
    )
    fig.update_layout(barmode="overlay")
    return apply_defaults(
        fig,
        title=(
            f"純粋なノイズに {n_tests} 回検定 — "
            f"補正なし {raw} 件、Bonferroni {bonf} 件、BH {bh} 件"
        ),
        xaxis_title="p 値",
        yaxis_title="件数",
    )
```

`analytics/statistics/src/stats_textbook/plotting/__init__.py` を差し替える:

```python
"""Plotly figure helpers, grouped by the chapters they serve.

``probability`` covers Part I (01-05), ``inference`` covers 06-08.
``regression`` (09-10) arrives later in Plan 2. Consumers import from this
package, not the submodules, so the split stays an implementation detail.
"""

from .core import apply_defaults, curve_slider, frame_slider
from .inference import (
    bootstrap_distribution,
    coverage_intervals,
    likelihood_curve,
    mle_sampling_distribution,
    phacking_demo,
    power_curves,
)
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
    "bootstrap_distribution",
    "clt_convergence",
    "coverage_intervals",
    "curve_slider",
    "frame_slider",
    "joint_marginal_heatmap",
    "likelihood_curve",
    "markov_convergence_slider",
    "mle_sampling_distribution",
    "phacking_demo",
    "poisson_limit_slider",
    "power_curves",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
]
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting_inference.py analytics/statistics/tests/test_plotting.py -q`
Expected: PASS 10 + 14 件

- [ ] **Step 5: 看板図を目視で確認する**

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
from stats_textbook import plotting
S = "/tmp/claude-1000/-home-kazumasa-projects/28c66143-33d0-48c2-9656-a56508369cc3/scratchpad"
fig = plotting.coverage_intervals(n_intervals=100, n=12, seed=0)
fig.write_html(f"{S}/coverage_check.html", include_plotlyjs="cdn")
print(fig.layout.title.text)
fig2 = plotting.phacking_demo(n_tests=200, n=30, seed=0)
fig2.write_html(f"{S}/phacking_check.html", include_plotlyjs="cdn")
print(fig2.layout.title.text)
PY
```

Expected: 被覆図のタイトルが 90–99/100 を報告する。ブラウザで開き、**外した区間が赤で、真値の縦線を跨いでいない**ことを目で確認する。

- [ ] **Step 6: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/plotting analytics/statistics/tests/test_plotting_inference.py
git commit -m "feat(statistics): figures for estimation, intervals and testing

coverage_intervals puts the measured hit count in its own title rather
than the nominal 95, so the figure reports what happened. A test reads
that number back out and checks it lands near the nominal rate -- the
figure cannot quietly start lying.

Both Part I rules carry over and are re-pinned for this module: every
animation goes through frame_slider, and nothing ships raw samples where
bin counts will do."
```

---

## M4 — NB06–08（Task 5–7）の共通ルール

Plan 1 の M2 と同じ。各タスクで繰り返さない。

**標準セットアップセル**（章タイトルの直後に必ず置く）:

```python
code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    datasets, distributions, estimation, intervals, plotting, processes, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
""")
```

**章の節構成**: 1 導入 → 2 直感と図 → 3 定式化 → 4 実装 → 5 実験 → 6 落とし穴 → 7 演習（3–5 問、解答は Plan 3 の 13 章）

**検証手順**（毎回同じ）:

```bash
cd analytics/statistics
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py --check
PYTHONPATH=src /home/kazumasa/projects/.venv/bin/python tools/build_notebooks.py
cd -
time PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python -m jupyter \
  nbconvert --to notebook --execute --inplace analytics/statistics/notebooks/NN_*.ipynb
```

**実行時間の予算**: NB06–13 の 8 章で合計 271 秒。**1 章 34 秒**を目安とし、超えたら反復数を下げる。
計測値は Task 13 の README 表に記録する。

`book/_toc.yml` の `chapters:` と `tools/build_notebooks.py` の `NOTEBOOKS` に 1 行ずつ追加する。

**出力の点検**（毎回）: 生成後に必ず次を走らせ、エラーと stderr が無いことを確認する。

```bash
PYTHONPATH=analytics/statistics/src /home/kazumasa/projects/.venv/bin/python - <<'PY'
import json, sys, pathlib
nb = json.load(open(sys.argv[1] if len(sys.argv)>1 else "analytics/statistics/notebooks/06_estimation_mle.ipynb"))
for c in nb["cells"]:
    for o in c.get("outputs", []):
        if o.get("output_type") == "error":
            print("ERROR:", o["ename"], o["evalue"]); raise SystemExit(1)
        if o.get("name") == "stderr":
            print("STDERR:", "".join(o["text"])[:300])
    if c["cell_type"] == "code":
        t = "".join("".join(o.get("text", [])) for o in c.get("outputs", []))
        if t.strip(): print(t.rstrip()); print("-")
print("--- ok ---")
PY
```

**本文の数字は必ずセル出力と一致させること。** Plan 1 で「8 回表」と書きながら 3 回を出力する誤りを踏んだ。
本文が特定の数値を語るなら、そのセルに `assert` を置いて固定する。

---

### Task 5: NB06 — 推定と最尤法

**Files:**
- Create: `analytics/statistics/tools/build_nb06.py`
- Create: `analytics/statistics/notebooks/06_estimation_mle.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `estimation.*`、`plotting.likelihood_curve` / `mle_sampling_distribution`、`simulation.sampling_distribution`
- Produces: なし

- [ ] **Step 1: `build_nb06.py` を書く**

`cells` を次の順で構成する。

1. `md` — タイトル `# 06. 推定と最尤法 — データから母数を当てる` ＋ 一文要約「良い推定量とは何かを先に決めなければ、良い推定量は選べない」＋「この章で分かること」5 点（推定量の 3 つの性質／最尤法の考え方／Fisher 情報は尤度の尖り具合であること／Cramér–Rao 下限／期待情報と観測情報の違い）
2. 標準セットアップセル
3. `md` — §1 推定量の良さを定義する。**不偏性**（平均的に当たる）・**一致性**（$n \to \infty$ で真値に収束）・**有効性**（分散が小さい）。3 つは独立で、両立しないこともある
4. `code` — 不偏だが分散が大きい推定量と、偏っているが分散が小さい推定量を比べる:

```python
code("""
# 正規分布の平均を、標本平均と「最初の 1 個」で推定する。
# どちらも不偏だが、有効性がまったく違う。
def first_obs(s):
    return float(s[0])

for name, stat in [("標本平均", np.mean), ("最初の 1 個", first_obs)]:
    hats = simulation.sampling_distribution(
        stat, lambda n, rng: rng.normal(2.0, 1.0, n), n=25, n_reps=20_000, seed=RANDOM_SEED
    )
    print(f"{name:12s} 平均 = {hats.mean():+.4f}(真値 2.0)   分散 = {hats.var():.4f}")
print("\\nどちらも不偏。分散は 25 倍違う = これが有効性")
""")
```

5. `md` — §2 最尤法。「観測されたデータを最も起こりやすくする母数を選ぶ」。尤度と対数尤度、なぜ対数を取るか（積が和になる・数値的に安定）
6. `code` — 尤度曲線（図）:

```python
code("""
rng = np.random.default_rng(RANDOM_SEED)
x = rng.poisson(3.0, 100)
print(f"標本平均 = {x.mean():.4f}")
plotting.likelihood_curve("poisson", x)
""")
```

7. `md` — §3 03 章の伏線回収。指数型分布族では対数尤度が $\eta(\theta)\sum T(x_i) - nA(\eta)$ の形になるので、**MLE は必ず十分統計量の関数になる**。ポアソンなら標本平均
8. `code` — 4 つの族で MLE が閉じた形と一致することを確認:

```python
code("""
rng = np.random.default_rng(1)
cases = [
    ("bernoulli", 0.3, (rng.random(500) < 0.3).astype(float), "標本比率"),
    ("poisson", 3.0, rng.poisson(3.0, 500).astype(float), "標本平均"),
    ("normal_unit_var", 1.2, rng.normal(1.2, 1.0, 500), "標本平均"),
    ("exponential", 2.5, rng.exponential(1 / 2.5, 500), "標本平均の逆数"),
]
print(f"{'族':18s} {'真値':>7} {'MLE':>9} {'標準誤差':>10}  閉じた形")
for name, truth, data, closed in cases:
    r = estimation.mle(name, data)
    print(f"{name:18s} {truth:7.2f} {r.estimate:9.4f} {r.se:10.4f}  {closed}")
""")
```

9. `md` — §4 Fisher 情報。$I(\theta) = -E[\partial^2 \ell / \partial\theta^2]$ は**対数尤度の尖り具合**。尖っていれば $\theta$ を少し動かすだけで尤度が落ちる＝データが $\theta$ について多くを語っている
10. `code` — **期待情報と観測情報の違い**（この章の核心）:

```python
code("""
rng = np.random.default_rng(1)
lam, n = 2.5, 50
x = rng.poisson(lam, n)
hat = estimation.mle("poisson", x).estimate

def ll(theta):
    return estimation.log_likelihood("poisson", theta, x)

print(f"真値 lambda = {lam}   標本平均(= MLE) = {hat:.4f}\\n")
print(f"{'評価点':>12} {'観測情報':>12} {'期待情報':>12}")
for label, theta in [("真値で", lam), ("MLE で", hat)]:
    obs = estimation.observed_information(ll, theta)
    exp = estimation.expected_fisher_information("poisson", theta, n)
    print(f"{label:>12} {obs:12.2f} {exp:12.2f}")
print("\\nMLE で評価したときだけ一致する。真値では標本平均のずれの分だけ食い違う")
""")
```

11. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
Fisher 情報は対数尤度の尖り具合であり、推定の難しさをそのまま表す。
尖っていれば少ないデータで決まり、平らならいくらデータを集めても決まらない。
そして手元にあるのは期待情報ではなく観測情報である。両者が一致するのは最尤推定量の上だけである。
```
````

12. `md` — §5 Cramér–Rao 下限。$\mathrm{Var}(\hat\theta) \ge 1/I(\theta)$。**どんなに賢い不偏推定量を作っても、この下には行けない**
13. `code` — MLE の標本分布が下限に張り付くのを見る（図）:

```python
code("""
plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 30, 100, 400], n_reps=3000)
""")
```

14. `code` — 数値で確認:

```python
code("""
lam = 3.0
print(f"{'n':>6} {'MLE の実測分散':>16} {'Cramer-Rao 下限':>18} {'比':>7}")
for n in [10, 30, 100, 400]:
    hats = simulation.sampling_distribution(
        lambda s: estimation.mle("poisson", s).estimate,
        lambda m, rng: rng.poisson(lam, m).astype(float),
        n=n, n_reps=8000, seed=2,
    )
    bound = estimation.cramer_rao_bound("poisson", lam, n)
    print(f"{n:6d} {hats.var():16.6f} {bound:18.6f} {hats.var() / bound:7.3f}")
print("\\n比が 1 に張り付く = MLE は漸近的に有効")
""")
```

15. `md` — §6 漸近正規性。$\sqrt{n}(\hat\theta - \theta) \to N(0, 1/I_1(\theta))$。04 章のデルタ法と組み合わせれば、$g(\hat\theta)$ の分布もすぐ出る
16. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
A/B テストの必要サンプル数、臨床試験の症例数設計、センサーの校正回数。
いずれも「どれだけ集めれば決まるか」の見積もりで、Fisher 情報がその答えを与える。
逆に、いくら集めても決まらない量があるときは、尤度が平らになっていないかを疑う。
```
````

17. `md` — §7 落とし穴（MLE は不偏とは限らない（正規分布の分散の MLE は $n$ で割る）／尤度が多峰なら最適化が局所解に落ちる／台が母数に依存する場合（一様分布）は微分が使えず Cramér–Rao も成り立たない）
18. `code` — MLE が偏る例:

```python
code("""
# 正規分布の分散の MLE は n で割る -> 系統的に小さい
sigma2 = 4.0
mle_var = simulation.sampling_distribution(
    lambda s: float(s.var(ddof=0)), lambda n, rng: rng.normal(0, 2.0, n),
    n=10, n_reps=20_000, seed=3,
)
unbiased = simulation.sampling_distribution(
    lambda s: float(s.var(ddof=1)), lambda n, rng: rng.normal(0, 2.0, n),
    n=10, n_reps=20_000, seed=3,
)
print(f"真値 = {sigma2}")
print(f"MLE (n で割る)   平均 = {mle_var.mean():.4f}  偏り = {mle_var.mean() - sigma2:+.4f}")
print(f"不偏 (n-1 で割る) 平均 = {unbiased.mean():.4f}  偏り = {unbiased.mean() - sigma2:+.4f}")
print(f"\\nただし MLE の方が分散は小さい: {mle_var.var():.4f} 対 {unbiased.var():.4f}")
print("不偏性と有効性は両立しないことがある")
""")
```

19. `md` — §8 演習 5 問（(1) 指数分布の MLE を対数尤度の微分から導け (2) 正規分布の分散の MLE の偏りが $-\sigma^2/n$ であることを示し数値で確認せよ (3) 一様分布 $U(0,\theta)$ の MLE を求め、Cramér–Rao が使えない理由を説明せよ (4) デルタ法で $\log\hat\lambda$ の漸近分散を求め、シミュレーションで確かめよ (5) 尤度が 2 峰になる混合正規で、初期値によって最適化の結果が変わることを示せ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

`NOTEBOOKS` に `("build_nb06", "06_estimation_mle")` を、`_toc.yml` に `  - file: notebooks/06_estimation_mle` を追加してから共通手順を実行する。
Expected: 実行 25 秒以内。§4 の表は「真値で 18.12 / 20.00、MLE で 18.12 / 18.12」に近い値になる（seed 1・$n=50$ の実測）。

- [ ] **Step 3: 本をビルドして目視確認**

Run: `/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/`
`_build/html/notebooks/06_estimation_mle.html` を開き、尤度曲線と MLE 標本分布のスライダーが動くこと、コールアウト 2 種が描画されていることを確認する。

- [ ] **Step 4: commit**

```bash
git add analytics/statistics/tools/build_nb06.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/06_estimation_mle.ipynb
git commit -m "docs(statistics): NB06 estimation and maximum likelihood

Opens by making unbiasedness cheap and efficiency expensive: the sample
mean and the first observation are both unbiased for a normal mean, and
their variances differ by a factor of 25.

The chapter's own contribution is the expected/observed distinction, shown
as a two-row table rather than a remark. At the true parameter the two
numbers differ; at the MLE they are identical. What an estimator actually
has is the second one."
```

---

### Task 6: NB07 — 信頼区間とブートストラップ

**Files:**
- Create: `analytics/statistics/tools/build_nb07.py`
- Create: `analytics/statistics/notebooks/07_confidence_intervals_bootstrap.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `intervals.*`、`plotting.coverage_intervals` / `bootstrap_distribution`、`simulation.coverage_probability`
- Produces: なし

> **本書の看板章の 1 つ。** 被覆確率の図は report ポータルのギャラリーにも出す（Plan 3）。

- [ ] **Step 1: `build_nb07.py` を書く**

`cells`:

1. `md` — タイトル `# 07. 信頼区間とブートストラップ — 「95%」は何についての主張か` ＋ 一文要約「信頼区間の 95% は、この区間についての確率ではない。手続きについての長期頻度である」＋「この章で分かること」5 点
2. 標準セットアップセル
3. `md` — §1 よくある誤解から入る。「この区間が真値を含む確率は 95%」は**誤り**。頻度論では真値は定数であり、確率変数ではない。ランダムなのは区間の方である。**正しい読み方**: この手続きを繰り返すと、作られる区間の 95% が真値を含む
4. `code` — **看板図**。100 本の区間を描いて数える:

```python
code("""
plotting.coverage_intervals(n_intervals=100, n=12, truth=0.0, seed=RANDOM_SEED)
""")
```

5. `md` — 図の読み方。青が真値を含んだ区間、赤が外した区間。**どの 1 本を取っても「95%」ではない** — 含むか含まないかのどちらかである。95% は 100 本を眺めて初めて意味を持つ
6. `code` — 被覆確率を実測する（本書の第 2 原則）:

```python
code("""
r = simulation.coverage_probability(
    lambda n, rng: rng.normal(0.0, 1.0, n),
    lambda s: tuple(intervals.t_interval(s)),
    truth=0.0, n=12, n_reps=20_000, seed=1,
)
lo, hi = r.ci95()
print(f"実測被覆率 = {r.estimate:.4f}   モンテカルロ 95% 区間 = [{lo:.4f}, {hi:.4f}]")
print(f"名目値 0.95 は区間の中: {lo <= 0.95 <= hi}")
""")
```

7. `md` — §2 なぜ $t$ 分布なのか。標準偏差を推定で置き換えると、分母がぶれる分だけ裾が重くなる（03 章）。正規の分位点を使うとどうなるかを測る
8. `code` — 正規分位点を使った区間は過小被覆になる:

```python
code("""
from scipy import stats

def normal_interval(s):
    half = 1.96 * s.std(ddof=1) / np.sqrt(s.size)
    return float(s.mean() - half), float(s.mean() + half)

print(f"{'n':>5} {'t 区間':>12} {'正規分位点':>12}")
for n in [5, 10, 30, 100]:
    a = simulation.coverage_probability(
        lambda m, rng: rng.normal(0, 1, m), lambda s: tuple(intervals.t_interval(s)),
        truth=0.0, n=n, n_reps=8000, seed=2,
    ).estimate
    b = simulation.coverage_probability(
        lambda m, rng: rng.normal(0, 1, m), normal_interval, truth=0.0, n=n, n_reps=8000, seed=2,
    ).estimate
    print(f"{n:5d} {a:12.4f} {b:12.4f}")
print("\\n小標本では正規分位点が明確に過小被覆。n が増えると差は消える")
""")
```

9. `md` — §3 ピボット法。$\frac{\bar X - \mu}{S/\sqrt{n}}$ のように**母数に依らない分布を持つ量**（ピボット）を見つければ、その分位点から区間が作れる。ピボットが無い場合はどうするか → ブートストラップ
10. `md` — §4 ブートストラップ。「標本を母集団と見なして、そこから再標本する」。中央値・分位点・比など、標準誤差の公式が無い統計量に効く
11. `code` — 中央値のブートストラップ分布（図）:

```python
code("""
rng = np.random.default_rng(3)
sample = rng.exponential(1.0, 60)
print(f"標本中央値 = {np.median(sample):.4f}   真の中央値 = {np.log(2):.4f}")
plotting.bootstrap_distribution(sample, np.median, n_boot=3000, seed=0)
""")
```

12. `code` — ブートストラップ区間の被覆を実測:

```python
code("""
truth = float(np.log(2.0))
r = simulation.coverage_probability(
    lambda n, rng: rng.exponential(1.0, n),
    lambda s: tuple(intervals.bootstrap_interval(s, np.median, n_boot=400, seed=0)),
    truth=truth, n=60, n_reps=1000, seed=5,
)
print(f"中央値のブートストラップ区間の被覆率 = {r.estimate:.4f}(名目 0.95)")
""")
```

13. `md` — §5 percentile と BCa。percentile 法は歪んだ統計量で過小被覆になる。BCa は偏りと歪みを補正する
14. `code` — **両者を比べる**（実測済み: $n=40$ の指数分布の分散で percentile 0.747・BCa 0.800）:

```python
code("""
truth = 1.0                      # 指数分布(rate 1)の分散
print(f"{'手法':>12} {'被覆率':>10}   (名目 0.95)")
for method in ["percentile", "bca"]:
    r = simulation.coverage_probability(
        lambda n, rng: rng.exponential(1.0, n),
        lambda s, _m=method: tuple(
            intervals.bootstrap_interval(s, lambda a: a.var(ddof=1), method=_m, n_boot=400, seed=0)
        ),
        truth=truth, n=40, n_reps=600, seed=6,
    )
    print(f"{method:>12} {r.estimate:10.4f}")
print("\\nBCa の方が良いが、どちらも 0.95 には届かない。")
print("小標本で歪んだ統計量にブートストラップを使うと、区間は狭すぎる方に外れる")
""")
```

15. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
95% 信頼区間の 95% は、手続きの長期頻度であって、目の前の区間の確率ではない。
だから被覆率は実測できるし、実測すべきである。
導出が正しくても、手元の標本サイズで名目値どおりに動く保証はない。
```
````

16. `md` — §6 順列検定。ブートストラップが**区間**の道具なら、順列は**検定**の道具。帰無仮説の下でラベルが交換可能であることだけを仮定する
17. `code` — 順列検定を動かす:

```python
code("""
rng = np.random.default_rng(8)
a, b = rng.normal(0, 1, 60), rng.normal(0, 1, 60)
c, d = rng.normal(0, 1, 60), rng.normal(0.6, 1, 60)
print(f"差が無い 2 群: p = {intervals.permutation_test(a, b, n_perm=5000, seed=0):.4f}")
print(f"差がある 2 群: p = {intervals.permutation_test(c, d, n_perm=5000, seed=0):.4f}")
""")
```

18. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
論文やダッシュボードに並ぶ誤差棒の多くは、名目上の被覆率で描かれている。
モデルの仮定が現場のデータに合っていなければ、その棒は見た目より短い。
新しい指標に区間を付けるときは、手元のデータ生成過程を模したシミュレーションで
被覆率を一度測っておくと、後で高くつく誤解を防げる。
```
````

19. `md` — §7 落とし穴（区間の解釈の誤り／複数の区間を同時に見ると同時被覆率は下がる／ブートストラップは標本が母集団を代表していることに依存し、極値や裾では破綻する）
20. `code` — ブートストラップが破綻する例:

```python
code("""
# 最大値のブートストラップ。再標本は元の標本の最大値を超えられない
rng = np.random.default_rng(9)
sample = rng.uniform(0, 10, 50)
boot_ci = intervals.bootstrap_interval(sample, np.max, n_boot=3000, seed=0)
print(f"標本最大値 = {sample.max():.4f}   真の上限 = 10.0")
print(f"ブートストラップ 95% 区間 = [{boot_ci.lo:.4f}, {boot_ci.hi:.4f}]")
print(f"真値 10.0 を含む: {boot_ci.contains(10.0)}")
print("\\n再標本は元の最大値を超えられないので、区間は真値の手前で頭打ちになる")
""")
```

21. `md` — §8 演習 4 問（(1) 名目 95% の区間を 3 本同時に見たときの同時被覆率を測れ (2) 歪んだ分布で $n$ を変えて $t$ 区間の被覆率を測り、必要な $n$ を決めよ (3) 比 $\bar X/\bar Y$ のブートストラップ区間を作り被覆率を測れ (4) 順列検定と $t$ 検定を、正規でない分布で比較せよ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

Expected: **この章は Plan 2 で最も重い**（被覆実験が多い）。実行 60 秒以内。超えたら §2 の `n_reps` を 8000 → 4000、§4 の `n_reps` を 1000 → 600 に下げる。

- [ ] **Step 3: 本をビルドして看板図を目視確認**

`_build/html/notebooks/07_confidence_intervals_bootstrap.html` を開き、次を確認する。

- 100 本の区間が縦に並び、赤い区間が真値の縦線を跨いでいない
- タイトルが実測の的中数（90–99/100 のはず）を表示している

- [ ] **Step 4: commit**

```bash
git add analytics/statistics/tools/build_nb07.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/07_confidence_intervals_bootstrap.ipynb
git commit -m "docs(statistics): NB07 confidence intervals and the bootstrap

The chapter's argument is that 95% is a property of the procedure, so it
opens by drawing 100 intervals and counting, then measures the coverage
rate directly rather than citing the derivation.

Both directions are shown. The t interval covers at its nominal rate; the
normal quantile under-covers visibly at n=5 and catches up by n=100. The
percentile bootstrap under-covers badly on the variance of skewed data
(0.75 against a nominal 0.95) and BCa improves it to 0.80 without fixing
it -- which is the honest picture, not a advertisement for BCa."
```

---

### Task 7: NB08 — 仮説検定

**Files:**
- Create: `analytics/statistics/tools/build_nb08.py`
- Create: `analytics/statistics/notebooks/08_hypothesis_testing.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `testing.*`、`plotting.power_curves` / `phacking_demo`、`simulation.rejection_rate`
- Produces: なし

- [ ] **Step 1: `build_nb08.py` を書く**

`cells`:

1. `md` — タイトル `# 08. 仮説検定 — 何を保証し、何を保証しないのか` ＋ 一文要約「p 値は仮説が正しい確率ではない。帰無仮説の下でデータがこれほど極端になる確率である」＋「この章で分かること」5 点
2. 標準セットアップセル
3. `md` — §1 検定の構造。帰無仮説・対立仮説・検定統計量・棄却域。**第 1 種の誤り**（帰無が真なのに棄却）と**第 2 種の誤り**（対立が真なのに棄却しない）。$\alpha$ は前者の上限として**こちらが選ぶ**数
4. `code` — 第 1 種の誤り率が $\alpha$ に一致することを実測:

```python
code("""
print(f"{'alpha':>7} {'実測の棄却率':>14} {'モンテカルロ 95% 区間':>26}")
for alpha in [0.01, 0.05, 0.10]:
    r = simulation.rejection_rate(
        lambda n, rng: rng.normal(0.0, 1.0, n),
        lambda s: testing.t_test(s).pvalue,
        alpha=alpha, n=20, n_reps=20_000, seed=RANDOM_SEED,
    )
    lo, hi = r.ci95()
    print(f"{alpha:7.2f} {r.estimate:14.4f} {f'[{lo:.4f}, {hi:.4f}]':>26}")
print("\\n帰無仮説が真のとき、棄却率は指定した alpha に一致する。これが検定の設計目標")
""")
```

5. `md` — §2 p 値の定義と、よくある誤解 4 つ。(a) 帰無仮説が正しい確率ではない (b) 効果の大きさではない (c) 再現性の指標ではない (d) $p > 0.05$ は「差が無い」ことの証明ではない
6. `code` — 帰無仮説の下で p 値が一様分布することを見る:

```python
code("""
pvals = simulation.sampling_distribution(
    lambda s: testing.t_test(s).pvalue,
    lambda n, rng: rng.normal(0.0, 1.0, n),
    n=20, n_reps=20_000, seed=1,
)
print("帰無仮説が真のときの p 値の分布(一様のはず):")
for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
    share = float(np.mean((pvals >= lo) & (pvals < lo + 0.2)))
    print(f"  [{lo:.1f}, {lo + 0.2:.1f}) に {share:.4f}(理論 0.2)")
print("\\n一様ということは、p = 0.04 も p = 0.96 も同じくらい起きる。")
print("小さい p 値は「珍しい」のではなく「珍しいと定義した領域」に入っただけである")
""")
```

7. `md` — §3 Neyman–Pearson 補題。単純仮説どうしなら、尤度比が最も検出力の高い検定を与える。$\alpha$ を固定したときの最良検定が一意に決まる、という主張
8. `md` — §4 検出力。$1 - \beta$。効果量・標本サイズ・$\alpha$ の 3 つで決まる
9. `code` — 検出力曲線（図）:

```python
code("""
plotting.power_curves(effects=[0.2, 0.5, 0.8], ns=[5, 10, 20, 40, 80, 160], alpha=0.05)
""")
```

10. `code` — 必要標本サイズ:

```python
code("""
print(f"{'効果量':>8} {'検出力 0.8 に必要な n':>24}")
for effect in [0.2, 0.35, 0.5, 0.8, 1.2]:
    print(f"{effect:8.2f} {testing.required_n(effect, alpha=0.05, power=0.8):24d}")
print("\\n効果量が半分になると必要な n は約 4 倍。これが小さな差の検出が高くつく理由")
""")
```

11. `code` — 解析値とシミュレーションの一致（第 2 原則）:

```python
code("""
effect, n = 0.6, 25
analytic = testing.power_t_test(effect, n, alpha=0.05)
sim_r = simulation.rejection_rate(
    lambda m, rng: rng.normal(effect, 1.0, m),
    lambda s: testing.t_test(s).pvalue,
    alpha=0.05, n=n, n_reps=20_000, seed=3,
)
lo, hi = sim_r.ci95()
print(f"非心 t による解析値 = {analytic:.4f}")
print(f"実際に 2 万回検定した実測 = {sim_r.estimate:.4f}   95% 区間 [{lo:.4f}, {hi:.4f}]")
print(f"解析値は実測の区間の中: {lo <= analytic <= hi}")
""")
```

12. `md` — §5 多重比較。検定を繰り返せば、偶然の「有意」が量産される。$m$ 回で少なくとも 1 回誤る確率は $1 - (1-\alpha)^m$
13. `code` — **p-hacking の実演**（図）:

```python
code("""
plotting.phacking_demo(n_tests=200, n=30, seed=4)
""")
```

14. `code` — 補正の効き方:

```python
code("""
rng = np.random.default_rng(4)
pvals = np.array([testing.t_test(rng.normal(0, 1, 30)).pvalue for _ in range(200)])
print("200 回すべて帰無仮説が真(効果はゼロ):")
print(f"  補正なしで p < 0.05    : {int((pvals < 0.05).sum()):3d} 件")
print(f"  Bonferroni 補正後       : {int(testing.bonferroni(pvals).sum()):3d} 件")
print(f"  Benjamini-Hochberg 補正後: {int(testing.benjamini_hochberg(pvals).sum()):3d} 件")
print(f"\\n少なくとも 1 回誤る確率(理論) = {1 - 0.95 ** 200:.4f}")
""")
```

15. `md` — §6 Bonferroni と BH は**違うものを制御している**。前者は「1 つでも誤る確率」（FWER）、後者は「棄却したうちの誤りの割合」（FDR）。探索的な解析では後者が実用的
16. `code` — 本物の効果が混じっているときの挙動:

```python
code("""
rng = np.random.default_rng(5)
fdps, powers = [], []
for _ in range(300):
    null_p = rng.uniform(0, 1, 180)                      # 180 個は効果なし
    alt_p = np.array([testing.t_test(rng.normal(1.0, 1.0, 20)).pvalue for _ in range(20)])
    pvals = np.concatenate([null_p, alt_p])
    is_null = np.concatenate([np.ones(180, bool), np.zeros(20, bool)])
    rejected = testing.benjamini_hochberg(pvals, alpha=0.1)
    fdps.append(testing.false_discovery_proportion(rejected, is_null))
    powers.append(float((rejected & ~is_null).sum() / 20))
print(f"BH(alpha = 0.1) の平均 FDP = {np.mean(fdps):.4f}(0.1 以下に抑えられている)")
print(f"本物の効果を拾えた割合    = {np.mean(powers):.4f}")

bonf_power = []
for _ in range(300):
    alt_p = np.array([testing.t_test(rng.normal(1.0, 1.0, 20)).pvalue for _ in range(20)])
    pvals = np.concatenate([rng.uniform(0, 1, 180), alt_p])
    bonf_power.append(float(testing.bonferroni(pvals, 0.1)[180:].sum() / 20))
print(f"Bonferroni だと拾えた割合  = {np.mean(bonf_power):.4f}   <- 保守的すぎて取り逃がす")
""")
```

17. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
p 値は帰無仮説が正しい確率ではない。帰無仮説の下でこれほど極端なデータが出る確率である。
帰無仮説が真なら p 値は一様分布するので、0.05 を切る結果は 20 回に 1 回は必ず出る。
検定を何回行ったかを数えずに p 値を読むことはできない。
```
````

18. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
A/B テストのダッシュボードで有意になるまで毎日眺める運用は、
検定回数を数えずに繰り返しているのと同じである。
事前に標本サイズを決めておくか、逐次検定の枠組みを使うかのどちらかが要る。
医学研究の事前登録制度も、解析の自由度を封じて同じ問題に対処している。
```
````

19. `md` — §7 落とし穴（有意差と実質的な差は別／$p > 0.05$ は差が無い証拠ではない（検出力不足かもしれない）／効果量と信頼区間を併記する）
20. `code` — 有意だが実質的に無意味な差:

```python
code("""
rng = np.random.default_rng(6)
big = rng.normal(0.02, 1.0, 100_000)      # 効果量 0.02 = 実質ゼロ
r = testing.t_test(big)
ci = intervals.t_interval(big)
print(f"n = 100,000、真の効果 0.02")
print(f"  p 値 = {r.pvalue:.6f}  -> 有意")
print(f"  95% 信頼区間 = [{ci.lo:.4f}, {ci.hi:.4f}]  -> 差は 0.02 前後で実質ゼロ")
print("\\n標本を増やせばどんな小さな差も有意になる。p 値だけでは大きさが分からない")
""")
```

21. `md` — §8 演習 5 問（(1) $m$ 回の独立な検定で少なくとも 1 回誤る確率を導き、数値で確認せよ (2) 検出力 0.8 に必要な $n$ を効果量の関数として図示せよ (3) 帰無が真の割合を変えて BH の FDR 制御を確かめよ (4) 逐次的に検定を繰り返すと第 1 種の誤り率がどこまで上がるか測れ (5) 同じデータに対する $t$ 検定と順列検定の p 値を比較せよ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

Expected: 実行 45 秒以内。§4 の p 値の一様性は各区間 0.20 ± 0.01、§5 の p-hacking は補正なし 12 件・Bonferroni 0 件・BH 0 件（seed 4 の実測値）。

- [ ] **Step 3: 本をビルドして目視確認**

検出力曲線と p-hacking 図が描画されていること、コールアウト 2 種が出ていることを確認する。

- [ ] **Step 4: commit**

```bash
git add analytics/statistics/tools/build_nb08.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/08_hypothesis_testing.ipynb
git commit -m "docs(statistics): NB08 hypothesis testing

Attacks the p-value misreading from the direction that settles it: under
the null the p-value is uniform, so 0.04 and 0.96 are equally likely and a
small p is not rare -- it is inside a region we defined as rare.

The p-hacking demonstration runs 200 tests on pure noise: 12 come back
significant uncorrected, none survive either correction. Bonferroni and BH
are then separated by what they control rather than by their formulas,
with BH's power advantage measured against Bonferroni's conservatism on
data that has 20 real effects among 180 nulls.

Closes on the opposite failure: at n=100,000 an effect of 0.02 is highly
significant and still meaningless, which is why the interval is printed
next to the p-value."
```

---

### Task 8: `regression.py` — 回帰を推測として扱う

**Files:**
- Create: `analytics/statistics/src/stats_textbook/regression.py`
- Test: `analytics/statistics/tests/test_regression.py`

**Interfaces:**
- Consumes: なし（`numpy` / `scipy` のみ。**`statsmodels` は import しない**）
- Produces:
  - `OLSResult` — frozen dataclass、フィールド `params: np.ndarray` / `se: np.ndarray` / `tvalues: np.ndarray` / `pvalues: np.ndarray` / `fitted: np.ndarray` / `resid: np.ndarray` / `df_resid: int` / `r_squared: float` / `sigma2: float`
  - `ols(X: np.ndarray, y: np.ndarray) -> OLSResult`
  - `robust_se(X: np.ndarray, resid: np.ndarray, kind: str = "HC0") -> np.ndarray`（`kind` は `"HC0"` `"HC1"` `"HC2"` `"HC3"`）
  - `f_test_overall(result: OLSResult, X: np.ndarray, y: np.ndarray) -> tuple[float, float]`（$F$ 統計量と p 値）
  - `vif(X: np.ndarray) -> np.ndarray`（定数列は `nan` を返す）
  - `leverage(X: np.ndarray) -> np.ndarray`

> **照合先は `statsmodels.api.OLS`。実測済みの参照値**（seed 0、$n = 200$、切片＋2 説明変数、`beta = [1, 2, -0.5]`、誤差 sd 1.5）:
> - `params = [1.014016, 2.100656, -0.410725]`
> - `se = [0.106840, 0.110972, 0.104033]`
> - `tvalues = [9.490974, 18.929674, -3.948029]`
> - `r_squared = 0.661654`、`df_resid = 197`
> - `HC0 = [0.105780, 0.094074, 0.105917]`、`HC1 = [0.106582, 0.094787, 0.106721]`、
>   `HC2 = [0.106564, 0.094977, 0.107316]`、`HC3 = [0.107360, 0.095895, 0.108747]`
>
> **テストは参照値をハードコードせず `statsmodels` を実際に呼んで比較すること。** 上の数値は実装が正しく動いたときの目安であり、食い違ったときの診断に使う。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_regression.py`:

```python
"""OLS as inference, matched against statsmodels."""

import numpy as np
import pytest
import statsmodels.api as sm
from stats_textbook import regression as reg


def make_data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
    y = X @ np.array([1.0, 2.0, -0.5]) + rng.normal(0, 1.5, n)
    return X, y


def test_ols_matches_statsmodels():
    X, y = make_data()
    got = reg.ols(X, y)
    ref = sm.OLS(y, X).fit()
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-10)
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-10)
    np.testing.assert_allclose(got.tvalues, ref.tvalues, rtol=1e-10)
    np.testing.assert_allclose(got.pvalues, ref.pvalues, rtol=1e-8, atol=1e-12)
    assert got.df_resid == int(ref.df_resid)
    assert abs(got.r_squared - ref.rsquared) < 1e-12


def test_ols_recovers_the_true_coefficients():
    X, y = make_data(n=20_000, seed=1)
    got = reg.ols(X, y)
    np.testing.assert_allclose(got.params, [1.0, 2.0, -0.5], atol=0.05)


def test_fitted_and_residuals_decompose_y():
    X, y = make_data()
    got = reg.ols(X, y)
    np.testing.assert_allclose(got.fitted + got.resid, y, rtol=1e-12)
    # Residuals are orthogonal to every column of X -- the normal equations.
    np.testing.assert_allclose(X.T @ got.resid, np.zeros(X.shape[1]), atol=1e-9)


@pytest.mark.parametrize("kind", ["HC0", "HC1", "HC2", "HC3"])
def test_robust_standard_errors_match_statsmodels(kind):
    X, y = make_data()
    got = reg.robust_se(X, reg.ols(X, y).resid, kind=kind)
    ref = sm.OLS(y, X).fit(cov_type=kind).bse
    np.testing.assert_allclose(got, ref, rtol=1e-9)


def test_robust_se_rejects_an_unknown_kind():
    X, y = make_data()
    with pytest.raises(ValueError, match="kind"):
        reg.robust_se(X, reg.ols(X, y).resid, kind="HC4")


def test_robust_se_differs_from_ordinary_se_under_heteroskedasticity():
    rng = np.random.default_rng(2)
    n = 500
    x = rng.normal(size=n)
    X = np.column_stack([np.ones(n), x])
    y = 1.0 + 2.0 * x + rng.normal(0, 0.5 + np.abs(x), n)  # variance grows with |x|
    fit = reg.ols(X, y)
    hc3 = reg.robust_se(X, fit.resid, kind="HC3")
    # The ordinary SE is the one that is wrong here.
    assert abs(hc3[1] - fit.se[1]) / fit.se[1] > 0.05


def test_overall_f_test_matches_statsmodels():
    X, y = make_data()
    fit = reg.ols(X, y)
    f, p = reg.f_test_overall(fit, X, y)
    ref = sm.OLS(y, X).fit()
    assert abs(f - ref.fvalue) < 1e-8
    assert abs(p - ref.f_pvalue) < 1e-12


def test_vif_flags_collinearity_and_ignores_the_intercept():
    rng = np.random.default_rng(3)
    n = 400
    a = rng.normal(size=n)
    X = np.column_stack([np.ones(n), a, a + rng.normal(0, 0.05, n), rng.normal(size=n)])
    v = reg.vif(X)
    assert np.isnan(v[0]), "the intercept has no VIF"
    assert v[1] > 10 and v[2] > 10, "the near-duplicate pair must be flagged"
    assert v[3] < 2, "the independent column must not be"


def test_leverage_sums_to_the_number_of_parameters():
    X, y = make_data()
    h = reg.leverage(X)
    assert abs(h.sum() - X.shape[1]) < 1e-9
    assert np.all((h >= 0) & (h <= 1))
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_regression.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.regression'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/regression.py`:

```python
"""Linear regression read as inference rather than as curve fitting.

The coefficients are estimates, so they have a sampling distribution, and
every t and F below is a statement about that distribution under a set of
assumptions. Those assumptions are the interesting part -- ``robust_se``
exists because one of them (constant error variance) fails routinely, and
the fix costs nothing.

Deliberately built on numpy alone. ``statsmodels`` appears only in the
tests, as the reference implementation this must agree with.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = ["OLSResult", "f_test_overall", "leverage", "ols", "robust_se", "vif"]

_HC_KINDS = ("HC0", "HC1", "HC2", "HC3")


@dataclass(frozen=True)
class OLSResult:
    """A least-squares fit with everything needed to do inference on it."""

    params: np.ndarray
    se: np.ndarray
    tvalues: np.ndarray
    pvalues: np.ndarray
    fitted: np.ndarray
    resid: np.ndarray
    df_resid: int
    r_squared: float
    sigma2: float


def ols(X: np.ndarray, y: np.ndarray) -> OLSResult:
    """Ordinary least squares by the normal equations, via ``lstsq``.

    ``lstsq`` rather than an explicit inverse: it is the numerically stable
    route and degrades gracefully on near-collinear designs, which the VIF
    section deliberately constructs.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    params, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ params
    resid = y - fitted
    df_resid = n - k
    sigma2 = float(resid @ resid / df_resid)
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(sigma2 * np.diag(xtx_inv))
    tvalues = params / se
    pvalues = 2.0 * stats.t.sf(np.abs(tvalues), df_resid)
    tss = float(((y - y.mean()) ** 2).sum())
    return OLSResult(
        params=params,
        se=se,
        tvalues=tvalues,
        pvalues=pvalues,
        fitted=fitted,
        resid=resid,
        df_resid=df_resid,
        r_squared=1.0 - float(resid @ resid) / tss,
        sigma2=sigma2,
    )


def leverage(X: np.ndarray) -> np.ndarray:
    """Diagonal of the hat matrix: how much each point pulls its own fit."""
    X = np.asarray(X, dtype=float)
    return np.einsum("ij,jk,ik->i", X, np.linalg.pinv(X.T @ X), X)


def robust_se(X: np.ndarray, resid: np.ndarray, kind: str = "HC0") -> np.ndarray:
    """Heteroskedasticity-consistent standard errors (White's sandwich).

    The ordinary formula assumes every observation has the same error
    variance. When it does not, the coefficients stay unbiased but their
    standard errors are wrong -- and the t statistics built from them
    inherit the error. HC3 is the usual default in small samples.
    """
    if kind not in _HC_KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {_HC_KINDS}")
    X = np.asarray(X, dtype=float)
    resid = np.asarray(resid, dtype=float)
    n, k = X.shape
    h = leverage(X)
    if kind == "HC0":
        w = resid**2
    elif kind == "HC1":
        w = resid**2 * n / (n - k)
    elif kind == "HC2":
        w = resid**2 / (1.0 - h)
    else:
        w = resid**2 / (1.0 - h) ** 2
    bread = np.linalg.pinv(X.T @ X)
    meat = X.T @ (X * w[:, None])
    return np.sqrt(np.diag(bread @ meat @ bread))


def f_test_overall(result: OLSResult, X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Test that every slope is zero, against the intercept-only model."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    k = X.shape[1]
    df_model = k - 1
    tss = float(((y - y.mean()) ** 2).sum())
    rss = float(result.resid @ result.resid)
    f = ((tss - rss) / df_model) / (rss / result.df_resid)
    return f, float(stats.f.sf(f, df_model, result.df_resid))


def vif(X: np.ndarray) -> np.ndarray:
    """Variance inflation factor per column; ``nan`` for a constant column.

    VIF_j = 1 / (1 - R2_j), where R2_j regresses column j on the others.
    A value of 10 means that coefficient's variance is 10 times what it
    would be with uncorrelated predictors.
    """
    X = np.asarray(X, dtype=float)
    k = X.shape[1]
    out = np.full(k, np.nan)
    for j in range(k):
        if np.allclose(X[:, j], X[0, j]):
            continue  # constant column: no variance to inflate
        others = np.delete(X, j, axis=1)
        r2 = ols(others, X[:, j]).r_squared
        out[j] = 1.0 / (1.0 - r2) if r2 < 1.0 else np.inf
    return out
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_regression.py -q`
Expected: PASS 12 件（`robust_se` は 4 通りのパラメータ化で 4 件）

> **HC1 の定義に注意。** `statsmodels` の `cov_type="HC1"` は $\frac{n}{n-k}$ を掛ける。実測の参照値 `HC1 = [0.106582, 0.094787, 0.106721]` と `HC0 = [0.105780, 0.094074, 0.105917]` の比は $\sqrt{200/197} = 1.00758$ で一致する。テストが落ちたらまずこの係数を疑う。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/regression.py analytics/statistics/tests/test_regression.py
git commit -m "feat(statistics): OLS as inference, with robust standard errors

Built on numpy alone so the notebook can show the normal equations doing
the work; statsmodels appears only in the tests, where all four HC
variants have to agree with it to 1e-9.

The residuals-orthogonal-to-X test is the one that would catch a genuinely
wrong implementation -- it is the normal equations restated, so it fails
the moment the solve is wrong in a way that coefficient comparison alone
might mask."
```

---

### Task 9: `glm.py` — IRLS を自前で書き、statsmodels と一致させる

**Files:**
- Create: `analytics/statistics/src/stats_textbook/glm.py`
- Test: `analytics/statistics/tests/test_glm.py`

**Interfaces:**
- Consumes: なし（`numpy` / `scipy` のみ）
- Produces:
  - `GLMResult` — frozen dataclass、フィールド `params: np.ndarray` / `se: np.ndarray` / `fitted: np.ndarray` / `deviance: float` / `loglik: float` / `n_iter: int` / `converged: bool`
  - `irls(X: np.ndarray, y: np.ndarray, family: str = "binomial", max_iter: int = 50, tol: float = 1e-10) -> GLMResult`（`family` は `"binomial"` / `"poisson"` / `"gaussian"`）
  - `deviance_residuals(y: np.ndarray, mu: np.ndarray, family: str) -> np.ndarray`
  - `dispersion(result: GLMResult, y: np.ndarray, X: np.ndarray, family: str) -> float`（過分散の検出用。ピアソン $\chi^2$ / 自由度）

> **これが 10 章の主張そのもの。** 実測済みの `statsmodels` 参照値:
> - ロジスティック（seed 0、$n=400$、`beta=[-0.5, 1.2]`）: `params = [-0.672473, 1.337109]`、`se = [0.122909, 0.155216]`、`deviance = 418.806706`
> - ポアソン（seed 1、$n=300$、`beta=[0.7, 0.4]`）: `params = [0.718458, 0.455925]`、`se = [0.041297, 0.040442]`、`deviance = 322.533634`
>
> **プロトタイプで実測した一致度**: ロジスティックは係数 6.7e-16・標準誤差 4.8e-10（絶対）、
> ポアソンは係数 7.2e-12・標準誤差 8.0e-8（絶対、相対 2.0e-6）、正規は OLS と 4.4e-16 で一致。
> 逸脱度は両方とも小数 6 桁まで一致する。**反復回数は本書の実装で 6 回、`statsmodels` は 4 回**
> — 収束判定が違うだけで、結果は一致する。

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_glm.py`:

```python
"""The book's own IRLS must reproduce statsmodels exactly."""

import numpy as np
import pytest
import statsmodels.api as sm
from stats_textbook import glm


def logistic_data(n=400, seed=0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    eta = X @ np.array([-0.5, 1.2])
    return X, rng.binomial(1, 1.0 / (1.0 + np.exp(-eta))).astype(float)


def poisson_data(n=300, seed=1):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    return X, rng.poisson(np.exp(X @ np.array([0.7, 0.4]))).astype(float)


def test_logistic_irls_matches_statsmodels():
    X, y = logistic_data()
    got = glm.irls(X, y, family="binomial")
    ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-7)
    assert abs(got.deviance - ref.deviance) < 1e-7
    assert abs(got.loglik - ref.llf) < 1e-7


def test_poisson_irls_matches_statsmodels():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    ref = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    # Measured agreement: params to 7e-12, se to 2e-6 relative. The looser
    # tolerance on se is real -- statsmodels stops iterating on a different
    # criterion, so the covariance is evaluated at a marginally different mu.
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-5)
    assert abs(got.deviance - ref.deviance) < 1e-6


def test_gaussian_irls_reduces_to_ordinary_least_squares():
    """With an identity link, one IRLS step is the OLS solve."""
    from stats_textbook import regression as reg

    rng = np.random.default_rng(2)
    n = 200
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    y = X @ np.array([1.0, -2.0]) + rng.normal(0, 1.0, n)
    np.testing.assert_allclose(
        glm.irls(X, y, family="gaussian").params, reg.ols(X, y).params, rtol=1e-10
    )


def test_irls_converges_in_a_handful_of_iterations():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    assert 2 <= got.n_iter <= 10, f"took {got.n_iter} iterations"


def test_irls_rejects_an_unknown_family():
    X, y = logistic_data()
    with pytest.raises(ValueError, match="family"):
        glm.irls(X, y, family="gamma")


def test_binomial_response_outside_zero_one_is_rejected():
    X, _ = logistic_data()
    with pytest.raises(ValueError, match="binomial"):
        glm.irls(X, np.full(X.shape[0], 2.0), family="binomial")


def test_deviance_residuals_square_to_the_deviance():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    d = glm.deviance_residuals(y, got.fitted, "poisson")
    assert abs(float((d**2).sum()) - got.deviance) < 1e-8


def test_dispersion_is_about_one_for_a_true_poisson():
    X, y = poisson_data(n=2000, seed=3)
    got = glm.irls(X, y, family="poisson")
    assert 0.85 <= glm.dispersion(got, y, X, "poisson") <= 1.15


def test_dispersion_detects_overdispersion():
    """Negative-binomial data fitted as Poisson must show dispersion > 1."""
    rng = np.random.default_rng(4)
    n = 2000
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    mu = np.exp(X @ np.array([1.0, 0.5]))
    y = rng.negative_binomial(2.0, 2.0 / (2.0 + mu)).astype(float)
    got = glm.irls(X, y, family="poisson")
    assert glm.dispersion(got, y, X, "poisson") > 1.5
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_glm.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_textbook.glm'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/glm.py`:

```python
"""Generalised linear models, fitted by iteratively reweighted least squares.

A GLM is three choices: a distribution from the exponential family (NB03),
a link function tying its mean to a linear predictor, and the data. IRLS
then fits all of them with the same loop -- at each step it forms a working
response and a weight, and runs a weighted least squares. Writing that loop
out is the point of NB10; the agreement with statsmodels is what proves the
loop was written correctly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import special, stats

__all__ = ["GLMResult", "deviance_residuals", "dispersion", "irls"]

_FAMILIES = ("binomial", "poisson", "gaussian")


@dataclass(frozen=True)
class GLMResult:
    """A fitted GLM and the pieces needed to judge it."""

    params: np.ndarray
    se: np.ndarray
    fitted: np.ndarray
    deviance: float
    loglik: float
    n_iter: int
    converged: bool


def _check_family(family: str) -> None:
    if family not in _FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {_FAMILIES}")


def _link_inverse(eta: np.ndarray, family: str) -> np.ndarray:
    """Canonical inverse link: logit, log, or identity."""
    if family == "binomial":
        return special.expit(eta)
    if family == "poisson":
        return np.exp(eta)
    return eta


def _variance(mu: np.ndarray, family: str) -> np.ndarray:
    """The family's mean-variance relationship."""
    if family == "binomial":
        return mu * (1.0 - mu)
    if family == "poisson":
        return mu
    return np.ones_like(mu)


def _deviance(y: np.ndarray, mu: np.ndarray, family: str) -> float:
    """Twice the log-likelihood gap to the saturated model."""
    if family == "binomial":
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(y > 0, y * np.log(y / mu), 0.0)
            b = np.where(y < 1, (1 - y) * np.log((1 - y) / (1 - mu)), 0.0)
        return float(2.0 * np.sum(a + b))
    if family == "poisson":
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / mu), 0.0)
        return float(2.0 * np.sum(term - (y - mu)))
    return float(np.sum((y - mu) ** 2))


def _loglik(y: np.ndarray, mu: np.ndarray, family: str) -> float:
    if family == "binomial":
        return float(np.sum(stats.bernoulli.logpmf(y, mu)))
    if family == "poisson":
        return float(np.sum(stats.poisson.logpmf(y, mu)))
    resid = y - mu
    sigma2 = float(resid @ resid / y.size)
    return float(np.sum(stats.norm.logpdf(y, mu, np.sqrt(sigma2))))


def irls(
    X: np.ndarray,
    y: np.ndarray,
    family: str = "binomial",
    max_iter: int = 50,
    tol: float = 1e-10,
) -> GLMResult:
    """Fit a GLM by iteratively reweighted least squares.

    Each iteration linearises the link around the current fit, forming a
    working response ``z`` and weights ``w``, then solves a weighted least
    squares. For canonical links this is exactly Newton-Raphson on the
    log-likelihood, which is why it converges in a handful of steps.
    """
    _check_family(family)
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if family == "binomial" and np.any((y < 0.0) | (y > 1.0)):
        raise ValueError("binomial response must lie in [0, 1]")

    n, k = X.shape
    # Start from a mildly shrunk response so the link is finite at step 0.
    mu = (y + 0.5) / 2.0 if family == "binomial" else np.maximum(y, 0.25) + 0.1
    if family == "gaussian":
        mu = np.full_like(y, y.mean())
    beta = np.zeros(k)
    converged = False
    it = 0

    for it in range(1, max_iter + 1):
        var = _variance(mu, family)
        if family == "binomial":
            eta = special.logit(mu)
            dmu_deta = var
        elif family == "poisson":
            eta = np.log(mu)
            dmu_deta = mu
        else:
            eta = mu
            dmu_deta = np.ones_like(mu)
        z = eta + (y - mu) / dmu_deta
        w = dmu_deta**2 / var
        sqrt_w = np.sqrt(w)
        beta_new, *_ = np.linalg.lstsq(X * sqrt_w[:, None], z * sqrt_w, rcond=None)
        mu = _link_inverse(X @ beta_new, family)
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            converged = True
            break
        beta = beta_new

    var = _variance(mu, family)
    if family == "binomial":
        w = var
    elif family == "poisson":
        w = mu
    else:
        w = np.ones_like(mu)
    cov = np.linalg.pinv((X * w[:, None]).T @ X)
    scale = 1.0
    if family == "gaussian":
        resid = y - mu
        scale = float(resid @ resid / (n - k))
    return GLMResult(
        params=beta,
        se=np.sqrt(scale * np.diag(cov)),
        fitted=mu,
        deviance=_deviance(y, mu, family),
        loglik=_loglik(y, mu, family),
        n_iter=it,
        converged=converged,
    )


def deviance_residuals(y: np.ndarray, mu: np.ndarray, family: str) -> np.ndarray:
    """Signed square roots of each observation's deviance contribution."""
    _check_family(family)
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if family == "poisson":
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / mu), 0.0)
        d = 2.0 * (term - (y - mu))
    elif family == "binomial":
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(y > 0, y * np.log(y / mu), 0.0)
            b = np.where(y < 1, (1 - y) * np.log((1 - y) / (1 - mu)), 0.0)
        d = 2.0 * (a + b)
    else:
        d = (y - mu) ** 2
    return np.sign(y - mu) * np.sqrt(np.maximum(d, 0.0))


def dispersion(result: GLMResult, y: np.ndarray, X: np.ndarray, family: str) -> float:
    """Pearson chi-square over residual degrees of freedom.

    Should sit near 1 when the family's mean-variance relationship holds.
    Well above 1 is overdispersion: the counts vary more than a Poisson
    can, and every standard error from the fit is too small.
    """
    _check_family(family)
    y = np.asarray(y, dtype=float)
    n, k = np.asarray(X).shape
    var = _variance(result.fitted, family)
    chi2 = float(np.sum((y - result.fitted) ** 2 / var))
    return chi2 / (n - k)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_glm.py -q`
Expected: PASS 9 件

> **収束しない・一致しない場合の診断順序**: (1) 初期値 `mu` が定義域の端に落ちていないか（二項なら 0 や 1、ポアソンなら 0） (2) `w` の定義が $\left(\frac{d\mu}{d\eta}\right)^2 / V(\mu)$ になっているか (3) 標準誤差の `cov` に重み `w` が入っているか。参照値は Task 冒頭の実測表を使う。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/glm.py analytics/statistics/tests/test_glm.py
git commit -m "feat(statistics): IRLS from scratch, held to statsmodels

The loop is the deliverable: form a working response and a weight, run a
weighted least squares, repeat. Writing it out is what NB10 needs; matching
statsmodels to 1e-8 on both logistic and Poisson fits is what shows it was
written correctly.

Two tests are about the model rather than the arithmetic. The deviance
residuals must square back to the deviance, and the dispersion statistic
must sit near 1 on true Poisson data and above 1.5 on negative-binomial
data fitted as Poisson -- which is the diagnostic the chapter is really
selling."
```

---

### Task 10: `plotting/regression.py` — 09–10 章の図

**Files:**
- Create: `analytics/statistics/src/stats_textbook/plotting/regression.py`
- Modify: `analytics/statistics/src/stats_textbook/plotting/__init__.py`
- Test: `analytics/statistics/tests/test_plotting_regression.py`

**Interfaces:**
- Consumes: `regression.ols` / `robust_se` / `leverage`、`glm.irls` / `deviance_residuals`、`plotting.core.apply_defaults` / `frame_slider`
- Produces（`plotting/__init__.py` から再エクスポート）:
  - `residual_catalogue(seed: int = 0, n: int = 200) -> Figure` — 4 つの病理を切り替えるスライダー
  - `coefficient_sampling(n: int = 60, n_reps: int = 3000, seed: int = 0) -> Figure`
  - `robust_se_comparison(seed: int = 0, ns: Sequence[int] = (50, 200, 1000)) -> Figure`
  - `link_function_fits(x: np.ndarray, y: np.ndarray, families: Sequence[str] = ("binomial", "gaussian")) -> Figure`
  - `irls_convergence(X: np.ndarray, y: np.ndarray, family: str = "binomial", max_iter: int = 8) -> Figure`

- [ ] **Step 1: 失敗するテストを書く**

`analytics/statistics/tests/test_plotting_regression.py`:

```python
"""Figures for chapters 09-10."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_residual_catalogue_has_one_frame_per_pathology():
    fig = plotting.residual_catalogue(seed=0, n=150)
    assert len(fig.frames) == 4
    labels = [f.name for f in fig.frames]
    assert "健全" in labels[0]


def test_coefficient_sampling_centres_on_the_true_slope():
    fig = plotting.coefficient_sampling(n=60, n_reps=800, seed=0)
    bars = [tr for tr in fig.data if tr.type == "bar"]
    assert bars, "the sampling distribution is drawn as binned bars"
    x = np.asarray(bars[0].x, dtype=float)
    y = np.asarray(bars[0].y, dtype=float)
    centre = float((x * y).sum() / y.sum())
    assert abs(centre - 2.0) < 0.15, f"centred at {centre}"


def test_robust_se_comparison_shows_both_kinds():
    fig = plotting.robust_se_comparison(seed=0, ns=(50, 200))
    names = [tr.name for tr in fig.data if tr.name]
    assert any("通常" in n for n in names)
    assert any("HC3" in n for n in names)


def test_link_function_fits_draws_one_curve_per_family():
    rng = np.random.default_rng(1)
    x = rng.normal(size=200)
    y = (rng.random(200) < 1 / (1 + np.exp(-x))).astype(float)
    fig = plotting.link_function_fits(x, y, families=("binomial", "gaussian"))
    curves = [tr for tr in fig.data if tr.mode and "lines" in tr.mode]
    assert len(curves) == 2


def test_irls_convergence_shows_the_parameter_path():
    rng = np.random.default_rng(2)
    n = 300
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    y = rng.binomial(1, 1 / (1 + np.exp(-(X @ [-0.5, 1.2])))).astype(float)
    fig = plotting.irls_convergence(X, y, family="binomial", max_iter=8)
    assert len(fig.data) >= 1
    y0 = np.asarray(fig.data[0].y, dtype=float)
    assert len(y0) >= 3, "at least three iterations should be plotted"


def test_regression_figures_go_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import regression as rp

    assert '"method": "animate"' not in inspect.getsource(rp)


def test_regression_figures_ship_counts_not_raw_samples():
    import inspect

    from stats_textbook.plotting import regression as rp

    assert "go.Histogram(" not in inspect.getsource(rp)


def test_all_regression_figures_are_plotly_figures():
    rng = np.random.default_rng(3)
    x = rng.normal(size=120)
    y = (rng.random(120) < 0.5).astype(float)
    figs = [
        plotting.residual_catalogue(seed=0, n=100),
        plotting.coefficient_sampling(n=40, n_reps=400, seed=0),
        plotting.robust_se_comparison(seed=0, ns=(50,)),
        plotting.link_function_fits(x, y),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/test_plotting_regression.py -q`
Expected: FAIL — `AttributeError: module 'stats_textbook.plotting' has no attribute 'residual_catalogue'`

- [ ] **Step 3: 実装する**

`analytics/statistics/src/stats_textbook/plotting/regression.py`:

```python
"""Figures for chapters 09-10.

The residual catalogue is the workhorse: four designs that a coefficient
table cannot tell apart, and which the residual plot separates instantly.
That is the chapter's argument for looking at residuals at all.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go

from .. import glm, regression, simulation
from .core import apply_defaults, frame_slider

__all__ = [
    "coefficient_sampling",
    "irls_convergence",
    "link_function_fits",
    "residual_catalogue",
    "robust_se_comparison",
]

_BINS = 40


def _density_bars(values: np.ndarray, name: str) -> go.Bar:
    edges = np.linspace(values.min(), values.max(), _BINS + 1)
    counts, _ = np.histogram(values, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]
    return go.Bar(
        x=centres, y=counts / (values.size * width), name=name, opacity=0.65, width=width
    )


def _pathologies(n: int, seed: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Four datasets whose coefficient tables look similar and whose
    residual plots do not."""
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(-3, 3, n))
    X = np.column_stack([np.ones(n), x])
    out = [
        ("健全 — 仮定どおり", X, 1.0 + 2.0 * x + rng.normal(0, 1.0, n)),
        ("不均一分散 — ばらつきが x で変わる", X, 1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.6 * np.abs(x), n)),
        ("非線形 — 直線では足りない", X, 1.0 + 2.0 * x + 0.7 * x**2 + rng.normal(0, 1.0, n)),
        ("外れ値 — 少数の点が引っ張る", X, 1.0 + 2.0 * x + rng.normal(0, 1.0, n)),
    ]
    # Plant the outliers in the last design only.
    y = out[3][2].copy()
    y[[2, n // 2, n - 3]] += 12.0
    out[3] = (out[3][0], out[3][1], y)
    return out


def residual_catalogue(seed: int = 0, n: int = 200) -> go.Figure:
    """Fitted-vs-residual plots for four designs, on one slider (NB09)."""
    frames = []
    for label, X, y in _pathologies(n, seed):
        fit = regression.ols(X, y)
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(
                        x=fit.fitted,
                        y=fit.resid,
                        mode="markers",
                        marker={"size": 6},
                        name=f"R^2 = {fit.r_squared:.3f}",
                    )
                ],
                name=label,
            )
        )
    fig = frame_slider(frames, "データ")
    fig.add_hline(y=0.0, line={"color": "grey", "dash": "dash"})
    return apply_defaults(
        fig,
        title="残差プロットの病理カタログ — 係数表では見分けがつかない",
        xaxis_title="当てはめ値",
        yaxis_title="残差",
    )


def coefficient_sampling(n: int = 60, n_reps: int = 3000, seed: int = 0) -> go.Figure:
    """The slope's own sampling distribution against its theoretical normal (NB09)."""
    true_slope = 2.0

    def sampler(m, rng):
        x = rng.normal(size=m)
        return np.column_stack([x, 1.0 + true_slope * x + rng.normal(0, 1.5, m)])

    def slope(pair):
        x, y = pair[:, 0], pair[:, 1]
        return float(regression.ols(np.column_stack([np.ones(x.size), x]), y).params[1])

    slopes = simulation.sampling_distribution(slope, sampler, n=n, n_reps=n_reps, seed=seed)
    grid = np.linspace(slopes.min(), slopes.max(), 200)
    sd = slopes.std(ddof=1)
    normal = np.exp(-0.5 * ((grid - true_slope) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
    fig = go.Figure(
        data=[
            _density_bars(slopes, f"傾きの標本分布 (sd = {sd:.4f})"),
            go.Scatter(x=grid, y=normal, mode="lines", name="正規近似"),
        ]
    )
    fig.add_vline(x=true_slope, line={"color": "crimson", "dash": "dash"})
    return apply_defaults(
        fig,
        title=f"回帰係数は推定量である — n = {n} での標本分布",
        xaxis_title="推定された傾き",
        yaxis_title="密度",
    )


def robust_se_comparison(
    seed: int = 0, ns: Sequence[int] = (50, 200, 1000)
) -> go.Figure:
    """Ordinary vs HC3 standard errors under heteroskedasticity (NB09)."""
    rng = np.random.default_rng(seed)
    ns = list(ns)
    ordinary, robust = [], []
    for n in ns:
        x = rng.normal(size=n)
        X = np.column_stack([np.ones(n), x])
        y = 1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.8 * np.abs(x), n)
        fit = regression.ols(X, y)
        ordinary.append(float(fit.se[1]))
        robust.append(float(regression.robust_se(X, fit.resid, kind="HC3")[1]))
    fig = go.Figure(
        data=[
            go.Bar(x=[str(n) for n in ns], y=ordinary, name="通常の標準誤差"),
            go.Bar(x=[str(n) for n in ns], y=robust, name="HC3(頑健)"),
        ]
    )
    return apply_defaults(
        fig,
        title="不均一分散があると通常の標準誤差は当てにならない",
        xaxis_title="標本サイズ",
        yaxis_title="傾きの標準誤差",
    )


def link_function_fits(
    x: np.ndarray, y: np.ndarray, families: Sequence[str] = ("binomial", "gaussian")
) -> go.Figure:
    """The same binary data fitted with different links (NB10)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(x.size), x])
    grid = np.linspace(x.min(), x.max(), 200)
    Xg = np.column_stack([np.ones(grid.size), grid])
    labels = {"binomial": "ロジスティック(logit リンク)", "gaussian": "線形確率モデル(恒等リンク)"}
    traces: list[go.Scatter] = [
        go.Scatter(x=x, y=y, mode="markers", marker={"size": 5, "opacity": 0.4}, name="観測")
    ]
    for family in families:
        fit = glm.irls(X, y, family=family)
        eta = Xg @ fit.params
        mu = 1.0 / (1.0 + np.exp(-eta)) if family == "binomial" else eta
        traces.append(go.Scatter(x=grid, y=mu, mode="lines", name=labels.get(family, family)))
    fig = go.Figure(data=traces)
    fig.add_hline(y=0.0, line={"color": "grey", "dash": "dot"})
    fig.add_hline(y=1.0, line={"color": "grey", "dash": "dot"})
    return apply_defaults(
        fig,
        title="リンク関数が確率を [0, 1] に収める",
        xaxis_title="説明変数",
        yaxis_title="P(y = 1)",
    )


def irls_convergence(
    X: np.ndarray, y: np.ndarray, family: str = "binomial", max_iter: int = 8
) -> go.Figure:
    """Parameter estimates against IRLS iteration count (NB10)."""
    X = np.asarray(X, dtype=float)
    paths = [[] for _ in range(X.shape[1])]
    iters = list(range(1, max_iter + 1))
    for it in iters:
        fit = glm.irls(X, y, family=family, max_iter=it, tol=0.0)
        for j, value in enumerate(fit.params):
            paths[j].append(float(value))
    final = glm.irls(X, y, family=family)
    fig = go.Figure(
        data=[
            go.Scatter(x=iters, y=path, mode="lines+markers", name=f"beta[{j}]")
            for j, path in enumerate(paths)
        ]
    )
    for value in final.params:
        fig.add_hline(y=float(value), line={"color": "grey", "dash": "dot"})
    return apply_defaults(
        fig,
        title=f"IRLS の収束 — {final.n_iter} 反復で収束",
        xaxis_title="反復回数",
        yaxis_title="係数の推定値",
    )
```

`plotting/__init__.py` に `regression` の 5 関数を import して `__all__` に追加する（既存の `core` / `probability` / `inference` の行はそのまま残す）。

- [ ] **Step 4: テストが通ることを確認する**

Run: `/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests/ -q`
Expected: 全て PASS

> `irls_convergence` は `tol=0.0` で反復回数を固定して呼ぶ。`irls` の実装で `max_iter` に達したときに `converged=False` で戻ることを確認しておくこと（例外を投げてはいけない）。

- [ ] **Step 5: lint と commit**

```bash
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics && /home/kazumasa/projects/.venv/bin/ruff format analytics/statistics
git add analytics/statistics/src/stats_textbook/plotting analytics/statistics/tests/test_plotting_regression.py
git commit -m "feat(statistics): figures for regression and GLMs

residual_catalogue puts four designs on one slider precisely because their
coefficient tables look alike. Reading them off the residual plot takes a
second; reading them off the summary takes forever, because the summary
does not contain the information.

coefficient_sampling makes the point the chapter opens with -- a regression
coefficient is an estimator with a distribution -- by simulating that
distribution rather than describing it."
```

---

### Task 11: NB09 — 回帰の推測

**Files:**
- Create: `analytics/statistics/tools/build_nb09.py`
- Create: `analytics/statistics/notebooks/09_regression_inference.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `regression.*`、`plotting.residual_catalogue` / `coefficient_sampling` / `robust_se_comparison`
- Produces: なし

- [ ] **Step 1: `build_nb09.py` を書く**

セットアップセルに `from stats_textbook import glm, regression` を足したものを使う。`cells`:

1. `md` — タイトル `# 09. 回帰の推測 — 係数は推定量である` ＋ 一文要約「回帰の出力は数値ではなく分布である。標準誤差を読めなければ、係数を読んだことにならない」＋「この章で分かること」5 点
2. 標準セットアップセル（`regression` と `glm` を追加）
3. `md` — §1 モデルと仮定。$y = X\beta + \varepsilon$、$E[\varepsilon] = 0$、$\mathrm{Var}(\varepsilon) = \sigma^2 I$、$X$ は固定。**この 3 つ目（等分散かつ無相関）が現実で最も破れやすい**
4. `code` — 係数の標本分布（図）:

```python
code("""
plotting.coefficient_sampling(n=60, n_reps=4000, seed=RANDOM_SEED)
""")
```

5. `md` — §2 係数の分布。$\hat\beta \sim N(\beta, \sigma^2 (X^\top X)^{-1})$。$\sigma^2$ を推定で置き換えると $t$ 分布になる（03 章）
6. `code` — 自前 OLS の出力を読む:

```python
code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 200
X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
y = X @ np.array([1.0, 2.0, -0.5]) + rng.normal(0, 1.5, n)

fit = regression.ols(X, y)
print(f"{'':>10} {'推定値':>10} {'標準誤差':>10} {'t 値':>10} {'p 値':>10}")
for i, name in enumerate(["切片", "x1", "x2"]):
    print(f"{name:>10} {fit.params[i]:10.4f} {fit.se[i]:10.4f} "
          f"{fit.tvalues[i]:10.4f} {fit.pvalues[i]:10.4f}")
print(f"\\nR^2 = {fit.r_squared:.4f}   残差自由度 = {fit.df_resid}")
f, p = regression.f_test_overall(fit, X, y)
print(f"全体の F 検定: F = {f:.3f}, p = {p:.3e}")
""")
```

7. `code` — statsmodels と一致することを確認（本書の姿勢: 自前実装を信じる根拠を示す）:

```python
code("""
import statsmodels.api as sm

ref = sm.OLS(y, X).fit()
print(f"{'':>10} {'本書の実装':>14} {'statsmodels':>14} {'差':>12}")
for i, name in enumerate(["切片", "x1", "x2"]):
    print(f"{name:>10} {fit.params[i]:14.8f} {ref.params[i]:14.8f} "
          f"{abs(fit.params[i] - ref.params[i]):12.2e}")
assert np.allclose(fit.params, ref.params, rtol=1e-10)
assert np.allclose(fit.se, ref.bse, rtol=1e-10)
print("\\n係数も標準誤差も一致する")
""")
```

8. `md` — §3 残差診断。**係数表を見ても仮定が成り立っているかは分からない。** 残差を見る
9. `code` — 病理カタログ（図）:

```python
code("""
plotting.residual_catalogue(seed=1, n=200)
""")
```

10. `code` — 4 つのデータで係数表がどれも似ていることを数値で示す:

```python
code("""
rng = np.random.default_rng(1)
n = 200
x = np.sort(rng.uniform(-3, 3, n))
Xs = np.column_stack([np.ones(n), x])
designs = {
    "健全": 1.0 + 2.0 * x + rng.normal(0, 1.0, n),
    "不均一分散": 1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.6 * np.abs(x), n),
    "非線形": 1.0 + 2.0 * x + 0.7 * x**2 + rng.normal(0, 1.0, n),
}
print(f"{'データ':>12} {'傾き':>10} {'標準誤差':>10} {'p 値':>12} {'R^2':>8}")
for label, yy in designs.items():
    f2 = regression.ols(Xs, yy)
    print(f"{label:>12} {f2.params[1]:10.4f} {f2.se[1]:10.4f} "
          f"{f2.pvalues[1]:12.3e} {f2.r_squared:8.4f}")
print("\\nどれも「傾きは 2 付近で高度に有意」と読める。残差を見ないと違いが分からない")
""")
```

11. `md` — §4 不均一分散と頑健標準誤差。等分散が破れても**係数は不偏のまま**。壊れるのは標準誤差の方である。White のサンドイッチ推定量（HC0–HC3）で直せる
12. `code` — 比較（図と数値）:

```python
code("""
plotting.robust_se_comparison(seed=2, ns=(50, 200, 1000))
""")
```

13. `code` — 被覆率で確かめる（第 2 原則）:

```python
code("""
def coverage_of(kind):
    hits = 0
    reps = 2000
    rng2 = np.random.default_rng(7)
    for _ in range(reps):
        m = 100
        xx = rng2.normal(size=m)
        XX = np.column_stack([np.ones(m), xx])
        yy = 1.0 + 2.0 * xx + rng2.normal(0, 0.3 + 0.8 * np.abs(xx), m)
        f3 = regression.ols(XX, yy)
        se = f3.se[1] if kind == "ordinary" else regression.robust_se(XX, f3.resid, kind)[1]
        if abs(f3.params[1] - 2.0) <= 1.96 * se:
            hits += 1
    return hits / reps

print(f"不均一分散のデータで、傾きの 95% 区間の実測被覆率:")
for kind in ["ordinary", "HC0", "HC3"]:
    print(f"  {kind:>9}: {coverage_of(kind):.4f}")
print("\\n通常の標準誤差では名目 0.95 を下回る。HC3 が最も近い")
""")
```

14. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
等分散の仮定が破れても、係数の推定値は不偏のままである。壊れるのは標準誤差の方である。
だから対処は「係数を捨てる」ことではなく「標準誤差を直す」ことになる。
頑健標準誤差は 1 行で計算でき、仮定が成り立っている場合でもほとんど損をしない。
```
````

15. `md` — §5 多重共線性。説明変数どうしが強く相関すると、個々の係数の分散が跳ね上がる。**予測は悪化しないが、解釈が壊れる**
16. `code` — VIF と係数の不安定さ:

```python
code("""
rng = np.random.default_rng(3)
n = 400
a = rng.normal(size=n)
X2 = np.column_stack([np.ones(n), a, a + rng.normal(0, 0.05, n), rng.normal(size=n)])
y2 = X2 @ np.array([1.0, 2.0, 1.0, -0.5]) + rng.normal(0, 1.0, n)

v = regression.vif(X2)
f4 = regression.ols(X2, y2)
print(f"{'':>8} {'VIF':>10} {'推定値':>10} {'標準誤差':>10}")
for i, name in enumerate(["切片", "a", "a の複製", "独立"]):
    print(f"{name:>8} {v[i]:10.2f} {f4.params[i]:10.4f} {f4.se[i]:10.4f}")
print("\\n相関した 2 本は標準誤差が跳ね上がり、係数の符号すら当てにならない")
print(f"ただし当てはまりは良いまま: R^2 = {f4.r_squared:.4f}")
""")
```

17. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
広告費とブランド認知度のように、実務のデータでは説明変数が絡み合っていることが多い。
このとき「どの施策が効いたか」を係数から読み取ろうとすると、
符号が入れ替わるほど不安定な数字を根拠にすることになる。
予測が目的なら問題にならないという点も、同時に押さえておく必要がある。
```
````

18. `md` — §6 落とし穴（$R^2$ は説明変数を足せば必ず上がる／外れ値と高レバレッジ点は別物／有意性は因果の証拠ではない — `machine_learning` NB09 へリンク）
19. `code` — レバレッジと外れ値:

```python
code("""
rng = np.random.default_rng(4)
n = 60
x5 = np.concatenate([rng.normal(0, 1, n - 1), [8.0]])     # 1 点だけ遠い
X5 = np.column_stack([np.ones(n), x5])
y5 = 1.0 + 2.0 * x5 + rng.normal(0, 1.0, n)
h = regression.leverage(X5)
print(f"レバレッジの合計 = {h.sum():.4f}(= 説明変数の本数 {X5.shape[1]})")
print(f"最大レバレッジ   = {h.max():.4f}(平均 {h.mean():.4f} の {h.max() / h.mean():.1f} 倍)")
print("\\nこの 1 点は当てはめを強く引っ張るが、残差自体は小さいので残差プロットでは目立たない")
""")
```

20. `md` — §7 演習 4 問（(1) $R^2$ が説明変数の追加で必ず上がることを示し、自由度調整済み $R^2$ と比べよ (2) 誤差が自己相関している場合に標準誤差がどうずれるか測れ (3) HC0–HC3 の被覆率を標本サイズ別に比較せよ (4) レバレッジの高い点を除くと係数がどう動くか調べよ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

Expected: 実行 35 秒以内（§4 の被覆実験が最も重い。超えたら `reps` を 2000 → 1000 に下げる）。

- [ ] **Step 3: 本をビルドして目視確認・commit**

```bash
git add analytics/statistics/tools/build_nb09.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/09_regression_inference.ipynb
git commit -m "docs(statistics): NB09 regression as inference

Three designs -- clean, heteroskedastic, and misspecified -- are shown to
produce coefficient tables that read identically: slope near 2, highly
significant, respectable R^2. The residual plot separates them at a
glance. That contrast is the argument for looking at residuals.

The fix is then priced rather than recommended: measured coverage of the
slope's 95% interval under heteroskedasticity, ordinary against HC0 and
HC3, so the reader sees how much the ordinary standard error actually
costs."
```

---

### Task 12: NB10 — 一般化線形モデル

**Files:**
- Create: `analytics/statistics/tools/build_nb10.py`
- Create: `analytics/statistics/notebooks/10_glm.ipynb`（生成物）
- Modify: `analytics/statistics/tools/build_notebooks.py`、`analytics/statistics/book/_toc.yml`

**Interfaces:**
- Consumes: `glm.*`、`distributions.EXPONENTIAL_FAMILIES`、`plotting.link_function_fits` / `irls_convergence`
- Produces: なし

- [ ] **Step 1: `build_nb10.py` を書く**

`cells`:

1. `md` — タイトル `# 10. 一般化線形モデル — 指数型分布族から 1 本の道具へ` ＋ 一文要約「分布とリンク関数を選べば、当てはめの手続きは 1 つで済む」＋「この章で分かること」5 点
2. 標準セットアップセル
3. `md` — §1 なぜ線形回帰では足りないか。二値の応答に直線を当てると、確率が 0 未満や 1 超になる
4. `code` — 線形確率モデルの破綻（図）:

```python
code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 300
x = rng.normal(0, 1.5, n)
y = (rng.random(n) < 1 / (1 + np.exp(-(0.5 + 1.5 * x)))).astype(float)
plotting.link_function_fits(x, y, families=("binomial", "gaussian"))
""")
```

5. `md` — §2 GLM の 3 つの構成要素。(a) 指数型分布族（03 章）(b) 線形予測子 $\eta = X\beta$ (c) リンク関数 $g(\mu) = \eta$。正準リンクは自然母数と $\eta$ を一致させる選び方
6. `code` — 族とリンクの対応表:

```python
code("""
table = [
    ("gaussian", "恒等 g(mu) = mu", "実数", "分散一定"),
    ("binomial", "logit g(mu) = log(mu/(1-mu))", "[0, 1]", "mu(1-mu)"),
    ("poisson", "log g(mu) = log(mu)", "非負整数", "mu"),
]
print(f"{'族':>10} {'正準リンク':>32} {'応答の範囲':>12} {'分散関数':>12}")
for row in table:
    print(f"{row[0]:>10} {row[1]:>32} {row[2]:>12} {row[3]:>12}")
print("\\n分散関数が族ごとに決まる = 重み付き最小二乗の重みが決まる(次節)")
""")
```

7. `md` — §3 IRLS。各反復で作業応答 $z = \eta + (y - \mu)/\frac{d\mu}{d\eta}$ と重み $w = \left(\frac{d\mu}{d\eta}\right)^2 / V(\mu)$ を作り、重み付き最小二乗を解く。正準リンクならこれは Newton–Raphson と一致する
8. `code` — 反復を 1 つずつ表示（自前実装の中身を見せる）:

```python
code("""
X = np.column_stack([np.ones(n), x])
print(f"{'反復':>6} {'切片':>12} {'傾き':>12} {'逸脱度':>12}")
for it in range(1, 7):
    r = glm.irls(X, y, family="binomial", max_iter=it, tol=0.0)
    print(f"{it:6d} {r.params[0]:12.6f} {r.params[1]:12.6f} {r.deviance:12.6f}")
final = glm.irls(X, y, family="binomial")
print(f"\\n収束: {final.n_iter} 反復   真値 (0.5, 1.5)")
""")
```

9. `code` — 収束の図:

```python
code("""
plotting.irls_convergence(X, y, family="binomial", max_iter=8)
""")
```

10. `md` — §4 **statsmodels と一致するか**。自前実装を信じる根拠を示す
11. `code` — 一致の確認:

```python
code("""
import statsmodels.api as sm

mine = glm.irls(X, y, family="binomial")
ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
print(f"{'':>10} {'本書の IRLS':>16} {'statsmodels':>16} {'差':>12}")
for i, name in enumerate(["切片", "傾き"]):
    print(f"{name:>10} {mine.params[i]:16.10f} {ref.params[i]:16.10f} "
          f"{abs(mine.params[i] - ref.params[i]):12.2e}")
print(f"{'逸脱度':>10} {mine.deviance:16.10f} {ref.deviance:16.10f} "
      f"{abs(mine.deviance - ref.deviance):12.2e}")
assert np.allclose(mine.params, ref.params, rtol=1e-8)
assert np.allclose(mine.se, ref.bse, rtol=1e-7)
print("\\n係数・標準誤差・逸脱度すべて一致する")
""")
```

12. `md` — §5 ポアソン回帰。カウントデータ。$\log \mu = X\beta$ なので係数は**倍率**として読む（$e^\beta$ 倍）
13. `code` — ポアソン回帰と係数の読み方:

```python
code("""
rng = np.random.default_rng(1)
m = 300
Xp = np.column_stack([np.ones(m), rng.normal(size=m)])
yp = rng.poisson(np.exp(Xp @ np.array([0.7, 0.4]))).astype(float)
fp = glm.irls(Xp, yp, family="poisson")
print(f"係数 = {fp.params.round(6)}   標準誤差 = {fp.se.round(6)}")
print(f"逸脱度 = {fp.deviance:.6f}   反復 = {fp.n_iter}")
print(f"\\n傾き {fp.params[1]:.4f} -> 説明変数が 1 増えると期待件数が "
      f"{np.exp(fp.params[1]):.4f} 倍になる")
""")
```

14. `md` — §6 逸脱度と過分散。逸脱度は「飽和モデルとの対数尤度の差の 2 倍」。ポアソンは平均＝分散を仮定しているので、実データで分散が大きいと**標準誤差が過小になる**
15. `code` — 過分散の検出:

```python
code("""
rng = np.random.default_rng(4)
k = 2000
Xo = np.column_stack([np.ones(k), rng.normal(size=k)])
mu = np.exp(Xo @ np.array([1.0, 0.5]))

true_poisson = rng.poisson(mu).astype(float)
overdispersed = rng.negative_binomial(2.0, 2.0 / (2.0 + mu)).astype(float)

print(f"{'データ':>18} {'分散/平均の比':>16} {'過分散統計量':>16}")
for label, data in [("真のポアソン", true_poisson), ("負の二項(過分散)", overdispersed)]:
    fo = glm.irls(Xo, data, family="poisson")
    phi = glm.dispersion(fo, data, Xo, "poisson")
    print(f"{label:>18} {data.var() / data.mean():16.4f} {phi:16.4f}")
print("\\n過分散統計量が 1 から大きく離れたら、標準誤差は sqrt(phi) 倍に補正する必要がある")
""")
```

16. `md` — 💡 核心コールアウト:

````
```{admonition} 核心 — ひとことで
:class: tip
GLM は「分布・リンク関数・線形予測子」の 3 つを選ぶだけで、当てはめの手続きは共通である。
その共通の手続きが IRLS で、各反復は重み付き最小二乗にすぎない。
分布ごとに別々のアルゴリズムを覚える必要がないのは、指数型分布族という共通の骨格のおかげである。
```
````

17. `md` — 🌍 実社会コールアウト:

````
```{admonition} 実社会では
:class: note
保険の請求件数、ウェブサイトのクリック、故障件数。
いずれもポアソン回帰の出番だが、実データはほぼ必ず過分散である。
過分散を見ずにポアソンを当てると、標準誤差が小さく出て「有意」が量産される。
当てはめの前に分散と平均の比を見る習慣が、そのまま誤りを防ぐ。
```
````

18. `md` — §7 落とし穴（完全分離（perfect separation）でロジスティック回帰の係数が発散する／リンク関数の選択はモデルの一部であり後付けで変えられない／逸脱度の絶対値には意味がなく、比較にしか使えない）
19. `code` — 完全分離:

```python
code("""
# 説明変数が y を完全に決めてしまうと、尤度は最大値に到達しない
xs = np.array([-3.0, -2.0, -1.0, 1.0, 2.0, 3.0])
ys = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
Xs = np.column_stack([np.ones(6), xs])
r = glm.irls(Xs, ys, family="binomial", max_iter=50)
print(f"係数 = {r.params.round(3)}   収束した: {r.converged}")
print(f"当てはめ確率 = {r.fitted.round(6)}")
print("\\n傾きが発散していく。データが分離していると最尤推定量が存在しない")
""")
```

20. `md` — §8 演習 4 問（(1) プロビットリンクで当てはめ、logit と比較せよ (2) 過分散に対する準ポアソン補正（標準誤差を $\sqrt{\phi}$ 倍）の被覆率を測れ (3) IRLS が Newton–Raphson と一致することを正準リンクの場合に示せ (4) オフセット項を入れたポアソン回帰（露出時間の調整）を実装せよ）

- [ ] **Step 2: 登録・生成・実行・出力点検・時間計測**

Expected: 実行 25 秒以内。§4 の一致確認セルの `assert` が通ることが、この章の成立条件である。
§7 の完全分離では `converged=False` になる（例外にはならない）ことを確認する。

- [ ] **Step 3: 本をビルドして目視確認・commit**

```bash
git add analytics/statistics/tools/build_nb10.py analytics/statistics/tools/build_notebooks.py \
        analytics/statistics/book/_toc.yml analytics/statistics/notebooks/10_glm.ipynb
git commit -m "docs(statistics): NB10 generalised linear models

Shows the IRLS loop iteration by iteration before naming it, then asserts
in the notebook itself that the result matches statsmodels to 1e-8. The
assert is the point: a chapter that says 'here is how the library does it'
should fail loudly if it does not.

Overdispersion gets equal billing with the fitting. Negative-binomial
counts fitted as Poisson are shown to look fine coefficient-wise while the
dispersion statistic gives them away, which is the diagnostic that keeps
Poisson regression honest in practice."
```

---

### Task 13: Plan 2 の仕上げ

**Files:**
- Modify: `analytics/statistics/README.md`
- Modify: `docs/superpowers/specs/2026-08-01-analytics-statistics-design.md`
- Modify: `analytics/statistics/notebooks/*.ipynb`（全章の再実行）

**Interfaces:**
- Consumes: Task 1–12 の全成果
- Produces: なし（Plan 3 の起点となる実測値を記録する）

- [ ] **Step 1: 全 11 章を頭から再実行し、章ごとの時間を測る**

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
    assert r.returncode == 0, r.stderr.decode()[-800:]
    total += dt
    print(f"{nb.name:<44} {dt:6.1f}s {nb.stat().st_size/1024:9.1f} KB")
print(f"{'合計':<44} {total:6.1f}s")
print(f"全 14 章 300 秒の予算に対する残り: {300 - total:.1f}s / 3 章")
PY
```

Expected: 11 章の合計が **190 秒以内**（Plan 3 の 3 章に 110 秒以上残す）。超えた章は反復数を下げて測り直す。

- [ ] **Step 2: 全テストと lint**

```bash
/home/kazumasa/projects/.venv/bin/python -m pytest analytics/statistics/tests -q
/home/kazumasa/projects/.venv/bin/ruff check analytics/statistics
/home/kazumasa/projects/.venv/bin/ruff format --check analytics/statistics
```

Expected: 全て PASS。想定テスト数は **65 + 11(estimation) + 10(intervals) + 13(testing) + 10(plotting_inference) + 12(regression) + 9(glm) + 8(plotting_regression) = 138 前後**。実測値を記録する。

- [ ] **Step 3: 他の教材を壊していないことを確認する**

```bash
W=/home/kazumasa/projects/.claude/worktrees/analytics-statistics-plan2
PYTHONPATH=$W/analytics/bayesian/src:$W/analytics/neural_net/src:$W/analytics/linear_algebra/src \
  /home/kazumasa/projects/.venv/bin/python -m pytest analytics/ -q
```

Expected: PASS。`PYTHONPATH` を付けるのは、root の `.venv` の editable install が main ツリー側を読むため（並行セッションの編集が混ざるのを避ける）。

- [ ] **Step 4: 本を通しでビルドして全 11 章を目視確認**

```bash
rm -rf analytics/statistics/book/_build
/home/kazumasa/projects/.venv/bin/jupyter-book build analytics/statistics/book/
```

`_build/html/index.html` から 11 章すべてを開き、次を確認する。

- 新しいインタラクティブ図が動く（MLE 標本分布・検出力曲線・残差カタログ・IRLS 収束）
- **被覆確率の図**（NB07）で赤い区間が真値の縦線を跨いでいない
- コールアウトが 💡/🌍 の 2 種で描画され、太字が崩れていない
- 数式に日本語が入っていない

さらに、レンダリング後の HTML に literal な `**` が残っていないことを走査する。

```bash
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
        bad += len(hits)
        print(f"{f.name}: {len(hits)} 件"); [print("   ", h.replace("\n"," ")) for h in hits[:3]]
print(f"literal ** in prose: {bad}")
PY
```

Expected: `literal ** in prose: 0`

- [ ] **Step 5: README を実測値で更新する**

`analytics/statistics/README.md` の章構成表で NB06–10 の行を ✅ に変え、実測実行時間を入れる。
「第Ⅰ部の実測値」の段落を第Ⅰ部＋第Ⅱ部前半の実測値に書き換える。
共通コードの表に `estimation` / `intervals` / `testing` / `regression` / `glm` /
`plotting/inference` / `plotting/regression` の行を足す。
テスト数の内訳も実測値に更新する。

**目標値ではなく実測値を書くこと。**

- [ ] **Step 6: 設計書に Plan 2 の実測結果を記録する**

`docs/superpowers/specs/2026-08-01-analytics-statistics-design.md` の §10 の表で Plan 2 を「完了」にし、
Plan 1 と同形式の実測結果ブロックを足す。**Plan 3 が引き継ぐ前提**として少なくとも次を書く。

- 残りの実行時間予算（秒 / 3 章）
- 新しく確立した規約（あれば）
- 11 章のうち最も重い章とその理由

- [ ] **Step 7: commit**

```bash
git add analytics/statistics docs/
git commit -m "docs(statistics): complete Part II's first half -- measured numbers

Records what the eleven chapters actually cost rather than what they were
budgeted, and what Plan 3 inherits: the remaining notebook time, the test
count, and which chapter is the expensive one.

Also re-scans the built HTML for literal asterisks. The CJK bold trap is
silent at build time, so the only way to know the prose rendered is to
look at what was rendered."
```

---

## Plan 2 完了時の状態

| 項目 | 予定 |
|---|---|
| ソースモジュール | Plan 1 の 6 本 ＋ `estimation` `intervals` `testing` `regression` `glm` ＋ `plotting/{inference,regression}` |
| テスト | 138 本前後（実測を README と設計書に記録） |
| Notebook | 00–10 の 11 章 |
| インタラクティブ図 | 8 点（Plan 1）＋ 11 点（Plan 2）＝ 19 点前後 |
| コールアウト | 核心 11・実社会 11 |
| `statsmodels` | Task 8 以降で照合先として使用（`regression.py` / `glm.py` 本体は import しない） |

**Plan 2 では触らないもの**: NB11 橋渡し章・NB12 キャップストーン・NB13 演習解答（Plan 3）、
report ポータル統合（Plan 3）、`analytics/report/report_builder/figures.py`（Plan 3）。
