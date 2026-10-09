"""Add checked inference/loading measurements to saved barrier fits.

Refresh never fits a model. Check never times a callback: it replays saved
price/Delta outputs and recomputes summaries from the retained timing samples.
The warm loading artifact is the input archive before measurement arrays are
added, so its digest is historical provenance rather than the final digest.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from time import perf_counter

import numpy as np

HERE = Path(__file__).resolve().parent
_MODULES = {}
_UNMEASURED = [
    "cold_filesystem_io",
    "process_start",
    "module_import",
    "teacher_module_import",
    "protocol_loading",
    "source_discovery",
    "minimal_standalone_packaging",
    "benchmark_execution",
    "report_and_plot_generation",
]


def _module(name):
    if name not in _MODULES:
        spec = importlib.util.spec_from_file_location(
            "barrier_finalize_" + name, HERE / (name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULES[name] = module
    return _MODULES[name]


def _runner():
    return _module("build_reference")


def _benchmarks():
    return _module("benchmarks")


def checked_oracle(protocol, teacher):
    """Prepare a fixed-contract oracle with no file IO or result memoization.

    All methods share this callback for raw reference and safe fallback. Each
    call recomputes GL128 and GL256, shares exact-equal T kernels within the
    call, and includes both tail bounds in the convergence check.
    """
    p = copy.deepcopy(protocol)
    contract = {key: p["contract"][key] for key in ("strike", "barrier", "rate", "volatility")}
    ref, monitors = p["reference"], p["contract"]["positive_monitoring"]
    if ref["order"] != 128 or ref["check_order"] != 256 or ref["tail_sigma"] != 12:
        raise ValueError("fixed GL128/256 and tail12 reference required")

    def evaluate(inputs):
        x = np.asarray(inputs, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError("physical [spot,maturity] rows required")
        prediction = np.full((len(x), 2), np.nan)
        valid = np.isfinite(x).all(axis=1) & np.all(x > 0, axis=1)
        if not np.any(valid):
            return prediction
        result = teacher.markov_batch(
            x[valid], monitoring=monitors, order=128, check_order=256, tail_sigma=12, **contract
        )
        value = np.column_stack((result["price"].ravel(), result["delta"].ravel()))
        refinement = result["refinement"]
        error = np.column_stack((refinement["price"].ravel(), refinement["delta"].ravel()))
        error += np.maximum(result["tail_bounds"][:, 1:], refinement["tail_bounds"][:, 1:])
        good = (
            np.isfinite(value).all(axis=1)
            & (error[:, 0] <= ref["quadrature_price_tolerance"])
            & (error[:, 1] <= ref["quadrature_delta_tolerance"])
        )
        prediction[valid] = np.where(good[:, None], value, np.nan)
        knock = valid & (x[:, 0] >= contract["barrier"])
        prediction[knock] = 0
        prediction[knock & (x[:, 0] == contract["barrier"]), 1] = np.nan
        return prediction

    return evaluate


def _callbacks(record, arrays):
    runner, replay = _runner(), _module("replay")
    # Preparation is deliberately outside the measured inference callback.
    oracle = checked_oracle(record["protocol"], runner._teacher())
    functions = {}
    for model_id in arrays["model_ids"].tolist():
        exported = runner._export(arrays, model_id)
        functions[model_id] = lambda x, model=exported: replay.predict_nn(model, x)
    functions["hermite"], functions["oracle"] = runner._surface(arrays), oracle
    return functions, oracle


def _callback_metadata(record):
    return {
        "operation": "price+ordinary spot Delta",
        "reference": "same fixed protocol snapshot and checked markov_batch callback for every raw/safe method",
        "order": record["protocol"]["reference"]["order"],
        "check_order": record["protocol"]["reference"]["check_order"],
        "tail_sigma": record["protocol"]["reference"]["tail_sigma"],
        "setup": "protocol/source/teacher import prepared before timer",
        "within_call_sharing": "only exactly equal maturity transition/continuation",
        "input_result_memoization": False,
        "safe_price_bound": "experimental gate; does not certify Greek accuracy",
    }


def loading_summary(samples, provenance):
    """Recompute warm whole-archive decode median/p95 from all 100 samples."""
    samples = np.asarray(samples, dtype=float)
    if samples.shape != (100,) or not np.isfinite(samples).all() or np.any(samples < 0):
        raise ValueError("100 finite nonnegative warm loading samples required")
    if (
        not isinstance(provenance.get("bytes"), int)
        or provenance["bytes"] <= 0
        or len(provenance.get("sha256", "")) != 64
    ):
        raise ValueError("loading measurement source artifact size/digest required")
    return {
        "status": "measured",
        "median_s": float(np.median(samples)),
        "p95_s": float(np.quantile(samples, 0.95)),
        "mean_s": float(samples.mean()),
        "minimum_s": float(samples.min()),
        "maximum_s": float(samples.max()),
        "sample_std_s": float(samples.std(ddof=1)),
        "warmups": 3,
        "repeats": 100,
        "raw_key": "loading.samples_s",
        "unit": "seconds_per_full_archive_decode",
        "scope": "full_compressed_research_bundle_warm_cache_decode",
        "excludes": [
            "cold_filesystem_io",
            "process_start",
            "module_import",
            "minimal_standalone_packaging",
            "artifact_integrity_hashing",
        ],
        "source_artifact": copy.deepcopy(provenance),
        "source_note": "measurement input archive before finalization; its hash/size need not match the final archive",
        "assumption": "each standalone NN/Hermite comparison owes one warm decode of the main-fit bundle before measurement arrays were added; not the final benchmark archive; minimal packaging is unmeasured",
    }


def _decode(path):
    with np.load(path, allow_pickle=False) as data:
        # Materialize all arrays, not only the NPZ directory or one NN export.
        return [data[key] for key in data.files]


def measure_loading(path):
    path = Path(path)
    provenance = {
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "role": "measurement input, before finalization",
    }
    for _ in range(3):
        _decode(path)
    samples = []
    for _ in range(100):
        start = perf_counter()
        decoded = _decode(path)
        samples.append(perf_counter() - start)
        del decoded
    samples = np.asarray(samples)
    return loading_summary(samples, provenance), samples


def _offline(record):
    return {
        "hermite": {"grid_setup_s": record["interpolation"]["gridsetup_s"]},
        "unmeasured": list(_UNMEASURED),
    }


def _compare(actual, expected, name):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(name + ": keys differ")
        for key in expected:
            _compare(actual[key], expected[key], name + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(name + ": length differs")
        for i, value in enumerate(expected):
            _compare(actual[i], value, f"{name}[{i}]")
    elif isinstance(expected, float):
        if not np.isclose(actual, expected, rtol=1e-9, atol=1e-12, equal_nan=True):
            raise ValueError(name + ": number differs from recomputation")
    elif actual != expected:
        raise ValueError(name + ": metadata differs")


def refresh_result(output=HERE):
    """Measure once from saved exports; never import or fit the NN learner."""
    output, runner, benchmarks = Path(output), _runner(), _benchmarks()
    record, arrays = runner.load_result(output)
    runner.check_record(record, arrays)
    functions, oracle = _callbacks(record, arrays)
    benchmark, raw = benchmarks.measure(
        functions, arrays["test.inputs"], oracle, record["protocol"]
    )
    benchmark["common_initialization_s"] = record["common_initialization_s"]
    benchmark["callback_preparation"] = _callback_metadata(record)
    verification = benchmarks.check_measurements(
        benchmark, raw, replay_callbacks=functions, oracle=oracle
    )
    if not verification["passed"] or verification.get("numeric_replay") != "verified":
        raise ValueError(
            "measured outputs failed independent saved-weight replay: " + str(verification)
        )
    loading, samples = measure_loading(output / "reference.npz")
    record["benchmark"], record["loading"] = benchmark, loading
    arrays.update(raw)
    arrays["loading.samples_s"] = samples
    record["costs"] = benchmarks.cost_summary(
        benchmark, record["models"], _offline(record), loading
    )
    record["cost_scope"] = {
        "unmeasured": {name: "unmeasured; not charged as zero" for name in _UNMEASURED},
        "common_initialization": "already measured in each standalone NN offline cost; excluded from fit elapsed cap",
    }
    record["adoption"] = runner._adoption(record)
    runner.save_result(output, record, arrays)
    return record


def check_result(output=HERE):
    """No learning/timing; fresh callback prices/Greeks verify saved outputs."""
    runner, benchmarks = _runner(), _benchmarks()
    record, arrays = runner.load_result(output)
    runner.check_record(record, arrays)
    functions, oracle = _callbacks(record, arrays)
    benchmark = record.get("benchmark")
    if not isinstance(benchmark, dict):
        raise ValueError("saved benchmark required")
    _compare(benchmark["protocol"], record["protocol"], "benchmark protocol")
    _compare(
        benchmark["common_initialization_s"],
        record["common_initialization_s"],
        "common initialization",
    )
    _compare(benchmark["callback_preparation"], _callback_metadata(record), "callback contract")
    verification = benchmarks.check_measurements(
        benchmark, arrays, replay_callbacks=functions, oracle=oracle
    )
    if not verification["passed"] or verification.get("numeric_replay") != "verified":
        raise ValueError("benchmark evidence failed: " + str(verification))
    loading = loading_summary(arrays["loading.samples_s"], record["loading"]["source_artifact"])
    _compare(record["loading"], loading, "warm whole-bundle loading")
    costs = benchmarks.cost_summary(benchmark, record["models"], _offline(record), loading)
    _compare(record["costs"], costs, "full cost accounts")
    _compare(
        record["cost_scope"],
        {
            "unmeasured": {name: "unmeasured; not charged as zero" for name in _UNMEASURED},
            "common_initialization": "already measured in each standalone NN offline cost; excluded from fit elapsed cap",
        },
        "unmeasured cost boundary",
    )
    return {
        "passed": True,
        "measurements": verification["checked_measurements"],
        "replayed_measurements": verification["replayed_measurements"],
        "warm_load_samples": len(arrays["loading.samples_s"]),
        "cost_comparisons": len(costs["comparisons"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args(argv)
    if not args.refresh and not args.check:
        parser.error("choose --refresh or --check")
    if args.refresh:
        refresh_result(args.output)
    if args.check:
        print(json.dumps(check_result(args.output)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
