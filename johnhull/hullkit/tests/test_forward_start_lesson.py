"""Shared lesson plots show fixing, invariant tenor and honest MC uncertainty."""

import importlib

import numpy as np
import pytest


def lesson():
    return importlib.import_module("hullkit._forward_start_lesson")


def test_contract_strikes_are_fixed_at_the_path_start_spot():
    figure = lesson()._figures()["forward_contract"]
    roles = {trace.meta["role"]: trace for trace in figure.data}
    for name in ("A", "B", "C"):
        fixing, strike = roles[f"fixing-{name}"], roles[f"strike-{name}"]
        assert list(strike.y) == [fixing.y[0], fixing.y[0]]
        assert strike.x[0] == fixing.x[0] == 0.75
        assert strike.x[-1] == 1.75


def test_equal_life_zero_yield_delay_curve_is_flat():
    figure = lesson()._figures()["forward_start_delay"]
    zero = next(trace for trace in figure.data if trace.meta["role"] == "q-0")
    np.testing.assert_allclose(zero.y, 10.450583572185565, atol=1e-10)


def test_fixed_expiry_reaches_zero_and_monte_carlo_has_intervals():
    figure = lesson()._figures()["forward_fixed_expiry"]
    for trace in figure.data:
        if trace.meta["role"].startswith("q-"):
            assert trace.x[-1] == 2 and trace.y[-1] == 0
    mc = next(trace for trace in figure.data if trace.meta["role"] == "mc")
    assert mc.error_y.visible
    assert all(value > 0 for value in mc.error_y.array)
    assert list(mc.x) == [0, 1, 1.75]


def test_lesson_rejects_a_reference_with_a_missing_digest(tmp_path):
    module = lesson()
    import json

    record = json.loads(module._RECORD.read_text())
    del record["source_sha256"]["hullkit/src/hullkit/forward_start.py"]
    output = tmp_path / "record.json"
    output.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="source"):
        module._load_reference(record_path=output)
