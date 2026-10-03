"""Independent pins distinguish excess return from synthetic total return."""

import importlib

import pytest


def test_printed_example_negative_contribution_and_zero_price_extension():
    m = importlib.import_module("johnhull.scripts.build_factor_risk_reference")
    d = m.build()
    assert d["printed_pins"]["example_28_3_excess"] == pytest.approx(0.06)
    assert d["printed_pins"]["contributions"] == pytest.approx([0.01, -0.01, 0.06])
    assert d["synthetic_total_return"] == pytest.approx(0.10)
    assert d["zero_price_extension"]["excess"] == pytest.approx(0.06)
    assert d["zero_price_extension"]["with_priced_extra"] == pytest.approx(0.30)
    assert len(d["cases"]) == 12


def test_independent_hedge_and_orthogonal_basis_preserve_local_risk():
    m = importlib.import_module("johnhull.scripts.build_factor_risk_reference")
    d = m.build()
    assert d["hedge"]["weights"] == [0.25, 0.25, 0.5]
    assert d["hedge"]["portfolio_loading"] == pytest.approx([0, 0], abs=1e-15)
    assert d["hedge"]["portfolio_return"] == pytest.approx(0.04)
    for row in d["rotations"]:
        assert row["excess"] == pytest.approx(0.04)
        assert row["volatility"] == pytest.approx(5**0.5 / 10)
    assert d["capm"]["excess"][10] == pytest.approx(0)
