from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import Forecasts, strategy_returns
from bond_timing.stages import primary_tests, strategy_weights, summary


def test_primary_tests_apply_holm_over_five_and_two():
    rng = np.random.default_rng(0)
    months = pd.period_range("2000-02", periods=228, freq="M")
    hold = pd.Series(rng.normal(0.003, 0.02, 228), index=months)
    returns = {
        "hold": hold,
        "slope": hold * 0.5,
        "ols_p": hold + 0.004,
        "ols_pm": hold,
        "nn_fm": hold + 0.004,
        "et": hold - 0.001,
    }
    tests = primary_tests(returns, "slope")
    assert set(tests["vs_hold"]) == {"P1", "P2", "P3", "P4", "P5"}
    assert set(tests["vs_p1"]) == {"P4", "P5"}
    assert tests["vs_hold"]["P2"]["p_holm"] < 0.05
    assert tests["vs_hold"]["P3"]["p_holm"] == 1.0
    assert all(t["p_holm"] >= t["p_cer"] for t in tests["vs_hold"].values())


def test_summary_counts_switches_and_hold_share():
    decisions = pd.period_range("2000-01", periods=6, freq="M")
    weights = pd.Series([1, 1, 0, 0, 1, 1], index=decisions, dtype=float)
    out = summary(strategy_returns(weights, pd.Series(0.01, index=decisions + 1)), weights)
    assert out["switches"] == 2 and out["months"] == 6
    assert out["hold_share"] == pytest.approx(4 / 6)


def test_strategy_weights_cover_rules_models_and_benchmarks():
    index = pd.period_range("1999-01", "2001-12", freq="M")
    study = SimpleNamespace(
        zeros=pd.DataFrame({120: 0.05}, index=index), bey=pd.Series(0.04, index=index)
    )
    outcomes = SimpleNamespace(excess=pd.DataFrame({"tlt": 0.01}, index=index))
    decisions = pd.period_range("2000-01", "2000-12", freq="M")
    forecasts = Forecasts({"et": pd.DataFrame({0: -0.01}, index=decisions)}, {})
    w = strategy_weights(study, outcomes, decisions, forecasts, None, "tlt")
    assert set(w) == {"hold", "cash", "slope", "trend", "cp", "et"}
    assert w["slope"].eq(1.0).all() and w["trend"].eq(1.0).all()
    assert w["cp"].eq(0.0).all() and w["et"].eq(0.0).all() and w["cash"].eq(0.0).all()
