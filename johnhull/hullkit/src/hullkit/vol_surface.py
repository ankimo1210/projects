"""Arbitrage-aware total-variance surfaces and convex call projection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares, minimize


@dataclass(frozen=True)
class SSVIParameters:
    theta: float
    rho: float
    phi: float


@dataclass(frozen=True)
class SurfaceConstraintComparison:
    """Quote-grid comparison of unconstrained, soft, and hard decoders."""

    unconstrained: np.ndarray
    soft_penalty: np.ndarray
    hard_constrained: np.ndarray
    diagnostics: dict[str, dict[str, float | int | bool]]

    def to_dict(self) -> dict[str, object]:
        return {
            "prices": {
                "unconstrained": self.unconstrained.tolist(),
                "soft_penalty": self.soft_penalty.tolist(),
                "hard_constrained": self.hard_constrained.tolist(),
            },
            "diagnostics": self.diagnostics,
        }


def ssvi_butterfly_margins(theta: float, rho: float, phi: float) -> tuple[float, float]:
    """Sufficient Gatheral--Jacquier butterfly-arbitrage margins.

    Both returned margins must be non-negative.  Keeping the margins explicit
    avoids labelling a merely positive SSVI fit as arbitrage-free.
    """

    if theta <= 0 or phi <= 0 or not -1 < rho < 1:
        raise ValueError("theta/phi must be positive and rho must lie in (-1, 1)")
    multiplier = 1.0 + abs(rho)
    return 4.0 - theta * phi * multiplier, 4.0 - theta * phi**2 * multiplier


def ssvi_is_butterfly_safe(theta: float, rho: float, phi: float, *, tolerance: float = 0.0) -> bool:
    """Whether both documented sufficient SSVI slice conditions pass."""

    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    return min(ssvi_butterfly_margins(theta, rho, phi)) >= -tolerance


def ssvi_total_variance(
    log_moneyness: np.ndarray | float,
    theta: float,
    rho: float,
    phi: float,
) -> np.ndarray | float:
    """Gatheral--Jacquier SSVI slice total variance."""
    if theta <= 0 or phi <= 0 or not -1 < rho < 1:
        raise ValueError("theta/phi must be positive and rho must lie in (-1, 1)")
    k = np.asarray(log_moneyness, dtype=float)
    inner = (phi * k + rho) ** 2 + 1 - rho**2
    result = 0.5 * theta * (1 + rho * phi * k + np.sqrt(inner))
    return float(result) if result.ndim == 0 else result


def fit_ssvi_slice(
    log_moneyness: np.ndarray,
    total_variance: np.ndarray,
    *,
    initial: SSVIParameters | None = None,
) -> SSVIParameters:
    """Fit one positive SSVI slice with bounded least squares."""
    k = np.asarray(log_moneyness, dtype=float)
    target = np.asarray(total_variance, dtype=float)
    if k.ndim != 1 or target.shape != k.shape or len(k) < 5 or np.any(target <= 0):
        raise ValueError("need >=5 matching positive total-variance quotes")
    guess = initial or SSVIParameters(theta=float(np.median(target)), rho=0.0, phi=1.0)
    result = least_squares(
        lambda p: ssvi_total_variance(k, p[0], p[1], p[2]) - target,
        np.array([guess.theta, guess.rho, guess.phi]),
        bounds=(np.array([1e-8, -0.999, 1e-6]), np.array([5.0, 0.999, 50.0])),
    )
    if not result.success:
        raise RuntimeError(f"SSVI fit failed: {result.message}")
    fitted = SSVIParameters(*(float(value) for value in result.x))
    if ssvi_is_butterfly_safe(fitted.theta, fitted.rho, fitted.phi):
        return fitted

    constrained = minimize(
        lambda p: float(np.sum((ssvi_total_variance(k, p[0], p[1], p[2]) - target) ** 2)),
        result.x,
        bounds=((1e-8, 5.0), (-0.999, 0.999), (1e-6, 50.0)),
        constraints=(
            {
                "type": "ineq",
                "fun": lambda p: ssvi_butterfly_margins(p[0], p[1], p[2])[0],
            },
            {
                "type": "ineq",
                "fun": lambda p: ssvi_butterfly_margins(p[0], p[1], p[2])[1],
            },
        ),
        method="SLSQP",
        options={"ftol": 1e-13, "maxiter": 2_000},
    )
    if not constrained.success:
        raise RuntimeError(f"constrained SSVI fit failed: {constrained.message}")
    fitted = SSVIParameters(*(float(value) for value in constrained.x))
    if not ssvi_is_butterfly_safe(fitted.theta, fitted.rho, fitted.phi, tolerance=1e-10):
        raise RuntimeError("constrained SSVI fit violates butterfly conditions")
    return fitted


def project_convex_call_prices(
    strikes: np.ndarray,
    prices: np.ndarray,
    *,
    lower_bound: np.ndarray | float = 0.0,
    upper_bound: np.ndarray | float = np.inf,
) -> np.ndarray:
    """Least-squares project prices onto decreasing, convex strike slices."""
    k = np.asarray(strikes, dtype=float)
    observed = np.asarray(prices, dtype=float)
    if k.ndim != 1 or observed.shape != k.shape or len(k) < 3 or np.any(np.diff(k) <= 0):
        raise ValueError("strikes must be strictly increasing with matching prices")
    lower = np.broadcast_to(np.asarray(lower_bound, dtype=float), observed.shape)
    upper = np.broadcast_to(np.asarray(upper_bound, dtype=float), observed.shape)
    if (
        np.any(~np.isfinite(k))
        or np.any(~np.isfinite(observed))
        or np.any(np.isnan(lower))
        or np.any(np.isnan(upper))
        or np.any(lower > upper)
    ):
        raise ValueError("lower bound exceeds upper bound")
    constraints = [
        {"type": "ineq", "fun": lambda x: -np.diff(x)},
        {
            "type": "ineq",
            "fun": lambda x: np.diff(x)[1:] / np.diff(k)[1:] - np.diff(x)[:-1] / np.diff(k)[:-1],
        },
    ]
    initial = np.linspace(
        np.clip(observed[0], lower[0], upper[0]),
        np.clip(observed[-1], lower[-1], upper[-1]),
        len(observed),
    )
    result = minimize(
        lambda x: float(np.sum((x - observed) ** 2)),
        initial,
        bounds=list(zip(lower, upper, strict=True)),
        constraints=constraints,
        method="SLSQP",
        options={"ftol": 1e-13, "maxiter": 2_000},
    )
    if not result.success:
        raise RuntimeError(f"convex projection failed: {result.message}")
    return np.asarray(result.x)


def variance_term_rmse(model_variance: np.ndarray, target_variance: np.ndarray) -> float:
    """Compute an explicitly separate variance-term consistency metric."""
    model = np.asarray(model_variance, dtype=float)
    target = np.asarray(target_variance, dtype=float)
    if model.shape != target.shape or model.size == 0:
        raise ValueError("variance arrays must have matching shapes")
    if np.any(~np.isfinite(model)) or np.any(~np.isfinite(target)):
        raise ValueError("variance arrays must be finite")
    return float(np.sqrt(np.mean((model - target) ** 2)))


def _slice_diagnostics(
    strikes: np.ndarray,
    prices: np.ndarray,
    observed: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    tolerance: float,
) -> dict[str, float | int | bool]:
    slopes = np.diff(prices) / np.diff(strikes)
    bound_violations = int(
        np.count_nonzero(prices < lower - tolerance) + np.count_nonzero(prices > upper + tolerance)
    )
    monotonicity_violations = int(np.count_nonzero(np.diff(prices) > tolerance))
    convexity_violations = int(np.count_nonzero(np.diff(slopes) < -tolerance))
    total = bound_violations + monotonicity_violations + convexity_violations
    return {
        "quote_rmse": float(np.sqrt(np.mean((prices - observed) ** 2))),
        "bound_violations": bound_violations,
        "monotonicity_violations": monotonicity_violations,
        "convexity_violations": convexity_violations,
        "total_violations": total,
        "hard_checks_pass": total == 0,
        "tolerance": tolerance,
    }


def compare_surface_constraints(
    strikes: np.ndarray,
    prices: np.ndarray,
    *,
    soft_weight: float = 100.0,
    lower_bound: np.ndarray | float = 0.0,
    upper_bound: np.ndarray | float = np.inf,
    tolerance: float = 1e-8,
) -> SurfaceConstraintComparison:
    """Compare raw quotes, a soft penalty fit, and a hard convex projection.

    The soft result is never labelled arbitrage-free from its objective value;
    all three routes are subjected to the same explicit discrete hard checks.
    """

    k = np.asarray(strikes, dtype=float)
    observed = np.asarray(prices, dtype=float)
    if (
        k.ndim != 1
        or observed.shape != k.shape
        or len(k) < 3
        or np.any(np.diff(k) <= 0)
        or soft_weight <= 0
        or tolerance < 0
    ):
        raise ValueError("need an increasing strike grid, matching prices, and positive weight")
    lower = np.broadcast_to(np.asarray(lower_bound, dtype=float), observed.shape)
    upper = np.broadcast_to(np.asarray(upper_bound, dtype=float), observed.shape)
    if np.any(np.isnan(lower)) or np.any(np.isnan(upper)) or np.any(lower > upper):
        raise ValueError("invalid price bounds")

    def soft_objective(candidate: np.ndarray) -> float:
        differences = np.diff(candidate)
        slopes = differences / np.diff(k)
        violations = (
            np.sum(np.maximum(differences, 0.0) ** 2)
            + np.sum(np.maximum(-np.diff(slopes), 0.0) ** 2)
            + np.sum(np.maximum(lower - candidate, 0.0) ** 2)
            + np.sum(np.maximum(candidate - upper, 0.0) ** 2)
        )
        return float(np.sum((candidate - observed) ** 2) + soft_weight * violations)

    soft_result = minimize(
        soft_objective,
        np.clip(observed, lower, upper),
        method="SLSQP",
        options={"ftol": 1e-14, "maxiter": 2_000},
    )
    if not soft_result.success:
        # SLSQP can stall on normalized option prices where quote-fit and
        # penalty terms differ by several orders of magnitude.  Powell is a
        # deterministic derivative-free fallback for this soft diagnostic;
        # the hard projection below remains the authoritative repair.
        soft_result = minimize(
            soft_objective,
            np.asarray(soft_result.x),
            method="Powell",
            options={"ftol": 1e-12, "xtol": 1e-12, "maxiter": 2_000},
        )
    if not soft_result.success:
        raise RuntimeError(f"soft surface fit failed: {soft_result.message}")
    soft = np.asarray(soft_result.x)
    hard = project_convex_call_prices(
        k,
        observed,
        lower_bound=lower,
        upper_bound=upper,
    )
    candidates = {
        "unconstrained": observed.copy(),
        "soft_penalty": soft,
        "hard_constrained": hard,
    }
    diagnostics = {
        name: _slice_diagnostics(k, value, observed, lower, upper, tolerance=tolerance)
        for name, value in candidates.items()
    }
    return SurfaceConstraintComparison(
        unconstrained=candidates["unconstrained"],
        soft_penalty=candidates["soft_penalty"],
        hard_constrained=candidates["hard_constrained"],
        diagnostics=diagnostics,
    )
