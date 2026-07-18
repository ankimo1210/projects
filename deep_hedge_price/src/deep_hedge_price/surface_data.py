"""Synthetic forward-surface datasets for inverse-problem experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SUPPORTED_MODELS = ("heston", "sabr", "rbergomi")


@dataclass(frozen=True)
class ForwardSurfaceDataset:
    model: str
    parameters: np.ndarray
    log_moneyness: np.ndarray
    maturities: np.ndarray
    implied_volatility: np.ndarray
    variance_term: np.ndarray
    standard_error: np.ndarray
    teacher_method: str
    seed: int


@dataclass(frozen=True)
class SurfaceTradeoff:
    lambda_var: float
    total_loss: float
    iv_loss: float
    variance_loss: float


def _parameter_bounds(model: str) -> tuple[np.ndarray, np.ndarray]:
    bounds = {
        "heston": (np.array([0.01, 0.5, 0.01, 0.1, -0.9]), np.array([0.16, 4.0, 0.16, 1.2, 0.2])),
        "sabr": (np.array([0.05, 0.1, -0.9, 0.05]), np.array([0.6, 1.0, 0.5, 1.5])),
        "rbergomi": (np.array([0.01, 0.03, 0.03, -0.95]), np.array([0.2, 0.45, 1.5, -0.05])),
    }
    try:
        return bounds[model]
    except KeyError as exc:
        raise ValueError(f"model must be one of {SUPPORTED_MODELS}") from exc


def generate_forward_surfaces(
    model: str,
    *,
    n_samples: int,
    seed: int,
    log_moneyness: np.ndarray | None = None,
    maturities: np.ndarray | None = None,
) -> ForwardSurfaceDataset:
    """Generate deterministic model-specific IV/variance fixtures."""
    if n_samples < 1:
        raise ValueError("n_samples must be positive")
    lower, upper = _parameter_bounds(model)
    rng = np.random.default_rng(seed)
    parameters = rng.uniform(lower, upper, size=(n_samples, len(lower)))
    k = (
        np.linspace(-0.3, 0.3, 13)
        if log_moneyness is None
        else np.asarray(log_moneyness, dtype=float)
    )
    t = (
        np.array([0.08, 0.25, 0.5, 1.0, 2.0])
        if maturities is None
        else np.asarray(maturities, dtype=float)
    )
    if (
        k.ndim != 1
        or t.ndim != 1
        or k.size < 2
        or t.size < 1
        or np.any(~np.isfinite(k))
        or np.any(~np.isfinite(t))
        or np.any(np.diff(k) <= 0)
        or np.any(np.diff(t) <= 0)
        or np.any(t <= 0)
    ):
        raise ValueError("log_moneyness/maturities must be finite and strictly increasing")
    kk, tt = np.meshgrid(k, t)
    surfaces: list[np.ndarray] = []
    terms: list[np.ndarray] = []
    for p in parameters:
        if model == "heston":
            v0, kappa, theta, xi, rho = p
            term = theta + (v0 - theta) * np.exp(-kappa * t)
            iv = np.sqrt(np.maximum(theta + (v0 - theta) * np.exp(-kappa * tt), 1e-8))
            iv = iv * (1 + 0.20 * xi * kk**2) + 0.12 * rho * xi * kk
        elif model == "sabr":
            alpha, beta, rho, nu = p
            term = np.full_like(t, alpha**2)
            iv = alpha * np.exp(-(1 - beta) * kk) * (1 + 0.35 * nu**2 * kk**2 * tt)
            iv = iv * (1 + 0.20 * rho * nu * kk)
        else:
            v0, hurst, eta, rho = p
            term = v0 * (1 + 0.18 * eta**2 * t ** (2 * hurst))
            iv = np.sqrt(v0) * (1 + 0.30 * eta * np.abs(kk) * tt**hurst + 0.15 * rho * eta * kk)
        surfaces.append(np.maximum(iv, 1e-4))
        terms.append(np.maximum(term, 1e-8))
    return ForwardSurfaceDataset(
        model=model,
        parameters=parameters,
        log_moneyness=k,
        maturities=t,
        implied_volatility=np.stack(surfaces),
        variance_term=np.stack(terms),
        standard_error=np.zeros_like(np.stack(surfaces)),
        teacher_method="synthetic_proxy",
        seed=seed,
    )


def generate_numerical_forward_surfaces(
    model: str,
    *,
    n_samples: int,
    seed: int,
    log_moneyness: np.ndarray | None = None,
    maturities: np.ndarray | None = None,
    rbergomi_paths: int = 2_000,
) -> ForwardSurfaceDataset:
    """Generate surfaces with hullkit's COS/Hagan/rough-Bergomi teachers.

    This optional integration is intentionally separate from the fast proxy
    generator.  It fails explicitly when the torch-free ``hullkit`` package is
    unavailable, while serialized JSON/NPZ artifacts remain the project
    boundary used by the teaching notebooks.
    """

    if n_samples < 1 or rbergomi_paths < 100:
        raise ValueError("n_samples must be positive and rbergomi_paths at least 100")
    try:
        from hullkit.surrogate_data import forward_surface_teacher
    except ImportError as exc:  # pragma: no cover - isolated-install contract
        raise RuntimeError("hullkit is required for numerical forward-surface teachers") from exc
    lower, upper = _parameter_bounds(model)
    rng = np.random.default_rng(seed)
    parameters = rng.uniform(lower, upper, size=(n_samples, len(lower)))
    k = (
        np.linspace(-0.3, 0.3, 13)
        if log_moneyness is None
        else np.asarray(log_moneyness, dtype=float)
    )
    t = (
        np.array([0.08, 0.25, 0.5, 1.0, 2.0])
        if maturities is None
        else np.asarray(maturities, dtype=float)
    )
    if (
        k.ndim != 1
        or t.ndim != 1
        or len(k) < 2
        or len(t) < 1
        or np.any(np.diff(k) <= 0)
        or np.any(np.diff(t) <= 0)
        or np.any(t <= 0)
    ):
        raise ValueError("log_moneyness/maturities must be strictly increasing")
    strikes = np.exp(k)
    implied_volatility = []
    standard_error = []
    variance_term = []
    methods = []
    for sample_index, values in enumerate(parameters):
        if model == "heston":
            v0, kappa, theta, xi, rho = values
            teacher_parameters = {
                "v0": v0,
                "kappa": kappa,
                "theta": theta,
                "xi": xi,
                "rho": rho,
            }
            term = theta + (v0 - theta) * np.exp(-kappa * t)
        elif model == "sabr":
            alpha, beta, rho, nu = values
            teacher_parameters = {
                "alpha": alpha,
                "beta": beta,
                "rho": rho,
                "nu": nu,
            }
            term = np.full_like(t, alpha**2)
        else:
            xi0, hurst, eta, rho = values
            teacher_parameters = {
                "xi0": xi0,
                "eta": eta,
                "hurst": hurst,
                "rho": rho,
                "n_steps": 24,
            }
            term = np.full_like(t, xi0)
        result = forward_surface_teacher(
            model,
            1.0,
            strikes,
            t,
            0.0,
            teacher_parameters,
            seed=seed + 10_000 * sample_index,
            n_paths=rbergomi_paths,
        )
        implied_volatility.append(result["implied_volatility"])
        standard_error.append(result["standard_error"])
        variance_term.append(term)
        methods.append(result["method"])
    if len(set(methods)) != 1:
        raise RuntimeError("numerical teacher methods changed within one dataset")
    return ForwardSurfaceDataset(
        model=model,
        parameters=parameters,
        log_moneyness=k,
        maturities=t,
        implied_volatility=np.stack(implied_volatility),
        variance_term=np.stack(variance_term),
        standard_error=np.stack(standard_error),
        teacher_method=methods[0],
        seed=seed,
    )


def joint_surface_loss(
    predicted_iv: np.ndarray,
    target_iv: np.ndarray,
    predicted_variance: np.ndarray,
    target_variance: np.ndarray,
    *,
    lambda_var: float,
) -> tuple[float, float, float]:
    """Return total, IV, and variance losses for a joint objective."""
    if not np.isfinite(lambda_var) or lambda_var < 0:
        raise ValueError("lambda_var cannot be negative")
    predicted_iv = np.asarray(predicted_iv, dtype=float)
    target_iv = np.asarray(target_iv, dtype=float)
    predicted_variance = np.asarray(predicted_variance, dtype=float)
    target_variance = np.asarray(target_variance, dtype=float)
    if predicted_iv.shape != target_iv.shape or predicted_iv.size == 0:
        raise ValueError("predicted and target IV arrays must have matching non-empty shapes")
    if predicted_variance.shape != target_variance.shape or predicted_variance.size == 0:
        raise ValueError("predicted and target variance arrays must have matching non-empty shapes")
    arrays = (predicted_iv, target_iv, predicted_variance, target_variance)
    if any(np.any(~np.isfinite(array)) for array in arrays):
        raise ValueError("joint loss inputs must be finite")
    iv_loss = float(np.mean((predicted_iv - target_iv) ** 2))
    variance_loss = float(np.mean((predicted_variance - target_variance) ** 2))
    return iv_loss + lambda_var * variance_loss, iv_loss, variance_loss


def joint_surface_pareto(
    candidates: dict[float, tuple[np.ndarray, np.ndarray]],
    target_iv: np.ndarray,
    target_variance: np.ndarray,
) -> tuple[tuple[SurfaceTradeoff, ...], tuple[SurfaceTradeoff, ...]]:
    """Evaluate a lambda sweep and return all and non-dominated refitted points.

    Each candidate must already have been refitted at its dictionary key
    ``lambda_var``; merely reweighting one fixed fit is not a calibration
    frontier.
    """

    if not candidates:
        raise ValueError("candidates cannot be empty")
    points = []
    for lambda_var, (predicted_iv, predicted_variance) in sorted(candidates.items()):
        total, iv_loss, variance_loss = joint_surface_loss(
            predicted_iv,
            target_iv,
            predicted_variance,
            target_variance,
            lambda_var=lambda_var,
        )
        points.append(SurfaceTradeoff(float(lambda_var), total, iv_loss, variance_loss))
    frontier = tuple(
        point
        for point in points
        if not any(
            other.iv_loss <= point.iv_loss
            and other.variance_loss <= point.variance_loss
            and (other.iv_loss < point.iv_loss or other.variance_loss < point.variance_loss)
            for other in points
        )
    )
    return tuple(points), frontier
