"""Sensitivity, stability and perturbation analysis.

Every check answers the same question in a different direction: *how much of the
published curve is information, and how much is a choice I made?*  Each one
refits the selected estimator under a controlled change and reports the induced
shift in continuously compounded zero rates, in basis points, on the published
grid.  The smoothing hyper-parameters are held at their selected values so that
each check isolates the effect being tested rather than re-running model
selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .curve import DiscountCurve
from .instruments import Instrument

__all__ = ["SensitivityCheck", "curve_shift", "leave_block_out", "quote_perturbation"]

REPORT_TENORS = (0.25, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)


@dataclass
class SensitivityCheck:
    name: str
    description: str
    metric: str
    value: float
    detail: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "metric": self.metric,
            "value": self.value,
            "detail": self.detail,
        }


def curve_shift(
    base: DiscountCurve, other: DiscountCurve, grid: np.ndarray
) -> dict[str, float]:
    """Zero-rate shift statistics between two curves, in basis points."""
    grid = np.asarray(grid, dtype=float)
    delta = (np.asarray(other.zero(grid)) - np.asarray(base.zero(grid))) * 1.0e4
    finite = delta[np.isfinite(delta)]
    if finite.size == 0:
        return {"max_abs_bp": float("nan"), "mean_abs_bp": float("nan")}
    out = {
        "max_abs_bp": float(np.max(np.abs(finite))),
        "mean_abs_bp": float(np.mean(np.abs(finite))),
        "signed_mean_bp": float(np.mean(finite)),
    }
    for tenor in REPORT_TENORS:
        if grid[0] <= tenor <= grid[-1]:
            value = (float(other.zero(np.array([tenor]))[0]) - float(
                base.zero(np.array([tenor]))[0]
            )) * 1.0e4
            out[f"shift_{tenor:g}y_bp"] = value
    return out


def leave_block_out(
    instruments: list[Instrument],
    blocks: list[list[int]],
    fit: Callable[[list[Instrument]], DiscountCurve],
    base: DiscountCurve,
    grid: np.ndarray,
    max_blocks: int = 8,
) -> dict[str, float]:
    """Refit with each of a deterministic sample of maturity blocks removed.

    The dispersion of the refitted curves is a direct estimate of how much any
    single region of the quote set is holding the published curve in place.
    """
    if not blocks:
        return {"n_refits": 0}
    interior = [b for b in range(1, max(len(blocks) - 1, 1))]
    if not interior:
        interior = list(range(len(blocks)))
    step = max(1, len(interior) // max_blocks)
    chosen = interior[::step][:max_blocks]
    shifts: list[float] = []
    tenor_shifts: dict[float, list[float]] = {t: [] for t in REPORT_TENORS}
    for block_index in chosen:
        drop = set(blocks[block_index])
        subset = [inst for k, inst in enumerate(instruments) if k not in drop]
        if len(subset) < 4:
            continue
        try:
            curve = fit(subset)
        except Exception:  # pragma: no cover - defensive
            continue
        stats = curve_shift(base, curve, grid)
        shifts.append(stats["max_abs_bp"])
        for tenor in REPORT_TENORS:
            key = f"shift_{tenor:g}y_bp"
            if key in stats:
                tenor_shifts[tenor].append(abs(stats[key]))
    if not shifts:
        return {"n_refits": 0}
    out = {
        "n_refits": len(shifts),
        "worst_max_abs_bp": float(np.max(shifts)),
        "median_max_abs_bp": float(np.median(shifts)),
    }
    for tenor, values in tenor_shifts.items():
        if values:
            out[f"worst_shift_{tenor:g}y_bp"] = float(np.max(values))
    return out


def quote_perturbation(
    instruments: list[Instrument],
    fit: Callable[[list[Instrument]], DiscountCurve],
    base: DiscountCurve,
    grid: np.ndarray,
    target_maturity: float = 10.0,
    bump_bp: float = 1.0,
) -> dict:
    """Bump the single most heavily weighted quote near ``target_maturity``.

    The response measures how far a one-basis-point data error propagates: a
    local, bounded response is the sign of a well-conditioned estimator.
    """
    if not instruments:
        return {}
    index = min(
        range(len(instruments)),
        key=lambda k: (
            abs(instruments[k].maturity_years - target_maturity),
            -instruments[k].weight,
            instruments[k].instrument_id,
        ),
    )
    target = instruments[index]
    if target.is_rate_quote:
        bumped_quote = target.quote + bump_bp * 0.01
    else:
        # A one-basis-point yield rise lowers a bond price by P * Duration * 1e-4.
        approx_duration = (1.0 - np.exp(-0.025 * target.maturity_years)) / 0.025
        bumped_quote = target.quote - target.quote * approx_duration * bump_bp * 1.0e-4
    perturbed = list(instruments)
    perturbed[index] = Instrument(
        obs_id=target.obs_id,
        instrument_id=target.instrument_id,
        instrument_type=target.instrument_type,
        maturity_years=target.maturity_years,
        coupon_rate=target.coupon_rate,
        payment_frequency=target.payment_frequency,
        quote=float(bumped_quote),
        half_spread=target.half_spread,
        liquidity_score=target.liquidity_score,
        weight=target.weight,
        source=target.source,
        timestamp=target.timestamp,
        quality_factor=target.quality_factor,
        sigma_quote_bp=target.sigma_quote_bp,
        notes=target.notes,
    )
    curve = fit(perturbed)
    stats = curve_shift(base, curve, grid)
    stats["perturbed_instrument"] = target.instrument_id
    stats["perturbed_maturity_years"] = target.maturity_years
    stats["bump_bp"] = bump_bp
    return stats
