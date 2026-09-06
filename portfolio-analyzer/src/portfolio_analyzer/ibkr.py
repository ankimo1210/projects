"""Read an IBKR base-currency transaction history and derive cost basis and performance.

The broker exports several sections in one CSV. Only the ``Transaction History`` section
carries rows we can use, and every money column in it is already stated in the account's
base currency (JPY here), while ``Price`` stays in the instrument's own currency. That
split is what lets us recover the trade-date FX rate for each fill.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

SECTION = "Transaction History"
MISSING = "-"
EXPECTED_COLUMNS = (
    "Date",
    "Account",
    "Description",
    "Transaction Type",
    "Symbol",
    "Quantity",
    "価格",
    "Price Currency",
    "Gross Amount",
    "Commission",
    "Net Amount",
)


@dataclass(frozen=True)
class Transaction:
    """One row of the transaction history, in the account's base currency."""

    date: str
    description: str
    transaction_type: str
    symbol: str | None
    quantity: Decimal | None
    price: Decimal | None
    price_currency: str | None
    gross_amount: Decimal | None
    commission: Decimal | None
    net_amount: Decimal | None


def _text(value: str) -> str | None:
    stripped = value.strip()
    return None if stripped in ("", MISSING) else stripped


def _number(value: str) -> Decimal | None:
    stripped = _text(value)
    return None if stripped is None else Decimal(stripped.replace(",", ""))


def parse_transactions(text: str) -> list[Transaction]:
    """Return the ``Transaction History`` rows, ignoring every other section."""
    rows = list(csv.reader(io.StringIO(text)))
    header = next(
        (row for row in rows if len(row) > 2 and row[0] == SECTION and row[1] == "Header"),
        None,
    )
    if header is None:
        raise ValueError(f"no {SECTION} header found")
    labels = tuple(cell.strip() for cell in header[2:])
    if labels != EXPECTED_COLUMNS:
        raise ValueError(f"unexpected {SECTION} column layout: {labels}")

    transactions = []
    for row in rows:
        if len(row) < 2 or row[0] != SECTION or row[1] != "Data":
            continue
        fields = row[2:]
        if len(fields) != len(EXPECTED_COLUMNS):
            raise ValueError(f"unexpected {SECTION} column count in row: {row}")
        date, _account, description, kind, symbol, quantity, price, currency, gross, fee, net = (
            fields
        )
        transactions.append(
            Transaction(
                date=date.strip(),
                description=description.strip(),
                transaction_type=kind.strip(),
                symbol=_text(symbol),
                quantity=_number(quantity),
                price=_number(price),
                price_currency=_text(currency),
                gross_amount=_number(gross),
                commission=_number(fee),
                net_amount=_number(net),
            )
        )
    return transactions


TRADE_TYPES = ("Buy", "Sell")


@dataclass(frozen=True)
class Holding:
    """Average-cost state of one instrument after replaying every fill."""

    symbol: str
    currency: str
    quantity: Decimal
    cost_basis_jpy: Decimal
    cost_basis_gross_jpy: Decimal
    cost_basis_native: Decimal
    average_trade_fx: Decimal | None
    realized_pnl_jpy: Decimal

    @property
    def is_closed(self) -> bool:
        return self.quantity == 0


def _chronological(transactions: list[Transaction]) -> list[Transaction]:
    """Oldest first. The export is newest first, so reverse before the stable sort by date."""
    return sorted(reversed(transactions), key=lambda row: row.date)


def derive_holdings(transactions: list[Transaction]) -> dict[str, Holding]:
    """Replay the fills under the average-cost method and return the surviving state.

    Cost basis is kept twice: in JPY including commission, which is what the snapshot wants,
    and in the instrument's own currency excluding it, which is what separates a price move
    from an FX move later on.
    """
    state: dict[str, dict[str, Decimal | str]] = {}
    for row in _chronological(transactions):
        if row.transaction_type not in TRADE_TYPES:
            continue
        if row.symbol is None or row.quantity is None or row.price is None:
            raise ValueError(f"trade row without symbol, quantity or price: {row}")
        book = state.setdefault(
            row.symbol,
            {
                "currency": row.price_currency or "JPY",
                "quantity": Decimal(0),
                "cost_jpy": Decimal(0),
                "cost_gross_jpy": Decimal(0),
                "cost_native": Decimal(0),
                "realized": Decimal(0),
            },
        )
        gross = row.gross_amount or Decimal(0)
        net = row.net_amount or Decimal(0)
        native = row.quantity * row.price
        if row.quantity > 0:
            book["quantity"] += row.quantity
            book["cost_jpy"] += -net
            book["cost_gross_jpy"] += -gross
            book["cost_native"] += native
            continue

        sold = -row.quantity
        held = book["quantity"]
        if sold > held:
            raise ValueError(f"{row.symbol}: sold {sold} but only {held} was held on {row.date}")
        share = sold / held
        removed_jpy = book["cost_jpy"] * share
        book["quantity"] = held - sold
        book["cost_jpy"] -= removed_jpy
        book["cost_gross_jpy"] -= book["cost_gross_jpy"] * share
        book["cost_native"] -= book["cost_native"] * share
        book["realized"] += net - removed_jpy

    holdings = {}
    for symbol, book in state.items():
        native = book["cost_native"]
        holdings[symbol] = Holding(
            symbol=symbol,
            currency=str(book["currency"]),
            quantity=book["quantity"],
            cost_basis_jpy=book["cost_jpy"],
            cost_basis_gross_jpy=book["cost_gross_jpy"],
            cost_basis_native=native,
            average_trade_fx=(book["cost_gross_jpy"] / native if native else None),
            realized_pnl_jpy=book["realized"],
        )
    return holdings


@dataclass(frozen=True)
class CashSummary:
    """Where the base-currency cash balance came from, split by what caused it."""

    ending_cash_jpy: Decimal
    deposits_jpy: Decimal
    dividends_jpy: Decimal
    withholding_tax_jpy: Decimal
    other_fees_jpy: Decimal
    trade_commissions_jpy: Decimal
    fx_translation_pnl_jpy: Decimal
    forex_trade_component_jpy: Decimal
    deposit_flows: list[tuple[str, Decimal]]


def summarize_cash(transactions: list[Transaction]) -> CashSummary:
    """Bucket the ledger by cause. The buckets sum back to the ending cash balance."""
    rows = _chronological(transactions)

    def total(*kinds: str) -> Decimal:
        return sum(
            (row.net_amount or Decimal(0) for row in rows if row.transaction_type in kinds),
            Decimal(0),
        )

    return CashSummary(
        ending_cash_jpy=sum((row.net_amount or Decimal(0) for row in rows), Decimal(0)),
        deposits_jpy=total("Deposit"),
        dividends_jpy=total("Dividend"),
        withholding_tax_jpy=total("Foreign Tax Withholding"),
        other_fees_jpy=total("Other Fee"),
        trade_commissions_jpy=sum(
            (row.commission or Decimal(0) for row in rows if row.transaction_type in TRADE_TYPES),
            Decimal(0),
        ),
        fx_translation_pnl_jpy=sum(
            (
                row.net_amount or Decimal(0)
                for row in rows
                if row.transaction_type == "Adjustment" and "FX Translation" in row.description
            ),
            Decimal(0),
        ),
        forex_trade_component_jpy=total("Forex Trade Component"),
        deposit_flows=[
            (row.date, row.net_amount or Decimal(0))
            for row in rows
            if row.transaction_type == "Deposit"
        ],
    )


DAYS_PER_YEAR = 365.0
_RATE_FLOOR = -0.9999
_RATE_CEILING = 10.0
_BISECTION_STEPS = 200


def money_weighted_return(flows: list[tuple[str, Decimal]]) -> Decimal | None:
    """Annualised internal rate of return (XIRR) over dated cash flows, ACT/365.

    Bisection rather than Newton: no dependency, and it cannot diverge on the flat
    stretches an irregular contribution schedule produces. Returns None when the flows
    have no sign change, which is when the rate is not defined.
    """
    if len(flows) < 2:
        return None
    amounts = [amount for _, amount in flows]
    if not (any(amount > 0 for amount in amounts) and any(amount < 0 for amount in amounts)):
        return None

    start = min(date.fromisoformat(day) for day, _ in flows)
    dated = [
        ((date.fromisoformat(day) - start).days / DAYS_PER_YEAR, float(amount))
        for day, amount in flows
    ]

    def npv(rate: float) -> float:
        return sum(amount / (1.0 + rate) ** years for years, amount in dated)

    low, high = _RATE_FLOOR, _RATE_CEILING
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(_BISECTION_STEPS):
        middle = (low + high) / 2
        if npv(low) * npv(middle) <= 0:
            high = middle
        else:
            low = middle
    return Decimal(repr((low + high) / 2))


@dataclass(frozen=True)
class PnlDecomposition:
    """Unrealised JPY P&L of one holding, split into what actually caused it.

    The yen cost basis is struck at the trade-date FX rate, so a yen-based gain on a
    foreign holding mixes a price move with a currency move. The three terms are the
    usual factorisation of q*P1*S1 - q*P0*S0, and the commission term carries the fees
    that the cost basis absorbed, so the four add back to the total exactly.
    """

    market_value_jpy: Decimal
    price_jpy: Decimal
    fx_jpy: Decimal
    cross_jpy: Decimal
    commission_jpy: Decimal
    total_jpy: Decimal


def decompose_pnl(holding: Holding, price_now: Decimal, fx_now: Decimal) -> PnlDecomposition | None:
    """Split a holding's unrealised JPY P&L into price, FX, cross and commission terms."""
    if holding.is_closed or holding.average_trade_fx is None:
        return None

    entry_fx = holding.average_trade_fx
    native_now = holding.quantity * price_now
    native_gain = native_now - holding.cost_basis_native

    market_value = native_now * fx_now
    price = native_gain * entry_fx
    fx = holding.cost_basis_native * fx_now - holding.cost_basis_gross_jpy
    # Residual rather than native_gain * (fx_now - entry_fx): entry_fx is itself a quotient,
    # and taking the leftover keeps the four terms summing to the total exactly.
    cross = native_gain * fx_now - price
    commission = holding.cost_basis_gross_jpy - holding.cost_basis_jpy

    return PnlDecomposition(
        market_value_jpy=market_value,
        price_jpy=price,
        fx_jpy=fx,
        cross_jpy=cross,
        commission_jpy=commission,
        total_jpy=market_value - holding.cost_basis_jpy,
    )
