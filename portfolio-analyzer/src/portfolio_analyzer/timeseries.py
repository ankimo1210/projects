"""Reconstruct the account's daily NAV and P&L paths from the transaction history.

The ledger replay (``ibkr.derive_holdings``) is exact at one point in time; running it
once per calendar date gives the quantity, cost basis and realised P&L of every symbol
on every date, and summing the cash rows gives the cash balance. Marking the quantities
with daily closes and USD/JPY then yields NAV, and NAV minus cumulative deposits is the
account's all-in P&L, which the buckets (unrealised, realised, dividends, fees, FX
translation) add up to by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from portfolio_analyzer.ibkr import TRADE_TYPES, Transaction, derive_holdings

ZERO = Decimal(0)


@dataclass
class PositionPath:
    symbol: str
    currency: str
    quantity: list[Decimal]
    cost_basis_jpy: list[Decimal]
    realized_cum: list[Decimal]


@dataclass
class Paths:
    dates: list[str]
    cash: list[Decimal]
    deposits_cum: list[Decimal]
    dividends_cum: list[Decimal]
    fees_cum: list[Decimal]
    fx_translation_cum: list[Decimal]
    forex_cum: list[Decimal]
    realized_cum: list[Decimal]
    positions: dict[str, PositionPath]
    first_trade: dict[str, str] = field(default_factory=dict)
    last_trade: dict[str, str] = field(default_factory=dict)
    trades: dict[str, list[tuple[str, Decimal, Decimal]]] = field(default_factory=dict)


def _net(row: Transaction) -> Decimal:
    return row.net_amount or ZERO


def replay(transactions: list[Transaction], dates: list[str]) -> Paths:
    """State of the account at the close of every date in ``dates`` (ISO, ascending)."""
    rows = sorted(transactions, key=lambda r: r.date)
    symbols = sorted({r.symbol for r in rows if r.transaction_type in TRADE_TYPES and r.symbol})
    currency = {
        r.symbol: (r.price_currency or "JPY")
        for r in rows
        if r.transaction_type in TRADE_TYPES and r.symbol in symbols
    }
    positions = {s: PositionPath(s, currency[s], [], [], []) for s in symbols}
    cash, deposits, dividends, fees, fxadj, forex, realized = ([] for _ in range(7))
    for day in dates:
        upto = [r for r in rows if r.date <= day]
        holdings = derive_holdings(upto)
        for s in symbols:
            h = holdings.get(s)
            positions[s].quantity.append(h.quantity if h else ZERO)
            positions[s].cost_basis_jpy.append(h.cost_basis_jpy if h else ZERO)
            positions[s].realized_cum.append(h.realized_pnl_jpy if h else ZERO)
        cash.append(sum((_net(r) for r in upto), ZERO))
        deposits.append(sum((_net(r) for r in upto if r.transaction_type == "Deposit"), ZERO))
        dividends.append(
            sum(
                (
                    _net(r)
                    for r in upto
                    if r.transaction_type in ("Dividend", "Foreign Tax Withholding")
                ),
                ZERO,
            )
        )
        fees.append(sum((_net(r) for r in upto if r.transaction_type == "Other Fee"), ZERO))
        fxadj.append(sum((_net(r) for r in upto if r.transaction_type == "Adjustment"), ZERO))
        forex.append(
            sum((_net(r) for r in upto if r.transaction_type == "Forex Trade Component"), ZERO)
        )
        realized.append(sum((h.realized_pnl_jpy for h in holdings.values()), ZERO))
    trades: dict[str, list[tuple[str, Decimal, Decimal]]] = {s: [] for s in symbols}
    for r in rows:
        if r.transaction_type in TRADE_TYPES and r.symbol and r.quantity is not None:
            trades[r.symbol].append((r.date, r.quantity, r.price or ZERO))
    return Paths(
        dates=list(dates),
        cash=cash,
        deposits_cum=deposits,
        dividends_cum=dividends,
        fees_cum=fees,
        fx_translation_cum=fxadj,
        forex_cum=forex,
        realized_cum=realized,
        positions=positions,
        first_trade={s: t[0][0] for s, t in trades.items() if t},
        last_trade={s: t[-1][0] for s, t in trades.items() if t},
        trades=trades,
    )


@dataclass
class ValuePaths:
    nav: list[Decimal]
    positions_value: list[Decimal]
    pnl_total: list[Decimal]
    unrealized: dict[str, list[Decimal]]
    value: dict[str, list[Decimal]]


def value_paths(paths: Paths, prices: dict[str, list[Decimal]], fx: list[Decimal]) -> ValuePaths:
    """Mark the replayed quantities with closes (per symbol, aligned to ``paths.dates``)."""
    n = len(paths.dates)
    unrealized: dict[str, list[Decimal]] = {}
    value: dict[str, list[Decimal]] = {}
    positions_value = [ZERO] * n
    for s, pos in paths.positions.items():
        series = prices.get(s)
        if series is None:
            continue
        vals, unr = [], []
        for i in range(n):
            rate = fx[i] if pos.currency == "USD" else Decimal(1)
            v = pos.quantity[i] * series[i] * rate
            vals.append(v)
            unr.append(v - pos.cost_basis_jpy[i])
            positions_value[i] += v
        value[s] = vals
        unrealized[s] = unr
    nav = [paths.cash[i] + positions_value[i] for i in range(n)]
    pnl_total = [nav[i] - paths.deposits_cum[i] for i in range(n)]
    return ValuePaths(nav, positions_value, pnl_total, unrealized, value)


def window_return(values: list[Decimal], lookback: int) -> Decimal | None:
    """Return over the last ``lookback`` observations (clipped to the available history)."""
    if len(values) < 2:
        return None
    base = values[max(0, len(values) - 1 - lookback)]
    return values[-1] / base - 1 if base else None


def window_start_index(dates: list[str], as_of: str, days: int) -> int:
    """Index of the first date on or after ``as_of`` minus ``days`` calendar days."""
    floor = (date.fromisoformat(as_of) - timedelta(days=days)).isoformat()
    for i, d in enumerate(dates):
        if d >= floor:
            return i
    return len(dates) - 1


def max_drawdown(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    peak = values[0]
    worst = ZERO
    for v in values:
        peak = max(peak, v)
        if peak:
            worst = min(worst, v / peak - 1)
    return worst
