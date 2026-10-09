"""Fixed RB-F08 Euler pilot, cost calibration and saved-observation checks.

This module generates pilot randomness from an already resolved candidate
ledger. Main prices never enter its level selection or path allocation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import platform
import sys
from copy import deepcopy
from functools import cache
from itertools import pairwise
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _multilevel_mc as mlmc
from scipy.stats import norm, t

HERE = Path(__file__).resolve().parent
JOHNHULL = HERE.parents[1]
METHODS = ["mlmc", "plain_euler", "exact_plain", "exact_cv"]
ESTIMATORS = ("fine", "coarse", "difference", "bias", "exact")


@cache
def module(name):
    """Load one adjacent research module without changing import search paths."""
    path = HERE / (name + ".py")
    spec = importlib.util.spec_from_file_location("rbf08_pilot_" + name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def _current_source():
    protocol = module("protocol")
    return protocol.source_fingerprint([JOHNHULL / name for name in protocol.SOURCE_FILES])


def cost_counts(*, level: int, base_steps: int, paths: int) -> dict:
    """Count Euler estimator operations without double counting coupled normals."""
    for value, minimum in ((level, 0), (base_steps, 1), (paths, 1)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
            raise ValueError("nonnegative level and positive integer steps/paths required")
    steps = int(base_steps) * 2 ** int(level)
    coarse = steps // 2 if level else 0
    return {
        "stock_updates": (steps + coarse) * int(paths),
        "normal_draws": steps * int(paths),
        "payoff_evaluations": (1 + bool(level)) * int(paths),
        "coarse_aggregations": coarse * int(paths),
    }


def _moment_summary(moment):
    count, mean, m2 = int(moment["count"]), float(moment["mean"]), float(moment["m2"])
    if count < 2 or not all(math.isfinite(x) for x in (mean, m2)) or m2 < 0:
        raise ValueError("at least two finite observations with nonnegative centered M2 required")
    variance = m2 / (count - 1)
    return {**moment, "variance": variance, "standard_error": math.sqrt(variance / count)}


def _pair_moments(first, second):
    first, second = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if first.shape != second.shape or first.ndim != 1:
        raise ValueError("matching one-dimensional paired observations required")
    left, right = mlmc.block_moments(first), mlmc.block_moments(second)
    return {
        "first": left,
        "second": right,
        "c2": float(np.dot(first - left["mean"], second - right["mean"])),
    }


def _merge_pair_moments(blocks):
    if not blocks:
        raise ValueError("paired moment blocks required")
    first = mlmc.merge_moments([block["first"] for block in blocks])
    second = mlmc.merge_moments([block["second"] for block in blocks])
    count = int(blocks[0]["first"]["count"])
    mean_a, mean_b = blocks[0]["first"]["mean"], blocks[0]["second"]["mean"]
    cross = float(blocks[0]["c2"])
    for block in blocks[1:]:
        n = int(block["first"]["count"])
        if n != int(block["second"]["count"]):
            raise ValueError("paired block denominators differ")
        total = count + n
        delta_a = block["first"]["mean"] - mean_a
        delta_b = block["second"]["mean"] - mean_b
        cross = math.fsum((cross, block["c2"], delta_a * delta_b * count * n / total))
        mean_a += delta_a * n / total
        mean_b += delta_b * n / total
        count = total
    if first["count"] != second["count"] or not math.isfinite(cross):
        raise ValueError("nonfinite or mismatched paired moments")
    a, b = _moment_summary(first), _moment_summary(second)
    covariance = cross / (count - 1)
    if abs(covariance) > math.sqrt(a["variance"] * b["variance"]) + 1e-9:
        raise ValueError("covariance exceeds the Cauchy bound")
    return {"first": a, "second": b, "c2": cross, "covariance": covariance}


def _block_sizes(paths, block_size):
    if paths < 2 or block_size < 2:
        raise ValueError("at least two pilot paths and block_size >= 2 required")
    sizes = [block_size] * (paths // block_size)
    if paths % block_size:
        sizes.append(paths % block_size)
    if sizes[-1] == 1:
        remainder = sizes.pop()
        sizes[-1] += remainder
    return sizes


def _seed(protocol, phase, *, method=None, level=None, run=None):
    candidates = [
        row
        for row in module("protocol").seed_roster(protocol, phase)
        if (method is None or row["method"] == method)
        and (level is None or row["level"] == level)
        and (run is None or row["run"] == run)
    ]
    if len(candidates) != 1:
        raise ValueError("exactly one frozen logical pilot seed slot required")
    return candidates[0]["seed"]


def _as_columns(rows, prefix):
    if not rows:
        raise ValueError("nonempty pilot table required")
    result = {}
    for key in rows[0]:
        values = [row[key] for row in rows]
        kind = (
            bool
            if isinstance(values[0], bool)
            else (np.uint32 if key == "seed" else np.int64 if isinstance(values[0], int) else float)
        )
        result[prefix + "." + key] = np.asarray(values, dtype=kind)
    return result


def _euler_observation(contract, normals, *, level, base_steps):
    start = perf_counter()
    result = mlmc.gbm_level_samples(contract, normals, level=level, base_steps=base_steps)
    engine_s = perf_counter() - start
    start = perf_counter()
    fine = result["fine_payoffs"]
    coarse = result["coarse_payoffs"]
    exact = fine - result["paired_exact_bias"]
    row = {"count": len(fine)}
    for name, samples in (
        ("fine", fine),
        ("coarse", np.zeros_like(fine) if coarse is None else coarse),
        ("difference", result["differences"]),
        ("bias", result["paired_exact_bias"]),
        ("exact", exact),
    ):
        moment = mlmc.block_moments(samples)
        row[name + ".mean"], row[name + ".m2"] = moment["mean"], moment["m2"]
    row["fine_coarse_c2"] = 0.0 if coarse is None else _pair_moments(fine, coarse)["c2"]
    row["fine_exact_c2"] = _pair_moments(fine, exact)["c2"]
    for name in ("fine_negative_states", "coarse_negative_states", "negative_paths"):
        row[name] = result[name]
    row.update({"cost." + key: value for key, value in result["cost_counts"].items()})
    row.update(
        {"diagnostic_cost." + key: value for key, value in result["diagnostic_cost_counts"].items()}
    )
    row["engine_s"] = engine_s
    row["summary_s"] = perf_counter() - start
    return row


def _collect_euler(p, actual):
    contract = mlmc.GBMCall(**p["parameters"])
    rows = []
    for level in actual["levels"]:
        for stream in range(actual["streams"]):
            seed = _seed(p, "pilot", method="mlmc", level=level, run=stream)
            rng = np.random.default_rng(seed)
            for index, count in enumerate(_block_sizes(actual["paths"], p["block_size"])):
                start = perf_counter()
                normals = rng.standard_normal((count, p["base_steps"] * 2**level))
                rng_s = perf_counter() - start
                observation = _euler_observation(
                    contract, normals, level=level, base_steps=p["base_steps"]
                )
                rows.append(
                    {
                        "level": level,
                        "stream": stream,
                        "block": index,
                        "seed": seed,
                        **observation,
                        "rng_s": rng_s,
                    }
                )
    return _as_columns(rows, "euler")


def _exact_observation(contract, normals):
    start = perf_counter()
    with np.errstate(over="raise", invalid="raise"):
        try:
            terminal = contract.spot * np.exp(
                (contract.rate - contract.yield_rate - 0.5 * contract.sigma**2) * contract.maturity
                + contract.sigma * math.sqrt(contract.maturity) * normals
            )
            control = math.exp(-contract.rate * contract.maturity) * terminal
            payoff = math.exp(-contract.rate * contract.maturity) * np.maximum(
                terminal - contract.strike, 0
            )
            if not np.all(np.isfinite(payoff)) or not np.all(np.isfinite(control)):
                raise ValueError("nonfinite exact pilot observation")
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("nonfinite exact pilot observation") from exc
    engine_s = perf_counter() - start
    start = perf_counter()
    pair = _pair_moments(payoff, control)
    return {
        "count": len(normals),
        "payoff.mean": pair["first"]["mean"],
        "payoff.m2": pair["first"]["m2"],
        "control.mean": pair["second"]["mean"],
        "control.m2": pair["second"]["m2"],
        "payoff_control_c2": pair["c2"],
        "engine_s": engine_s,
        "summary_s": perf_counter() - start,
        "cost.stock_updates": len(normals),
        "cost.normal_draws": len(normals),
        "cost.payoff_evaluations": len(normals),
        "diagnostic_cost.control_evaluations": len(normals),
    }


def _collect_exact(p, actual):
    contract, rows = mlmc.GBMCall(**p["parameters"]), []
    for stream in range(actual["streams"]):
        seed = _seed(p, "pilot", method="exact_cv", run=stream)
        rng = np.random.default_rng(seed)
        for index, count in enumerate(_block_sizes(actual["exact_paths"], p["block_size"])):
            start = perf_counter()
            normals = rng.standard_normal(count)
            rng_s = perf_counter() - start
            rows.append(
                {
                    "stream": stream,
                    "block": index,
                    "seed": seed,
                    **_exact_observation(contract, normals),
                    "rng_s": rng_s,
                }
            )
    return _as_columns(rows, "exact")


def _calibrate(p, actual):
    contract, rows = mlmc.GBMCall(**p["parameters"]), []
    warmups = p["timing"]["warmup_repetitions"]
    repeats = warmups + p["timing"]["measured_repetitions"]
    for level in actual["levels"]:
        for repetition in range(repeats):
            seed = _seed(p, "timing", level=level, run=repetition)
            start = perf_counter()
            normals = np.random.default_rng(seed).standard_normal(
                (actual["timing_paths"], p["base_steps"] * 2**level)
            )
            rng_s = perf_counter() - start
            row = _euler_observation(contract, normals, level=level, base_steps=p["base_steps"])
            rows.append(
                {
                    "level": level,
                    "repeat": repetition,
                    "seed": seed,
                    "warmup": repetition < warmups,
                    "count": actual["timing_paths"],
                    "rng_s": rng_s,
                    "engine_s": row["engine_s"],
                    "summary_s": row["summary_s"],
                    "total_s": rng_s + row["engine_s"] + row["summary_s"],
                    **{
                        name: value
                        for name, value in row.items()
                        if name.startswith(("cost.", "diagnostic_cost."))
                    },
                }
            )
    return _as_columns(rows, "calibration")


def _clip_from_uniforms(p, uniforms, *, elapsed_s=0.0):
    uniforms = np.asarray(uniforms, dtype=float)
    power = p["clip_diagnostic"]["power"]
    if (
        uniforms.shape != (2**power,)
        or np.any(~np.isfinite(uniforms))
        or np.any(uniforms < 0)
        or np.any(uniforms > 1)
    ):
        raise ValueError("finite full Sobol unit-interval sequence required")
    private = [p["rqmc"]["clip"]["lower"], p["rqmc"]["clip"]["upper"]]
    public = p["clip_diagnostic"]["public_clip"]
    clips, strikes = [private, public], p["rqmc"]["strikes"]
    payoffs, truths = [], []
    parameters = p["parameters"]
    reference = module("reference_methods")
    for strike in strikes:
        row, target = [], []
        for lower, upper in clips:
            z = norm.ppf(np.clip(uniforms, lower, upper))
            terminal = parameters["spot"] * np.exp(
                (parameters["rate"] - parameters["yield_rate"] - 0.5 * parameters["sigma"] ** 2)
                * parameters["maturity"]
                + parameters["sigma"] * math.sqrt(parameters["maturity"]) * z
            )
            row.append(
                math.exp(-parameters["rate"] * parameters["maturity"])
                * np.maximum(terminal - strike, 0)
            )
            target.append(
                reference.clipped_black_call({**parameters, "strike": strike}, (lower, upper))
            )
        payoffs.append(row)
        truths.append(target)
    return {
        "clip.uniforms": uniforms.copy(),
        "clip.seed": np.array([_seed(p, "pilot", method="clip_diagnostic")], dtype=np.uint32),
        "clip.power": np.array([power], dtype=np.int64),
        "clip.strikes": np.asarray(strikes),
        "clip.private_clip": np.asarray(private),
        "clip.public_clip": np.asarray(public),
        "clip.payoffs": np.asarray(payoffs),
        "clip.truths": np.asarray(truths),
        "clip.bsm_truth": np.array(
            [reference.black_call({**parameters, "strike": strike}) for strike in strikes]
        ),
        "clip.endpoint_counts": np.array(
            [np.count_nonzero(uniforms == 0), np.count_nonzero(uniforms == 1)], dtype=np.int64
        ),
        "clip.clipped_points": np.array(
            [np.count_nonzero((uniforms < lower) | (uniforms > upper)) for lower, upper in clips],
            dtype=np.int64,
        ),
        "clip.elapsed_s": np.array([elapsed_s]),
    }


def _collect_clip(p):
    from hullkit import _numerical_mc as numerical

    started = perf_counter()
    seed = _seed(p, "pilot", method="clip_diagnostic")
    uniforms = numerical.sobol_normal_points(
        p["clip_diagnostic"]["power"], scramble=True, seed=seed
    )["uniforms"][:, 0]
    result = _clip_from_uniforms(p, uniforms)
    result["clip.elapsed_s"][0] = perf_counter() - started
    return result


def _clip_summary(arrays, p):
    expected = _clip_from_uniforms(
        p, arrays["clip.uniforms"], elapsed_s=float(arrays["clip.elapsed_s"][0])
    )
    for name, value in expected.items():
        if name == "clip.elapsed_s":
            if not np.isfinite(value).all() or np.any(value < 0):
                raise ValueError("nonnegative finite clip diagnostic seconds required")
        elif value.dtype.kind in "iub":
            if not np.array_equal(arrays[name], value):
                raise ValueError("clip diagnostic integer metadata mismatch")
        else:
            _close(arrays[name], value, "clip diagnostic " + name)
    estimates = arrays["clip.payoffs"].mean(axis=2)
    return {
        "seed": int(arrays["clip.seed"][0]),
        "power": int(arrays["clip.power"][0]),
        "points": len(arrays["clip.uniforms"]),
        "paired_comparison": True,
        "used_in_mlmc": False,
        "private_clip": arrays["clip.private_clip"].tolist(),
        "public_clip": arrays["clip.public_clip"].tolist(),
        "endpoint_counts": arrays["clip.endpoint_counts"].tolist(),
        "clipped_points": arrays["clip.clipped_points"].tolist(),
        "cases": [
            {
                "strike": float(strike),
                "private_estimate": float(estimates[i, 0]),
                "public_estimate": float(estimates[i, 1]),
                "sample_difference": float(estimates[i, 1] - estimates[i, 0]),
                "private_truth": float(arrays["clip.truths"][i, 0]),
                "public_truth": float(arrays["clip.truths"][i, 1]),
                "analytic_difference": float(
                    arrays["clip.truths"][i, 1] - arrays["clip.truths"][i, 0]
                ),
                "bsm_truth": float(arrays["clip.bsm_truth"][i]),
            }
            for i, strike in enumerate(arrays["clip.strikes"])
        ],
    }


def _validate_allocation_expenses(arrays, p):
    roster = [
        ("allocation.euler_summary", ["mlmc", "plain_euler"], p["epsilon"]),
        ("allocation.exact_summary", ["exact_plain", "exact_cv"], p["epsilon"]),
    ]
    for epsilon in p["epsilon"]:
        roster.extend(
            [
                (f"allocation.select.{epsilon}", ["mlmc", "plain_euler"], [epsilon]),
                (f"allocation.exact_plain.{epsilon}", ["exact_plain"], [epsilon]),
                (f"allocation.exact_cv.{epsilon}", ["exact_cv"], [epsilon]),
                (f"allocation.euler_counts.{epsilon}", ["mlmc", "plain_euler"], [epsilon]),
            ]
        )
    if arrays["allocation.expense_id"].tolist() != [row[0] for row in roster]:
        raise ValueError("fixed allocation expense registry differs")
    if arrays["allocation.methods"].tolist() != ["|".join(row[1]) for row in roster]:
        raise ValueError("allocation method applicability differs from actual calculation")
    expected_epsilon = [row[2][0] if len(row[2]) == 1 else -1.0 for row in roster]
    _close(arrays["allocation.epsilon"], expected_epsilon, "allocation budget applicability")
    seconds = arrays["allocation.seconds"]
    if seconds.shape != (len(roster),) or np.any(~np.isfinite(seconds)) or np.any(seconds < 0):
        raise ValueError("finite nonnegative allocation expense seconds required")


def _moments_at(arrays, prefix, name, indices):
    return [
        {
            "count": int(arrays[prefix + ".count"][i]),
            "mean": float(arrays[prefix + "." + name + ".mean"][i]),
            "m2": float(arrays[prefix + "." + name + ".m2"][i]),
        }
        for i in indices
    ]


def _paired_at(arrays, prefix, first, second, cross_name, indices):
    left, right = (
        _moments_at(arrays, prefix, first, indices),
        _moments_at(arrays, prefix, second, indices),
    )
    return _merge_pair_moments(
        [
            {"first": a, "second": b, "c2": float(arrays[prefix + "." + cross_name][i])}
            for a, b, i in zip(left, right, indices, strict=True)
        ]
    )


def _close(actual, expected, name):
    try:
        np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-10)
    except AssertionError as exc:
        raise ValueError("pilot numerical mismatch: " + name) from exc


def _level_summaries(arrays, p):
    summaries = []
    for level in sorted(set(map(int, arrays["euler.level"]))):
        indices = np.flatnonzero(arrays["euler.level"] == level)
        moments = {
            name: _moment_summary(mlmc.merge_moments(_moments_at(arrays, "euler", name, indices)))
            for name in ESTIMATORS
        }
        fine_coarse = _paired_at(arrays, "euler", "fine", "coarse", "fine_coarse_c2", indices)
        fine_exact = _paired_at(arrays, "euler", "fine", "exact", "fine_exact_c2", indices)
        _close(
            moments["difference"]["mean"],
            moments["fine"]["mean"] - moments["coarse"]["mean"],
            "difference mean",
        )
        _close(
            moments["bias"]["mean"],
            moments["fine"]["mean"] - moments["exact"]["mean"],
            "paired bias mean",
        )
        _close(
            moments["difference"]["variance"],
            moments["fine"]["variance"]
            + moments["coarse"]["variance"]
            - 2 * fine_coarse["covariance"],
            "coupled variance",
        )
        _close(
            moments["bias"]["variance"],
            moments["fine"]["variance"]
            + moments["exact"]["variance"]
            - 2 * fine_exact["covariance"],
            "paired bias variance",
        )
        count = moments["fine"]["count"]
        steps = p["base_steps"] * 2**level
        fine_negative = int(arrays["euler.fine_negative_states"][indices].sum())
        coarse_negative = int(arrays["euler.coarse_negative_states"][indices].sum())
        negative_paths = int(arrays["euler.negative_paths"][indices].sum())
        coarse_steps = steps // 2 if level else 0
        if (
            not 0 <= negative_paths <= count
            or not 0 <= fine_negative <= count * steps
            or not 0 <= coarse_negative <= count * coarse_steps
        ):
            raise ValueError("negative counts exceed original denominators")
        bias = moments["bias"]
        half = (
            float(t.ppf((1 + p["pilot"]["bias_confidence"]) / 2, count - 1))
            * bias["standard_error"]
        )
        summaries.append(
            {
                "level": level,
                "steps": steps,
                "count": count,
                **moments,
                "fine_coarse_covariance": fine_coarse["covariance"],
                "fine_exact_covariance": fine_exact["covariance"],
                "coupled_variance": moments["difference"]["variance"],
                "uncoupled_variance": moments["fine"]["variance"] + moments["coarse"]["variance"],
                "fine_negative_states": fine_negative,
                "coarse_negative_states": coarse_negative,
                "negative_paths": negative_paths,
                "negative_path_rate": negative_paths / count,
                "fine_state_denominator": count * steps,
                "coarse_state_denominator": count * coarse_steps,
                "fine_negative_state_rate": fine_negative / (count * steps),
                "coarse_negative_state_rate": (
                    coarse_negative / (count * coarse_steps) if coarse_steps else 0.0
                ),
                "bias_half_width": half,
                "bias_bound": abs(bias["mean"]) + half,
            }
        )
    return summaries


def _exact_summary(arrays, p):
    indices = np.arange(len(arrays["exact.count"]))
    pair = _paired_at(arrays, "exact", "payoff", "control", "payoff_control_c2", indices)
    variance_control = pair["second"]["variance"]
    beta = pair["covariance"] / variance_control if variance_control else 0.0
    cv_variance = (
        pair["first"]["variance"] + beta**2 * variance_control - 2 * beta * pair["covariance"]
    )
    if cv_variance < -1e-9:
        raise ValueError("negative control-variate variance")
    return {
        "payoff": pair["first"],
        "control": pair["second"],
        "covariance": pair["covariance"],
        "cv_beta": beta,
        "cv_variance": max(0.0, cv_variance),
        "control_expectation": p["parameters"]["spot"]
        * math.exp(-p["parameters"]["yield_rate"] * p["parameters"]["maturity"]),
        "beta_fallback": variance_control == 0,
    }


def _calibration_summary(arrays):
    summaries = []
    for level in sorted(set(map(int, arrays["calibration.level"]))):
        mask = (arrays["calibration.level"] == level) & ~arrays["calibration.warmup"]
        seconds = arrays["calibration.total_s"][mask] / arrays["calibration.count"][mask]
        if seconds.size < 1 or np.any(~np.isfinite(seconds)) or np.any(seconds <= 0):
            raise ValueError("positive finite measured calibration seconds required")
        summaries.append(
            {
                "level": level,
                "measurements": int(seconds.size),
                "median_seconds_per_pair": float(np.median(seconds)),
                "p95_seconds_per_pair": float(np.quantile(seconds, 0.95)),
            }
        )
    return summaries


def _rates(levels, p):
    multiplier = p["pilot"]["alpha_signal_multiplier"]
    consecutive = p["pilot"]["alpha_consecutive_levels"]
    supported = [
        row
        for row in levels[1:]
        if abs(row["difference"]["mean"]) > multiplier * row["difference"]["standard_error"]
    ]
    windows = []
    for start in range(max(0, len(supported) - consecutive + 1)):
        window = supported[start : start + consecutive]
        if len(window) == consecutive and all(
            b["level"] == a["level"] + 1 for a, b in pairwise(window)
        ):
            windows.append(
                {
                    "levels": [row["level"] for row in window],
                    "alpha": -float(
                        np.polyfit(
                            [row["level"] for row in window],
                            np.log2([abs(row["difference"]["mean"]) for row in window]),
                            1,
                        )[0]
                    ),
                }
            )
    beta = [
        {
            "coarse": a["level"],
            "fine": b["level"],
            "beta": math.log2(a["difference"]["variance"] / b["difference"]["variance"]),
        }
        for a, b in pairwise(levels)
        if a["difference"]["variance"] > 0 and b["difference"]["variance"] > 0
    ]
    signs = [
        {
            "coarse": a["level"],
            "fine": b["level"],
            "sign_flip": a["difference"]["mean"] * b["difference"]["mean"] < 0,
        }
        for a, b in pairwise(levels[1:])
    ]
    return {
        "alpha_status": "supported" if windows else "unresolved",
        "alpha_windows": windows,
        "beta_adjacent": beta,
        "sign_changes": signs,
    }


def _cap_status(paths, updates, p):
    return (
        "budget_failure"
        if paths > p["caps"]["paths_per_run"] or updates > p["caps"]["steps_per_run"]
        else "ready"
    )


def choose_allocations(record: dict, arrays: dict, protocol: dict, *, _timings=None) -> list[dict]:
    """Select levels and counts only from fixed pilot moments and measured costs.

    Exact baselines retain their allocations even when an Euler cell has no
    acceptable grid. Finite-pilot bias envelopes and observed negative rates
    are diagnostics, not probability guarantees.
    """
    del record
    p = protocol
    started = perf_counter()
    levels, calibration = _level_summaries(arrays, p), _calibration_summary(arrays)
    if _timings is not None:
        _timings.append(
            {
                "expense_id": "allocation.euler_summary",
                "seconds": perf_counter() - started,
                "methods": ["mlmc", "plain_euler"],
                "epsilons": p["epsilon"],
            }
        )
    started = perf_counter()
    exact = _exact_summary(arrays, p)
    if _timings is not None:
        _timings.append(
            {
                "expense_id": "allocation.exact_summary",
                "seconds": perf_counter() - started,
                "methods": ["exact_plain", "exact_cv"],
                "epsilons": p["epsilon"],
            }
        )
    costs = {row["level"]: row["median_seconds_per_pair"] for row in calibration}
    minimum, floor = p["allocation"]["minimum_paths"], p["allocation"]["variance_floor"]
    allocations = []
    for epsilon in p["epsilon"]:
        target = epsilon**2 * p["allocation"]["sampling_variance_fraction"]
        bias_target = epsilon * math.sqrt(p["allocation"]["bias_fraction_sqrt"])
        started = perf_counter()
        candidates, selected = [], None
        for level in levels:
            if level["level"] < p["pilot"]["minimum_main_level"]:
                continue
            prefix = [row for row in levels if row["level"] <= level["level"]]
            negative_rate = max(row["negative_path_rate"] for row in prefix)
            valid_negative = negative_rate <= p["pilot"]["negative_path_rate_cap"]
            valid_bias = level["bias_bound"] <= bias_target
            candidates.append(
                {
                    "level": level["level"],
                    "bias_bound": level["bias_bound"],
                    "bias_target": bias_target,
                    "negative_path_rate": negative_rate,
                    "bias_pass": valid_bias,
                    "negative_pass": valid_negative,
                }
            )
            if selected is None and valid_bias and valid_negative:
                selected = level
        if _timings is not None:
            _timings.append(
                {
                    "expense_id": f"allocation.select.{epsilon}",
                    "seconds": perf_counter() - started,
                    "methods": ["mlmc", "plain_euler"],
                    "epsilons": [epsilon],
                }
            )
        started = perf_counter()
        exact_n = max(minimum, math.ceil(exact["payoff"]["variance"] / target))
        if _timings is not None:
            _timings.append(
                {
                    "expense_id": f"allocation.exact_plain.{epsilon}",
                    "seconds": perf_counter() - started,
                    "methods": ["exact_plain"],
                    "epsilons": [epsilon],
                }
            )
        started = perf_counter()
        cv_n = max(minimum, math.ceil(exact["cv_variance"] / target))
        if _timings is not None:
            _timings.append(
                {
                    "expense_id": f"allocation.exact_cv.{epsilon}",
                    "seconds": perf_counter() - started,
                    "methods": ["exact_cv"],
                    "epsilons": [epsilon],
                }
            )
        started = perf_counter()
        method_status = {
            "exact_plain": _cap_status(exact_n, exact_n, p),
            "exact_cv": _cap_status(cv_n, cv_n, p),
        }
        reason = None
        level_index, mlmc_counts, plain_n, bound = None, None, None, None
        counters, floor_levels, allocation_info = {}, [], None
        if selected is None:
            status = (
                "coarse_grid_invalid"
                if any(not row["negative_pass"] for row in candidates)
                else "bias_unresolved"
            )
            reason = (
                "observed negative path rate exceeds fixed cap"
                if status == "coarse_grid_invalid"
                else "no candidate level meets empirical paired bias target"
            )
            method_status.update(mlmc=status, plain_euler=status)
        else:
            level_index, bound = selected["level"], selected["bias_bound"]
            prefix = [row for row in levels if row["level"] <= level_index]
            variances = np.array([row["difference"]["variance"] for row in prefix])
            median_costs = np.array([costs[row["level"]] for row in prefix])
            mlmc_counts = mlmc.allocate_paths(
                variances,
                median_costs,
                sampling_variance=target,
                minimum=minimum,
                variance_floor=floor,
            ).tolist()
            floor_levels = [
                row["level"] for row, value in zip(prefix, variances, strict=True) if value < floor
            ]
            plain_n = max(minimum, math.ceil(selected["fine"]["variance"] / target))
            per_level = [
                cost_counts(level=row["level"], base_steps=p["base_steps"], paths=n)
                for row, n in zip(prefix, mlmc_counts, strict=True)
            ]
            counters = {key: sum(row[key] for row in per_level) for key in per_level[0]}
            method_status["mlmc"] = _cap_status(sum(mlmc_counts), counters["stock_updates"], p)
            method_status["plain_euler"] = _cap_status(plain_n, plain_n * selected["steps"], p)
            status = method_status["mlmc"]
            if status != "ready":
                reason = "fixed MLMC path or update cap exceeded"
            step_costs = np.array(
                [
                    cost_counts(level=row["level"], base_steps=p["base_steps"], paths=1)[
                        "stock_updates"
                    ]
                    for row in prefix
                ]
            )
            allocation_info = {
                "variances": variances.tolist(),
                "median_seconds_per_pair": median_costs.tolist(),
                "step_proxy_paths": mlmc.allocate_paths(
                    variances,
                    step_costs,
                    sampling_variance=target,
                    minimum=minimum,
                    variance_floor=floor,
                ).tolist(),
                "estimated_sampling_variance": float(np.sum(variances / mlmc_counts)),
            }
        if _timings is not None:
            _timings.append(
                {
                    "expense_id": f"allocation.euler_counts.{epsilon}",
                    "seconds": perf_counter() - started,
                    "methods": ["mlmc", "plain_euler"],
                    "epsilons": [epsilon],
                }
            )
        reasons = {
            method: (
                None
                if state == "ready"
                else (
                    reason
                    if method in ("mlmc", "plain_euler") and reason
                    else "fixed method budget cap exceeded"
                )
            )
            for method, state in method_status.items()
        }
        allocations.append(
            {
                "epsilon": epsilon,
                "status": status,
                "reason": reason,
                "level": level_index,
                "mlmc_paths": mlmc_counts,
                "plain_euler_paths": plain_n,
                "exact_plain_paths": exact_n,
                "exact_cv_paths": cv_n,
                "bias_bound": bound,
                "sampling_variance": target,
                "bias_target": bias_target,
                "method_status": {method: method_status[method] for method in METHODS},
                "method_reasons": reasons,
                "candidate_levels": candidates,
                "cost_counts": counters,
                "floor_levels": floor_levels,
                "variance_cost_allocation": allocation_info,
            }
        )
    return allocations


def _actual(p, mode):
    if mode not in ("full", "smoke"):
        raise ValueError("pilot mode must be full or smoke")
    return {
        "levels": p["pilot"]["levels"] if mode == "full" else p["pilot"]["levels"][:3],
        "streams": p["pilot"]["streams"] if mode == "full" else 1,
        "paths": p["pilot"]["paths_per_stream"] if mode == "full" else 32,
        "exact_paths": p["pilot"]["exact_cv_paths_per_stream"] if mode == "full" else 32,
        "timing_paths": p["timing"]["pairs_per_level"] if mode == "full" else 32,
    }


def _table_seconds(arrays, prefix):
    return arrays[prefix + ".rng_s"] + arrays[prefix + ".engine_s"] + arrays[prefix + ".summary_s"]


def _expenses(arrays, p, allocation_s, validation_s):
    expenses = [
        {
            "expense_id": "research_setup",
            "kind": "source and resolved ledger setup",
            "seconds": float(arrays["setup.seconds"][0]),
            "methods": ["research_setup"],
            "epsilons": p["epsilon"],
        }
    ]
    for prefix, kind, methods in (
        ("euler", "Euler full candidate pilot", ["mlmc", "plain_euler"]),
        ("exact", "independent exact/control pilot", ["exact_plain", "exact_cv"]),
    ):
        for index, seconds in enumerate(_table_seconds(arrays, prefix)):
            level = int(arrays[prefix + ".level"][index]) if prefix == "euler" else -1
            expenses.append(
                {
                    "expense_id": f"pilot.{prefix}.{index}",
                    "kind": kind,
                    "seconds": float(seconds),
                    "methods": methods,
                    "epsilons": p["epsilon"],
                    "level": level,
                    "stream": int(arrays[prefix + ".stream"][index]),
                    "block": int(arrays[prefix + ".block"][index]),
                }
            )
    for index, seconds in enumerate(arrays["calibration.total_s"]):
        expenses.append(
            {
                "expense_id": f"calibration.{index}",
                "kind": "isolated calibration",
                "seconds": float(seconds),
                "methods": ["mlmc"],
                "epsilons": p["epsilon"],
                "level": int(arrays["calibration.level"][index]),
                "warmup": bool(arrays["calibration.warmup"][index]),
            }
        )
    for i, identity in enumerate(arrays["allocation.expense_id"]):
        eps = arrays["allocation.epsilon"][i]
        expenses.append(
            {
                "expense_id": str(identity),
                "kind": "fixed pilot selection/counts/statistics",
                "seconds": float(arrays["allocation.seconds"][i]),
                "methods": str(arrays["allocation.methods"][i]).split("|"),
                "epsilons": p["epsilon"] if eps < 0 else [float(eps)],
            }
        )
    if not math.isclose(
        allocation_s,
        sum(row["seconds"] for row in expenses if row["expense_id"].startswith("allocation.")),
        rel_tol=1e-12,
        abs_tol=1e-10,
    ):
        raise ValueError("allocation seconds differ from phase ledger")
    expenses.append(
        {
            "expense_id": "clip_diagnostic",
            "kind": "fixed-seed CRN clip comparison",
            "seconds": float(arrays["clip.elapsed_s"][0]),
            "methods": ["rqmc"],
            "epsilons": p["epsilon"],
        }
    )
    expenses.extend(
        [
            {
                "expense_id": "pilot_validation",
                "kind": "saved moment/ledger/source validation",
                "seconds": validation_s,
                "methods": METHODS,
                "epsilons": p["epsilon"],
            }
        ]
    )
    return expenses


def _hardware():
    cpu = platform.processor()
    if Path("/proc/cpuinfo").is_file():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "threads": {
            name: os.environ.get(name)
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def _record(p, arrays, *, mode, source, allocation_s, validation_s):
    levels = _level_summaries(arrays, p)
    exact = _exact_summary(arrays, p)
    expenses = _expenses(arrays, p, allocation_s, validation_s)
    return {
        "schema": "RB-F08-pilot-v1",
        "mode": mode,
        "protocol": module("protocol").protocol_for_json(p),
        "protocol_digest": module("protocol").json_digest(
            module("protocol").protocol_conditions(p)
        ),
        "seed_ledger_digest": p["seed_ledger_meta"]["digest"],
        "source_fingerprint": source["digest"],
        "source": source,
        "actual": _actual(p, mode),
        "level_summaries": levels,
        "exact_summary": exact,
        "calibration": _calibration_summary(arrays),
        "rates": _rates(levels, p),
        "clip_diagnostic": _clip_summary(arrays, p),
        "allocations": choose_allocations({}, arrays, p),
        "cv_beta": exact["cv_beta"],
        "allocation_s": allocation_s,
        "setup_s": float(arrays["setup.seconds"][0]),
        "setup_ledger_generated": bool(arrays["setup.ledger_generated"][0]),
        "pilot_validation_s": validation_s,
        "pilot_s": float(
            _table_seconds(arrays, "euler").sum() + _table_seconds(arrays, "exact").sum()
        ),
        "calibration_s": float(arrays["calibration.total_s"].sum()),
        "freeze_validation_s": 0.0,
        "freeze_validation_pending": True,
        "expenses": expenses,
        "total_measured_s": math.fsum(row["seconds"] for row in expenses),
        "hardware": _hardware(),
        "limitations": [
            "finite-pilot bias envelope is empirical",
            "rates may be unresolved",
            "negative states retained",
            "smoke cannot freeze",
            "freeze time not yet incurred",
        ],
    }


def run_pilot(protocol: dict, *, mode: str = "full") -> tuple[dict, dict]:
    """Run the fixed full pilot, or the explicitly non-freezeable small smoke."""
    setup_started = perf_counter()
    ledger_generated = "seed_ledger" not in protocol
    source = _current_source()  # All required files must exist before any sampling.
    tools = module("protocol")
    tools.validate_protocol(protocol)
    if protocol["state"] != "candidate":
        raise ValueError("pilot generation requires candidate protocol")
    p = deepcopy(protocol)
    if "seed_ledger" not in p:
        p = tools.attach_seed_ledger(p, tools.build_seed_ledger(p))
    tools.validate_protocol(p)
    actual = _actual(p, mode)
    arrays = tools.pack_seed_ledger(p["seed_ledger"])
    arrays["setup.seconds"] = np.array([perf_counter() - setup_started])
    arrays["setup.ledger_generated"] = np.array([ledger_generated])
    arrays.update(_collect_euler(p, actual))
    arrays.update(_collect_exact(p, actual))
    arrays.update(_calibrate(p, actual))
    arrays.update(_collect_clip(p))
    allocation_timing = []
    choose_allocations({}, arrays, p, _timings=allocation_timing)
    arrays["allocation.expense_id"] = np.array([row["expense_id"] for row in allocation_timing])
    arrays["allocation.seconds"] = np.array([row["seconds"] for row in allocation_timing])
    arrays["allocation.methods"] = np.array(["|".join(row["methods"]) for row in allocation_timing])
    arrays["allocation.epsilon"] = np.array(
        [row["epsilons"][0] if len(row["epsilons"]) == 1 else -1.0 for row in allocation_timing]
    )
    allocation_s = sum(row["seconds"] for row in allocation_timing)
    record = _record(
        p, arrays, mode=mode, source=source, allocation_s=allocation_s, validation_s=0.0
    )
    start = perf_counter()
    validate_pilot(record, arrays, p)
    validation_s = perf_counter() - start
    record = _record(
        p, arrays, mode=mode, source=source, allocation_s=allocation_s, validation_s=validation_s
    )
    if source != _current_source():
        raise ValueError("pilot source/dependencies changed during execution")
    return record, arrays


def _compare(actual, expected, name):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError("pilot record fields differ: " + name)
        for key in expected:
            _compare(actual[key], expected[key], name + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("pilot record list differs: " + name)
        for index, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _compare(a, b, name + "." + str(index))
    elif isinstance(expected, float):
        _close(actual, expected, name)
    elif actual != expected:
        raise ValueError("pilot record metadata differs: " + name)


def _validate_operation_columns(arrays, p):
    for prefix in ("euler", "calibration"):
        for index, count in enumerate(arrays[prefix + ".count"]):
            level = int(arrays[prefix + ".level"][index])
            if not isinstance(arrays[prefix + ".level"][index], (int, np.integer)):
                raise ValueError("integer level metadata required")
            expected = cost_counts(level=level, base_steps=p["base_steps"], paths=int(count))
            expected = {"cost." + key: value for key, value in expected.items()}
            expected.update(
                {
                    "diagnostic_cost.stock_updates": int(count),
                    "diagnostic_cost.normal_draws": 0,
                    "diagnostic_cost.payoff_evaluations": int(count),
                    "diagnostic_cost.normal_sums": p["base_steps"] * 2**level * int(count),
                }
            )
            for key, value in expected.items():
                if (
                    arrays[prefix + "." + key].dtype.kind not in "iu"
                    or arrays[prefix + "." + key][index] != value
                ):
                    raise ValueError("Euler estimator or exact diagnostic cost count differs")
    for index, count in enumerate(arrays["exact.count"]):
        for key in (
            "cost.stock_updates",
            "cost.normal_draws",
            "cost.payoff_evaluations",
            "diagnostic_cost.control_evaluations",
        ):
            if (
                arrays["exact." + key].dtype.kind not in "iu"
                or arrays["exact." + key][index] != count
            ):
                raise ValueError("exact pilot/control operation count differs")


def _validate_tables(arrays, p, actual):
    for prefix in ("euler", "exact", "calibration"):
        count = arrays[prefix + ".count"]
        columns = [name for name in arrays if name.startswith(prefix + ".")]
        if count.dtype.kind not in "iu" or np.any(count < 2):
            raise ValueError("integer original pilot block counts >= 2 required")
        for name in columns:
            value = np.asarray(arrays[name])
            if value.ndim != 1 or len(value) != len(count) or not np.all(np.isfinite(value)):
                raise ValueError("finite same-sized one-dimensional pilot columns required")
            if name.endswith(("_s", ".m2")) and np.any(value < 0):
                raise ValueError("negative pilot seconds or centered M2")
    if (
        arrays["setup.seconds"].shape != (1,)
        or not np.isfinite(arrays["setup.seconds"]).all()
        or arrays["setup.seconds"][0] < 0
        or arrays["setup.ledger_generated"].shape != (1,)
        or arrays["setup.ledger_generated"].dtype.kind != "b"
    ):
        raise ValueError("explicit setup timing and ledger provenance required")
    _validate_allocation_expenses(arrays, p)
    _validate_operation_columns(arrays, p)
    expected_blocks = _block_sizes(actual["paths"], p["block_size"])
    for level in actual["levels"]:
        for stream in range(actual["streams"]):
            mask = (arrays["euler.level"] == level) & (arrays["euler.stream"] == stream)
            indices = np.flatnonzero(mask)
            if len(indices) != len(expected_blocks):
                raise ValueError("missing/extra fixed Euler pilot block")
            if arrays["euler.count"][indices].tolist() != expected_blocks:
                raise ValueError("Euler original block denominator differs from protocol")
            if arrays["euler.block"][indices].tolist() != list(range(len(expected_blocks))):
                raise ValueError("Euler fixed block order differs")
            if np.any(
                arrays["euler.seed"][indices]
                != _seed(p, "pilot", method="mlmc", level=level, run=stream)
            ):
                raise ValueError("Euler pilot seed differs from frozen ledger")
            for index in indices:
                expected = cost_counts(
                    level=level, base_steps=p["base_steps"], paths=int(arrays["euler.count"][index])
                )
                for name, value in expected.items():
                    if arrays["euler.cost." + name][index] != value:
                        raise ValueError("Euler operation count differs from original denominator")
    if len(arrays["euler.count"]) != len(actual["levels"]) * actual["streams"] * len(
        expected_blocks
    ):
        raise ValueError("extra Euler pilot roster")
    expected_exact = _block_sizes(actual["exact_paths"], p["block_size"])
    for stream in range(actual["streams"]):
        indices = np.flatnonzero(arrays["exact.stream"] == stream)
        if arrays["exact.count"][indices].tolist() != expected_exact or arrays["exact.block"][
            indices
        ].tolist() != list(range(len(expected_exact))):
            raise ValueError("exact original block denominators/order differ")
        if np.any(
            arrays["exact.seed"][indices] != _seed(p, "pilot", method="exact_cv", run=stream)
        ):
            raise ValueError("exact pilot seed differs from frozen ledger")
    if len(arrays["exact.count"]) != actual["streams"] * len(expected_exact):
        raise ValueError("extra exact pilot roster")
    repeats = p["timing"]["warmup_repetitions"] + p["timing"]["measured_repetitions"]
    for level in actual["levels"]:
        indices = np.flatnonzero(arrays["calibration.level"] == level)
        if (
            len(indices) != repeats
            or arrays["calibration.repeat"][indices].tolist() != list(range(repeats))
            or np.any(arrays["calibration.count"][indices] != actual["timing_paths"])
        ):
            raise ValueError("fixed timing roster/count differs")
        expected_warmups = [i < p["timing"]["warmup_repetitions"] for i in range(repeats)]
        if arrays["calibration.warmup"][indices].tolist() != expected_warmups:
            raise ValueError("warmup flags differ from fixed repetitions")
        for index in indices:
            if arrays["calibration.seed"][index] != _seed(
                p, "timing", level=level, run=int(arrays["calibration.repeat"][index])
            ):
                raise ValueError("timing seed differs from frozen ledger")
    if len(arrays["calibration.count"]) != len(actual["levels"]) * repeats:
        raise ValueError("extra calibration roster")
    _close(
        arrays["calibration.total_s"], _table_seconds(arrays, "calibration"), "calibration times"
    )


def validate_pilot(record: dict, arrays: dict, protocol: dict) -> dict:
    """Recompute pilot mathematics, allocations, CV beta and expenses from columns."""
    tools = module("protocol")
    if record.get("schema") != "RB-F08-pilot-v1" or record.get("mode") not in ("smoke", "full"):
        raise ValueError("known full/smoke pilot schema required")
    # Freeze validation supplies the candidate; a main checker may supply its frozen copy.
    candidate = deepcopy(protocol)
    candidate.pop("frozen", None)
    candidate["state"] = "candidate"
    if "seed_ledger" not in candidate:
        candidate = tools.attach_seed_ledger(candidate, tools.unpack_seed_ledger(arrays))
    tools.validate_protocol(candidate)
    hydrated = tools.hydrate_protocol(record["protocol"], arrays)
    if tools.protocol_conditions(hydrated) != tools.protocol_conditions(candidate):
        raise ValueError("pilot protocol conditions differ from fixed candidate")
    source = _current_source()
    if record.get("source") != source or record.get("source_fingerprint") != source["digest"]:
        raise ValueError("pilot source/dependency fingerprint mismatch")
    actual = _actual(candidate, record["mode"])
    _validate_tables(arrays, candidate, actual)
    for name in ("allocation_s", "pilot_validation_s"):
        if not math.isfinite(record[name]) or record[name] < 0:
            raise ValueError("finite nonnegative pilot overhead seconds required")
    expected = _record(
        candidate,
        arrays,
        mode=record["mode"],
        source=source,
        allocation_s=record["allocation_s"],
        validation_s=record["pilot_validation_s"],
    )
    for key in expected:
        if key in ("hardware",):
            continue  # Hardware belongs to the original timing provenance.
        _compare(record.get(key), expected[key], key)
    return {
        "passed": True,
        "mode": record["mode"],
        "levels": len(expected["level_summaries"]),
        "original_euler_paths": sum(row["count"] for row in expected["level_summaries"]),
        "original_exact_paths": expected["exact_summary"]["payoff"]["count"],
        "allocation_cells": len(expected["allocations"]),
        "numerical_comparison": {"rtol": 1e-9, "atol": 1e-10},
    }


def fresh_check(record, arrays, protocol):
    """Replay all pilot numerical blocks using stored seeds, excluding new timings."""
    validate_pilot(record, arrays, protocol)
    candidate = deepcopy(protocol)
    candidate.pop("frozen", None)
    candidate["state"] = "candidate"
    actual = _actual(candidate, record["mode"])
    start = perf_counter()
    reproduced = (
        _collect_euler(candidate, actual)
        | _collect_exact(candidate, actual)
        | _collect_clip(candidate)
    )
    checked = 0
    for name, expected in reproduced.items():
        if name.endswith("_s"):
            continue
        if expected.dtype.kind in "iub":
            if not np.array_equal(arrays[name], expected):
                raise ValueError("fresh pilot integer metadata mismatch: " + name)
        else:
            _close(arrays[name], expected, "fresh " + name)
        checked += 1
    return {
        "passed": True,
        "numerical_columns": checked,
        "fresh_s": perf_counter() - start,
        "timing_replay": "new wall seconds not required to match",
    }


def _artifact_tools():
    path = HERE.parent / "RB-F05" / "discrete" / "artifacts.py"
    spec = importlib.util.spec_from_file_location("rbf08_pilot_artifacts", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def _require_new_pilot(directory):
    """Keep every existing original observation, metadata file and CAS manifest."""
    if any(
        (Path(directory) / name).exists()
        for name in ("pilot.json", "pilot.npz", "pilot_manifest.json")
    ):
        raise FileExistsError(
            "existing pilot evidence cannot be overwritten; use a new output directory"
        )


def save_pilot(record, arrays, *, directory=HERE):
    """Save typed observations and compact metadata through the existing CAS helper."""
    directory = Path(directory)
    _require_new_pilot(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "pilot.npz").open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    saved = deepcopy(record)
    saved["artifact"] = _artifact_tools().store_large(directory, stem="pilot")
    with (directory / "pilot.json").open("x") as stream:
        json.dump(saved, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    (directory / "protocol.json").write_text(
        json.dumps(record["protocol"], ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    return saved


def main(argv=None):
    """Generate, check, replay or freeze a candidate pilot bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", nargs="?", const=True, type=Path)
    actions.add_argument("--freeze", nargs="?", const=True, type=Path)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("full", "smoke"), default="full")
    args = parser.parse_args(argv)
    tools = module("protocol")
    checking = args.check is not None or args.fresh or args.freeze is not None
    if args.freeze is not None and args.fresh:
        parser.error("--fresh belongs to a saved check, not --freeze")
    if checking:
        if args.protocol is not None or args.output is not None:
            parser.error("saved check/freeze is separate from --protocol/--output generation")
        named_directory = (
            args.check
            if isinstance(args.check, Path)
            else args.freeze
            if isinstance(args.freeze, Path)
            else None
        )
        directory = named_directory or args.directory or HERE
        if (
            named_directory is not None
            and args.directory is not None
            and named_directory.resolve() != args.directory.resolve()
        ):
            parser.error("named check/freeze directory differs from --directory")
        record, arrays = _artifact_tools().load_bundle(directory, stem="pilot")
        p = tools.hydrate_protocol(record["protocol"], arrays)
        if args.freeze is not None:
            review = json.loads((args.review or directory / "pilot_review.json").read_text())
            start = perf_counter()
            frozen = tools.freeze_protocol(p, record, arrays, review, source=_current_source())
            (directory / "protocol.json").write_text(
                json.dumps(
                    tools.protocol_for_json(frozen), ensure_ascii=False, indent=2, allow_nan=False
                )
                + "\n"
            )
            reloaded = tools.hydrate_protocol(
                json.loads((directory / "protocol.json").read_text()), arrays
            )
            tools.verify_frozen_source(reloaded, _current_source())
            elapsed = perf_counter() - start
            timing = {
                "schema": "RB-F08-freeze-cost-v1",
                "seconds": elapsed,
                "expense_id": "freeze_validation",
                "methods": METHODS,
                "epsilons": p["epsilon"],
                "protocol_frozen_digest": frozen["frozen"]["digest"],
                "scope": "freeze_protocol plus protocol save/read/validation; receipt serialization excluded",
            }
            (directory / "freeze_cost.json").write_text(json.dumps(timing, indent=2) + "\n")
            outcome = {"passed": True, "state": "frozen", "freeze_validation_s": elapsed}
        else:
            outcome = (
                fresh_check(record, arrays, p) if args.fresh else validate_pilot(record, arrays, p)
            )
    else:
        directory = args.output or args.directory or HERE
        if (
            args.output is not None
            and args.directory is not None
            and args.output.resolve() != args.directory.resolve()
        ):
            parser.error("--output differs from legacy --directory destination")
        _require_new_pilot(directory)  # Refuse before any full/smoke sampling starts.
        path = args.protocol or directory / "protocol.json"
        if args.protocol is not None and not path.is_file():
            raise FileNotFoundError("explicit input protocol does not exist: " + str(path))
        candidate = json.loads(path.read_text()) if path.is_file() else tools.candidate_protocol()
        if candidate.get("seed_ledger_meta") is not None and "seed_ledger" not in candidate:
            _, previous = _artifact_tools().load_bundle(path.parent, stem="pilot")
            candidate = tools.hydrate_protocol(candidate, previous)
        record, arrays = run_pilot(candidate, mode=args.mode)
        saved = save_pilot(record, arrays, directory=directory)
        outcome = {
            "passed": True,
            "mode": args.mode,
            "allocations": saved["allocations"],
            "cv_beta": saved["cv_beta"],
            "total_measured_s": saved["total_measured_s"],
        }
    print(json.dumps(outcome, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
