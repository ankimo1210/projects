#!/usr/bin/env python3
"""Additional RB-F05 verification support; not a primary financial source.

The fresh roster/N were fixed by the parent before main-result inspection.
--generate requires a completed frozen main; --check never draws, fits or trains.
All canonical financial sources remain immutable. Output does not alter main
labels, model selection, protocol, or the immutable main study record.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import numpy as np

SOURCE_DEFAULT = Path(
    "/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity"
)
MINUTES = (1, 5, 30, 60, 240, 390)
N = 1048576
BLOCK = 16384
SCALES = (0.02, 0.05, 0.10)
RAW = ("price", "pw_delta", "lr_delta", "lrpw_gamma", "lr2_gamma", "naive_gamma")
METHODS = (
    "conditioned_price",
    "conditioned_delta",
    "conditioned_gamma",
    *RAW,
    "crn_delta_0.02",
    "crn_gamma_0.02",
    "crn_delta_0.05",
    "crn_gamma_0.05",
    "crn_delta_0.10",
    "crn_gamma_0.10",
)
FILES = ("fresh_check.json", "fresh_arrays.npz", "fresh_cost.json")
ROSTER = [
    {
        "id": i,
        "remaining_minutes": minute,
        "event": event,
        "spot": 100.0,
        "strike": 100.0,
        "seed_ids": {k: f"fresh/raw/{i}/{k}" for k in ("count", "jump", "brown")},
    }
    for i, (minute, event) in enumerate((m, e) for m in MINUTES for e in (False, True))
]
FIXED = {
    "sample_count": N,
    "block_size": BLOCK,
    "normal_draw_policy": "full_N_diagnostic",
    "roster": ROSTER,
    "method_order": list(METHODS),
    "crn_scaled_bumps": list(SCALES),
    "se_multiple": 6.0,
    "absolute_tolerance": [1e-7, 1e-9, 1e-9],
    "relative_tolerance": [1e-10, 1e-10, 1e-9],
    "nmax": 8,
    "epsabs": 1e-10,
    "epsrel": 1e-10,
    "tighten_factor": 4,
}
_MOD = {}


def modules(source=SOURCE_DEFAULT):
    source = Path(source).resolve()
    key = str(source)
    if key not in _MOD:
        path = source / "build_reference.py"
        spec = importlib.util.spec_from_file_location("_rbf05_fresh_support_runner", path)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        from hullkit import _short_maturity_teachers as core

        _MOD[key] = (
            runner,
            runner.module("protocol"),
            runner.module("analytics"),
            runner.module("reference_methods"),
            core,
        )
    return _MOD[key]


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def dump(path, value):
    Path(path).write_text(json.dumps(plain(value), indent=2, allow_nan=False))


def close(actual, expected, name, *, atol=1e-11, rtol=1e-8):
    a, e = np.asarray(actual), np.asarray(expected)
    if a.shape != e.shape:
        raise ValueError(f"{name}: changed shape")
    if a.dtype.kind in "biu" or e.dtype.kind in "biu":
        ok = np.array_equal(a, e)
    else:
        ok = np.allclose(a, e, atol=atol, rtol=rtol, equal_nan=True)
    if not ok:
        raise ValueError(f"{name}: saved values changed")


def tree_close(actual, expected, name):
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(f"{name}: changed keys")
        for k in expected:
            tree_close(actual[k], expected[k], f"{name}/{k}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{name}: changed list")
        for i, item in enumerate(expected):
            tree_close(actual[i], item, f"{name}/{i}")
    elif expected is None or isinstance(expected, (str, bool)):
        if actual != expected:
            raise ValueError(f"{name}: changed discrete metadata")
    elif isinstance(expected, (float, int)):
        close(actual, expected, name)
    else:
        close(actual, expected, name)


def _moment_block(values):
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("finite joint values with original block denominator required")
    origin = values[0]
    shifted = values - origin
    average = shifted.mean(axis=0)
    deviations = shifted - average
    return len(values), origin + average, deviations.T @ deviations


def _merge(left, right):
    if left is None:
        return right
    n, mean, m2 = left
    k, other, other_m2 = right
    d = other - mean
    return n + k, mean + d * (k / (n + k)), m2 + other_m2 + np.outer(d, d) * (n * k / (n + k))


def _finish(accumulator):
    n, mean, m2 = accumulator
    covariance = m2 / (n - 1)
    return {
        "n": int(n),
        "mean": mean,
        "m2": m2,
        "covariance": covariance,
        "se": np.sqrt(np.maximum(np.diag(m2), 0) / (n * (n - 1))),
    }


def _block_sizes(n, block):
    sizes = [min(block, n - i) for i in range(0, n, block)]
    if len(sizes) > 1 and sizes[-1] == 1:
        tail = sizes.pop()
        sizes[-1] += tail
    return sizes


def summarize_samples(spot, strike, state, parameters, counts, zj, zb, core, *, block=BLOCK):
    """Use supplied original primitives only; no RNG and no sample exclusion."""
    counts, zj, zb = np.asarray(counts), np.asarray(zj), np.asarray(zb)
    n = len(counts)
    if (
        counts.shape != (n,)
        or zj.shape != (n,)
        or zb.shape != (n,)
        or n < 2
        or counts.dtype.kind not in "iu"
        or np.any(counts < 0)
        or not np.isfinite(zj).all()
        or not np.isfinite(zb).all()
    ):
        raise ValueError("invalid full original count/mark/Brownian primitives")
    discount = math.exp(-parameters.rate * state.carry_years)
    widths = spot * math.sqrt(state.variance) * np.asarray(SCALES)
    accumulator = None
    nonzero = np.zeros(6, dtype=np.int64)
    crossings = np.zeros(3, dtype=np.int64)
    start = 0
    for size in _block_sizes(n, block):
        stop = start + size
        ns, js, bs = counts[start:stop], zj[start:stop], zb[start:stop]
        conditioned = core.conditional_values(spot, strike, state, parameters, ns, js)
        raw = core.path_values(spot, strike, state, parameters, ns, bs, js)
        raw_matrix = np.column_stack([raw[name] for name in RAW])
        multiplier = raw["terminal_spot"] / spot
        columns = [conditioned, raw_matrix]
        nonzero += np.count_nonzero(raw_matrix, axis=0)
        for i, h in enumerate(widths):
            lower_spot = (spot - h) * multiplier
            upper_spot = (spot + h) * multiplier
            lower = discount * np.maximum(lower_spot - strike, 0)
            upper = discount * np.maximum(upper_spot - strike, 0)
            columns.append(
                np.column_stack(
                    (
                        (upper - lower) / (2 * h),
                        (upper + lower - 2 * raw["price"]) / (h * h),
                    )
                )
            )
            crossings[i] += np.count_nonzero((lower_spot < strike) & (upper_spot > strike))
        matrix = np.column_stack(columns)
        accumulator = _merge(accumulator, _moment_block(matrix))
        start = stop
    result = _finish(accumulator)
    result.update(
        active_count=int(np.count_nonzero(counts)),
        zero_count=int(np.count_nonzero(counts == 0)),
        nonzero_raw=nonzero,
        crossings=crossings,
        finite_steps=widths,
    )
    return result


def references(spot, strike, state, parameters, ref):
    """Independent count mixture and normal-density integrals; FD bias retained."""
    mixture = ref.independent_mixture(spot, strike, state, parameters, nmax=8)
    quad = ref.density_quad(spot, strike, state, parameters, nmax=8, epsabs=1e-10, epsrel=1e-10)
    tight = ref.density_quad(
        spot, strike, state, parameters, nmax=8, epsabs=2.5e-11, epsrel=2.5e-11
    )
    fds = ref.spot_finite_differences(
        spot,
        strike,
        state,
        parameters,
        nmax=8,
        relative_steps=tuple(scale * math.sqrt(state.variance) for scale in reversed(SCALES)),
    )
    by_scale = list(reversed(fds))
    values = np.asarray(mixture["values"])
    tolerance = np.asarray(FIXED["absolute_tolerance"]) + np.asarray(
        FIXED["relative_tolerance"]
    ) * np.abs(values)
    primary_messages = [
        message
        for item in (quad, tight)
        for term in item["terms"]
        if term["weight"] > 0
        for message in term.get("primary_quadrature_messages", [])
    ]
    primary_passed = bool(
        np.all(np.abs(quad["values"] - values) <= tolerance)
        and np.all(np.abs(tight["values"] - quad["values"]) <= tolerance / 4)
        and np.all(np.maximum(quad["error_estimates"], tight["error_estimates"]) <= tolerance / 4)
        and np.all(mixture["tail_bounds"] <= tolerance / 4)
        and quad["status"] != "nonfinite"
        and tight["status"] != "nonfinite"
        and not primary_messages
    )
    fd_values = np.asarray([[fd["delta"], fd["gamma"]] for fd in by_scale])
    return plain(
        {
            "values": values,
            "tail_bounds": mixture["tail_bounds"],
            "status": mixture["status"],
            "tolerance": tolerance,
            "quad_values": quad["values"],
            "quad_errors": quad["error_estimates"],
            "tight_values": tight["values"],
            "tight_errors": tight["error_estimates"],
            "quad_status": quad["status"],
            "tight_status": tight["status"],
            "quad_messages": quad["quadrature_messages"],
            "tight_messages": tight["quadrature_messages"],
            "quad_lr_gamma": quad["lr_gamma"],
            "quad_lr_gamma_error": quad["lr_gamma_error_estimate"],
            "tight_lr_gamma": tight["lr_gamma"],
            "tight_lr_gamma_error": tight["lr_gamma_error_estimate"],
            "finite_steps": [fd["step"] for fd in by_scale],
            "finite_values": fd_values,
            "finite_h_bias": fd_values - values[1:],
            "primary_passed": primary_passed,
            "scope": "independent ordinary Poisson mixture and normal-density payoff integral; finite-h CRN target differs from true Greeks",
            "error_scope": "quadrature errors are numerical estimates; mixture omitted-tail bounds are separate",
        }
    )


def diagnostics(moment, reference, state):
    truth = np.asarray(reference["values"])
    finite = np.asarray(reference["finite_values"])
    targets = np.r_[truth, truth[[0, 1, 1, 2, 2, 2]], finite.reshape(-1)]
    components = [0, 1, 2, 0, 1, 1, 2, 2, 2, 1, 2, 1, 2, 1, 2]
    tolerance = np.asarray(reference["tolerance"])[components]
    mean, se = moment["mean"], moment["se"]
    supported = np.abs(mean - targets) <= 6 * se + tolerance
    rows = []
    for i, name in enumerate(METHODS):
        if name == "naive_gamma":
            status, ok = "negative_control", False
        elif i < 3 and state.jump_mean_count == 0:
            status = "analytic_deterministic" if supported[i] else "unsupported"
            ok = bool(supported[i])
        elif (
            (i < 3 and moment["active_count"] == 0)
            or (i in (10, 12, 14) and moment["crossings"][(i - 10) // 2] == 0)
            or (se[i] == 0 and abs(mean[i] - targets[i]) > tolerance[i])
        ):
            status, ok = "diagnostic_inconclusive", False
        else:
            status = "supported" if supported[i] else "unsupported"
            ok = bool(supported[i])
        rows.append(
            {
                "method": name,
                "original_n": moment["n"],
                "mean": float(mean[i]),
                "se": float(se[i]),
                "target": float(targets[i]),
                "difference": float(mean[i] - targets[i]),
                "tolerance": float(tolerance[i]),
                "criterion": "abs(mean-target)<=6*SE+fixed_abs+fixed_rel*abs(target)",
                "supported": ok,
                "status": status,
            }
        )
    return rows


def _record_keys(i):
    return {
        k: f"fresh_{i}_{k}"
        for k in ("counts", "z_jump", "z_brown", "mean", "m2", "covariance", "se")
    }


def _draw_metadata(state, n):
    return {
        "original_n": n,
        "normal_draw_policy": "full_N_diagnostic",
        "count_outputs": n,
        "count_random_variates": n if state.jump_mean_count > 0 else 0,
        "jump_normal_outputs": n,
        "brownian_normal_outputs": n,
        "requested_stochastic_variates": 3 * n if state.jump_mean_count > 0 else 2 * n,
        "count_status": "IID_poisson" if state.jump_mean_count > 0 else "deterministic_zero",
        "conditioned_effective_observed_mc_n": n if state.jump_mean_count > 0 else 0,
        "conditioned_aggregation_n": n,
        "scope": "fresh full-N raw diagnostic, distinct from active-only main compact teachers; Poisson(0) outputs are deterministic",
        "engine_scope": "requested variates, not a count of primitive generator words or rejection retries",
    }


def _source_binding(main, protocol):
    current = protocol.source_registry(require_complete=True)
    if (
        current != main["source_registry"]
        or current != main["protocol"]["frozen"]["source_registry"]
    ):
        raise ValueError("frozen financial source registry changed")
    return current


def _declared_plan(directory):
    plan = json.loads((Path(directory) / "fresh_plan.json").read_text())
    cases = [
        {
            "index": row["id"],
            "spot": row["spot"],
            "minutes": row["remaining_minutes"],
            "event": row["event"],
            "seeds": row["seed_ids"],
        }
        for row in ROSTER
    ]
    if (
        plan.get("schema") != "RB-F05-short-fresh-plan-v1"
        or plan.get("sample_count") != N
        or plan.get("normal_draw_policy") != "full_N_diagnostic"
        or plan.get("cases") != cases
    ):
        raise ValueError("parent's pre-main fixed fresh plan disagrees with support design")
    return plan


def _main_gate(directory, source):
    runner, protocol, _analytics, _ref, _core = modules(source)
    main, main_arrays = runner.load_result(directory)
    if main.get("mode") != "main" or not main.get("complete") or len(main.get("fits", [])) != 6:
        raise ValueError("completed six-original-fit frozen main required before fresh generation")
    protocol.validate_protocol(main["protocol"], require_frozen=True)
    protocol.verify_frozen_evidence(main["protocol"])
    _source_binding(main, protocol)
    runner.check_record(main, main_arrays)
    del main_arrays
    if main["protocol"]["contract"]["strike"] != 100:
        raise ValueError("predeclared fresh spot/strike requires K100")
    if main["protocol"]["pilot"]["crn_scaled_bumps"] != list(SCALES):
        raise ValueError("fresh fixed bump contract disagrees with frozen pilot")
    if (
        main["protocol"]["pilot"]["absolute_reference_tolerance"] != FIXED["absolute_tolerance"]
        or main["protocol"]["pilot"]["relative_reference_tolerance"] != FIXED["relative_tolerance"]
        or main["protocol"]["pilot"]["se_multiple"] != 6
        or main["protocol"]["reference_nmax"] != 8
    ):
        raise ValueError("fresh fixed tolerance contract disagrees with frozen pilot")
    return main


def _charge(expenses, identity, category, seconds, scope):
    expenses.append(
        {
            "id": identity,
            "category": category,
            "charged": True,
            "parent": None,
            "seconds": float(seconds),
            "scope": scope,
        }
    )


def generate(directory, *, source=SOURCE_DEFAULT):
    """Actual fresh sampling; parent authorization/main completion required."""
    started = perf_counter()
    directory = Path(directory)
    if any((directory / name).exists() for name in FILES):
        raise FileExistsError("fresh immutable verification evidence already exists")
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise ValueError("single-thread BLAS environment required")
    declared_plan = _declared_plan(directory)
    main = _main_gate(directory, source)  # all gates happen before first RNG
    _runner, protocol, analytics, ref, core = modules(source)
    proof = directory / "fresh_support.py"
    support_bytes = Path(__file__).read_bytes()
    if proof.exists() and proof.read_bytes() != support_bytes:
        raise FileExistsError("different fresh support source proof already exists")
    if not proof.exists():
        proof.write_bytes(support_bytes)
    expenses = []
    _charge(
        expenses,
        "main_gate",
        "validation",
        perf_counter() - started,
        "read/replay main and actual frozen pilot plus complete source binding",
    )
    record = {
        "schema": "RB-F05-short-fresh-v1",
        "phase": "additional_verification",
        "main_record_digest": protocol.json_digest(main),
        "protocol_digest": main["protocol_digest"],
        "source_registry": main["source_registry"],
        "support_script_sha256": hashlib.sha256(support_bytes).hexdigest(),
        "support_source_filename": "fresh_support.py",
        "declared_plan": declared_plan,
        "declared_plan_digest": protocol.json_digest(declared_plan),
        "fixed_design": FIXED,
        "original_case_count": 12,
        "cases": [],
        "expenses": expenses,
        "accepted": False,
        "main_selection_changed": False,
        "main_labels_pooled": False,
        "scope": "additional fixed fresh estimator verification, never the original study's generation source",
        "limits": [
            "6SE is a diagnostic comparison, not a simultaneous confidence guarantee",
            "ordinary mixture and density integration share the specified synthetic model, not market validation",
            "unknown/unsupported and negative-control original slots remain",
            "finite-h CRN checked at finite-h target; true Greek finite-h bias is separately retained",
            "full-N fresh primitive storage intentionally differs from main active-only compact sampling",
        ],
    }
    arrays = {}
    p = main["protocol"]
    params = analytics.parameters(p)
    for definition in ROSTER:
        i = definition["id"]
        keys = _record_keys(i)
        state = analytics.states(
            [[100.0, definition["remaining_minutes"] * 60, int(definition["event"])]], p
        )[0]
        seeds = {
            kind: protocol.seed_for(p, identity)
            for kind, identity in definition["seed_ids"].items()
        }
        row = dict(
            definition, state=asdict(state), parameters=asdict(params), seeds=seeds, keys=keys
        )
        # Full physical streams: no conditioning/rare-event stratification or replacement.
        before = perf_counter()
        counts = np.random.default_rng(seeds["count"]).poisson(state.jump_mean_count, N)
        zj = np.random.default_rng(seeds["jump"]).standard_normal(N)
        zb = np.random.default_rng(seeds["brown"]).standard_normal(N)
        _charge(
            expenses,
            f"fresh/{i}/draw",
            "draw",
            perf_counter() - before,
            "full original count outputs and separate full-N mark/Brownian normal streams",
        )
        arrays[keys["counts"]] = counts
        arrays[keys["z_jump"]] = zj
        arrays[keys["z_brown"]] = zb
        row["draws"] = _draw_metadata(state, N)
        before = perf_counter()
        row["reference"] = references(100.0, 100.0, state, params, ref)
        _charge(
            expenses,
            f"fresh/{i}/reference",
            "reference",
            perf_counter() - before,
            "ordinary Poisson mixture, two independent-density tolerances and deterministic finite-h targets",
        )
        before = perf_counter()
        try:
            moment = summarize_samples(100.0, 100.0, state, params, counts, zj, zb, core)
            for name in ("mean", "m2", "covariance", "se"):
                arrays[keys[name]] = moment[name]
            row.update(
                status="observed",
                n=moment["n"],
                active_count=moment["active_count"],
                zero_count=moment["zero_count"],
                nonzero_raw=plain(moment["nonzero_raw"]),
                crossings=plain(moment["crossings"]),
                finite_steps=plain(moment["finite_steps"]),
                methods=diagnostics(moment, row["reference"], state),
            )
        except (ValueError, OverflowError, FloatingPointError) as exc:
            row.update(
                status="unknown",
                original_n=N,
                failure={"type": type(exc).__name__, "message": str(exc)},
                methods=[
                    {
                        "method": name,
                        "original_n": N,
                        "status": "unknown",
                        "supported": False,
                        "reason": "case computation failure",
                    }
                    for name in METHODS
                ],
            )
        _charge(
            expenses,
            f"fresh/{i}/estimator",
            "estimator",
            perf_counter() - before,
            "conditioned3/raw6/3hCRN original-N joint covariance in saved fixed blocks",
        )
        record["cases"].append(row)
    record["summary"] = _summary(record)
    record["numeric_arrays_digest"] = protocol.arrays_digest(arrays)
    before = perf_counter()
    record["saved_check"] = check_record(record, arrays, main, source=source, check_costs=False)
    _charge(
        expenses,
        "saved_replay",
        "validation",
        perf_counter() - before,
        "read-only re-evaluation of all original fresh primitives/references/statistics",
    )
    record["categorized_cost"] = analytics.expense_totals(expenses)
    before = perf_counter()
    np.savez_compressed(directory / "fresh_arrays.npz", **arrays)
    dump(directory / "fresh_check.json", record)
    serialization_s = perf_counter() - before
    receipt = {
        "schema": "RB-F05-short-fresh-cost-v1",
        "record_digest": protocol.json_digest(main),
        "fresh_record_digest": protocol.json_digest(record),
        "expense_id": "fresh",
        "seconds": perf_counter() - started,
        "categorized_before_serialization_s": record["categorized_cost"]["measured_seconds"],
        "serialization_s": serialization_s,
        "npz_bytes": (directory / "fresh_arrays.npz").stat().st_size,
        "scope": "whole supplemental fresh function through evidence save; fresh-cost receipt write excluded",
        "charged_once": True,
        "main_only_cost": False,
        "cold_pricing_cost": False,
    }
    dump(directory / "fresh_cost.json", receipt)
    return record, receipt


def _summary(record):
    statuses = {}
    for row in record["cases"]:
        for method in row["methods"]:
            name = method["status"]
            statuses[name] = statuses.get(name, 0) + 1
    return {
        "original_cases": 12,
        "original_method_slots": 12 * len(METHODS),
        "observed_cases": sum(row["status"] == "observed" for row in record["cases"]),
        "unknown_cases": sum(row["status"] == "unknown" for row in record["cases"]),
        "method_status_counts": statuses,
        "primary_reference_supported_cases": sum(
            row["reference"]["primary_passed"] for row in record["cases"]
        ),
        "scope": "negative_control/unsupported/inconclusive remain in original 180 slots",
    }


def check_record(record, arrays, main, *, source=SOURCE_DEFAULT, check_costs=True):
    """Replay saved original primitives; never invoke an RNG, fit or optimizer."""
    _runner, protocol, analytics, ref, core = modules(source)
    if (
        record.get("schema") != "RB-F05-short-fresh-v1"
        or record.get("phase") != "additional_verification"
        or record.get("fixed_design") != FIXED
        or record.get("original_case_count") != 12
        or record.get("accepted") is not False
        or record.get("main_labels_pooled") is not False
        or record.get("main_selection_changed") is not False
        or record.get("main_record_digest") != protocol.json_digest(main)
        or record.get("protocol_digest") != main["protocol_digest"]
        or record.get("source_registry") != _source_binding(main, protocol)
    ):
        raise ValueError("fresh study binding or fixed original scope changed")
    if len(record["cases"]) != 12:
        raise ValueError("original fresh cases were dropped")
    expected_keys = set()
    params = analytics.parameters(main["protocol"])
    for row, definition in zip(record["cases"], ROSTER, strict=True):
        i = definition["id"]
        for k, v in definition.items():
            if row.get(k) != v:
                raise ValueError("fresh original case roster changed")
        keys = _record_keys(i)
        if row["keys"] != keys:
            raise ValueError("fresh primitive/moment array binding changed")
        state = analytics.states(
            [[100.0, definition["remaining_minutes"] * 60, int(definition["event"])]],
            main["protocol"],
        )[0]
        tree_close(row["state"], asdict(state), "clock")
        tree_close(row["parameters"], asdict(params), "parameters")
        expected_seeds = {
            kind: protocol.seed_for(main["protocol"], identity)
            for kind, identity in definition["seed_ids"].items()
        }
        if row["seeds"] != expected_seeds or row["draws"] != _draw_metadata(state, N):
            raise ValueError("saved reserved seed/full-N draw role changed")
        counts, zj, zb = (arrays[keys[name]] for name in ("counts", "z_jump", "z_brown"))
        expected_keys.update(keys[name] for name in ("counts", "z_jump", "z_brown"))
        if counts.shape != (N,) or zj.shape != (N,) or zb.shape != (N,):
            raise ValueError("original fresh denominator/primitive shape changed")
        if (
            counts.dtype.kind not in "iu"
            or np.any(counts < 0)
            or not np.isfinite(zj).all()
            or not np.isfinite(zb).all()
        ):
            raise ValueError("saved fresh primitive type or values invalid")
        if state.jump_mean_count == 0 and np.any(counts != 0):
            raise ValueError("Poisson(0) deterministic outputs changed")
        independent = references(100.0, 100.0, state, params, ref)
        tree_close(row["reference"], independent, "independent-reference")
        try:
            moment = summarize_samples(100.0, 100.0, state, params, counts, zj, zb, core)
        except (ValueError, OverflowError, FloatingPointError) as exc:
            if row["status"] != "unknown" or row.get("original_n") != N:
                raise ValueError("fresh failed original case was promoted") from exc
            if row["failure"] != {"type": type(exc).__name__, "message": str(exc)}:
                raise ValueError("saved failure changed") from exc
            expected_methods = [
                {
                    "method": name,
                    "original_n": N,
                    "status": "unknown",
                    "supported": False,
                    "reason": "case computation failure",
                }
                for name in METHODS
            ]
            tree_close(row["methods"], expected_methods, "failed-methods")
        else:
            if row["status"] != "observed":
                raise ValueError("finite observed case was mislabeled unknown")
            for name in ("mean", "m2", "covariance", "se"):
                expected_keys.add(keys[name])
                close(arrays[keys[name]], moment[name], f"case{i}/{name}")
            for name in (
                "n",
                "active_count",
                "zero_count",
                "nonzero_raw",
                "crossings",
                "finite_steps",
            ):
                close(row[name], moment[name], f"case{i}/{name}")
            tree_close(
                row["methods"], diagnostics(moment, independent, state), "diagnostic-methods"
            )
    if set(arrays) != expected_keys:
        raise ValueError("fresh plain-array closed roster changed")
    if record["numeric_arrays_digest"] != protocol.arrays_digest(arrays):
        raise ValueError("fresh original primitive provenance identity changed")
    tree_close(record["summary"], _summary(record), "summary")
    if check_costs:
        expected = {"main_gate", "saved_replay"} | {
            f"fresh/{i}/{kind}" for i in range(12) for kind in ("draw", "reference", "estimator")
        }
        if (
            len(record["expenses"]) != len(expected)
            or {x["id"] for x in record["expenses"]} != expected
        ):
            raise ValueError("fresh measured expense closed roster changed")
        for receipt in record["expenses"]:
            kind = receipt["id"].rsplit("/", 1)[-1]
            category = kind if kind in ("draw", "reference", "estimator") else "validation"
            if (
                receipt["category"] != category
                or receipt["charged"] is not True
                or receipt["parent"] is not None
                or not isinstance(receipt["seconds"], (int, float))
                or not math.isfinite(receipt["seconds"])
                or receipt["seconds"] < 0
            ):
                raise ValueError("fresh expense category/charge/finite measured seconds changed")
        tree_close(
            record["categorized_cost"], analytics.expense_totals(record["expenses"]), "costs"
        )
    return {
        "passed": True,
        "original_cases": 12,
        "original_method_slots": 180,
        "replay_rng": False,
        "optimizer_or_training": False,
        "scope": "saved primitive/statistical consistency, not all-estimator support or teaching acceptance",
    }


def load_fresh(directory):
    directory = Path(directory)
    record = json.loads((directory / "fresh_check.json").read_text())
    with np.load(directory / "fresh_arrays.npz", allow_pickle=False) as saved:
        arrays = {name: saved[name].copy() for name in saved.files}
    return record, arrays


def check_saved(directory, *, source=SOURCE_DEFAULT):
    runner, protocol, _analytics, _ref, _core = modules(source)
    main, main_arrays = runner.load_result(directory)
    runner.check_record(main, main_arrays)
    del main_arrays
    record, arrays = load_fresh(directory)
    plan = _declared_plan(directory)
    if (
        record["declared_plan"] != plan
        or record["declared_plan_digest"] != protocol.json_digest(plan)
        or record["support_source_filename"] != "fresh_support.py"
        or record["support_script_sha256"]
        != hashlib.sha256((Path(directory) / "fresh_support.py").read_bytes()).hexdigest()
    ):
        raise ValueError("fresh declared plan or support source proof identity changed")
    result = check_record(record, arrays, main, source=source)
    cost = json.loads((Path(directory) / "fresh_cost.json").read_text())
    if (
        cost.get("schema") != "RB-F05-short-fresh-cost-v1"
        or cost.get("record_digest") != protocol.json_digest(main)
        or cost.get("fresh_record_digest") != protocol.json_digest(record)
        or cost.get("expense_id") != "fresh"
        or cost.get("charged_once") is not True
        or cost.get("main_only_cost") is not False
        or cost.get("cold_pricing_cost") is not False
        or not math.isfinite(cost["seconds"])
        or cost["seconds"] < 0
        or not math.isfinite(cost["serialization_s"])
        or cost["serialization_s"] < 0
        or cost["npz_bytes"] != (Path(directory) / "fresh_arrays.npz").stat().st_size
    ):
        raise ValueError("fresh external receipt binding changed")
    close(
        cost["categorized_before_serialization_s"],
        record["categorized_cost"]["measured_seconds"],
        "fresh category sum",
    )
    if (
        cost["seconds"] + 1e-9
        < cost["categorized_before_serialization_s"] + cost["serialization_s"]
    ):
        raise ValueError("fresh whole-function seconds smaller than disjoint measured components")
    result.update(cost_receipt_verified=True, fresh_seconds=cost["seconds"])
    return result


def resolved_costs(directory, main, *, source=SOURCE_DEFAULT, external_paths=None):
    """Display overlay only: never rewrite immutable pending5 main accounting.

    Provisional external schema for cold_import/archive_load/pilot_freeze:
    RB-F05-short-external-cost-v1, record_digest, expense_id, seconds, scope,
    charged_once=True, disjoint_from_main=True. Root may supply custom paths.
    This generic interface is not part of a frozen financial source/API.
    """
    runner, protocol, _analytics, _ref, _core = modules(source)
    directory = Path(directory)
    identity = protocol.json_digest(main)
    pending = set(main["costs"]["categorized"]["pending_ids"])
    if pending != {"serialization", "cold_import", "archive_load", "pilot_freeze", "fresh"}:
        raise ValueError("immutable main pending roster changed")
    resolved = {}
    serialization = runner.serialization_receipt(directory, main)
    if not serialization["pending"]:
        resolved["serialization"] = serialization
    fresh_path = directory / "fresh_cost.json"
    if fresh_path.exists():
        receipt = json.loads(fresh_path.read_text())
        fresh = json.loads((directory / "fresh_check.json").read_text())
        if (
            receipt.get("schema") != "RB-F05-short-fresh-cost-v1"
            or receipt.get("record_digest") != identity
            or receipt.get("fresh_record_digest") != protocol.json_digest(fresh)
            or receipt.get("expense_id") != "fresh"
            or receipt.get("charged_once") is not True
            or receipt.get("main_only_cost") is not False
            or receipt.get("cold_pricing_cost") is not False
        ):
            raise ValueError("fresh display receipt binding changed")
        resolved["fresh"] = receipt
    for name, path in (external_paths or {}).items():
        if name not in {"cold_import", "archive_load", "pilot_freeze"}:
            raise ValueError("external cost is not one of the remaining pending categories")
        path = Path(path)
        if not path.exists():
            continue
        receipt = json.loads(path.read_text())
        if (
            receipt.get("schema") != "RB-F05-short-external-cost-v1"
            or receipt.get("record_digest") != identity
            or receipt.get("expense_id") != name
            or receipt.get("charged_once") is not True
            or receipt.get("disjoint_from_main") is not True
            or not receipt.get("scope")
        ):
            raise ValueError("external receipt changed binding/category/disjoint scope")
        resolved[name] = receipt
    for name, receipt in resolved.items():
        seconds = receipt.get("seconds")
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError(f"external {name} measured seconds invalid")
    unresolved = sorted(pending - set(resolved))
    original = main["costs"]["main_only_s"]
    accumulated = original + sum(r["seconds"] for r in resolved.values())
    cold_required = {"serialization", "cold_import", "archive_load", "pilot_freeze"}
    cold = (
        original + sum(resolved[k]["seconds"] for k in cold_required)
        if cold_required <= set(resolved)
        else None
    )
    return {
        "main_record_digest": identity,
        "raw_main_costs_unchanged": True,
        "raw_main_pending_ids": sorted(pending),
        "resolved_receipts": resolved,
        "unresolved_pending_ids": unresolved,
        "recorded_main_categories_s": original,
        "recorded_research_categories_plus_resolved_external_s": accumulated,
        "recorded_cold_research_pipeline_s": cold,
        "fresh_s": resolved.get("fresh", {}).get("seconds"),
        "complete_cost_accounting": not unresolved,
        "scope": "display overlay of disjoint measured categories; not CLI wall or mathematical minimum startup",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--resolved-costs", action="store_true")
    args = parser.parse_args(argv)
    if args.generate:
        record, receipt = generate(args.directory, source=args.source)
        print(json.dumps({"summary": record["summary"], "receipt": receipt}, indent=2))
    elif args.check:
        # Install a sampling trap after imports. Seed lookup never invents streams.
        def forbidden(*a, **kw):
            raise RuntimeError("fresh saved-only checker attempted RNG generation")

        modules(args.source)
        np.random.default_rng = forbidden
        print(json.dumps(check_saved(args.directory, source=args.source), indent=2))
    else:
        runner = modules(args.source)[0]
        record, arrays = runner.load_result(args.directory)
        runner.check_record(record, arrays)
        print(json.dumps(resolved_costs(args.directory, record, source=args.source), indent=2))


if __name__ == "__main__":
    main()
