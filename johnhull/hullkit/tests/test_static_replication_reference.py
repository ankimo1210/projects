"""Independent BSM and absorbed-density references for Hull GE §26.17."""

import sys
from pathlib import Path

import pytest
from hullkit.static_replication import up_and_out_call_hedge

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def test_absorbed_density_prices_hull_barrier_independently():
    from build_static_replication_reference import absorbed_up_and_out_call

    assert absorbed_up_and_out_call(50, 50, 60, 0.10, 0.30, 0.75) == pytest.approx(
        0.313571, abs=1e-5
    )


def test_linear_system_reproduces_hull_table_and_convergence():
    from build_static_replication_reference import linear_system_hedge

    expected = {3: 0.73, 18: 0.38, 100: 0.32}
    for steps, printed in expected.items():
        result = linear_system_hedge(50, 50, 60, 0.10, 0.30, 0.75, steps)
        assert result["initial_value"] == pytest.approx(printed, abs=0.005)
        assert max(abs(value) for value in result["boundary_residuals"]) < 1e-9
    assert linear_system_hedge(50, 50, 60, 0.10, 0.30, 0.75, 3)["positions"] == pytest.approx(
        [1, -2.66, 0.97, 0.28], abs=0.005
    )


def test_library_matches_independent_linear_system_under_nonzero_yield():
    from build_static_replication_reference import linear_system_hedge

    args = (42.0, 50.0, 60.0, -0.01, 0.35, 0.8)
    independent = linear_system_hedge(*args, 18, dividend_yield=0.02)
    hedge = up_and_out_call_hedge(*args, steps=18, dividend_yield=0.02)
    assert hedge.positions == pytest.approx(independent["positions"], abs=1e-10)
    assert hedge.value(42.0, 0.0) == pytest.approx(independent["initial_value"], abs=1e-10)
