"""Hull Table2.1 margin accounting and independent cash-ledger identity."""

import numpy as np
import pytest
from hullkit import _futures_market as f

PRICES = [
    1741,
    1738.3,
    1744.6,
    1741.3,
    1740.1,
    1736.2,
    1729.9,
    1730.8,
    1725.4,
    1728.1,
    1711,
    1711,
    1714.3,
    1716.1,
    1723,
    1726.9,
]


def test_source_all_fifty_three_values():
    a = f.margin_account(1750, PRICES, units=200, initial=12000, maintenance=9000)
    assert a["daily_profit"] == pytest.approx(
        [
            -1800,
            -540,
            1260,
            -660,
            -240,
            -780,
            -1260,
            180,
            -1080,
            540,
            -3420,
            0,
            660,
            360,
            1380,
            780,
        ],
        abs=1e-7,
    )
    assert a["cumulative_profit"] == pytest.approx(
        [
            -1800,
            -2340,
            -1080,
            -1740,
            -1980,
            -2760,
            -4020,
            -3840,
            -4920,
            -4380,
            -7800,
            -7800,
            -7140,
            -6780,
            -5400,
            -4620,
        ],
        abs=1e-7,
    )
    assert a["balance"] == pytest.approx(
        [
            10200,
            9660,
            10920,
            10260,
            10020,
            9240,
            7980,
            12180,
            11100,
            11640,
            8220,
            12000,
            12660,
            13020,
            14400,
            15180,
        ],
        abs=1e-7,
    )
    assert a["calls"][[6, 10]] == pytest.approx([4020, 3780])
    assert f.margin_account(1750, [1759], units=200, initial=12000, maintenance=9000)["balance"][
        0
    ] == pytest.approx(13800)
    assert 9000 - a["balance"][6] == pytest.approx(1020)
    assert f.net_contracts(20, 15) == pytest.approx(5)


def test_independent_cumulative_cash_and_next_day_boundary():
    a = f.margin_account(1750, PRICES, units=200, initial=12000, maintenance=9000)
    deposits = np.zeros(16)
    deposits[[7, 11]] = [4020, 3780]
    direct = 12000 + 200 * (np.asarray(PRICES) - 1750) + np.tril(np.ones((16, 16))) @ deposits
    assert a["balance"] == pytest.approx(direct, abs=1e-7)
    assert a["deposits"] == pytest.approx(deposits)
    edge = f.margin_account(10, [9, 8.5, 8.5], units=1, initial=2, maintenance=1)
    assert edge["calls"] == pytest.approx([0, 1.5, 0])
    assert edge["balance"] == pytest.approx([1, 0.5, 2])
    pending = f.margin_account(10, [8.5], units=1, initial=2, maintenance=1)
    assert pending["pending_deposit"] == pytest.approx(1.5)
    with pytest.raises(ValueError):
        f.margin_account(10, [9], units=1, initial=1, maintenance=2)
