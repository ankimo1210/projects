"""Numerical rebuild checks accept roundoff and reject meaningful price changes."""

import hashlib
import json

import numpy as np
import pytest

from johnhull.scripts.verify_frontier_artifacts import _compare_npz, _json_values, _same_values


def _payload(directory, price):
    directory.mkdir()
    array = np.array([price])
    npz = directory / "prices.npz"
    np.savez(npz, prices=array)
    payload = {
        "companions": {"prices.npz": hashlib.sha256(npz.read_bytes()).hexdigest()},
        "metrics": {
            "array_fingerprint": hashlib.sha256(array.tobytes()).hexdigest(),
            "price": price,
        },
    }
    js = directory / "metrics.json"
    js.write_text(json.dumps(payload))
    return js, npz


def test_roundoff_is_accepted_despite_different_integrity_fingerprints(tmp_path):
    left, left_npz = _payload(tmp_path / "left", 1.0)
    right, right_npz = _payload(tmp_path / "right", float(np.nextafter(1.0, 2.0)))
    _compare_npz(left_npz, right_npz)
    assert _same_values(_json_values(left), _json_values(right))


def test_outside_tolerance_is_rejected(tmp_path):
    left, left_npz = _payload(tmp_path / "left", 1.0)
    right, right_npz = _payload(tmp_path / "right", 1.001)
    with pytest.raises(RuntimeError, match="array differs"):
        _compare_npz(left_npz, right_npz)
    assert not _same_values(_json_values(left), _json_values(right))
