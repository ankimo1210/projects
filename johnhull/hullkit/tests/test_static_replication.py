"""Hull 11e GE §26.17: a call ladder matches a barrier boundary."""

import pytest
from hullkit.static_replication import up_and_out_call_hedge


def test_table_26_1_positions_and_rounded_initial_values():
    hedge = up_and_out_call_hedge(50.0, 50.0, 60.0, 0.10, 0.30, 0.75, steps=3)
    assert hedge.strikes == (50.0, 60.0, 60.0, 60.0)
    assert hedge.maturities == pytest.approx((0.75, 0.75, 0.50, 0.25))
    assert hedge.positions == pytest.approx((1.0, -2.66, 0.97, 0.28), abs=0.005)
    assert hedge.value(50.0, 0.0) == pytest.approx(0.73, abs=0.005)


@pytest.mark.parametrize("steps, printed", [(3, 0.73), (18, 0.38), (100, 0.32)])
def test_hull_convergence_and_boundary_nodes(steps, printed):
    hedge = up_and_out_call_hedge(50.0, 50.0, 60.0, 0.10, 0.30, 0.75, steps=steps)
    assert hedge.value(50.0, 0.0) == pytest.approx(printed, abs=0.005)
    for index in range(steps):
        time = 0.75 * index / steps
        assert hedge.value(60.0, time) == pytest.approx(0.0, abs=2e-10)


@pytest.mark.parametrize(
    "args",
    [
        (50.0, 50.0, 50.0, 0.1, 0.3, 0.75, 3),
        (50.0, 60.0, 55.0, 0.1, 0.3, 0.75, 3),
        (50.0, 50.0, 60.0, 0.1, 0.0, 0.75, 3),
        (50.0, 50.0, 60.0, 0.1, 0.3, 0.0, 3),
        (50.0, 50.0, 60.0, 0.1, 0.3, 0.75, 0),
    ],
)
def test_invalid_boundary_or_grid_is_rejected(args):
    with pytest.raises(ValueError):
        up_and_out_call_hedge(*args[:-1], steps=args[-1])
