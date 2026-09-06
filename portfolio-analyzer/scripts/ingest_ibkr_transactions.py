#!/usr/bin/env python3
"""Turn an IBKR transaction history into a ledger, and backfill the snapshot's cost basis.

The snapshot records what is held today; the transaction history records how it was bought.
Reading the second gives the first its missing cost basis, and lets the yen-based gain on a
foreign holding be split into the part the price moved and the part the currency moved.

    uv run --package portfolio-analyzer python \
        portfolio-analyzer/scripts/ingest_ibkr_transactions.py \
        --snapshot portfolio-analyzer/data/portfolio-2026-09-01.private.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer import ibkr  # noqa: E402

DEFAULT_ACCOUNT = "global_broker"
DEFAULT_TRANSACTIONS = PROJECT_ROOT / "data/ibkr-transactions.private.csv"
DEFAULT_LEDGER = PROJECT_ROOT / "data/ibkr-ledger.private.json"
NON_MARKET_SYMBOLS = {"CASH_JPY", "RECONCILIATION"}
# Same bar as core.validate_portfolio: snapshots store rounded position values.
TOLERANCE_JPY = 1.0


def ledger_symbol(symbol: str, currency: str) -> str | None:
    """Return the transaction-history symbol for a snapshot holding, or None if it has none."""
    if symbol in NON_MARKET_SYMBOLS:
        return None
    if currency == "JPY" and symbol.isdigit():
        return f"{symbol}.T"
    if currency == "USD":
        return symbol
    return None


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _account_positions(snapshot: dict[str, Any], account_id: str) -> list[dict[str, Any]]:
    return [row for row in snapshot["positions"] if row["account_id"] == account_id]


def _mapped(snapshot: dict[str, Any], account_id: str) -> dict[str, dict[str, Any]]:
    """Snapshot positions of one account, keyed by their transaction-history symbol."""
    mapped = {}
    for row in _account_positions(snapshot, account_id):
        key = ledger_symbol(row["symbol"], row["currency"])
        if key is not None:
            mapped[key] = row
    return mapped


def _open_holdings(holdings: dict[str, ibkr.Holding]) -> dict[str, ibkr.Holding]:
    return {symbol: holding for symbol, holding in holdings.items() if not holding.is_closed}


def reconcile_quantities(
    holdings: dict[str, ibkr.Holding], snapshot: dict[str, Any], account_id: str
) -> list[str]:
    """Report every open holding whose quantity the snapshot does not agree with."""
    positions = _mapped(snapshot, account_id)
    problems = []
    for symbol, holding in sorted(_open_holdings(holdings).items()):
        position = positions.get(symbol)
        if position is None:
            problems.append(f"{symbol}: 台帳は {holding.quantity} 保有だがスナップショットにない")
            continue
        recorded = Decimal(str(position["quantity"]))
        if recorded != holding.quantity:
            problems.append(
                f"{symbol}: 台帳 {holding.quantity} とスナップショット {recorded} が一致しない"
            )
    for symbol in sorted(set(positions) - set(_open_holdings(holdings))):
        problems.append(f"{symbol}: スナップショットにあるが台帳に建玉がない")
    return problems


def apply_cost_basis(
    snapshot: dict[str, Any], transactions: list[ibkr.Transaction], account_id: str
) -> dict[str, Any]:
    """Return a copy of the snapshot with the account's cost basis and P&L filled in."""
    holdings = ibkr.derive_holdings(transactions)
    updated = copy.deepcopy(snapshot)
    positions = _mapped(updated, account_id)
    unrealized = Decimal(0)
    for symbol, holding in _open_holdings(holdings).items():
        position = positions.get(symbol)
        if position is None:
            continue
        position["average_cost"] = float(holding.cost_basis_native / holding.quantity)
        position["average_cost_currency"] = holding.currency
        unrealized += Decimal(str(position["market_value_jpy"])) - holding.cost_basis_jpy

    for account in updated["accounts"]:
        if account["id"] != account_id:
            continue
        account["unrealized_pnl_jpy"] = float(unrealized)
        account["quality_note"] = (
            "取得原価は IBKR 取引履歴（約定日レート換算・手数料込み）から平均法で逆算。"
            "口座損益は保有証券の含み損益のみで、現金・残高調整は含まない"
        )
    return updated


def _position_value(snapshot: dict[str, Any], account_id: str, symbol: str) -> Decimal:
    for row in _account_positions(snapshot, account_id):
        if row["symbol"] == symbol:
            return Decimal(str(row["market_value_jpy"]))
    return Decimal(0)


def build_ledger(
    transactions: list[ibkr.Transaction], snapshot: dict[str, Any], account_id: str
) -> dict[str, Any]:
    """Assemble the normalised ledger: cost basis, P&L attribution, cash buckets, XIRR."""
    holdings = ibkr.derive_holdings(transactions)
    cash = ibkr.summarize_cash(transactions)
    positions = _mapped(snapshot, account_id)
    account = next(row for row in snapshot["accounts"] if row["id"] == account_id)

    rows = []
    for symbol, holding in sorted(_open_holdings(holdings).items()):
        position = positions.get(symbol)
        if position is None:
            continue
        price_now = Decimal(str(position["price"]))
        fx_now = Decimal(str(position["fx_rate"]))
        split = ibkr.decompose_pnl(holding, price_now, fx_now)
        assert split is not None  # open holdings always decompose
        rows.append(
            {
                "symbol": position["symbol"],
                "ledger_symbol": symbol,
                "name": position["name"],
                "currency": holding.currency,
                "quantity": _float(holding.quantity),
                "average_cost": _float(holding.cost_basis_native / holding.quantity),
                "average_trade_fx": _float(holding.average_trade_fx),
                "price_now": _float(price_now),
                "fx_now": _float(fx_now),
                "cost_basis_jpy": _float(holding.cost_basis_jpy),
                "market_value_jpy": _float(split.market_value_jpy),
                "price_jpy": _float(split.price_jpy),
                "fx_jpy": _float(split.fx_jpy),
                "cross_jpy": _float(split.cross_jpy),
                "commission_jpy": _float(split.commission_jpy),
                "total_jpy": _float(split.total_jpy),
            }
        )

    closed = [
        {"symbol": symbol, "realized_pnl_jpy": _float(holding.realized_pnl_jpy)}
        for symbol, holding in sorted(holdings.items())
        if holding.is_closed
    ]
    account_value = Decimal(str(account["total_value_jpy"]))
    # An IRR is taken from the investor's side: a deposit into the account is money out.
    flows = [(day, -amount) for day, amount in cash.deposit_flows]
    flows.append((account["as_of"], account_value))
    dates = [row.date for row in transactions]

    # The account balance has to fall out of the ledger's own buckets, or one of them is wrong.
    # Commissions are already inside the trade net amounts, so they must not be added again.
    unrealized = sum((Decimal(str(row["total_jpy"])) for row in rows), Decimal(0))
    realized = sum((holding.realized_pnl_jpy for holding in holdings.values()), Decimal(0))
    snapshot_reconciliation = _position_value(snapshot, account_id, "RECONCILIATION")
    cash_after_snapshot = cash.ending_cash_jpy - _position_value(snapshot, account_id, "CASH_JPY")
    explained = (
        cash.deposits_jpy
        + realized
        + unrealized
        + cash.dividends_jpy
        + cash.withholding_tax_jpy
        + cash.other_fees_jpy
        + cash.fx_translation_pnl_jpy
        + cash.forex_trade_component_jpy
        + snapshot_reconciliation
        - cash_after_snapshot
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "IBKR transaction history (base currency JPY)",
        "account_id": account_id,
        "period": {"start": min(dates), "end": max(dates)},
        "cash": {
            "ending_cash_jpy": _float(cash.ending_cash_jpy),
            "deposits_jpy": _float(cash.deposits_jpy),
            "dividends_jpy": _float(cash.dividends_jpy),
            "withholding_tax_jpy": _float(cash.withholding_tax_jpy),
            "net_dividends_jpy": _float(cash.dividends_jpy + cash.withholding_tax_jpy),
            "other_fees_jpy": _float(cash.other_fees_jpy),
            "trade_commissions_jpy": _float(cash.trade_commissions_jpy),
            "fx_translation_pnl_jpy": _float(cash.fx_translation_pnl_jpy),
            "forex_trade_component_jpy": _float(cash.forex_trade_component_jpy),
        },
        "performance": {
            "deposits_jpy": _float(cash.deposits_jpy),
            "account_value_jpy": _float(account_value),
            "account_as_of": account["as_of"],
            "net_gain_jpy": _float(account_value - cash.deposits_jpy),
            "money_weighted_return": _float(ibkr.money_weighted_return(flows)),
            "realized_pnl_jpy": _float(realized),
            "unrealized_pnl_jpy": _float(unrealized),
        },
        "reconciliation": {
            "account_value_jpy": _float(account_value),
            "explained_jpy": _float(explained),
            "unexplained_jpy": _float(account_value - explained),
            "snapshot_reconciliation_jpy": _float(snapshot_reconciliation),
            "cash_after_snapshot_jpy": _float(cash_after_snapshot),
            "note": (
                "口座残高 = 入金 + 実現損益 + 含み損益 + 配当純額 + 諸費用 + FX換算損益 "
                "+ 為替取引損益 + 残高調整 − スナップショット後の現金増減"
            ),
        },
        "holdings": rows,
        "closed": closed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transactions", type=Path, default=DEFAULT_TRANSACTIONS)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--snapshot-out",
        type=Path,
        default=None,
        help="where to write the snapshot with cost basis (default: <snapshot>-with-cost)",
    )
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    transactions = ibkr.parse_transactions(args.transactions.read_text(encoding="utf-8"))
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))

    problems = reconcile_quantities(ibkr.derive_holdings(transactions), snapshot, args.account)
    if problems:
        print("数量が照合できないので書き戻しは行いません:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        raise SystemExit(1)

    ledger = build_ledger(transactions, snapshot, args.account)
    args.ledger.write_text(dumps(ledger), encoding="utf-8")

    target = args.snapshot_out or args.snapshot.with_name(
        args.snapshot.name.replace(".private.json", "-with-cost.private.json")
    )
    target.write_text(dumps(apply_cost_basis(snapshot, transactions, args.account)), "utf-8")

    cash = ledger["cash"]
    print(f"ledger   -> {args.ledger}")
    print(f"snapshot -> {target}")
    print(f"期間 {ledger['period']['start']} 〜 {ledger['period']['end']}")
    print(
        f"入金 {cash['deposits_jpy']:,.0f} 円 / 口座 {ledger['performance']['account_value_jpy']:,.0f} 円"
    )
    print(f"資金加重リターン {ledger['performance']['money_weighted_return']:.4%}")
    unexplained = ledger["reconciliation"]["unexplained_jpy"]
    if abs(unexplained) >= TOLERANCE_JPY:
        print(f"照合差異 {unexplained:,.2f} 円（1円を超えています）", file=sys.stderr)
    else:
        print(f"口座残高との照合 OK（差異 {unexplained:,.2f} 円）")


if __name__ == "__main__":
    main()
