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
    day_stock_pnl_jpy: Decimal | None
    day_fx_pnl_jpy: Decimal | None
    day_change_pct: Decimal | None
    cost_basis_jpy: Decimal | None
    average_cost: Decimal | None
    unrealized_jpy: Decimal | None
    unrealized_pct: Decimal | None
    unrealized_stock_jpy: Decimal | None
    unrealized_fx_jpy: Decimal | None
    price_pnl_jpy: Decimal | None
    fx_pnl_jpy: Decimal | None
    cross_pnl_jpy: Decimal | None
    commission_jpy: Decimal | None
    tax_category: str | None
    tax_rate: Decimal | None
    day_pnl_after_tax_jpy: Decimal | None
    unrealized_tax_jpy: Decimal | None
    unrealized_after_tax_jpy: Decimal | None
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
    account_rates = {str(a["id"]): _dec(a.get("tax_rate")) for a in snapshot.get("accounts", [])}
    rows: list[Row] = []
    for pos in snapshot["positions"]:
        account_id = str(pos["account_id"])
        symbol = str(pos["symbol"])
        currency = str(pos["currency"])
        quantity = _dec(pos.get("quantity"))
        ticker = str(pos["ticker"]) if pos.get("ticker") else market_symbol(symbol, currency)
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
            day_stock_pnl_jpy=None,
            day_fx_pnl_jpy=None,
            day_change_pct=None,
            cost_basis_jpy=None,
            average_cost=None,
            unrealized_jpy=None,
            unrealized_pct=None,
            unrealized_stock_jpy=None,
            unrealized_fx_jpy=None,
            price_pnl_jpy=None,
            fx_pnl_jpy=None,
            cross_pnl_jpy=None,
            commission_jpy=None,
            tax_category=None,
            tax_rate=_dec(pos.get("tax_rate")),
            day_pnl_after_tax_jpy=None,
            unrealized_tax_jpy=None,
            unrealized_after_tax_jpy=None,
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
                row.day_stock_pnl_jpy = quantity * (quote.close - quote.prev_close) * rate
                row.day_fx_pnl_jpy = row.day_pnl_jpy - row.day_stock_pnl_jpy
                row.day_change_pct = quote.close / quote.prev_close - ONE
            _attach_cost(row, cost.get((account_id, symbol)))
        _attach_tax(row, cost.get((account_id, symbol)), account_rates.get(account_id))
        rows.append(row)
    return rows


def _attach_tax(row: Row, holding: dict[str, Any] | None, account_rate: Decimal | None) -> None:
    """Rate: the position's own, else 0 for a holding bought only through NISA, else the account's.

    The tax itself is settled across positions by ``net_tax``.
    """
    row.tax_category = (
        str(holding["tax_category"]) if holding and holding.get("tax_category") else None
    )
    if row.tax_rate is None:
        row.tax_rate = ZERO if row.tax_category == "nisa" else account_rate


@dataclass
class TaxPool:
    """The taxable positions netted together, and what selling them all would cost in tax."""

    rate: Decimal | None
    unrealized_jpy: Decimal
    realized_ytd_jpy: Decimal
    carryforward_loss_jpy: Decimal
    tax_jpy: Decimal
    prev_tax_jpy: Decimal


def _liquidation_tax(
    unrealized: Decimal, realized: Decimal, carryforward: Decimal, rate: Decimal
) -> Decimal:
    """Tax owed for the year if everything were sold, less what is owed without selling.

    Negative when selling at a loss would win back tax on gains already realised.
    """
    with_sale = max(unrealized + realized - carryforward, ZERO)
    without = max(realized - carryforward, ZERO)
    return (with_sale - without) * rate


def _allocate(tax: Decimal, values: list[Decimal]) -> list[Decimal]:
    """Share the tax over the gains (or, when it is a refund, over the losses) pro rata."""
    weights = [max(v if tax > ZERO else -v, ZERO) for v in values]
    total = sum(weights, ZERO)
    if tax == ZERO or total == ZERO:
        return [ZERO] * len(values)
    return [tax * w / total for w in weights]


def net_tax(
    rows: list[Row], realized_ytd_jpy: Decimal = ZERO, carryforward_loss_jpy: Decimal = ZERO
) -> TaxPool:
    """Net gains against losses across every taxable position, then share the tax out.

    This follows how Japan taxes listed shares held outside NISA: gains and
    losses in taxable accounts at different brokers offset each other within a
    year (at filing), together with gains already realised that year and losses
    carried forward. A NISA holding (rate 0) sits outside it: its losses offset
    nothing. The tax lands on the positions with gains in proportion to the
    gain, so positions, accounts and the total all add up. Daily after-tax is the
    day's P&L less the change in each position's share since the previous close.
    """
    for r in rows:
        r.day_pnl_after_tax_jpy = r.unrealized_tax_jpy = r.unrealized_after_tax_jpy = None
        if r.tax_rate == ZERO:
            r.day_pnl_after_tax_jpy = r.day_pnl_jpy
            if r.unrealized_jpy is not None:
                r.unrealized_tax_jpy, r.unrealized_after_tax_jpy = ZERO, r.unrealized_jpy
    taxable = [r for r in rows if r.tax_rate is not None and r.tax_rate > ZERO]
    rates = sorted({r.tax_rate for r in taxable})
    if len(rates) > 1:
        raise ValueError(f"netting needs one tax rate across taxable positions, got {rates}")
    rate = rates[0] if rates else None
    pooled = [r for r in taxable if r.unrealized_jpy is not None]
    now = [r.unrealized_jpy for r in pooled]
    prev = [r.unrealized_jpy - (r.day_pnl_jpy or ZERO) for r in pooled]
    total_now, total_prev = sum(now, ZERO), sum(prev, ZERO)
    tax = prev_tax = ZERO
    if rate is not None:
        tax = _liquidation_tax(total_now, realized_ytd_jpy, carryforward_loss_jpy, rate)
        prev_tax = _liquidation_tax(total_prev, realized_ytd_jpy, carryforward_loss_jpy, rate)
    for r, share, prev_share in zip(
        pooled, _allocate(tax, now), _allocate(prev_tax, prev), strict=True
    ):
        r.unrealized_tax_jpy = share
        r.unrealized_after_tax_jpy = r.unrealized_jpy - share
        if r.day_pnl_jpy is not None:
            r.day_pnl_after_tax_jpy = r.day_pnl_jpy - (share - prev_share)
    return TaxPool(
        rate=rate,
        unrealized_jpy=total_now,
        realized_ytd_jpy=realized_ytd_jpy,
        carryforward_loss_jpy=carryforward_loss_jpy,
        tax_jpy=tax,
        prev_tax_jpy=prev_tax,
    )


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
    # A yen holding has no currency exposure; its decomposition's FX term is only the
    # commission folded into the cost basis, which belongs with the stock side.
    row.unrealized_fx_jpy = split.fx_jpy if row.currency != "JPY" else ZERO
    row.unrealized_stock_jpy = split.total_jpy - row.unrealized_fx_jpy
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
    day_stock_pnl_jpy: Decimal | None
    day_fx_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    unrealized_stock_jpy: Decimal | None
    unrealized_fx_jpy: Decimal | None
    unrealized_tax_jpy: Decimal | None
    unrealized_after_tax_jpy: Decimal | None
    day_pnl_after_tax_jpy: Decimal | None
    total_after_tax_jpy: Decimal | None
    cost_known_value_jpy: Decimal
    snapshot_unrealized_jpy: Decimal | None


@dataclass
class Summary:
    accounts: dict[str, AccountSummary]
    total_jpy: Decimal
    quoted_value_jpy: Decimal
    day_pnl_jpy: Decimal | None
    day_stock_pnl_jpy: Decimal | None
    day_fx_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    unrealized_stock_jpy: Decimal | None
    unrealized_fx_jpy: Decimal | None
    unrealized_tax_jpy: Decimal | None
    unrealized_after_tax_jpy: Decimal | None
    day_pnl_after_tax_jpy: Decimal | None
    total_after_tax_jpy: Decimal | None
    cost_known_value_jpy: Decimal


def _sum_optional(values: list[Decimal | None]) -> Decimal | None:
    present = [v for v in values if v is not None]
    return sum(present, ZERO) if present else None


def _sum_strict(pairs: list[tuple[Decimal | None, Decimal | None]]) -> Decimal | None:
    """Sum the second of each pair, but give up if any pair has a first without a second.

    An after-tax figure that silently skipped a position with no known rate
    would read as more precise than it is.
    """
    if any(base is not None and value is None for base, value in pairs):
        return None
    return _sum_optional([value for _, value in pairs])


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
            day_stock_pnl_jpy=_sum_optional([r.day_stock_pnl_jpy for r in mine]),
            day_fx_pnl_jpy=_sum_optional([r.day_fx_pnl_jpy for r in mine]),
            unrealized_known_jpy=_sum_optional([r.unrealized_jpy for r in mine]),
            unrealized_stock_jpy=_sum_optional([r.unrealized_stock_jpy for r in mine]),
            unrealized_fx_jpy=_sum_optional([r.unrealized_fx_jpy for r in mine]),
            unrealized_tax_jpy=(
                tax := _sum_strict([(r.unrealized_jpy, r.unrealized_tax_jpy) for r in mine])
            ),
            unrealized_after_tax_jpy=_sum_strict(
                [(r.unrealized_jpy, r.unrealized_after_tax_jpy) for r in mine]
            ),
            day_pnl_after_tax_jpy=_sum_strict(
                [(r.day_pnl_jpy, r.day_pnl_after_tax_jpy) for r in mine]
            ),
            total_after_tax_jpy=(
                None
                if tax is None and any(r.unrealized_jpy is not None for r in mine)
                else sum((r.market_value_jpy for r in mine), ZERO) - (tax or ZERO)
            ),
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
        day_stock_pnl_jpy=_sum_optional([a.day_stock_pnl_jpy for a in accounts.values()]),
        day_fx_pnl_jpy=_sum_optional([a.day_fx_pnl_jpy for a in accounts.values()]),
        unrealized_known_jpy=_sum_optional([a.unrealized_known_jpy for a in accounts.values()]),
        unrealized_stock_jpy=_sum_optional([a.unrealized_stock_jpy for a in accounts.values()]),
        unrealized_fx_jpy=_sum_optional([a.unrealized_fx_jpy for a in accounts.values()]),
        unrealized_tax_jpy=_sum_strict(
            [(a.unrealized_known_jpy, a.unrealized_tax_jpy) for a in accounts.values()]
        ),
        unrealized_after_tax_jpy=_sum_strict(
            [(a.unrealized_known_jpy, a.unrealized_after_tax_jpy) for a in accounts.values()]
        ),
        day_pnl_after_tax_jpy=_sum_strict(
            [(a.day_pnl_jpy, a.day_pnl_after_tax_jpy) for a in accounts.values()]
        ),
        total_after_tax_jpy=_sum_strict(
            [(a.total_jpy, a.total_after_tax_jpy) for a in accounts.values()]
        ),
        cost_known_value_jpy=sum((a.cost_known_value_jpy for a in accounts.values()), ZERO),
    )


def _rate_text(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}%"


def tax_note(snapshot: dict[str, Any], rows: list[Row], pool: TaxPool) -> str:
    """One line saying which rate each account's after-tax figures used, and how the tax was netted."""
    parts = []
    for acc in snapshot["accounts"]:
        mine = [
            r
            for r in rows
            if r.account_id == str(acc["id"])
            and r.tax_rate is not None
            and (r.day_pnl_jpy is not None or r.unrealized_jpy is not None)
        ]
        if not mine:
            continue
        nisa = any(r.tax_category == "nisa" for r in mine)
        others = sorted({r.tax_rate for r in mine if r.tax_category != "nisa"})
        if nisa and others:
            text = "NISA 0%・その他 " + "/".join(_rate_text(x) for x in others)
        elif nisa:
            text = "NISA 0%"
        else:
            text = "/".join(_rate_text(x) for x in others)
        if acc.get("tax_note"):
            text += f"（{acc['tax_note']}）"
        parts.append(f"{acc.get('name', acc['id'])} {text}")
    if not parts:
        return ""
    mixed = [r.symbol for r in rows if r.tax_category == "mixed"]
    tail = f" NISA と課税口座の両方で買った {'・'.join(mixed)} は課税側の率。" if mixed else ""

    def yen(value: Decimal, sign: bool = False) -> str:
        return (f"{round(value):+,}" if sign else f"{round(value):,}").replace("-", "−")

    netting = (
        f"課税分は口座をまたいで損益通算（含み損益 {yen(pool.unrealized_jpy, True)}・"
        f"今年の実現損益 {yen(pool.realized_ytd_jpy, True)}・繰越損失 {yen(pool.carryforward_loss_jpy)}）し、"
        f"見込み税額 {yen(pool.tax_jpy)} 円を含み益の銘柄に按分。配当との通算・外国税額控除は含まない。"
        if pool.rate is not None
        else ""
    )
    return "税引後は見込み: " + "、".join(parts) + "。" + netting + tail


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
        "day_stock_pnl_jpy": _f(summary.day_stock_pnl_jpy),
        "day_fx_pnl_jpy": _f(summary.day_fx_pnl_jpy),
        "unrealized_known_jpy": _f(summary.unrealized_known_jpy),
        "unrealized_stock_jpy": _f(summary.unrealized_stock_jpy),
        "unrealized_fx_jpy": _f(summary.unrealized_fx_jpy),
        "unrealized_after_tax_jpy": _f(summary.unrealized_after_tax_jpy),
        "day_pnl_after_tax_jpy": _f(summary.day_pnl_after_tax_jpy),
        "total_after_tax_jpy": _f(summary.total_after_tax_jpy),
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
                "day_fx_pnl_jpy": _f(r.day_fx_pnl_jpy),
                "unrealized_jpy": _f(r.unrealized_jpy),
                "unrealized_fx_jpy": _f(r.unrealized_fx_jpy),
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
