"""Saved barrier research must replay without fitting or trusting report flags."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest


def load_runner():
    path = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete/build_reference.py"
    spec = importlib.util.spec_from_file_location("barrier_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_and_main_requires_frozen_independent_pilot():
    runner = load_runner()
    p = runner.protocol()
    assert p["contract"]["include_zero"] and p["contract"]["include_maturity"]
    assert p["splits"]["train_scenarios"] != p["splits"]["validation_scenarios"]
    p["state"] = "candidate"
    with pytest.raises(ValueError, match=r"pilot|frozen"):
        runner.run_experiment(p)


@pytest.fixture(scope="module")
def smoke_result():
    pytest.importorskip("torch")
    runner = load_runner()
    record, arrays = runner.run_experiment(runner.protocol(), smoke=True)
    assert record["status"] == "complete", record["failures"]
    return runner, record, arrays


def test_smoke_axes_all_seeds_and_replay_without_training(smoke_result, monkeypatch):
    runner, record, arrays = smoke_result
    learner = runner._learner()
    monkeypatch.setattr(learner, "train", lambda *a, **k: pytest.fail("check must not fit"))
    runner.check_record(record, arrays, fresh=True)
    assert record["mode"] == "smoke"
    assert arrays["train.inputs"].shape == (16, 2)
    assert arrays["validation.inputs"].shape == (8, 2)
    assert arrays["test.inputs"].shape == (12, 2)
    assert set(record["models"]) == {
        f"{mode}_s{seed}" for mode in ("price", "dml") for seed in (11, 29, 47)
    }
    assert record["effective"]["updates"] == 2
    assert record["adoption"]["standard_speed_adopted"] is False


@pytest.mark.parametrize(
    "target", ["prediction", "scale", "seed", "se", "fit", "contract", "cost", "metric", "safe"]
)
def test_saved_evidence_tampering_is_rejected(smoke_result, target):
    runner, record, arrays = smoke_result
    r = copy.deepcopy(record)
    a = {key: value.copy() for key, value in arrays.items()}
    if target == "prediction":
        a["prediction.dml_s11.test"][0, 0] += 1
    elif target == "scale":
        a["weight.dml_s11.price_scale"] *= 2
    elif target == "seed":
        a["train.path_seed"][0] += 1
    elif target == "se":
        a["train.label_se"][0, 0] = -1
    elif target == "fit":
        r["models"]["dml_s11"]["updates"] += 1
    elif target == "contract":
        r["protocol"]["contract"]["barrier"] += 1
    elif target == "cost":
        r["models"]["dml_s11"]["offline_s"] += 1
    elif target == "metric":
        r["models"]["dml_s11"]["test"]["delta_rmse"] += 1
    else:
        a["safe.dml_s11.prediction"][0, 0] += 1
    with pytest.raises(ValueError):
        runner.check_record(r, a)


def test_row_path_streams_teacher_se_and_independent_validation(smoke_result):
    runner, record, arrays = smoke_result
    values = runner.mc_labels(arrays["train.inputs"][:2], 4017, 256)
    np.testing.assert_allclose(values[0], arrays["train.labels"][:2])
    np.testing.assert_allclose(values[1], arrays["train.label_se"][:2])
    assert len(np.unique(arrays["train.path_seed"])) == 16
    assert set(arrays["train.path_seed"]).isdisjoint(arrays["validation.path_seed"])
    assert np.all(arrays["train.label_se"] >= 0)
    assert record["teacher"]["method"] == "last_conditional + first-transition score"


def test_save_load_and_failed_partial_records(smoke_result, tmp_path, monkeypatch):
    runner, record, arrays = smoke_result
    runner.save_result(tmp_path, record, arrays)
    r, a = runner.load_result(tmp_path)
    runner.check_record(r, a)
    learner = runner._learner()

    def fail(*args, **kwargs):
        raise ArithmeticError("deliberate partial fit failure")

    monkeypatch.setattr(learner, "train", fail)
    failed, partial = runner.run_experiment(runner.protocol(), smoke=True)
    assert failed["status"] == "incomplete"
    assert "deliberate partial fit failure" in str(failed["failures"])
    runner.save_result(tmp_path / "partial", failed, partial)
    with pytest.raises(ValueError, match="incomplete"):
        runner.check_record(failed, partial)


def test_diagnostic_seed_and_positive_se_tampering_are_checked(smoke_result):
    runner, record, arrays = smoke_result
    altered = {key: value.copy() for key, value in arrays.items()}
    altered["diagnostic.path_seed"][0, 0] += 1
    with pytest.raises(ValueError, match="diagnostic"):
        runner.check_record(record, altered)
    altered = {key: value.copy() for key, value in arrays.items()}
    altered["train.label_se"][0, 0] += 0.01
    with pytest.raises(ValueError, match="fresh"):
        runner.check_record(record, altered, fresh=True)


def test_safe_test_metrics_are_separate_and_boundary_keeps_contact_jump(smoke_result):
    runner, record, arrays = smoke_result
    for model_id in [*arrays["model_ids"].tolist(), "hermite", "oracle"]:
        assert arrays[f"prediction.{model_id}.safe"].shape == (12, 2)
        assert arrays[f"routing.{model_id}.safe"].shape == (12,)
    contact = arrays["boundary.inputs"][:, 0] == 120
    left = arrays["boundary.inputs"][:, 0] == 119.999
    assert np.isnan(arrays["boundary.reference"][contact, 1]).all()
    assert np.all(arrays["boundary.reference"][left, 0] > 0)
    assert record["models"]["dml_s11"]["test_raw"] == record["models"]["dml_s11"]["test"]
    altered = {key: value.copy() for key, value in arrays.items()}
    altered["prediction.dml_s11.safe"][0, 1] += 1
    with pytest.raises(ValueError, match="safe"):
        runner.check_record(record, altered)


def test_checker_does_not_load_learner_and_cli_checks_saved_bundle(
    smoke_result, monkeypatch, tmp_path
):
    runner, record, arrays = smoke_result

    def forbidden():
        pytest.fail("checker must not import learner or fit")

    monkeypatch.setattr(runner, "_learner", forbidden)
    runner.save_result(tmp_path, record, arrays)
    assert runner.main(["--check", "--fresh", "--output", str(tmp_path)]) == 0


def test_archive_integrity_rejects_modified_blob(smoke_result, tmp_path):
    runner, record, arrays = smoke_result
    _, archive = runner.save_result(tmp_path, record, arrays)
    with archive.open("ab") as stream:
        stream.write(b"modified archive boundary")
    with pytest.raises((ValueError, AssertionError), match=r"size|integrity"):
        runner.load_result(tmp_path)


def test_oracle_shares_transition_setup_within_same_call(monkeypatch):
    runner = load_runner()
    teacher, calls = runner._teacher(), []
    batch = teacher.markov_batch

    def observed(inputs, **kwargs):
        result = batch(inputs, **kwargs)
        calls.append(result["transition_setup_count"])
        return result

    def forbidden(*args, **kwargs):
        pytest.fail("oracle baseline must not repeat scalar kernels")

    monkeypatch.setattr(teacher, "markov_batch", observed)
    monkeypatch.setattr(teacher, "markov_reference", forbidden)
    values = runner.oracle(np.array([[80.0, 1.0], [100.0, 1.0], [119.0, 1.0]]), verify=True)
    assert np.isfinite(values).all()
    assert calls == [1, 1]  # one shared setup per order, not per spot


def test_common_initialization_is_charged_once_per_standalone_model(smoke_result):
    _, record, _ = smoke_result
    common = record["common_initialization_s"]
    assert np.isfinite(common) and common > 0
    for stats in record["models"].values():
        assert stats["common_initialization_s"] == pytest.approx(common)
        assert stats["offline_s"] == pytest.approx(
            stats["train_teacher_s"] + stats["elapsed_s"] + stats["export_s"] + common
        )
        assert stats["budget_s"] == 120


@pytest.mark.parametrize("tamper", ["zero", "double"])
def test_common_cost_omission_and_double_charge_are_rejected(smoke_result, tamper):
    runner, record, arrays = smoke_result
    altered = copy.deepcopy(record)
    if tamper == "zero":
        altered["common_initialization_s"] = 0
    else:
        altered["models"]["dml_s11"]["offline_s"] += record.get("common_initialization_s", 1)
    with pytest.raises(ValueError, match=r"common|offline"):
        runner.check_record(altered, arrays)


def test_common_initialization_preserves_rng_and_meta_caller_device(monkeypatch):
    torch = pytest.importorskip("torch")
    runner = load_runner()
    before, threads = torch.random.get_rng_state().clone(), torch.get_num_threads()

    def forbidden(*args, **kwargs):
        pytest.fail("CPU initialization must not touch GPU RNG")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    monkeypatch.setattr(torch.cuda, "get_rng_state_all", forbidden)
    monkeypatch.setattr(torch.cuda, "set_rng_state_all", forbidden)
    with torch.device("meta"):
        elapsed = runner._initialize_framework()
        assert torch.get_default_device().type == "meta"
    assert elapsed > 0
    assert torch.equal(before, torch.random.get_rng_state())
    assert threads == torch.get_num_threads()
