"""Signal-layer tests: common schema, baseline orientation, combination, causality.

Signals must be standardized (comparable), correctly oriented (direction), safely
combinable, and — like features — free of look-ahead in their scores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from irp import signals as S
from irp.signals.schema import Signal, SignalCategory


def _trending_panel(n=300):
    """Five assets with strictly increasing drift A<B<C<D<E (known momentum order)."""
    idx = pd.bdate_range("2020-01-01", periods=n)
    drifts = {"A": 0.0000, "B": 0.0003, "C": 0.0006, "D": 0.0009, "E": 0.0012}
    return pd.DataFrame({a: 100 * np.exp(np.arange(n) * g) for a, g in drifts.items()}, index=idx)


def _vol_panel(n=200):
    """Two calm + two wild assets (known volatility order), same gentle drift."""
    idx = pd.bdate_range("2020-01-01", periods=n)
    t = np.arange(n)
    calm = 0.001 * (-1) ** t
    wild = 0.05 * (-1) ** t
    data = {
        "calm1": 100 * np.exp(np.cumsum(calm)),
        "calm2": 100 * np.exp(np.cumsum(calm + 0.0001)),
        "wild1": 100 * np.exp(np.cumsum(wild)),
        "wild2": 100 * np.exp(np.cumsum(wild + 0.0001)),
    }
    return pd.DataFrame(data, index=idx)


# --- schema -------------------------------------------------------------------
def test_signal_schema_validates():
    df = pd.DataFrame({"A": [0.1], "B": [-0.1]}, index=pd.bdate_range("2020-01-01", periods=1))
    sig = Signal("x", SignalCategory.TREND, df, direction=-1)
    assert sig.oriented.iloc[0]["A"] == pytest.approx(-0.1)  # score * direction
    with pytest.raises(ValueError):
        Signal("x", SignalCategory.TREND, df, direction=0)
    with pytest.raises(TypeError):
        Signal("x", SignalCategory.TREND, df["A"])  # Series, not DataFrame


def test_signal_lag_shifts_in_time():
    df = pd.DataFrame({"A": [1.0, 2.0, 3.0]}, index=pd.bdate_range("2020-01-01", periods=3))
    sig = Signal("x", SignalCategory.TREND, df)
    lagged = sig.lag(1).score["A"].tolist()
    assert np.isnan(lagged[0]) and lagged[1] == 1.0 and lagged[2] == 2.0


# --- baseline orientation -----------------------------------------------------
def test_momentum_ranks_high_drift_top():
    sig = S.momentum_signal(_trending_panel(), lookback=120, skip=0)
    last = sig.oriented.iloc[-1]
    assert last.idxmax() == "E" and last.idxmin() == "A"
    assert sig.category == SignalCategory.TREND


def test_low_vol_prefers_calm_assets():
    sig = S.low_volatility_signal(_vol_panel(), window=20)
    last = sig.oriented.dropna().iloc[-1]
    # direction = -1 -> calm names get the HIGHER oriented score
    assert last["calm1"] > last["wild1"]
    assert sig.category == SignalCategory.RISK


def test_scores_are_cross_sectionally_standardized():
    sig = S.momentum_signal(_trending_panel(), lookback=120, skip=0)
    row = sig.score.iloc[-1]
    assert row.mean() == pytest.approx(0.0, abs=1e-9)  # z-score: row mean 0


# --- combination --------------------------------------------------------------
def test_combine_averages_oriented_scores():
    p = _trending_panel()
    a = S.momentum_signal(p, lookback=120, skip=0)
    b = S.trend_following_signal(p, window=100)
    comp = S.combine([a, b])
    expected = (a.oriented.iloc[-1] + b.oriented.iloc[-1]) / 2
    pd.testing.assert_series_equal(comp.score.iloc[-1], expected, check_names=False)
    assert comp.meta["components"] == ["momentum", "trend_following"]


def test_long_short_quantile_is_dollar_neutral():
    sig = S.momentum_signal(_trending_panel(), lookback=120, skip=0)
    w = S.long_short_quantile(sig.oriented, quantile=0.4)
    last = w.iloc[-1]
    assert last.sum() == pytest.approx(0.0, abs=1e-9)  # net zero
    assert last.abs().sum() == pytest.approx(2.0, abs=1e-9)  # gross 2 (1 long + 1 short)
    assert last["E"] > 0 and last["A"] < 0  # high momentum long, low short


# --- registry -----------------------------------------------------------------
def test_registry_lists_and_resolves():
    assert set(S.available()) == {
        "momentum",
        "trend_following",
        "low_volatility",
        "mean_reversion",
        "macro_trend",
    }
    assert S.get_signal("momentum") is S.momentum_signal
    with pytest.raises(KeyError):
        S.get_signal("does_not_exist")


def test_planned_families_raise_clearly():
    for name in ("value", "quality", "carry"):
        builder = S.get_signal(name)
        with pytest.raises(NotImplementedError):
            builder(_trending_panel())


# --- causality ----------------------------------------------------------------
def test_signal_scores_are_causal():
    p = _trending_panel()

    def score_of(prices):
        return S.momentum_signal(prices, lookback=120, skip=0).score

    full = score_of(p)
    for k in (150, 220):
        pd.testing.assert_frame_equal(score_of(p.iloc[:k]), full.iloc[:k], check_freq=False)
