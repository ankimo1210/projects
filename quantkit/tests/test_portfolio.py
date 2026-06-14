"""Portfolio-layer tests: constraints are honored, the constructors do what they
claim (risk parity balances risk, min-variance minimizes variance, MVO tilts to
the signal), and build_weights produces a causal, held weight panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quantkit import portfolio as PF


def _cov(corr=0.2, vols=(0.1, 0.2, 0.4), assets=("A", "B", "C")):
    vols = np.array(vols)
    n = len(vols)
    c = np.full((n, n), corr) + np.eye(n) * (1 - corr)
    cov = np.outer(vols, vols) * c
    return pd.DataFrame(cov, index=list(assets), columns=list(assets))


# --- constraints --------------------------------------------------------------
def test_apply_constraints_caps_and_normalizes():
    w = pd.Series({"A": 0.9, "B": 0.05, "C": 0.05})
    c = PF.Constraints(long_only=True, max_gross=1.0, max_name_weight=0.4)
    out = PF.apply_constraints(w, c)
    assert (out <= 0.4 + 1e-9).all()  # per-name cap
    assert out.sum() == pytest.approx(1.0)  # gross normalized
    assert (out >= 0).all()  # long-only


def test_apply_constraints_long_only_removes_shorts():
    w = pd.Series({"A": 0.6, "B": -0.4})
    out = PF.apply_constraints(
        w, PF.Constraints(long_only=True, max_gross=1.0, max_name_weight=1.0)
    )
    assert out["B"] == 0.0 and out["A"] == pytest.approx(1.0)


def test_constraints_from_config():
    c = PF.Constraints.from_config(
        {"constraints": {"long_only": True, "max_gross": 2.0, "max_name_weight": 0.3}}
    )
    assert c.long_only and c.max_gross == 2.0 and c.max_name_weight == 0.3


def test_target_vol_scales_book():
    cov = _cov()
    w = PF.equal_weight(cov.index)
    c = PF.Constraints(max_gross=1.0, max_name_weight=1.0, target_vol=0.10)
    out = PF.apply_constraints(w, c, cov=cov, periods=252)
    realized = np.sqrt(out.to_numpy() @ cov.to_numpy() @ out.to_numpy()) * np.sqrt(252)
    assert realized == pytest.approx(0.10, rel=1e-6)


# --- constructors -------------------------------------------------------------
def test_inverse_vol_tilts_to_low_vol():
    vol = pd.Series({"A": 0.1, "B": 0.2, "C": 0.4})
    w = PF.inverse_volatility(vol)
    assert w["A"] > w["B"] > w["C"]
    assert w.sum() == pytest.approx(1.0)


def test_min_variance_has_lower_variance_than_equal_weight():
    cov = _cov()
    mv = PF.min_variance(cov)
    ew = PF.equal_weight(cov.index)

    def var(w):
        return w.reindex(cov.index).to_numpy() @ cov.to_numpy() @ w.reindex(cov.index).to_numpy()

    assert var(mv) < var(ew)


def test_risk_parity_equalizes_risk_contributions():
    cov = _cov()
    w = PF.risk_parity(cov)
    rc = PF.risk_contributions(w, cov)
    assert w.sum() == pytest.approx(1.0) and (w >= -1e-9).all()
    assert rc.max() - rc.min() < 0.02  # contributions ~ equal


def test_risk_parity_works_at_daily_covariance_scale():
    # regression: tiny covariance (daily returns, entries ~1e-4) must not make the
    # objective vanish and stall the optimizer at the equal-weight start.
    cov = _cov(corr=0.3, vols=(0.008, 0.015, 0.030))  # daily-vol scale
    w = PF.risk_parity(cov)
    rc = PF.risk_contributions(w, cov)
    ew_rc = PF.risk_contributions(PF.equal_weight(cov.index), cov)
    assert rc.max() - rc.min() < 0.02  # genuinely equalized
    assert ew_rc.max() - ew_rc.min() > 0.1  # equal weight is NOT balanced here
    assert abs(w["A"] - 1 / 3) > 0.05  # RP differs from equal weight


def test_mean_variance_tilts_toward_high_signal():
    cov = _cov(corr=0.0)  # diagonal -> weight ∝ mu/var
    mu = pd.Series({"A": 1.0, "B": 0.0, "C": -1.0})
    w = PF.mean_variance(mu, cov)
    assert w["A"] > 0 > w["C"]  # long the high-signal name, short the low


# --- panel builder ------------------------------------------------------------
def _returns(n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=n)
    return pd.DataFrame(rng.normal(0.0003, 0.012, (n, 4)), index=idx, columns=list("ABCD"))


def test_build_weights_is_held_and_constrained():
    rets = _returns()
    c = PF.Constraints(long_only=True, max_gross=1.0, max_name_weight=0.5)
    w = PF.build_weights(rets, method="risk_parity", constraints=c, lookback=63, rebalance="ME")
    held = w.dropna(how="all")
    assert not held.empty
    assert (held.sum(axis=1) <= 1.0 + 1e-6).all()  # gross cap
    assert (held.fillna(0) <= 0.5 + 1e-9).all().all()  # name cap
    # weights are held between month-ends (step function) -> few distinct rows
    assert held.drop_duplicates().shape[0] < held.shape[0]


def test_build_weights_mean_variance_needs_scores():
    rets = _returns()
    with pytest.raises(ValueError):
        PF.build_weights(rets, method="mean_variance", scores=None, rebalance="ME")


def test_build_weights_is_causal():
    rets = _returns()
    full = PF.build_weights(rets, method="min_variance", lookback=63, rebalance="ME")
    cut = 250
    trunc = PF.build_weights(rets.iloc[:cut], method="min_variance", lookback=63, rebalance="ME")
    common = full.index[:cut].intersection(trunc.index)
    # earlier weights must not change when future data is appended
    pd.testing.assert_frame_equal(
        full.loc[common].dropna(how="all"), trunc.loc[common].dropna(how="all")
    )
