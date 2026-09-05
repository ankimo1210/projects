"""Analytic-Jacobian calibration and iteratively reweighted robust fitting."""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from .config import Config
from .curves import CurveBasis, ZeroCurve
from .pricing import PricingEngine


@dataclass
class FitResult:
    curve: ZeroCurve
    quotes: np.ndarray
    robust_weights: np.ndarray
    residual_scale: float
    iterations: int
    converged: bool
    objective: float
    condition_number: float


def fit_curve(frame, kind="advanced", smoothing=None, threshold=None, liquidity=True, config=Config(), bond_stub="prorated", robust=None):
    lam = config.smoothing if smoothing is None else float(smoothing)
    delta = config.huber_threshold if threshold is None else float(threshold)
    if lam < 0 or not np.isfinite(lam) or delta <= 0 or not np.isfinite(delta):
        raise ValueError("smoothing must be nonnegative and threshold positive, both finite")
    engine = PricingEngine(frame, bond_stub=bond_stub)
    basis = CurveBasis(kind, max(30, frame.maturity_years.max()))
    b = basis.matrix(engine.times)
    target = frame.normalized_quote.to_numpy(float)
    sigma = frame.sigma.to_numpy(float)
    reliability = frame.reliability.to_numpy(float) if liquidity else np.ones(len(frame))
    reg = basis.penalty() * np.sqrt(lam * len(frame))
    rate_rows = frame.instrument_type != "bond"
    initial = np.median(target[rate_rows]) * 1e4 if rate_rows.any() else 200.0
    beta = np.full(basis.size, initial) if kind == "advanced" else np.array([initial, 0, 0])
    use_robust = kind == "advanced" if robust is None else bool(robust)
    robust = np.ones(len(frame))
    scale = 1.0
    converged = not use_robust
    # A short IRLS phase detects outliers and supplies a warm start. Exact
    # Huber refinement below avoids slow fixed-point convergence near kinks.
    loops = min(config.max_irls, 8) if use_robust else 1
    for iteration in range(1, loops + 1):
        precision = np.sqrt(reliability * robust) / sigma

        def residual(x):
            q, _ = engine.quotes_and_jacobian(x, b)
            return np.r_[(q - target) * precision, reg @ x]

        def jacobian(x):
            _, j = engine.quotes_and_jacobian(x, b)
            return np.vstack([j * precision[:, None], reg])

        result = least_squares(residual, beta, jac=jacobian, bounds=(-2000, 2000),
                               ftol=1e-10, xtol=1e-10, gtol=1e-9, max_nfev=180)
        if not result.success or not np.all(np.isfinite(result.x)):
            raise RuntimeError(f"{kind} calibration failed: {result.message}")
        if np.max(abs(result.x)) > 1999:
            raise RuntimeError("calibration hit +/-20% coefficient safety bounds; inspect input units and support")
        change = float(np.max(abs(result.x - beta)))
        beta = result.x
        q, _ = engine.quotes_and_jacobian(beta, b)
        if not use_robust:
            break
        standardized = (q - target) / sigma
        # Fixed uncertainty scale defines one objective throughout IRLS. A
        # repeatedly re-estimated residual MAD can mask outliers and oscillate.
        scale = 1.0
        new_weights = np.minimum(1.0, delta * scale / np.maximum(abs(standardized), 1e-12))
        weight_change = np.max(abs(new_weights - robust))
        # The returned weights are exactly those used in the final solve.
        if weight_change < config.irls_tolerance and change < 0.002:
            converged = True
            break
        if iteration < loops:
            robust = 0.5 * robust + 0.5 * new_weights
    if use_robust:
        precision = np.sqrt(reliability) / sigma
        cutoffs = np.r_[delta * np.sqrt(reliability), np.ones(len(reg))]

        def huber_data_linear_penalty(squared):
            rho = np.vstack([squared.copy(), np.ones(len(squared)), np.zeros(len(squared))])
            outside = squared[:len(frame)] > cutoffs[:len(frame)]**2
            indexes = np.flatnonzero(outside)
            root = np.sqrt(squared[indexes])
            c = cutoffs[indexes]
            rho[0, indexes] = 2 * c * root - c**2
            rho[1, indexes] = c / root
            rho[2, indexes] = -0.5 * c / root**3
            return rho

        result = least_squares(residual, beta, jac=jacobian, loss=huber_data_linear_penalty,
                               bounds=(-2000, 2000), ftol=1e-11, xtol=1e-11,
                               gtol=1e-9, max_nfev=800)
        if not result.success or not np.all(np.isfinite(result.x)):
            raise RuntimeError(f"exact Huber refinement failed: {result.message}")
        if np.max(abs(result.x)) > 1999:
            raise RuntimeError("robust calibration hit coefficient safety bounds")
        beta = result.x
        q, _ = engine.quotes_and_jacobian(beta, b)
        robust = np.minimum(1.0, delta / np.maximum(abs((q - target) / sigma), 1e-12))
        iteration += result.nfev
        converged = True
    curve = ZeroCurve(basis, beta)
    return FitResult(curve, engine.quote(curve), robust, scale, iteration, converged,
                     float(2 * result.cost), float(np.linalg.cond(result.jac)))
