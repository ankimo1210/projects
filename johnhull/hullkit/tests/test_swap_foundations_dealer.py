"""Hull Table7.4 dealer quote and actual/360 payment."""

from datetime import date

import numpy as np
import pytest
from hullkit import _swap_foundations as s


def test_source_all_thirteen_quote_and_interest_values():
    bid = np.array([2.97, 3.05, 3.15, 3.26, 3.4, 3.48]) / 100
    ask = np.array([3, 3.08, 3.19, 3.3, 3.44, 3.52]) / 100
    a = s.dealer_swap_quotes(bid, ask)
    assert 100 * a["mid"] == pytest.approx([2.985, 3.065, 3.170, 3.280, 3.420, 3.500])
    assert a["spread_bp"] == pytest.approx([3, 3, 4, 4, 4, 4])
    assert s.dated_interest(1e8, 0.022, "2022-03-08", "2022-06-08") == pytest.approx(
        562222, abs=0.5
    )


def test_independent_days_and_bid_ask_cash_profit():
    days = (date(2022, 6, 8) - date(2022, 3, 8)).days
    assert s.dated_interest(1e8, 0.022, "2022-03-08", "2022-06-08") == pytest.approx(
        1e8 * 0.022 * days / 360
    )
    a = s.dealer_swap_quotes([0.0297], [0.03])
    # Dealer pays bid, receives ask; matched floating cash cancels.
    cash_received = 1e8 * 0.25 * 0.03
    cash_paid = 1e8 * 0.25 * 0.0297
    assert cash_received - cash_paid == pytest.approx(1e8 * 0.25 * a["spread_bp"][0] * 1e-4)
