"""Tests for hullkit.credit_curve: piecewise hazard curves and Hull 24.4 bootstraps."""

import math

import numpy as np
import pytest
from hullkit import credit_curve as cc


def test_constant_curve_matches_exponential_survival():
    curve = cc.HazardCurve.from_constant(0.02)
    assert curve.survival(2.0) == pytest.approx(math.exp(-0.04), abs=1e-12)
    assert curve.default_prob_between(2.0, 3.0) == pytest.approx(
        math.exp(-0.04) - math.exp(-0.06), abs=1e-12
    )


def test_piecewise_curve_integrates_segment_by_segment_and_extrapolates_flat():
    curve = cc.HazardCurve((1.0, 2.0), (0.01, 0.03))
    assert curve.cumulative_hazard(0.5) == pytest.approx(0.005)
    assert curve.cumulative_hazard(1.5) == pytest.approx(0.01 + 0.015)
    assert curve.cumulative_hazard(4.0) == pytest.approx(0.01 + 0.03 * 3.0)  # flat beyond 2y
    np.testing.assert_allclose(curve.forward_hazard(np.array([0.5, 1.5, 9.0])), [0.01, 0.03, 0.03])


def test_curve_validation():
    with pytest.raises(ValueError):
        cc.HazardCurve((2.0, 1.0), (0.01, 0.02))
    with pytest.raises(ValueError):
        cc.HazardCurve((1.0,), (-0.01,))
    with pytest.raises(ValueError):
        cc.HazardCurve((1.0, 2.0), (0.01,))


def test_example_24_1_average_and_forward_hazards():
    avg = cc.average_hazards_from_spreads([0.0150, 0.0180, 0.0195], recovery=0.4)
    np.testing.assert_allclose(avg, [0.025, 0.030, 0.0325], atol=1e-12)
    curve = cc.forward_hazards_from_average([1.0, 2.0, 3.0], avg)
    np.testing.assert_allclose(curve.hazards, [0.025, 0.035, 0.0375], atol=1e-12)
    # average over 3y is recovered from the forward curve
    assert curve.cumulative_hazard(3.0) / 3.0 == pytest.approx(0.0325, abs=1e-12)


def test_example_24_2_bond_prices():
    prices = [
        cc.bond_price_from_yield(100, 0.08, T, y) for T, y in ((1, 0.065), (2, 0.068), (3, 0.0695))
    ]
    np.testing.assert_allclose(prices, [101.33, 101.99, 102.47], atol=0.005)
    risk_free = [cc.risk_free_bond_price(100, 0.08, T, 0.05) for T in (1, 2, 3)]
    np.testing.assert_allclose(risk_free, [102.83, 105.52, 108.08], atol=0.005)


def test_example_24_2_loss_given_default_points():
    # PV of loss if default at 3 months / 9 months on the 1-year bond (Hull: 63.33, 60.40)
    loss_3m = (cc.forward_risk_free_value(100, 0.08, 1.0, 0.05, 0.25) - 40.0) * math.exp(
        -0.05 * 0.25
    )
    loss_9m = (cc.forward_risk_free_value(100, 0.08, 1.0, 0.05, 0.75) - 40.0) * math.exp(
        -0.05 * 0.75
    )
    assert loss_3m == pytest.approx(63.33, abs=0.005)
    assert loss_9m == pytest.approx(60.40, abs=0.005)


def test_example_24_2_bootstrap_hazards():
    prices = [
        cc.bond_price_from_yield(100, 0.08, T, y) for T, y in ((1, 0.065), (2, 0.068), (3, 0.0695))
    ]
    result = cc.bootstrap_from_bonds(prices, 0.08, [1.0, 2.0, 3.0], r=0.05, recovery=0.4)
    np.testing.assert_allclose(result.curve.hazards, [0.0246, 0.0348, 0.0374], atol=5e-5)
    np.testing.assert_allclose(result.expected_loss_pv, [1.50, 3.53, 5.61], atol=0.005)
    # round trip: the bootstrapped curve reprices the expected-loss targets
    for T, target in zip((1.0, 2.0, 3.0), result.expected_loss_pv, strict=True):
        repriced = cc.expected_default_loss_pv(result.curve, 100, 0.08, T, 0.05, 0.4)
        assert repriced == pytest.approx(target, abs=1e-9)


def test_bootstrap_rejects_bad_inputs():
    with pytest.raises(ValueError):
        cc.bootstrap_from_bonds([101.0, 102.0], 0.08, [1.0], r=0.05, recovery=0.4)
    with pytest.raises(ValueError):
        cc.bootstrap_from_bonds([101.0], 0.08, [1.0], r=0.05, recovery=1.0)
