"""Finalization adds measurement evidence to existing fits without fitting."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest


def load_finalizer():
    path = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete/finalize.py"
    spec = importlib.util.spec_from_file_location("barrier_finalize_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_oracle_is_snapshot_based_and_recalculates(monkeypatch):
    finalizer = load_finalizer()
    runner = finalizer._runner()
    p, teacher = runner.protocol(), runner._teacher()
    calls, original = [], teacher.markov_batch

    def observed(inputs, **kwargs):
        calls.append((inputs.copy(), kwargs["order"], kwargs.get("check_order")))
        return original(inputs, **kwargs)

    monkeypatch.setattr(teacher, "markov_batch", observed)
    oracle = finalizer.checked_oracle(p, teacher)
    x = np.array([[100.0, 1.0], [119.0, 1.0], [120.0, 1.0], [121.0, 1.0]])
    expected = runner.oracle(x, verify=True)
    monkeypatch.setattr(
        runner, "protocol", lambda: pytest.fail("snapshot callback must not read protocol")
    )
    actual = oracle(x)
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-10)
    changed = x.copy()
    changed[0, 0] = 95
    updated = oracle(changed)
    assert updated[0, 0] != pytest.approx(actual[0, 0])
    assert any(order == 128 and check == 256 for _, order, check in calls)
    assert any(order == 256 and check is None for _, order, check in calls)


def test_loading_summary_recomputes_all_samples_and_preserves_provenance():
    finalizer = load_finalizer()
    samples = np.linspace(0.001, 0.010, 100)
    provenance = {"bytes": 17, "sha256": "a" * 64, "role": "measurement input, before finalization"}
    summary = finalizer.loading_summary(samples, provenance)
    assert summary["median_s"] == pytest.approx(0.0055)
    assert summary["p95_s"] == pytest.approx(np.quantile(samples, 0.95))
    assert summary["source_artifact"] == provenance
    assert "module_import" in summary["excludes"]
    assert summary["repeats"] == 100 and summary["warmups"] == 3
    with pytest.raises(ValueError):
        finalizer.loading_summary(samples[:99], provenance)


@pytest.fixture
def saved_fixture(tmp_path, monkeypatch):
    finalizer = load_finalizer()
    runner, benchmarks = finalizer._runner(), finalizer._benchmarks()
    p = runner.protocol()
    ids = [f"{mode}_s{seed}" for mode in ("price", "dml") for seed in (11, 29, 47)]
    record = {
        "schema": "fixture",
        "status": "complete",
        "protocol": p,
        "mode": "fixture",
        "models": {},
        "common_initialization_s": 0.25,
        "interpolation": {"gridsetup_s": 0.5},
    }
    arrays = {"model_ids": np.asarray(ids), "test.inputs": np.array([[100.0, 1.0], [115.0, 0.5]])}
    for model_id in ids:
        record["models"][model_id] = {
            "updates": 512,
            "requested_updates": 512,
            "budget_failure": False,
            "train_teacher_s": 1.0,
            "setup_s": 0.5,
            "training_s": 1.0,
            "elapsed_s": 2.0,
            "export_s": 0.1,
            "common_initialization_s": 0.25,
            "offline_s": 3.35,
        }
        export = {
            "kind": "barrier_nn",
            "dml": model_id.startswith("dml"),
            "feature_mean": [100.0, 0.0],
            "feature_std": [10.0, 1.0],
            "price_mean": 1.0,
            "price_scale": 1.0,
            "delta_scale": 1.0,
        }
        for j, shape in enumerate(((32, 2), (32, 32), (1, 32))):
            export[f"layer{j}_weight"], export[f"layer{j}_bias"] = (
                np.zeros(shape),
                np.zeros(shape[0]),
            )
        arrays.update(
            {f"weight.{model_id}.{key}": np.asarray(value) for key, value in export.items()}
        )
    arrays["interpolation.spots"], arrays["interpolation.times"] = (
        np.array([80.0, 119.0]),
        np.array([0.25, 2.0]),
    )
    arrays["interpolation.reference"] = np.dstack((np.ones((2, 2)), np.zeros((2, 2))))
    runner.save_result(tmp_path, record, arrays)
    # Runner behavior is independently tested; this fixture intentionally
    # contains saved synthetic exports, with no optimizer or NN training.
    monkeypatch.setattr(runner, "check_record", lambda *a, **k: {"fixture": True})
    monkeypatch.setattr(runner, "_learner", lambda: pytest.fail("finalizer must never fit"))
    monkeypatch.setattr(
        runner,
        "_adoption",
        lambda r: {
            "timing_and_full_cost": "measured" if "benchmark" in r and "costs" in r else "pending",
            "standard_speed_adopted": False,
        },
    )

    # Financial correctness of the actual checked oracle has its own test.
    # The wiring fixture uses a cheap independent callback and saved exports.
    def fixture_oracle(protocol, teacher):
        return lambda x: np.tile([1.0, -0.1], (len(x), 1))

    monkeypatch.setattr(finalizer, "checked_oracle", fixture_oracle)
    return finalizer, runner, benchmarks, tmp_path


def test_refresh_adds_outputs_loading_costs_and_check_does_not_retime(saved_fixture, monkeypatch):
    finalizer, runner, benchmarks, directory = saved_fixture
    result = finalizer.refresh_result(directory)
    assert result["benchmark"]["common_initialization_s"] == 0.25
    assert result["loading"]["repeats"] == 100
    assert result["costs"]["loading"]["status"] == "measured"
    assert result["adoption"]["timing_and_full_cost"] == "measured"
    assert "teacher_module_import" in result["costs"]["unmeasured_boundary"]
    record, arrays = runner.load_result(directory)
    assert arrays["loading.samples_s"].shape == (100,)
    assert record["loading"]["source_artifact"]["sha256"] != record["artifact"]["sha256"]
    monkeypatch.setattr(benchmarks, "measure", lambda *a, **k: pytest.fail("check must not retime"))
    monkeypatch.setattr(
        finalizer, "measure_loading", lambda *a, **k: pytest.fail("check must not reload-time")
    )
    assert finalizer.check_result(directory)["passed"] is True


def test_safe32_preserves_latency_but_cannot_compare_ordinary_delta_cost(saved_fixture):
    finalizer, _, _, directory = saved_fixture
    record = finalizer.refresh_result(directory)
    rows = [
        row
        for row in record["costs"]["comparisons"]
        if row["phase"] == "safe" and row["batch_size"] == 32
    ]
    assert len(rows) == 8
    for row in rows:
        assert row["comparison_status"] == "unsupported"
        for value in row["statistics"].values():
            assert value["training_only"] is None and value["deployment"] is None
            assert value["surrogate_online_s_per_batch"] >= 0


@pytest.mark.parametrize("target", ["timing", "load", "output", "cost", "common"])
def test_finalized_evidence_tampering_is_rejected(saved_fixture, target):
    finalizer, runner, _, directory = saved_fixture
    finalizer.refresh_result(directory)
    record, arrays = runner.load_result(directory)
    r, a = copy.deepcopy(record), {key: value.copy() for key, value in arrays.items()}
    row = r["benchmark"]["measurements"][0]
    if target == "timing":
        r["benchmark"]["measurements"][0]["median_s"] += 0.1
    elif target == "load":
        a["loading.samples_s"][0] += 1
    elif target == "output":
        a[row["output_key"]][0, 0, 0] += 1
    elif target == "common":
        r["benchmark"]["common_initialization_s"] = 0
    else:
        r["costs"]["comparisons"][0]["statistics"]["median"]["surrogate_online_s_per_batch"] += 1
    runner.save_result(directory, r, a)
    with pytest.raises(ValueError):
        finalizer.check_result(directory)
