"""Torch/teacher-free batch timing evidence and discrete-barrier cost accounts.

Callbacks supply price and physical spot Delta. Raw evaluation and the saved
replay serving policy are measured separately, including identical safe rules
for the oracle. Cost units are measured whole-batch calls, never fractions of
a batch. This module performs no training and imports no financial teacher.
"""

from __future__ import annotations

import hashlib
import importlib.util
from copy import deepcopy
from math import ceil, isclose, isfinite
from pathlib import Path
from time import perf_counter

import numpy as np

HERE = Path(__file__).resolve().parent
PHASES = ("raw", "safe")
COUNTS = (1, 10, 100, 1000, 10000)
UNSUPPORTED = frozenset({"oracle_failure", "unsupported", "invalid", "delta_undefined"})
_REPLAY = None


def _replay():
    global _REPLAY
    if _REPLAY is None:
        spec = importlib.util.spec_from_file_location(
            "discrete_barrier_benchmark_replay", HERE / "replay.py"
        )
        _REPLAY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_REPLAY)
    return _REPLAY


def _registry(protocol):
    contract = protocol["contract"]
    fixed = {
        "model": "GBM",
        "strike": 100,
        "barrier": 120,
        "rate": 0.03,
        "volatility": 0.2,
        "rebate": 0,
        "dividend": 0,
        "positive_monitoring": 12,
        "include_zero": True,
        "include_maturity": True,
        "touch": "S>=H knocks out",
    }
    for name, value in fixed.items():
        actual = contract[name]
        equal = (
            isclose(float(actual), float(value), rel_tol=1e-12, abs_tol=1e-12)
            if isinstance(value, (float, int))
            else actual == value
        )
        if not equal:
            raise ValueError("benchmark serving contract differs from the fixed study")
    if not np.allclose(
        protocol["domain"]["spot"], [80.0, 119.0], atol=1e-12, rtol=1e-12
    ) or not np.allclose(protocol["domain"]["maturity"], [0.25, 2.0], atol=1e-12, rtol=1e-12):
        raise ValueError("benchmark domain differs from the serving policy")
    training, timing = protocol["learning"], protocol["timing"]
    if training["modes"] != ["price", "dml"] or training["seeds"] != [11, 29, 47]:
        raise ValueError("fixed paired method registry required")
    if (
        timing["warmups"] != 3
        or timing["repeats"] != 20
        or timing["batches"] != [1, 32]
        or timing["operation"] != "price+spot Delta"
        or not np.allclose(timing["quantiles"], [0.5, 0.95])
    ):
        raise ValueError("fixed warmups/repeats/batches/price+Delta timing protocol required")
    return [f"{mode}_s{seed}" for mode in training["modes"] for seed in training["seeds"]] + [
        "hermite",
        "oracle",
    ]


def _inputs(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all() or np.any(x <= 0):
        raise ValueError("finite positive nonempty [spot,maturity] inputs required")
    if not np.all(_replay().inside(x)):
        raise ValueError("raw timing inputs must lie inside the fixed training domain")
    return x


def _batch(inputs, phase, batch):
    result = inputs[np.arange(batch) % len(inputs)].copy()
    if phase == "safe":
        if batch == 1:
            result[:] = [100.0, 1.0]
        else:
            result[-4:] = [[70.0, 0.1], [100.0, 3.0], [120.0, 1.0], [121.0, 1.0]]
    return result


def _summary(samples, routing):
    names, counts = np.unique(routing, return_counts=True)
    tally = {str(name): int(count) for name, count in zip(names, counts, strict=True)}
    return {
        "median_s": float(np.median(samples)),
        "p95_s": float(np.quantile(samples, 0.95)),
        "routing_counts": tally,
        "routing_per_call": {name: count / len(samples) for name, count in tally.items()},
    }


def _comparison(routing_counts):
    reasons = sorted(
        name for name, count in routing_counts.items() if name in UNSUPPORTED and count
    )
    return {
        "comparison_status": "unsupported" if reasons else "supported",
        "unsupported_reasons": reasons,
    }


def _output_summary(outputs):
    columns = np.asarray(outputs, dtype=float).reshape(-1, 2)
    result = {"finite_count": [], "nan_count": [], "mean": [], "min": [], "max": []}
    for column in columns.T:
        finite = column[np.isfinite(column)]
        result["finite_count"].append(len(finite))
        result["nan_count"].append(int(np.count_nonzero(np.isnan(column))))
        for name, function in (("mean", np.mean), ("min", np.min), ("max", np.max)):
            result[name].append(float(function(finite)) if len(finite) else None)
    return result


def measure(functions, inputs, oracle, protocol):
    """Measure all eight methods, raw/safe and batch1/32; retain every sample.

    Safe batch32 has two OOD rows, initial contact and initial knockout. All
    methods, including the oracle, use exactly replay.serve's policy. Warmups
    are excluded. The source digest is provenance, not a numeric identity test.
    """
    methods = _registry(protocol)
    if (
        set(functions) != set(methods)
        or not all(callable(functions[name]) for name in methods)
        or functions["oracle"] is not oracle
    ):
        raise ValueError("complete fixed callback registry with the shared oracle required")
    original = _inputs(inputs).copy()
    record = {
        "schema": 1,
        "protocol": deepcopy(protocol),
        "method_ids": methods,
        "phases": list(PHASES),
        "settings": {**deepcopy(protocol["timing"]), "unit": "seconds_per_batch"},
        "input_registry": {"original": original.tolist()},
        "measurements": [],
        "source_digest": {
            name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in ("benchmarks.py", "replay.py")
        },
    }
    arrays = {
        "benchmark_inputs": original,
        "benchmark_method_ids": np.asarray(methods),
        "benchmark_phases": np.asarray(PHASES),
        "benchmark_batches": np.asarray(protocol["timing"]["batches"]),
    }
    for method in methods:
        for phase in PHASES:
            for batch in protocol["timing"]["batches"]:
                identifier = f"{method}__{phase}__batch{batch}"
                input_key = f"benchmark_inputs__{phase}__batch{batch}"
                x = _batch(original, phase, batch)
                arrays[input_key] = x.copy()

                def call(fn=functions[method], x=x, phase=phase):
                    if phase == "raw":
                        return fn(x), None
                    served = _replay().serve(fn, x, oracle)
                    return served["prediction"], served["status"]

                for _ in range(protocol["timing"]["warmups"]):
                    call()
                seconds, routes, outputs = [], [], []
                for _ in range(protocol["timing"]["repeats"]):
                    started = perf_counter()
                    output, routing = call()
                    elapsed = perf_counter() - started
                    if routing is None:
                        # Raw provenance bookkeeping is outside the inference
                        # timer; safe routing is real serving work inside it.
                        routing = np.full(batch, "raw", dtype="<U20")
                    output, routing = np.asarray(output, dtype=float), np.asarray(routing)
                    if output.shape != (batch, 2) or routing.shape != (batch,):
                        raise ValueError("callbacks must return aligned price+Delta rows")
                    if phase == "raw" and not np.isfinite(output).all():
                        raise ValueError("raw callback returned nonfinite price/Delta")
                    seconds.append(elapsed)
                    routes.append(routing.copy())
                    # Evidence copying and summaries are outside the timer.
                    outputs.append(output.copy())
                raw_key, routing_key = f"timing__{identifier}", f"routing__{identifier}"
                output_key = f"benchmark_output__{identifier}"
                arrays[raw_key], arrays[routing_key] = np.asarray(seconds), np.asarray(routes)
                arrays[output_key] = np.asarray(outputs)
                summary = _summary(arrays[raw_key], arrays[routing_key])
                record["measurements"].append(
                    {
                        "id": identifier,
                        "method_id": method,
                        "phase": phase,
                        "batch_size": batch,
                        "operation": protocol["timing"]["operation"],
                        "raw_key": raw_key,
                        "routing_key": routing_key,
                        "output_key": output_key,
                        "input_key": input_key,
                        **summary,
                        "output_summary": _output_summary(arrays[output_key]),
                        **_comparison(summary["routing_counts"]),
                    }
                )
    return record, arrays


def _topology(record):
    methods = _registry(record["protocol"])
    if record["method_ids"] != methods or record["phases"] != list(PHASES):
        raise ValueError("saved timing registry mismatch")
    if record["settings"] != {**record["protocol"]["timing"], "unit": "seconds_per_batch"}:
        raise ValueError("saved timing settings mismatch")
    expected = {
        (method, phase, batch)
        for method in methods
        for phase in PHASES
        for batch in record["settings"]["batches"]
    }
    rows = {}
    for item in record["measurements"]:
        key = item["method_id"], item["phase"], item["batch_size"]
        if key not in expected or key in rows:
            raise ValueError("duplicate/unexpected timing measurement")
        identifier = f"{key[0]}__{key[1]}__batch{key[2]}"
        if (
            item["id"] != identifier
            or item["raw_key"] != f"timing__{identifier}"
            or item["routing_key"] != f"routing__{identifier}"
            or item["output_key"] != f"benchmark_output__{identifier}"
            or item["input_key"] != f"benchmark_inputs__{key[1]}__batch{key[2]}"
            or item["operation"] != record["settings"]["operation"]
        ):
            raise ValueError("measurement registry keys mismatch")
        for statistic in ("median", "p95"):
            _seconds(item[f"{statistic}_s"], statistic)
        if item["p95_s"] < item["median_s"]:
            raise ValueError("p95 smaller than median")
        comparison = _comparison(item["routing_counts"])
        if any(item[name] != value for name, value in comparison.items()):
            raise ValueError("unsupported timing comparison status mismatch")
        rows[key] = item
    if set(rows) != expected:
        raise ValueError("missing method/phase/batch measurement")
    return rows


def _routing_valid(routing, phase, x):
    if phase == "raw":
        return np.all(routing == "raw")
    inside = _replay().inside(x)
    for index, (spot, _) in enumerate(x):
        allowed = (
            {"delta_undefined"}
            if spot == 120
            else {"knocked_out"}
            if spot > 120
            else {"approximation", "fallback", "oracle_failure"}
            if inside[index]
            else {"fallback", "oracle_failure"}
        )
        if not set(map(str, routing[:, index])) <= allowed:
            return False
    return True


def _values_valid(output, routing, phase, x):
    """Check failure/KO/contact values without treating undefined Delta as zero."""
    if phase == "raw":
        return np.isfinite(output).all()
    for index, (_, maturity) in enumerate(x):
        values, statuses = output[:, index], routing[:, index]
        for status in np.unique(statuses):
            subset = values[statuses == status]
            if status in {"approximation", "fallback"}:
                cap = 20.0 * np.exp(-0.03 * maturity)
                if not np.isfinite(subset).all() or np.any(
                    (subset[:, 0] < 0) | (subset[:, 0] > cap)
                ):
                    return False
            elif status == "delta_undefined":
                if not np.all(subset[:, 0] == 0) or not np.isnan(subset[:, 1]).all():
                    return False
            elif status == "knocked_out":
                if not np.all(subset == 0):
                    return False
            elif status in {"oracle_failure", "unsupported", "invalid"}:
                if not np.isnan(subset).all():
                    return False
            else:
                return False
    return True


def _check_output_summary(saved, outputs):
    expected = _output_summary(outputs)
    if set(saved) != set(expected):
        raise ValueError("saved output summary keys mismatch")
    for name in expected:
        if len(saved[name]) != 2:
            raise ValueError("saved output summary shape mismatch")
        for actual, value in zip(saved[name], expected[name], strict=True):
            if value is None:
                if actual is not None:
                    raise ValueError("saved nonfinite output summary mismatch")
            elif name.endswith("count"):
                if actual != value:
                    raise ValueError("saved output count summary mismatch")
            else:
                _equal(actual, value, "output " + name)


def check_measurements(
    record, arrays, *, replay_callbacks=None, oracle=None, rtol=1e-8, atol=1e-10
):
    """Check saved values/routes and optionally replay independent callbacks.

    A valid failure record or contract contact can pass this evidence audit;
    its price+ordinary-Delta comparison remains explicitly unsupported.
    Replay callbacks must cover the fixed eight-method registry. No callbacks
    means numeric replay is unverified, not a claim that prices are correct.
    """
    failures, checked, replayed = [], 0, 0
    try:
        rows = _topology(record)
        if replay_callbacks is not None:
            if set(replay_callbacks) != set(record["method_ids"]) or not all(
                callable(function) for function in replay_callbacks.values()
            ):
                raise ValueError("complete independent replay callback registry required")
            oracle = replay_callbacks["oracle"] if oracle is None else oracle
            if not callable(oracle) or replay_callbacks["oracle"] is not oracle:
                raise ValueError("shared independent replay oracle required")
        elif oracle is not None:
            raise ValueError("oracle requires independent replay callbacks")
        if not isfinite(rtol) or not isfinite(atol) or min(rtol, atol) < 0:
            raise ValueError("finite nonnegative replay tolerances required")
        original = _inputs(record["input_registry"]["original"])
        if np.asarray(arrays["benchmark_inputs"]).shape != original.shape or not np.allclose(
            arrays["benchmark_inputs"], original, rtol=1e-12, atol=1e-12
        ):
            raise ValueError("original timing input registry mismatch")
        for key, expected in (
            ("benchmark_method_ids", record["method_ids"]),
            ("benchmark_phases", list(PHASES)),
            ("benchmark_batches", record["settings"]["batches"]),
        ):
            if np.asarray(arrays[key]).tolist() != expected:
                raise ValueError("saved array registry mismatch")
        expected_keys = {
            "benchmark_inputs",
            "benchmark_method_ids",
            "benchmark_phases",
            "benchmark_batches",
        }
        for row in rows.values():
            expected_keys.update(
                row[key] for key in ("raw_key", "routing_key", "output_key", "input_key")
            )
            samples = np.asarray(arrays[row["raw_key"]], dtype=float)
            routing = np.asarray(arrays[row["routing_key"]])
            output = np.asarray(arrays[row["output_key"]], dtype=float)
            expected_input = _batch(original, row["phase"], row["batch_size"])
            saved_input = np.asarray(arrays[row["input_key"]], dtype=float)
            if saved_input.shape != expected_input.shape or not np.allclose(
                saved_input, expected_input, rtol=1e-12, atol=1e-12
            ):
                raise ValueError("timed batch input mismatch")
            if (
                samples.shape != (record["settings"]["repeats"],)
                or not np.isfinite(samples).all()
                or np.any(samples < 0)
            ):
                raise ValueError("finite nonnegative aligned timing samples required")
            if routing.shape != (len(samples), row["batch_size"]) or not _routing_valid(
                routing, row["phase"], expected_input
            ):
                raise ValueError("aligned serving-route observations required")
            if output.shape != (len(samples), row["batch_size"], 2) or not _values_valid(
                output, routing, row["phase"], expected_input
            ):
                raise ValueError(
                    "saved price/Delta values disagree with serving status or contract"
                )
            _check_output_summary(row["output_summary"], output)
            if replay_callbacks is not None:
                callback = replay_callbacks[row["method_id"]]
                if row["phase"] == "raw":
                    reference = np.asarray(callback(expected_input), dtype=float)
                    reference_routing = np.full(row["batch_size"], "raw")
                else:
                    served = _replay().serve(callback, expected_input, oracle)
                    reference = np.asarray(served["prediction"], dtype=float)
                    reference_routing = np.asarray(served["status"])
                if reference.shape != (row["batch_size"], 2) or not np.allclose(
                    output, reference[None, :, :], rtol=rtol, atol=atol, equal_nan=True
                ):
                    raise ValueError("saved price/Delta differs from independent numeric replay")
                if reference_routing.shape != (row["batch_size"],) or not np.all(
                    routing == reference_routing[None, :]
                ):
                    raise ValueError("saved serving route differs from independent replay")
                replayed += 1
            summary = _summary(samples, routing)
            for statistic in ("median_s", "p95_s"):
                _equal(row[statistic], summary[statistic], "timing summary")
            if row["routing_counts"] != summary["routing_counts"]:
                raise ValueError("routing count summary mismatch")
            if set(row["routing_per_call"]) != set(summary["routing_per_call"]):
                raise ValueError("routing per-call summary mismatch")
            for name, value in summary["routing_per_call"].items():
                _equal(row["routing_per_call"][name], value, "routing per-call")
            checked += 1
        owned_keys = {
            key
            for key in arrays
            if key.startswith(("timing__", "routing__", "benchmark_inputs__", "benchmark_output__"))
            or key
            in ("benchmark_inputs", "benchmark_method_ids", "benchmark_phases", "benchmark_batches")
        }
        if owned_keys != expected_keys:
            raise ValueError("missing or orphan timing/input/routing/output arrays")
    except (KeyError, ValueError, TypeError, IndexError) as error:
        failures.append(str(error))
    return {
        "passed": not failures,
        "failures": failures,
        "checked_measurements": checked,
        "replayed_measurements": replayed,
        "numeric_replay": "verified" if not failures and replayed == len(rows) else "unverified",
    }


def _seconds(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"finite nonnegative {name} seconds required") from error
    if not isfinite(result) or result < 0:
        raise ValueError(f"finite nonnegative {name} seconds required")
    return result


def _equal(actual, expected, name):
    if not isclose(float(actual), float(expected), rel_tol=1e-8, abs_tol=1e-12):
        raise ValueError(f"{name} disagrees with its measured components")


def _loading(loading_s):
    common = {
        "scope": "full_compressed_research_bundle_warm_cache_decode",
        "excludes": [
            "cold_filesystem_io",
            "process_start",
            "module_import",
            "minimal_standalone_packaging",
        ],
        "assumption": "Each NN/hermite deployment loads the entire research bundle once; this is not minimal standalone packaging.",
    }
    if loading_s is None:
        return {"status": "missing", "median_s": None, "p95_s": None, **common}
    if isinstance(loading_s, dict):
        median, p95 = (_seconds(loading_s[f"{name}_s"], "loading") for name in ("median", "p95"))
        if p95 < median:
            raise ValueError("loading p95 smaller than median")
        return {
            **common,
            **deepcopy(loading_s),
            "status": "measured",
            "median_s": median,
            "p95_s": p95,
        }
    value = _seconds(loading_s, "loading")
    return {
        **common,
        "status": "scalar_cost_assumption",
        "median_s": value,
        "p95_s": value,
        "statistic_note": "A supplied scalar is the same declared component charge in both scenarios, not a measured p95.",
    }


def _cost_models(models, offline, methods):
    if set(models) != set(methods[:-2]):
        raise ValueError("complete six-model cost metadata required")
    result, teacher, initialization = {}, None, None
    for identifier in methods[:-2]:
        item = models[identifier]
        if (
            item.get("budget_failure") is not False
            or item["updates"] != item["requested_updates"]
            or item["updates"] <= 0
        ):
            raise ValueError("failed or incomplete fit cannot support deployment cost")
        components = {
            name: _seconds(item[name], name)
            for name in (
                "train_teacher_s",
                "setup_s",
                "training_s",
                "elapsed_s",
                "export_s",
                "offline_s",
            )
        }
        components["common_initialization_s"] = _seconds(
            item.get("common_initialization_s", 0.0), "common_initialization_s"
        )
        if teacher is None:
            teacher = components["train_teacher_s"]
            initialization = components["common_initialization_s"]
        _equal(components["train_teacher_s"], teacher, "shared conditioned teacher cost")
        _equal(
            components["common_initialization_s"], initialization, "shared CPU initialization cost"
        )
        overhead = components["elapsed_s"] - components["setup_s"] - components["training_s"]
        if overhead < -1e-9:
            raise ValueError("setup+training exceeds elapsed fit cost")
        known = (
            components["train_teacher_s"]
            + components["elapsed_s"]
            + components["export_s"]
            + components["common_initialization_s"]
        )
        _equal(components["offline_s"], known, "offline_s")
        result[identifier] = {
            **components,
            "fit_overhead_s": max(0.0, overhead),
            "offline_without_load_s": known,
            "accounting": "teacher+elapsed_s+export_s+common_initialization_s; shared initialization is charged once per standalone NN; setup/training are components of elapsed_s, not extra costs",
        }
    try:
        grid = _seconds(
            offline["hermite"]["grid_setup_s"], "hermite grid generation and construction"
        )
    except KeyError as error:
        raise ValueError("measured hermite grid_setup_s required") from error
    result["hermite"] = {"grid_setup_s": grid, "offline_without_load_s": grid}
    result["oracle"] = {
        "offline_without_load_s": 0.0,
        "accounting": "no fit/load; numerical reference calculation is inside the measured online callback",
    }
    return result


def _scenario(offline, online, reference, batch):
    def total(calls, requested=None):
        return {
            "measured_calls": calls,
            "processed_rows": calls * batch,
            "requested_queries": requested,
            "surrogate_s": offline + calls * online,
            "reference_s": calls * reference,
        }

    saving = reference - online
    recovery = {
        "offline_difference_s": offline,
        "online_saving_s_per_batch": saving,
        "initial_advantage": offline <= 0,
    }
    if saving <= 0:
        recovery.update(
            status="no_online_advantage",
            continuous_calls=None,
            first_integer_call=None,
            rows_at_first_integer_call=None,
        )
    else:
        calls = max(0.0, offline / saving)
        integer = ceil(calls)
        recovery.update(
            status="advantage_from_start" if offline <= 0 else "break_even",
            continuous_calls=calls,
            first_integer_call=integer,
            rows_at_first_integer_call=integer * batch,
        )
    return {
        "offline_s": offline,
        "batch_counts": {str(n): total(n) for n in COUNTS},
        "query_counts": {str(n): total(ceil(n / batch), n) for n in COUNTS},
        "break_even": recovery,
    }


def cost_summary(record, models_metadata, offline_metadata, loading_s):
    """Account matched whole-batch costs after independent measurement checking.

    Each NN owes its common training-label generation plus elapsed fit, export,
    one shared CPU initialization and one bundle load. Legacy metadata without
    a common-initialization measurement retains an explicit zero charge.
    Hermite owes grid generation/construction plus load;
    the matched oracle owes no offline fit/load. Unknown loading stays missing.
    Summed p95 components are a scenario, not a measured p95 total or a CI.
    """
    rows = _topology(record)
    models = _cost_models(models_metadata, offline_metadata, record["method_ids"])
    if "common_initialization_s" in record:
        common = _seconds(record["common_initialization_s"], "record common_initialization_s")
        for identifier in record["method_ids"][:-2]:
            _equal(
                models[identifier]["common_initialization_s"], common, "record CPU initialization"
            )
    loading = _loading(loading_s)
    comparisons = []
    for (method, phase, batch), row in rows.items():
        oracle = rows["oracle", phase, batch]
        reasons = [
            f"{name}:{reason}"
            for name, item in (("method", row), ("reference", oracle))
            for reason in item["unsupported_reasons"]
        ]
        supported = not reasons
        statistics = {}
        for name in ("median", "p95"):
            online, reference = float(row[f"{name}_s"]), float(oracle[f"{name}_s"])
            offline = models[method]["offline_without_load_s"]
            deployment = None
            if supported and (method == "oracle" or loading["status"] != "missing"):
                deployment = _scenario(
                    offline + (0.0 if method == "oracle" else loading[f"{name}_s"]),
                    online,
                    reference,
                    batch,
                )
            statistics[name] = {
                "surrogate_online_s_per_batch": online,
                "reference_online_s_per_batch": reference,
                "training_only": _scenario(offline, online, reference, batch)
                if supported
                else None,
                "deployment": deployment,
            }
        comparisons.append(
            {
                "method_id": method,
                "phase": phase,
                "batch_size": batch,
                "operation": row["operation"],
                "measurement_id": row["id"],
                "reference_id": oracle["id"],
                "comparison_status": "supported" if supported else "unsupported",
                "unsupported_reasons": reasons,
                "statistics": statistics,
            }
        )
    return {
        "schema": 1,
        "unit": "seconds_per_measured_whole_batch_call",
        "formula": "C(N_calls)=offline+N_calls*online_per_batch",
        "query_policy": "ceil(N_queries/batch_size) full/padded calls; never amortized fractional calls",
        "offline_reference_s": 0.0,
        "models": models,
        "loading": loading,
        "comparisons": comparisons,
        "unmeasured_boundary": offline_metadata.get(
            "unmeasured",
            ["cold_filesystem_io", "process_start", "module_import", "benchmark_execution"],
        ),
        "p95_policy": "Sum of observed p95 components is a component scenario, not measured total p95 or a confidence interval.",
        "unsupported_policy": "Measured latency remains recorded, but an entire price+ordinary-Delta batch containing failed or undefined outputs cannot support successful speed or cost-recovery comparisons.",
        "experiment_accounting": "Shared train labels are generated once across the experiment; per-model deployment comparisons charge them to each standalone fit, not as an all-experiment sum.",
    }
