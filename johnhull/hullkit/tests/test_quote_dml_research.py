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
