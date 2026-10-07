"""Hull §25.7 total-return cashflows, independently replicated with financed ownership."""

import numpy as np
import pytest
from hullkit import _credit_contracts as c


@pytest.mark.parametrize("last,amount", [(1.1, 10_000_000), (0.85, -15_000_000)])
def test_source_100m_five_year_gain_loss_and_25bp_financing(last, amount):
    result = c.total_return_swap_cashflows(100_000_000, [1, last], [0], [0.05], [5], spread=0.0025)
    assert result["capital_change"][0] == pytest.approx(amount)
    assert result["financing"][0] == pytest.approx(100_000_000 * (0.05 + 0.0025) * 5)
    assert result["payer_cashflows"] == pytest.approx(-result["receiver_cashflows"])


def test_total_return_replicated_by_bond_purchase_and_borrowing_cash_account():
    notional = 1000
    marks = [1, 1.03, 0.98, 0.9]
    coupons = [12, 12, 24]
    floating = [0.02, 0.025, 0.03]
    dt = [0.25, 0.25, 0.5]
    result = c.total_return_swap_cashflows(notional, marks, coupons, floating, dt, spread=0.0025)
    # Finance initial purchase; at each mark distribute capital gain/loss,
    # retaining a fixed loan and bond basis. Closing sale cancels original principal.
    cash = []
    previous_value = notional
    for price, coupon, rate, year in zip(marks[1:], coupons, floating, dt, strict=True):
        value = notional * price
        cash.append(
            value - previous_value + coupon - notional * rate * year - notional * 0.0025 * year
        )
        previous_value = value
    assert result["receiver_cashflows"] == pytest.approx(cash)
    assert sum(cash) == pytest.approx(
        notional * marks[-1]
        - notional
        + sum(coupons)
        - sum(notional * (np.array(floating) + 0.0025) * dt)
    )
    with pytest.raises(ValueError):
        c.total_return_swap_cashflows(100, [1, 1], [0], [0.02], [0])
