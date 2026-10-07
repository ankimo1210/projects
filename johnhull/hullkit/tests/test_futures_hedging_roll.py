"""Hull Table3.5 stack and roll, with a separate transaction ledger."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h


def test_source_six_roll_values():
    a = h.stack_roll(
        [48.2, 47, 46.3],
        [47.4, 46.5, 45.9],
        units=100000,
        contract_size=1000,
        initial_spot=49,
        terminal_spot=46,
    )
    assert [
        a["contracts"],
        *a["per_unit_profit"],
        a["total_per_unit"],
        a["spot_decline"],
    ] == pytest.approx([100, 0.8, 0.5, 0.4, 1.7, 3])
    assert a["effective_sale_price"] == pytest.approx(47.7)


def test_independent_all_trade_cash_timeline():
    a = h.stack_roll(
        [48.2, 47, 46.3],
        [47.4, 46.5, 45.9],
        units=100000,
        contract_size=1000,
        initial_spot=49,
        terminal_spot=46,
    )
    ledger = np.array([4820000, -4740000, 4700000, -4650000, 4630000, -4590000, 4600000])
    assert a["net_cash"] == pytest.approx(np.sum(ledger))
    assert a["cash_profit"] == pytest.approx(np.add.reduce(ledger[:-1].reshape(3, 2), axis=1))
