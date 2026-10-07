"""Hull Example5.4 and Snapshot5.2 forward mark versus settlement."""

import math

import pytest
from hullkit import _forward_pricing as f


def test_source_four_reproducible_values():
    forward = f.no_income_forward(25, 0.1, 0.5)
    assert forward == pytest.approx(26.28, abs=0.005)
    assert f.forward_value(forward, 24, 0.1, 0.5) == pytest.approx(2.17, abs=0.005)
    cash = f.offset_forward_cash(1e6, 62500, 1.5, 1.504)
    assert [cash["contracts"], cash["locked_terminal_cash"]] == pytest.approx([16, 4000])


def test_independent_spot_bond_replication_offset_and_limits():
    forward = f.no_income_forward(25, 0.1, 0.5)
    value = f.forward_value(forward, 24, 0.1, 0.5)
    assert value == pytest.approx(25 - 24 * math.exp(-0.1 * 0.5))
    assert f.forward_value(forward, 24, 0.1, 0.5, side="short") == pytest.approx(-value)
    assert f.forward_value(forward, forward, 0.1, 0.5) == pytest.approx(0, abs=1e-12)
    assert f.forward_value(25, 24, 0.1, 0) == pytest.approx(1)
    # Synthetic funding rate: cannot pin the source's 3900 without an input rate.
    assert f.forward_value(1.504, 1.5, 0.05, 0.25, units=1e6) == pytest.approx(
        4000 * math.exp(-0.05 * 0.25)
    )
