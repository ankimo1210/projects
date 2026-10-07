"""Hull Table4.5 and forward-rate locked cash examples."""

import numpy as np
import pytest
from hullkit import _rates_foundations as r

CURVE = ([1, 2, 3, 4, 5], [0.03, 0.04, 0.046, 0.05, 0.053])


def test_source_all_ten_values():
    forwards = [r.curve_forward(i, i + 1, CURVE)["continuous_rate"] for i in [1, 2, 3, 4]]
    assert 100 * np.array(forwards) == pytest.approx([5, 5.8, 6.2, 6.5])
    a = r.curve_forward(1, 2, CURVE)
    b = r.curve_forward(3, 4, CURVE)
    assert b["continuous_rate"] == pytest.approx(0.062)
    assert [
        100 * a["start_growth"],
        100 * a["end_growth"],
        100 * b["start_growth"],
        100 * b["end_growth"],
    ] == pytest.approx([103.05, 108.33, 114.80, 122.14], abs=0.005)
    assert 100 * (0.053 - 0.03) == pytest.approx(2.3)
    assert a["start_growth"] * np.exp(a["continuous_rate"]) == pytest.approx(a["end_growth"])


def test_independent_discount_cash_replication_and_derivative():
    a = r.curve_forward(1, 2, CURVE)
    # Borrow 100 at time zero until t1, invest 100 until t2; zero entry cash.
    payments = np.array([-100 * np.exp(0.03), 100 * np.exp(0.04 * 2)])
    assert np.log(-payments[1] / payments[0]) == pytest.approx(a["continuous_rate"])
    curve = ([0, 1, 2, 3], [0.02, 0.03, 0.04, 0.05])
    for t in [0.4, 1.4, 2.4]:
        assert r.instantaneous_curve_forward(t, curve) == pytest.approx(0.02 + 0.02 * t, abs=1e-9)
    # Distinct slopes at a knot: central derivative is their mean.
    assert r.instantaneous_curve_forward(1, ([0, 1, 2], [0.02, 0.03, 0.05])) == pytest.approx(
        0.045, abs=2e-7
    )
