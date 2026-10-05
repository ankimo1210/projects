"""Hull §10.2: four positions, writer profit and independent min-form payoffs."""

import numpy as np
import pytest
from hullkit._option_mechanics import option_cashflows


@pytest.mark.parametrize("kind,strike,premium", [("call", 100, 5), ("put", 70, 7)])
@pytest.mark.parametrize("quantity", [1, -1])
def test_four_positions_against_independent_minimum_forms(kind, strike, premium, quantity):
    spot = np.array([0, 55, 63, 70, 98, 100, 102, 105, 115, 120, 1000])
    # Hull Fig10.5 expresses writer payoffs with min rather than -max.
    writer = np.minimum(strike - spot if kind == "call" else spot - strike, 0)
    expected_payoff = -quantity * writer
    row = option_cashflows(spot, strike, premium, kind=kind, quantity=quantity)
    assert np.allclose(row["payoff"], expected_payoff, atol=1e-12, rtol=1e-12)
    assert np.allclose(row["profit"], expected_payoff - quantity * premium, atol=1e-12, rtol=1e-12)


def test_figures_103_104_writer_printed_premiums_and_short_losses():
    call = option_cashflows([0, 100, 115, 120], 100, 5, quantity=-1)
    put = option_cashflows([0, 55, 70, 100], 70, 7, kind="put", quantity=-1)
    assert call["profit"] == pytest.approx([5, 5, -10, -15])
    assert put["profit"] == pytest.approx([-63, -8, 7, 7])
    assert np.max(call["profit"]) == pytest.approx(5)
    assert np.max(put["profit"]) == pytest.approx(7)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_buyer_and_writer_cashflows_cancel_with_broadcast_contract_counts(kind):
    spot = np.linspace(0, 180, 37)
    quantity = np.array([3, -3])[:, None]
    row = option_cashflows(spot, 100, 5, kind=kind, quantity=quantity, multiplier=100)
    for key in ("payoff", "premium_cashflow", "profit", "unexercised_profit"):
        assert np.allclose(np.sum(row[key], axis=0), 0, atol=1e-12, rtol=1e-12)


def test_closed_position_has_no_signed_cashflow():
    row = option_cashflows([90, 110], 100, 5, quantity=0)
    assert row["profit"] == pytest.approx([0, 0])
    assert row["payoff"] == pytest.approx([0, 0])
