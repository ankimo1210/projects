"""Hull Figure7.9 symbolic ten exchanges, on explicit synthetic monotone forwards."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s


@pytest.mark.parametrize("slope", [0.001, -0.001])
@pytest.mark.parametrize("receive", ["fixed", "floating"])
def test_source_ten_exchanges_and_independent_residual_pv(slope, receive):
    t = np.arange(1, 11, dtype=float)
    z = 0.04 + slope * t
    a = s.swap_roll_schedule(1e6, t, (t, z), receive=receive)
    assert a["initial_value"] == pytest.approx(0, abs=1e-8)
    assert len(a["net_cash"]) == 10
    sign = 1 if receive == "fixed" else -1
    expected_sign = sign * np.sign(slope)
    assert np.sign(a["net_cash"][0]) == expected_sign
    assert np.sign(a["net_cash"][-1]) == -expected_sign
    df = np.exp(-t * z)
    for i in range(1, 11):
        settled = np.sum(a["net_cash"][:i] * df[:i])
        remaining = (a["initial_value"] - settled) / df[i - 1]
        assert a["roll_values"][i] == pytest.approx(remaining, abs=1e-8)
    assert a["roll_values"][-1] == pytest.approx(0, abs=1e-8)
