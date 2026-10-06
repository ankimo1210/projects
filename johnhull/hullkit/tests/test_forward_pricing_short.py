"""Hull Table5.1 short-sale cashflows."""

import numpy as np
import pytest
from hullkit import _forward_pricing as f


def test_source_four_short_sale_values():
    a = f.stock_trade_cash(500, 120, 100, 1, side="short")
    assert [a["entry_cash"], -a["income_cash"], -a["exit_cash"], a["profit"]] == pytest.approx(
        [60000, 500, 50000, 9500]
    )


def test_independent_trade_cash_columns_and_long_symmetry():
    ledger = np.dot([500, 500, 500, 1], [120, -100, -1, -75])
    a = f.stock_trade_cash(500, 120, 100, 1, side="short", borrow_fee=75)
    assert a["profit"] == pytest.approx(ledger)
    long = f.stock_trade_cash(500, 120, 100, 1)
    short = f.stock_trade_cash(500, 120, 100, 1, side="short")
    assert long["profit"] == pytest.approx(-short["profit"])
