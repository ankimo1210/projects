"""Hull §22.8: previsible forecasts and finite-sample exception counts."""

import math
from itertools import pairwise

import numpy as np
import pytest
from hullkit import _market_risk as m
from scipy.stats import chi2


def test_forecasts_use_only_previous_window_and_align_realized_profit():
    pnl = np.array([1, -2, 3, -4, 5, -6, 7, -8], dtype=float)
    result = m.rolling_var(pnl, 3, lambda past: -min(past))
    assert result["indices"] == pytest.approx(np.arange(3, 8))
    assert result["forecasts"] == pytest.approx([2, 4, 4, 6, 6])
    assert result["pnl"] == pytest.approx(pnl[3:])
    changed = pnl.copy()
    changed[6:] = 1000
    again = m.rolling_var(changed, 3, lambda past: -min(past))
    assert again["forecasts"][:4] == pytest.approx(result["forecasts"][:4])


@pytest.mark.parametrize("count", [1, 7])
def test_source_1_and_7_percent_example_with_explicit_synthetic_sample_size(count):
    # Hull provides percentages, not n; choose 100 days explicitly for this test.
    pnl = np.ones(100)
    pnl[:count] = -2
    result = m.backtest_summary(pnl, np.ones(100))
    assert result["exceedance_rate"] == pytest.approx(count / 100)
    exact = sum(math.comb(100, k) * 0.01**k * 0.99 ** (100 - k) for k in range(count, 101))
    assert result["binomial_upper_tail"] == pytest.approx(exact)
    observed = count / 100
    lr = -2 * ((100 - count) * math.log(0.99 / (1 - observed)) + count * math.log(0.01 / observed))
    assert result["kupiec"][0] == pytest.approx(lr)
    assert result["kupiec"][1] == pytest.approx(chi2.sf(lr, 1))


def test_transition_counts_independent_likelihood_and_equal_threshold():
    flags = np.array([0, 0, 1, 1, 0, 1, 0, 0, 0, 1])
    pnl = np.where(flags, -2, -1)  # equality to threshold is not an exception
    result = m.backtest_summary(pnl, np.ones(10))
    counts = np.zeros((2, 2), dtype=int)
    for first, second in pairwise(flags):
        counts[first, second] += 1
    assert result["transitions"] == pytest.approx(counts)
    p = counts[:, 1].sum() / counts.sum()
    log_null = sum(counts[i, j] * math.log(p if j else 1 - p) for i in range(2) for j in range(2))
    log_alt = 0
    for row in counts:
        prob = row[1] / row.sum()
        log_alt += sum(n * math.log(prob if j else 1 - prob) for j, n in enumerate(row) if n)
    assert result["independence"][0] == pytest.approx(2 * (log_alt - log_null))


def test_same_frequency_does_not_establish_es_quality():
    small = m.backtest_summary([-2, 0, 0, 0], [1] * 4)
    large = m.backtest_summary([-20, 0, 0, 0], [1] * 4)
    assert small["exceedance_rate"] == large["exceedance_rate"]
    assert small["realized_tail_mean"] == 2
    assert large["realized_tail_mean"] == 20
