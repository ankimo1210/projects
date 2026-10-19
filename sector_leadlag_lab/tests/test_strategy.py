import numpy as np
import pandas as pd
import pytest
from sector_leadlag.strategy import cash_long, long_short_returns, selection_spread

DAYS = pd.bdate_range("2026-01-05", periods=3)
SECTORS = list(range(1, 18))


def test_long_short_returns():
    weights = pd.DataFrame(0.0, index=DAYS, columns=SECTORS)
    weights.loc[DAYS[0], [1, 2]] = [0.5, -0.5]
    returns = pd.DataFrame(0.01, index=DAYS, columns=SECTORS)
    returns.loc[DAYS[0], 2] = -0.01
    out = long_short_returns(weights, returns)
    assert out.tolist() == pytest.approx([0.01, 0.0, 0.0])


def _signal(order: list[int]) -> pd.DataFrame:
    """A signal whose top five sectors are ``order``."""
    values = np.zeros(17)
    for rank, code in enumerate(order):
        values[code - 1] = 10.0 - rank
    return pd.DataFrame([values], index=DAYS[1:2], columns=SECTORS)


def test_cash_long_buys_whole_lots_of_the_top_sectors_and_pays_costs_both_ways():
    columns = ["a", "b", "c"]
    sector = pd.Series([1, 1, 3], index=columns)
    picks = pd.DataFrame(True, index=DAYS, columns=columns)
    traded = pd.DataFrame(True, index=DAYS, columns=columns)
    traded.loc[DAYS[1], "b"] = False
    quoted_close = pd.DataFrame(
        [[1000.0, 3000.0, 500.0], [1010.0, 3000.0, 505.0], [1000.0, 3000.0, 500.0]],
        index=DAYS,
        columns=columns,
    )
    quoted_open = quoted_close.copy()
    quoted_open.loc[DAYS[1]] = [1000.0, 3000.0, 500.0]
    signal = _signal([1, 2, 4, 5, 6])  # sector 3 (name c) is not among the top five
    out = cash_long(
        signal, picks, quoted_open, quoted_close, traded, sector, capital=1_500_000.0, cost_bp=10.0
    )
    # budget 100,000 yen per name: a buys 100 shares at 1,000 (previous close 1,000)
    pnl = 100 * (1010 - 1000) - 0.001 * 100 * (1000 + 1010)
    assert out.returns.iloc[0] == pytest.approx(pnl / 1_500_000)
    assert out.names.iloc[0] == 1  # b did not trade, c's sector was not chosen
    assert out.invested.iloc[0] == pytest.approx(100 * 1000 / 1_500_000)


def test_cash_long_skips_a_name_whose_lot_does_not_fit():
    columns = ["a"]
    sector = pd.Series([1], index=columns)
    picks = pd.DataFrame(True, index=DAYS, columns=columns)
    traded = pd.DataFrame(True, index=DAYS, columns=columns)
    price = pd.DataFrame(5000.0, index=DAYS, columns=columns)
    out = cash_long(
        _signal([1, 2, 3, 4, 5]), picks, price, price, traded, sector, capital=1_500_000.0
    )
    assert out.names.iloc[0] == 0 and out.returns.iloc[0] == 0.0


def test_selection_spread_is_the_top_five_minus_all():
    returns = pd.DataFrame([np.arange(17) / 100.0], index=DAYS[1:2], columns=SECTORS)
    spread = selection_spread(_signal([17, 16, 15, 14, 13]), returns)
    assert spread.iloc[0] == pytest.approx(np.mean([0.16, 0.15, 0.14, 0.13, 0.12]) - 0.08)
