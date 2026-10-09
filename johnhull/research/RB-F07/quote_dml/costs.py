"""Cost accounts from saved observations, without pricing or fitting a model.

Online observations are seconds per measured batch, so the primary cost is
``C(N_calls) = offline + N_calls * seconds_per_batch``. Query counts require
ceil-rounded full (possibly padded) calls; timings are never divided into
fractional calls. Median and p95 scenarios remain separate observations.
"""

from __future__ import annotations

from math import ceil, isclose, isfinite

import numpy as np

COUNTS = (1, 10, 100, 1000, 10000)
STATISTICS = ("median", "p95")


def _seconds(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite nonnegative seconds") from error
    if not isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite nonnegative seconds")
    return result


def _equal(actual, expected, name):
    if not isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-9):
        raise ValueError(f"{name} disagrees with its recorded components")


def _generation(arrays, split):
    values = np.asarray(arrays[f"{split}_market_generation_s"], dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("market generation observations must be finite nonnegative vectors")
    return values


def _roster(record, arrays):
    training = record["protocol"]["training"]
    modes, sizes, seeds = training["modes"], training["sizes"], training["seeds"]
    expected = {
        f"{mode}_n{size}_s{seed}": ("nn", size)
        for size in sizes
        for mode in modes
        for seed in seeds
    }
    expected.update(
        {
            f"ridge_{method}_n{size}": ("ridge", size)
            for size in sizes
            for method in ("price", "dml")
        }
    )
    identifiers = list(map(str, np.asarray(arrays["model_ids"]).tolist()))
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(expected):
        raise ValueError("saved model roster does not match protocol")
    return expected, identifiers


def _fits(record, arrays, expected):
    if record.get("complete_fits") is not True:
        raise ValueError("incomplete or failed fits cannot support a cost account")
    generation = _generation(arrays, "train")
    contracts = int(record["protocol"]["sampling"]["contracts_per_market"])
    if contracts <= 0:
        raise ValueError("contracts_per_market must be positive")
    fits = {}
    for item in record["fits"]:
        identifier = item["id"]
        if identifier not in expected or identifier in fits:
            raise ValueError("missing, duplicate or unexpected fit identifier")
        kind, size = expected[identifier]
        if item["kind"] != kind or item.get("budget_failure") is not False:
            raise ValueError("fit family mismatch or budget failure")
        if size % contracts or size // contracts > len(generation):
            raise ValueError("fit size does not match stored market generation prefix")
        teacher = _seconds(item["train_teacher_s"], "train_teacher_s")
        _equal(teacher, float(generation[: size // contracts].sum()), "train_teacher_s")
        elapsed = _seconds(item["elapsed_s"], "elapsed_s")
        offline = _seconds(item["offline_s"], "offline_s")
        fit = {
            "kind": kind,
            "size": size,
            "train_teacher_s": teacher,
            "elapsed_s": elapsed,
            "offline_s": offline,
        }
        if kind == "nn":
            requested = item["requested_updates"]
            updates = record["protocol"]["training"].get("updates", 512)
            if item["updates"] != requested or (
                record.get("experiment", "main") == "main" and requested != updates
            ):
                raise ValueError("fit did not complete the declared updates")
            setup = _seconds(item["setup_s"], "setup_s")
            training = _seconds(item["training_s"], "training_s")
            export = _seconds(item["export_s"], "export_s")
            overhead = elapsed - setup - training
            if overhead < -1e-9:
                raise ValueError("fit setup/training exceeds recorded elapsed_s")
            fit.update(
                setup_s=setup,
                training_s=training,
                export_s=export,
                fit_overhead_s=max(0.0, overhead),
                fit_component_status="separate_setup_training_export",
            )
            _equal(offline, teacher + elapsed + export, "offline_s")
        else:
            # fit_ridge returns the exported dictionary: the saved elapsed
            # measurement covers setup, fitting and export together.
            fit.update(
                setup_s=None,
                training_s=None,
                export_s=None,
                fit_overhead_s=None,
                fit_component_status="combined_setup_training_export",
            )
            _equal(offline, teacher + elapsed, "offline_s")
        fits[identifier] = fit
    if set(fits) != set(expected):
        raise ValueError("declared fit roster is incomplete")
    total_fit = _seconds(record["total_fit_s"], "total_fit_s")
    _equal(total_fit, sum(item["elapsed_s"] for item in fits.values()), "total_fit_s")
    teacher = _seconds(record["teacher_s"], "teacher_s")
    generation_total = sum(
        float(_generation(arrays, split).sum()) for split in ("train", "validation", "test")
    )
    if teacher + 1e-9 < generation_total:
        raise ValueError("experiment teacher_s is smaller than generation observations")
    exports = sum(item["export_s"] or 0.0 for item in fits.values())
    experiment = {
        "teacher_s": teacher,
        "teacher_generation_s": generation_total,
        "teacher_overhead_s": max(0.0, teacher - generation_total),
        "total_fit_s": total_fit,
        "known_export_s": exports,
        "measured_subtotal_s": teacher + total_fit + exports,
        "status": "measured_subtotal",
        "unmeasured": [
            "independent_oracle_checks",
            "benchmark_execution",
            "artifact_serialization",
            "report_generation",
        ],
        "teacher_accounting": "Shared train/validation/test generation once; not the sum of each model's train teacher cost.",
        "ridge_export_accounting": "Included in elapsed_s; separate setup/training/export observations unavailable.",
    }
    return fits, experiment


def _loading(record, identifiers):
    source = record.get("loading") or {}

    def observation(item):
        if item is None:
            return {"status": "missing", "median_s": None, "p95_s": None}
        result = {"status": "measured"}
        for statistic in STATISTICS:
            key = f"{statistic}_s"
            result[key] = _seconds(item[key], key)
        if result["p95_s"] < result["median_s"]:
            raise ValueError("loading p95 cannot be smaller than median")
        return result

    return {
        "full_npz": observation(source.get("full_npz")),
        "model_decode": {
            identifier: observation(source.get("model_decode", {}).get(identifier))
            for identifier in identifiers
        },
        "scope": source.get("scope", "whole_compressed_research_bundle_warm_cache"),
        "excludes": source.get(
            "excludes",
            ["cold_filesystem_io", "minimal_model_packaging", "json_parse", "module_import"],
        ),
        "assumption": "Deployment includes loading the entire research bundle once plus decoding one model; this is not minimal standalone packaging.",
    }


def _measurements(record, identifiers):
    benchmark = record["benchmark"]
    if benchmark["settings"]["unit"] != "seconds_per_batch":
        raise ValueError("online cost requires measured seconds_per_batch")
    batches = benchmark["settings"]["batches"]
    if (
        not batches
        or len(set(batches)) != len(batches)
        or any(int(batch) != batch or batch <= 0 for batch in batches)
    ):
        raise ValueError("positive unique integer batch sizes required")
    if "model_ids" in benchmark and set(benchmark["model_ids"]) != set(identifiers):
        raise ValueError("benchmark model roster mismatch")
    largest = max(record["protocol"]["training"]["sizes"])
    representatives = [f"{mode}_n{largest}_s11" for mode in record["protocol"]["training"]["modes"]]
    representatives += [f"ridge_{method}_n{largest}" for method in ("price", "dml")]
    if set(benchmark["representative_ids"]) != set(representatives):
        raise ValueError("benchmark representative roster mismatch")
    expected = set()
    for batch in batches:
        for operation in ("price", "price_risk"):
            expected.add(("exact_cached", None, operation, "prepared", batch))
            expected.update(("raw", model, operation, "prepared", batch) for model in identifiers)
        for cache in ("market", "row"):
            expected.add(("e2e", "exact", "price_risk", cache, batch))
            expected.update(
                (source, model, "price_risk", cache, batch)
                for source in ("e2e", "safe")
                for model in representatives
            )
    observations, ids = {}, set()
    for item in benchmark["measurements"]:
        if item["id"] in ids:
            raise ValueError("duplicate benchmark measurement identifier")
        ids.add(item["id"])
        if item["source"] not in ("exact_cached", "raw", "e2e", "safe"):
            continue
        key = tuple(
            item[name] for name in ("source", "model_id", "operation", "cache", "batch_size")
        )
        if key not in expected or key in observations:
            raise ValueError("duplicate or unexpected benchmark measurement")
        observations[key] = item
        for statistic in STATISTICS:
            _seconds(item[f"{statistic}_s"], statistic)
        if item["p95_s"] < item["median_s"]:
            raise ValueError("benchmark p95 cannot be smaller than median")
    if set(observations) != expected:
        raise ValueError("missing declared model measurement or matched exact comparator")
    return observations


def _break_even(offline, reference, online, batch):
    difference, saving = offline, reference - online
    common = {
        "offline_difference_s": difference,
        "online_saving_s_per_batch": saving,
        "initial_advantage": difference <= 0,
    }
    if saving <= 0:
        return {
            "status": "no_online_advantage",
            "continuous_calls": None,
            "first_integer_call": None,
            "rows_at_first_integer_call": None,
            **common,
        }
    calls = max(0.0, difference / saving)
    integer = ceil(calls)
    return {
        "status": "advantage_from_start" if difference <= 0 else "break_even",
        "continuous_calls": calls,
        "first_integer_call": integer,
        "rows_at_first_integer_call": integer * batch,
        **common,
    }


def _scenario(offline, reference, online, batch):
    def total(calls, requested=None):
        return {
            "measured_calls": calls,
            "processed_rows": calls * batch,
            "requested_queries": requested,
            "surrogate_s": offline + calls * online,
            "reference_s": calls * reference,
        }

    return {
        "offline_s": offline,
        "batch_counts": {str(count): total(count) for count in COUNTS},
        "query_counts": {str(count): total(ceil(count / batch), count) for count in COUNTS},
        "break_even": _break_even(offline, reference, online, batch),
    }


def cost_summary(record, arrays):
    """Return JSON-ready, measured-call cost comparisons for the declared roster.

    The saved benchmark checker must have verified its raw sample summaries.
    This account verifies coverage, unit consistency and offline decomposition;
    it does not rerun measurements. An unknown deployment cost stays null.
    """
    expected, identifiers = _roster(record, arrays)
    fits, experiment = _fits(record, arrays, expected)
    loading = _loading(record, identifiers)
    observations = _measurements(record, identifiers)
    comparisons = []
    for key, item in observations.items():
        source, identifier, operation, cache, batch = key
        if source == "exact_cached" or identifier == "exact":
            continue
        comparator = observations[
            ("exact_cached", None, operation, cache, batch)
            if source == "raw"
            else ("e2e", "exact", operation, cache, batch)
        ]
        statistics = {}
        for statistic in STATISTICS:
            online = float(item[f"{statistic}_s"])
            reference = float(comparator[f"{statistic}_s"])
            offline = fits[identifier]["offline_s"]
            deployed = None
            bundle, decode = loading["full_npz"], loading["model_decode"][identifier]
            if bundle["status"] == decode["status"] == "measured":
                deployed = _scenario(
                    offline + bundle[f"{statistic}_s"] + decode[f"{statistic}_s"],
                    reference,
                    online,
                    batch,
                )
            statistics[statistic] = {
                "surrogate_online_s_per_batch": online,
                "reference_online_s_per_batch": reference,
                "training_only": _scenario(offline, reference, online, batch),
                "deployment": deployed,
            }
        comparisons.append(
            {
                "model_id": identifier,
                "source": source,
                "operation": operation,
                "cache": cache,
                "batch_size": batch,
                "measurement_id": item["id"],
                "reference_id": comparator["id"],
                "statistics": statistics,
            }
        )
    return {
        "schema_version": 1,
        "unit": "seconds_per_measured_batch_call",
        "formula": "C(N_calls)=offline_s+N_calls*online_s_per_batch",
        "query_policy": "ceil(N_queries/batch_size) full/padded measured calls",
        "offline_reference_s": 0.0,
        "reference_policy": "Exact baseline needs no additional fit; shared curve preparation/cache is compared in matched online operations.",
        "p95_policy": "Sum of observed p95 operation costs is a separate cost scenario, not a measured p95 total or confidence interval.",
        "fits": fits,
        "experiment": experiment,
        "loading": loading,
        "comparisons": comparisons,
    }
