"""Daily mark-to-market P&L summary.

Positions come from the snapshot (what is held), closes and FX from the market,
cost basis from the IBKR ledger where it exists. Everything here is offline and
pure; ``scripts/daily_pl_report.py`` fetches the quotes and writes the files.

Day P&L is the yen change between the last two closes the market has for each
instrument (price and FX both move), so it is a mark-to-market number, not a
calendar-day number: on a Monday it spans the weekend, and a JP close and a US
close of the same report can carry different dates.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from portfolio_analyzer.ibkr import Holding, decompose_pnl

NON_MARKET_SYMBOLS = {"CASH_JPY", "RECONCILIATION"}
FX_SYMBOL = "JPY=X"
ZERO = Decimal(0)
ONE = Decimal(1)


@dataclass(frozen=True)
class Quote:
    """Last close and the close before it, with their dates."""

    close: Decimal
    prev_close: Decimal | None
    date: str
    prev_date: str | None


def market_symbol(symbol: str, currency: str) -> str | None:
    """Return the yfinance ticker for a holding, or None if it has no quote."""
    if symbol in NON_MARKET_SYMBOLS:
        return None
    if currency == "JPY" and symbol.isdigit():
        return f"{symbol}.T"
    if currency == "USD":
        return symbol
    return None


def _dec(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


@dataclass
class Row:
    """One position, marked to market."""

    account_id: str
    symbol: str
    name: str
    asset_class: str
    currency: str
    quantity: Decimal | None
    quoted: bool
    ticker: str | None
    price: Decimal | None
    prev_price: Decimal | None
    price_date: str | None
    prev_price_date: str | None
    fx: Decimal
    prev_fx: Decimal | None
    market_value_jpy: Decimal
    prev_value_jpy: Decimal | None
    day_pnl_jpy: Decimal | None
    day_price_pnl_jpy: Decimal | None
    day_change_pct: Decimal | None
    cost_basis_jpy: Decimal | None
    average_cost: Decimal | None
    unrealized_jpy: Decimal | None
    unrealized_pct: Decimal | None
    price_pnl_jpy: Decimal | None
    fx_pnl_jpy: Decimal | None
    cross_pnl_jpy: Decimal | None
    commission_jpy: Decimal | None
    note: str


def _cost_index(
    ledger: dict[str, Any] | Sequence[dict[str, Any]] | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Cost by (account, symbol). Takes one ledger or several — one per account."""
    if not ledger:
        return {}
    ledgers = [ledger] if isinstance(ledger, dict) else list(ledger)
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for one in ledgers:
        account = str(one.get("account_id", ""))
        for holding in one.get("holdings", []):
            index[(account, str(holding["symbol"]))] = holding
    return index


def mark_positions(
    snapshot: dict[str, Any],
    quotes: dict[str, Quote],
    fx: Quote,
    ledger: dict[str, Any] | Sequence[dict[str, Any]] | None,
) -> list[Row]:
    """Mark every snapshot position; positions without a quote are carried at snapshot value."""
    cost = _cost_index(ledger)
    rows: list[Row] = []
    for pos in snapshot["positions"]:
        account_id = str(pos["account_id"])
        symbol = str(pos["symbol"])
        currency = str(pos["currency"])
        quantity = _dec(pos.get("quantity"))
        ticker = market_symbol(symbol, currency)
        quote = quotes.get(ticker) if ticker else None
        row = Row(
            account_id=account_id,
            symbol=symbol,
            name=str(pos.get("name", symbol)),
            asset_class=str(pos.get("asset_class", "")),
            currency=currency,
            quantity=quantity,
            quoted=False,
            ticker=ticker,
            price=_dec(pos.get("price")),
            prev_price=None,
            price_date=None,
            prev_price_date=None,
            fx=_dec(pos.get("fx_rate")) or ONE,
            prev_fx=None,
            market_value_jpy=_dec(pos["market_value_jpy"]) or ZERO,
            prev_value_jpy=None,
            day_pnl_jpy=None,
            day_price_pnl_jpy=None,
            day_change_pct=None,
            cost_basis_jpy=None,
            average_cost=None,
            unrealized_jpy=None,
            unrealized_pct=None,
            price_pnl_jpy=None,
            fx_pnl_jpy=None,
            cross_pnl_jpy=None,
            commission_jpy=None,
            note="時価が取れないためスナップショットの値を据え置き",
        )
        if quote is not None and quantity is not None:
            rate, prev_rate = (fx.close, fx.prev_close) if currency == "USD" else (ONE, ONE)
            row.quoted = True
            row.price, row.prev_price = quote.close, quote.prev_close
            row.price_date, row.prev_price_date = quote.date, quote.prev_date
            row.fx, row.prev_fx = rate, prev_rate
            row.market_value_jpy = quantity * quote.close * rate
            row.note = ""
            if quote.prev_close is not None and prev_rate is not None:
                row.prev_value_jpy = quantity * quote.prev_close * prev_rate
                row.day_pnl_jpy = row.market_value_jpy - row.prev_value_jpy
                row.day_price_pnl_jpy = quantity * (quote.close - quote.prev_close) * rate
                row.day_change_pct = quote.close / quote.prev_close - ONE
            _attach_cost(row, cost.get((account_id, symbol)))
        rows.append(row)
    return rows


def _attach_cost(row: Row, holding: dict[str, Any] | None) -> None:
    """Fill the unrealised P&L columns from a ledger holding (average cost, trade-date FX)."""
    if holding is None or row.quantity is None or row.price is None:
        return
    average_cost = _dec(holding.get("average_cost"))
    trade_fx = _dec(holding.get("average_trade_fx")) or ONE
    ledger_qty = _dec(holding.get("quantity"))
    if average_cost is None or ledger_qty in (None, ZERO):
        return
    scale = row.quantity / ledger_qty
    cost_basis_jpy = (_dec(holding.get("cost_basis_jpy")) or ZERO) * scale
    commission_jpy = (_dec(holding.get("commission_jpy")) or ZERO) * scale
    cost_native = row.quantity * average_cost
    holding_state = Holding(
        symbol=row.symbol,
        currency=row.currency,
        quantity=row.quantity,
        cost_basis_jpy=cost_basis_jpy,
        cost_basis_gross_jpy=cost_basis_jpy + commission_jpy,
        cost_basis_native=cost_native,
        average_trade_fx=trade_fx,
        realized_pnl_jpy=ZERO,
    )
    split = decompose_pnl(holding_state, row.price, row.fx)
    if split is None:
        return
    row.cost_basis_jpy = cost_basis_jpy
    row.average_cost = average_cost
    row.unrealized_jpy = split.total_jpy
    row.unrealized_pct = split.total_jpy / cost_basis_jpy if cost_basis_jpy else None
    row.price_pnl_jpy = split.price_jpy
    row.fx_pnl_jpy = split.fx_jpy
    row.cross_pnl_jpy = split.cross_jpy
    row.commission_jpy = split.commission_jpy
    if scale != ONE:
        row.note = f"台帳の数量 {ledger_qty} と異なるため平均取得単価を数量に掛けて按分"


@dataclass
class AccountSummary:
    id: str
    name: str
    snapshot_as_of: str
    total_jpy: Decimal
    quoted_value_jpy: Decimal
    day_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    cost_known_value_jpy: Decimal
    snapshot_unrealized_jpy: Decimal | None


@dataclass
class Summary:
    accounts: dict[str, AccountSummary]
    total_jpy: Decimal
    quoted_value_jpy: Decimal
    day_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    cost_known_value_jpy: Decimal


def _sum_optional(values: list[Decimal | None]) -> Decimal | None:
    present = [v for v in values if v is not None]
    return sum(present, ZERO) if present else None


def summarize(snapshot: dict[str, Any], rows: list[Row]) -> Summary:
    accounts: dict[str, AccountSummary] = {}
    for acc in snapshot["accounts"]:
        acc_id = str(acc["id"])
        mine = [r for r in rows if r.account_id == acc_id]
        accounts[acc_id] = AccountSummary(
            id=acc_id,
            name=str(acc.get("name", acc_id)),
            snapshot_as_of=str(acc.get("as_of", "")),
            total_jpy=sum((r.market_value_jpy for r in mine), ZERO),
            quoted_value_jpy=sum((r.market_value_jpy for r in mine if r.quoted), ZERO),
            day_pnl_jpy=_sum_optional([r.day_pnl_jpy for r in mine]),
            unrealized_known_jpy=_sum_optional([r.unrealized_jpy for r in mine]),
            cost_known_value_jpy=sum(
                (r.market_value_jpy for r in mine if r.unrealized_jpy is not None), ZERO
            ),
            snapshot_unrealized_jpy=_dec(acc.get("unrealized_pnl_jpy")),
        )
    return Summary(
        accounts=accounts,
        total_jpy=sum((a.total_jpy for a in accounts.values()), ZERO),
        quoted_value_jpy=sum((a.quoted_value_jpy for a in accounts.values()), ZERO),
        day_pnl_jpy=_sum_optional([a.day_pnl_jpy for a in accounts.values()]),
        unrealized_known_jpy=_sum_optional([a.unrealized_known_jpy for a in accounts.values()]),
        cost_known_value_jpy=sum((a.cost_known_value_jpy for a in accounts.values()), ZERO),
    )


# ---------------------------------------------------------------- history ---


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def history_record(summary: Summary, rows: list[Row], meta: dict[str, Any]) -> dict[str, Any]:
    """One JSON-serialisable line for the history file."""
    fx: Quote = meta["fx"]
    return {
        "as_of": meta["as_of"],
        "generated_at": meta["generated_at"],
        "fx_usdjpy": _f(fx.close),
        "total_jpy": _f(summary.total_jpy),
        "quoted_value_jpy": _f(summary.quoted_value_jpy),
        "day_pnl_jpy": _f(summary.day_pnl_jpy),
        "unrealized_known_jpy": _f(summary.unrealized_known_jpy),
        "accounts": {
            k: {"total_jpy": _f(a.total_jpy), "day_pnl_jpy": _f(a.day_pnl_jpy)}
            for k, a in summary.accounts.items()
        },
        "positions": {
            f"{r.account_id}:{r.symbol}": {
                "price": _f(r.price),
                "price_date": r.price_date,
                "value_jpy": _f(r.market_value_jpy),
                "day_pnl_jpy": _f(r.day_pnl_jpy),
                "unrealized_jpy": _f(r.unrealized_jpy),
            }
            for r in rows
            if r.quoted
        },
    }


def upsert_history(path: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    """Append ``record`` to the JSONL history, replacing any line with the same ``as_of``."""
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    records = [r for r in records if r.get("as_of") != record["as_of"]]
    records.append(record)
    records.sort(key=lambda r: str(r.get("as_of", "")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    return records


def previous_record(records: list[dict[str, Any]], as_of: str) -> dict[str, Any] | None:
    earlier = [r for r in records if str(r.get("as_of", "")) < as_of]
    return earlier[-1] if earlier else None
