"""Known-curve diagnostics used by the feedback-round audit.

The synthetic scenarios are deliberately generic and do not derive parameters
from the supplied market observations.  They distinguish estimator accuracy
from public-quote fit, where no true curve is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .curve import LogDiscountCurve, fit_curve
from .pricing import bond_clean_price, deposit_simple_rate, ois_par_rate


@dataclass(frozen=True)
class KnownDiscount:
    """Analytic continuously compounded zero and forward curves."""

    zero_function: Callable[[np.ndarray], np.ndarray]
    forward_function: Callable[[np.ndarray], np.ndarray]

    def discount(self, maturity: float | np.ndarray) -> np.ndarray:
        t = np.asarray(maturity, dtype=float)
        return np.exp(-self.zero_function(t) * t)

    def zero(self, maturity: np.ndarray) -> np.ndarray:
        return self.zero_function(np.asarray(maturity, dtype=float))

    def forward(self, maturity: np.ndarray) -> np.ndarray:
        return self.forward_function(np.asarray(maturity, dtype=float))


def synthetic_scenarios() -> dict[str, KnownDiscount]:
    """Flat, rising, falling/humped, and negative-rate curve cases."""
    return {
        "flat_2pct": KnownDiscount(lambda t: np.full_like(t, 0.02), lambda t: np.full_like(t, 0.02)),
        "rising": KnownDiscount(lambda t: 0.01 + 0.00045 * t, lambda t: 0.01 + 0.0009 * t),
        "hump": KnownDiscount(
            lambda t: 0.01 + 0.015 * t * np.exp(-t / 8.0),
            lambda t: 0.01 + 0.015 * np.exp(-t / 8.0) * (2.0 * t - t * t / 8.0),
        ),
        "negative_to_positive": KnownDiscount(lambda t: -0.005 + 0.001 * t, lambda t: -0.005 + 0.002 * t),
    }


def synthetic_observations(discounts: KnownDiscount) -> pd.DataFrame:
    """Construct clean observations using generic maturities and coupons."""
    rows: list[dict[str, object]] = []
    for maturity in (1 / 12, 0.25, 0.5, 0.75, 1.0):
        rows.append({
            "obs_id": f"d_{maturity}", "instrument_id": f"d_{maturity}", "instrument_type": "deposit",
            "maturity_years": maturity, "payment_frequency": 1, "coupon_rate": np.nan,
            "normalized_quote": deposit_simple_rate(discounts, maturity), "weight": 1.0, "stale": False,
        })
    for maturity in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0):
        frequency = 1 if maturity <= 2.0 else 2
        rows.append({
            "obs_id": f"s_{maturity}", "instrument_id": f"s_{maturity}", "instrument_type": "ois_swap",
            "maturity_years": maturity, "payment_frequency": frequency, "coupon_rate": np.nan,
            "normalized_quote": ois_par_rate(discounts, maturity, frequency), "weight": 1.0, "stale": False,
        })
    for index, maturity in enumerate((1.3, 2.7, 5.2, 9.6, 15.4, 22.3, 29.7)):
        coupon = 0.012 + 0.003 * (index % 5)
        rows.append({
            "obs_id": f"b_{maturity}", "instrument_id": f"b_{maturity}", "instrument_type": "bond",
            "maturity_years": maturity, "payment_frequency": 2, "coupon_rate": coupon,
            "normalized_quote": bond_clean_price(discounts, maturity, coupon, 2), "weight": 1.0, "stale": False,
        })
    return pd.DataFrame(rows)


def _band_metrics(curve: LogDiscountCurve, truth: KnownDiscount) -> dict[str, dict[str, float]]:
    grid = np.linspace(1 / 12, 30.0, 1801)
    results: dict[str, dict[str, float]] = {}
    for name, mask in {
        "short": grid <= 2.0,
        "medium": (grid > 2.0) & (grid < 15.0),
        "long": grid >= 15.0,
        "overall": np.full(len(grid), True),
    }.items():
        zero_error = curve.zero(grid[mask]) - truth.zero(grid[mask])
        forward_error = curve.forward(grid[mask]) - truth.forward(grid[mask])
        results[name] = {
            "zero_rmse_bp": float(np.sqrt(np.mean(zero_error * zero_error)) * 10_000),
            "forward_rmse_bp": float(np.sqrt(np.mean(forward_error * forward_error)) * 10_000),
        }
    return results


def evaluate_synthetic_suite(long_end_multiplier: float = 1.0) -> dict[str, object]:
    """Fit baseline and advanced models against independently known curves."""
    results: dict[str, object] = {}
    for name, truth in synthetic_scenarios().items():
        observations = synthetic_observations(truth)
        baseline = fit_curve(observations, "baseline", smoothing=0.0, long_end_multiplier=long_end_multiplier)
        advanced = fit_curve(observations, "advanced", smoothing=10.0, long_end_multiplier=long_end_multiplier)
        results[name] = {
            "baseline": _band_metrics(baseline.curve, truth),
            "advanced": _band_metrics(advanced.curve, truth),
        }
    return {
        "synthetic_definition": "four analytic continuously compounded discount curves; 1,801-point truth grid; errors in bp",
        "long_end_multiplier": long_end_multiplier,
        "scenarios": results,
    }
