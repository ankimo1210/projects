"""One-factor Jarrow--Yildirim inflation model and measure-consistent pricing.

Nominal and real zero curves are separate numeraires. CPI is treated like an
exchange rate between the real and nominal economies, giving
``F_I(t,T) = I(t) P_r(t,T) / P_n(t,T)``. Options and YoY ratios are evaluated
under their nominal payment-date forward measures; a nominal-measure simulator
includes the real-rate quanto drift.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad
from scipy.special import ndtr

from .hull_white import HullWhiteParams, hw_b, hw_phi
from .inflation import zcis_cashflow
from .rates import forward_discount

FloatArray = NDArray[np.float64]
ZeroCurve = tuple[Sequence[float], Sequence[float]]


@dataclass(frozen=True)
class JarrowYildirimParams:
    """Gaussian nominal-rate, real-rate, and CPI-volatility parameters."""

    nominal_mean_reversion: float
    nominal_volatility: float
    real_mean_reversion: float
    real_volatility: float
    inflation_volatility: float
    rho_nominal_real: float
    rho_nominal_inflation: float
    rho_real_inflation: float

    def validate(self) -> None:
        """Require valid dynamics and a positive-semidefinite correlation matrix."""
        values = (
            self.nominal_mean_reversion,
            self.nominal_volatility,
            self.real_mean_reversion,
            self.real_volatility,
            self.inflation_volatility,
            self.rho_nominal_real,
            self.rho_nominal_inflation,
            self.rho_real_inflation,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Jarrow-Yildirim parameters must be finite")
        if self.nominal_mean_reversion <= 0.0 or self.real_mean_reversion <= 0.0:
            raise ValueError("nominal and real mean reversions must be positive")
        if min(
            self.nominal_volatility, self.real_volatility, self.inflation_volatility
        ) < 0.0:
            raise ValueError("Jarrow-Yildirim volatilities cannot be negative")
        correlations = (
            self.rho_nominal_real,
            self.rho_nominal_inflation,
            self.rho_real_inflation,
        )
        if any(abs(value) > 1.0 for value in correlations):
            raise ValueError("Jarrow-Yildirim correlations must lie in [-1, 1]")
        eigenvalues = np.linalg.eigvalsh(_raw_correlation_matrix(self))
        if eigenvalues[0] < -1e-12:
            raise ValueError("Jarrow-Yildirim correlation matrix must be positive semidefinite")


@dataclass(frozen=True)
class JYSimulation:
    """Nominal-measure factor, CPI, and money-market-account paths."""

    times: FloatArray
    nominal_factors: FloatArray
    real_factors: FloatArray
    cpi: FloatArray
    nominal_bank_accounts: FloatArray
    real_bank_accounts: FloatArray


def _raw_correlation_matrix(params: JarrowYildirimParams) -> FloatArray:
    return np.asarray(
        [
            [1.0, params.rho_nominal_real, params.rho_nominal_inflation],
            [params.rho_nominal_real, 1.0, params.rho_real_inflation],
            [params.rho_nominal_inflation, params.rho_real_inflation, 1.0],
        ],
        dtype=float,
    )


def jy_correlation_matrix(params: JarrowYildirimParams) -> FloatArray:
    """Return the validated Brownian correlation matrix in nominal/real/CPI order."""
    params.validate()
    return _raw_correlation_matrix(params)


def _validate_times(t: float, observation: float, payment: float) -> tuple[float, float, float]:
    values = tuple(float(value) for value in (t, observation, payment))
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Jarrow-Yildirim times must be finite")
    if values[0] < 0.0 or values[1] < values[0] or values[2] < values[1]:
        raise ValueError("times must satisfy 0 <= t <= observation <= payment")
    return values


def _cpi_kernel(time: float, observation: float, params: JarrowYildirimParams) -> FloatArray:
    return np.asarray(
        [
            params.nominal_volatility
            * hw_b(time, observation, params.nominal_mean_reversion),
            -params.real_volatility * hw_b(time, observation, params.real_mean_reversion),
            params.inflation_volatility,
        ]
    )


def jy_cpi_forward(
    t: float,
    maturity: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
) -> float:
    """Return ``I(t) P_r(t,T) / P_n(t,T)`` from nominal and real curves."""
    t = float(t)
    maturity = float(maturity)
    spot_cpi = float(spot_cpi)
    if not all(math.isfinite(value) for value in (t, maturity, spot_cpi)):
        raise ValueError("CPI-forward inputs must be finite")
    if t < 0.0 or maturity < t or spot_cpi <= 0.0:
        raise ValueError("CPI forward requires 0 <= t <= maturity and positive spot CPI")
    real_discount = forward_discount(t, maturity, real_curve)
    nominal_discount = forward_discount(t, maturity, nominal_curve)
    return float(spot_cpi * real_discount / nominal_discount)


def jy_cpi_log_covariance(
    t: float,
    first_observation: float,
    second_observation: float,
    params: JarrowYildirimParams,
) -> float:
    """Return covariance of two log CPI levels under any equivalent forward measure."""
    params.validate()
    t = float(t)
    first = float(first_observation)
    second = float(second_observation)
    if not all(math.isfinite(value) for value in (t, first, second)):
        raise ValueError("CPI covariance times must be finite")
    if t < 0.0 or first < t or second < t:
        raise ValueError("CPI observations cannot precede valuation time")
    upper = min(first, second)
    if upper == t:
        return 0.0
    correlation = jy_correlation_matrix(params)

    def _integrand(time: float) -> float:
        first_kernel = _cpi_kernel(time, first, params)
        second_kernel = _cpi_kernel(time, second, params)
        return float(first_kernel @ correlation @ second_kernel)

    result, _ = quad(_integrand, t, upper, epsabs=1e-12, epsrel=1e-10)
    return float(max(result, 0.0)) if first == second else float(result)


def jy_cpi_total_variance(
    t: float,
    observation: float,
    payment: float,
    params: JarrowYildirimParams,
) -> float:
    """Return integrated log-CPI variance under the nominal payment forward measure.

    A Gaussian change of numeraire shifts the log mean but not its variance;
    ``payment`` is nevertheless explicit to prevent observation/payment confusion.
    """
    t, observation, _ = _validate_times(t, observation, payment)
    return jy_cpi_log_covariance(t, observation, observation, params)


def _payment_measure_adjustment(
    t: float,
    observation: float,
    payment: float,
    params: JarrowYildirimParams,
) -> float:
    if payment == observation:
        return 0.0
    correlation = jy_correlation_matrix(params)

    def _integrand(time: float) -> float:
        cpi_kernel = _cpi_kernel(time, observation, params)
        bond_kernel = np.asarray(
            [
                -params.nominal_volatility
                * (
                    hw_b(time, payment, params.nominal_mean_reversion)
                    - hw_b(time, observation, params.nominal_mean_reversion)
                ),
                0.0,
                0.0,
            ]
        )
        return float(cpi_kernel @ correlation @ bond_kernel)

    covariance, _ = quad(_integrand, t, observation, epsabs=1e-12, epsrel=1e-10)
    return float(covariance)


def jy_payment_forward_cpi(
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
) -> float:
    """Return expected observed CPI under the nominal payment-date forward measure."""
    t, observation, payment = _validate_times(t, observation, payment)
    params.validate()
    observation_forward = jy_cpi_forward(
        t, observation, spot_cpi, nominal_curve, real_curve
    )
    adjustment = _payment_measure_adjustment(t, observation, payment, params)
    return float(observation_forward * math.exp(adjustment))


def jy_expected_cpi_ratio(
    t: float,
    start_observation: float,
    end_observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
) -> float:
    """Return ``E[I(end)/I(start)]`` under the nominal payment forward measure."""
    t = float(t)
    start = float(start_observation)
    end = float(end_observation)
    payment = float(payment)
    if t < 0.0 or start < t or end < start or payment < end:
        raise ValueError("ratio times must satisfy 0 <= t <= start <= end <= payment")
    first_forward = jy_payment_forward_cpi(
        t, start, payment, spot_cpi, nominal_curve, real_curve, params
    )
    second_forward = jy_payment_forward_cpi(
        t, end, payment, spot_cpi, nominal_curve, real_curve, params
    )
    first_variance = jy_cpi_log_covariance(t, start, start, params)
    covariance = jy_cpi_log_covariance(t, start, end, params)
    return float(second_forward / first_forward * math.exp(first_variance - covariance))


def jy_cpi_option(
    notional: float,
    strike_index: float,
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    option_type: str = "call",
) -> float:
    """Price a European option on an observed CPI level paid on a nominal date."""
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if not math.isfinite(notional) or notional < 0.0:
        raise ValueError("notional must be non-negative and finite")
    if not math.isfinite(strike_index) or strike_index <= 0.0:
        raise ValueError("strike_index must be positive and finite")
    forward = jy_payment_forward_cpi(
        t, observation, payment, spot_cpi, nominal_curve, real_curve, params
    )
    variance = jy_cpi_total_variance(t, observation, payment, params)
    discount = forward_discount(t, payment, nominal_curve)
    direction = 1.0 if option_type == "call" else -1.0
    if variance <= 1e-16:
        return float(notional * discount * max(direction * (forward - strike_index), 0.0))
    total_volatility = math.sqrt(variance)
    d1 = math.log(forward / strike_index) / total_volatility + 0.5 * total_volatility
    d2 = d1 - total_volatility
    return float(
        notional
        * discount
        * direction
        * (
            forward * ndtr(direction * d1)
            - strike_index * ndtr(direction * d2)
        )
    )


def jy_zcis_value(
    notional: float,
    start_index: float,
    fixed_rate: float,
    accrual_years: float,
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    pay_fixed: bool = True,
) -> float:
    """Value a receive-inflation ZCIS with explicit observation and payment dates."""
    expected_end = jy_payment_forward_cpi(
        t, observation, payment, spot_cpi, nominal_curve, real_curve, params
    )
    cashflow = zcis_cashflow(
        notional, start_index, expected_end, fixed_rate, accrual_years
    )
    direction = 1.0 if pay_fixed else -1.0
    return float(direction * forward_discount(t, payment, nominal_curve) * cashflow)


def jy_yoy_value(
    notional: float,
    observation_pairs: Sequence[tuple[float, float]],
    payment_times: Sequence[float],
    fixed_rate: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    t: float = 0.0,
    pay_fixed: bool = True,
) -> float:
    """Value a YoY swap using forward-measure expected CPI ratios coupon by coupon."""
    pairs = tuple(observation_pairs)
    payments = tuple(float(value) for value in payment_times)
    if not pairs or len(pairs) != len(payments):
        raise ValueError("observation_pairs and payment_times need equal non-zero length")
    if not math.isfinite(notional) or notional < 0.0 or not math.isfinite(fixed_rate):
        raise ValueError("YoY notional and rate inputs must be finite")
    value = 0.0
    for (start, end), payment in zip(pairs, payments, strict=True):
        ratio = jy_expected_cpi_ratio(
            t,
            start,
            end,
            payment,
            spot_cpi,
            nominal_curve,
            real_curve,
            params,
        )
        value += forward_discount(t, payment, nominal_curve) * (ratio - 1.0 - fixed_rate)
    receive_inflation = notional * value
    return float(receive_inflation if pay_fixed else -receive_inflation)


def simulate_jy_forward_levels(
    observation_times: Sequence[float],
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    t: float = 0.0,
    n_paths: int = 10_000,
    seed: int = 42,
) -> FloatArray:
    """Draw exact joint CPI levels under one nominal payment-date forward measure."""
    observations = np.asarray(observation_times, dtype=float)
    if observations.ndim != 1 or observations.size == 0:
        raise ValueError("observation_times must be a non-empty vector")
    if np.any(~np.isfinite(observations)) or np.any(np.diff(observations) <= 0.0):
        raise ValueError("observation_times must be finite and strictly increasing")
    if observations[0] < t or payment < observations[-1]:
        raise ValueError("forward-level times must satisfy t <= observations <= payment")
    if not isinstance(n_paths, int) or n_paths <= 0:
        raise ValueError("n_paths must be a positive integer")
    params.validate()
    forwards = np.asarray(
        [
            jy_payment_forward_cpi(
                t, observation, payment, spot_cpi, nominal_curve, real_curve, params
            )
            for observation in observations
        ]
    )
    covariance = np.asarray(
        [
            [jy_cpi_log_covariance(t, first, second, params) for second in observations]
            for first in observations
        ]
    )
    covariance = 0.5 * (covariance + covariance.T)
    log_means = np.log(forwards) - 0.5 * np.diag(covariance)
    rng = np.random.default_rng(seed)
    log_levels = rng.multivariate_normal(log_means, covariance, size=n_paths)
    return np.exp(log_levels)


def _step_covariance(dt: float, params: JarrowYildirimParams) -> FloatArray:
    an = params.nominal_mean_reversion
    ar = params.real_mean_reversion
    sn = params.nominal_volatility
    sr = params.real_volatility
    covariance = np.asarray(
        [
            [
                sn**2 * -math.expm1(-2.0 * an * dt) / (2.0 * an),
                params.rho_nominal_real
                * sn
                * sr
                * -math.expm1(-(an + ar) * dt)
                / (an + ar),
                params.rho_nominal_inflation * sn * -math.expm1(-an * dt) / an,
            ],
            [
                0.0,
                sr**2 * -math.expm1(-2.0 * ar * dt) / (2.0 * ar),
                params.rho_real_inflation * sr * -math.expm1(-ar * dt) / ar,
            ],
            [0.0, 0.0, dt],
        ]
    )
    covariance[1, 0] = covariance[0, 1]
    covariance[2, 0] = covariance[0, 2]
    covariance[2, 1] = covariance[1, 2]
    return covariance


def simulate_jy_paths(
    times: Sequence[float],
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    n_paths: int = 10_000,
    seed: int = 42,
) -> JYSimulation:
    """Simulate Jarrow--Yildirim paths under the nominal money-market measure.

    The real OU factor contains the FX-style quanto drift
    ``-rho(real,CPI) * sigma_real * sigma_CPI``. Exact factor innovations are
    jointly drawn; trapezoidal short-rate integration updates CPI and accounts.
    """
    params.validate()
    grid = np.asarray(times, dtype=float)
    if grid.ndim != 1 or len(grid) < 2 or not np.all(np.isfinite(grid)):
        raise ValueError("times must be a finite one-dimensional grid of length at least two")
    if grid[0] != 0.0 or np.any(np.diff(grid) <= 0.0):
        raise ValueError("times must start at zero and be strictly increasing")
    if not math.isfinite(spot_cpi) or spot_cpi <= 0.0:
        raise ValueError("spot_cpi must be positive and finite")
    if not isinstance(n_paths, int) or n_paths <= 0:
        raise ValueError("n_paths must be a positive integer")
    shape = (n_paths, len(grid))
    nominal = np.zeros(shape)
    real = np.zeros(shape)
    log_cpi = np.empty(shape)
    log_cpi[:, 0] = math.log(spot_cpi)
    nominal_bank = np.ones(shape)
    real_bank = np.ones(shape)
    rng = np.random.default_rng(seed)
    nominal_hw = HullWhiteParams(
        params.nominal_mean_reversion, params.nominal_volatility
    )
    real_hw = HullWhiteParams(params.real_mean_reversion, params.real_volatility)
    real_quanto_drift = (
        -params.rho_real_inflation
        * params.real_volatility
        * params.inflation_volatility
    )

    for index in range(1, len(grid)):
        start, end = grid[index - 1], grid[index]
        dt = end - start
        innovations = rng.multivariate_normal(
            np.zeros(3), _step_covariance(dt, params), size=n_paths
        )
        nominal[:, index] = (
            math.exp(-params.nominal_mean_reversion * dt) * nominal[:, index - 1]
            + innovations[:, 0]
        )
        real[:, index] = (
            math.exp(-params.real_mean_reversion * dt) * real[:, index - 1]
            + real_quanto_drift
            * -math.expm1(-params.real_mean_reversion * dt)
            / params.real_mean_reversion
            + innovations[:, 1]
        )
        midpoint = 0.5 * (start + end)
        nominal_rate = hw_phi(midpoint, nominal_curve, nominal_hw) + 0.5 * (
            nominal[:, index - 1] + nominal[:, index]
        )
        real_rate = hw_phi(midpoint, real_curve, real_hw) + 0.5 * (
            real[:, index - 1] + real[:, index]
        )
        log_cpi[:, index] = (
            log_cpi[:, index - 1]
            + (nominal_rate - real_rate - 0.5 * params.inflation_volatility**2) * dt
            + params.inflation_volatility * innovations[:, 2]
        )
        nominal_bank[:, index] = nominal_bank[:, index - 1] * np.exp(nominal_rate * dt)
        real_bank[:, index] = real_bank[:, index - 1] * np.exp(real_rate * dt)

    return JYSimulation(
        grid,
        nominal,
        real,
        np.exp(log_cpi),
        nominal_bank,
        real_bank,
    )
