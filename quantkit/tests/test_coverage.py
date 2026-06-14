"""Coverage-expansion tests: risk decomposition, regime detection, diagnostics.

These probe the new analysis layers added on top of the existing signal/backtest
stack — each kept causal (no look-ahead) where it touches time, consistent with
the platform's banner invariant.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quantkit.labels import forward_return

from quantkit import diagnostics as DG
from quantkit import regime as RG
from quantkit import risk as RK


def _dates(n):
    return pd.bdate_range("2018-01-01", periods=n)


# --- risk decomposition -------------------------------------------------------
def test_portfolio_vol_hand_value():
    cov = pd.DataFrame([[0.04, 0.00], [0.00, 0.09]], index=["X", "Y"], columns=["X", "Y"])
    w = pd.Series({"X": 0.5, "Y": 0.5})
    # var = 0.25*0.04 + 0.25*0.09 = 0.0325 -> vol = sqrt(0.0325)
    assert RK.portfolio_vol(w, cov) == pytest.approx(np.sqrt(0.0325))


def test_component_risk_sums_to_total_vol():
    rng = np.random.default_rng(0)
    a = rng.standard_normal((300, 4))
    cov = pd.DataFrame(np.cov(a, rowvar=False), index=list("ABCD"), columns=list("ABCD"))
    w = pd.Series({"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1})
    comp = RK.component_risk(w, cov)  # Euler decomposition, in vol units
    assert comp.sum() == pytest.approx(RK.portfolio_vol(w, cov))  # contributions add to total
    assert list(comp.index) == list("ABCD")


def test_pca_factors_finds_one_dominant_factor():
    rng = np.random.default_rng(1)
    n, k = 500, 6
    market = rng.standard_normal(n)
    rets = pd.DataFrame(
        {f"S{i}": market + 0.2 * rng.standard_normal(n) for i in range(k)},
        index=_dates(n),
    )
    pca = RK.pca_factors(rets, n_components=3)
    assert pca.explained_variance_ratio.iloc[0] > 0.8  # one common factor dominates
    assert RK.effective_n_bets(rets) < 2.0  # risk concentrated in ~1 bet


def test_effective_n_bets_independent_assets():
    rng = np.random.default_rng(2)
    rets = pd.DataFrame(rng.standard_normal((600, 5)), columns=list("VWXYZ"), index=_dates(600))
    assert RK.effective_n_bets(rets) > 3.5  # ~5 independent bets


# --- regime detection (causal) ------------------------------------------------
def _calm_then_turbulent(n=600, seed=3):
    rng = np.random.default_rng(seed)
    half = n // 2
    r = np.concatenate([0.003 * rng.standard_normal(half), 0.02 * rng.standard_normal(n - half)])
    return pd.Series(r, index=_dates(n))


def test_vol_regime_separates_calm_from_turbulent():
    r = _calm_then_turbulent()
    reg = RG.vol_regime(r, lookback=21, n_states=3, min_history=126)
    early = reg.iloc[150:250].mean()
    late = reg.iloc[450:550].mean()
    assert late > early  # turbulent half sits in higher vol states


def test_vol_regime_is_causal():
    r = _calm_then_turbulent()
    full = RG.vol_regime(r, lookback=21, n_states=3, min_history=126)
    cut = 400
    prefix = RG.vol_regime(r.iloc[:cut], lookback=21, n_states=3, min_history=126)
    # the regime at each past date must not change when future data is appended
    pd.testing.assert_series_equal(full.iloc[:cut].dropna(), prefix.dropna())


def test_trend_regime_tracks_direction():
    up = pd.Series(np.linspace(100, 200, 300), index=_dates(300))
    down = pd.Series(np.linspace(200, 100, 300), index=_dates(300))
    assert RG.trend_regime(up, fast=10, slow=50).iloc[-1] == 1
    assert RG.trend_regime(down, fast=10, slow=50).iloc[-1] == -1


def test_regime_summary_table():
    r = _calm_then_turbulent()
    reg = RG.vol_regime(r, lookback=21, n_states=3, min_history=126)
    tbl = RG.regime_summary(r, reg)
    assert {"mean", "vol", "sharpe", "count"}.issubset(tbl.columns)
    assert tbl["vol"].is_monotonic_increasing  # higher state -> higher realized vol


# --- diagnostics: IC decay, factor exposure, capacity -------------------------
def test_ic_decay_falls_with_horizon():
    rng = np.random.default_rng(4)
    n, k = 260, 30
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(0.01 * rng.standard_normal((n, k)), axis=0)),
        index=_dates(n),
        columns=[f"A{i}" for i in range(k)],
    )
    signal = forward_return(prices, horizon=1)  # a perfect 1-day-ahead oracle signal
    decay = DG.ic_decay(signal, prices, horizons=[1, 5, 10])
    assert decay.loc[1] > decay.loc[5] > 0  # predictive power fades with horizon


def test_factor_exposure_recovers_beta_and_alpha():
    rng = np.random.default_rng(5)
    n = 500
    factor = pd.Series(0.01 * rng.standard_normal(n), index=_dates(n), name="MKT")
    strat = 0.0003 + 1.5 * factor + 0.001 * rng.standard_normal(n)
    strat.name = "strategy"
    exp = DG.factor_exposure(strat, factor.to_frame())
    assert exp.loc["MKT", "beta"] == pytest.approx(1.5, rel=0.1)
    assert exp.loc["alpha", "beta"] == pytest.approx(0.0003, abs=2e-4)
    assert exp.attrs["r_squared"] > 0.8


def test_capacity_binding_name_hand_value():
    idx = _dates(2)
    w = pd.DataFrame({"X": [0.5, 0.2], "Y": [0.5, 0.8]}, index=idx)
    adv = pd.Series({"X": 1_000_000.0, "Y": 2_000_000.0})
    cap = DG.capacity(w, adv, participation=0.1)
    # d0: enter from cash, dw=0.5 each. binding = X: 1e6*0.1/0.5 = 2e5
    assert cap.iloc[0] == pytest.approx(200_000.0)
    # d1: dw=0.3 each. binding = X: 1e6*0.1/0.3
    assert cap.iloc[1] == pytest.approx(1_000_000.0 * 0.1 / 0.3)
