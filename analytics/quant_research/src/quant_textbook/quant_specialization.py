"""Decision-boundary helpers for the B11 quant research specialization.

The APIs deliberately separate predictive evidence, observable trade-cost
measurements, and hypothetical execution scenarios.  A daily par-yield curve
or an aggregate TRACE report is not silently converted into executable P&L.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _finite_vector(value: object, *, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a non-empty finite one-dimensional array")
    return array


@dataclass(frozen=True)
class SignalResearchProtocol:
    """Pre-registered signal contract required before model comparison."""

    economic_hypothesis: str
    information_timestamp: str
    target: str
    universe: str
    holding_period: str
    rebalancing_rule: str
    neutralization: str
    transaction_cost_model: str
    primary_metric: str
    falsification_test: str
    data_source: str
    tradability_claim_allowed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "economic_hypothesis",
            "information_timestamp",
            "target",
            "universe",
            "holding_period",
            "rebalancing_rule",
            "neutralization",
            "transaction_cost_model",
            "primary_metric",
            "falsification_test",
            "data_source",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.tradability_claim_allowed, bool):
            raise TypeError("tradability_claim_allowed must be bool")


@dataclass(frozen=True)
class ForecastSignalAudit:
    """Prediction diagnostics that do not imply a tradable return."""

    formation_lag: int
    observation_count: int
    correlation: float
    directional_accuracy: float
    mean_signed_target: float
    target_unit: str
    pnl_interpretation_allowed: bool = False


def audit_forecast_signal(
    signal: object,
    future_target: object,
    *,
    formation_lag: int = 1,
    target_unit: str = "basis points",
) -> ForecastSignalAudit:
    """Align a signal with a later target and report non-P&L diagnostics."""
    signal_array = _finite_vector(signal, name="signal")
    target_array = _finite_vector(future_target, name="future_target")
    if signal_array.shape != target_array.shape:
        raise ValueError("signal and future_target must have the same shape")
    if isinstance(formation_lag, bool) or not isinstance(formation_lag, int):
        raise TypeError("formation_lag must be an integer")
    if formation_lag < 1 or formation_lag >= signal_array.size:
        raise ValueError("formation_lag must be between one and n-1")
    if not isinstance(target_unit, str) or not target_unit.strip():
        raise ValueError("target_unit must be a non-empty string")

    aligned_signal = signal_array[:-formation_lag]
    aligned_target = target_array[formation_lag:]
    signal_std = float(np.std(aligned_signal))
    target_std = float(np.std(aligned_target))
    correlation = (
        float(np.corrcoef(aligned_signal, aligned_target)[0, 1])
        if signal_std > 0.0 and target_std > 0.0
        else 0.0
    )
    direction = float(np.mean(np.sign(aligned_signal) == np.sign(aligned_target)))
    mean_signed_target = float(np.mean(np.sign(aligned_signal) * aligned_target))
    return ForecastSignalAudit(
        formation_lag=formation_lag,
        observation_count=aligned_target.size,
        correlation=correlation,
        directional_accuracy=direction,
        mean_signed_target=mean_signed_target,
        target_unit=target_unit.strip(),
    )


@dataclass(frozen=True)
class MicrostructureMeasurements:
    """Trade-level spread decomposition in the input price units."""

    quoted_spread: np.ndarray
    effective_spread: np.ndarray
    realized_spread: np.ndarray
    adverse_selection: np.ndarray


def measure_trade_costs(
    bid: object,
    ask: object,
    trade_price: object,
    future_mid: object,
    side: object,
) -> MicrostructureMeasurements:
    """Compute quoted/effective/realized spreads for signed trades.

    ``side`` is +1 for a buyer-initiated trade and -1 for a seller-initiated
    trade.  The function requires trade-level quotes; aggregate volume is not a
    valid substitute.
    """
    arrays = {
        name: _finite_vector(value, name=name)
        for name, value in {
            "bid": bid,
            "ask": ask,
            "trade_price": trade_price,
            "future_mid": future_mid,
            "side": side,
        }.items()
    }
    shape = arrays["bid"].shape
    if any(array.shape != shape for array in arrays.values()):
        raise ValueError("all trade arrays must have the same shape")
    if np.any(arrays["ask"] < arrays["bid"]):
        raise ValueError("ask must be greater than or equal to bid")
    if not np.all(np.isin(arrays["side"], (-1.0, 1.0))):
        raise ValueError("side must contain only -1 and +1")
    midpoint = 0.5 * (arrays["bid"] + arrays["ask"])
    quoted = arrays["ask"] - arrays["bid"]
    effective = 2.0 * arrays["side"] * (arrays["trade_price"] - midpoint)
    realized = 2.0 * arrays["side"] * (arrays["trade_price"] - arrays["future_mid"])
    return MicrostructureMeasurements(
        quoted_spread=quoted,
        effective_spread=effective,
        realized_spread=realized,
        adverse_selection=effective - realized,
    )


@dataclass(frozen=True)
class ExecutionCostScenario:
    """Explicit scenario inputs, not estimates from aggregate market data."""

    half_spread_bps: float
    temporary_impact_bps: float
    permanent_impact_bps: float
    delay_bps: float
    funding_bps: float

    def __post_init__(self) -> None:
        values = np.asarray(
            [
                self.half_spread_bps,
                self.temporary_impact_bps,
                self.permanent_impact_bps,
                self.delay_bps,
                self.funding_bps,
            ],
            dtype=float,
        )
        if not np.isfinite(values).all() or np.any(values < 0.0):
            raise ValueError("execution cost components must be finite and nonnegative")

    @property
    def total_bps(self) -> float:
        return float(
            self.half_spread_bps
            + self.temporary_impact_bps
            + self.permanent_impact_bps
            + self.delay_bps
            + self.funding_bps
        )

    def net_value_bps(self, gross_value_bps: float) -> float:
        if not np.isfinite(gross_value_bps):
            raise ValueError("gross_value_bps must be finite")
        return float(gross_value_bps - self.total_bps)


@dataclass(frozen=True)
class AllocationResult:
    """Equality-constrained shrinkage mean-variance allocation."""

    weights: np.ndarray
    expected_value: float
    variance: float
    turnover_squared: float
    stationarity_residual: float
    budget_residual: float


def mean_variance_allocation(
    expected_change: object,
    covariance: object,
    *,
    risk_aversion: float,
    previous_weights: object | None = None,
    turnover_penalty: float = 0.0,
    net_exposure: float = 0.0,
) -> AllocationResult:
    """Solve a transparent quadratic decision with a net-exposure equality."""
    expected = _finite_vector(expected_change, name="expected_change")
    covariance_array = np.asarray(covariance, dtype=float)
    n_assets = expected.size
    if covariance_array.shape != (n_assets, n_assets):
        raise ValueError("covariance must be square and match expected_change")
    if not np.isfinite(covariance_array).all():
        raise ValueError("covariance must be finite")
    symmetry_scale = max(float(np.linalg.norm(covariance_array, ord=2)), np.finfo(float).tiny)
    if np.linalg.norm(covariance_array - covariance_array.T, ord=2) > 1e-10 * symmetry_scale:
        raise ValueError("covariance must be symmetric")
    covariance_array = 0.5 * (covariance_array + covariance_array.T)
    if float(np.linalg.eigvalsh(covariance_array).min()) < -1e-10 * symmetry_scale:
        raise ValueError("covariance must be positive semidefinite")
    if not np.isfinite(risk_aversion) or risk_aversion <= 0.0:
        raise ValueError("risk_aversion must be strictly positive")
    if not np.isfinite(turnover_penalty) or turnover_penalty < 0.0:
        raise ValueError("turnover_penalty must be nonnegative")
    if not np.isfinite(net_exposure):
        raise ValueError("net_exposure must be finite")
    previous = (
        np.zeros(n_assets)
        if previous_weights is None
        else _finite_vector(previous_weights, name="previous_weights")
    )
    if previous.shape != expected.shape:
        raise ValueError("previous_weights must match expected_change")

    hessian = risk_aversion * covariance_array + 2.0 * turnover_penalty * np.eye(n_assets)
    rhs = expected + 2.0 * turnover_penalty * previous
    ones = np.ones(n_assets)
    kkt = np.block([[hessian, ones[:, None]], [ones[None, :], np.zeros((1, 1))]])
    solution = np.linalg.solve(kkt, np.r_[rhs, net_exposure])
    weights = solution[:-1]
    multiplier = solution[-1]
    stationarity = hessian @ weights + multiplier * ones - rhs
    return AllocationResult(
        weights=weights,
        expected_value=float(expected @ weights),
        variance=float(weights @ covariance_array @ weights),
        turnover_squared=float(np.sum((weights - previous) ** 2)),
        stationarity_residual=float(np.linalg.norm(stationarity, ord=np.inf)),
        budget_residual=float(abs(weights.sum() - net_exposure)),
    )


@dataclass(frozen=True)
class FiniteHorizonControl:
    """Backward-induction result for a finite Markov decision problem."""

    values: np.ndarray
    policy: np.ndarray


def finite_horizon_control(
    transition: object,
    stage_cost: object,
    terminal_cost: object,
    *,
    horizon: int,
) -> FiniteHorizonControl:
    """Minimize expected cost by exact finite-horizon backward induction."""
    probabilities = np.asarray(transition, dtype=float)
    costs = np.asarray(stage_cost, dtype=float)
    terminal = _finite_vector(terminal_cost, name="terminal_cost")
    if probabilities.ndim != 3:
        raise ValueError("transition must have shape (actions, states, states)")
    n_actions, n_states, next_states = probabilities.shape
    if next_states != n_states or costs.shape != (n_actions, n_states):
        raise ValueError("stage_cost and transition shapes are inconsistent")
    if terminal.size != n_states:
        raise ValueError("terminal_cost must match the state dimension")
    if not np.isfinite(probabilities).all() or not np.isfinite(costs).all():
        raise ValueError("transition and stage_cost must be finite")
    if np.any(probabilities < 0.0) or not np.allclose(probabilities.sum(axis=2), 1.0):
        raise ValueError("each transition row must be a probability vector")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")

    values = np.empty((horizon + 1, n_states), dtype=float)
    policy = np.empty((horizon, n_states), dtype=int)
    values[-1] = terminal
    for time in range(horizon - 1, -1, -1):
        action_values = costs + probabilities @ values[time + 1]
        policy[time] = np.argmin(action_values, axis=0)
        values[time] = action_values[policy[time], np.arange(n_states)]
    return FiniteHorizonControl(values=values, policy=policy)


__all__ = [
    "AllocationResult",
    "ExecutionCostScenario",
    "FiniteHorizonControl",
    "ForecastSignalAudit",
    "MicrostructureMeasurements",
    "SignalResearchProtocol",
    "audit_forecast_signal",
    "finite_horizon_control",
    "mean_variance_allocation",
    "measure_trade_costs",
]
