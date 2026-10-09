"""Whole-batch timing evidence, routing coverage and component cost accounts."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete"
IDS = [f"{mode}_s{seed}" for mode in ("price", "dml") for seed in (11, 29, 47)]
IDS += ["hermite", "oracle"]


def benchmark():
    path = HERE / "benchmarks.py"
    assert path.exists(), "discrete-barrier benchmark account is not implemented"
    spec = importlib.util.spec_from_file_location("discrete_barrier_benchmarks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture():
    protocol = json.loads((HERE / "protocol.json").read_text())
    inputs = np.array([[90.0, 0.5], [100.0, 1.0], [118.0, 2.0]])

    def oracle(x):
        x = np.asarray(x)
        return np.column_stack(
            [2.0 + 0.01 * (x[:, 0] - 100) + 0.1 * x[:, 1], np.full(len(x), 0.01)]
        )

    def bounded_approximation(x):
        return oracle(x) + np.array([0.01, 0.001])

    functions = {identifier: bounded_approximation for identifier in IDS}
    functions["oracle"] = oracle
    return functions, inputs, oracle, protocol


def measured():
    functions, inputs, oracle, protocol = fixture()
    record, arrays = benchmark().measure(functions, inputs, oracle, protocol)
    return record, arrays


def metadata():
    models = {
        identifier: {
            "train_teacher_s": 2.0,
            "setup_s": 0.1,
            "training_s": 0.8,
            "elapsed_s": 1.0,
            "export_s": 0.01,
            "offline_s": 3.01,
            "budget_failure": False,
            "updates": 512,
            "requested_updates": 512,
        }
        for identifier in IDS[:-2]
    }
    offline = {
        "hermite": {"grid_setup_s": 0.5},
        "unmeasured": ["cold_filesystem_io", "process_start", "module_import"],
    }
    return models, offline


def find(rows, method="dml_s11", phase="raw", batch=32):
    return next(
        item
        for item in rows
        if item["method_id"] == method and item["phase"] == phase and item["batch_size"] == batch
    )


def test_measure_retains_raw_samples_inputs_and_all_methods_for_both_serving_phases():
    record, arrays = measured()
    assert len(record["measurements"]) == 32
    check = benchmark().check_measurements(record, arrays)
    assert check["passed"], check["failures"]
    for row in record["measurements"]:
        samples = arrays[row["raw_key"]]
        assert samples.shape == (20,)
        assert row["median_s"] == pytest.approx(np.median(samples))
        assert row["p95_s"] == pytest.approx(np.quantile(samples, 0.95))
        assert arrays[row["routing_key"]].shape == (20, row["batch_size"])
        assert arrays[row["input_key"]].shape == (row["batch_size"], 2)
    assert record["source_digest"]["benchmarks.py"]
    assert record["source_digest"]["replay.py"]


def test_saved_outputs_replay_independently_and_keep_contract_boundary_values():
    functions, inputs, oracle, protocol = fixture()
    record, arrays = benchmark().measure(functions, inputs, oracle, protocol)
    checked = benchmark().check_measurements(
        record, arrays, replay_callbacks=functions, oracle=oracle
    )
    assert checked["passed"], checked["failures"]
    assert checked["replayed_measurements"] == 32
    for row in record["measurements"]:
        assert arrays[row["output_key"]].shape == (20, row["batch_size"], 2)
        if row["phase"] == "safe" and row["batch_size"] == 32:
            output = arrays[row["output_key"]]
            np.testing.assert_allclose(output[:, -2, 0], 0.0)
            assert np.isnan(output[:, -2, 1]).all()
            np.testing.assert_allclose(output[:, -1], 0.0)
            assert row["comparison_status"] == "unsupported"
            assert row["unsupported_reasons"] == ["delta_undefined"]
        else:
            assert row["comparison_status"] == "supported"


@pytest.mark.parametrize("coordinate", [0, 1], ids=["price", "delta"])
def test_saved_price_or_delta_tampering_fails_independent_replay(coordinate):
    functions, inputs, oracle, protocol = fixture()
    module = benchmark()
    record, arrays = module.measure(functions, inputs, oracle, protocol)
    row = find(record["measurements"], "dml_s11", "raw", 32)
    arrays[row["output_key"]][:, 0, coordinate] += 0.05
    # An attacker changing the summary as well still cannot defeat the replay.
    row["output_summary"] = module._output_summary(arrays[row["output_key"]])
    checked = module.check_measurements(record, arrays, replay_callbacks=functions, oracle=oracle)
    assert not checked["passed"] and checked["failures"]


def test_oracle_failure_is_retained_and_cannot_support_cost_recovery_or_be_hidden():
    functions, inputs, original_oracle, protocol = fixture()

    def failing_oracle(x):
        result = original_oracle(x)
        result[(x[:, 0] == 70) | (x[:, 1] == 3), 0] = -1.0
        return result

    functions["oracle"] = failing_oracle
    module = benchmark()
    record, arrays = module.measure(functions, inputs, failing_oracle, protocol)
    checked = module.check_measurements(
        record, arrays, replay_callbacks=functions, oracle=failing_oracle
    )
    assert checked["passed"], checked["failures"]
    row = find(record["measurements"], "dml_s11", "safe", 32)
    assert np.isnan(arrays[row["output_key"]][:, -4:-2]).all()
    assert "oracle_failure" in row["unsupported_reasons"]
    result = module.cost_summary(record, *metadata(), 0.2)
    cost = find(result["comparisons"], "dml_s11", "safe", 32)
    assert cost["comparison_status"] == "unsupported"
    assert any("oracle_failure" in reason for reason in cost["unsupported_reasons"])
    assert cost["statistics"]["median"]["deployment"] is None
    assert cost["statistics"]["median"]["training_only"] is None
    # Route relabeling plus recomputed counts must not turn NaNs into success.
    arrays[row["routing_key"]][:, -4:-2] = "fallback"
    row.update(module._summary(arrays[row["raw_key"]], arrays[row["routing_key"]]))
    row["comparison_status"], row["unsupported_reasons"] = "unsupported", ["delta_undefined"]
    assert not module.check_measurements(record, arrays)["passed"]


@pytest.mark.parametrize("boundary", ["contact_price", "contact_delta", "ko_price", "ko_delta"])
def test_safe_boundary_output_tampering_is_not_allowed_without_replay(boundary):
    record, arrays = measured()
    module = benchmark()
    row = find(record["measurements"], "dml_s11", "safe", 32)
    coordinate = 0 if boundary.endswith("price") else 1
    index = -2 if boundary.startswith("contact") else -1
    arrays[row["output_key"]][0, index, coordinate] = 0.1
    row["output_summary"] = module._output_summary(arrays[row["output_key"]])
    assert not module.check_measurements(record, arrays)["passed"]


def test_undefined_delta_retains_latency_but_excludes_whole_batch_cost_claim():
    record, models, offline = cost_fixture()
    result = benchmark().cost_summary(record, models, offline, 0.2)
    safe = find(result["comparisons"], "dml_s11", "safe", 32)
    assert safe["comparison_status"] == "unsupported"
    assert any("delta_undefined" in reason for reason in safe["unsupported_reasons"])
    for scenario in safe["statistics"].values():
        assert scenario["surrogate_online_s_per_batch"] > 0
        assert scenario["reference_online_s_per_batch"] > 0
        assert scenario["training_only"] is None and scenario["deployment"] is None
    assert find(result["comparisons"], "dml_s11", "safe", 1)["comparison_status"] == "supported"


def test_safe_batch_exercises_ood_contact_and_knockout_for_oracle_and_approximations():
    record, arrays = measured()
    for method in IDS:
        row = find(record["measurements"], method, "safe", 32)
        inputs = arrays[row["input_key"]]
        np.testing.assert_allclose(
            inputs[-4:], [[70.0, 0.1], [100.0, 3.0], [120.0, 1.0], [121.0, 1.0]]
        )
        routing = arrays[row["routing_key"]]
        assert np.all(routing[:, -4:-2] == "fallback")
        assert np.all(routing[:, -2] == "delta_undefined")
        assert np.all(routing[:, -1] == "knocked_out")
        assert row["routing_counts"]["fallback"] == 40
        assert row["routing_counts"]["delta_undefined"] == 20
        one = find(record["measurements"], method, "safe", 1)
        np.testing.assert_allclose(arrays[one["input_key"]], [[100.0, 1.0]])


def test_safe_bounds_failure_routes_to_oracle_instead_of_clipping():
    functions, inputs, oracle, protocol = fixture()
    functions["dml_s47"] = lambda x: np.column_stack([np.full(len(x), -1.0), np.zeros(len(x))])
    record, arrays = benchmark().measure(functions, inputs, oracle, protocol)
    raw = find(record["measurements"], "dml_s47", "raw", 32)
    safe = find(record["measurements"], "dml_s47", "safe", 32)
    assert raw["routing_counts"] == {"raw": 640}
    assert safe["routing_counts"]["fallback"] == 600
    assert benchmark().check_measurements(record, arrays)["passed"]


def test_raw_clock_excludes_provenance_route_allocation(monkeypatch):
    module = benchmark()
    _, inputs, _, protocol = fixture()
    clock = [0.0]
    original_full = np.full

    def counted_full(shape, value, *args, **kwargs):
        # Controlled overhead makes the timing boundary observable without a
        # flaky wall-clock speed assertion. Only raw provenance is charged.
        if isinstance(value, str) and value == "raw":
            clock[0] += 10.0
        return original_full(shape, value, *args, **kwargs)

    def oracle(x):
        clock[0] += 0.01
        return np.column_stack([np.ones(len(x)), np.zeros(len(x))])

    monkeypatch.setattr(module, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(np, "full", counted_full)
    functions = {identifier: oracle for identifier in IDS}
    record, arrays = module.measure(functions, inputs, oracle, protocol)
    for row in record["measurements"]:
        if row["phase"] == "raw":
            np.testing.assert_allclose(arrays[row["raw_key"]], 0.01, atol=1e-9, rtol=1e-9)


@pytest.mark.parametrize(
    "tamper",
    ["missing", "orphan", "negative", "summary", "routing", "input", "duplicate", "registry"],
)
def test_saved_measurement_tampering_fails_from_arrays_and_declared_registry(tamper):
    record, arrays = measured()
    row = record["measurements"][0]
    if tamper == "missing":
        del arrays[row["raw_key"]]
    elif tamper == "orphan":
        arrays["timing__orphan"] = np.ones(20)
    elif tamper == "negative":
        arrays[row["raw_key"]][0] = -0.01
    elif tamper == "summary":
        row["median_s"] += 0.1
    elif tamper == "routing":
        row["routing_counts"]["raw"] -= 1
    elif tamper == "input":
        arrays[row["input_key"]][0, 0] += 1.0
    elif tamper == "duplicate":
        record["measurements"].append(deepcopy(row))
    else:
        record["method_ids"][0] = "invented_method"
    check = benchmark().check_measurements(record, arrays)
    assert not check["passed"] and check["failures"]


def test_missing_callable_or_changed_contract_cannot_enter_timing_registry():
    functions, inputs, oracle, protocol = fixture()
    del functions["hermite"]
    with pytest.raises(ValueError):
        benchmark().measure(functions, inputs, oracle, protocol)
    functions, inputs, oracle, protocol = fixture()
    protocol["contract"]["barrier"] = 121
    with pytest.raises(ValueError):
        benchmark().measure(functions, inputs, oracle, protocol)


def cost_fixture():
    record, _ = measured()
    for row in record["measurements"]:
        # Replace noisy clock outcomes with explicit per-batch cost observations.
        # The cost account consumes summaries only after separate sample checking.
        if row["method_id"] == "oracle":
            row.update(median_s=0.064, p95_s=0.128)
        else:
            row.update(median_s=0.032, p95_s=0.096)
    return record, *metadata()


def test_cost_decomposition_uses_elapsed_once_and_matched_phase_batch_oracle():
    record, models, offline = cost_fixture()
    result = benchmark().cost_summary(record, models, offline, {"median_s": 0.2, "p95_s": 0.3})
    assert len(result["comparisons"]) == 32
    model = result["models"]["dml_s11"]
    assert model["fit_overhead_s"] == pytest.approx(0.1)
    assert model["offline_without_load_s"] == pytest.approx(3.01)
    item = find(result["comparisons"])
    median = item["statistics"]["median"]
    assert median["deployment"]["offline_s"] == pytest.approx(3.21)
    assert median["deployment"]["batch_counts"]["10"]["surrogate_s"] == pytest.approx(3.21 + 0.32)
    assert median["deployment"]["query_counts"]["1"]["measured_calls"] == 1
    assert median["deployment"]["query_counts"]["1"]["processed_rows"] == 32
    assert median["deployment"]["query_counts"]["1"]["surrogate_s"] == pytest.approx(3.21 + 0.032)
    assert item["reference_id"] == find(record["measurements"], "oracle", "raw", 32)["id"]
    p95 = item["statistics"]["p95"]["deployment"]
    assert p95["offline_s"] == pytest.approx(3.31)
    assert p95["batch_counts"]["10"]["surrogate_s"] == pytest.approx(3.31 + 0.96)
    hermite = find(result["comparisons"], "hermite")["statistics"]["median"]["deployment"]
    assert hermite["offline_s"] == pytest.approx(0.7)
    oracle = find(result["comparisons"], "oracle")["statistics"]["median"]["deployment"]
    assert oracle["offline_s"] == 0.0


def test_common_initialization_is_one_separate_charge_for_each_nn():
    record, models, offline = cost_fixture()
    record["common_initialization_s"] = 0.4
    for item in models.values():
        item["common_initialization_s"] = 0.4
        item["offline_s"] += 0.4
    result = benchmark().cost_summary(record, models, offline, 0.2)
    for identifier in IDS[:-2]:
        item = result["models"][identifier]
        assert item["common_initialization_s"] == pytest.approx(0.4)
        assert item["setup_s"] == pytest.approx(0.1)
        assert item["training_s"] == pytest.approx(0.8)
        assert item["elapsed_s"] == pytest.approx(1.0)
        assert item["fit_overhead_s"] == pytest.approx(0.1)
        assert item["offline_without_load_s"] == pytest.approx(3.41)
        assert find(result["comparisons"], identifier)["statistics"]["median"]["deployment"][
            "offline_s"
        ] == pytest.approx(3.61)
    assert result["models"]["hermite"]["offline_without_load_s"] == pytest.approx(0.5)
    assert result["models"]["oracle"]["offline_without_load_s"] == 0.0


def test_legacy_cost_metadata_has_explicit_zero_common_initialization():
    record, models, offline = cost_fixture()
    result = benchmark().cost_summary(record, models, offline, None)
    assert result["models"]["dml_s11"]["common_initialization_s"] == 0.0


@pytest.mark.parametrize("tamper", ["double_count", "unequal_common", "record_common"])
def test_common_initialization_double_count_or_inconsistent_record_is_rejected(tamper):
    record, models, offline = cost_fixture()
    record["common_initialization_s"] = 0.4
    for item in models.values():
        item["common_initialization_s"] = 0.4
        item["offline_s"] += 0.4
    if tamper == "double_count":
        models["dml_s11"]["offline_s"] += 0.4
    elif tamper == "unequal_common":
        models["dml_s11"]["common_initialization_s"] += 0.1
        models["dml_s11"]["offline_s"] += 0.1
    else:
        record["common_initialization_s"] += 0.1
    with pytest.raises(ValueError):
        benchmark().cost_summary(record, models, offline, None)


def test_break_even_is_integer_measured_calls_and_missing_load_is_not_zero():
    record, models, offline = cost_fixture()
    result = benchmark().cost_summary(record, models, offline, None)
    row = find(result["comparisons"])
    assert result["loading"]["status"] == "missing"
    assert row["statistics"]["median"]["deployment"] is None
    recovery = row["statistics"]["median"]["training_only"]["break_even"]
    assert recovery["continuous_calls"] == pytest.approx(3.01 / 0.032)
    assert recovery["first_integer_call"] == 95
    assert recovery["rows_at_first_integer_call"] == 3040
    for item in record["measurements"]:
        if item["method_id"] == "dml_s11":
            item.update(median_s=0.07, p95_s=0.13)
    result = benchmark().cost_summary(record, models, offline, 0.2)
    recovery = find(result["comparisons"])["statistics"]["median"]["deployment"]["break_even"]
    assert recovery["status"] == "no_online_advantage" and recovery["continuous_calls"] is None


@pytest.mark.parametrize(
    "tamper", ["teacher", "offline", "setup", "failed", "updates", "hermite", "load", "comparator"]
)
def test_bad_fit_metadata_or_missing_cost_component_is_rejected(tamper):
    record, models, offline = cost_fixture()
    load = 0.2
    if tamper == "teacher":
        models["dml_s11"]["train_teacher_s"] += 0.1
        models["dml_s11"]["offline_s"] += 0.1
    elif tamper == "offline":
        models["dml_s11"]["offline_s"] += 0.1
    elif tamper == "setup":
        models["dml_s11"]["setup_s"] += 2.0
    elif tamper == "failed":
        models["dml_s11"]["budget_failure"] = True
    elif tamper == "updates":
        models["dml_s11"]["updates"] -= 1
    elif tamper == "hermite":
        del offline["hermite"]["grid_setup_s"]
    elif tamper == "load":
        load = -0.2
    else:
        index = next(
            i for i, item in enumerate(record["measurements"]) if item["method_id"] == "oracle"
        )
        del record["measurements"][index]
    with pytest.raises(ValueError):
        benchmark().cost_summary(record, models, offline, load)
