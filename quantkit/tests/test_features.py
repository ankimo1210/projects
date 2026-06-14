"""Feature-layer rigor: causality (no look-ahead), correctness, and no silent fill.

The signature invariant of this platform is *causality*: ``feature(x)[t]`` may
depend only on ``x`` up to ``t``. We test it directly — computing a feature on a
series truncated at ``k`` must reproduce, exactly, the first ``k`` values computed
on the full series. If anything peeked at the future, truncation would change the
earlier output.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quantkit.features import macro as M
from quantkit.features import price as P
from quantkit.macro.schema import MacroObservation, to_macro_frame


def _series(vals):
    idx = pd.bdate_range("2020-01-01", periods=len(vals))
    return pd.Series(vals, index=idx, dtype="float64")


def _panel(seed=0, n=260, k=5):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    steps = rng.normal(0.0005, 0.01, size=(n, k))
    prices = 100 * np.exp(np.cumsum(steps, axis=0))
    return pd.DataFrame(prices, index=idx, columns=list("ABCDE")[:k])


def assert_causal(func, x, ks=(30, 90, 180)):
    """func(x[:k]) must equal func(x)[:k] exactly (NaNs included)."""
    full = func(x)
    for k in ks:
        truncated = func(x.iloc[:k])
        if isinstance(full, pd.DataFrame):
            pd.testing.assert_frame_equal(truncated, full.iloc[:k], check_freq=False)
        else:
            pd.testing.assert_series_equal(truncated, full.iloc[:k], check_freq=False)


# --- causality across every price feature ------------------------------------
@pytest.mark.parametrize(
    "func",
    [
        lambda x: P.returns(x, 5),
        lambda x: P.returns(x, 1, log=True),
        lambda x: P.cumulative_return(x, 20),
        lambda x: P.momentum(x, lookback=120, skip=20),
        lambda x: P.moving_average(x, 50),
        lambda x: P.ma_ratio(x, 50),
        lambda x: P.realized_volatility(x, 21),
        lambda x: P.rolling_volatility(P.returns(x), 21),
        lambda x: P.ewma_volatility(P.returns(x), 20),
        lambda x: P.rolling_zscore(x, 60),
        lambda x: P.drawdown(x),
        lambda x: P.cross_sectional_zscore(x),
        lambda x: P.cross_sectional_rank(x),
    ],
)
def test_price_features_are_causal(func):
    assert_causal(func, _panel())


def test_rsi_is_causal():
    assert_causal(P.rsi, _panel()["A"])


# --- hand-computed correctness ------------------------------------------------
def test_returns_values():
    s = _series([100, 110, 121])
    r = P.returns(s)
    assert np.isnan(r.iloc[0])
    assert r.iloc[1] == pytest.approx(0.1)
    assert r.iloc[2] == pytest.approx(0.1)
    lr = P.returns(s, log=True)
    assert lr.iloc[1] == pytest.approx(np.log(1.1))


def test_momentum_skips_recent():
    s = _series([100, 110, 121, 133.1])
    # lookback=3, skip=1: at t=3 -> price[t-1]/price[t-3] - 1 = 121/100 - 1
    # (the most recent bar, 133.1, is skipped — that is the point of `skip`)
    m = P.momentum(s, lookback=3, skip=1)
    assert m.iloc[3] == pytest.approx(121 / 100 - 1)
    with pytest.raises(ValueError):
        P.momentum(s, lookback=2, skip=2)


def test_drawdown_from_running_peak():
    s = _series([100, 120, 90, 95])
    dd = P.drawdown(s)
    assert dd.iloc[1] == pytest.approx(0.0)
    assert dd.iloc[2] == pytest.approx(90 / 120 - 1)
    assert dd.iloc[3] == pytest.approx(95 / 120 - 1)
    assert (dd <= 1e-12).all()


def test_cross_sectional_zscore_and_rank():
    idx = pd.bdate_range("2020-01-01", periods=1)
    row = pd.DataFrame([[1.0, 2.0, 3.0]], index=idx, columns=["A", "B", "C"])
    z = P.cross_sectional_zscore(row)
    assert z.iloc[0].tolist() == pytest.approx([-1.0, 0.0, 1.0])  # sample std = 1
    r = P.cross_sectional_rank(row)
    assert r.iloc[0].tolist() == pytest.approx([1 / 3, 2 / 3, 1.0])


def test_cross_sectional_zscore_needs_min_count():
    idx = pd.bdate_range("2020-01-01", periods=1)
    row = pd.DataFrame([[1.0, 2.0, np.nan]], index=idx, columns=["A", "B", "C"])
    z = P.cross_sectional_zscore(row, min_count=3)
    assert z.iloc[0].isna().all()  # only 2 valid < min_count -> all NaN, not guessed


# --- the no-silent-fill guarantee --------------------------------------------
def test_returns_do_not_forward_fill_gaps():
    s = _series([100, np.nan, 121])
    r = P.returns(s)
    # if pct_change forward-filled the gap, iloc[2] would be 0.21; it must be NaN.
    assert np.isnan(r.iloc[2])


# --- macro features are point-in-time ----------------------------------------
def _revised_frame(extra=False):
    obs = [
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-15"),
            3.0,
            "ALFRED",
            vintage_available=True,
        ),
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-03-15"),
            3.2,
            "ALFRED",
            vintage_available=True,
        ),
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-02-01"),
            pd.Timestamp("2024-02-29"),
            pd.Timestamp("2024-03-15"),
            2.8,
            "ALFRED",
            vintage_available=True,
        ),
    ]
    if extra:  # a FUTURE vintage that must not affect earlier feature dates
        obs.append(
            MacroObservation(
                "cpi",
                "US",
                pd.Timestamp("2024-03-01"),
                pd.Timestamp("2024-03-31"),
                pd.Timestamp("2024-04-15"),
                2.5,
                "ALFRED",
                vintage_available=True,
            )
        )
    return to_macro_frame(obs)


def test_pit_feature_uses_only_visible_release():
    f = _revised_frame()
    dates = ["2024-02-20", "2024-03-20"]
    feat = M.pit_feature_frame(f, dates)
    # 02-20: only Jan's ORIGINAL print is out (3.0); Feb not yet, Jan revision is future
    assert feat.loc["2024-02-20", "value"] == 3.0
    assert feat.loc["2024-02-20", "period_start"] == pd.Timestamp("2024-01-01")
    # 03-20: Feb is the latest visible period (2.8)
    assert feat.loc["2024-03-20", "value"] == 2.8
    assert feat.loc["2024-02-20", "days_since_release"] == 5  # 02-20 minus 02-15


def test_pit_feature_is_causal_to_future_vintages():
    base = M.pit_feature_frame(_revised_frame(), ["2024-02-20", "2024-03-20"])
    withfuture = M.pit_feature_frame(_revised_frame(extra=True), ["2024-02-20", "2024-03-20"])
    # adding an April release cannot change Feb/Mar feature values
    pd.testing.assert_frame_equal(base, withfuture)


def test_pit_change_uses_visible_periods():
    f = _revised_frame()
    chg = M.pit_change(f, ["2024-03-20"], periods=1)
    # at 03-20 visible periods: Jan=3.2 (revised), Feb=2.8 -> change 2.8/3.2 - 1
    assert chg.loc["2024-03-20"] == pytest.approx(2.8 / 3.2 - 1)
