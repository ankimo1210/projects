"""Mark the defined-contribution (DC) plan's fund to market like any other holding.

The snapshot carries the DC account as a balance on the day it was read, so it
never moved. Two sources fix that. The fund company publishes every day's price
(基準価額, per 10,000 units) as a CSV, and the plan's site shows the units held
and the contributions paid in on a given day (the anchor). The monthly
contributions listed in the plan's trade history move the anchor forward to
today and back through the window, the same way ``jpbroker.replay`` does for
the domestic account.

Units are carried in ten-thousands so that the price is the per-10,000-unit
figure the fund company and the plan's site both print. Cost is the
contributions paid in (拠出金累計), not the site's per-fund purchase amount, which
also folds in gains realised by earlier switches between funds.
"""

from __future__ import annotations

import copy
import csv
import io
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

ZERO, ONE = Decimal("0"), Decimal("1")
UNIT = Decimal("10000")
_DATE = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")


@dataclass(frozen=True)
class Trade:
    trade_date: str
    settle_date: str
    name: str
    units: Decimal
    price: Decimal  # per unit
    amount: Decimal
    kind: str


def decode(raw: bytes) -> str:
    """The fund company writes cp932; fall back to UTF-8 for a hand-made file."""
    for encoding in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("could not decode the file (tried cp932 and UTF-8)")


def _iso(text: str) -> str:
    y, m, d = text.strip().split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def _number(text: str) -> Decimal:
    return Decimal(text.strip().replace(",", "").replace("円", "").replace("口", ""))


def parse_nav(text: str) -> list[tuple[str, Decimal]]:
    """(date, price per 10,000 units) for every row of the fund company's CSV, oldest first."""
    out = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2 and _DATE.match(row[0].strip()):
            out.append((_iso(row[0]), _number(row[1])))
    return sorted(out)


def parse_trades(text: str) -> list[Trade]:
    """Rows of the plan's trade history as pasted from the site (tab-separated), oldest first.

    The pasted header wraps over several lines and repeats on every page, so a
    row is any line whose first field is a date.
    """
    trades = []
    for line in text.splitlines():
        fields = [f.strip() for f in line.split("\t")]
        if len(fields) < 7 or not _DATE.match(fields[0]):
            continue
        trades.append(
            Trade(
                trade_date=_iso(fields[0]),
                settle_date=_iso(fields[1]),
                name=fields[2],
                units=_number(fields[3]),
                price=_number(fields[4]),
                amount=_number(fields[5]),
                kind=fields[6],
            )
        )
    return sorted(trades, key=lambda t: (t.trade_date, t.settle_date))


def _signed(trade: Trade) -> tuple[Decimal, Decimal]:
    """(units, cost) the trade adds; a sale takes them away."""
    sign = -ONE if trade.kind.startswith("売") else ONE
    return sign * trade.units, sign * trade.amount


def _after_anchor(holding: dict[str, Any], trades: Sequence[Trade]) -> tuple[Decimal, Decimal]:
    anchor = holding["anchor"]
    units, cost = Decimal(str(anchor["units"])), Decimal(str(anchor["contributions_jpy"]))
    for t in trades:
        if t.trade_date > anchor["as_of"]:
            du, dc = _signed(t)
            units, cost = units + du, cost + dc
    return units, cost


def ledger(holding: dict[str, Any], trades: Sequence[Trade]) -> dict[str, Any]:
    """Today's holding in the shape ``mtm.mark_positions`` reads (quantity in 10,000 units)."""
    units, cost = _after_anchor(holding, trades)
    quantity = units / UNIT
    return {
        "account_id": holding["account_id"],
        "source": "DC plan balance (anchor) + trade history",
        "holdings": [
            {
                "symbol": holding["symbol"],
                "currency": "JPY",
                "quantity": quantity,
                "average_cost": cost / quantity if quantity else None,
                "average_trade_fx": ONE,
                "cost_basis_jpy": cost,
                "commission_jpy": ZERO,
            }
        ],
        "closed": [],
    }


def replay(
    holding: dict[str, Any], trades: Sequence[Trade], dates: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """Quantity and cost on each date, walked back from today, plus the trade markers.

    Before the oldest trade in the history there may be contributions the
    history does not list, so those dates are None rather than a wrong number.
    """
    units_now, cost_now = _after_anchor(holding, trades)
    first = trades[0].trade_date if trades else None
    path: dict[str, Any] = {"quantity": [], "cost_basis_jpy": [], "trades": []}
    for date in dates:
        if first is None or date < first:
            path["quantity"].append(None)
            path["cost_basis_jpy"].append(None)
            continue
        units, cost = units_now, cost_now
        for t in trades:
            if t.trade_date > date:
                du, dc = _signed(t)
                units, cost = units - du, cost - dc
        path["quantity"].append(units / UNIT)
        path["cost_basis_jpy"].append(cost)
    path["trades"] = [(t.trade_date, _signed(t)[0] / UNIT, t.price * UNIT) for t in trades]
    return {holding["symbol"]: path}


def apply_to_snapshot(
    snapshot: dict[str, Any], holding: dict[str, Any], dc_ledger: dict[str, Any]
) -> dict[str, Any]:
    """A copy of the snapshot whose DC position is priced by the fund's own series."""
    out = copy.deepcopy(snapshot)
    (h,) = dc_ledger["holdings"]
    for pos in out["positions"]:
        if pos["account_id"] == holding["account_id"] and pos["symbol"] == holding["symbol"]:
            pos["ticker"] = holding["ticker"]
            pos["quantity"] = h["quantity"]
    return out
