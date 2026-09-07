import itertools

import numpy as np
import pandas as pd
import pytest
from timesfm_lab.datasets import FINANCE_SPECS, build_windows
from timesfm_lab.finance import (
    CACHE,
    POST_CUTOFF,
    FinanceWindowPlan,
    _parkinson,
    build_targets,
    load_ohlcv,
)

needs_data = pytest.mark.skipif(
    not CACHE.exists(), reason="run scripts/fetch_finance.py first"
)


def test_parkinson_scales_with_the_log_range():
    high = np.array([110.0, 101.0])
    low = np.array([100.0, 100.0])
    got = _parkinson(high, low)
    want = np.log(high / low) / np.sqrt(4.0 * np.log(2.0))
    np.testing.assert_allclose(got, want)
    assert got[0] > got[1]


def test_parkinson_rejects_a_nonpositive_range():
    out = _parkinson(np.array([100.0, 0.0]), np.array([100.0, 100.0]))
    assert np.isnan(out).all()


def test_window_plan_stops_before_the_training_cutoff():
    """The point of the financial section: no held-out point may predate the model."""
    dates = pd.date_range("2020-01-01", periods=2000, freq="B").to_numpy()
    plan = FinanceWindowPlan(context_length=100, horizon=20, n_windows=50)
    cuts = plan.cutoffs(dates)
    assert cuts
    for c in cuts:
        assert pd.Timestamp(dates[c]) >= POST_CUTOFF


def test_window_plan_yields_no_windows_when_all_history_predates_the_cutoff():
    dates = pd.date_range("2019-01-01", periods=900, freq="B").to_numpy()
    assert FinanceWindowPlan(context_length=100, horizon=20).cutoffs(dates) == []


def test_window_plan_cutoffs_do_not_overlap():
    dates = pd.date_range("2020-01-01", periods=2000, freq="B").to_numpy()
    plan = FinanceWindowPlan(context_length=100, horizon=20, n_windows=6)
    cuts = plan.cutoffs(dates)
    assert all(b - a >= plan.horizon for a, b in itertools.pairwise(cuts))


@needs_data
def test_targets_are_finite_and_long_enough():
    tg = build_targets(load_ohlcv())
    assert set(tg) == {"fin_log_volume", "fin_range_vol", "fin_log_return"}
    for key, series in tg.items():
        assert series, key
        for _ticker, values, dates in series:
            assert np.isfinite(values).all()
            assert len(values) == len(dates) >= 800


@needs_data
@pytest.mark.parametrize("spec", FINANCE_SPECS, ids=lambda s: s.key)
def test_every_financial_window_is_held_out_by_the_calendar(spec):
    from timesfm_lab.finance import build_targets as bt
    from timesfm_lab.finance import load_ohlcv as lo

    dates_by_ticker = {t: d for t, _v, d in bt(lo())[spec.key]}
    ws = build_windows(spec)
    assert ws
    for w in ws:
        first_held_out = pd.Timestamp(dates_by_ticker[w.series_id][w.cutoff])
        assert first_held_out >= POST_CUTOFF, (w.series_id, first_held_out)
        assert w.context.shape == (spec.context_length,)
        assert w.actual.shape == (spec.horizon,)
