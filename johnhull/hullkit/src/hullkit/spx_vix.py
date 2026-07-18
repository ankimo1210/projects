"""Teaching utilities for joint SPX/VIX models (beyond-Hull volume 21).

This module deliberately owns *interfaces and diagnostics*, not the heavy path
simulators.  ``rough_volatility`` remains the owner of rBergomi, Heston and
Hawkes simulation.  The small deterministic functions here make it possible
to compare a four-factor path-dependent-volatility (PDV) baseline, affine
forward-variance factors and a quintic-OU observation map with one joint loss.

Signature models and perturbed optimal transport remain research-only; they
are named in :data:`RESEARCH_ONLY_MODELS` but are not runtime dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import gamma

FloatArray = NDArray[np.float64]

RESEARCH_ONLY_MODELS = ("signature", "perturbed_optimal_transport")
MODEL_OWNERS: Mapping[str, str] = MappingProxyType(
    {
        "joint_objective_and_pdv": "hullkit.spx_vix",
        "rbergomi_heston_hawkes_paths": "rough_volatility",
        "neural_surrogate_training": "deep_hedge_price",
    }
)
CORE_MODEL_FAMILIES = (
    "four_factor_pdv",
    "affine_forward_variance",
    "rough_heston_kernel",
    "quintic_ou",
)


def _finite_vector(values: ArrayLike, name: str, *, nonnegative: bool = False) -> FloatArray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or result.size == 0 or np.any(~np.isfinite(result)):
        raise ValueError(f"{name} must be a non-empty finite vector")
    if nonnegative and np.any(result < 0.0):
        raise ValueError(f"{name} must be non-negative")
    return result


@dataclass(frozen=True)
class PDVParameters:
    """Parameters of a four-factor PDV volatility map.

    The state contains fast/slow exponentially weighted returns and fast/slow
    exponentially weighted squared returns.  The affine observation is a
    volatility, which is floored before squaring to obtain instantaneous
    variance.  Decays use the convention ``new = decay*old + (1-decay)*x``.
    """

    return_decays: tuple[float, float] = (0.80, 0.98)
    variance_decays: tuple[float, float] = (0.70, 0.97)
    intercept: float = 0.12
    return_loadings: tuple[float, float] = (-0.35, -0.15)
    variance_loadings: tuple[float, float] = (0.45, 0.25)
    volatility_floor: float = 1e-4

    def validate(self) -> None:
        decays = (*self.return_decays, *self.variance_decays)
        if any(not 0.0 <= decay < 1.0 for decay in decays):
            raise ValueError("PDV decays must lie in [0, 1)")
        coefficients = (
            self.intercept,
            *self.return_loadings,
            *self.variance_loadings,
            self.volatility_floor,
        )
        if any(not np.isfinite(value) for value in coefficients):
            raise ValueError("PDV coefficients must be finite")
        if self.volatility_floor <= 0.0:
            raise ValueError("volatility_floor must be positive")


@dataclass(frozen=True)
class PDVPath:
    """Four PDV factors and the resulting variance path."""

    factors: FloatArray
    variance: FloatArray


def four_factor_pdv(
    log_returns: ArrayLike,
    parameters: PDVParameters = PDVParameters(),
    *,
    initial_variance: float | None = None,
) -> PDVPath:
    """Build the causal four-factor PDV state from a return history.

    ``factors[t]`` only uses returns strictly before or at ``t-1``.  This
    explicit update order is useful when the function is reused in calibration
    or walk-forward tests because it prevents accidental look-ahead.
    """

    parameters.validate()
    returns = _finite_vector(log_returns, "log_returns")
    if initial_variance is None:
        initial_variance = float(max(np.mean(returns**2), parameters.volatility_floor**2))
    if not np.isfinite(initial_variance) or initial_variance < 0.0:
        raise ValueError("initial_variance must be finite and non-negative")

    factors = np.empty((returns.size + 1, 4), dtype=float)
    factors[0] = (0.0, 0.0, initial_variance, initial_variance)
    variance = np.empty(returns.size + 1, dtype=float)

    def observe(state: FloatArray) -> float:
        raw_volatility = (
            parameters.intercept
            + parameters.return_loadings[0] * state[0]
            + parameters.return_loadings[1] * state[1]
            + parameters.variance_loadings[0] * np.sqrt(max(state[2], 0.0))
            + parameters.variance_loadings[1] * np.sqrt(max(state[3], 0.0))
        )
        return max(raw_volatility, parameters.volatility_floor) ** 2

    # If the intercept/loadings are intentionally all zero, the documented
    # floor remains the state value rather than silently returning NaN.
    variance[0] = observe(factors[0])
    for index, value in enumerate(returns):
        previous = factors[index]
        factors[index + 1, 0] = (
            parameters.return_decays[0] * previous[0] + (1.0 - parameters.return_decays[0]) * value
        )
        factors[index + 1, 1] = (
            parameters.return_decays[1] * previous[1] + (1.0 - parameters.return_decays[1]) * value
        )
        squared = value * value
        factors[index + 1, 2] = (
            parameters.variance_decays[0] * previous[2]
            + (1.0 - parameters.variance_decays[0]) * squared
        )
        factors[index + 1, 3] = (
            parameters.variance_decays[1] * previous[3]
            + (1.0 - parameters.variance_decays[1]) * squared
        )
        variance[index + 1] = observe(factors[index + 1])
    return PDVPath(factors=factors, variance=variance)


def affine_forward_variance(
    maturities: ArrayLike,
    long_run_variance: float,
    factor_levels: ArrayLike,
    mean_reversions: ArrayLike,
) -> FloatArray:
    r"""Affine-forward-variance comparison curve.

    .. math:: \xi(T)=\bar v+\sum_i x_i e^{-\kappa_iT}.
    """

    times = _finite_vector(maturities, "maturities", nonnegative=True)
    factors = _finite_vector(factor_levels, "factor_levels")
    kappas = _finite_vector(mean_reversions, "mean_reversions", nonnegative=True)
    if factors.shape != kappas.shape:
        raise ValueError("factor_levels and mean_reversions must have identical shapes")
    if not np.isfinite(long_run_variance) or long_run_variance < 0.0:
        raise ValueError("long_run_variance must be finite and non-negative")
    curve = long_run_variance + np.exp(-np.outer(times, kappas)) @ factors
    if np.any(curve < 0.0):
        raise ValueError("affine factors imply negative forward variance")
    return np.asarray(curve)


def rough_heston_fractional_kernel(times: ArrayLike, hurst: float) -> FloatArray:
    r"""Fractional rough-Heston kernel ``t^(H-1/2) / Gamma(H+1/2)``.

    This supplies the comparison kernel while leaving convergence-controlled
    rough path simulation with the dedicated ``rough_volatility`` project.
    """

    values = _finite_vector(times, "times")
    if np.any(values <= 0.0):
        raise ValueError("rough-Heston kernel times must be positive")
    if not np.isfinite(hurst) or not 0.0 < hurst <= 0.5:
        raise ValueError("hurst must lie in (0, 0.5]")
    return np.asarray(values ** (hurst - 0.5) / gamma(hurst + 0.5))


def quintic_ou_variance(state: ArrayLike, coefficients: ArrayLike) -> FloatArray:
    """Positive quintic-OU observation map ``variance = p_5(X)^2``.

    The OU transition itself can be supplied by a caller (or by
    ``rough_volatility.fractional_ou.ou_exact``).  Keeping the observation map
    here avoids a second competing OU simulator.
    """

    values = np.asarray(state, dtype=float)
    coeffs = np.asarray(coefficients, dtype=float)
    if np.any(~np.isfinite(values)) or coeffs.shape != (6,) or np.any(~np.isfinite(coeffs)):
        raise ValueError("state must be finite and coefficients must contain powers 0..5")
    polynomial = np.polynomial.polynomial.polyval(values, coeffs)
    return np.asarray(polynomial * polynomial)


@dataclass(frozen=True)
class JointMarketTargets:
    """Aligned observables used by the joint SPX/VIX objective."""

    spx_iv: FloatArray
    vix_futures: FloatArray
    vix_options: FloatArray
    variance_term: FloatArray

    def validated(self) -> JointMarketTargets:
        return JointMarketTargets(
            spx_iv=_finite_vector(self.spx_iv, "spx_iv", nonnegative=True),
            vix_futures=_finite_vector(self.vix_futures, "vix_futures", nonnegative=True),
            vix_options=_finite_vector(self.vix_options, "vix_options", nonnegative=True),
            variance_term=_finite_vector(self.variance_term, "variance_term", nonnegative=True),
        )


@dataclass(frozen=True)
class JointObjective:
    """Total and per-market normalized mean-square errors."""

    total: float
    components: Mapping[str, float]


def joint_spx_vix_objective(
    model: JointMarketTargets,
    market: JointMarketTargets,
    *,
    scales: Mapping[str, float | ArrayLike] | None = None,
    weights: Mapping[str, float] | None = None,
) -> JointObjective:
    """Evaluate SPX IV, VIX futures/options and variance in one objective.

    Explicit scales prevent a quote expressed in index points from dominating
    an implied volatility expressed as a decimal.  The default scale is one,
    suitable for already-normalized synthetic fixtures.
    """

    predicted = model.validated()
    observed = market.validated()
    scale_map = {} if scales is None else dict(scales)
    weight_map = {} if weights is None else dict(weights)
    components: dict[str, float] = {}
    total = 0.0
    for name in ("spx_iv", "vix_futures", "vix_options", "variance_term"):
        lhs = getattr(predicted, name)
        rhs = getattr(observed, name)
        if lhs.shape != rhs.shape:
            raise ValueError(f"model and market {name} grids must align")
        scale = np.asarray(scale_map.get(name, 1.0), dtype=float)
        if np.any(~np.isfinite(scale)) or np.any(scale <= 0.0):
            raise ValueError(f"{name} scales must be finite and positive")
        try:
            residual = (lhs - rhs) / scale
        except ValueError as exc:
            raise ValueError(f"{name} scale is not broadcastable to the quote grid") from exc
        value = float(np.mean(residual * residual))
        weight = float(weight_map.get(name, 1.0))
        if not np.isfinite(weight) or weight < 0.0:
            raise ValueError(f"{name} weight must be finite and non-negative")
        components[name] = value
        total += weight * value
    return JointObjective(total=float(total), components=components)


@dataclass(frozen=True)
class VixTeacherResult:
    """Nested-Monte-Carlo VIX values, future and call estimate."""

    vix: FloatArray
    future: float
    call_price: float
    standard_error: float


def nested_vix_teacher(
    conditional_variance_paths: ArrayLike,
    *,
    strike: float,
    discount_factor: float = 1.0,
    index_scale: float = 100.0,
) -> VixTeacherResult:
    """Price a VIX call from ``(outer, inner, time)`` variance paths.

    Each outer state gets a conditional expected average variance from its
    inner paths.  Taking the square root *after* that conditional expectation
    is the important nested-MC ordering.
    """

    paths = np.asarray(conditional_variance_paths, dtype=float)
    if paths.ndim != 3 or min(paths.shape) < 1 or np.any(~np.isfinite(paths)):
        raise ValueError("conditional_variance_paths must have shape (outer, inner, time)")
    if np.any(paths < 0.0):
        raise ValueError("variance paths must be non-negative")
    if strike < 0.0 or not 0.0 < discount_factor <= 1.0 or index_scale <= 0.0:
        raise ValueError("strike/discount_factor/index_scale are invalid")
    conditional_average = paths.mean(axis=(1, 2))
    vix = index_scale * np.sqrt(conditional_average)
    discounted = discount_factor * np.maximum(vix - strike, 0.0)
    standard_error = (
        0.0 if discounted.size == 1 else float(discounted.std(ddof=1) / np.sqrt(discounted.size))
    )
    return VixTeacherResult(
        vix=np.asarray(vix),
        future=float(vix.mean()),
        call_price=float(discounted.mean()),
        standard_error=standard_error,
    )


def finite_difference_greeks(
    pricer: Callable[[float], float],
    spot: float,
    *,
    bump: float | None = None,
) -> dict[str, float]:
    """Return central delta/gamma for any deterministic scalar pricer."""

    if not np.isfinite(spot) or spot <= 0.0:
        raise ValueError("spot must be finite and positive")
    h = 1e-4 * spot if bump is None else float(bump)
    if not np.isfinite(h) or not 0.0 < h < spot:
        raise ValueError("bump must lie in (0, spot)")
    base = float(pricer(spot))
    up = float(pricer(spot + h))
    down = float(pricer(spot - h))
    if not np.all(np.isfinite([base, up, down])):
        raise ValueError("pricer returned a non-finite value")
    return {
        "price": base,
        "delta": (up - down) / (2.0 * h),
        "gamma": (up - 2.0 * base + down) / (h * h),
    }


def out_of_domain_flags(
    samples: ArrayLike,
    lower: ArrayLike,
    upper: ArrayLike,
) -> NDArray[np.bool_]:
    """Flag rows outside an axis-aligned training domain."""

    values = np.asarray(samples, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    if values.ndim != 2 or lo.shape != (values.shape[1],) or hi.shape != lo.shape:
        raise ValueError("samples must be 2-D and bounds must match its columns")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(lo)) or np.any(~np.isfinite(hi)):
        raise ValueError("samples and bounds must be finite")
    if np.any(lo >= hi):
        raise ValueError("every lower bound must be below its upper bound")
    return np.any((values < lo) | (values > hi), axis=1)


def _quadratic_design(samples: FloatArray) -> FloatArray:
    columns = [np.ones(samples.shape[0], dtype=float)]
    columns.extend(samples[:, index] for index in range(samples.shape[1]))
    columns.extend(
        samples[:, left] * samples[:, right]
        for left in range(samples.shape[1])
        for right in range(left, samples.shape[1])
    )
    return np.column_stack(columns)


@dataclass(frozen=True)
class PolynomialSurrogate:
    """Small CPU quadratic surrogate with an explicit training domain."""

    coefficients: FloatArray
    n_features: int
    lower: FloatArray
    upper: FloatArray

    def predict(self, samples: ArrayLike) -> FloatArray:
        values = np.asarray(samples, dtype=float)
        if values.ndim != 2 or values.shape[1] != self.n_features:
            raise ValueError("samples do not match the surrogate feature count")
        if np.any(~np.isfinite(values)):
            raise ValueError("samples must be finite")
        return np.asarray(_quadratic_design(values) @ self.coefficients)

    def ood(self, samples: ArrayLike) -> NDArray[np.bool_]:
        return out_of_domain_flags(samples, self.lower, self.upper)


def fit_polynomial_surrogate(
    samples: ArrayLike,
    teacher_values: ArrayLike,
    *,
    ridge: float = 1e-10,
) -> PolynomialSurrogate:
    """Fit a deterministic quadratic learned surrogate with ridge least squares.

    This baseline gives the nested-MC teacher a real, dependency-free surrogate
    comparator.  Neural and signature surrogates remain outside ``hullkit``.
    """

    values = np.asarray(samples, dtype=float)
    targets = np.asarray(teacher_values, dtype=float)
    if (
        values.ndim != 2
        or values.shape[0] < 2
        or values.shape[1] < 1
        or targets.shape != (values.shape[0],)
        or np.any(~np.isfinite(values))
        or np.any(~np.isfinite(targets))
    ):
        raise ValueError("samples and teacher_values must be finite and aligned")
    if not np.isfinite(ridge) or ridge < 0.0:
        raise ValueError("ridge must be finite and non-negative")
    design = _quadratic_design(values)
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
    return PolynomialSurrogate(
        coefficients=np.asarray(coefficients),
        n_features=values.shape[1],
        lower=np.min(values, axis=0),
        upper=np.max(values, axis=0),
    )


@dataclass(frozen=True)
class SurrogateComparison:
    """Accuracy and measured speed comparison against a numerical teacher."""

    price_rmse: float
    price_max_abs: float
    greek_rmse: float | None
    speedup: float


def compare_teacher_surrogate(
    teacher_prices: ArrayLike,
    surrogate_prices: ArrayLike,
    *,
    teacher_seconds: float,
    surrogate_seconds: float,
    teacher_greeks: ArrayLike | None = None,
    surrogate_greeks: ArrayLike | None = None,
) -> SurrogateComparison:
    """Summarize teacher/surrogate price, Greek and wall-clock differences."""

    teacher = _finite_vector(teacher_prices, "teacher_prices")
    surrogate = _finite_vector(surrogate_prices, "surrogate_prices")
    if teacher.shape != surrogate.shape:
        raise ValueError("teacher and surrogate price grids must align")
    if not np.isfinite(teacher_seconds) or not np.isfinite(surrogate_seconds):
        raise ValueError("timings must be finite")
    if teacher_seconds <= 0.0 or surrogate_seconds <= 0.0:
        raise ValueError("timings must be positive")
    greek_rmse = None
    if (teacher_greeks is None) != (surrogate_greeks is None):
        raise ValueError("both Greek grids must be supplied together")
    if teacher_greeks is not None and surrogate_greeks is not None:
        greek_teacher = np.asarray(teacher_greeks, dtype=float)
        greek_surrogate = np.asarray(surrogate_greeks, dtype=float)
        if greek_teacher.shape != greek_surrogate.shape or np.any(~np.isfinite(greek_teacher)):
            raise ValueError("teacher and surrogate Greek grids must be finite and aligned")
        if np.any(~np.isfinite(greek_surrogate)):
            raise ValueError("teacher and surrogate Greek grids must be finite and aligned")
        greek_rmse = float(np.sqrt(np.mean((greek_teacher - greek_surrogate) ** 2)))
    error = teacher - surrogate
    return SurrogateComparison(
        price_rmse=float(np.sqrt(np.mean(error * error))),
        price_max_abs=float(np.max(np.abs(error))),
        greek_rmse=greek_rmse,
        speedup=float(teacher_seconds / surrogate_seconds),
    )
