"""Maturity-blocked holdout validation and model selection.

Why not a random split
----------------------
The universe contains several quotes on *the same* pillar (four 10Y OIS from
different venues) and bonds whose maturities differ by days from a benchmark
swap.  A random split would put near-identical instruments on both sides, so the
"validation" error would measure quote dispersion, not curve quality, and would
flatter any estimator that simply interpolates.

What is done instead
--------------------
Instruments are grouped into **maturity blocks**: a new block starts whenever the
gap to the previous maturity exceeds ``max(abs_gap, rel_gap * T)``.  Every quote
in a block moves together.  Blocks are then assigned deterministically -- every
``stride``-th interior block is held out -- so the training set always spans the
full maturity range and the validation error is a genuine *interpolation* test:
can the curve price a maturity region it never saw?

The first and last blocks are never held out, otherwise the metric would be
measuring extrapolation policy rather than curve quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .instruments import Instrument
from .models import (
    AdvancedFit,
    BaselineFit,
    FitConfig,
    fit_advanced,
    fit_baseline,
    fit_metrics,
)

__all__ = [
    "HoldoutConfig",
    "HoldoutSplit",
    "ModelComparison",
    "build_split",
    "compare_models",
    "forward_admissibility",
]


@dataclass(frozen=True)
class HoldoutConfig:
    #: A new maturity block starts when the gap exceeds this many years ...
    block_abs_gap_years: float = 0.15
    #: ... or this fraction of the maturity, whichever is larger.
    block_rel_gap: float = 0.02
    #: Every ``stride``-th interior block is held out.
    stride: int = 4
    #: Minimum number of blocks before a blocked holdout is attempted.
    min_blocks: int = 6
    #: Relative improvement the advanced model must show on the holdout before it
    #: is preferred to the simpler baseline.
    selection_margin: float = 0.05
    #: Economic-admissibility gate.  A curve whose instantaneous forward leaves
    #: the quoted rate range by more than this many percentage points is not a
    #: usable discount curve however well it reprices: such forwards are an
    #: artefact of exact interpolation between nearly coincident maturities, not
    #: information, and they make every forward-starting valuation meaningless.
    forward_tolerance_percent: float = 2.0


@dataclass
class HoldoutSplit:
    train: list[Instrument]
    holdout: list[Instrument]
    blocks: list[list[int]]
    holdout_blocks: list[int]
    block_maturities: list[tuple[float, float]]
    method: str
    notes: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return bool(self.holdout) and len(self.train) >= 4


def maturity_blocks(
    instruments: list[Instrument], config: HoldoutConfig | None = None
) -> list[list[int]]:
    """Contiguous maturity blocks; near-duplicate instruments stay together."""
    config = config or HoldoutConfig()
    order = sorted(
        range(len(instruments)),
        key=lambda k: (instruments[k].maturity_years, instruments[k].instrument_id),
    )
    blocks: list[list[int]] = []
    previous: float | None = None
    for idx in order:
        maturity = instruments[idx].maturity_years
        threshold = max(config.block_abs_gap_years, config.block_rel_gap * maturity)
        if previous is None or maturity - previous > threshold:
            blocks.append([idx])
        else:
            blocks[-1].append(idx)
        previous = maturity
    return blocks


def build_split(
    instruments: list[Instrument], config: HoldoutConfig | None = None
) -> HoldoutSplit:
    """Deterministic maturity-blocked train / holdout split."""
    config = config or HoldoutConfig()
    blocks = maturity_blocks(instruments, config)
    ranges = [
        (
            float(min(instruments[i].maturity_years for i in block)),
            float(max(instruments[i].maturity_years for i in block)),
        )
        for block in blocks
    ]
    notes: list[str] = []
    n_blocks = len(blocks)
    if n_blocks < 3:
        return HoldoutSplit(
            train=list(instruments),
            holdout=[],
            blocks=blocks,
            holdout_blocks=[],
            block_maturities=ranges,
            method="none",
            notes=[
                f"only {n_blocks} maturity block(s); a blocked holdout would leave "
                "no interior region to validate on"
            ],
        )

    interior = list(range(1, n_blocks - 1))
    if n_blocks < config.min_blocks:
        selected = [interior[len(interior) // 2]]
        notes.append(
            f"only {n_blocks} maturity blocks; a single interior block was held out"
        )
    else:
        offset = min(config.stride // 2, len(interior) - 1)
        selected = interior[offset :: config.stride]
    hold = {i for block_index in selected for i in blocks[block_index]}
    train = [inst for k, inst in enumerate(instruments) if k not in hold]
    holdout = [inst for k, inst in enumerate(instruments) if k in hold]
    if len(train) < 4 or not holdout:
        return HoldoutSplit(
            train=list(instruments),
            holdout=[],
            blocks=blocks,
            holdout_blocks=[],
            block_maturities=ranges,
            method="none",
            notes=notes + ["too few instruments to hold any block out"],
        )
    method = (
        f"maturity-blocked interpolation holdout: {len(blocks)} blocks formed with a "
        f"max(gap {config.block_abs_gap_years:g}Y, {config.block_rel_gap:.0%} of "
        f"maturity) rule, every {config.stride}th interior block withheld"
    )
    return HoldoutSplit(
        train=train,
        holdout=holdout,
        blocks=blocks,
        holdout_blocks=sorted(selected),
        block_maturities=ranges,
        method=method,
        notes=notes,
    )


@dataclass
class ModelComparison:
    split: HoldoutSplit
    baseline_train: BaselineFit | None
    advanced_train: AdvancedFit | None
    baseline_full: BaselineFit
    advanced_full: AdvancedFit
    metrics: dict
    selected: str
    rationale: str

    @property
    def selected_curve(self):
        fit = self.advanced_full if self.selected == "advanced" else self.baseline_full
        return fit.curve


def forward_admissibility(
    curve,
    instruments: list[Instrument],
    horizon: float,
    tolerance_percent: float = 2.0,
) -> dict:
    """Check that the instantaneous forward curve stays economically plausible.

    Quoted rates bound the level of the curve; instantaneous forwards may sit
    outside that range (they are local, not average, rates), but only by so much.
    A forward several hundred basis points beyond every quote in the file is the
    signature of an exact bootstrap solving two nearly coincident pillars, and a
    curve carrying one cannot be used to price a forward-starting trade or to
    produce a stable key-rate profile.
    """
    grid = np.linspace(max(horizon, 1.0) / 720.0, max(horizon, 1.0), 1441)
    forwards = np.asarray(curve.forward(grid), dtype=float) * 100.0
    rates = [i.quote for i in instruments if i.is_rate_quote]
    if rates:
        lo_quote, hi_quote = float(min(rates)), float(max(rates))
    else:
        zeros = np.asarray(curve.zero(grid), dtype=float) * 100.0
        lo_quote, hi_quote = float(np.min(zeros)), float(np.max(zeros))
    lower = lo_quote - tolerance_percent
    upper = hi_quote + tolerance_percent
    lo_f, hi_f = float(np.min(forwards)), float(np.max(forwards))
    return {
        "min_forward_percent": lo_f,
        "max_forward_percent": hi_f,
        "lower_bound_percent": lower,
        "upper_bound_percent": upper,
        "quoted_rate_range_percent": [lo_quote, hi_quote],
        "breach_percent": float(max(lower - lo_f, hi_f - upper, 0.0)),
        "admissible": bool(lo_f >= lower and hi_f <= upper),
    }


def _forward_roughness(curve, horizon: float) -> float:
    """Mean squared second difference of the forward curve on a dense grid."""
    grid = np.linspace(max(horizon, 1.0) / 360.0, max(horizon, 1.0), 721)
    forwards = np.asarray(curve.forward(grid), dtype=float)
    step = float(grid[1] - grid[0])
    second = np.diff(forwards, 2) / step**2
    return float(np.mean(second**2))


def compare_models(
    instruments: list[Instrument],
    fit_config: FitConfig | None = None,
    config: HoldoutConfig | None = None,
) -> ModelComparison:
    """Fit both estimators on the training split, score them, and select one."""
    fit_config = fit_config or FitConfig()
    config = config or HoldoutConfig()
    split = build_split(instruments, config)

    baseline_train: BaselineFit | None = None
    advanced_train: AdvancedFit | None = None
    holdout_metrics: dict[str, dict[str, float]] = {}
    train_metrics: dict[str, dict[str, float]] = {}
    if split.usable:
        baseline_train = fit_baseline(split.train, fit_config)
        advanced_train = fit_advanced(split.train, fit_config)
        train_metrics = {
            "baseline": fit_metrics(baseline_train.curve, split.train),
            "advanced": fit_metrics(advanced_train.curve, split.train),
        }
        holdout_metrics = {
            "baseline": fit_metrics(baseline_train.curve, split.holdout),
            "advanced": fit_metrics(advanced_train.curve, split.holdout),
        }

    baseline_full = fit_baseline(instruments, fit_config)
    advanced_full = fit_advanced(instruments, fit_config)
    horizon = float(max(i.maturity_years for i in instruments))

    admissibility = {
        "baseline": forward_admissibility(
            baseline_full.curve, instruments, horizon, config.forward_tolerance_percent
        ),
        "advanced": forward_admissibility(
            advanced_full.curve, instruments, horizon, config.forward_tolerance_percent
        ),
    }

    # Selection rule, fixed before any number was looked at:
    #   1. a model whose forward curve fails the admissibility gate is not usable
    #      in production, whatever it does to the repricing statistics;
    #   2. among admissible models the lower maturity-blocked holdout weighted
    #      RMSE wins, and the advanced model must beat the baseline by the
    #      parsimony margin before its extra complexity is accepted.
    base_ok = admissibility["baseline"]["admissible"]
    adv_ok = admissibility["advanced"]["admissible"]
    base_score = holdout_metrics.get("baseline", {}).get("weighted_rmse_bp", float("nan"))
    adv_score = holdout_metrics.get("advanced", {}).get("weighted_rmse_bp", float("nan"))
    accuracy_note = (
        f"holdout weighted RMSE: bootstrap {base_score:.2f}bp, penalised spline "
        f"{adv_score:.2f}bp"
        if holdout_metrics
        else "no maturity-blocked holdout could be formed from this data set"
    )

    if base_ok and not adv_ok:
        selected = "baseline"
        rationale = (
            "the penalised spline's instantaneous forward curve breaches the "
            f"admissibility band by {admissibility['advanced']['breach_percent']:.2f} "
            f"percentage points, so the bootstrap is retained ({accuracy_note})"
        )
    elif adv_ok and not base_ok:
        selected = "advanced"
        rationale = (
            "the bootstrap reprices its pillars exactly but its instantaneous forward "
            f"curve runs from {admissibility['baseline']['min_forward_percent']:.2f}% "
            f"to {admissibility['baseline']['max_forward_percent']:.2f}% against a "
            f"quoted range of "
            f"{admissibility['baseline']['quoted_rate_range_percent'][0]:.2f}%-"
            f"{admissibility['baseline']['quoted_rate_range_percent'][1]:.2f}%, breaching "
            f"the admissibility band by "
            f"{admissibility['baseline']['breach_percent']:.2f} percentage points; that "
            "is exact interpolation of quote noise between nearly coincident pillars, "
            "not information, and it makes forward-starting valuation and key-rate risk "
            "unusable. The penalised spline is admissible, so it is selected "
            f"({accuracy_note})"
        )
    elif holdout_metrics and np.isfinite(base_score) and base_score > 0:
        improvement = (base_score - adv_score) / base_score
        if np.isfinite(adv_score) and improvement > config.selection_margin:
            selected = "advanced"
            rationale = (
                f"both curves are admissible; the penalised robust spline cuts the "
                f"maturity-blocked holdout weighted RMSE from {base_score:.2f}bp to "
                f"{adv_score:.2f}bp ({improvement:.1%} better), beyond the "
                f"{config.selection_margin:.0%} margin required to justify the extra "
                "complexity"
            )
        else:
            selected = "baseline"
            rationale = (
                "both curves are admissible and the penalised spline does not beat the "
                f"bootstrap by more than the {config.selection_margin:.0%} margin on "
                f"the maturity-blocked holdout ({adv_score:.2f}bp versus "
                f"{base_score:.2f}bp), so the simpler, fully transparent estimator is "
                "retained"
            )
    else:
        selected = "advanced" if adv_ok else "baseline"
        rationale = (
            "no maturity-blocked holdout could be formed from this data set; the "
            f"selection falls back to the forward-curve admissibility gate ({selected} "
            "is admissible)"
        )

    metrics = {
        "train": train_metrics,
        "holdout": holdout_metrics,
        "full_sample": {
            "baseline": fit_metrics(baseline_full.curve, instruments),
            "advanced": fit_metrics(advanced_full.curve, instruments),
        },
        "forward_roughness": {
            "baseline": _forward_roughness(baseline_full.curve, horizon),
            "advanced": _forward_roughness(advanced_full.curve, horizon),
        },
        "forward_admissibility": admissibility,
    }
    return ModelComparison(
        split=split,
        baseline_train=baseline_train,
        advanced_train=advanced_train,
        baseline_full=baseline_full,
        advanced_full=advanced_full,
        metrics=metrics,
        selected=selected,
        rationale=rationale,
    )
