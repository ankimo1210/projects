"""Read the Japanese broker's trade-history CSV into a cost-basis ledger.

The domestic account has no cost in the snapshot, so every position there shows
"原価なし". This module replays the broker's own export — the same idea as
``ibkr`` for the foreign account — and produces holdings in the shape
``mtm.mark_positions`` already understands.

Two things are specific to this export. The settled amount (受渡金額) is what
actually left the account, so it carries the fees; the execution price
(約定単価) times the quantity is the price-only cost, and the difference is the
commission. A share split arrives as a 保振増減資 row that adds quantity with no
money attached, so the average cost has to be divided down rather than kept.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from portfolio_analyzer.timeseries import AccountSeries

ZERO, ONE = Decimal("0"), Decimal("1")
BUY, SELL, SPLIT = "買", "売", "保振増減資"
DIVIDEND_KINDS = ("入金(配当)", "入金(分配)")
TRADE_KINDS = ("株式", "上場投信")


@dataclass(frozen=True)
class Txn:
    kind: str
    trade_date: str
    settle_date: str
    symbol: str | None
    name: str
    action: str
    price: Decimal | None
    quantity: Decimal | None
    amount: Decimal | None
    note: str


def decode(raw: bytes) -> str:
    """The broker exports cp932; fall back to UTF-8 for a hand-made file."""
    for encoding in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("could not decode the trade history (tried cp932 and UTF-8)")


def _date(text: str) -> str:
    text = text.strip()
    return "" if text.startswith("-") else text.replace("/", "-")


def _number(text: str) -> Decimal | None:
    cleaned = text.strip().replace("円", "").replace(",", "")
    if not cleaned or cleaned == "-":
        return None
    return Decimal(cleaned)


def _split_symbol(field: str) -> tuple[str | None, str]:
    """ "8976 大和証券オフィス投資法人" -> ("8976", "大和証券オフィス投資法人")."""
    head, _, rest = field.strip().partition(" ")
    if head.isdigit() and len(head) == 4:
        return head, rest.strip()
    return None, field.strip()


def parse_transactions(text: str) -> list[Txn]:
    """Every row of the export, oldest last (the broker writes newest first)."""
    rows: list[Txn] = []
    for row in csv.DictReader(io.StringIO(text)):
        symbol, name = _split_symbol(row.get("銘柄", ""))
        rows.append(
            Txn(
                kind=row.get("商品分類", "").strip(),
                trade_date=_date(row.get("約定日", "")),
                settle_date=_date(row.get("受渡日", "")),
                symbol=symbol,
                name=name,
                action=row.get("取引", "").strip(),
                price=_number(row.get("約定単価", "")),
                quantity=_number(row.get("数量", "")),
                amount=_number(row.get("受渡金額", "")),
                note=row.get("備考", "").strip(),
            )
        )
    return rows


def _ordered(rows: list[Txn]) -> list[Txn]:
    return sorted(rows, key=lambda r: (r.settle_date or r.trade_date, r.trade_date))


def _replay(rows: list[Txn]) -> dict[str, dict[str, Any]]:
    """Average-cost replay over the whole export."""
    state: dict[str, dict[str, Any]] = {}
    for txn in _ordered(rows):
        if txn.symbol is None:
            continue
        book = state.setdefault(
            txn.symbol,
            {
                "symbol": txn.symbol,
                "name": txn.name,
                "quantity": ZERO,
                "cost_basis_jpy": ZERO,
                "cost_native_jpy": ZERO,
                "realized_pnl_jpy": ZERO,
                "dividends_jpy": ZERO,
                "first_trade": "",
                "last_trade": "",
                "trades": 0,
                "tax_categories": set(),
                "sales": [],
            },
        )
        if txn.name:
            book["name"] = txn.name
        if txn.kind in DIVIDEND_KINDS and txn.amount is not None:
            book["dividends_jpy"] += txn.amount
            continue
        if txn.action == SPLIT and txn.quantity is not None:
            book["quantity"] += txn.quantity
            continue
        if txn.kind not in TRADE_KINDS or txn.quantity is None or txn.amount is None:
            continue
        book["trades"] += 1
        book["first_trade"] = book["first_trade"] or txn.trade_date
        book["last_trade"] = txn.trade_date
        native = (txn.price or ZERO) * txn.quantity
        if txn.action == BUY:
            book["quantity"] += txn.quantity
            book["cost_basis_jpy"] += -txn.amount
            book["cost_native_jpy"] += native
            book["tax_categories"].add("nisa" if "NISA" in txn.note else "taxable")
        elif txn.action == SELL:
            held = book["quantity"]
            if held <= ZERO:
                continue
            share = min(txn.quantity / held, ONE)
            removed = book["cost_basis_jpy"] * share
            book["realized_pnl_jpy"] += txn.amount - removed
            book["sales"].append((txn.trade_date, txn.amount - removed, txn.note))
            book["cost_basis_jpy"] -= removed
            book["cost_native_jpy"] -= book["cost_native_jpy"] * share
            book["quantity"] -= txn.quantity
            if book["quantity"] <= ZERO:
                book["tax_categories"] = set()  # a later rebuy starts a new holding
    return state


def derive_holdings(rows: list[Txn]) -> dict[str, dict[str, Any]]:
    """Open positions with the average cost the marker needs."""
    out: dict[str, dict[str, Any]] = {}
    for symbol, book in _replay(rows).items():
        quantity = book["quantity"]
        if quantity <= ZERO:
            continue
        native = book["cost_native_jpy"]
        out[symbol] = {
            "symbol": symbol,
            "name": book["name"],
            "currency": "JPY",
            "quantity": quantity,
            "average_cost": native / quantity,
            "average_trade_fx": ONE,
            "cost_basis_jpy": book["cost_basis_jpy"],
            # negative: the fee is a drag, and gross = all-in + commission
            "commission_jpy": native - book["cost_basis_jpy"],
            "realized_pnl_jpy": book["realized_pnl_jpy"],
            "dividends_jpy": book["dividends_jpy"],
            "first_trade": book["first_trade"],
            "last_trade": book["last_trade"],
            "trades": book["trades"],
            # "nisa" / "taxable", or "mixed" when the lots still held came through both
            "tax_category": (
                "mixed"
                if len(book["tax_categories"]) > 1
                else next(iter(book["tax_categories"]), "taxable")
            ),
        }
    return out


def taxable_realized_since(rows: list[Txn], since: str) -> Decimal:
    """Realised P&L of sales outside NISA on or after ``since`` (ISO date) — what tax nets."""
    return sum(
        (
            realized
            for book in _replay(rows).values()
            for date, realized, note in book["sales"]
            if date >= since and "NISA" not in note
        ),
        ZERO,
    )


def closed_positions(rows: list[Txn]) -> dict[str, dict[str, Any]]:
    """Symbols the account no longer holds, with what they realised."""
    return {
        symbol: {
            "symbol": symbol,
            "name": book["name"],
            "realized_pnl_jpy": book["realized_pnl_jpy"],
            "dividends_jpy": book["dividends_jpy"],
            "first_trade": book["first_trade"],
            "last_trade": book["last_trade"],
            "trades": book["trades"],
        }
        for symbol, book in _replay(rows).items()
        if book["quantity"] <= ZERO and book["trades"]
    }


def dividends(rows: list[Txn]) -> dict[str, Decimal]:
    """Cash received per symbol (dividends and fund distributions)."""
    out: dict[str, Decimal] = {}
    for txn in rows:
        if txn.kind in DIVIDEND_KINDS and txn.symbol and txn.amount is not None:
            out[txn.symbol] = out.get(txn.symbol, ZERO) + txn.amount
    return out


def deposits(rows: list[Txn]) -> Decimal:
    """Cash paid into the account."""
    return sum(
        (t.amount for t in rows if t.kind.startswith("入金(振込)") and t.amount is not None), ZERO
    )


def ledger(rows: list[Txn], account_id: str) -> dict[str, Any]:
    """The same shape as the IBKR ledger, so the marker can read either."""
    return {
        "account_id": account_id,
        "source": "broker trade history (CSV)",
        "holdings": list(derive_holdings(rows).values()),
        "closed": list(closed_positions(rows).values()),
        "deposits_jpy": deposits(rows),
    }


def _event_date(txn: Txn) -> str:
    """A trade moves the position on its execution date; a split only has a settlement date."""
    return txn.trade_date or txn.settle_date


def replay(rows: list[Txn], dates: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Quantity and cost basis on each date, plus the trades, for every symbol seen.

    The domestic account's P&L cards need the same treatment as the foreign one:
    what was held, and at what cost, on each day of the window.

    Quantities come out in today's shares. The prices these paths are multiplied
    by are split-adjusted (Yahoo adjusts its close even with ``auto_adjust``
    off), so a holding from before a split has to be restated in the shares it
    became — otherwise the pre-split part of the line shows a loss the size of
    the split. The trade markers move with it: the quantity up, the price down.
    """
    ordered = sorted(
        (t for t in rows if t.symbol), key=lambda t: (_event_date(t), t.settle_date or "")
    )
    symbols = {t.symbol for t in ordered if t.symbol}
    paths: dict[str, dict[str, Any]] = {
        s: {"quantity": [], "cost_basis_jpy": [], "realized_cum": [], "trades": []} for s in symbols
    }
    book = {s: {"quantity": ZERO, "cost_basis_jpy": ZERO, "realized": ZERO} for s in symbols}
    splits: dict[str, list[tuple[str, Decimal]]] = {s: [] for s in symbols}

    def apply(txn: Txn, *, record: bool) -> None:
        state = book[txn.symbol]
        if txn.action == SPLIT and txn.quantity is not None:
            before = state["quantity"]
            state["quantity"] += txn.quantity
            if before > ZERO:
                splits[txn.symbol].append((_event_date(txn), state["quantity"] / before))
        elif txn.kind in TRADE_KINDS and txn.quantity is not None and txn.amount is not None:
            if record:
                paths[txn.symbol]["trades"].append(
                    (
                        _event_date(txn),
                        txn.quantity if txn.action == BUY else -txn.quantity,
                        txn.price,
                    )
                )
            if txn.action == BUY:
                state["quantity"] += txn.quantity
                state["cost_basis_jpy"] += -txn.amount
            elif txn.action == SELL and state["quantity"] > ZERO:
                share = min(txn.quantity / state["quantity"], ONE)
                removed = state["cost_basis_jpy"] * share
                state["realized"] += txn.amount - removed
                state["cost_basis_jpy"] -= removed
                state["quantity"] -= txn.quantity

    cursor = 0
    for date in dates:
        while cursor < len(ordered) and _event_date(ordered[cursor]) <= date:
            apply(ordered[cursor], record=True)
            cursor += 1
        for symbol, state in book.items():
            paths[symbol]["quantity"].append(state["quantity"])
            paths[symbol]["cost_basis_jpy"].append(state["cost_basis_jpy"])
            paths[symbol]["realized_cum"].append(state["realized"])
    while cursor < len(ordered):
        # a split after the window still restates everything inside it
        apply(ordered[cursor], record=False)
        cursor += 1

    for symbol, events in splits.items():
        path = paths[symbol]
        for on, factor in events:
            path["quantity"] = [
                q * factor if d < on else q for d, q in zip(dates, path["quantity"], strict=False)
            ]
            path["trades"] = [
                (d, q * factor, None if p is None else p / factor) if d < on else (d, q, p)
                for d, q, p in path["trades"]
            ]
    return paths


def account_paths(
    rows: list[Txn],
    dates: Sequence[str],
    prices: dict[str, list[Decimal | None]],
    account_id: str = "securities",
) -> AccountSeries:
    """The account's NAV, deposits and P&L buckets on each date.

    Cash moves on the trade date (``_event_date``), the same day the quantity does,
    so NAV never counts a purchase twice between trade and settlement. With cost at
    the settled amount, ``NAV − deposits = unrealised + realised + dividends`` on every
    date; commissions are inside the cost basis, so ``fees_cum`` stays zero. A date on
    which a held symbol has no price is None.
    """
    ordered = sorted(rows, key=lambda t: (_event_date(t), t.settle_date or ""))
    paths = replay(rows, dates)
    n = len(dates)
    cash: list[Decimal] = []
    deposits: list[Decimal | None] = []
    dividends: list[Decimal | None] = []
    running_cash = running_dep = running_div = ZERO
    cursor = 0
    for date in dates:
        while cursor < len(ordered) and _event_date(ordered[cursor]) <= date:
            txn = ordered[cursor]
            cursor += 1
            if txn.amount is None:
                continue
            running_cash += txn.amount
            if txn.kind.startswith("入金(振込)"):
                running_dep += txn.amount
            elif txn.kind in DIVIDEND_KINDS:
                running_div += txn.amount
        cash.append(running_cash)
        deposits.append(running_dep)
        dividends.append(running_div)
    nav: list[Decimal | None] = []
    unrealized: list[Decimal | None] = []
    realized: list[Decimal | None] = []
    for i in range(n):
        value = unreal = ZERO
        defined = True
        for symbol, path in paths.items():
            q = path["quantity"][i]
            if q <= ZERO:
                continue
            price = (prices.get(symbol) or [None] * n)[i]
            if price is None:
                defined = False
                break
            value += q * price
            unreal += q * price - path["cost_basis_jpy"][i]
        realized.append(sum((p["realized_cum"][i] for p in paths.values()), ZERO))
        nav.append(cash[i] + value if defined else None)
        unrealized.append(unreal if defined else None)
    zeros: list[Decimal | None] = [ZERO] * n
    return AccountSeries(
        account_id=account_id,
        nav=nav,
        deposits_cum=deposits,
        unrealized=unrealized,
        realized_cum=realized,
        dividends_cum=dividends,
        fees_cum=list(zeros),
        fx_translation_cum=list(zeros),
        forex_cum=list(zeros),
        xirr_flows=[
            (_event_date(t), t.amount)
            for t in ordered
            if t.kind.startswith("入金(振込)") and t.amount is not None
        ],
    )
