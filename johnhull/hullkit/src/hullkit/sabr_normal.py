"""Normal, shifted and free-boundary SABR diagnostics for RFR options.

The module implements a transparent model ladder:

1. Bachelier pricing;
2. Hagan normal or shifted-lognormal SABR;
3. a normal-SABR Monte Carlo teacher;
4. grid diagnostics for Hagan approximation error and static arbitrage.

The functions are educational and deliberately expose the lower boundary
``-shift`` instead of silently selecting a shift from market data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm

from . import rfr_options, sabr

FloatArray = NDArray[np.float64]


def _z_over_x(z: float, rho: float) -> float:
    if abs(z) < 1e-7:
        return 1.0 - 0.5 * rho * z + (1.0 / 6.0 - 0.25 * rho**2) * z * z
    root = np.sqrt(1.0 - 2.0 * rho * z + z * z)
    x = np.log((root + z - rho) / (1.0 - rho))
    return float(z / x)


def normal_sabr_implied_vol(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    rho: float,
    nu: float,
) -> float:
    """Hagan normal implied volatility for beta-zero SABR."""

    values = (forward, strike, expiry, alpha, rho, nu)
    if any(not np.isfinite(value) for value in values):
        raise ValueError("normal SABR inputs must be finite")
    if expiry < 0.0 or alpha <= 0.0 or nu < 0.0 or not -1.0 < rho < 1.0:
        raise ValueError("normal SABR expiry/alpha/rho/nu are invalid")
    z = (nu / alpha) * (forward - strike)
    time_correction = 1.0 + ((2.0 - 3.0 * rho**2) / 24.0) * nu**2 * expiry
    return float(alpha * _z_over_x(z, rho) * time_correction)


def normal_sabr_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    rho: float,
    nu: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Bachelier price evaluated at Hagan's normal-SABR implied volatility."""

    sigma = normal_sabr_implied_vol(forward, strike, expiry, alpha, rho, nu)
    return rfr_options.bachelier_price(
        forward,
        strike,
        sigma,
        expiry,
        discount_factor=discount_factor,
        kind=kind,
    )


def shifted_sabr_implied_vol(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float,
) -> float:
    """Hagan lognormal SABR volatility on ``F+shift`` and ``K+shift``."""

    if not np.isfinite(shift) or forward + shift <= 0.0 or strike + shift <= 0.0:
        raise ValueError("forward and strike must lie above the boundary -shift")
    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie in [0, 1]")
    return float(
        sabr.sabr_implied_vol(
            forward + shift,
            strike + shift,
            expiry,
            alpha,
            beta,
            rho,
            nu,
        )
    )


def free_boundary_sabr_implied_vol(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    lower_boundary: float,
) -> float:
    """SABR smile with an explicit attainable lower rate boundary.

    ``lower_boundary`` is represented by the shift ``-lower_boundary``.  The
    name emphasizes that this boundary is a model assumption, not a fitted
    consequence of the quotes.
    """

    if not np.isfinite(lower_boundary):
        raise ValueError("lower_boundary must be finite")
    return shifted_sabr_implied_vol(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=-lower_boundary,
    )


def _black_shifted_price(
    forward: float,
    strike: float,
    expiry: float,
    volatility: float,
    discount_factor: float,
    kind: str,
    shift: float,
) -> float:
    shifted_forward = forward + shift
    shifted_strike = strike + shift
    if shifted_forward <= 0.0 or shifted_strike <= 0.0:
        raise ValueError("forward and strike must lie above -shift")
    if volatility < 0.0 or expiry < 0.0 or discount_factor <= 0.0:
        raise ValueError("volatility/expiry/discount factor are invalid")
    sign = 1.0 if kind == "call" else -1.0 if kind == "put" else 0.0
    if sign == 0.0:
        raise ValueError("kind must be call or put")
    standard_deviation = volatility * np.sqrt(expiry)
    if standard_deviation == 0.0:
        return float(discount_factor * max(sign * (forward - strike), 0.0))
    d1 = np.log(shifted_forward / shifted_strike) / standard_deviation + 0.5 * standard_deviation
    d2 = d1 - standard_deviation
    return float(
        discount_factor
        * sign
        * (shifted_forward * norm.cdf(sign * d1) - shifted_strike * norm.cdf(sign * d2))
    )


def shifted_sabr_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Shifted-Black price evaluated at Hagan shifted-SABR volatility."""

    implied = shifted_sabr_implied_vol(forward, strike, expiry, alpha, beta, rho, nu, shift=shift)
    return _black_shifted_price(
        forward,
        strike,
        expiry,
        implied,
        discount_factor,
        kind,
        shift,
    )


def free_boundary_sabr_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    lower_boundary: float,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Price with a lower-boundary SABR assumption made explicit.

    This is the price-level counterpart of
    :func:`free_boundary_sabr_implied_vol`.  A boundary ``b`` is represented
    by the shifted state ``F-b``; keeping the boundary as an argument makes it
    possible to report that model-risk assumption separately from the fitted
    SABR parameters.
    """

    if not np.isfinite(lower_boundary):
        raise ValueError("lower_boundary must be finite")
    return shifted_sabr_price(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=-lower_boundary,
        discount_factor=discount_factor,
        kind=kind,
    )


def sticky_strike_delta(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Shifted-Black delta with the strike volatility held fixed."""

    implied = shifted_sabr_implied_vol(forward, strike, expiry, alpha, beta, rho, nu, shift=shift)
    shifted_forward = forward + shift
    shifted_strike = strike + shift
    standard_deviation = implied * np.sqrt(expiry)
    sign = 1.0 if kind == "call" else -1.0 if kind == "put" else 0.0
    if sign == 0.0:
        raise ValueError("kind must be call or put")
    if standard_deviation == 0.0:
        return float(
            sign * discount_factor if sign * (shifted_forward - shifted_strike) > 0.0 else 0.0
        )
    d1 = np.log(shifted_forward / shifted_strike) / standard_deviation + 0.5 * standard_deviation
    return float(sign * discount_factor * norm.cdf(sign * d1))


def bartlett_delta(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float,
    discount_factor: float = 1.0,
    kind: str = "call",
    bump: float | None = None,
) -> float:
    r"""Finite-difference Bartlett delta for shifted SABR.

    The alpha co-move follows the instantaneous SABR projection
    :math:`d\alpha/dF=\rho\nu/(F+s)^\beta`.  This removes the correlated
    volatility shock from the residual hedge instead of assuming sticky strike.
    """

    shifted_forward = forward + shift
    if shifted_forward <= 0.0:
        raise ValueError("forward must lie above -shift")
    h = max(1e-7, 1e-4 * shifted_forward) if bump is None else float(bump)
    if h <= 0.0 or forward - h + shift <= 0.0:
        raise ValueError("bump crosses the lower boundary")
    alpha_slope = rho * nu / shifted_forward**beta
    alpha_up = alpha + alpha_slope * h
    alpha_down = alpha - alpha_slope * h
    if min(alpha_up, alpha_down) <= 0.0:
        raise ValueError("Bartlett alpha bump became non-positive")
    up = shifted_sabr_price(
        forward + h,
        strike,
        expiry,
        alpha_up,
        beta,
        rho,
        nu,
        shift=shift,
        discount_factor=discount_factor,
        kind=kind,
    )
    down = shifted_sabr_price(
        forward - h,
        strike,
        expiry,
        alpha_down,
        beta,
        rho,
        nu,
        shift=shift,
        discount_factor=discount_factor,
        kind=kind,
    )
    return float((up - down) / (2.0 * h))


@dataclass(frozen=True)
class NormalSabrTeacherResult:
    """Normal-SABR Monte Carlo price and terminal forwards."""

    price: float
    standard_error: float
    terminal_forward: FloatArray


@dataclass(frozen=True)
class ConditionalNormalSabrTeacherResult:
    """Conditional-Monte-Carlo normal-SABR price diagnostics.

    ``conditional_prices`` integrate out the Brownian shock orthogonal to the
    volatility driver.  Their cross-path standard error is therefore a more
    useful accuracy diagnostic than the raw terminal-payoff error in stressed
    long-maturity/high-volatility regimes.
    """

    price: float
    standard_error: float
    conditional_prices: FloatArray


@dataclass(frozen=True)
class ShiftedSabrTeacherResult:
    """Full-truncation Monte Carlo teacher for shifted SABR."""

    price: float
    standard_error: float
    terminal_forward: FloatArray


def normal_sabr_mc_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    rho: float,
    nu: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
    n_steps: int = 100,
    n_paths: int = 50_000,
    seed: int = 0,
) -> NormalSabrTeacherResult:
    """Euler/log-Euler Monte Carlo teacher for beta-zero SABR."""

    normal_sabr_implied_vol(forward, strike, expiry, alpha, rho, nu)
    if discount_factor <= 0.0 or kind not in {"call", "put"}:
        raise ValueError("discount_factor/kind are invalid")
    if n_steps < 1 or n_paths < 2:
        raise ValueError("n_steps and n_paths are too small")
    rng = np.random.default_rng(seed)
    dt = expiry / n_steps
    sqrt_dt = np.sqrt(dt)
    forwards = np.full(n_paths, forward, dtype=float)
    volatilities = np.full(n_paths, alpha, dtype=float)
    correlation_scale = np.sqrt(1.0 - rho * rho)
    for _ in range(n_steps):
        normals = rng.standard_normal((n_paths, 2))
        forwards += volatilities * sqrt_dt * normals[:, 0]
        correlated = rho * normals[:, 0] + correlation_scale * normals[:, 1]
        volatilities *= np.exp(-0.5 * nu**2 * dt + nu * sqrt_dt * correlated)
    payoff = (
        np.maximum(forwards - strike, 0.0) if kind == "call" else np.maximum(strike - forwards, 0.0)
    )
    discounted = discount_factor * payoff
    return NormalSabrTeacherResult(
        price=float(discounted.mean()),
        standard_error=float(discounted.std(ddof=1) / np.sqrt(n_paths)),
        terminal_forward=np.asarray(forwards),
    )


def normal_sabr_conditional_mc_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    rho: float,
    nu: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
    n_steps: int = 100,
    n_paths: int = 50_000,
    seed: int = 0,
) -> ConditionalNormalSabrTeacherResult:
    r"""Conditional-Monte-Carlo teacher for beta-zero SABR.

    For ``dF=alpha dW_1`` and ``dalpha=nu alpha dW_2``, condition on the
    volatility path and integrate the Brownian component orthogonal to
    ``W_2`` analytically.  The conditional terminal law is normal with

    .. math::

       m = F_0 + \rho(\alpha_T-\alpha_0)/\nu,
       \qquad
       s^2=(1-\rho^2)\int_0^T\alpha_t^2dt.

    This estimator remains seeded and synthetic, while materially reducing
    teacher noise in the long-maturity/high-volatility diagnostic grid.
    """

    normal_sabr_implied_vol(forward, strike, expiry, alpha, rho, nu)
    if discount_factor <= 0.0 or kind not in {"call", "put"}:
        raise ValueError("discount_factor/kind are invalid")
    if n_steps < 1 or n_paths < 2:
        raise ValueError("n_steps and n_paths are too small")
    if expiry == 0.0 or nu == 0.0:
        price = rfr_options.bachelier_price(
            forward,
            strike,
            alpha,
            expiry,
            discount_factor=discount_factor,
            kind=kind,
        )
        conditional = np.full(n_paths, price, dtype=float)
        return ConditionalNormalSabrTeacherResult(price, 0.0, conditional)

    rng = np.random.default_rng(seed)
    dt = expiry / n_steps
    sqrt_dt = np.sqrt(dt)
    volatilities = np.full(n_paths, alpha, dtype=float)
    integrated_variance = np.zeros(n_paths, dtype=float)
    for _ in range(n_steps):
        integrated_variance += volatilities * volatilities * dt
        shock = rng.standard_normal(n_paths)
        volatilities *= np.exp(-0.5 * nu**2 * dt + nu * sqrt_dt * shock)

    conditional_forward = forward + rho * (volatilities - alpha) / nu
    conditional_std = np.sqrt(np.maximum((1.0 - rho * rho) * integrated_variance, 0.0))
    sign = 1.0 if kind == "call" else -1.0
    intrinsic = sign * (conditional_forward - strike)
    positive_std = conditional_std > 0.0
    conditional_prices = np.maximum(intrinsic, 0.0)
    d = np.zeros_like(conditional_forward)
    d[positive_std] = intrinsic[positive_std] / conditional_std[positive_std]
    conditional_prices[positive_std] = intrinsic[positive_std] * norm.cdf(
        d[positive_std]
    ) + conditional_std[positive_std] * norm.pdf(d[positive_std])
    conditional_prices *= discount_factor
    return ConditionalNormalSabrTeacherResult(
        price=float(conditional_prices.mean()),
        standard_error=float(conditional_prices.std(ddof=1) / np.sqrt(n_paths)),
        conditional_prices=np.asarray(conditional_prices),
    )


def shifted_sabr_mc_price(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float,
    discount_factor: float = 1.0,
    kind: str = "call",
    n_steps: int = 100,
    n_paths: int = 50_000,
    seed: int = 0,
) -> ShiftedSabrTeacherResult:
    """Monte Carlo teacher independent of Hagan's shifted-SABR expansion.

    The shifted forward is evolved directly under SABR.  Euler steps use an
    absorbing full-truncation boundary at zero; ``beta=1`` uses a log step so
    the exact positivity property of that special case is retained.  This
    numerical path is intentionally separate from :func:`shifted_sabr_price`
    and is suitable for checking approximation or hedge-model risk.
    """

    shifted_sabr_implied_vol(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=shift,
    )
    if discount_factor <= 0.0 or kind not in {"call", "put"}:
        raise ValueError("discount_factor/kind are invalid")
    if n_steps < 1 or n_paths < 2:
        raise ValueError("n_steps and n_paths are too small")

    rng = np.random.default_rng(seed)
    dt = expiry / n_steps
    sqrt_dt = np.sqrt(dt)
    shifted_forwards = np.full(n_paths, forward + shift, dtype=float)
    volatilities = np.full(n_paths, alpha, dtype=float)
    correlation_scale = np.sqrt(1.0 - rho * rho)
    for _ in range(n_steps):
        normals = rng.standard_normal((n_paths, 2))
        forward_shock = normals[:, 0]
        correlated = rho * forward_shock + correlation_scale * normals[:, 1]
        if beta == 1.0:
            shifted_forwards *= np.exp(
                -0.5 * volatilities * volatilities * dt + volatilities * sqrt_dt * forward_shock
            )
        else:
            local_scale = volatilities * np.maximum(shifted_forwards, 0.0) ** beta
            shifted_forwards = np.maximum(
                shifted_forwards + local_scale * sqrt_dt * forward_shock,
                0.0,
            )
        volatilities *= np.exp(-0.5 * nu**2 * dt + nu * sqrt_dt * correlated)

    terminal = shifted_forwards - shift
    sign = 1.0 if kind == "call" else -1.0
    discounted = discount_factor * np.maximum(sign * (terminal - strike), 0.0)
    return ShiftedSabrTeacherResult(
        price=float(discounted.mean()),
        standard_error=float(discounted.std(ddof=1) / np.sqrt(n_paths)),
        terminal_forward=np.asarray(terminal),
    )


@dataclass(frozen=True)
class StaticArbitrageDiagnostics:
    """Strike convexity/monotonicity and calendar checks for a call grid."""

    nonnegative: bool
    strike_monotone: bool
    strike_convex: bool
    calendar_monotone: bool
    violations: tuple[str, ...]


def call_grid_arbitrage_diagnostics(
    strikes: ArrayLike,
    maturities: ArrayLike,
    call_prices: ArrayLike,
    *,
    tolerance: float = 1e-10,
) -> StaticArbitrageDiagnostics:
    """Hard static checks on a rectangular undiscounted call-price grid."""

    K = np.asarray(strikes, dtype=float)
    T = np.asarray(maturities, dtype=float)
    prices = np.asarray(call_prices, dtype=float)
    if (
        K.ndim != 1
        or K.size < 3
        or T.ndim != 1
        or T.size < 2
        or prices.shape != (T.size, K.size)
        or np.any(~np.isfinite(K))
        or np.any(~np.isfinite(T))
        or np.any(~np.isfinite(prices))
        or np.any(np.diff(K) <= 0.0)
        or np.any(np.diff(T) <= 0.0)
    ):
        raise ValueError("strikes, maturities and call grid are invalid")
    slopes = np.diff(prices, axis=1) / np.diff(K)[None, :]
    nonnegative = bool(np.all(prices >= -tolerance))
    strike_monotone = bool(np.all(slopes <= tolerance))
    strike_convex = bool(np.all(np.diff(slopes, axis=1) >= -tolerance))
    calendar_monotone = bool(np.all(np.diff(prices, axis=0) >= -tolerance))
    violations: list[str] = []
    if not nonnegative:
        violations.append("negative_call_price")
    if not strike_monotone:
        violations.append("strike_monotonicity")
    if not strike_convex:
        violations.append("butterfly_convexity")
    if not calendar_monotone:
        violations.append("calendar_monotonicity")
    return StaticArbitrageDiagnostics(
        nonnegative=nonnegative,
        strike_monotone=strike_monotone,
        strike_convex=strike_convex,
        calendar_monotone=calendar_monotone,
        violations=tuple(violations),
    )


@dataclass(frozen=True)
class HaganErrorDiagnostics:
    """Approximation errors split into long maturity, high-vol and wings."""

    overall_max_abs: float
    overall_rmse: float
    long_maturity_rmse: float
    high_vol_rmse: float
    wing_rmse: float


def hagan_error_diagnostics(
    approximation: ArrayLike,
    teacher: ArrayLike,
    strikes: ArrayLike,
    maturities: ArrayLike,
    volatility_levels: ArrayLike,
) -> HaganErrorDiagnostics:
    """Report Hagan errors in the regions where the expansion is stressed."""

    approx = np.asarray(approximation, dtype=float)
    truth = np.asarray(teacher, dtype=float)
    K = np.asarray(strikes, dtype=float)
    T = np.asarray(maturities, dtype=float)
    levels = np.asarray(volatility_levels, dtype=float)
    expected_shape = (T.size, K.size)
    if (
        K.ndim != 1
        or T.ndim != 1
        or approx.shape != expected_shape
        or truth.shape != expected_shape
        or levels.shape not in {expected_shape, (T.size,)}
        or np.any(~np.isfinite(approx))
        or np.any(~np.isfinite(truth))
        or np.any(~np.isfinite(levels))
    ):
        raise ValueError("Hagan/teacher/region grids are invalid")
    if levels.shape == (T.size,):
        levels = np.broadcast_to(levels[:, None], expected_shape)
    error = approx - truth

    def rmse(mask: NDArray[np.bool_]) -> float:
        return float(np.sqrt(np.mean(error[mask] ** 2)))

    long_mask = np.broadcast_to((T >= np.median(T))[:, None], expected_shape)
    high_mask = levels >= np.median(levels)
    distance = np.abs(K - np.median(K))
    wing_columns = distance >= np.quantile(distance, 0.75)
    wing_mask = np.broadcast_to(wing_columns[None, :], expected_shape)
    return HaganErrorDiagnostics(
        overall_max_abs=float(np.max(np.abs(error))),
        overall_rmse=float(np.sqrt(np.mean(error * error))),
        long_maturity_rmse=rmse(long_mask),
        high_vol_rmse=rmse(high_mask),
        wing_rmse=rmse(wing_mask),
    )


@dataclass(frozen=True)
class HedgeComparison:
    """One-step hedging errors under sticky-strike and Bartlett deltas."""

    sticky_error: FloatArray
    bartlett_error: FloatArray
    sticky_rmse: float
    bartlett_rmse: float


def compare_delta_hedges(
    option_pnl: ArrayLike,
    forward_changes: ArrayLike,
    sticky_delta_value: float,
    bartlett_delta_value: float,
) -> HedgeComparison:
    """Compare both deltas on identical realized option/forward changes."""

    pnl = np.asarray(option_pnl, dtype=float)
    changes = np.asarray(forward_changes, dtype=float)
    if pnl.ndim != 1 or changes.shape != pnl.shape or np.any(~np.isfinite(pnl)):
        raise ValueError("option_pnl and forward_changes must be finite aligned vectors")
    if (
        np.any(~np.isfinite(changes))
        or not np.isfinite(sticky_delta_value)
        or not np.isfinite(bartlett_delta_value)
    ):
        raise ValueError("hedge inputs must be finite")
    sticky_error = pnl - sticky_delta_value * changes
    bartlett_error = pnl - bartlett_delta_value * changes
    return HedgeComparison(
        sticky_error=np.asarray(sticky_error),
        bartlett_error=np.asarray(bartlett_error),
        sticky_rmse=float(np.sqrt(np.mean(sticky_error**2))),
        bartlett_rmse=float(np.sqrt(np.mean(bartlett_error**2))),
    )
