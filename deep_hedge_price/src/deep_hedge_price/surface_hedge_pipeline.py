"""Synthetic surrogate -> calibration -> forecast -> hedge orchestration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .hedge_capstone import HedgeComparison, synthetic_hedge_capstone
from .pricing_calibration import CalibrationResult, calibrate_parameters
from .walk_forward import fit_regularized_linear, har_features


@dataclass(frozen=True)
class SurfaceHedgePipelineResult:
    calibration: CalibrationResult
    true_parameters: np.ndarray
    forecast_variance: float
    forecast_volatility: float
    hedge: HedgeComparison


def run_synthetic_surface_hedge_pipeline(
    *,
    seed: int = 0,
    n_paths: int = 1_000,
    n_steps: int = 20,
    deep_policy_positions: np.ndarray | None = None,
) -> SurfaceHedgePipelineResult:
    """Run the vol-20 chain on one fixed synthetic scenario.

    The polynomial quote map stands in for a trained forward surrogate.  The
    same interface accepts a real surrogate, while this core fixture remains
    CPU-only and deterministic.  ``deep_policy_positions`` is an external
    Phase-1 adapter: when absent, no neural-policy result is fabricated.
    """
    strikes = np.linspace(-0.3, 0.3, 17)
    truth = np.array([0.20, -0.035, 0.16])

    def teacher(parameters: np.ndarray) -> np.ndarray:
        return parameters[0] + parameters[1] * strikes + parameters[2] * strikes**2

    def surrogate(parameters: np.ndarray) -> np.ndarray:
        base = teacher(parameters)
        return base + 2e-5 * np.sin(7 * strikes)

    target_quotes = teacher(truth)
    calibration = calibrate_parameters(
        surrogate,
        target_quotes,
        np.array([0.18, 0.0, 0.10]),
        (np.array([0.05, -0.3, 0.0]), np.array([0.6, 0.3, 0.8])),
        n_starts=5,
        seed=seed,
    )

    rng = np.random.default_rng(seed + 1)
    log_variance = np.empty(180)
    long_run = np.log(max(calibration.parameters[0] ** 2, 1e-8))
    log_variance[0] = long_run
    for index in range(1, len(log_variance)):
        log_variance[index] = (
            0.96 * log_variance[index - 1] + 0.04 * long_run + rng.normal(0.0, 0.025)
        )
    features, targets = har_features(log_variance)
    split = int(0.8 * len(features))
    forecaster = fit_regularized_linear(features[:split], targets[:split], ridge=1e-3)
    predicted_log_variance = float(forecaster.predict(features[-1:])[0])
    forecast_variance = float(np.clip(np.exp(predicted_log_variance), 0.0025, 0.36))
    forecast_volatility = float(np.sqrt(forecast_variance))
    hedge = synthetic_hedge_capstone(
        n_paths=n_paths,
        n_steps=n_steps,
        seed=seed + 2,
        volatility=forecast_volatility,
        deep_policy_positions=deep_policy_positions,
    )
    return SurfaceHedgePipelineResult(
        calibration=calibration,
        true_parameters=truth,
        forecast_variance=forecast_variance,
        forecast_volatility=forecast_volatility,
        hedge=hedge,
    )
