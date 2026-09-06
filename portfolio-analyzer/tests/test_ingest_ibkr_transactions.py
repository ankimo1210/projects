"""Tests for the IBKR ingestion script (synthetic rows only, no private data)."""

from __future__ import annotations

import copy
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from portfolio_analyzer import ibkr
from portfolio_analyzer.core import build_artifact, load_portfolio, validate_portfolio
from test_ibkr import BUY_QQQ, BUY_TOPIX, DEPOSIT, DIVIDEND, statement

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "ingest_ibkr_transactions", PROJECT_ROOT / "scripts/ingest_ibkr_transactions.py"
)
ingest = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ingest)


@pytest.fixture
def snapshot() -> dict:
    return {
        "snapshot_name": "test",
        "base_currency": "JPY",
        "accounts": [
            {
                "id": "global_broker",
                "name": "海外証券口座",
                "as_of": "2026-09-01",
                "total_value_jpy": 5039349.0197669,
                "unrealized_pnl_jpy": None,
                "daily_pnl_jpy": None,
                "quality_note": "取得原価が未入力",
                "account_type": "cash",
                "base_currency": "JPY",
                "purpose": "foreign_equities",
                "tax_category": "unknown",
            }
        ],
        "positions": [
            {
                "account_id": "global_broker",
                "symbol": "QQQ",
                "name": "Invesco QQQ Trust",
                "asset_class": "米国株",
                "currency": "USD",
                "quantity": 10,
                "price": 716.76,
                "fx_rate": 159.915,
                "market_value_jpy": 1146206.75,
                "value_status": "estimated",
                "source_note": "終値 × 数量",
            },
            {
                "account_id": "global_broker",
                "symbol": "1475",
                "name": "iシェアーズ・コア TOPIX ETF",
                "asset_class": "日本株",
                "currency": "JPY",
                "quantity": 2500,
                "price": 430.5,
                "fx_rate": 1.0,
                "market_value_jpy": 1076250.0,
                "value_status": "estimated",
                "source_note": "終値 × 数量",
            },
            {
                "account_id": "global_broker",
                "symbol": "CASH_JPY",
                "name": "円現金",
                "asset_class": "現金",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": 2816892.2697669,
                "value_status": "exact",
                "source_note": "現金欄",
            },
        ],
    }


@pytest.fixture
def transactions() -> list[ibkr.Transaction]:
    return ibkr.parse_transactions(statement(DIVIDEND, DEPOSIT, BUY_QQQ, BUY_TOPIX))


@pytest.mark.parametrize(
    ("symbol", "currency", "expected"),
    [
        ("1475", "JPY", "1475.T"),
        ("QQQ", "USD", "QQQ"),
        ("SMH", "USD", "SMH"),
        ("CASH_JPY", "JPY", None),
        ("RECONCILIATION", "JPY", None),
    ],
)
def test_ledger_symbol(symbol: str, currency: str, expected: str | None) -> None:
    assert ingest.ledger_symbol(symbol, currency) == expected


def test_reconcile_quantities_is_silent_when_every_position_matches(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    holdings = ibkr.derive_holdings(transactions)

    assert ingest.reconcile_quantities(holdings, snapshot, "global_broker") == []


def test_reconcile_quantities_reports_a_position_the_ledger_disagrees_with(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    snapshot["positions"][0]["quantity"] = 12
    holdings = ibkr.derive_holdings(transactions)

    problems = ingest.reconcile_quantities(holdings, snapshot, "global_broker")

    assert len(problems) == 1
    assert "QQQ" in problems[0]


def test_reconcile_quantities_reports_a_holding_missing_from_the_snapshot(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    del snapshot["positions"][1]
    holdings = ibkr.derive_holdings(transactions)

    problems = ingest.reconcile_quantities(holdings, snapshot, "global_broker")

    assert len(problems) == 1
    assert "1475.T" in problems[0]


def test_apply_cost_basis_fills_the_native_average_cost(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    updated = ingest.apply_cost_basis(snapshot, transactions, "global_broker")

    qqq = updated["positions"][0]
    assert qqq["average_cost"] == pytest.approx(727.715)
    assert qqq["average_cost_currency"] == "USD"
    topix = updated["positions"][1]
    assert topix["average_cost"] == pytest.approx(417.2)
    assert topix["average_cost_currency"] == "JPY"


def test_apply_cost_basis_leaves_cash_without_a_cost(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    updated = ingest.apply_cost_basis(snapshot, transactions, "global_broker")

    assert "average_cost" not in updated["positions"][2]


def test_apply_cost_basis_sets_the_account_pnl_from_the_jpy_cost_basis(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    updated = ingest.apply_cost_basis(snapshot, transactions, "global_broker")

    expected = (
        Decimal("1146206.75")
        - Decimal("1148273.7302331")
        + Decimal("1076250.0")
        - Decimal("1043834.0")
    )
    assert updated["accounts"][0]["unrealized_pnl_jpy"] == pytest.approx(float(expected))


def test_apply_cost_basis_does_not_mutate_the_input_snapshot(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    before = copy.deepcopy(snapshot)

    ingest.apply_cost_basis(snapshot, transactions, "global_broker")

    assert snapshot == before


def test_apply_cost_basis_output_still_loads_and_validates(
    snapshot: dict, transactions: list[ibkr.Transaction], tmp_path: Path
) -> None:
    updated = ingest.apply_cost_basis(snapshot, transactions, "global_broker")
    path = tmp_path / "snapshot.json"
    path.write_text(ingest.dumps(updated), encoding="utf-8")

    portfolio = load_portfolio(path)

    assert validate_portfolio(portfolio) == []


def test_build_ledger_splits_each_holding_into_price_and_fx(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    qqq = next(row for row in ledger["holdings"] if row["symbol"] == "QQQ")
    assert qqq["price_jpy"] < 0
    assert qqq["fx_jpy"] > 0
    assert qqq["price_jpy"] + qqq["fx_jpy"] + qqq["cross_jpy"] + qqq["commission_jpy"] == (
        pytest.approx(qqq["total_jpy"])
    )
    topix = next(row for row in ledger["holdings"] if row["symbol"] == "1475")
    assert topix["fx_jpy"] == 0


def test_build_ledger_carries_the_cash_buckets_and_the_money_weighted_return(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    assert ledger["cash"]["deposits_jpy"] == pytest.approx(5000000.0)
    assert ledger["cash"]["dividends_jpy"] == pytest.approx(9000.0)
    assert ledger["performance"]["deposits_jpy"] == pytest.approx(5000000.0)
    assert ledger["performance"]["account_value_jpy"] == pytest.approx(5039349.0197669)
    assert ledger["performance"]["money_weighted_return"] > 0


def test_build_ledger_lists_closed_positions_with_their_realized_pnl(
    snapshot: dict,
) -> None:
    from test_ibkr import SELL_QQQ_ALL

    transactions = ibkr.parse_transactions(statement(BUY_QQQ, BUY_TOPIX, SELL_QQQ_ALL))

    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    assert [row["symbol"] for row in ledger["closed"]] == ["QQQ"]
    assert ledger["closed"][0]["realized_pnl_jpy"] == pytest.approx(
        float(Decimal("1279840.0") - Decimal("1148273.7302331"))
    )


def test_build_ledger_reconciles_the_account_balance_against_the_buckets(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    check = ledger["reconciliation"]
    assert check["account_value_jpy"] == pytest.approx(5039349.0197669)
    assert check["explained_jpy"] == pytest.approx(5039349.0197669, abs=ingest.TOLERANCE_JPY)
    # Same 1-yen bar core.validate_portfolio uses: the snapshot stores rounded position
    # values, so the buckets can only be expected to close to the yen.
    assert abs(check["unexplained_jpy"]) < ingest.TOLERANCE_JPY


def test_build_ledger_reports_cash_that_moved_after_the_snapshot_was_taken(
    snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    snapshot["positions"][2]["market_value_jpy"] = 2816892.2697669 - 9000.0
    snapshot["accounts"][0]["total_value_jpy"] = 5039349.0197669 - 9000.0

    check = ingest.build_ledger(transactions, snapshot, "global_broker")["reconciliation"]

    assert check["cash_after_snapshot_jpy"] == pytest.approx(9000.0)
    assert abs(check["unexplained_jpy"]) < ingest.TOLERANCE_JPY


@pytest.fixture
def portfolio_snapshot(snapshot: dict, tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(ingest.dumps(snapshot), encoding="utf-8")
    return path


def test_build_artifact_without_a_ledger_has_no_ledger_widgets(portfolio_snapshot: Path) -> None:
    artifact = build_artifact(load_portfolio(portfolio_snapshot))

    ids = {item["id"] for item in artifact["manifest"]["tables"]}
    assert not any(name.startswith("ledger_") for name in ids)
    assert not any(name.startswith("ledger_") for name in artifact["snapshot"]["datasets"])


def test_build_artifact_with_a_ledger_adds_the_attribution_table(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    ids = {item["id"] for item in artifact["manifest"]["tables"]}
    assert {"ledger_attribution", "ledger_performance", "ledger_closed"} <= ids
    rows = artifact["snapshot"]["datasets"]["ledger_attribution"]
    assert {row["symbol"] for row in rows} == {"QQQ", "1475"}


def test_build_artifact_with_a_ledger_records_it_as_a_source(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(
        load_portfolio(portfolio_snapshot), ledger=ledger, ledger_source_path="data/led.json"
    )

    assert any(source["path"] == "data/led.json" for source in artifact["sources"])


def test_build_artifact_ledger_performance_reports_the_money_weighted_return(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    rows = {row["metric"]: row for row in artifact["snapshot"]["datasets"]["ledger_performance"]}
    # In percent points, not as a raw rate: the table shares one numeric column with the yen
    # rows, and a "number"-formatted 0.0366 renders as 0.04 on the page.
    assert rows["資金加重リターン（年率）"]["value"] == pytest.approx(
        ledger["performance"]["money_weighted_return"] * 100
    )
    assert rows["資金加重リターン（年率）"]["unit"] == "%"


def test_ledger_tables_never_format_a_yen_column_as_currency(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    # The reader renders "currency" with a dollar sign, and every figure here is yen.
    for table in artifact["manifest"]["tables"]:
        if not table["id"].startswith("ledger_"):
            continue
        assert [column for column in table["columns"] if column.get("format") == "currency"] == []


def test_build_artifact_with_a_ledger_renders_every_ledger_table_as_a_block(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    # A table only reaches the page if a block points at it; the manifest alone renders nothing.
    referenced = {
        block["tableId"] for block in artifact["manifest"]["blocks"] if block["type"] == "table"
    }
    assert {"ledger_performance", "ledger_attribution", "ledger_closed"} <= referenced


def test_ledger_tables_stay_narrow_enough_to_render_without_clipping(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    # Measured in the reader at 1440px: past ten columns the last one is cut off the page
    # and the table offers no horizontal scroll to reach it.
    for table in artifact["manifest"]["tables"]:
        if table["id"].startswith("ledger_"):
            assert len(table["columns"]) <= 10, table["id"]


def test_ledger_attribution_keeps_every_term_of_the_identity(
    portfolio_snapshot: Path, snapshot: dict, transactions: list[ibkr.Transaction]
) -> None:
    ledger = ingest.build_ledger(transactions, snapshot, "global_broker")

    artifact = build_artifact(load_portfolio(portfolio_snapshot), ledger=ledger)

    table = next(
        item for item in artifact["manifest"]["tables"] if item["id"] == "ledger_attribution"
    )
    fields = {column["field"] for column in table["columns"]}
    assert {"price_jpy", "fx_jpy", "cross_jpy", "commission_jpy", "total_jpy"} <= fields
