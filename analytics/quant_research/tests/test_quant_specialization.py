from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.quant_specialization import (
    ExecutionCostScenario,
    SignalResearchProtocol,
    audit_forecast_signal,
    finite_horizon_control,
    mean_variance_allocation,
    measure_trade_costs,
)


def test_signal_protocol_requires_every_pre_registered_field() -> None:
    values = dict(
        economic_hypothesis="curve steepening predicts later normalization",
        information_timestamp="after official 18:00 ET publication",
        target="next five-publication-day 10y yield change",
        universe="official 3m/2y/5y/10y/30y par yields",
        holding_period="five Treasury publication days",
        rebalancing_rule="each publication day",
        neutralization="none; forecast study only",
        transaction_cost_model="not identified from daily par yields",
        primary_metric="RMSE versus zero-change",
        falsification_test="reverse-time signal",
        data_source="U.S. Treasury official snapshot",
    )
    protocol = SignalResearchProtocol(**values)
    assert not protocol.tradability_claim_allowed
    with pytest.raises(ValueError, match="economic_hypothesis"):
        SignalResearchProtocol(**{**values, "economic_hypothesis": ""})


def test_forecast_signal_applies_formation_lag_and_prohibits_pnl_label() -> None:
    target = np.array([0.0, 1.0, -1.0, 2.0, -2.0])
    signal = np.array([1.0, -1.0, 1.0, -1.0, 1.0])
    result = audit_forecast_signal(signal, target, formation_lag=1)
    assert result.observation_count == 4
    assert result.directional_accuracy == pytest.approx(1.0)
    assert result.mean_signed_target == pytest.approx(1.5)
    assert not result.pnl_interpretation_allowed


def test_trade_cost_measurements_match_standard_decomposition() -> None:
    result = measure_trade_costs(
        bid=[99.9, 99.9],
        ask=[100.1, 100.1],
        trade_price=[100.1, 99.9],
        future_mid=[100.05, 99.95],
        side=[1, -1],
    )
    np.testing.assert_allclose(result.quoted_spread, [0.2, 0.2])
    np.testing.assert_allclose(result.effective_spread, [0.2, 0.2])
    np.testing.assert_allclose(result.realized_spread, [0.1, 0.1])
    np.testing.assert_allclose(result.adverse_selection, [0.1, 0.1])


def test_trade_cost_measurements_reject_aggregate_or_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="side"):
        measure_trade_costs([99], [101], [100], [100], [0])
    with pytest.raises(ValueError, match="ask"):
        measure_trade_costs([101], [99], [100], [100], [1])


def test_execution_cost_scenario_is_explicit_and_additive() -> None:
    scenario = ExecutionCostScenario(0.5, 0.3, 0.1, 0.2, 0.05)
    assert scenario.total_bps == pytest.approx(1.15)
    assert scenario.net_value_bps(2.0) == pytest.approx(0.85)
    with pytest.raises(ValueError, match="nonnegative"):
        ExecutionCostScenario(-0.1, 0.0, 0.0, 0.0, 0.0)


def test_mean_variance_allocation_satisfies_kkt_and_budget() -> None:
    covariance = np.array([[2.0, 0.5], [0.5, 1.0]])
    result = mean_variance_allocation([0.3, -0.1], covariance, risk_aversion=2.0, net_exposure=0.0)
    assert result.weights.sum() == pytest.approx(0.0, abs=1e-12)
    assert result.stationarity_residual < 1e-12
    assert result.budget_residual < 1e-12


def test_turnover_penalty_moves_allocation_toward_previous_weights() -> None:
    covariance = np.eye(3)
    unpenalized = mean_variance_allocation([1.0, 0.0, -1.0], covariance, risk_aversion=1.0)
    penalized = mean_variance_allocation(
        [1.0, 0.0, -1.0],
        covariance,
        risk_aversion=1.0,
        previous_weights=[0.0, 0.0, 0.0],
        turnover_penalty=5.0,
    )
    assert np.linalg.norm(penalized.weights) < np.linalg.norm(unpenalized.weights)


def test_finite_horizon_control_matches_manual_one_state_choice() -> None:
    transition = np.ones((2, 1, 1))
    result = finite_horizon_control(
        transition,
        stage_cost=np.array([[2.0], [1.0]]),
        terminal_cost=[3.0],
        horizon=4,
    )
    np.testing.assert_array_equal(result.policy, np.ones((4, 1), dtype=int))
    assert result.values[0, 0] == pytest.approx(7.0)


def test_allocation_and_control_reject_invalid_problem_contracts() -> None:
    with pytest.raises(ValueError, match="positive semidefinite"):
        mean_variance_allocation([0.0, 0.0], [[1.0, 2.0], [2.0, 1.0]], risk_aversion=1.0)
    with pytest.raises(ValueError, match="probability"):
        finite_horizon_control(np.array([[[1.2]]]), np.array([[0.0]]), [0.0], horizon=1)
