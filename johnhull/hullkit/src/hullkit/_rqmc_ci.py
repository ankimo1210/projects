"""Private RB-F08 Student uncertainty across independent Sobol scrambles.

The statistical sample is the set of complete scramble estimates. The resulting
Student interval is approximate for a general integrand and does not bound
time-discretization error or guarantee finite-sample coverage.
"""

from __future__ import annotations

import math
from copy import deepcopy
from numbers import Integral
from time import perf_counter
from typing import TYPE_CHECKING

import numpy as np
import scipy
from scipy.stats import t

from . import _numerical_mc as numerical

if TYPE_CHECKING:
    from ._multilevel_mc import GBMCall


def _integer(value, lower, upper, name):
    if isinstance(value, bool) or not isinstance(value, Integral) or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer in [{lower}, {upper}]")
    return int(value)


def student_summary(estimates: np.ndarray, *, confidence: float = 0.95) -> dict:
    """Summarize independent scramble estimates with an approximate t interval.

    All observations must be finite, with at least two independent scrambles.
    Identical estimates give a degenerate interval with no meaningful degrees
    of freedom; they provide no general coverage guarantee.
    """
    values = np.asarray(estimates, dtype=float)
    if values.ndim != 1 or values.size < 2 or np.any(~np.isfinite(values)):
        raise ValueError("at least two finite one-dimensional scramble estimates required")
    if not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("finite confidence strictly between zero and one required")
    identical = bool(np.all(values == values[0]))
    price = float(values[0]) if identical else float(values.mean())
    standard_error = 0.0 if identical else float(values.std(ddof=1) / math.sqrt(values.size))
    if not math.isfinite(price) or not math.isfinite(standard_error):
        raise ValueError("nonfinite scramble summary")
    degenerate = standard_error == 0
    degrees = None if degenerate else int(values.size - 1)
    half_width = 0.0 if degenerate else float(t.ppf((1 + confidence) / 2, degrees)) * standard_error
    interval = [price - half_width, price + half_width]
    if not all(math.isfinite(value) for value in interval):
        raise ValueError("nonfinite confidence interval")
    return {
        "price": price,
        "estimates": values.copy(),
        "scrambles": int(values.size),
        "standard_error": standard_error,
        "df": degrees,
        "confidence_level": float(confidence),
        "interval": interval,
        "width": 2 * half_width,
        "degenerate": degenerate,
        "approximate": True,
    }


def rqmc_gbm_call_from_seeds(
    contract: GBMCall,
    *,
    power: int,
    child_seeds: list[int],
    child_metadata: list[dict] | None = None,
) -> dict:
    """Replay a GBM call with already frozen, distinct uint32 scramble seeds.

    No child seeds are spawned, retried, or replaced here. Each complete Sobol
    scramble is one observation for the Student interval. The inverse-normal
    endpoint clip matches the existing private sampler, and endpoint counts
    retain every point including Sobol point zero.
    """
    wall_start = perf_counter()
    rng_s = engine_s = summary_s = 0.0
    power = _integer(power, 0, 20, "power")
    seeds = [_integer(seed, 0, 2**32 - 1, "child seed") for seed in child_seeds]
    _integer(len(seeds), 2, 1024, "scrambles")
    if len(set(seeds)) != len(seeds):
        raise ValueError("distinct child seeds required")
    metadata = None if child_metadata is None else deepcopy(list(child_metadata))
    if metadata is not None:
        if len(metadata) != len(seeds) or any(
            not isinstance(row, dict) or row.get("seed") != seed
            for row, seed in zip(metadata, seeds, strict=False)
        ):
            raise ValueError("one matching metadata seed per scramble required")

    clip = [float(np.nextafter(0.0, 1.0)), float(np.nextafter(1.0, 0.0))]
    estimates, clipped_counts, zero_counts, one_counts = [], [], [], []
    for seed in seeds:
        phase_start = perf_counter()
        points = numerical.sobol_normal_points(power, scramble=True, seed=seed)
        rng_s += perf_counter() - phase_start
        phase_start = perf_counter()
        uniforms = points["uniforms"]
        clipped_counts.append(int(np.count_nonzero((uniforms < clip[0]) | (uniforms > clip[1]))))
        zero_counts.append(int(np.count_nonzero(uniforms == 0)))
        one_counts.append(int(np.count_nonzero(uniforms == 1)))
        summary_s += perf_counter() - phase_start
        phase_start = perf_counter()
        terminal = numerical.gbm_paths_from_normals(
            contract.spot,
            contract.rate,
            contract.sigma,
            contract.maturity,
            points["normals"],
            yield_rate=contract.yield_rate,
            scheme="exact",
        )[:, -1]
        estimates.append(
            float(
                math.exp(-contract.rate * contract.maturity)
                * np.maximum(terminal - contract.strike, 0).mean()
            )
        )
        engine_s += perf_counter() - phase_start
    phase_start = perf_counter()
    summary = student_summary(np.asarray(estimates))
    result = {
        **summary,
        "child_seeds": seeds,
        "child_metadata": metadata,
        "child_spawn_keys": (
            [None] * len(seeds)
            if metadata is None
            else [deepcopy(row.get("spawn_key")) for row in metadata]
        ),
        "points_per_scramble": 2**power,
        "payoff_evaluations": len(seeds) * 2**power,
        "uniform_clip": clip,
        "uniform_clip_hex": [value.hex() for value in clip],
        "clipped_points": sum(clipped_counts),
        "clipped_points_by_scramble": clipped_counts,
        "uniform_zero_points": sum(zero_counts),
        "uniform_zero_points_by_scramble": zero_counts,
        "uniform_one_points": sum(one_counts),
        "uniform_one_points_by_scramble": one_counts,
        "normal_dimensions": 1,
        "scipy_version": scipy.__version__,
    }
    summary_s += perf_counter() - phase_start
    wall_s = perf_counter() - wall_start
    result["timing"] = {
        "rng_s": rng_s,
        "engine_s": engine_s,
        "summary_s": summary_s,
        "overhead_s": max(0.0, wall_s - rng_s - engine_s - summary_s),
        "wall_s": wall_s,
    }
    return result


def rqmc_gbm_call(contract: GBMCall, *, power: int, scrambles: int, seed: int) -> dict:
    """Legacy-compatible RQMC point estimates with a Student scramble interval.

    The seed children match the existing private randomized_qmc_price wrapper.
    Research orchestration uses rqmc_gbm_call_from_seeds to consume its frozen
    seed ledger directly.
    """
    power = _integer(power, 0, 20, "power")
    scrambles = _integer(scrambles, 2, 1024, "scrambles")
    seed = _integer(seed, 0, 2**32 - 1, "seed")
    children = np.random.SeedSequence(seed).spawn(scrambles)
    seeds = [int(child.generate_state(1)[0]) for child in children]
    metadata = [
        {
            "seed": child_seed,
            "raw_seed": child_seed,
            "retry_count": 0,
            "candidate_seeds": [child_seed],
            "entropy": seed,
            "spawn_key": list(child.spawn_key),
        }
        for child, child_seed in zip(children, seeds, strict=True)
    ]
    return rqmc_gbm_call_from_seeds(
        contract, power=power, child_seeds=seeds, child_metadata=metadata
    )
