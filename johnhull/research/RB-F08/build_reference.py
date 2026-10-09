"""Frozen F08 experiment execution and compact raw-observation verification.

Main execution consumes a reviewed pilot and its final typed seed ledger.
Tiny fixture execution is explicitly separate and cannot authorize a main run.
Negative paths and failed original run slots remain in the saved roster.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _multilevel_mc as multilevel
from hullkit import _numerical_mc as numerical
from hullkit import _rqmc_ci as rqmc

HERE = Path(__file__).resolve().parent
SCHEMA = "RB-F08-reference-v1"
FIXTURE_SCHEMA = "RB-F08-fixture-v1"
METHODS = ("mlmc", "plain_euler", "exact_plain", "exact_cv")
_MODULES = {}
_COST_COLUMNS = ("stock_updates", "normal_draws", "payoff_evaluations", "coarse_aggregations")
_DIAGNOSTIC_COLUMNS = ("stock_updates", "normal_draws", "payoff_evaluations", "normal_sums")


def module(name):
    """Load a sibling research module or the existing explicit-directory CAS helper."""
    if name not in _MODULES:
        path = (
            HERE.parent / "RB-F05/discrete/artifacts.py"
            if name == "artifacts"
            else HERE / (name + ".py")
        )
        spec = importlib.util.spec_from_file_location("rbf08_execution_" + name, path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = loaded
        spec.loader.exec_module(loaded)
        _MODULES[name] = loaded
    return _MODULES[name]


def _json(value):
    """Convert scalar metadata for strict JSON; failed array values stay in NPZ."""
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json(value.tolist())
    if isinstance(value, np.generic):
        return _json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _snapshot(value):
    return np.asarray(
        json.dumps(_json(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def _read_snapshot(arrays, key):
    value = np.asarray(arrays[key])
    if value.shape != () or value.dtype.kind not in "US":
        raise ValueError(key + ": scalar JSON observation snapshot required")
    return json.loads(value.item())


def _compare(actual, expected, label):
    """Compare numerical derived claims with tolerance, and metadata exactly."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(label + ": dictionary registry differs")
        for key in expected:
            _compare(actual[key], expected[key], label + "." + key)
    elif isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise ValueError(label + ": sequence registry differs")
        for i, item in enumerate(expected):
            _compare(actual[i], item, label + "." + str(i))
    elif isinstance(expected, (float, np.floating)):
        if not isinstance(actual, (int, float)) or not math.isclose(
            actual, float(expected), rel_tol=1e-10, abs_tol=1e-12
        ):
            raise ValueError(label + ": numeric evidence differs")
    elif actual != expected:
        raise ValueError(label + ": metadata differs")


def _registry(arrays):
    return {
        key: {"shape": list(np.asarray(value).shape), "dtype": np.asarray(value).dtype.str}
        for key, value in sorted(arrays.items())
    }


def _source(*, strict=True):
    protocol = module("protocol")
    root = HERE.parents[1]
    paths = [root / name for name in protocol.SOURCE_FILES]
    if strict and any(not path.is_file() for path in paths):
        raise ValueError("complete frozen source registry required")
    return protocol.source_fingerprint([path for path in paths if path.is_file()])


def fixture_protocol() -> dict:
    """Create the isolated 4-run, m3/R4/L2 fixture; never an accepted main protocol."""
    protocol = module("protocol")
    p = protocol.candidate_protocol()
    p["epsilon"] = [0.4]
    p["pilot"].update(
        levels=[0, 1, 2], streams=1, paths_per_stream=16, exact_cv_paths_per_stream=16
    )
    p["main"].update(outer_runs=4, levels_reserved=[0, 1, 2])
    p["rqmc"].update(outer_runs=4, powers=[3], scrambles=[4])
    p["fresh_review"].update(paths_per_level=16, coverage_replay_runs=[0, 1, 3])
    p["timing"].update(pairs_per_level=8, warmup_repetitions=1, measured_repetitions=2)
    p["bootstrap"]["resamples"] = 32
    p["block_size"] = 8
    p["allocation"]["minimum_paths"] = 2
    p["fixture"] = {
        "schema": FIXTURE_SCHEMA,
        "cv_beta": 1.0,
        "review_digest": "fixture: no independent main approval",
        "allocations": [
            {
                "epsilon": 0.4,
                "status": "ready",
                "reason": "fixture only",
                "level": 2,
                "mlmc_paths": [16, 8, 4],
                "plain_euler_paths": 16,
                "exact_plain_paths": 16,
                "exact_cv_paths": 16,
                "bias_bound": 0.1,
                "sampling_variance": 0.08,
                "bias_target": 0.4 / math.sqrt(2),
                "method_status": {name: "ready" for name in METHODS},
                "method_reasons": {name: "fixture only" for name in METHODS},
            }
        ],
        "expenses": [
            {"expense_id": name, "seconds": value, "methods": ["all"], "epsilons": [0.4]}
            for name, value in (
                ("pilot", 0.01),
                ("calibration", 0.01),
                ("allocation", 0.001),
                ("freeze_validation", 0.001),
            )
        ],
    }
    return protocol.attach_seed_ledger(p, protocol.build_seed_ledger(p))


def _load_inputs(path, mode):
    protocol = module("protocol")
    saved = json.loads(Path(path).read_text())
    if mode == "main" and "fixture" in saved:
        raise ValueError("fixture can never be promoted to main")
    pilot_record = pilot_arrays = review = receipt = None
    if "seed_ledger" in saved:
        p = saved
        protocol.validate_protocol(p, require_frozen=mode == "main")
    else:
        pilot_record, pilot_arrays = module("artifacts").load_bundle(
            Path(path).parent, stem="pilot"
        )
        p = protocol.hydrate_protocol(saved, pilot_arrays)
    if mode == "fixture":
        if p.get("fixture", {}).get("schema") != FIXTURE_SCHEMA or p["state"] != "candidate":
            raise ValueError("explicit isolated fixture schema required")
        return p, None, None, None, None
    if mode != "main":
        raise ValueError("mode must be main or fixture")
    if pilot_record is None:
        pilot_record, pilot_arrays = module("artifacts").load_bundle(
            Path(path).parent, stem="pilot"
        )
    review = json.loads((Path(path).parent / "pilot_review.json").read_text())
    source = _source()
    protocol.verify_frozen_evidence(p, pilot_record, pilot_arrays, review, source=source)
    receipt = json.loads((Path(path).parent / "freeze_cost.json").read_text())
    if (
        receipt.get("schema") != "RB-F08-freeze-cost-v1"
        or receipt.get("protocol_frozen_digest") != p["frozen"]["digest"]
        or receipt.get("expense_id") != "freeze_validation"
        or receipt.get("methods") != list(METHODS)
        or receipt.get("epsilons") != p["epsilon"]
        or not isinstance(receipt.get("seconds"), (int, float))
        or not math.isfinite(receipt["seconds"])
        or receipt["seconds"] < 0
    ):
        raise ValueError("freeze cost receipt is missing or differs from frozen main")
    for name, value in p["threads"].items():
        if os.environ.get(name) != str(value):
            raise ValueError("main requires explicit frozen BLAS thread environment: " + name)
    return p, pilot_record, pilot_arrays, review, receipt


def _ledger_index(p):
    return {
        (
            row["phase"],
            row["case"],
            row["budget"],
            row["run"],
            row["method"],
            row["level"],
            row["scramble"],
        ): i
        for i, row in enumerate(p["seed_ledger"])
    }


def _index(index, phase, *, case=0, budget=0, run=0, method="mlmc", level=-1, scramble=-1):
    return index[(phase, case, budget, run, method, level, scramble)]


def _block_lengths(count, block_size):
    if count < 2 or block_size < 2:
        raise ValueError("at least two paths per block and original sample required")
    sizes = [min(block_size, count - start) for start in range(0, count, block_size)]
    if len(sizes) > 1 and sizes[-1] == 1:
        if sizes[-2] > 2:
            sizes[-2] -= 1
            sizes[-1] = 2
        else:
            tail = sizes.pop()
            sizes[-1] += tail
    return sizes


def _exact_samples(contract, z, beta):
    with np.errstate(over="raise", invalid="raise"):
        try:
            terminal = numerical.gbm_paths_from_normals(
                contract.spot,
                contract.rate,
                contract.sigma,
                contract.maturity,
                z,
                yield_rate=contract.yield_rate,
                scheme="exact",
            )[:, -1]
            discount = math.exp(-contract.rate * contract.maturity)
            samples = discount * np.maximum(terminal - contract.strike, 0)
            if beta is not None:
                samples -= beta * (
                    discount * terminal
                    - contract.spot * math.exp(-contract.yield_rate * contract.maturity)
                )
            if not np.isfinite(samples).all():
                raise ValueError("nonfinite exact payoff invalidates the original run")
            return samples
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("nonfinite exact payoff invalidates the original run") from exc


def _execute_level(p, row, *, level, paths, method, allocation, beta, prefix, arrays):
    base = (
        p["base_steps"]
        if method == "mlmc"
        else p["base_steps"] * 2 ** allocation["level"]
        if method == "plain_euler"
        else 1
    )
    core_level = level if method == "mlmc" else 0
    steps = base * 2**core_level if method in {"mlmc", "plain_euler"} else 1
    contract = multilevel.GBMCall(**p["parameters"])
    begin = perf_counter()
    rng = np.random.default_rng(row["seed"])
    init = perf_counter() - begin
    counts, moments, negatives, counters, timings = [], [], [], [], []
    error = None
    for n in _block_lengths(paths, p["block_size"]):
        try:
            start = perf_counter()
            z = rng.standard_normal((n, steps))
            rng_s = perf_counter() - start + init
            init = 0.0
            start = perf_counter()
            if method in {"mlmc", "plain_euler"}:
                result = multilevel.gbm_level_samples(
                    contract, z, level=core_level, base_steps=base
                )
                samples = result["differences"]
                negative = [
                    result[key]
                    for key in ("fine_negative_states", "coarse_negative_states", "negative_paths")
                ]
                cost = [result["cost_counts"][key] for key in _COST_COLUMNS]
                cost += [result["diagnostic_cost_counts"][key] for key in _DIAGNOSTIC_COLUMNS]
            else:
                samples = _exact_samples(contract, z, beta if method == "exact_cv" else None)
                negative = [0, 0, 0]
                cost = [n, n, n, 0, 0, 0, 0, 0]
            engine_s = perf_counter() - start
            start = perf_counter()
            block = multilevel.block_moments(samples)
            summary_s = perf_counter() - start
            counts.append(n)
            moments.append([block["mean"], block["m2"]])
            negatives.append(negative)
            counters.append(cost)
            timings.append([rng_s, engine_s, summary_s])
        except (ValueError, FloatingPointError, OverflowError) as exc:
            error = type(exc).__name__ + ": " + str(exc)
            break
    keys = {
        name + "_key": prefix + "_" + name
        for name in ("counts", "moments", "negatives", "counters", "timings")
    }
    arrays[keys["counts_key"]] = np.asarray(counts, dtype=np.int64)
    arrays[keys["moments_key"]] = np.asarray(moments, dtype=float).reshape(-1, 2)
    arrays[keys["negatives_key"]] = np.asarray(negatives, dtype=np.int64).reshape(-1, 3)
    arrays[keys["counters_key"]] = np.asarray(counters, dtype=np.int64).reshape(-1, 8)
    arrays[keys["timings_key"]] = np.asarray(timings, dtype=float).reshape(-1, 3)
    return {
        **keys,
        "level": level,
        "core_level": core_level,
        "base_steps": base,
        "steps": steps,
        "paths": paths,
        "seed": row["seed"],
        "logical_id": row["logical_id"],
        "status": "failed" if error else "complete",
        "reason": error,
    }


def _level_moments(level, arrays):
    counts = arrays[level["counts_key"]]
    values = arrays[level["moments_key"]]
    return multilevel.merge_moments(
        [
            {"count": int(n), "mean": float(mean), "m2": float(m2)}
            for n, (mean, m2) in zip(counts, values, strict=True)
        ]
    )


def _execute_method(p, index, allocation, *, budget, run, method, beta, arrays):
    start = perf_counter()
    levels = []
    method_status = allocation.get("method_status", {}).get(method, allocation["status"])
    if method_status not in {"ready", "valid"}:
        return {
            "run": run,
            "status": "skipped",
            "reason": allocation.get("method_reasons", {}).get(method, allocation["reason"]),
            "levels": [],
            "summary": None,
            "main_s": 0.0,
            "timing": {"rng_s": 0.0, "engine_s": 0.0, "summary_s": 0.0, "overhead_s": 0.0},
        }
    wanted = (
        list(enumerate(allocation["mlmc_paths"]))
        if method == "mlmc"
        else [(-1, allocation[method + "_paths"])]
    )
    for level, paths in wanted:
        i = _index(index, "main", budget=budget, run=run, method=method, level=level)
        row = p["seed_ledger"][i]
        saved = _execute_level(
            p,
            row,
            level=level,
            paths=paths,
            method=method,
            allocation=allocation,
            beta=beta,
            prefix=f"b{budget}_{method}_r{run}_l{level}",
            arrays=arrays,
        )
        saved["ledger_index"] = i
        levels.append(saved)
        if saved["status"] == "failed":
            break
    failed = any(level["status"] == "failed" for level in levels)
    start_summary = perf_counter()
    summary = (
        None
        if failed
        else multilevel.mlmc_summary(
            [_level_moments(level, arrays) for level in levels], confidence=p["main"]["confidence"]
        )
    )
    aggregate_s = perf_counter() - start_summary
    total = np.sum([arrays[level["timings_key"]].sum(axis=0) for level in levels], axis=0)
    total[2] += aggregate_s
    wall = perf_counter() - start
    timing = dict(zip(("rng_s", "engine_s", "summary_s"), map(float, total), strict=True))
    timing["overhead_s"] = max(0.0, wall - float(np.sum(total)))
    timing_key = f"b{budget}_{method}_r{run}_timing"
    arrays[timing_key] = np.asarray([*total, timing["overhead_s"], wall, aggregate_s], dtype=float)
    return {
        "run": run,
        "status": "failed" if failed else "complete",
        "reason": next((level["reason"] for level in levels if level["status"] == "failed"), None),
        "levels": levels,
        "summary": _json(summary),
        "main_s": wall,
        "timing": timing,
        "timing_key": timing_key,
    }


def _balanced_order(seed, repetitions):
    rng = np.random.default_rng(seed)
    out = []
    for start in range(0, repetitions, len(METHODS)):
        base = rng.permutation(len(METHODS))
        out.extend(np.roll(base, -i) for i in range(min(len(METHODS), repetitions - start)))
    return np.asarray(out, dtype=np.int64)


def _bootstrap_indices(seed, repetitions, resamples):
    """Generate frozen-seed integer resampling metadata once outside online methods."""
    return np.random.default_rng(seed).integers(
        0, repetitions, size=(resamples, repetitions), dtype=np.int64
    )


def _check_balanced_order(order):
    """Inspect saved order metadata without generating new order randomness."""
    if not np.all(np.sort(order, axis=1) == np.arange(len(METHODS))[None, :]):
        raise ValueError("saved method order does not contain every method exactly once")
    for start in range(0, len(order), len(METHODS)):
        group = order[start : start + len(METHODS)]
        if len(group) == len(METHODS) and not np.all(
            np.sort(group, axis=0) == np.arange(len(METHODS))[:, None]
        ):
            raise ValueError("saved method order is not balanced over each complete group")


def _coupling(p, index, arrays):
    row = p["seed_ledger"][_index(index, "fresh_review", method="mlmc", level=1)]
    normals = np.random.default_rng(row["seed"]).standard_normal(
        (p["fresh_review"]["paths_per_level"], p["base_steps"] * 2)
    )
    coarse = multilevel.coarse_normals(normals)
    result = multilevel.gbm_level_samples(
        multilevel.GBMCall(**p["parameters"]), normals, level=1, base_steps=p["base_steps"]
    )
    arrays.update(
        coupling_fine_normals=normals,
        coupling_coarse_normals=coarse,
        coupling_fine_payoffs=result["fine_payoffs"],
        coupling_coarse_payoffs=result["coarse_payoffs"],
    )
    return {
        "parameters": copy.deepcopy(p["parameters"]),
        "ledger_index": _index(index, "fresh_review", method="mlmc", level=1),
        "fine_normals_key": "coupling_fine_normals",
        "coarse_normals_key": "coupling_coarse_normals",
        "fine_payoffs_key": "coupling_fine_payoffs",
        "coarse_payoffs_key": "coupling_coarse_payoffs",
    }


def _coverage_cell(p, index, *, case, budget, scrambles, arrays):
    contract = multilevel.GBMCall(**{**p["parameters"], "strike": p["rqmc"]["strikes"][case]})
    power = p["rqmc"]["powers"][budget]
    count = p["rqmc"]["outer_runs"]
    prefix = f"coverage_k{case}_m{budget}_r{scrambles}"
    values = np.full((count, scrambles), np.nan)
    seed_indices = np.zeros((count, scrambles), dtype=np.int64)
    child_seeds = np.zeros((count, scrambles), dtype=np.uint32)
    endpoints = np.full((count, scrambles, 3), -1, dtype=np.int64)
    intervals = np.full((count, 2), np.nan)
    times = np.zeros((count, 6))
    runs = []
    for run in range(count):
        ids = [
            _index(
                index,
                "coverage",
                case=case,
                budget=budget,
                run=run,
                method="rqmc_r" + str(scrambles),
                scramble=scramble,
            )
            for scramble in range(scrambles)
        ]
        rows = [p["seed_ledger"][i] for i in ids]
        seed_indices[run] = ids
        child_seeds[run] = [row["seed"] for row in rows]
        start = perf_counter()
        try:
            result = rqmc.rqmc_gbm_call_from_seeds(
                contract,
                power=power,
                child_seeds=child_seeds[run].astype(int).tolist(),
                child_metadata=rows,
                confidence=p["rqmc"]["confidence"],
            )
            values[run] = result["estimates"]
            summary = {
                key: result[key]
                for key in (
                    "price",
                    "estimates",
                    "scrambles",
                    "standard_error",
                    "df",
                    "confidence_level",
                    "interval",
                    "width",
                    "degenerate",
                    "approximate",
                )
            }
            intervals[run] = summary["interval"]
            endpoints[run] = np.column_stack(
                [
                    result[name + "_by_scramble"]
                    for name in ("clipped_points", "uniform_zero_points", "uniform_one_points")
                ]
            )
            timing = result.get("timing", {})
            wall = perf_counter() - start
            internal = [
                float(timing.get(name, 0.0))
                for name in ("rng_s", "engine_s", "summary_s", "overhead_s", "wall_s")
            ]
            times[run] = [*internal, wall]
            if result["uniform_clip"] != [p["rqmc"]["clip"]["lower"], p["rqmc"]["clip"]["upper"]]:
                raise ValueError("RQMC generated clip differs from frozen input")
            runs.append(
                {
                    "run": run,
                    "status": "complete",
                    "reason": None,
                    "summary": _json({k: v for k, v in summary.items() if k != "estimates"}),
                }
            )
        except (ValueError, FloatingPointError, OverflowError) as exc:
            times[run, 5] = perf_counter() - start
            runs.append(
                {
                    "run": run,
                    "status": "failed",
                    "reason": type(exc).__name__ + ": " + str(exc),
                    "summary": None,
                }
            )
    keys = {
        name + "_key": prefix + "_" + name
        for name in (
            "estimates",
            "ledger_indices",
            "child_seeds",
            "endpoints",
            "intervals",
            "timings",
        )
    }
    arrays.update(
        {
            keys["estimates_key"]: values,
            keys["ledger_indices_key"]: seed_indices,
            keys["child_seeds_key"]: child_seeds,
            keys["endpoints_key"]: endpoints,
            keys["intervals_key"]: intervals,
            keys["timings_key"]: times,
        }
    )
    parameters = {**p["parameters"], "strike": contract.strike}
    truth = module("reference_methods").black_call(parameters)
    clip_truth = module("reference_methods").clipped_black_call(
        parameters, (p["rqmc"]["clip"]["lower"], p["rqmc"]["clip"]["upper"])
    )
    valid = all(row["status"] == "complete" for row in runs)
    return {
        **keys,
        "case": case,
        "budget": budget,
        "strike": contract.strike,
        "power": power,
        "scrambles": scrambles,
        "points_per_scramble": 2**power,
        "outer_runs": count,
        "status": "valid" if valid else "failed",
        "reason": None if valid else "original_run_failure",
        "truth_BSM": truth,
        "truth_clip": clip_truth,
        "clip": copy.deepcopy(p["rqmc"]["clip"]),
        "child_metadata_source": "full frozen typed ledger at ledger_indices_key",
        "runs": runs,
        "coverage_BSM": module("analytics").coverage_summary(intervals, truth) if valid else None,
        "coverage_clip": module("analytics").coverage_summary(intervals, clip_truth)
        if valid
        else None,
        "errors_BSM": module("analytics").error_summary(values.mean(axis=1), truth)
        if valid
        else None,
        "errors_clip": module("analytics").error_summary(values.mean(axis=1), clip_truth)
        if valid
        else None,
    }


def _input_snapshot(record):
    return {
        key: copy.deepcopy(record[key])
        for key in (
            "schema",
            "mode",
            "protocol",
            "allocations",
            "cv_beta",
            "review_digest",
            "source",
            "offline_expenses",
            "freeze_cost",
        )
    }


def _summary_costs(record):
    runs = [
        {"method": name, "epsilon": cell["epsilon"], "main_s": run["main_s"]}
        for cell in record["budget_cells"]
        for name, method in cell["methods"].items()
        for run in method["runs"]
    ]
    pilot = {
        "expenses": record["offline_expenses"],
        "serialization_s": record.get("serialization_s", 0.0),
        "fresh_review_s": record.get("fresh_review_s", 0.0),
    }
    result = {
        "total": module("analytics").cost_account(pilot, runs),
        "methods": {
            str(cell["epsilon"]): {
                name: module("analytics").cost_account(
                    pilot, runs, method=name, epsilon=cell["epsilon"]
                )
                for name in METHODS
            }
            for cell in record["budget_cells"]
        },
        "coverage_main_s": math.fsum(
            float(row["main_s"]) for row in record.get("coverage_cost_runs", [])
        ),
    }
    result["analytic_reference_s"] = record["analytic_reference"]["seconds"]
    result["full_experiment_s"] = (
        result["total"]["experiment_s"]
        + result["coverage_main_s"]
        + record.get("diagnostic_s", 0.0)
        + result["analytic_reference_s"]
    )
    result["full_research_s_before_fresh"] = (
        result["total"]["research_total_s"]
        + result["coverage_main_s"]
        + record.get("diagnostic_s", 0.0)
        + result["analytic_reference_s"]
    )
    result["fresh_cost_pending"] = True
    return result


def run_reference(output: Path, *, protocol_path: Path, mode: str = "main") -> dict:
    """Execute the complete input roster once, retaining failed/skipped original slots."""
    output = Path(output)
    if any(
        (output / name).exists()
        for name in ("reference.json", "reference.npz", "reference_manifest.json")
    ):
        raise FileExistsError(
            "existing reference cannot be overwritten; use a new output directory"
        )
    start_setup = perf_counter()
    p, pilot_record, pilot_arrays, review, receipt = _load_inputs(protocol_path, mode)
    protocol = module("protocol")
    index = _ledger_index(p)
    if mode == "fixture":
        inputs = p["fixture"]
        allocations, beta = copy.deepcopy(inputs["allocations"]), inputs["cv_beta"]
        review_digest = inputs["review_digest"]
        expenses = copy.deepcopy(inputs["expenses"])
    else:
        allocations, beta = copy.deepcopy(p["frozen"]["allocations"]), p["frozen"]["cv_beta"]
        review_digest = p["frozen"]["review_digest"]
        expenses = [
            copy.deepcopy(e)
            for e in pilot_record["expenses"]
            if e["expense_id"] != "freeze_validation"
        ]
        expenses.append(
            {
                key: copy.deepcopy(receipt[key])
                for key in ("expense_id", "seconds", "methods", "epsilons")
            }
        )
    if [a["epsilon"] for a in allocations] != p["epsilon"]:
        raise ValueError("allocation epsilon roster differs from frozen input")
    if mode == "main":
        expenses.append(
            {
                "expense_id": "main_setup_validation",
                "seconds": perf_counter() - start_setup,
                "methods": ["all"],
                "epsilons": p["epsilon"],
                "kind": "input validation and seed indexing",
            }
        )
    analytic_start = perf_counter()
    analytic_price = module("reference_methods").black_call(p["parameters"])
    analytic_seconds = perf_counter() - analytic_start
    arrays = protocol.pack_seed_ledger(p["seed_ledger"])
    record = {
        "schema": SCHEMA if mode == "main" else FIXTURE_SCHEMA,
        "mode": mode,
        "protocol": protocol.protocol_for_json(p),
        "allocations": allocations,
        "cv_beta": beta,
        "analytic_reference": {
            "method": "independent_BSM",
            "evaluations": 1,
            "price": analytic_price,
            "seconds": analytic_seconds,
            "scope": "single evaluation including module lookup; descriptive, not a robust benchmark",
        },
        "review_digest": review_digest,
        "source": _source(strict=mode == "main"),
        "freeze_cost": receipt,
        "offline_expenses": expenses,
        "epsilons": p["epsilon"],
        "main_repetitions": p["main"]["outer_runs"],
        "coverage_repetitions": p["rqmc"]["outer_runs"],
        "bootstrap_resamples": p["bootstrap"]["resamples"],
        "budget_cells": [],
        "coverage_cells": [],
        "coverage_cost_runs": [],
        "serialization_s": 0.0,
        "fresh_review_s": 0.0,
        "fresh_review_pending": True,
        "teaching_acceptance": False,
        "limits": [
            "Student intervals are approximate",
            "sampling CI targets Euler expectation",
            "bias envelope is finite-pilot empirical evidence",
            "negative paths retained",
            "unique physical seeds do not prove mathematical independence",
        ],
    }
    if mode == "main":
        arrays["pilot_record_snapshot"] = _snapshot(pilot_record)
        arrays["pilot_review_snapshot"] = _snapshot(review)
        arrays.update(
            {"pilot_" + key: np.asarray(value).copy() for key, value in pilot_arrays.items()}
        )
    bootstrap_s = 0.0
    for budget, allocation in enumerate(allocations):
        order_row = p["seed_ledger"][
            _index(index, "method_order", budget=budget, method="method_order")
        ]
        order = _balanced_order(order_row["seed"], p["main"]["outer_runs"])
        order_key = f"b{budget}_method_order"
        arrays[order_key] = order
        bootstrap_row = p["seed_ledger"][
            _index(index, "bootstrap", budget=budget, method="bootstrap")
        ]
        indices_key = f"b{budget}_bootstrap_indices"
        start_indices = perf_counter()
        arrays[indices_key] = _bootstrap_indices(
            bootstrap_row["seed"], p["main"]["outer_runs"], p["bootstrap"]["resamples"]
        )
        bootstrap_s += perf_counter() - start_indices
        cell = {
            "epsilon": allocation["epsilon"],
            "status": "valid",
            "reason": None,
            "truth": analytic_price,
            "bootstrap_seed": p["seed_ledger"][
                _index(index, "bootstrap", budget=budget, method="bootstrap")
            ]["seed"],
            "bootstrap_indices_key": indices_key,
            "bootstrap_indices_digest": protocol.arrays_digest({indices_key: arrays[indices_key]}),
            "method_order_key": order_key,
            "method_order_seed": order_row["seed"],
            "method_order_digest": protocol.arrays_digest({order_key: arrays[order_key]}),
            "methods": {},
        }
        for name in METHODS:
            cell["methods"][name] = {"runs": [None] * p["main"]["outer_runs"]}
        for run, ordinals in enumerate(order):
            for ordinal in ordinals:
                name = METHODS[int(ordinal)]
                cell["methods"][name]["runs"][run] = _execute_method(
                    p,
                    index,
                    allocation,
                    budget=budget,
                    run=run,
                    method=name,
                    beta=beta,
                    arrays=arrays,
                )
        for name, method in cell["methods"].items():
            prices = np.asarray(
                [run["summary"]["price"] if run["summary"] else np.nan for run in method["runs"]]
            )
            elapsed = np.asarray([run["main_s"] for run in method["runs"]])
            intervals = np.asarray(
                [
                    run["summary"]["interval"] if run["summary"] else [np.nan, np.nan]
                    for run in method["runs"]
                ]
            )
            keys = {
                kind + "_key": f"b{budget}_{name}_{kind}"
                for kind in ("prices", "seconds", "intervals", "bias_intervals")
            }
            (
                arrays[keys["prices_key"]],
                arrays[keys["seconds_key"]],
                arrays[keys["intervals_key"]],
            ) = prices, elapsed, intervals
            bias = allocation.get("bias_bound") if name in {"mlmc", "plain_euler"} else 0.0
            arrays[keys["bias_intervals_key"]] = (
                intervals + np.array([-bias, bias])
                if bias is not None
                else np.full_like(intervals, np.nan)
            )
            valid = all(run["status"] == "complete" for run in method["runs"])
            method.update(
                keys,
                status="valid" if valid else "failed",
                reason=None
                if valid
                else "original_run_failure"
                if any(run["status"] == "failed" for run in method["runs"])
                else "frozen_method_unavailable",
                errors=module("analytics").error_summary(prices, cell["truth"]) if valid else None,
                coverage=module("analytics").coverage_summary(intervals, cell["truth"])
                if valid
                else None,
                bias_aware_coverage=module("analytics").coverage_summary(
                    arrays[keys["bias_intervals_key"]], cell["truth"]
                )
                if valid and bias is not None
                else None,
            )
        if allocation["status"] not in {"ready", "valid"}:
            cell.update(status="failed", reason=allocation.get("reason") or allocation["status"])
        elif any(method["status"] != "valid" for method in cell["methods"].values()):
            cell.update(status="failed", reason="original_run_failure")
        record["budget_cells"].append(cell)
    for case in range(len(p["rqmc"]["strikes"])):
        for budget in range(len(p["rqmc"]["powers"])):
            for scrambles in p["rqmc"]["scrambles"]:
                cell = _coverage_cell(
                    p, index, case=case, budget=budget, scrambles=scrambles, arrays=arrays
                )
                record["coverage_cells"].append(cell)
                record["coverage_cost_runs"].extend(
                    {
                        "case": case,
                        "power": cell["power"],
                        "scrambles": scrambles,
                        "run": run,
                        "main_s": float(seconds),
                    }
                    for run, seconds in enumerate(arrays[cell["timings_key"]][:, 5])
                )
    diagnostic_start = perf_counter()
    record["coupling_diagnostic"] = _coupling(p, index, arrays)
    record["bootstrap_setup_s"] = bootstrap_s
    record["diagnostic_s"] = perf_counter() - diagnostic_start + bootstrap_s
    record["decision"] = module("analytics").decision(record, arrays)
    record["costs"] = _summary_costs(record)
    arrays["input_snapshot"] = _snapshot(_input_snapshot(record))
    record["array_registry"] = _registry(arrays)
    check_record(record, arrays)
    save_result(output, record, arrays)
    return record


def save_result(output: Path, record: dict, arrays: dict) -> None:
    """Save typed compact observations once, using existing two-store CAS above 20MB."""
    output = Path(output)
    if any(
        (output / name).exists()
        for name in ("reference.json", "reference.npz", "reference_manifest.json")
    ):
        raise FileExistsError("existing reference cannot be overwritten")
    output.mkdir(parents=True, exist_ok=True)
    if any(np.asarray(value).dtype.kind == "O" for value in arrays.values()):
        raise ValueError("object arrays are forbidden")
    record["array_registry"] = _registry(arrays)
    start = perf_counter()
    with (output / "reference.npz").open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    record["artifact"] = module("artifacts").store_large(output, stem="reference")
    record["serialization_s"] = perf_counter() - start
    record["costs"] = _summary_costs(record)
    with (output / "reference.json").open("x") as stream:
        json.dump(_json(record), stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def load_result(output: Path) -> tuple[dict, dict]:
    """Load declared local/CAS observations without permitting NumPy pickle."""
    return module("artifacts").load_bundle(Path(output), stem="reference")


def _array(arrays, key, shape, *, kind="f", finite=True):
    value = np.asarray(arrays[key])
    if (
        value.shape != shape
        or value.dtype.kind not in kind
        or (finite and not np.isfinite(value).all())
    ):
        raise ValueError(key + ": raw shape/dtype/finite evidence differs")
    return value


def _check_level(p, level, arrays, *, method, allocation, row):
    paths = level["paths"]
    if isinstance(paths, bool) or not isinstance(paths, int) or paths < 2:
        raise ValueError("integer original level paths required")
    if level["seed"] != row["seed"] or level["logical_id"] != row["logical_id"]:
        raise ValueError("level seed differs from frozen logical slot")
    base = (
        p["base_steps"]
        if method == "mlmc"
        else p["base_steps"] * 2 ** allocation["level"]
        if method == "plain_euler"
        else 1
    )
    core = level["level"] if method == "mlmc" else 0
    steps = base * 2**core if method in {"mlmc", "plain_euler"} else 1
    if (level["base_steps"], level["core_level"], level["steps"]) != (base, core, steps):
        raise ValueError("level Euler/exact scheme or grid differs")
    counts = np.asarray(arrays[level["counts_key"]])
    if counts.ndim != 1 or counts.dtype.kind not in "iu" or np.any(counts < 2):
        raise ValueError("integer independent block path counts required")
    nblocks = len(counts)
    values = _array(arrays, level["moments_key"], (nblocks, 2))
    negatives = _array(arrays, level["negatives_key"], (nblocks, 3), kind="iu")
    counters = _array(arrays, level["counters_key"], (nblocks, 8), kind="iu")
    timings = _array(arrays, level["timings_key"], (nblocks, 3))
    expected_counts = np.asarray(_block_lengths(paths, p["block_size"]), dtype=np.int64)
    if not np.array_equal(counts, expected_counts[:nblocks]):
        raise ValueError("block path counts differ from frozen original allocation")
    if (
        np.any(values[:, 1] < 0)
        or np.any(negatives < 0)
        or np.any(counters < 0)
        or np.any(timings < 0)
    ):
        raise ValueError("negative M2, incidence, counter or seconds")
    if level["status"] == "complete":
        if (
            nblocks != len(expected_counts)
            or int(counts.sum()) != paths
            or level["reason"] is not None
        ):
            raise ValueError("complete level omitted original paths")
    elif level["status"] == "failed":
        if (
            nblocks >= len(expected_counts)
            or not isinstance(level["reason"], str)
            or not level["reason"]
        ):
            raise ValueError("failed level must retain its incomplete original slot and reason")
    else:
        raise ValueError("unknown level status")
    coarse_steps = steps // 2 if method == "mlmc" and core > 0 else 0
    bounds = counts[:, None] * np.array([steps, coarse_steps, 1])[None, :]
    if np.any(negatives > bounds):
        raise ValueError("negative incidence exceeds original path/state denominators")
    expected = []
    for n in counts:
        if method in {"mlmc", "plain_euler"}:
            expected.append(
                [
                    (steps + coarse_steps) * n,
                    steps * n,
                    (1 + (coarse_steps > 0)) * n,
                    coarse_steps * n,
                    n,
                    0,
                    n,
                    steps * n,
                ]
            )
        else:
            expected.append([n, n, n, 0, 0, 0, 0, 0])
    if not np.array_equal(counters, np.asarray(expected, dtype=np.int64).reshape(-1, 8)):
        raise ValueError("physical Euler/diagnostic cost counters differ")
    return _level_moments(level, arrays) if level["status"] == "complete" else None


def _check_method(p, index, method, arrays, *, allocation, budget, name):
    count = p["main"]["outer_runs"]
    if len(method["runs"]) != count or [run["run"] for run in method["runs"]] != list(range(count)):
        raise ValueError("original independent main run roster differs")
    expected_prices = np.full(count, np.nan)
    expected_intervals = np.full((count, 2), np.nan)
    seconds = np.zeros(count)
    method_status = allocation.get("method_status", {}).get(name, allocation["status"])
    wanted = (
        list(enumerate(allocation["mlmc_paths"]))
        if name == "mlmc" and method_status in {"ready", "valid"}
        else [(-1, allocation.get(name + "_paths"))]
    )
    for run in method["runs"]:
        run_number = run["run"]
        if run["status"] == "skipped":
            if (
                method_status in {"ready", "valid"}
                or run["levels"]
                or run["summary"] is not None
                or run["main_s"] != 0
            ):
                raise ValueError("valid frozen method was skipped")
            continue
        if run["status"] not in {"complete", "failed"} or method_status not in {"ready", "valid"}:
            raise ValueError("unknown main run status or executed unavailable method")
        levels = run["levels"]
        if not levels or len(levels) > len(wanted):
            raise ValueError("level roster omitted or added slots")
        moments = []
        for saved, (level, paths) in zip(levels, wanted, strict=False):
            i = _index(index, "main", budget=budget, run=run_number, method=name, level=level)
            if (saved["level"], saved["paths"], saved["ledger_index"]) != (level, paths, i):
                raise ValueError("fixed allocation or seed slot differs")
            moments.append(
                _check_level(
                    p, saved, arrays, method=name, allocation=allocation, row=p["seed_ledger"][i]
                )
            )
        completed = len(levels) == len(wanted) and all(
            saved["status"] == "complete" for saved in levels
        )
        if (run["status"] == "complete") != completed:
            raise ValueError("failed/complete main status differs from original level slots")
        if completed:
            summary = _json(multilevel.mlmc_summary(moments, confidence=p["main"]["confidence"]))
            _compare(run["summary"], summary, "main summary")
            expected_prices[run_number] = summary["price"]
            expected_intervals[run_number] = summary["interval"]
            if run["reason"] is not None:
                raise ValueError("complete run cannot have a failure reason")
        elif run["summary"] is not None or not run["reason"]:
            raise ValueError("failed original run must remain unsupported")
        timing = _array(arrays, run["timing_key"], (6,))
        if np.any(timing < 0) or timing[4] <= 0:
            raise ValueError("finite nonnegative timing observations required")
        raw = np.sum([arrays[level["timings_key"]].sum(axis=0) for level in levels], axis=0)
        raw[2] += timing[5]
        if not np.allclose(timing[:3], raw, rtol=1e-10, atol=1e-12) or not math.isclose(
            float(timing[:4].sum()), float(timing[4]), rel_tol=1e-9, abs_tol=1e-10
        ):
            raise ValueError("main component timings differ from raw blocks and wall time")
        _compare(
            run["timing"],
            dict(zip(("rng_s", "engine_s", "summary_s", "overhead_s"), timing[:4], strict=True)),
            "main timing",
        )
        _compare(run["main_s"], float(timing[4]), "main seconds")
        seconds[run_number] = timing[4]
    prices = _array(arrays, method["prices_key"], (count,), finite=False)
    intervals = _array(arrays, method["intervals_key"], (count, 2), finite=False)
    elapsed = _array(arrays, method["seconds_key"], (count,))
    if (
        not np.allclose(prices, expected_prices, rtol=1e-10, atol=1e-12, equal_nan=True)
        or not np.allclose(intervals, expected_intervals, rtol=1e-10, atol=1e-12, equal_nan=True)
        or not np.allclose(elapsed, seconds, rtol=1e-10, atol=1e-12)
    ):
        raise ValueError("method observations differ from all original run statistics")
    bound = allocation.get("bias_bound") if name in {"mlmc", "plain_euler"} else 0.0
    expected_bias = (
        intervals + np.array([-bound, bound])
        if bound is not None
        else np.full_like(intervals, np.nan)
    )
    bias_intervals = _array(arrays, method["bias_intervals_key"], (count, 2), finite=False)
    if not np.allclose(bias_intervals, expected_bias, rtol=1e-10, atol=1e-12, equal_nan=True):
        raise ValueError("sampling and empirical bias-aware intervals differ")
    valid = all(run["status"] == "complete" for run in method["runs"])
    if method["status"] != ("valid" if valid else "failed"):
        raise ValueError("method status differs from original runs")
    expected_reason = (
        None
        if valid
        else "original_run_failure"
        if any(run["status"] == "failed" for run in method["runs"])
        else "frozen_method_unavailable"
    )
    if method["reason"] != expected_reason:
        raise ValueError("method reason differs from frozen/original run roster")
    truth = module("reference_methods").black_call(p["parameters"])
    _compare(
        method["errors"],
        module("analytics").error_summary(prices, truth) if valid else None,
        "method errors",
    )
    _compare(
        method["coverage"],
        module("analytics").coverage_summary(intervals, truth) if valid else None,
        "method coverage",
    )
    _compare(
        method["bias_aware_coverage"],
        module("analytics").coverage_summary(bias_intervals, truth)
        if valid and bound is not None
        else None,
        "method bias-aware coverage",
    )


def _check_coverage(p, index, cell, arrays):
    case, budget, scrambles = cell["case"], cell["budget"], cell["scrambles"]
    count = p["rqmc"]["outer_runs"]
    if (cell["strike"], cell["power"], cell["points_per_scramble"], cell["outer_runs"]) != (
        p["rqmc"]["strikes"][case],
        p["rqmc"]["powers"][budget],
        2 ** p["rqmc"]["powers"][budget],
        count,
    ):
        raise ValueError("RQMC product or point/run roster differs")
    if cell["clip"] != p["rqmc"]["clip"]:
        raise ValueError("RQMC clip values/hex differ from frozen input")
    estimates = _array(arrays, cell["estimates_key"], (count, scrambles), finite=False)
    intervals = _array(arrays, cell["intervals_key"], (count, 2), finite=False)
    ids = _array(arrays, cell["ledger_indices_key"], (count, scrambles), kind="iu")
    seeds = _array(arrays, cell["child_seeds_key"], (count, scrambles), kind="iu")
    endpoints = _array(arrays, cell["endpoints_key"], (count, scrambles, 3), kind="iu")
    timings = _array(arrays, cell["timings_key"], (count, 6))
    if len(cell["runs"]) != count or [run["run"] for run in cell["runs"]] != list(range(count)):
        raise ValueError("original coverage run roster differs")
    for run in cell["runs"]:
        r = run["run"]
        wanted = [
            _index(
                index,
                "coverage",
                case=case,
                budget=budget,
                run=r,
                method="rqmc_r" + str(scrambles),
                scramble=s,
            )
            for s in range(scrambles)
        ]
        wanted_seeds = [p["seed_ledger"][i]["seed"] for i in wanted]
        if not np.array_equal(ids[r], wanted) or not np.array_equal(seeds[r], wanted_seeds):
            raise ValueError("RQMC physical/logical child seed differs from frozen ledger")
        if np.any(timings[r] < 0) or timings[r, 5] <= 0:
            raise ValueError("positive original RQMC run wall time required")
        if run["status"] == "complete":
            summary = rqmc.student_summary(estimates[r], confidence=p["rqmc"]["confidence"])
            _compare(
                run["summary"],
                _json({key: value for key, value in summary.items() if key != "estimates"}),
                "Student scramble summary",
            )
            if not np.allclose(intervals[r], summary["interval"], rtol=1e-10, atol=1e-12):
                raise ValueError("RQMC interval differs from independent scramble observations")
            if (
                np.any(endpoints[r] < 0)
                or np.any(endpoints[r] > 2 ** cell["power"])
                or np.any(endpoints[r, :, 1:].sum(axis=1) > endpoints[r, :, 0])
            ):
                raise ValueError("Sobol endpoint incidence exceeds point denominator")
            if (
                not math.isclose(
                    float(timings[r, :4].sum()), float(timings[r, 4]), rel_tol=1e-8, abs_tol=1e-8
                )
                or timings[r, 4] > timings[r, 5] + 1e-8
            ):
                raise ValueError("RQMC component timing and internal/external wall differ")
            if run["reason"] is not None:
                raise ValueError("complete coverage run has failure reason")
        elif run["status"] == "failed":
            if run["summary"] is not None or not run["reason"]:
                raise ValueError("failed original coverage run was replaced")
        else:
            raise ValueError("unknown coverage run status")
    valid = all(run["status"] == "complete" for run in cell["runs"])
    if cell["status"] != ("valid" if valid else "failed") or cell["reason"] != (
        None if valid else "original_run_failure"
    ):
        raise ValueError("coverage status differs from original run roster")
    parameters = {**p["parameters"], "strike": cell["strike"]}
    truth = module("reference_methods").black_call(parameters)
    clipped = module("reference_methods").clipped_black_call(
        parameters, (p["rqmc"]["clip"]["lower"], p["rqmc"]["clip"]["upper"])
    )
    _compare(cell["truth_BSM"], truth, "BSM truth")
    _compare(cell["truth_clip"], clipped, "clipped integral truth")
    for label, reference in (("BSM", truth), ("clip", clipped)):
        _compare(
            cell["coverage_" + label],
            module("analytics").coverage_summary(intervals, reference) if valid else None,
            "coverage " + label,
        )
        _compare(
            cell["errors_" + label],
            module("analytics").error_summary(estimates.mean(axis=1), reference) if valid else None,
            "errors " + label,
        )


def check_record(record: dict, arrays: dict, *, fresh: bool = False) -> dict:
    """Recompute all claims from original block/scramble observations and fixed inputs."""
    if record.get("mode") not in {"fixture", "main"} or record.get("schema") != (
        FIXTURE_SCHEMA if record["mode"] == "fixture" else SCHEMA
    ):
        raise ValueError("explicit main/fixture reference schema required")
    if record.get("teaching_acceptance") is not False:
        raise ValueError("execution evidence does not authorize final teaching acceptance")
    if record.get("fresh_review_pending") is not True or record.get("fresh_review_s") != 0:
        raise ValueError("original reference keeps fresh cost pending; use bound separate receipts")
    if any(np.asarray(value).dtype.kind == "O" for value in arrays.values()):
        raise ValueError("object arrays are forbidden")
    if record["array_registry"] != _registry(arrays):
        raise ValueError("array registry/shape/dtype differs")
    if (
        _snapshot(_input_snapshot(record)).item()
        != _snapshot(_read_snapshot(arrays, "input_snapshot")).item()
    ):
        raise ValueError("input snapshot differs from fixed provenance/conditions")
    protocol = module("protocol")
    p = protocol.hydrate_protocol(record["protocol"], arrays)
    if record["mode"] == "main":
        if "fixture" in p:
            raise ValueError("fixture cannot pass main checker")
        pilot = _read_snapshot(arrays, "pilot_record_snapshot")
        review = _read_snapshot(arrays, "pilot_review_snapshot")
        pilot_arrays = {
            key.removeprefix("pilot_"): value
            for key, value in arrays.items()
            if key.startswith("pilot_")
            and key not in {"pilot_record_snapshot", "pilot_review_snapshot"}
        }
        protocol.verify_frozen_evidence(p, pilot, pilot_arrays, review, source=_source())
        expected_allocations, beta = p["frozen"]["allocations"], p["frozen"]["cv_beta"]
        review_digest = p["frozen"]["review_digest"]
    else:
        if p.get("fixture", {}).get("schema") != FIXTURE_SCHEMA:
            raise ValueError("isolated fixture input required")
        expected_allocations, beta = p["fixture"]["allocations"], p["fixture"]["cv_beta"]
        review_digest = p["fixture"]["review_digest"]
    _compare(record["allocations"], expected_allocations, "approved allocations")
    _compare(record["cv_beta"], beta, "independent fixed beta")
    if record["review_digest"] != review_digest:
        raise ValueError("approved review digest differs")
    if (
        record["main_repetitions"],
        record["coverage_repetitions"],
        record["bootstrap_resamples"],
        record["epsilons"],
    ) != (
        p["main"]["outer_runs"],
        p["rqmc"]["outer_runs"],
        p["bootstrap"]["resamples"],
        p["epsilon"],
    ):
        raise ValueError("frozen main repetition/epsilon/bootstrap roster differs")
    analytic = record.get("analytic_reference", {})
    if analytic.get("method") != "independent_BSM" or analytic.get("evaluations") != 1:
        raise ValueError("analytic BSM one-evaluation comparator required")
    _compare(
        analytic.get("price"),
        module("reference_methods").black_call(p["parameters"]),
        "analytic price",
    )
    seconds = analytic.get("seconds")
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("analytic time must be finite and nonnegative")
    index = _ledger_index(p)
    proof = record["coupling_diagnostic"]
    proof_index = _index(index, "fresh_review", method="mlmc", level=1)
    if proof["parameters"] != p["parameters"] or proof["ledger_index"] != proof_index:
        raise ValueError("coupling product/stream differs from independent frozen diagnostic")
    _array(
        arrays,
        proof["fine_normals_key"],
        (p["fresh_review"]["paths_per_level"], p["base_steps"] * 2),
    )
    if len(record["budget_cells"]) != len(p["epsilon"]):
        raise ValueError("complete epsilon budget roster required")
    for budget, (cell, allocation) in enumerate(
        zip(record["budget_cells"], expected_allocations, strict=True)
    ):
        if cell["epsilon"] != p["epsilon"][budget] or set(cell["methods"]) != set(METHODS):
            raise ValueError("fixed budget/method roster differs")
        _compare(
            cell["truth"],
            module("reference_methods").black_call(p["parameters"]),
            "Euler economic truth",
        )
        order_row = p["seed_ledger"][
            _index(index, "method_order", budget=budget, method="method_order")
        ]
        order = _array(arrays, cell["method_order_key"], (p["main"]["outer_runs"], 4), kind="iu")
        if cell["method_order_seed"] != order_row["seed"] or cell[
            "method_order_digest"
        ] != protocol.arrays_digest({cell["method_order_key"]: order}):
            raise ValueError("balanced method order differs from frozen seed")
        _check_balanced_order(order)
        bootstrap = p["seed_ledger"][_index(index, "bootstrap", budget=budget, method="bootstrap")][
            "seed"
        ]
        if cell["bootstrap_seed"] != bootstrap:
            raise ValueError("bootstrap seed differs from frozen ledger")
        indices = _array(
            arrays,
            cell["bootstrap_indices_key"],
            (p["bootstrap"]["resamples"], p["main"]["outer_runs"]),
            kind="iu",
        )
        if (
            np.any(indices >= p["main"]["outer_runs"])
            or np.any(indices < 0)
            or cell["bootstrap_indices_digest"]
            != protocol.arrays_digest({cell["bootstrap_indices_key"]: indices})
        ):
            raise ValueError("bootstrap integer metadata differs from original run bounds/digest")
        for name, method in cell["methods"].items():
            _check_method(p, index, method, arrays, allocation=allocation, budget=budget, name=name)
        valid = allocation["status"] in {"ready", "valid"} and all(
            method["status"] == "valid" for method in cell["methods"].values()
        )
        expected_reason = (
            None
            if valid
            else (allocation.get("reason") or allocation["status"])
            if allocation["status"] not in {"ready", "valid"}
            else "original_run_failure"
        )
        if cell["status"] != ("valid" if valid else "failed") or cell["reason"] != expected_reason:
            raise ValueError(
                "budget status differs from frozen availability/original failure roster"
            )
    wanted = [
        (case, budget, r)
        for case in range(len(p["rqmc"]["strikes"]))
        for budget in range(len(p["rqmc"]["powers"]))
        for r in p["rqmc"]["scrambles"]
    ]
    if [(c["case"], c["budget"], c["scrambles"]) for c in record["coverage_cells"]] != wanted:
        raise ValueError("full RQMC strike/power/scramble cell roster differs")
    for cell in record["coverage_cells"]:
        _check_coverage(p, index, cell, arrays)
    expected_cost_rows = [
        {
            "case": c["case"],
            "power": c["power"],
            "scrambles": c["scrambles"],
            "run": run,
            "main_s": float(seconds),
        }
        for c in record["coverage_cells"]
        for run, seconds in enumerate(arrays[c["timings_key"]][:, 5])
    ]
    _compare(record["coverage_cost_runs"], expected_cost_rows, "coverage cost observations")
    _compare(record["decision"], module("analytics").decision(record, arrays), "numerical decision")
    _compare(record["costs"], _summary_costs(record), "cost account")
    result = {
        "passed": True,
        "fixture": record["mode"] == "fixture",
        "main_runs": sum(
            len(m["runs"]) for c in record["budget_cells"] for m in c["methods"].values()
        ),
        "coverage_cells": len(record["coverage_cells"]),
        "fresh": False,
    }
    if fresh:
        result["fresh"] = _fresh(record, arrays, p, index)
    return result


def _fresh(record, arrays, p, index):
    temporary = {}
    regenerated = 0
    for budget, (cell, allocation) in enumerate(
        zip(record["budget_cells"], record["allocations"], strict=True)
    ):
        expected_order = _balanced_order(cell["method_order_seed"], p["main"]["outer_runs"])
        expected_indices = _bootstrap_indices(
            cell["bootstrap_seed"], p["main"]["outer_runs"], p["bootstrap"]["resamples"]
        )
        if not np.array_equal(
            arrays[cell["method_order_key"]], expected_order
        ) or not np.array_equal(arrays[cell["bootstrap_indices_key"]], expected_indices):
            raise ValueError("fresh frozen-seed order/bootstrap metadata differs")
        for name, method in cell["methods"].items():
            for run_number in sorted({0, p["main"]["outer_runs"] - 1}):
                saved = method["runs"][run_number]
                if saved["status"] != "complete":
                    continue
                replay = _execute_method(
                    p,
                    index,
                    allocation,
                    budget=budget,
                    run=run_number,
                    method=name,
                    beta=record["cv_beta"],
                    arrays=temporary,
                )
                if replay["status"] != "complete":
                    raise ValueError("fresh main replay failed")
                for old, new in zip(saved["levels"], replay["levels"], strict=True):
                    for field in ("counts_key", "moments_key", "negatives_key", "counters_key"):
                        a, b = arrays[old[field]], temporary[new[field]]
                        equal = (
                            np.array_equal(a, b)
                            if a.dtype.kind in "iu"
                            else np.allclose(a, b, rtol=1e-10, atol=1e-12)
                        )
                        if a.shape != b.shape or not equal:
                            raise ValueError("fresh block statistics differ")
                regenerated += 1
    for cell in record["coverage_cells"]:
        runs = (
            list(range(p["rqmc"]["outer_runs"]))
            if record["mode"] == "fixture"
            else p["fresh_review"]["coverage_replay_runs"]
        )
        contract = multilevel.GBMCall(**{**p["parameters"], "strike": cell["strike"]})
        for run in runs:
            if cell["runs"][run]["status"] != "complete":
                continue
            ids = arrays[cell["ledger_indices_key"]][run]
            rows = [p["seed_ledger"][int(i)] for i in ids]
            fresh = rqmc.rqmc_gbm_call_from_seeds(
                contract,
                power=cell["power"],
                child_seeds=[row["seed"] for row in rows],
                child_metadata=rows,
                confidence=p["rqmc"]["confidence"],
            )
            if not np.allclose(
                fresh["estimates"], arrays[cell["estimates_key"]][run], rtol=1e-10, atol=1e-12
            ):
                raise ValueError("fresh independent scramble observations differ")
            expected_endpoints = np.column_stack(
                [
                    fresh[name + "_by_scramble"]
                    for name in ("clipped_points", "uniform_zero_points", "uniform_one_points")
                ]
            )
            if not np.array_equal(expected_endpoints, arrays[cell["endpoints_key"]][run]):
                raise ValueError("fresh Sobol endpoint incidence differs")
            regenerated += 1
    # Additional independent fresh-review streams never enter the main estimator.
    for case, strike in enumerate(p["fresh_review"]["strikes"]):
        parameters = {**p["parameters"], "strike": strike}
        for level in p["main"]["levels_reserved"]:
            row = p["seed_ledger"][
                _index(index, "fresh_review", case=case, method="mlmc", level=level)
            ]
            normals = np.random.default_rng(row["seed"]).standard_normal(
                (p["fresh_review"]["paths_per_level"], p["base_steps"] * 2**level)
            )
            pair = multilevel.gbm_level_samples(
                multilevel.GBMCall(**parameters), normals, level=level, base_steps=p["base_steps"]
            )
            if case == 0 and level == 1:
                proof = record["coupling_diagnostic"]
                if not np.allclose(
                    arrays[proof["fine_normals_key"]], normals, rtol=1e-10, atol=1e-12
                ):
                    raise ValueError(
                        "fresh stored coupling stream differs from frozen diagnostic seed"
                    )
            scalar_fine = module("reference_methods").scalar_euler_payoffs(parameters, normals)
            if not np.allclose(pair["fine_payoffs"], scalar_fine, rtol=1e-10, atol=1e-12):
                raise ValueError("independent scalar fine Euler replay differs")
            if level:
                coarse = normals.reshape(len(normals), -1, 2).sum(axis=2) / math.sqrt(2)
                scalar_coarse = module("reference_methods").scalar_euler_payoffs(parameters, coarse)
                if not np.allclose(pair["coarse_payoffs"], scalar_coarse, rtol=1e-10, atol=1e-12):
                    raise ValueError("independent scalar coarse Euler replay differs")
            regenerated += 1
    return {
        "passed": True,
        "replayed_groups": regenerated,
        "independent_paths_per_level": p["fresh_review"]["paths_per_level"],
        "main_pooled": False,
        "timing_reproduction_required": False,
    }


def save_fresh_receipt(output: Path, record: dict, checks: dict, seconds: float) -> Path:
    """Append a bound reproducibility-cost receipt without changing original results."""
    if (
        not math.isfinite(seconds)
        or seconds < 0
        or checks.get("passed") is not True
        or not checks.get("fresh")
    ):
        raise ValueError("successful fresh checks and actual nonnegative seconds required")
    protocol = module("protocol")
    receipt = {
        "schema": "RB-F08-fresh-check-v1",
        "reference_record_digest": protocol.json_digest(record),
        "protocol_frozen_digest": record["protocol"].get("frozen", {}).get("digest"),
        "seconds": seconds,
        "checks": checks,
        "scope": "saved evidence load/check and selected fresh replay; separate research reproducibility cost",
    }
    ordinal = 1
    while True:
        path = Path(output) / (
            "fresh_check.json" if ordinal == 1 else f"fresh_check_{ordinal:03d}.json"
        )
        try:
            with path.open("x") as stream:
                json.dump(_json(receipt), stream, indent=2, allow_nan=False)
                stream.write("\n")
            return path
        except FileExistsError:
            ordinal += 1


def fresh_receipts(output: Path, record: dict) -> dict:
    """Validate all bound fresh receipts and sum actual research verification costs."""
    digest = module("protocol").json_digest(record)
    frozen = record["protocol"].get("frozen", {}).get("digest")
    receipts = []
    for path in sorted(Path(output).glob("fresh_check*.json")):
        receipt = json.loads(path.read_text())
        if (
            receipt.get("schema") != "RB-F08-fresh-check-v1"
            or receipt.get("reference_record_digest") != digest
            or receipt.get("protocol_frozen_digest") != frozen
            or receipt.get("checks", {}).get("passed") is not True
            or not isinstance(receipt.get("seconds"), (int, float))
            or not math.isfinite(receipt["seconds"])
            or receipt["seconds"] < 0
        ):
            raise ValueError("fresh cost receipt differs from original reference/protocol")
        receipts.append(
            {"file": path.name, "seconds": float(receipt["seconds"]), "checks": receipt["checks"]}
        )
    return {
        "receipts": receipts,
        "total_s": math.fsum(item["seconds"] for item in receipts),
        "pending": not bool(receipts),
        "main_or_cold_cost": False,
    }


def main(argv=None):
    """Run a reviewed main once, or check saved evidence with optional fresh replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("main", "fixture"), default="main")
    parser.add_argument("--check", type=Path)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.check is not None:
        if args.protocol is not None or args.output is not None:
            parser.error("--check is separate from execution output/protocol")
        start = perf_counter()
        record, arrays = load_result(args.check)
        result = check_record(record, arrays, fresh=args.fresh)
        if args.fresh:
            path = save_fresh_receipt(args.check, record, result, perf_counter() - start)
            result["receipt"] = str(path)
    else:
        if args.protocol is None or args.output is None or args.fresh:
            parser.error("execution requires --protocol and --output; --fresh belongs to --check")
        record = run_reference(args.output, protocol_path=args.protocol, mode=args.mode)
        result = {"saved": str(args.output), "mode": record["mode"], "decision": record["decision"]}
    print(json.dumps(_json(result), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
