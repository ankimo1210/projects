"""Fixed short-call study runner and deterministic saved-only numerical checker.

Main observations are forbidden until the complete financial registry, actual
numeric pilot and independent approval are frozen. Smoke uses explicit reduced
rosters and is never accepted. JSON holds metadata; non-object NPZ arrays hold
original observations, joint moments, plain weights and whole-call outputs.
"""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from copy import deepcopy
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _short_maturity_teachers as core

DIRECTORY = Path(__file__).resolve().parent
_MODULES = {}
SMOKE_TEST_IDS = [8, 29, 0, 21, 50, 71, 134, 155, 260, 281, 314, 335]


def module(name):
    """Load research siblings without installing a public package."""
    if name not in _MODULES:
        spec = importlib.util.spec_from_file_location(
            f"short_study_{name}", DIRECTORY / f"{name}.py"
        )
        result = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = result
        spec.loader.exec_module(result)
        _MODULES[name] = result
    return _MODULES[name]


def _learner():
    # Deliberately after the lifecycle gate: no Torch import before main approval.
    from deep_hedge_price import _short_maturity_dml

    return _short_maturity_dml


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _put(arrays, key, value):
    if key in arrays:
        raise ValueError(f"duplicate array key: {key}")
    a = np.asarray(value)
    if a.dtype.hasobject:
        raise ValueError("plain non-object arrays required")
    arrays[key] = a.copy()
    return key


def _charge(expenses, identity, category, seconds, scope):
    expenses.append(
        {"id": identity, "category": category, "seconds": seconds, "charged": True, "scope": scope}
    )


def _close(actual, expected, label, *, atol=1e-10, rtol=1e-8):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape:
        raise ValueError(f"{label} changed shape")
    if a.dtype.kind in "USbiu" and b.dtype.kind in "USbiu":
        same = np.array_equal(a, b)
    else:
        same = np.allclose(a, b, atol=atol, rtol=rtol, equal_nan=True)
    if not same:
        raise ValueError(f"{label} changed or disagrees")


def _nested_close(actual, expected, label):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{label} changed keys")
        for key in expected:
            _nested_close(actual[key], expected[key], f"{label}/{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{label} changed roster")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _nested_close(a, b, f"{label}/{i}")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        _close(actual, expected, label)
    elif actual != expected:
        raise ValueError(f"{label} changed")


def _execution(p, mode):
    if mode == "main":
        return {
            "splits": dict(p["splits"]),
            "teacher_sample_count": p["teacher_sample_count"],
            "fit": deepcopy(p["fit"]),
            "hermite": deepcopy(p["hermite"]),
            "timing": deepcopy(p["timing"]),
            "test_original_indices": list(range(p["splits"]["test"])),
            "phase": "main",
            "paired_seed_ids": [
                {"init": f"main/init/{s}", "batch": f"main/batch/{s}"}
                for s in p["fit"]["paired_seeds"]
            ],
        }
    return {
        "splits": {"train": 12, "validation": 6, "test": 12},
        "teacher_sample_count": 512,
        "fit": dict(p["fit"], max_updates=8, batch_size=6),
        "hermite": dict(p["hermite"], spot_nodes=17, time_nodes=7),
        "timing": dict(p["timing"], batches=[1, 4], repetitions=2),
        "test_original_indices": list(SMOKE_TEST_IDS),
        "phase": "pilot",
        "paired_seed_ids": [{"init": "pilot/init/0", "batch": "pilot/batch/0"}],
    }


def _effective_protocol(p, execution):
    result = deepcopy(p)
    result["hermite"] = deepcopy(execution["hermite"])
    return result


def _fixed_test_inputs(p):
    """The deterministic roster, without entering any sampling function."""
    rows = []
    for minutes in p["remaining_minutes"]:
        root = np.sqrt(module("protocol")._variance(p, minutes * 60))
        for event in [0, 1]:
            for x in [*(d * root for d in p["test_scaled_distance"]), *p["test_fixed_distance"]]:
                rows.append([p["contract"]["strike"] * np.exp(x), minutes * 60, event])
    return np.asarray(rows)


def _precision(moment, oracle, state, p):
    if state.jump_mean_count == 0:
        return {"precision_ready": True, "reason": None}
    thresholds = np.array(
        [
            p["pilot"]["max_price_se"],
            p["pilot"]["max_delta_se"],
            p["pilot"]["max_scaled_gamma_se_fraction"]
            * max(1.0, abs(p["contract"]["strike"] * oracle[2]))
            / p["contract"]["strike"],
        ]
    )
    rare_ready = moment["active_count"] >= p["pilot"]["minimum_active_count"]
    se_ready = bool(np.all(moment["se"] <= thresholds))
    abs_tol = np.asarray(p["pilot"]["absolute_reference_tolerance"])
    rel_tol = np.asarray(p["pilot"]["relative_reference_tolerance"])
    witness = bool(
        np.all(
            np.abs(moment["mean"] - oracle)
            <= p["pilot"]["se_multiple"] * moment["se"] + abs_tol + rel_tol * np.abs(oracle)
        )
    )
    ready = rare_ready and se_ready and witness
    reason = (
        None
        if ready
        else (
            "rare_event_unobserved"
            if moment["active_count"] == 0
            else "rare_event_unresolved"
            if not rare_ready
            else "teacher_precision_unresolved"
            if not se_ready
            else "teacher_reference_disagreement"
        )
    )
    return {"precision_ready": bool(ready), "reason": reason}


def _save_teacher(arrays, prefix, compact, moment, seeds, precision):
    names = ["zero_values", "active_indices", "active_counts", "z_jump", "active_values"]
    keys = {name: _put(arrays, f"{prefix}/{name}", compact[name]) for name in names}
    keys.update(
        {
            name: _put(arrays, f"{prefix}/{name}", moment[name])
            for name in ["mean", "m2_matrix", "covariance", "se"]
        }
    )
    metadata = {key: _plain(value) for key, value in compact.items() if key not in names}
    metadata.update(
        {
            key: _plain(value)
            for key, value in moment.items()
            if key not in ["mean", "m2_matrix", "covariance", "se"]
        }
    )
    return {**metadata, **precision, "seeds": seeds, "keys": keys}


def _initial_weights(learner, scale, strike, seed):
    import torch

    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            net = learner._CallNet(scale, strike)
            return {key: value.detach().numpy().copy() for key, value in net.named_parameters()}
    finally:
        torch.set_num_threads(previous)


def _weights(fit, arrays):
    return {name: arrays[key] for name, key in fit["weights_keys"].items()}


def _prediction(weights, scale, inputs, strike):
    try:
        return _learner().numpy_predict(weights, scale, inputs, strike=strike)
    except (ValueError, FloatingPointError):
        # Invalid exported weights remain failed original rows, never a new fit.
        return np.full((len(inputs), 3), np.nan)


def _loss(weights, scale, inputs, labels, differential, strike):
    y = _prediction(weights, scale, inputs, strike)
    result = np.mean(((y[:, 0] - labels[:, 0]) / (strike * scale["price_scale"])) ** 2)
    if differential:
        result += np.mean(((y[:, 1] - labels[:, 1]) / scale["delta_scale"]) ** 2)
    return float(result)


def _safe_diagnostic_inputs(p):
    k = p["contract"]["strike"]
    return np.asarray(
        [
            [k, 0, 0],
            [k - 1, 0, 0],
            [k + 1, 0, 1],
            [k, 1, 1],
            [k, 30, 0],
            [k * np.exp(0.15), 60, 1],
            [0, 60, 0],
            [k, -1, 0],
            [k, 60, 0.5],
            [k, 24000, 0],
        ],
        dtype=float,
    )


def _diagnostic_raw(weights, scale, inputs, p):
    values = np.full((len(inputs), 3), np.nan)
    valid = (inputs[:, 0] > 0) & (inputs[:, 1] > 0)
    valid &= np.isin(inputs[:, 2], [0, 1])
    values[valid] = _prediction(weights, scale, inputs[valid], p["contract"]["strike"])
    return values


def _runtime():
    cpu = platform.processor()
    path = Path("/proc/cpuinfo")
    if path.exists():
        cpu = next(
            (
                row.split(":", 1)[1].strip()
                for row in path.read_text().splitlines()
                if row.startswith("model name")
            ),
            cpu,
        )
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": cpu,
        "versions": {
            name: importlib.metadata.version(name) for name in ["numpy", "scipy", "torch"]
        },
        "blas_environment": {
            name: os.environ.get(name)
            for name in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]
        },
        "requested_torch_threads": 1,
    }


def _call(method, inputs, p, grid, fit_map, arrays):
    analytics = module("analytics")
    if method == "core_mixture":
        return analytics.oracle(inputs, p), np.full(len(inputs), "mixture", dtype="U32")
    if method == "hermite":
        return analytics.hermite_predict(grid, inputs, p), np.full(
            len(inputs), "hermite", dtype="U32"
        )
    fit_id, route = method.split("/")
    fit = fit_map[fit_id]
    raw = _prediction(_weights(fit, arrays), fit["normalization"], inputs, p["contract"]["strike"])
    if route == "raw":
        return raw, np.full(len(inputs), "raw", dtype="U32")
    safe = analytics.safe_route(raw, inputs, p)
    return safe["values"], safe["routes"]


def _timings(record, arrays, p, execution, grid, expenses):
    x = arrays[record["datasets"]["test"]["inputs_key"]]
    fits = {fit["id"]: fit for fit in record["fits"]}
    methods = [
        "core_mixture",
        "hermite",
        *(f"{fit['id']}/{route}" for fit in record["fits"] for route in ["raw", "safe"]),
    ]
    settings = execution["timing"]
    result = []
    started = perf_counter()
    for minutes in p["remaining_minutes"]:
        for event in [0, 1]:
            ids = np.flatnonzero((x[:, 1] == minutes * 60) & (x[:, 2] == event))
            if not len(ids):
                continue
            for batch in settings["batches"]:
                indices = np.resize(ids, batch)
                for method in methods:
                    prefix = f"timing/{len(result)}"
                    elapsed, values, routes = [], [], []
                    for rep in range(settings["warmup"] + settings["repetitions"]):
                        before = perf_counter()
                        value, route = _call(method, x[indices], p, grid, fits, arrays)
                        seconds = perf_counter() - before
                        values.append(value)
                        routes.append(route)
                        if rep >= settings["warmup"]:
                            elapsed.append(seconds)
                    result.append(
                        {
                            "method": method,
                            "minutes": minutes,
                            "event": event,
                            "batch_size": batch,
                            "warmup": settings["warmup"],
                            "repetitions": settings["repetitions"],
                            "input_indices_key": _put(arrays, f"{prefix}/indices", indices),
                            "seconds_key": _put(arrays, f"{prefix}/seconds", elapsed),
                            "values_key": _put(arrays, f"{prefix}/values", values),
                            "routes_key": _put(arrays, f"{prefix}/routes", routes),
                            "scope": "whole returned price, physical Delta, Gamma and route",
                            "order": len(result),
                        }
                    )
    _charge(
        expenses,
        "timing",
        "timing",
        perf_counter() - started,
        "fixed order, warmup and repeated whole calls; includes saving in-memory outputs",
    )
    return result


def run_study(p, directory, *, mode="main"):
    """Run the frozen study or an explicit non-accepted smoke, then save.

    The shared train-teacher cost enters each independent fit's cap, but is
    charged once in categorized study expenses. Incomplete attempts stay in
    their original two/six slots. Returned scalar-price derivatives are raw.
    """
    if mode not in ["main", "smoke"]:
        raise ValueError("mode must be main or smoke")
    directory = Path(directory)
    if any((directory / name).exists() for name in ["reference.json", "reference.npz"]):
        raise FileExistsError("existing study output would be replaced")
    protocol, analytics, reference = (
        module("protocol"),
        module("analytics"),
        module("reference_methods"),
    )
    gate_started = perf_counter()
    protocol.validate_protocol(p, require_frozen=mode == "main")
    if mode == "main":
        protocol.verify_frozen_evidence(p)
    gate_s = perf_counter() - gate_started
    registry = protocol.source_registry(require_complete=mode == "main")
    execution = _execution(p, mode)
    for name in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            raise ValueError("BLAS/OMP/MKL single-thread environment required")
    arrays, expenses = {}, []
    _charge(
        expenses,
        "protocol_gate",
        "validation",
        gate_s,
        "source/conditions/seed roster and main's actual frozen pilot validation",
    )
    record = {
        "schema": "RB-F05-short-study-v1",
        "mode": mode,
        "phase": execution["phase"],
        "protocol": deepcopy(p),
        "protocol_digest": protocol.json_digest(p),
        "source_registry": registry,
        "source_registry_complete": len(registry) == len(protocol.SOURCES),
        "execution": execution,
        "accepted": False,
        "teaching_acceptance": False,
        "complete": False,
        "datasets": {},
        "fits": [],
        "initializations": [],
        "runtime": _runtime(),
        "expenses": expenses,
        "limits": [
            "synthetic fixed cash-call contract; no official market calibration",
            "teacher precision failures remain labels and original slots",
            "raw model errors and safe fallback are separate; bounds do not detect unknown error",
            "all Greeks differentiate the same scalar price at fixed clocks and jump law",
            "main-only measured costs are not independent mathematical startup requirements",
        ],
    }
    started = perf_counter()
    phase = execution["phase"]
    for split in ["train", "validation", "test"]:
        if split == "test":
            inputs = _fixed_test_inputs(p)[execution["test_original_indices"]]
        else:
            inputs = protocol.scenario_inputs(p, split, phase=phase)[: execution["splits"][split]]
        record["datasets"][split] = {
            "original_count": len(inputs),
            "inputs_key": _put(arrays, f"{split}/inputs", inputs),
            "teacher_sample_count": execution["teacher_sample_count"] if split != "test" else None,
            "teachers": [],
            "original_indices_key": _put(
                arrays,
                f"{split}/original_indices",
                execution["test_original_indices"] if split == "test" else np.arange(len(inputs)),
            ),
            "scenario_seed_id": f"{phase}/scenario/{split}" if split != "test" else None,
        }
    _charge(
        expenses,
        "geometry",
        "geometry",
        perf_counter() - started,
        "original balanced train/validation and deterministic test rosters",
    )

    reference_started = perf_counter()
    ps = analytics.parameters(p)
    for split, dataset in record["datasets"].items():
        inputs = arrays[dataset["inputs_key"]]
        oracle = analytics.oracle(inputs, p)
        dataset["oracle_key"] = _put(arrays, f"{split}/oracle", oracle)
    test = record["datasets"]["test"]
    tx = arrays[test["inputs_key"]]
    states = analytics.states(tx, p)
    independent = [
        reference.independent_mixture(
            row[0], p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
        )
        for row, state in zip(tx, states, strict=True)
    ]
    test["independent_key"] = _put(arrays, "test/independent", [v["values"] for v in independent])
    test["independent_tails_key"] = _put(
        arrays, "test/independent_tails", [v["tail_bounds"] for v in independent]
    )
    merton = [
        reference.merton_price_check(
            row[0], p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
        )
        for row, state in zip(tx, states, strict=True)
    ]
    test["merton_prices_key"] = _put(arrays, "test/merton_prices", [v["price"] for v in merton])
    record["references"] = {
        "merton": {
            "original_count": len(tx),
            "scope": "price only; existing integrated-clock comparator",
            "statuses": [v["status"] for v in merton],
        },
        "independent_mixture": {
            "original_count": len(tx),
            "nmax": p["reference_nmax"],
            "status": [v["status"] for v in independent],
        },
        "density": [],
    }
    representative = []
    for event in [0, 1]:
        ids = np.flatnonzero(tx[:, 2] == event)
        if len(ids):
            representative.append(
                int(ids[np.argmin(np.abs(np.log(tx[ids, 0] / p["contract"]["strike"])))])
            )
    for idx in representative:
        density = reference.density_quad(
            tx[idx, 0], p["contract"]["strike"], states[idx], ps, nmax=p["reference_nmax"]
        )
        prefix = f"density/{idx}"
        record["references"]["density"].append(
            {
                "test_index": idx,
                "status": density["status"],
                "values_key": _put(arrays, f"{prefix}/values", density["values"]),
                "errors_key": _put(arrays, f"{prefix}/errors", density["error_estimates"]),
                "tails_key": _put(arrays, f"{prefix}/tails", density["tail_bounds"]),
                "lr_gamma": density["lr_gamma"],
                "lr_gamma_error_estimate": density["lr_gamma_error_estimate"],
                "messages": density["quadrature_messages"],
            }
        )
    _charge(
        expenses,
        "reference",
        "reference",
        perf_counter() - reference_started,
        "all core oracle rows, independent test mixture and representative density integrals",
    )

    for split in ["train", "validation"]:
        dataset = record["datasets"][split]
        inputs = arrays[dataset["inputs_key"]]
        oracle = arrays[dataset["oracle_key"]]
        means = []
        for i, (row, state) in enumerate(zip(inputs, analytics.states(inputs, p), strict=True)):
            count_id, jump_id = (
                f"{phase}/teacher/{split}/{i}/count",
                f"{phase}/teacher/{split}/{i}/jump",
            )
            seeds = {
                "count_id": count_id,
                "jump_id": jump_id,
                "count": protocol.seed_for(p, count_id),
                "jump": protocol.seed_for(p, jump_id),
            }
            before = perf_counter()
            compact = core.compact_teacher(
                row[0],
                p["contract"]["strike"],
                state,
                ps,
                sample_count=execution["teacher_sample_count"],
                count_seed=seeds["count"],
                jump_seed=seeds["jump"],
            )
            moment = core.compact_moments(compact)
            identity = f"teacher/{split}/{i}"
            generation_s = perf_counter() - before
            _charge(
                expenses,
                identity,
                f"teacher_{split}",
                generation_s,
                "all original count draws, active-only marks, conditional values and joint moments",
            )
            teacher = _save_teacher(
                arrays, identity, compact, moment, seeds, _precision(moment, oracle[i], state, p)
            )
            teacher["expense_id"] = identity
            teacher["generation_s"] = generation_s
            dataset["teachers"].append(teacher)
            means.append(moment["mean"])
        dataset["labels_key"] = _put(arrays, f"{split}/labels", means)
        dataset["precision_ready_count"] = sum(t["precision_ready"] for t in dataset["teachers"])
    train_dataset = record["datasets"]["train"]
    train_x = arrays[train_dataset["inputs_key"]]
    labels = arrays[train_dataset["labels_key"]]
    train_teacher_s = sum(e["seconds"] for e in expenses if e["category"] == "teacher_train")
    before = perf_counter()
    hp = _effective_protocol(p, execution)
    grid = analytics.build_hermite(hp)
    record["hermite"] = {
        "keys": {key: _put(arrays, f"hermite/{key}", value) for key, value in grid.items()},
        "predictions": {},
        "node_count": int(np.prod(grid["derivatives"].shape[:-1])),
        "scalar_price_continuity": "C2 in log spot; log-time affine blend",
    }
    _charge(
        expenses,
        "hermite_grid",
        "grid",
        perf_counter() - before,
        "one grid build including all node price/Delta/Gamma oracle work",
    )
    before = perf_counter()
    prepared = analytics.prepare_hermite(grid)
    _charge(
        expenses,
        "hermite_prepare",
        "prepare",
        perf_counter() - before,
        "saved derivatives to online quintic spline objects, charged once",
    )
    before = perf_counter()
    for split, dataset in record["datasets"].items():
        inputs = arrays[dataset["inputs_key"]]
        y = analytics.hermite_predict(prepared, inputs, p)
        record["hermite"]["predictions"][split] = _put(arrays, f"hermite/{split}", y)
    record["hermite"]["test_errors"] = analytics.error_summary(
        arrays[record["hermite"]["predictions"]["test"]],
        arrays[test["oracle_key"]],
        strike=p["contract"]["strike"],
    )
    record["hermite"]["test_buckets"] = analytics.bucket_errors(
        arrays[record["hermite"]["predictions"]["test"]], arrays[test["oracle_key"]], tx, p
    )
    _charge(
        expenses,
        "hermite_evaluation",
        "evaluation",
        perf_counter() - before,
        "whole predictions for all original split rows and error summaries",
    )

    learner = _learner()
    scale = learner.normalization(
        train_x, labels[:, 0], labels[:, 1], strike=p["contract"]["strike"]
    )
    diag_inputs = _safe_diagnostic_inputs(p)
    diagnostic_reference = np.full((len(diag_inputs), 3), np.nan)
    diagnostic_valid = (
        (diag_inputs[:, 0] > 0)
        & (diag_inputs[:, 1] >= 0)
        & (diag_inputs[:, 1] <= 390 * 60)
        & np.isin(diag_inputs[:, 2], [0, 1])
    )
    diagnostic_reference[diagnostic_valid] = analytics.oracle(diag_inputs[diagnostic_valid], p)
    record["diagnostics"] = {
        "inputs_key": _put(arrays, "diagnostics/inputs", diag_inputs),
        "reference_key": _put(arrays, "diagnostics/reference", diagnostic_reference),
        "original_count": len(diag_inputs),
        "invalid_contract_count": int((~diagnostic_valid).sum()),
        "price_defined_count": int(np.isfinite(diagnostic_reference[:, 0]).sum()),
        "ordinary_greeks_defined_count": int(np.isfinite(diagnostic_reference).all(axis=1).sum()),
        "expiry_atm_unknown_count": 1,
        "scope": "full original boundary/OOD/invalid roster; separate from fixed48 test buckets",
    }
    settings = execution["fit"]
    for pair_id, seed_ids in enumerate(execution["paired_seed_ids"]):
        seed = protocol.seed_for(p, seed_ids["init"])
        batch_seed = protocol.seed_for(p, seed_ids["batch"])
        before = perf_counter()
        initial_weights = _initial_weights(learner, scale, p["contract"]["strike"], seed)
        # This independent recorded master sequence verifies order without RNG in replay.
        batches = np.random.default_rng(batch_seed).integers(
            0, len(train_x), (settings["max_updates"], settings["batch_size"]), dtype=np.int32
        )
        initialization = {
            "id": f"pair{pair_id}",
            "seed_id": seed_ids["init"],
            "seed": seed,
            "batch_seed_id": seed_ids["batch"],
            "batch_seed": batch_seed,
            "weights_keys": {
                name: _put(arrays, f"initial/{pair_id}/{name}", value)
                for name, value in initial_weights.items()
            },
            "batch_roster_key": _put(arrays, f"initial/{pair_id}/batches", batches),
        }
        record["initializations"].append(initialization)
        _charge(
            expenses,
            f"initial/{pair_id}",
            "initialization",
            perf_counter() - before,
            "recorded paired initial weights and full master batch roster; train setup separately measured",
        )
        for differential in [False, True]:
            fit_id = f"fit{len(record['fits'])}"
            before = perf_counter()
            try:
                fitted = learner.train(
                    train_x,
                    labels[:, 0],
                    labels[:, 1],
                    seed=seed,
                    batch_seed=batch_seed,
                    dml=differential,
                    max_updates=settings["max_updates"],
                    batch_size=settings["batch_size"],
                    learning_rate=settings["learning_rate"],
                    budget_s=settings["budget_s"],
                    teacher_s=train_teacher_s,
                    strike=p["contract"]["strike"],
                )
                train_s = fitted.stats["training_s"]
            except (ValueError, RuntimeError, FloatingPointError) as exc:
                train_s = perf_counter() - before
                fitted = None
                failure = {
                    "status": "training_exception",
                    "complete": False,
                    "reason": str(exc),
                    "updates": 0,
                    "requested_updates": settings["max_updates"],
                    "batch_indices": np.empty((0, settings["batch_size"]), dtype=np.int32),
                    "batch_attempts": 0,
                    "batch_size": settings["batch_size"],
                    "initial_loss": None,
                    "final_loss": None,
                    "seed": seed,
                    "batch_seed": batch_seed,
                    "dml": differential,
                    "gamma_loss": False,
                    "learning_rate": settings["learning_rate"],
                    "training_s": train_s,
                    "teacher_s": train_teacher_s,
                    "teacher_and_training_s": train_s + train_teacher_s,
                    "budget_s": settings["budget_s"],
                    "overrun_s": max(0.0, train_s + train_teacher_s - settings["budget_s"]),
                    "threads": 1,
                    "strike": p["contract"]["strike"],
                    "cost_scope": "failed train call including setup; excludes import",
                }
            _charge(
                expenses,
                f"fit/{fit_id}",
                "fit",
                train_s,
                "learner validation/setup/initialization/updates/evaluation/thread restore; shared teacher excluded",
            )
            before = perf_counter()
            exported = (
                learner.export_fit(fitted)
                if fitted is not None
                else {
                    "weights": deepcopy(initial_weights),
                    "normalization": deepcopy(scale),
                    "stats": failure,
                }
            )
            fit = {
                "id": fit_id,
                "dml": differential,
                "pair_id": pair_id,
                "initial_weights_id": initialization["id"],
                "weights_state": "final" if fitted is not None else "initial_after_exception",
                "weights_keys": {
                    name: _put(arrays, f"{fit_id}/weights/{name}", value)
                    for name, value in exported["weights"].items()
                },
                "normalization": _plain(exported["normalization"]),
                "stats": _plain(
                    {k: v for k, v in exported["stats"].items() if k != "batch_indices"}
                ),
                "batch_indices_key": _put(
                    arrays, f"{fit_id}/batches", exported["stats"]["batch_indices"]
                ),
                "predictions": {},
            }
            _charge(
                expenses,
                f"export/{fit_id}",
                "export",
                perf_counter() - before,
                "plain copied weights/normalization/stats and in-memory NPZ fields",
            )
            before = perf_counter()
            for split, dataset in record["datasets"].items():
                inputs = arrays[dataset["inputs_key"]]
                raw = _prediction(
                    exported["weights"], exported["normalization"], inputs, p["contract"]["strike"]
                )
                safe = analytics.safe_route(raw, inputs, p)
                fit["predictions"][split] = {
                    "raw_key": _put(arrays, f"{fit_id}/{split}/raw", raw),
                    "safe_key": _put(arrays, f"{fit_id}/{split}/safe", safe["values"]),
                    "routes_key": _put(arrays, f"{fit_id}/{split}/routes", safe["routes"]),
                    "original_count": len(inputs),
                    "raw_count": safe["raw_count"],
                    "raw_errors": analytics.error_summary(
                        raw, arrays[dataset["oracle_key"]], strike=p["contract"]["strike"]
                    ),
                    "safe_errors": analytics.error_summary(
                        safe["values"],
                        arrays[dataset["oracle_key"]],
                        strike=p["contract"]["strike"],
                    ),
                }
            fit["test_buckets"] = analytics.bucket_errors(
                arrays[fit["predictions"]["test"]["raw_key"]], arrays[test["oracle_key"]], tx, p
            )
            fit["safe_test_buckets"] = analytics.bucket_errors(
                arrays[fit["predictions"]["test"]["safe_key"]], arrays[test["oracle_key"]], tx, p
            )
            diag_raw = _diagnostic_raw(
                exported["weights"], exported["normalization"], diag_inputs, p
            )
            diag_safe = analytics.safe_route(diag_raw, diag_inputs, p)
            fit["diagnostics"] = {
                "raw_key": _put(arrays, f"{fit_id}/diagnostics/raw", diag_raw),
                "safe_key": _put(arrays, f"{fit_id}/diagnostics/safe", diag_safe["values"]),
                "routes_key": _put(arrays, f"{fit_id}/diagnostics/routes", diag_safe["routes"]),
                "original_count": len(diag_inputs),
                "route_counts": {
                    str(route): int(np.sum(diag_safe["routes"] == route))
                    for route in np.unique(diag_safe["routes"])
                },
                "raw_errors": analytics.error_summary(
                    diag_raw, diagnostic_reference, strike=p["contract"]["strike"]
                ),
                "safe_errors": analytics.error_summary(
                    diag_safe["values"], diagnostic_reference, strike=p["contract"]["strike"]
                ),
            }
            record["fits"].append(fit)
            _charge(
                expenses,
                f"evaluation/{fit_id}",
                "evaluation",
                perf_counter() - before,
                "all NumPy raw/safe predictions, original errors/buckets and contract diagnostics",
            )
    record["timing"] = _timings(record, arrays, p, execution, prepared, expenses)
    record["complete"] = True
    for identity, scope in [
        ("serialization", "JSON/NPZ measured in separate record-bound serialization_cost.json"),
        ("cold_import", "new-process import/startup not measured by this function"),
        ("archive_load", "new archive/weights load not measured by in-memory study timing"),
        ("pilot_freeze", "full independent pilot/freeze outside main-only study receipt"),
        ("fresh", "independent fresh replay outside this saved-only study"),
    ]:
        _charge(expenses, identity, identity, None, scope)
    record["costs"] = {
        "categorized": analytics.expense_totals(expenses),
        "scope": "recorded categories; CLI total wall includes additional overhead",
        "main_only_s": analytics.expense_totals(expenses)["measured_seconds"],
        "cold_pipeline_s": None,
        "archive_load_s": None,
        "fresh_s": None,
        "shared_train_teacher_s": train_teacher_s,
        "serialization_pending": True,
    }
    before = perf_counter()
    record["saved_check"] = _check_record(record, arrays, recording=True)
    _charge(
        expenses,
        "saved_check",
        "validation",
        perf_counter() - before,
        "all original compact/Greek/prediction/timing/cost checks, no RNG or training",
    )
    record["costs"]["categorized"] = analytics.expense_totals(expenses)
    record["costs"]["main_only_s"] = record["costs"]["categorized"]["measured_seconds"]
    directory.mkdir(parents=True, exist_ok=True)
    before = perf_counter()
    np.savez_compressed(directory / "reference.npz", **arrays)
    (directory / "reference.json").write_text(json.dumps(_plain(record), indent=2, allow_nan=False))
    seconds = perf_counter() - before
    receipt = {
        "schema": "RB-F05-short-serialization-v1",
        "record_digest": protocol.json_digest(record),
        "seconds": seconds,
        "expense_id": "serialization",
        "npz_bytes": (directory / "reference.npz").stat().st_size,
        "scope": "NPZ compression/write and study JSON serialization/write; receipt write excluded",
    }
    (directory / "serialization_cost.json").write_text(json.dumps(receipt, indent=2))
    return record, arrays


def load_result(directory):
    """Read strict JSON/plain NPZ without drawing or training."""
    directory = Path(directory)
    record = json.loads((directory / "reference.json").read_text())
    with np.load(directory / "reference.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key].copy() for key in saved.files}
    return record, arrays


def serialization_receipt(directory, record):
    """Resolve the explicitly pending save category using a separate receipt."""
    path = Path(directory) / "serialization_cost.json"
    if not path.exists():
        return {"pending": True, "seconds": None}
    receipt = json.loads(path.read_text())
    if (
        receipt.get("schema") != "RB-F05-short-serialization-v1"
        or receipt.get("record_digest") != module("protocol").json_digest(record)
        or not np.isfinite(receipt["seconds"])
        or receipt["seconds"] < 0
        or receipt.get("expense_id") != "serialization"
    ):
        raise ValueError("serialization receipt changed binding or seconds")
    return {"pending": False, **receipt}


def _teacher_check(t, row, oracle, arrays, p, execution, *, split, index):
    analytics, protocol = module("analytics"), module("protocol")
    state, ps = analytics.states(row[None], p)[0], analytics.parameters(p)
    n = execution["teacher_sample_count"]
    compact = {
        key: arrays[t["keys"][key]]
        for key in ["zero_values", "active_indices", "active_counts", "z_jump", "active_values"]
    }
    compact.update(
        {
            key: t[key]
            for key in [
                "sample_count",
                "zero_count",
                "status",
                "actual_random_draws",
                "reason",
                "delta_status",
                "gamma_status",
            ]
            if key in t
        }
    )
    if t["sample_count"] != n or t["reserved_sample_count"] != n:
        raise ValueError("teacher original denominator changed")
    ids, counts, marks = compact["active_indices"], compact["active_counts"], compact["z_jump"]
    if (
        counts.shape != ids.shape
        or marks.shape != ids.shape
        or counts.dtype.kind not in "iu"
        or np.any(counts < 1)
    ):
        raise ValueError("invalid active count/mark original roster")
    _close(
        compact["zero_values"],
        core.conditional_values(row[0], p["contract"]["strike"], state, ps, 0, 0),
        "teacher zero block",
    )
    _close(
        compact["active_values"],
        core.conditional_values(row[0], p["contract"]["strike"], state, ps, counts, marks),
        "teacher active values",
    )
    seeds = t["seeds"]
    for kind in ["count", "jump"]:
        expected_id = f"{execution['phase']}/teacher/{split}/{index}/{kind}"
        if seeds[f"{kind}_id"] != expected_id:
            raise ValueError("teacher seed ID changed original slot")
        if seeds[kind] != protocol.seed_for(p, seeds[f"{kind}_id"]):
            raise ValueError("teacher physical seed changed")
    moment = core.compact_moments(compact)
    for name in ["mean", "m2_matrix", "covariance", "se"]:
        _close(arrays[t["keys"][name]], moment[name], f"teacher/{name}")
    for name in [
        "count",
        "reserved_sample_count",
        "active_count",
        "zero_count",
        "status",
        "actual_random_draws",
        "prefix_equivalent_draws",
    ]:
        if t[name] != moment[name]:
            raise ValueError(f"teacher {name} changed")
    if state.jump_mean_count == 0:
        if (
            len(ids)
            or t["count_draws"] != 0
            or t["normal_draws"] != 0
            or t["observed_mc_count"] != 0
        ):
            raise ValueError("analytic zero-Lambda random observations changed")
    elif (
        t["count_draws"] != n
        or t["observed_mc_count"] != n
        or t["normal_draws"] != len(ids)
        or t["actual_random_draws"] != n + len(ids)
    ):
        raise ValueError("teacher actual draw accounting changed")
    _nested_close(
        {k: t[k] for k in ["precision_ready", "reason"]},
        _precision(moment, oracle, state, p),
        "teacher precision classification",
    )
    return moment["mean"]


def _expense_requirements(execution, *, recording):
    """The runner's closed charge roster, derived from original execution slots."""
    result = {
        "protocol_gate": "validation",
        "geometry": "geometry",
        "reference": "reference",
        "hermite_grid": "grid",
        "hermite_prepare": "prepare",
        "hermite_evaluation": "evaluation",
        "timing": "timing",
        "serialization": "serialization",
        "cold_import": "cold_import",
        "archive_load": "archive_load",
        "pilot_freeze": "pilot_freeze",
        "fresh": "fresh",
    }
    if not recording:
        result["saved_check"] = "validation"
    for split in ["train", "validation"]:
        for i in range(execution["splits"][split]):
            result[f"teacher/{split}/{i}"] = f"teacher_{split}"
    for i in range(len(execution["paired_seed_ids"])):
        result[f"initial/{i}"] = "initialization"
    for i in range(2 * len(execution["paired_seed_ids"])):
        result[f"fit/fit{i}"] = "fit"
        result[f"export/fit{i}"] = "export"
        result[f"evaluation/fit{i}"] = "evaluation"
    return result


def _closed_accounting(record, arrays, execution, *, recording):
    """Reject omitted/unassigned/unpaid receipts and promoted unknown costs."""
    required = _expense_requirements(execution, recording=recording)
    expenses = record["expenses"]
    ids = [e["id"] for e in expenses]
    if len(ids) != len(set(ids)) or set(ids) != set(required):
        raise ValueError("expense closed roster changed, missing, extra or duplicate receipt")
    receipts = {e["id"]: e for e in expenses}
    pending = {"serialization", "cold_import", "archive_load", "pilot_freeze", "fresh"}
    for identity, category in required.items():
        row = receipts[identity]
        if (
            not {"id", "category", "seconds", "charged", "scope"} <= set(row)
            or set(row) - {"id", "category", "seconds", "charged", "scope", "parent"}
            or row["category"] != category
            or row["charged"] is not True
            or row.get("parent") is not None
            or not isinstance(row["scope"], str)
            or not row["scope"]
        ):
            raise ValueError("expense category/charged/parent schema changed")
        seconds = row["seconds"]
        if identity in pending:
            if seconds is not None:
                raise ValueError("pending expense was promoted to a measurement")
        elif seconds is None or not np.isfinite(seconds) or seconds < 0:
            raise ValueError("required measured expense receipt is invalid")
    expected_cost_keys = {
        "categorized",
        "scope",
        "main_only_s",
        "cold_pipeline_s",
        "fresh_s",
        "archive_load_s",
        "shared_train_teacher_s",
        "serialization_pending",
    }
    costs = record["costs"]
    if (
        set(costs) != expected_cost_keys
        or costs["cold_pipeline_s"] is not None
        or costs["fresh_s"] is not None
        or costs["archive_load_s"] is not None
        or costs["serialization_pending"] is not True
        or costs["scope"] != "recorded categories; CLI total wall includes additional overhead"
    ):
        raise ValueError("cost fixed fields or pending statuses changed")
    totals = module("analytics").expense_totals(expenses)
    if set(totals["pending_ids"]) != pending:
        raise ValueError("expense pending roster changed")
    _nested_close(costs["categorized"], totals, "cost categorized account")
    _close(costs["main_only_s"], totals["measured_seconds"], "cost main-only sum")
    generation = 0.0
    for split in ["train", "validation"]:
        teachers = record["datasets"][split]["teachers"]
        if len(teachers) != execution["splits"][split]:
            raise ValueError("teacher expense original roster changed")
        for i, teacher in enumerate(teachers):
            identity = f"teacher/{split}/{i}"
            if teacher["expense_id"] != identity:
                raise ValueError("teacher expense link changed original generation")
            if (
                "generation_s" not in teacher
                or not np.isfinite(teacher["generation_s"])
                or teacher["generation_s"] < 0
            ):
                raise ValueError("teacher generation cost measurement missing or invalid")
            _close(
                teacher["generation_s"], receipts[identity]["seconds"], "teacher generation receipt"
            )
            if split == "train":
                generation += teacher["generation_s"]
    _close(costs["shared_train_teacher_s"], generation, "shared teacher generation cost")
    for fit in record["fits"]:
        row = receipts[f"fit/{fit['id']}"]
        _close(row["seconds"], fit["stats"]["training_s"], "fit charged measured receipt")
        _close(fit["stats"]["teacher_s"], generation, "fit shared teacher generation cap")
    measured_timing = sum(float(np.sum(arrays[t["seconds_key"]])) for t in record["timing"])
    actual_timing = receipts["timing"]["seconds"]
    roundoff = 64 * np.finfo(float).eps * max(1.0, actual_timing, measured_timing)
    if not np.isfinite(measured_timing) or actual_timing + roundoff < measured_timing:
        raise ValueError("timing expense is below its measured whole-call repetitions")


def _fit_lifecycle(fit, arrays, initial_weights):
    """Use the actual learner's attempted-step and completion contract."""
    s = fit["stats"]
    status, updates, attempts = s["status"], s["updates"], s["batch_attempts"]
    limit = s["requested_updates"]
    statuses = {
        "completed",
        "time_cap",
        "optimizer_error",
        "nonfinite_loss",
        "nonfinite_gradient",
        "nonfinite_parameters",
        "training_exception",
    }
    if status not in statuses or s["complete"] != (status == "completed"):
        raise ValueError("fit lifecycle status is invalid")
    expected_state = "initial_after_exception" if status == "training_exception" else "final"
    if fit["weights_state"] != expected_state:
        raise ValueError("fit lifecycle weights state disagrees with observed outcome")
    if not s["complete"] and (not isinstance(s["reason"], str) or not s["reason"]):
        raise ValueError("failed fit lifecycle needs its observed reason")
    if status == "completed":
        if attempts != updates or updates != limit:
            raise ValueError("completed fit attempted/completed updates disagree")
        # An update or final evaluation may overrun after the final cap check.
    elif status == "time_cap":
        roundoff = 64 * np.finfo(float).eps * max(1.0, s["budget_s"])
        if attempts != updates or updates >= limit:
            raise ValueError("time cap fit attempted/completed lifecycle is impossible")
        if s["teacher_and_training_s"] + roundoff < s["budget_s"]:
            raise ValueError("time cap fit total time is below its observed budget")
        if s["initial_loss"] is None and (attempts or s["final_loss"] is not None):
            raise ValueError("pre-update time cap objective lifecycle changed")
    elif status in {"optimizer_error", "nonfinite_gradient"}:
        if attempts != updates + 1 or s["initial_loss"] is None:
            raise ValueError("failed fit step attempts disagree with completed updates")
    elif status == "nonfinite_parameters":
        if attempts != updates or updates < 1 or s["initial_loss"] is None:
            raise ValueError("nonfinite-parameter fit step lifecycle is impossible")
        if all(np.isfinite(value).all() for value in _weights(fit, arrays).values()):
            raise ValueError("nonfinite-parameter fit has no observed nonfinite weights")
    elif status == "training_exception":
        if updates or attempts or s["initial_loss"] is not None or s["final_loss"] is not None:
            raise ValueError(
                "escaped training exception cannot claim observed returned-fit updates"
            )
        weights = _weights(fit, arrays)
        if set(weights) != set(initial_weights):
            raise ValueError("exception fit initial weights schema changed")
        for name in weights:
            _close(weights[name], initial_weights[name], "exception fit initial weights")
    else:
        if s["initial_loss"] is None:
            valid = attempts == updates == 0 and s["final_loss"] is None
        elif attempts == updates + 1:
            valid = True  # nonfinite mini-batch objective before its optimizer step
        else:
            valid = attempts == updates == limit and s["final_loss"] is None
        if not valid:
            raise ValueError("nonfinite-loss fit objective/attempt lifecycle is impossible")

    # These exits have performed no optimizer call when updates==0. Gradients
    # and loss evaluation do not mutate this feed-forward model's parameters.
    # optimizer_error is excluded: a failed step can have partial mutations.
    if updates == 0 and status in {"time_cap", "nonfinite_loss", "nonfinite_gradient"}:
        weights = _weights(fit, arrays)
        if set(weights) != set(initial_weights):
            raise ValueError("zero-update fit initial weights schema changed")
        for name in weights:
            _close(weights[name], initial_weights[name], "zero-update fit initial weights")


def _check_record(record, arrays, *, recording):
    """Internal check: saved-check charge is absent only while measuring itself."""
    protocol, analytics, reference = (
        module("protocol"),
        module("analytics"),
        module("reference_methods"),
    )
    r, p = record, record["protocol"]
    if r.get("schema") != "RB-F05-short-study-v1" or r.get("mode") not in ["main", "smoke"]:
        raise ValueError("invalid study schema/mode")
    if not r["complete"] or r["accepted"] or r["teaching_acceptance"]:
        raise ValueError("study completion/acceptance metadata changed")
    if r["protocol_digest"] != protocol.json_digest(p):
        raise ValueError("protocol provenance binding changed")
    protocol.validate_protocol(p, require_frozen=r["mode"] == "main")
    if r["mode"] == "main":
        protocol.verify_frozen_evidence(p)
    registry = protocol.source_registry(require_complete=r["mode"] == "main")
    if r["source_registry"] != registry or r["source_registry_complete"] != (
        len(registry) == len(protocol.SOURCES)
    ):
        raise ValueError("financial source binding changed")
    execution = _execution(p, r["mode"])
    _nested_close(r["execution"], execution, "execution roster")
    _closed_accounting(r, arrays, execution, recording=recording)
    if r["phase"] != execution["phase"] or set(r["datasets"]) != {"train", "validation", "test"}:
        raise ValueError("original dataset roster changed")
    if any(np.asarray(a).dtype.hasobject for a in arrays.values()):
        raise ValueError("invalid non-plain saved arrays")
    required_runtime = {
        "python",
        "platform",
        "cpu",
        "versions",
        "blas_environment",
        "requested_torch_threads",
    }
    if set(r["runtime"]) != required_runtime or r["runtime"]["versions"] != p["runtime_versions"]:
        raise ValueError("runtime/version binding changed")
    if r["runtime"]["requested_torch_threads"] != 1 or set(
        r["runtime"]["blas_environment"].values()
    ) != {"1"}:
        raise ValueError("hardware thread context changed")
    tx = arrays[r["datasets"]["test"]["inputs_key"]]
    _close(tx, _fixed_test_inputs(p)[execution["test_original_indices"]], "test original geometry")
    ps = analytics.parameters(p)
    teacher_count = 0
    for split, dataset in r["datasets"].items():
        x = arrays[dataset["inputs_key"]]
        if x.shape != (execution["splits"][split], 3) or dataset["original_count"] != len(x):
            raise ValueError("dataset original row count changed")
        expected_indices = (
            execution["test_original_indices"] if split == "test" else np.arange(len(x))
        )
        _close(
            arrays[dataset["original_indices_key"]], expected_indices, "dataset original indices"
        )
        expected_n = execution["teacher_sample_count"] if split != "test" else None
        if dataset["teacher_sample_count"] != expected_n:
            raise ValueError("dataset teacher reservation changed")
        if split != "test":
            if (
                not np.isfinite(x).all()
                or np.any(x[:, 0] <= 0)
                or np.any(x[:, 1] < 60 - 1e-9)
                or np.any(x[:, 1] > 390 * 60 + 1e-9)
                or not np.array_equal(x[:, 2], np.tile([0, 1], len(x) // 2))
                or dataset["scenario_seed_id"] != f"{execution['phase']}/scenario/{split}"
            ):
                raise ValueError("invalid original train/validation geometry or seed")
        oracle = analytics.oracle(x, p)
        _close(arrays[dataset["oracle_key"]], oracle, f"{split} oracle")
        if split != "test":
            if len(dataset["teachers"]) != len(x):
                raise ValueError("teacher original roster changed")
            means = []
            for index, (t, row, y) in enumerate(zip(dataset["teachers"], x, oracle, strict=True)):
                means.append(
                    _teacher_check(t, row, y, arrays, p, execution, split=split, index=index)
                )
                teacher_count += 1
            _close(arrays[dataset["labels_key"]], means, f"{split} conditioned labels")
            if dataset["precision_ready_count"] != sum(
                t["precision_ready"] for t in dataset["teachers"]
            ):
                raise ValueError("teacher ready count changed")
    states = analytics.states(tx, p)
    independent = [
        reference.independent_mixture(
            row[0], p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
        )
        for row, state in zip(tx, states, strict=True)
    ]
    test = r["datasets"]["test"]
    _close(
        arrays[test["independent_key"]], [v["values"] for v in independent], "independent reference"
    )
    _close(
        arrays[test["independent_tails_key"]],
        [v["tail_bounds"] for v in independent],
        "reference tails",
    )
    _nested_close(
        r["references"]["independent_mixture"],
        {
            "original_count": len(tx),
            "nmax": p["reference_nmax"],
            "status": [v["status"] for v in independent],
        },
        "independent metadata",
    )
    abs_tol = np.asarray(p["pilot"]["absolute_reference_tolerance"])
    rel_tol = np.asarray(p["pilot"]["relative_reference_tolerance"])
    ys = arrays[test["oracle_key"]]
    iv = arrays[test["independent_key"]]
    if np.any(np.abs(ys - iv) > abs_tol + rel_tol * np.abs(iv)):
        raise ValueError("independent/core reference disagreement")
    merton = [
        reference.merton_price_check(
            row[0], p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
        )
        for row, state in zip(tx, states, strict=True)
    ]
    _close(arrays[test["merton_prices_key"]], [v["price"] for v in merton], "Merton reference")
    _nested_close(
        r["references"]["merton"],
        {
            "original_count": len(tx),
            "scope": "price only; existing integrated-clock comparator",
            "statuses": [v["status"] for v in merton],
        },
        "Merton metadata",
    )
    if np.any(
        np.abs(arrays[test["merton_prices_key"]] - iv[:, 0])
        > abs_tol[0] + rel_tol[0] * np.abs(iv[:, 0]) + arrays[test["independent_tails_key"]][:, 0]
    ):
        raise ValueError("Merton independent price disagreement")
    representative = []
    for event in [0, 1]:
        ids = np.flatnonzero(tx[:, 2] == event)
        if len(ids):
            representative.append(
                int(ids[np.argmin(np.abs(np.log(tx[ids, 0] / p["contract"]["strike"])))])
            )
    if [item["test_index"] for item in r["references"]["density"]] != representative:
        raise ValueError("density original representative roster changed")
    for item in r["references"]["density"]:
        idx = item["test_index"]
        # Only the two representative deterministic integrals are repeated;
        # no new paths or hundreds of quadrature observations are generated.
        expected = reference.density_quad(
            tx[idx, 0], p["contract"]["strike"], states[idx], ps, nmax=p["reference_nmax"]
        )
        for name, expected_name in [
            ("values", "values"),
            ("errors", "error_estimates"),
            ("tails", "tail_bounds"),
        ]:
            _close(arrays[item[f"{name}_key"]], expected[expected_name], f"density {name}")
        for name in ["status", "lr_gamma", "lr_gamma_error_estimate"]:
            _nested_close(item[name], expected[name], f"density {name}")
        _nested_close(item["messages"], expected["quadrature_messages"], "density messages")
        val = arrays[item["values_key"]]
        err = arrays[item["errors_key"]]
        tail = arrays[item["tails_key"]]
        if err.shape != (3,) or np.any(err < 0) or np.any(tail < 0):
            raise ValueError("invalid saved density error estimates")
        if np.any(np.abs(val - iv[idx]) > 8 * err + tail + abs_tol + rel_tol * np.abs(iv[idx])):
            raise ValueError("density reference disagreement")
        if abs(item["lr_gamma"] - val[2]) > 8 * item["lr_gamma_error_estimate"] + 8e-10:
            if item["status"] != "lr_gamma_cancellation":
                raise ValueError("density Gamma score disagreement")
    grid = {name: arrays[key] for name, key in r["hermite"]["keys"].items()}
    expected_grid = analytics.build_hermite(_effective_protocol(p, execution))
    for name in expected_grid:
        if not np.isfinite(grid[name]).all():
            raise ValueError("invalid nonfinite Hermite node data")
        _close(grid[name], expected_grid[name], f"Hermite grid/{name}")
    prepared = analytics.prepare_hermite(grid)
    for split, dataset in r["datasets"].items():
        x = arrays[dataset["inputs_key"]]
        expected = analytics.hermite_predict(prepared, x, p)
        _close(arrays[r["hermite"]["predictions"][split]], expected, f"Hermite/{split}")
    hermite_test = arrays[r["hermite"]["predictions"]["test"]]
    _nested_close(
        r["hermite"]["test_errors"],
        analytics.error_summary(hermite_test, ys, strike=p["contract"]["strike"]),
        "Hermite errors",
    )
    _nested_close(
        r["hermite"]["test_buckets"],
        analytics.bucket_errors(hermite_test, ys, tx, p),
        "Hermite buckets",
    )
    learner = _learner()
    train = r["datasets"]["train"]
    train_x, labels = arrays[train["inputs_key"]], arrays[train["labels_key"]]
    scale = learner.normalization(
        train_x, labels[:, 0], labels[:, 1], strike=p["contract"]["strike"]
    )
    if len(r["fits"]) != 2 * len(execution["paired_seed_ids"]) or len(r["initializations"]) != len(
        execution["paired_seed_ids"]
    ):
        raise ValueError("original fit slot roster changed")
    initialized = {item["id"]: item for item in r["initializations"]}
    settings = execution["fit"]
    diagnostics = arrays[r["diagnostics"]["inputs_key"]]
    _close(diagnostics, _safe_diagnostic_inputs(p), "diagnostic original inputs")
    diagnostic_reference = np.full((len(diagnostics), 3), np.nan)
    diagnostic_valid = (
        (diagnostics[:, 0] > 0)
        & (diagnostics[:, 1] >= 0)
        & (diagnostics[:, 1] <= 390 * 60)
        & np.isin(diagnostics[:, 2], [0, 1])
    )
    diagnostic_reference[diagnostic_valid] = analytics.oracle(diagnostics[diagnostic_valid], p)
    _close(arrays[r["diagnostics"]["reference_key"]], diagnostic_reference, "diagnostic oracle")
    for key, value in [
        ("original_count", len(diagnostics)),
        ("invalid_contract_count", int((~diagnostic_valid).sum())),
        ("price_defined_count", int(np.isfinite(diagnostic_reference[:, 0]).sum())),
        ("ordinary_greeks_defined_count", int(np.isfinite(diagnostic_reference).all(axis=1).sum())),
        ("expiry_atm_unknown_count", 1),
    ]:
        if r["diagnostics"][key] != value:
            raise ValueError("diagnostic original denominator changed")
    fit_ids = set()
    for i, fit in enumerate(r["fits"]):
        if (
            fit["id"] != f"fit{i}"
            or fit["id"] in fit_ids
            or fit["pair_id"] != i // 2
            or fit["dml"] != bool(i % 2)
        ):
            raise ValueError("original paired fit order changed")
        fit_ids.add(fit["id"])
        pair = initialized[fit["initial_weights_id"]]
        expected_pair = execution["paired_seed_ids"][i // 2]
        if (
            pair["seed_id"] != expected_pair["init"]
            or pair["batch_seed_id"] != expected_pair["batch"]
        ):
            raise ValueError("initialization physical seed id changed")
        if pair["seed"] != protocol.seed_for(p, pair["seed_id"]) or pair[
            "batch_seed"
        ] != protocol.seed_for(p, pair["batch_seed_id"]):
            raise ValueError("initialization concrete seed changed")
        _nested_close(fit["normalization"], _plain(scale), "train-only normalization")
        stats, batches = fit["stats"], arrays[fit["batch_indices_key"]]
        master = arrays[pair["batch_roster_key"]]
        if (
            master.shape != (settings["max_updates"], settings["batch_size"])
            or master.dtype.kind not in "iu"
            or np.any(master < 0)
            or np.any(master >= len(train_x))
            or batches.shape != (stats["batch_attempts"], settings["batch_size"])
            or not 0 <= stats["updates"] <= len(batches) <= settings["max_updates"]
        ):
            raise ValueError("invalid attempted batch or actual update count")
        _close(batches, master[: len(batches)], "paired batch order")
        if (
            stats["seed"] != pair["seed"]
            or stats["batch_seed"] != pair["batch_seed"]
            or stats["dml"] != fit["dml"]
            or stats["gamma_loss"]
        ):
            raise ValueError("fit seed/loss metadata changed")
        if (
            stats["requested_updates"] != settings["max_updates"]
            or stats["batch_size"] != settings["batch_size"]
        ):
            raise ValueError("fit update cap changed")
        if stats["complete"] != (stats["status"] == "completed") or (
            stats["complete"] and stats["updates"] != settings["max_updates"]
        ):
            raise ValueError("fit completion or original failure status changed")
        if fit["initial_weights_id"] != f"pair{i // 2}":
            raise ValueError("fit original paired initialization changed")
        if (
            stats["learning_rate"] != settings["learning_rate"]
            or stats["budget_s"] != settings["budget_s"]
            or stats["threads"] != 1
            or stats["strike"] != p["contract"]["strike"]
        ):
            raise ValueError("fit frozen optimization/thread conditions changed")
        if stats["complete"]:
            if (
                stats["initial_loss"] is None
                or stats["final_loss"] is None
                or not np.isfinite([stats["initial_loss"], stats["final_loss"]]).all()
                or stats["reason"] is not None
            ):
                raise ValueError("completed fit needs finite observed objectives")
            if not all(np.isfinite(v).all() for v in _weights(fit, arrays).values()):
                raise ValueError("completed fit has invalid nonfinite weights")
        _close(stats["teacher_s"], r["costs"]["shared_train_teacher_s"], "fit shared teacher cap")
        _close(
            stats["teacher_and_training_s"],
            stats["training_s"] + stats["teacher_s"],
            "fit time total",
        )
        _close(
            stats["overrun_s"],
            max(0.0, stats["teacher_and_training_s"] - stats["budget_s"]),
            "fit overrun",
        )
        initial_w = {name: arrays[key] for name, key in pair["weights_keys"].items()}
        _fit_lifecycle(fit, arrays, initial_w)
        if stats["initial_loss"] is not None:
            _close(
                stats["initial_loss"],
                _loss(initial_w, scale, train_x, labels, fit["dml"], p["contract"]["strike"]),
                "initial objective",
            )
        w = _weights(fit, arrays)
        if stats["final_loss"] is not None:
            _close(
                stats["final_loss"],
                _loss(w, scale, train_x, labels, fit["dml"], p["contract"]["strike"]),
                "final objective",
            )
        for split, dataset in r["datasets"].items():
            x = arrays[dataset["inputs_key"]]
            pred = fit["predictions"][split]
            raw = _prediction(w, scale, x, p["contract"]["strike"])
            safe = analytics.safe_route(raw, x, p)
            _close(arrays[pred["raw_key"]], raw, "raw model prediction")
            _close(arrays[pred["safe_key"]], safe["values"], "safe prediction")
            _close(arrays[pred["routes_key"]], safe["routes"], "safe routes")
            if pred["original_count"] != len(x) or pred["raw_count"] != safe["raw_count"]:
                raise ValueError("prediction original denominator changed")
            _nested_close(
                pred["raw_errors"],
                analytics.error_summary(
                    raw, arrays[dataset["oracle_key"]], strike=p["contract"]["strike"]
                ),
                "raw errors",
            )
            _nested_close(
                pred["safe_errors"],
                analytics.error_summary(
                    safe["values"], arrays[dataset["oracle_key"]], strike=p["contract"]["strike"]
                ),
                "safe errors",
            )
        _nested_close(
            fit["test_buckets"],
            analytics.bucket_errors(arrays[fit["predictions"]["test"]["raw_key"]], ys, tx, p),
            "raw bucket errors",
        )
        _nested_close(
            fit["safe_test_buckets"],
            analytics.bucket_errors(arrays[fit["predictions"]["test"]["safe_key"]], ys, tx, p),
            "safe bucket errors",
        )
        raw = _diagnostic_raw(w, scale, diagnostics, p)
        safe = analytics.safe_route(raw, diagnostics, p)
        for name, value in [("raw", raw), ("safe", safe["values"]), ("routes", safe["routes"])]:
            _close(arrays[fit["diagnostics"][f"{name}_key"]], value, "diagnostic values/routes")
        _nested_close(
            fit["diagnostics"]["route_counts"],
            {
                str(route): int(np.sum(safe["routes"] == route))
                for route in np.unique(safe["routes"])
            },
            "diagnostic route counts",
        )
        _nested_close(
            fit["diagnostics"]["raw_errors"],
            analytics.error_summary(raw, diagnostic_reference, strike=p["contract"]["strike"]),
            "diagnostic raw errors",
        )
        _nested_close(
            fit["diagnostics"]["safe_errors"],
            analytics.error_summary(
                safe["values"], diagnostic_reference, strike=p["contract"]["strike"]
            ),
            "diagnostic safe errors",
        )
    expected_timing = []
    methods = [
        "core_mixture",
        "hermite",
        *(f"{fit['id']}/{route}" for fit in r["fits"] for route in ["raw", "safe"]),
    ]
    for minutes in p["remaining_minutes"]:
        for event in [0, 1]:
            ids = np.flatnonzero((tx[:, 1] == minutes * 60) & (tx[:, 2] == event))
            if len(ids):
                for batch in execution["timing"]["batches"]:
                    for method in methods:
                        expected_timing.append(
                            (minutes, event, batch, method, np.resize(ids, batch))
                        )
    if len(r["timing"]) != len(expected_timing):
        raise ValueError("timing original bucket/method roster changed")
    fit_map = {fit["id"]: fit for fit in r["fits"]}
    for i, (t, expected) in enumerate(zip(r["timing"], expected_timing, strict=True)):
        minutes, event, batch, method, indices = expected
        if (t["minutes"], t["event"], t["batch_size"], t["method"], t["order"]) != (
            minutes,
            event,
            batch,
            method,
            i,
        ):
            raise ValueError("timing fixed method order changed")
        if (
            t["warmup"] != execution["timing"]["warmup"]
            or t["repetitions"] != execution["timing"]["repetitions"]
            or t["scope"] != "whole returned price, physical Delta, Gamma and route"
        ):
            raise ValueError("timing whole-call metadata changed")
        _close(arrays[t["input_indices_key"]], indices, "timing original indices")
        y, routes = _call(method, tx[indices], p, prepared, fit_map, arrays)
        reps, warm = execution["timing"]["repetitions"], execution["timing"]["warmup"]
        _close(
            arrays[t["values_key"]],
            np.repeat(y[None], reps + warm, axis=0),
            "timing whole returned values",
        )
        _close(
            arrays[t["routes_key"]],
            np.repeat(routes[None], reps + warm, axis=0),
            "timing whole routes",
        )
        seconds = arrays[t["seconds_key"]]
        if seconds.shape != (reps,) or not np.isfinite(seconds).all() or np.any(seconds < 0):
            raise ValueError("invalid timing observations")
    totals = analytics.expense_totals(r["expenses"])
    _nested_close(r["costs"]["categorized"], totals, "cost account")
    _close(r["costs"]["main_only_s"], totals["measured_seconds"], "main-only categorized cost")
    train_s = sum(e["seconds"] for e in r["expenses"] if e["category"] == "teacher_train")
    _close(r["costs"]["shared_train_teacher_s"], train_s, "shared train teacher cost")
    for fit in r["fits"]:
        expense = [e for e in r["expenses"] if e["id"] == f"fit/{fit['id']}"]
        if len(expense) != 1:
            raise ValueError("fit cost identity changed")
        _close(expense[0]["seconds"], fit["stats"]["training_s"], "fit measured cost")
    if not {"serialization", "cold_import", "pilot_freeze", "fresh"} <= set(totals["pending_ids"]):
        raise ValueError("unmeasured pipeline cost was promoted to measured")
    checked = {
        "passed": True,
        "mode": r["mode"],
        "teacher_slots": teacher_count,
        "fit_slots": len(r["fits"]),
        "original_test_count": len(tx),
        "timing_slots": len(r["timing"]),
        "accepted": False,
        "scope": "saved-only numeric reconstruction; no RNG, training, optimizer or main adoption",
    }
    if "saved_check" in r:
        _nested_close(r["saved_check"], checked, "stored saved-check report")
    return checked


def check_record(record, arrays):
    """Reconstruct the complete saved record with a closed measured charge roster."""
    return _check_record(record, arrays, recording=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DIRECTORY)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--mode", choices=["main", "smoke"], default="main")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        record, arrays = load_result(args.directory)
        print(json.dumps(check_record(record, arrays), indent=2))
    else:
        p = (
            module("protocol").candidate_protocol()
            if args.mode == "smoke" and args.protocol is None
            else module("protocol").load_protocol(args.protocol)
        )
        record, arrays = run_study(p, args.directory, mode=args.mode)
        print(
            json.dumps(
                {
                    "mode": record["mode"],
                    "fit_slots": len(record["fits"]),
                    "accepted": False,
                    "npz_arrays": len(arrays),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
