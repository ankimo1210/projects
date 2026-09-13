"""Tests for hullkit.xva (exposure profiles + CVA/DVA/FVA).

The exposure of an at-the-money forward starts at zero and grows; PFE dominates
EE; and CVA matches a hand-computed constant-exposure case exactly.
"""

import numpy as np
import pytest
from hullkit import xva


def test_exposure_profile_shape():
    S0, r, sigma, T = 100.0, 0.05, 0.20, 1.0
    k = S0 * np.exp(r * T)  # at-the-money forward
    _, mtm = xva.forward_exposure(
        S0, r, sigma, k, T, n_steps=50, n_paths=40_000, rng=np.random.default_rng(0)
    )
    ee = xva.expected_exposure(mtm)
    pf = xva.pfe(mtm, 0.975)
    assert ee[0] < 1e-9  # MtM is exactly 0 at inception
    assert ee[-1] > ee[1]  # exposure grows with diffusion
    assert np.all(pf >= ee - 1e-9)  # PFE quantile dominates the mean


def test_cva_matches_hand_computation():
    # constant EE = 5, r = 0  =>  CVA = (1-R) * EE * (1 - e^{-lambda T})
    t = np.linspace(0.0, 1.0, 51)
    ee = np.full(51, 5.0)
    expected = (1 - 0.4) * 5.0 * (1 - np.exp(-0.02 * 1.0))
    assert abs(xva.cva(t, ee, hazard=0.02, recovery=0.4, r=0.0) - expected) < 1e-12


def test_cva_dva_fva_are_positive():
    S0, r, sigma, T = 100.0, 0.05, 0.20, 1.0
    k = S0 * np.exp(r * T)
    t, mtm = xva.forward_exposure(
        S0, r, sigma, k, T, n_steps=50, n_paths=40_000, rng=np.random.default_rng(1)
    )
    ee = xva.expected_exposure(mtm)
    ene = xva.expected_negative_exposure(mtm)
    assert xva.cva(t, ee, 0.02, 0.4, r) > 0
    assert xva.dva(t, ene, 0.015, 0.4, r) > 0
    assert xva.fva(t, ee, 0.01, r) > 0


def test_default_probs_from_spreads_follow_hull_24_7():
    times = np.array([1.0, 2.0, 3.0])
    spreads = np.array([0.0150, 0.0180, 0.0195])  # Example 24.1 spreads
    q = xva.default_probs_from_spreads(times, spreads, recovery=0.4)
    survival = np.exp(-spreads * times / 0.6)
    np.testing.assert_allclose(q, -np.diff(np.concatenate([[1.0], survival])), atol=1e-15)
    assert q.sum() == pytest.approx(1.0 - survival[-1], abs=1e-15)


def test_netting_reduces_exposure_from_40_to_15():
    trades = np.array([10.0, 30.0, -25.0])
    assert xva.netting_set_exposure(trades) == pytest.approx(15.0)
    assert xva.netting_set_exposure(trades, netting=False) == pytest.approx(40.0)
    paths = np.array([[10.0, 30.0, -25.0], [-5.0, -5.0, 2.0]])
    np.testing.assert_allclose(xva.netting_set_exposure(paths), [15.0, 0.0])


def test_collateral_rule_reproduces_example_24_4():
    value = np.array([50.0, 50.0, -50.0, -50.0])
    lagged = np.array([45.0, 55.0, -45.0, -55.0])
    np.testing.assert_allclose(xva.collateralized_exposure(value, lagged), [5.0, 0.0, 0.0, 5.0])
    # a threshold reduces the collateral that would have been posted
    np.testing.assert_allclose(
        xva.collateralized_exposure(value, lagged, threshold=10.0), [15.0, 5.0, 0.0, 0.0]
    )


def test_cva_special_case_matches_general_formula():
    r, T, f_nd, R, hazard = 0.05, 2.0, 7.0, 0.4, 0.03
    t = np.linspace(0.0, T, 2001)
    q = xva.default_probs_from_spreads(t[1:], np.full(2000, hazard * (1 - R)), R)
    special = xva.cva_single_payoff(f_nd, R, q)
    assert special == pytest.approx((1 - R) * f_nd * (1 - np.exp(-hazard * T)), abs=1e-12)
    # exposure of a single-payoff derivative grows at the risk-free rate: EE_t = f_nd e^{rt}
    general = xva.cva(t, f_nd * np.exp(r * t), hazard, R, r)
    assert general == pytest.approx(special, abs=1e-5)
