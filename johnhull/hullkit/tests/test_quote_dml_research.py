"""Research protocol, grouped sampling and artifact recomputation contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"


def runner():
    path = HERE / "build_reference.py"
    assert path.exists(), "quote-DML dataset/experiment runner is missing"
    spec = importlib.util.spec_from_file_location("quote_dml_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protocol():
    path = HERE / "protocol.json"
    assert path.exists(), "fixed quote-DML protocol is missing"
    return json.loads(path.read_text())


def test_protocol_and_grouped_splits():
    run, config = runner(), protocol()
    splits = {name: run.make_dataset(config, name) for name in ("train", "validation", "test")}
    for name, nrows in [("train", 2048), ("validation", 512), ("test", 1024)]:
        data = splits[name]
        assert data["x_quote"].shape == (nrows, 7)
        assert data["x_theta"].shape == (nrows, 7)
        assert data["g_quote"].shape == (nrows, 6)
        assert data["A"].shape == (nrows, 5, 5)
        assert np.unique(data["market_id"]).size == nrows // 8
        assert np.all(np.unique(data["market_id"], return_counts=True)[1] == 8)
        assert not np.any(data["failure_reason"])
    ids = [set(data["market_id"]) for data in splits.values()]
    assert ids[0].isdisjoint(ids[1]) and ids[0].isdisjoint(ids[2]) and ids[1].isdisjoint(ids[2])
    assert np.unique(splits["train"]["market_id"][:512]).size == 64
    expected = np.array(
        [(80, 0.05), (95, 0.25), (100, 1.5), (110, 4.5), (120, 5), (100, 0.5), (100, 1), (110, 3)]
    )
    np.testing.assert_allclose(splits["test"]["x_quote"][:8, 5:], expected, atol=1e-14, rtol=1e-12)


def test_calibration_shared_once_per_market(monkeypatch):
    run, config = runner(), protocol()
    config["sampling"]["markets"]["train"] = 4
    calls = []
    prepare = teacher.prepare_market

    def counted(q):
        calls.append(q.copy())
        return prepare(q)

    monkeypatch.setattr(teacher, "prepare_market", counted)
    data = run.make_dataset(config, "train")
    assert len(calls) == 4
    assert data["calibration_count"] == 4
    for start in range(0, 32, 8):
        np.testing.assert_allclose(
            data["x_quote"][start : start + 8, :5],
            np.tile(data["x_quote"][start, :5], (8, 1)),
            atol=1e-14,
        )
        np.testing.assert_allclose(
            data["A"][start : start + 8], np.tile(data["A"][start], (8, 1, 1)), atol=1e-14
        )


def test_dataset_regeneration_uses_tolerant_numeric_comparison():
    run, config = runner(), protocol()
    config["sampling"]["markets"]["train"] = 3
    first, second = run.make_dataset(config, "train"), run.make_dataset(config, "train")
    for key in (
        "x_quote",
        "x_theta",
        "price",
        "g_quote",
        "g_theta",
        "A",
        "a_quote",
        "integrated_rate",
    ):
        np.testing.assert_allclose(first[key], second[key], atol=1e-12, rtol=1e-10)
    np.testing.assert_array_equal(first["market_id"], second["market_id"])


def test_invalid_protocol_version_and_units_are_rejected(tmp_path):
    run, config = runner(), protocol()
    for mutated in (
        dict(config, schema_version=99),
        dict(config, curve=dict(config["curve"], quote_unit="bp")),
    ):
        path = tmp_path / "bad_protocol.json"
        path.write_text(json.dumps(mutated))
        with pytest.raises(ValueError):
            run.load_protocol(path)


def test_failed_calibration_is_recorded_without_resampling(monkeypatch):
    run, config = runner(), protocol()
    config["sampling"]["markets"]["train"] = 2
    original = run.make_dataset(copy.deepcopy(config), "train")

    def failed(q):
        raise RuntimeError("forced nonconvergence")

    monkeypatch.setattr(teacher, "prepare_market", failed)
    got = run.make_dataset(config, "train")
    assert got["x_quote"].shape == (16, 7)
    np.testing.assert_allclose(got["x_quote"], original["x_quote"], atol=1e-12, rtol=1e-10)
    assert np.all(np.isnan(got["price"]))
    assert all("forced nonconvergence" in value for value in got["failure_reason"])
    assert got["calibration_count"] == 2


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("contract", "payout", 2),
        ("contract", "strike", 105),
        ("training", "lr", 0.1),
        ("training", "hidden", [32, 32]),
        ("training", "lambda", 2),
        ("training", "dtype", "float32"),
        ("training", "modes", ["q_price"] * 5),
    ],
)
def test_protocol_cannot_claim_unimplemented_training_or_contract(section, key, value, tmp_path):
    run, config = runner(), protocol()
    config[section][key] = value
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="protocol"):
        run.load_protocol(path)


@pytest.fixture(scope="module")
def smoke_result():
    run = runner()
    record, arrays = run.run_experiment(protocol(), smoke=True)
    return run, record, arrays


def test_smoke_is_labelled_and_saved_predictions_replay(smoke_result):
    run, record, arrays = smoke_result
    assert record["experiment"] == "smoke"
    assert len(arrays["model_ids"]) == 34
    assert all(fit["updates"] == 2 for fit in record["fits"] if fit["kind"] == "nn")
    run.check_record(record, arrays, fresh=False)


@pytest.mark.parametrize("field", ["price", "g_quote", "coupon"])
def test_saved_prediction_risk_or_coupon_tamper_fails(smoke_result, field):
    run, record, original = smoke_result
    arrays = {key: value.copy() for key, value in original.items()}
    model = str(arrays["model_ids"][0])
    key = "contract_quotes" if field == "coupon" else f"pred__{model}__{field}"
    arrays[key].flat[0] += 0.001
    with pytest.raises((AssertionError, ValueError), match=r"replay|risk|contract|held|coupon"):
        run.check_record(record, arrays, fresh=False)


def test_saved_pass_flags_do_not_determine_numeric_acceptance(smoke_result):
    run, original, arrays = smoke_result
    record = copy.deepcopy(original)
    record["checks"] = {"arbitrary": "FAIL"}
    run.check_record(record, arrays, fresh=False)


def test_check_never_calls_training(smoke_result, monkeypatch):
    from deep_hedge_price import _quote_dml as learner

    run, record, arrays = smoke_result

    def forbidden(*args, **kwargs):
        raise AssertionError("check started training")

    monkeypatch.setattr(learner, "fit_nn", forbidden)
    monkeypatch.setattr(learner, "fit_ridge", forbidden)
    run.check_record(record, arrays, fresh=True)


@pytest.mark.parametrize(
    "key", ["test_market_id", "test_contract_id", "shock_dq", "cost_rate_bp", "reference_residual"]
)
def test_fixed_experiment_arrays_cannot_be_relabelled(smoke_result, key):
    run, record, original = smoke_result
    arrays = {name: value.copy() for name, value in original.items()}
    arrays[key].flat[0] += 1
    with pytest.raises((AssertionError, ValueError)):
        run.check_record(record, arrays, fresh=False)


def test_training_scales_cannot_be_changed_even_with_consistent_predictions(smoke_result):
    run, record, original = smoke_result
    arrays = {name: value.copy() for name, value in original.items()}
    model = str(arrays["model_ids"][0])
    arrays[f"weights__{model}__price_scale"] *= 2
    prediction = run._prediction(run._restore(arrays, model), run._dataset(arrays, "test"))
    arrays[f"pred__{model}__price"] = prediction["price"]
    arrays[f"pred__{model}__g_quote"] = prediction["g_quote"]
    with pytest.raises((AssertionError, ValueError), match="scale"):
        run.check_record(record, arrays, fresh=False)


def test_experiment_returns_failed_inputs_instead_of_discarding_them(monkeypatch):
    run = runner()

    def failed(q):
        raise RuntimeError("forced calibration failure")

    monkeypatch.setattr(teacher, "prepare_market", failed)
    record, arrays = run.run_experiment(protocol(), smoke=True)
    assert not record["complete_fits"]
    assert all("forced calibration failure" in value for value in arrays["train_failure_reason"])
    assert len(arrays["train_x_quote"]) == 32
    assert record["fits"] == []
