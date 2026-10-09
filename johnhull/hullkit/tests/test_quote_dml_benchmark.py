"""Quote-DML timing contracts, exact vectorized baseline and cost recovery."""

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_dml_hedging as hedging
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"


def benchmark():
    path = HERE / "benchmark.py"
    assert path.exists(), "Independent quote-DML benchmark not implemented"
    spec = importlib.util.spec_from_file_location("quote_dml_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_arrays():
    """Complete zero-weight exports: genuine curves and inference, no training."""
    protocol = json.loads((HERE / "protocol.json").read_text())
    terms = np.array(protocol["sampling"]["test_contracts"])
    q0 = np.array(protocol["curve"]["base_quotes"])
    data = {
        key: []
        for key in (
            "x_quote",
            "x_theta",
            "A",
            "price",
            "g_quote",
            "discount",
            "integrated_rate",
            "a_quote",
            "B",
        )
    }
    for q in (q0, q0 + np.array([0.001, -0.001, 0.001, -0.001, 0.001])):
        market = teacher.prepare_market(q)
        for spot, maturity in terms:
            exact = teacher.analytic(market, spot, maturity)
            data["x_quote"].append(np.r_[q, spot, maturity])
            data["x_theta"].append(np.r_[market.calibration.zeros, spot, maturity])
            data["A"].append(market.dz_dq)
            data["B"].append(hedging.held_risk(market, spot, q))
            for key in ("price", "g_quote", "discount", "integrated_rate", "a_quote"):
                data[key].append(exact[key])
    arrays = {"test_" + key: np.array(value) for key, value in data.items()}
    arrays["test_market_id"] = np.repeat([200000, 200001], 8)
    model_ids = []
    powers = np.array(
        [(i, j, k) for i in range(4) for j in range(4) for k in range(4) if i + j + k <= 3]
    )
    for size in (512, 2048):
        for mode in protocol["training"]["modes"]:
            for seed in protocol["training"]["seeds"]:
                identifier = f"{mode}_n{size}_s{seed}"
                exported = {
                    "kind": "nn",
                    "mode": mode,
                    "feature_mean": np.zeros(7),
                    "feature_std": np.ones(7),
                    "price_mean": 0.5,
                    "price_scale": 1.0,
                    "risk_scale": np.ones(6),
                    "layer0_weight": np.zeros((64, 7)),
                    "layer0_bias": np.zeros(64),
                    "layer1_weight": np.zeros((64, 64)),
                    "layer1_bias": np.zeros(64),
                    "layer2_weight": np.zeros((1, 64)),
                    "layer2_bias": np.zeros(1),
                }
                model_ids.append(identifier)
                for key, value in exported.items():
                    arrays[f"weights__{identifier}__{key}"] = np.asarray(value)
        for differential in (False, True):
            identifier = f"ridge_{'dml' if differential else 'price'}_n{size}"
            exported = {
                "kind": "ridge",
                "differential": differential,
                "feature_mean": np.zeros(3),
                "feature_std": np.ones(3),
                "price_mean": 0.5,
                "price_scale": 1.0,
                "risk_scale": np.ones(6),
                "powers": powers,
                "coefficients": np.zeros(20),
            }
            model_ids.append(identifier)
            for key, value in exported.items():
                arrays[f"weights__{identifier}__{key}"] = np.asarray(value)
    arrays["model_ids"] = np.array(model_ids)
    return protocol, arrays


def test_vectorized_exact_cached_price_and_six_greeks_match_teacher():
    module = benchmark()
    protocol, arrays = fixture_arrays()
    dataset = {
        key[len("test_") :]: value for key, value in arrays.items() if key.startswith("test_")
    }
    prediction = module.exact_cached(dataset, strike=100.0, sigma=0.2)
    np.testing.assert_allclose(prediction["price"], dataset["price"], atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(prediction["g_quote"], dataset["g_quote"], atol=1e-10, rtol=1e-9)
    price_only = module.exact_cached(
        dataset,
        strike=protocol["contract"]["strike"],
        sigma=protocol["contract"]["sigma"],
        greeks=False,
    )
    assert "g_quote" not in price_only
    np.testing.assert_allclose(price_only["price"], prediction["price"])


@pytest.mark.parametrize(
    "values,status,want",
    [
        ((100.0, 0.0, 0.1, 0.01), "break_even", 100 / 0.09),
        ((0.0, 10.0, 0.1, 0.01), "advantage_from_start", 0.0),
        ((20.0, 0.0, 0.01, 0.01), "no_online_advantage", None),
        ((20.0, 0.0, 0.01, 0.02), "no_online_advantage", None),
    ],
)
def test_break_even_respects_online_gain_and_initial_advantage(values, status, want):
    result = benchmark().break_even(*values)
    assert result["status"] == status
    if want is None:
        assert result["evaluations"] is None
    else:
        assert result["evaluations"] == pytest.approx(want)


def test_negative_or_nonfinite_costs_cannot_produce_recovery_claim():
    for values in ((-1.0, 0.0, 0.1, 0.01), (0.0, 0.0, 0.1, np.nan)):
        with pytest.raises(ValueError):
            benchmark().break_even(*values)


def test_rebootstrap_bump_baseline_returns_correct_price_risk_and_actual_count():
    module = benchmark()
    q = teacher.BASE_QUOTES + np.array([0.001, -0.001, 0.001, -0.001, 0.001])
    prediction, count = module._rebootstrap_bump(q, 100.0, 1.5, 100.0, 0.2)
    expected = teacher.analytic(teacher.prepare_market(q), 100.0, 1.5)
    assert count == 11
    np.testing.assert_allclose(prediction["price"], [expected["price"]], atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(prediction["g_quote"][0], expected["g_quote"], atol=1e-7, rtol=1e-6)


def test_measurement_check_recomputes_median_and_p95_from_samples():
    module = benchmark()
    record = {
        "settings": {"repeats": 3},
        "measurements": [
            {
                "id": "fixture",
                "raw_key": "timing__fixture",
                "count_key": "calibration_count__fixture",
                "calibrations_per_call": 0,
                "median_s": 2.0,
                "p95_s": 2.9,
            }
        ],
    }
    raw = {
        "timing__fixture": np.array([1.0, 2.0, 3.0]),
        "calibration_count__fixture": np.zeros(3, dtype=int),
    }
    module.check_measurement(record, raw)
    for field in ("median_s", "p95_s"):
        altered = copy.deepcopy(record)
        altered["measurements"][0][field] += 0.5
        with pytest.raises((AssertionError, ValueError)):
            module.check_measurement(altered, raw)


def test_smoke_measurement_covers_all_raw_modes_and_predeclared_representatives():
    module = benchmark()
    protocol, arrays = fixture_arrays()
    record, raw = module.measure(protocol, arrays, smoke=True)
    module.check_measurement(record, raw)
    json.dumps(record, allow_nan=False)
    assert record["settings"]["batches"] == [1, 8, 16]
    assert record["settings"]["repeats"] == 3
    assert len(record["representative_ids"]) == 7
    assert set(record["representative_ids"]) == {
        *(f"{mode}_n2048_s11" for mode in protocol["training"]["modes"]),
        "ridge_price_n2048",
        "ridge_dml_n2048",
    }
    raw_models = {item["model_id"] for item in record["measurements"] if item["source"] == "raw"}
    assert raw_models == set(arrays["model_ids"])
    for item in record["measurements"]:
        assert len(raw[item["raw_key"]]) == 3
        assert item["median_s"] >= 0
        if item["source"] in ("raw", "exact_cached"):
            assert item["calibrations_per_call"] == 0
        elif item["cache"] == "row":
            assert item["calibrations_per_call"] == item["batch_size"]
        elif item["cache"] == "market":
            assert item["calibrations_per_call"] == (1 if item["batch_size"] <= 8 else 2)
    assert any(
        item["source"] == "bump" and item["calibrations_per_call"] == 11
        for item in record["measurements"]
    )
    assert record["bump_reason"]


def registry_fixture():
    """Declared benchmark coverage with synthetic times, without any fitting."""
    protocol = json.loads((HERE / "protocol.json").read_text())
    identifiers = []
    for size in protocol["training"]["sizes"]:
        identifiers.extend(
            f"{mode}_n{size}_s{seed}"
            for mode in protocol["training"]["modes"]
            for seed in protocol["training"]["seeds"]
        )
        identifiers.extend(f"ridge_{kind}_n{size}" for kind in ("price", "dml"))
    largest = max(protocol["training"]["sizes"])
    representatives = [f"{mode}_n{largest}_s11" for mode in protocol["training"]["modes"]] + [
        f"ridge_{kind}_n{largest}" for kind in ("price", "dml")
    ]
    record = {
        "schema_version": 1,
        "experiment": "main",
        "model_ids": identifiers,
        "representative_ids": representatives,
        "settings": {
            "batches": [1, 32, 1024],
            "repeats": 100,
            "warmup": 3,
            "statistics": ["median", "p95"],
            "unit": "seconds_per_batch",
        },
        "measurements": [],
    }
    raw = {}

    def add(identifier, source, operation, cache, batch, model=None, count=0):
        timing_key = f"timing__{identifier}"
        count_key = f"calibration_count__{identifier}"
        raw[timing_key] = np.ones(100)
        raw[count_key] = np.full(100, count)
        item = {
            "id": identifier,
            "source": source,
            "operation": operation,
            "cache": cache,
            "batch_size": batch,
            "model_id": model,
            "raw_key": timing_key,
            "count_key": count_key,
            "calibrations_per_call": count,
            "median_s": 1.0,
            "p95_s": 1.0,
        }
        if source == "safe":
            routing_key = f"routing_count__{identifier}"
            item["routing_key"] = routing_key
            item["routing_counts_per_call"] = [batch, 0, 0, 0]
            raw[routing_key] = np.tile([batch, 0, 0, 0], (100, 1))
        record["measurements"].append(item)

    for batch in (1, 32, 1024):
        for operation in ("price", "price_risk"):
            add(
                f"exact_cached__{operation}__batch{batch}",
                "exact_cached",
                operation,
                "prepared",
                batch,
            )
        for model in identifiers:
            for operation in ("price", "price_risk"):
                add(
                    f"raw__{model}__{operation}__batch{batch}",
                    "raw",
                    operation,
                    "prepared",
                    batch,
                    model,
                )
        for cache in ("market", "row"):
            count = (batch + 7) // 8 if cache == "market" else batch
            add(
                f"calibration__{cache}__batch{batch}",
                "calibration",
                "calibration",
                cache,
                batch,
                count=count,
            )
            add(
                f"exact_e2e__{cache}__price_risk__batch{batch}",
                "e2e",
                "price_risk",
                cache,
                batch,
                "exact",
                count,
            )
            for model in representatives:
                for source in ("e2e", "safe"):
                    add(
                        f"{source}__{model}__{cache}__price_risk__batch{batch}",
                        source,
                        "price_risk",
                        cache,
                        batch,
                        model,
                        count,
                    )
        add(
            f"hedge_solve__batch{batch}",
            "hedge",
            "hedge_solve",
            "prepared",
            batch,
        )
    add(
        "rebootstrap_bump__price_risk__batch1",
        "bump",
        "price_risk",
        "none",
        1,
        "rebootstrap_bump",
        11,
    )
    return protocol, record, raw


def test_fixed_registry_accepts_complete_main_observations_without_rerunning_timing():
    protocol, record, raw = registry_fixture()
    benchmark().check_measurement(
        record,
        raw,
        model_ids=record["model_ids"],
        protocol=protocol,
    )


@pytest.mark.parametrize(
    "field,changed",
    [
        ("source", "raw"),
        ("operation", "price"),
        ("cache", "row"),
        ("batch_size", 1),
        ("model_id", "q_price_n512_s11"),
        ("raw_key", "timing__exact_cached__price__batch32"),
        ("count_key", "calibration_count__exact_cached__price__batch32"),
    ],
)
def test_fixed_measurement_identity_cannot_be_relabelled(field, changed):
    _, record, raw = registry_fixture()
    item = next(
        item
        for item in record["measurements"]
        if item["id"] == "exact_e2e__market__price_risk__batch32"
    )
    item[field] = changed
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


@pytest.mark.parametrize(
    "missing",
    [
        "raw__theta_quote_metric_n512_s29__price_risk__batch1024",
        "exact_e2e__market__price_risk__batch32",
        "safe__q_dml_n2048_s11__row__price_risk__batch1024",
        "calibration__market__batch32",
        "hedge_solve__batch1024",
        "rebootstrap_bump__price_risk__batch1",
    ],
)
def test_fixed_measurement_registry_rejects_missing_comparators(missing):
    _, record, raw = registry_fixture()
    record["measurements"] = [item for item in record["measurements"] if item["id"] != missing]
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


def test_fixed_registry_rejects_unplanned_observations_and_representatives():
    _, record, raw = registry_fixture()
    added = copy.deepcopy(record["measurements"][0])
    added["id"] = "additional_experiment"
    record["measurements"].append(added)
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)
    _, record, raw = registry_fixture()
    record["representative_ids"][0] = "q_price_n2048_s29"
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


def test_external_model_roster_and_protocol_cannot_be_replaced_by_saved_metadata():
    protocol, record, raw = registry_fixture()
    altered = copy.deepcopy(record)
    altered["model_ids"] = altered["model_ids"][:-1]
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(
            altered,
            raw,
            model_ids=record["model_ids"],
            protocol=protocol,
        )
    altered = copy.deepcopy(record)
    altered["settings"]["warmup"] = 0
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(
            altered,
            raw,
            model_ids=record["model_ids"],
            protocol=protocol,
        )


@pytest.mark.parametrize(
    "identifier,count",
    [
        ("raw__q_dml_n2048_s11__price_risk__batch32", 1),
        ("exact_e2e__market__price_risk__batch32", 32),
        ("safe__q_dml_n2048_s11__row__price_risk__batch32", 4),
        ("rebootstrap_bump__price_risk__batch1", 10),
    ],
)
def test_saved_calibration_counts_cannot_redefine_cache_conditions(identifier, count):
    _, record, raw = registry_fixture()
    item = next(item for item in record["measurements"] if item["id"] == identifier)
    item["calibrations_per_call"] = count
    raw[item["count_key"]] = np.full(100, count)
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


def test_safe_timing_requires_its_routing_samples_and_no_failed_predictions():
    _, record, raw = registry_fixture()
    item = next(
        item
        for item in record["measurements"]
        if item["id"] == "safe__q_dml_n2048_s11__market__price_risk__batch32"
    )
    del item["routing_key"]
    del item["routing_counts_per_call"]
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)
    _, record, raw = registry_fixture()
    item = next(
        item
        for item in record["measurements"]
        if item["id"] == "safe__q_dml_n2048_s11__market__price_risk__batch32"
    )
    item["routing_counts_per_call"] = [31, 0, 1, 0]
    raw[item["routing_key"]] = np.tile([31, 0, 1, 0], (100, 1))
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


def test_legacy_measurement_registry_can_be_checked_against_external_inputs():
    protocol, record, raw = registry_fixture()
    model_ids = record.pop("model_ids")
    benchmark().check_measurement(record, raw, model_ids=model_ids, protocol=protocol)


def test_missing_model_registry_cannot_disable_fixed_experiment_validation():
    _, record, raw = registry_fixture()
    del record["model_ids"]
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)


@pytest.mark.parametrize("change", ["missing", "orphan"])
def test_timing_array_registry_rejects_unregistered_or_missing_samples(change):
    _, record, raw = registry_fixture()
    if change == "missing":
        del raw["timing__exact_cached__price_risk__batch32"]
    else:
        raw["timing__unregistered_probe"] = np.ones(100)
    with pytest.raises((AssertionError, ValueError)):
        benchmark().check_measurement(record, raw)
