"""Recompute RB-F05 research metrics; saved flags are never numerical evidence."""

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F05"
SPEC = importlib.util.spec_from_file_location("digital_reference", HERE / "build_reference.py")
REF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REF)


def artifacts():
    """Read only the committed small reference arrays, never rerun training."""
    data = json.loads((HERE / "reference.json").read_text())
    with np.load(HERE / "reference.npz", allow_pickle=False) as source:
        arrays = {key: source[key].copy() for key in source.files}
    return data, arrays


def test_metrics_are_in_physical_units_and_reject_nonfinite_values():
    assert REF.metrics(np.array([[1.0, 0.03], [3.0, 0.07]]), np.array([[0.0, 0.02], [1.0, 0.05]]))[
        "delta_rmse"
    ] == pytest.approx(np.sqrt((0.01**2 + 0.02**2) / 2))
    with pytest.raises(ValueError):
        REF.metrics(np.array([[np.nan, 0]]), np.array([[0, 0]]))


def test_cached_and_fresh_independent_checks_pass():
    data, arrays = artifacts()
    REF.check_record(data, arrays, fresh=True)


@pytest.mark.parametrize("target", ["prediction", "metric", "split", "cost"])
def test_tampering_predictions_metrics_split_or_total_cost_is_detected(target):
    data, arrays = artifacts()
    data = copy.deepcopy(data)
    name = data["runs"][0]["name"]
    if target == "prediction":
        arrays[f"{name}_prediction"][0, 1] += 0.02
    elif target == "metric":
        data["runs"][0]["test"]["price_rmse"] += 0.1
    elif target == "split":
        arrays["validation_id"][0] = arrays["train_id"][0]
    else:
        data["runs"][0]["offline_s"] += 1
    with pytest.raises(AssertionError):
        REF.check_record(data, arrays, fresh=False)


def test_default_caller_threads_match_recorded_training_and_inference(monkeypatch, tmp_path):
    """Reproduce the review issue with genuine training/inference at a tiny cap."""
    import torch

    from deep_hedge_price import _digital_dml as learner

    original_train, original_predict = learner.train, learner.predict
    observed = []

    def small_train(*args, **kwargs):
        kwargs["max_updates"] = min(kwargs.get("max_updates", 2), 2)
        return original_train(*args, **kwargs)

    def measured_predict(*args, **kwargs):
        observed.append(torch.get_num_threads())
        return original_predict(*args, **kwargs)

    monkeypatch.setattr(learner, "train", small_train)
    monkeypatch.setattr(learner, "predict", measured_predict)
    monkeypatch.setattr(REF, "HERE", tmp_path)
    previous = torch.get_num_threads()
    try:
        torch.set_num_threads(2)
        REF.generate()
        record = json.loads((tmp_path / "reference.json").read_text())
        assert observed and set(observed) == {record["hardware"]["threads"]} == {1}
        assert torch.get_num_threads() == 2, "restore the caller's thread setting"
    finally:
        torch.set_num_threads(previous)
