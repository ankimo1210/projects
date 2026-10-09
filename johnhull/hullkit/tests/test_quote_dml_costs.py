"""Measured-call cost accounts: fit decomposition, padding and honest missingness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"


def costs():
    path = HERE / "costs.py"
    assert path.exists(), "quote-DML cost account has not been implemented"
    spec = importlib.util.spec_from_file_location("quote_dml_cost_account", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture():
    """Saved cost record and raw observations only, without financial imports."""
    modes = ["q_price", "theta_price", "theta_dml", "theta_quote_metric", "q_dml"]
    sizes, seeds, batches = [512, 2048], [11, 29, 47], [1, 32, 1024]
    arrays = {
        "train_market_generation_s": np.full(256, 0.1),
        "validation_market_generation_s": np.full(64, 0.1),
        "test_market_generation_s": np.full(128, 0.1),
    }
    fits, identifiers = [], []
    for size in sizes:
        teacher = size / 8 * 0.1
        for mode in modes:
            for seed in seeds:
                identifier = f"{mode}_n{size}_s{seed}"
                identifiers.append(identifier)
                fits.append(
                    {
                        "id": identifier,
                        "kind": "nn",
                        "train_teacher_s": teacher,
                        "setup_s": 0.1,
                        "training_s": 1.0,
                        "elapsed_s": 1.2,
                        "export_s": 0.01,
                        "offline_s": teacher + 1.21,
                        "updates": 512,
                        "requested_updates": 512,
                        "budget_failure": False,
                    }
                )
        for method in ["price", "dml"]:
            identifier = f"ridge_{method}_n{size}"
            identifiers.append(identifier)
            fits.append(
                {
                    "id": identifier,
                    "kind": "ridge",
                    "train_teacher_s": teacher,
                    "elapsed_s": 0.02,
                    "offline_s": teacher + 0.02,
                    "budget_failure": False,
                }
            )
    representatives = [f"{mode}_n2048_s11" for mode in modes]
    representatives += ["ridge_price_n2048", "ridge_dml_n2048"]
    measurements = []

    def measurement(source, model, operation, cache, batch, median, p95):
        identifier = f"{source}_{model}_{operation}_{cache}_{batch}"
        arrays["timing__" + identifier] = np.array([median, median, p95])
        # This fixture intentionally uses summary statistics directly: timings
        # have already passed the benchmark sample checker before this account.
        measurements.append(
            {
                "id": identifier,
                "source": source,
                "model_id": model,
                "operation": operation,
                "cache": cache,
                "batch_size": batch,
                "median_s": median,
                "p95_s": p95,
            }
        )

    for batch in batches:
        for operation in ["price", "price_risk"]:
            measurement(
                "exact_cached", None, operation, "prepared", batch, batch * 0.002, batch * 0.004
            )
            for identifier in identifiers:
                measurement(
                    "raw", identifier, operation, "prepared", batch, batch * 0.001, batch * 0.003
                )
        for cache in ["market", "row"]:
            measurement("e2e", "exact", "price_risk", cache, batch, batch * 0.004, batch * 0.008)
            for identifier in representatives:
                measurement(
                    "e2e", identifier, "price_risk", cache, batch, batch * 0.005, batch * 0.009
                )
                measurement(
                    "safe", identifier, "price_risk", cache, batch, batch * 0.006, batch * 0.012
                )
    arrays["model_ids"] = np.array(identifiers)
    record = {
        "complete_fits": True,
        "fits": fits,
        "teacher_s": 45.0,
        "total_fit_s": sum(item["elapsed_s"] for item in fits),
        "protocol": {
            "sampling": {"contracts_per_market": 8},
            "training": {"modes": modes, "sizes": sizes, "seeds": seeds},
        },
        "benchmark": {
            "settings": {"batches": batches, "unit": "seconds_per_batch"},
            "model_ids": identifiers,
            "representative_ids": representatives,
            "measurements": measurements,
        },
    }
    return record, arrays


def comparison(summary, identifier, source, *, batch=32, cache="prepared", operation="price_risk"):
    return next(
        item
        for item in summary["comparisons"]
        if item["model_id"] == identifier
        and item["source"] == source
        and item["batch_size"] == batch
        and item["cache"] == cache
        and item["operation"] == operation
    )


def test_offline_decomposition_keeps_shared_teacher_and_all_experiment_cost_separate():
    record, arrays = fixture()
    result = costs().cost_summary(record, arrays)
    single = result["fits"]["q_dml_n512_s11"]
    assert single["train_teacher_s"] == pytest.approx(6.4)
    assert single["setup_s"] == 0.1 and single["training_s"] == 1.0
    assert single["fit_overhead_s"] == pytest.approx(0.1)
    assert single["export_s"] == 0.01
    assert single["offline_s"] == pytest.approx(7.61)
    assert result["experiment"]["teacher_s"] == 45.0
    assert result["experiment"]["total_fit_s"] == pytest.approx(record["total_fit_s"])
    assert result["experiment"]["known_export_s"] == pytest.approx(0.3)
    assert result["experiment"]["measured_subtotal_s"] == pytest.approx(
        45.0 + record["total_fit_s"] + 0.3
    )
    ridge = result["fits"]["ridge_dml_n512"]
    assert ridge["setup_s"] is None and ridge["training_s"] is None and ridge["export_s"] is None
    assert ridge["fit_component_status"] == "combined_setup_training_export"
    assert result["offline_reference_s"] == 0.0


def test_full_batch_calls_and_padded_query_counts_preserve_timing_units():
    record, arrays = fixture()
    result = costs().cost_summary(record, arrays)
    item = comparison(result, "q_dml_n512_s11", "raw")
    median = item["statistics"]["median"]
    assert median["surrogate_online_s_per_batch"] == pytest.approx(0.032)
    assert median["reference_online_s_per_batch"] == pytest.approx(0.064)
    assert median["training_only"]["batch_counts"]["10"]["surrogate_s"] == pytest.approx(
        7.61 + 0.32
    )
    padded = median["training_only"]["query_counts"]["1"]
    assert padded["measured_calls"] == 1 and padded["processed_rows"] == 32
    assert padded["surrogate_s"] == pytest.approx(7.61 + 0.032)
    assert padded["reference_s"] == pytest.approx(0.064)
    # The p95 record is its own cost scenario, not a CI or median speedup.
    p95 = item["statistics"]["p95"]
    assert p95["surrogate_online_s_per_batch"] == pytest.approx(0.096)
    assert p95["reference_online_s_per_batch"] == pytest.approx(0.128)


def test_break_even_is_calls_then_full_batch_rows_and_uses_only_positive_savings():
    record, arrays = fixture()
    result = costs().cost_summary(record, arrays)
    raw = comparison(result, "q_dml_n512_s11", "raw")["statistics"]["median"]["training_only"][
        "break_even"
    ]
    assert raw["status"] == "break_even"
    assert raw["continuous_calls"] == pytest.approx(7.61 / 0.032)
    assert raw["first_integer_call"] == 238
    assert raw["rows_at_first_integer_call"] == 7616
    safe = comparison(result, "q_dml_n2048_s11", "safe", cache="market")
    assert safe["reference_id"].startswith("e2e_exact_")
    assert (
        safe["statistics"]["median"]["training_only"]["break_even"]["status"]
        == "no_online_advantage"
    )


def test_missing_loader_is_null_and_measured_bundle_and_model_decode_are_added():
    record, arrays = fixture()
    result = costs().cost_summary(record, arrays)
    item = comparison(result, "q_dml_n512_s11", "raw")
    assert result["loading"]["full_npz"]["status"] == "missing"
    assert result["loading"]["model_decode"]["q_dml_n512_s11"]["status"] == "missing"
    assert item["statistics"]["median"]["deployment"] is None
    record["loading"] = {
        "full_npz": {"median_s": 0.2, "p95_s": 0.3},
        "model_decode": {"q_dml_n512_s11": {"median_s": 0.01, "p95_s": 0.02}},
    }
    loaded = comparison(costs().cost_summary(record, arrays), "q_dml_n512_s11", "raw")
    assert loaded["statistics"]["median"]["deployment"]["offline_s"] == pytest.approx(7.82)
    assert loaded["statistics"]["p95"]["deployment"]["offline_s"] == pytest.approx(7.93)


def test_zero_offline_reports_initial_advantage_and_equal_online_has_no_recovery():
    record, arrays = fixture()
    arrays["train_market_generation_s"][:] = 0.0
    for fit in record["fits"]:
        fit["train_teacher_s"] = 0.0
        fit["offline_s"] = fit["elapsed_s"] + fit.get("export_s", 0.0)
    fit = record["fits"][0]
    fit.update(setup_s=0.0, training_s=0.0, elapsed_s=0.0, export_s=0.0, offline_s=0.0)
    record["total_fit_s"] = sum(item["elapsed_s"] for item in record["fits"])
    identifier = fit["id"]
    result = costs().cost_summary(record, arrays)
    first = comparison(result, identifier, "raw")["statistics"]["median"]["training_only"][
        "break_even"
    ]
    assert first["status"] == "advantage_from_start" and first["first_integer_call"] == 0
    for item in record["benchmark"]["measurements"]:
        if item["source"] == "raw" and item["model_id"] == identifier:
            item["median_s"] *= 2.0
    result = costs().cost_summary(record, arrays)
    flat = comparison(result, identifier, "raw")["statistics"]["median"]["training_only"][
        "break_even"
    ]
    assert flat["status"] == "no_online_advantage" and flat["continuous_calls"] is None


@pytest.mark.parametrize(
    "change", ["offline", "teacher", "setup", "total_fit", "failed", "updates"]
)
def test_inconsistent_or_failed_fit_is_rejected(change):
    record, arrays = fixture()
    if change == "offline":
        record["fits"][0]["offline_s"] += 0.5
    elif change == "teacher":
        record["fits"][0]["train_teacher_s"] += 0.5
        record["fits"][0]["offline_s"] += 0.5
    elif change == "setup":
        record["fits"][0]["setup_s"] += 2.0
    elif change == "total_fit":
        record["total_fit_s"] += 2.0
    elif change == "failed":
        record["fits"][0]["budget_failure"] = True
    else:
        record["fits"][0]["updates"] -= 1
    with pytest.raises(ValueError):
        costs().cost_summary(record, arrays)


@pytest.mark.parametrize("target", ["exact", "raw", "safe"])
def test_missing_comparator_or_declared_roster_measurement_is_rejected(target):
    record, arrays = fixture()
    source = "exact_cached" if target == "exact" else target
    index = next(
        i for i, item in enumerate(record["benchmark"]["measurements"]) if item["source"] == source
    )
    del record["benchmark"]["measurements"][index]
    with pytest.raises(ValueError):
        costs().cost_summary(record, arrays)


def test_cost_account_does_not_import_a_pricer_learner_or_benchmark():
    path = HERE / "costs.py"
    assert path.exists(), "quote-DML cost account has not been implemented"
    source = path.read_text()
    for forbidden in ("import torch", "from hullkit", "import benchmark", "from deep_hedge_price"):
        assert forbidden not in source
