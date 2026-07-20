from __future__ import annotations

import json

import numpy as np
import pytest

from deep_hedge_price.pricing_artifacts import (
    assert_disjoint_splits,
    load_pricing_dataset,
    save_pricing_dataset,
)


def _splits():
    result = {}
    for index, split in enumerate(("train", "validation", "test", "ood")):
        inputs = np.column_stack(
            (
                np.linspace(0.8, 1.2, 4) + index,
                np.full(4, 0.5),
                np.full(4, 0.02),
                np.zeros(4),
                np.full(4, 0.2),
            )
        )
        price = np.linspace(0.01, 0.2, 4)
        result[split] = {
            "inputs": inputs,
            "price": price,
            "delta": price,
            "gamma": price,
            "vega": price,
            "theta": price,
            "rho": price,
            "standard_error": np.zeros(4),
            "ci_lower": price,
            "ci_upper": price,
        }
    return result


def _save(tmp_path):
    return save_pricing_dataset(
        _splits(),
        output_dir=tmp_path,
        model="black_scholes",
        teacher_method="analytic",
        parameterization="dimensionless_v1",
        seed=1,
        generator_version="test",
    )


def test_round_trip_and_deterministic_npz(tmp_path):
    manifest, arrays = _save(tmp_path)
    first = arrays.read_bytes()
    loaded_manifest, loaded = load_pricing_dataset(manifest)
    assert loaded_manifest.overlap_count == 0
    assert loaded["train_inputs"].shape == (4, 5)
    _save(tmp_path)
    assert arrays.read_bytes() == first


def test_rejects_overlap_before_save(tmp_path):
    splits = _splits()
    splits["test"]["inputs"][0] = splits["train"]["inputs"][0]
    with pytest.raises(ValueError, match="overlap"):
        save_pricing_dataset(
            splits,
            output_dir=tmp_path,
            model="bs",
            teacher_method="analytic",
            parameterization="v1",
            seed=1,
            generator_version="test",
        )


def test_rejects_missing_unknown_schema_shape_and_digest(tmp_path):
    manifest, arrays = _save(tmp_path)
    original = json.loads(manifest.read_text())
    for mutation, match in (
        (lambda raw: raw.pop("model"), "missing fields"),
        (lambda raw: raw.__setitem__("schema_version", 999), "unsupported"),
        (
            lambda raw: raw["array_metadata"]["train_price"].__setitem__("shape", [99]),
            "metadata mismatch",
        ),
    ):
        raw = json.loads(json.dumps(original))
        mutation(raw)
        manifest.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match=match):
            load_pricing_dataset(manifest)
    manifest.write_text(json.dumps(original))
    arrays.write_bytes(arrays.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_pricing_dataset(manifest)


def test_disjoint_helper_requires_all_splits():
    with pytest.raises(ValueError, match="missing split"):
        assert_disjoint_splits({"train": np.zeros((1, 5))})
