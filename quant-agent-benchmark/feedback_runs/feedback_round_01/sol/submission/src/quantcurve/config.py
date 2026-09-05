"""Deterministic model configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CurveConfig:
    """Numerical and statistical controls for the curve workflow."""

    seed: int = 1729
    knot_years: tuple[float, ...] = (
        0.0, 1.0 / 12.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5,
        2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,
        10.0, 12.0, 15.0, 20.0, 25.0, 30.0,
    )
    smoothing_lambda: float = 2.0
    curvature_scale: float = 0.010
    outlier_threshold: float = 3.0
    robust_iterations: int = 5
    min_rate_scale: float = 1.0e-4
    min_price_scale: float = 0.05
    stale_after_days: int = 2
    stale_weight: float = 0.10
    low_liquidity_cutoff: float = 0.20
    holdout_bucket_years: float = 0.5
    holdout_modulus: int = 5
    holdout_remainder: int = 3
    parameter_lower_bound: float = -0.10
    parameter_upper_bound: float = 0.20

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "CurveConfig":
        normalized = dict(values)
        if "knot_years" in normalized:
            normalized["knot_years"] = tuple(float(value) for value in normalized["knot_years"])
        return cls(**normalized)
