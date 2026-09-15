"""Offline tests for the P&L time-series reconstruction (no network)."""

from __future__ import annotations

from decimal import Decimal

from portfolio_analyzer import timeseries as ts
from portfolio_analyzer.ibkr import Transaction

D = Decimal


def tx(date, kind, symbol=None, qty=None, price=None, cur=None, gross=None, comm=None, net=None):
    return Transaction(
        date=date,
        description=kind,
        transaction_type=kind,
        symbol=symbol,
        quantity=None if qty is None else D(str(qty)),
        price=None if price is None else D(str(price)),
        price_currency=cur,
        gross_amount=None if gross is None else D(str(gross)),
        commission=None if comm is None else D(str(comm)),
        net_amount=None if net is None else D(str(net)),
    )


def transactions() -> list[Transaction]:
    return [
        tx("2026-02-20", "Dividend", symbol="XLE", net=1000),
        tx("2026-02-10", "Sell", "XLE", -4, 60, "USD", gross=36000, comm=-50, net=35950),
        tx("2026-01-10", "Buy", "XLE", 10, 50, "USD", gross=-75000, comm=-100, net=-75100),
        tx("2026-01-05", "Deposit", net=1000000),
    ]


DATES = ["2026-01-05", "2026-01-10", "2026-02-10", "2026-02-20"]


def test_replay_tracks_cash_quantity_cost_and_realized() -> None:
    paths = ts.replay(transactions(), DATES)
    assert paths.cash == [D(1000000), D(924900), D(960850), D(961850)]
    assert paths.deposits_cum == [D(1000000)] * 4
    xle = paths.positions["XLE"]
    assert xle.currency == "USD"
    assert xle.quantity == [D(0), D(10), D(6), D(6)]
    assert xle.cost_basis_jpy == [D(0), D(75100), D(45060), D(45060)]
    assert xle.realized_cum == [D(0), D(0), D(5910), D(5910)]
    assert paths.dividends_cum == [D(0), D(0), D(0), D(1000)]
    assert paths.first_trade["XLE"] == "2026-01-10"
    assert paths.trades["XLE"] == [("2026-01-10", D(10), D(50)), ("2026-02-10", D(-4), D(60))]


def test_nav_and_pnl_paths_add_up() -> None:
    paths = ts.replay(transactions(), DATES)
    prices = {"XLE": [D(50), D(50), D(60), D(62)]}
    fx = [D(150), D(150), D(150), D(155)]
    out = ts.value_paths(paths, prices, fx)
    assert out.nav == [D(1000000), D(999900), D(1014850), D(1019510)]
    assert out.pnl_total == [D(0), D(-100), D(14850), D(19510)]
    assert out.unrealized["XLE"] == [D(0), D(-100), D(8940), D(12600)]
    assert out.positions_value == [D(0), D(75000), D(54000), D(57660)]
    last = 3
    buckets = out.unrealized["XLE"][last] + paths.realized_cum[last] + paths.dividends_cum[last]
    assert buckets == out.pnl_total[last]


def test_window_return_uses_available_history() -> None:
    values = [D(100), D(101), D(102), D(103), D(104), D(105), D(106)]
    assert ts.window_return(values, 1) == D(106) / D(105) - 1
    assert ts.window_return(values, 5) == D(106) / D(101) - 1
    assert ts.window_return(values, 50) == D(106) / D(100) - 1
    assert ts.window_return([D(100)], 1) is None


def test_window_slices_by_calendar_days() -> None:
    dates = ["2025-09-10", "2025-09-11", "2026-09-10", "2026-09-11"]
    assert ts.window_start_index(dates, "2026-09-11", days=365) == 1
    assert ts.window_start_index(dates, "2026-09-11", days=3650) == 0


def _series(account_id, nav, deposits, unrealized=None, flows=None):
    zeros = [None if v is None else D(0) for v in nav]
    return ts.AccountSeries(
        account_id=account_id,
        nav=nav,
        deposits_cum=deposits,
        unrealized=unrealized
        if unrealized is not None
        else [
            None if v is None or d is None else v - d for v, d in zip(nav, deposits, strict=True)
        ],
        realized_cum=list(zeros),
        dividends_cum=list(zeros),
        fees_cum=list(zeros),
        fx_translation_cum=list(zeros),
        forex_cum=list(zeros),
        xirr_flows=flows,
    )


def test_account_series_pnl_is_nav_minus_deposits_and_none_where_undefined() -> None:
    s = _series("a", [None, D(110), D(120)], [None, D(100), D(100)])
    assert s.pnl == [None, D(10), D(20)]


def test_combine_sums_accounts_and_propagates_none() -> None:
    a = _series("a", [D(100), D(110), D(120)], [D(100), D(100), D(100)])
    b = _series("b", [None, D(50), D(55)], [None, D(40), D(40)])
    total = ts.combine([a, b])
    assert total.account_id == "total"
    assert total.nav == [None, D(160), D(175)]
    assert total.deposits_cum == [None, D(140), D(140)]
    assert total.pnl == [None, D(20), D(35)]
    assert total.unrealized == [None, D(20), D(35)]
    assert total.xirr_flows is None


def test_from_ledger_reads_the_replayed_ibkr_paths() -> None:
    paths = ts.replay(transactions(), DATES)
    prices = {"XLE": [D(50), D(50), D(60), D(60)]}
    fx = [D(150)] * 4
    values = ts.value_paths(paths, prices, fx)
    s = ts.from_ledger("global_broker", paths, values, [("2026-01-05", D(1000000))])
    assert s.nav == values.nav and s.deposits_cum == paths.deposits_cum
    assert s.pnl == values.pnl_total
    assert s.realized_cum == paths.realized_cum and s.dividends_cum == paths.dividends_cum
    assert s.xirr_flows == [("2026-01-05", D(1000000))]
    # the buckets add up to NAV − deposits on every date
    for i in range(len(DATES)):
        parts = sum((getattr(s, b)[i] for b in ts.BUCKETS), D(0))
        assert parts == s.pnl[i]


def test_first_defined_and_daily_changes() -> None:
    values = [None, None, D(5), D(7), D(6)]
    assert ts.first_defined(values) == 2
    assert ts.first_defined([None, None]) is None
    assert ts.daily_changes(values) == [None, None, None, D(2), D(-1)]
