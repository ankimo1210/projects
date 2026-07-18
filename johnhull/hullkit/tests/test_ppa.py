"""PPA payoff conventions, synthetic dependence, and cash-flow risk."""

import numpy as np
import pytest
from hullkit import ppa


def test_fixed_volume_and_pay_as_produced_settlements():
    spot = np.array([40.0, 60.0, 80.0])
    generation = np.array([2.0, 1.0, 3.0])
    fixed = ppa.ppa_settlement(
        "fixed",
        spot,
        generation,
        fixed_price=60.0,
        contracted_volume=2.0,
    )
    pap = ppa.ppa_settlement(
        "pay_as_produced",
        spot,
        generation,
        fixed_price=60.0,
    )
    np.testing.assert_allclose(fixed, [40.0, 0.0, -40.0])
    np.testing.assert_allclose(pap, [40.0, 0.0, -60.0])


def test_floor_collar_protects_only_outside_the_band():
    spot = np.array([-10.0, 60.0, 100.0])
    generation = np.ones(3)
    settlement = ppa.ppa_settlement(
        "floor_collar",
        spot,
        generation,
        floor=50.0,
        cap=80.0,
    )
    np.testing.assert_allclose(settlement, [60.0, 0.0, -20.0])


def test_fixed_volume_ppa_eliminates_price_risk_when_generation_matches_volume():
    spot = np.array([[40.0, 80.0], [60.0, 70.0], [90.0, 30.0], [20.0, 90.0]])
    generation = np.full_like(spot, 2.0)
    result = ppa.evaluate_ppa(
        "fixed",
        spot,
        generation,
        fixed_price=60.0,
        contracted_volume=2.0,
    )
    assert result.unhedged_std > 0.0
    assert result.hedge_residual_std == pytest.approx(0.0, abs=1e-12)
    assert result.expected_hedged_cash_flow == pytest.approx(240.0)


def test_pay_as_produced_removes_price_risk_but_leaves_volume_risk():
    scenarios = ppa.simulate_price_generation(
        2_000,
        4,
        correlation=-0.6,
        seed=4,
    )
    result = ppa.evaluate_ppa(
        "pay_as_produced",
        scenarios.spot_prices,
        scenarios.generation,
        fixed_price=60.0,
    )
    assert result.hedge_residual_std < result.unhedged_std
    assert result.hedge_residual_std > 0.0
    assert result.volume_risk > 0.0
    assert result.price_generation_correlation < -0.45


def test_cash_flow_at_risk_and_cvar_are_distinct_tail_metrics():
    risk = ppa.cash_flow_risk([100.0, 90.0, 80.0, 20.0, -10.0], alpha=0.8)
    assert risk.cash_flow_cvar >= risk.cash_flow_at_risk >= 0.0
    assert risk.tail_mean <= risk.lower_quantile


def test_hedge_sensitivity_reports_residual_separately_from_fair_value():
    spot = np.array([[40.0, 80.0], [60.0, 70.0], [90.0, 30.0], [20.0, 90.0]])
    generation = np.full_like(spot, 1.0)
    residuals = ppa.hedge_sensitivity(
        "fixed",
        spot,
        generation,
        [0.0, 0.5, 1.0],
        fixed_price=60.0,
        contracted_volume=1.0,
    )
    assert residuals[1.0] < residuals[0.5] < residuals[0.0]
