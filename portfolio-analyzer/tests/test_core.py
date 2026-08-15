from decimal import Decimal
from pathlib import Path

import pytest
from portfolio_analyzer import (
    build_artifact,
    load_analysis_reference,
    load_portfolio,
    validate_analysis_reference,
    validate_portfolio,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DATA = PROJECT_ROOT / "data/portfolio.private.json"
EXAMPLE_DATA = PROJECT_ROOT / "data/portfolio.example.json"
PRIVATE_REFERENCE = PROJECT_ROOT / "data/analysis_reference.private.json"
EXAMPLE_REFERENCE = PROJECT_ROOT / "data/analysis_reference.example.json"
PRIVATE_DATA_ONLY = pytest.mark.skipif(
    not PRIVATE_DATA.is_file(), reason="private portfolio snapshot is not available"
)
PRIVATE_ANALYSIS_ONLY = pytest.mark.skipif(
    not (PRIVATE_DATA.is_file() and PRIVATE_REFERENCE.is_file()),
    reason="private portfolio analysis inputs are not available",
)


@pytest.mark.parametrize("path", [EXAMPLE_DATA])
def test_snapshots_reconcile(path: Path) -> None:
    portfolio = load_portfolio(path)
    assert validate_portfolio(portfolio) == []


@PRIVATE_DATA_ONLY
def test_private_total_matches_three_accounts() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    total = sum((account.total_value_jpy for account in portfolio.accounts), Decimal())
    assert total == Decimal("48298433")


@PRIVATE_DATA_ONLY
def test_private_data_keeps_estimates_and_reconciliation_visible() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    statuses = {position.value_status for position in portfolio.positions}
    assert statuses == {"exact", "estimated", "reconciliation"}
    assert sum(position.value_status == "estimated" for position in portfolio.positions) == 3
    assert sum(position.value_status == "reconciliation" for position in portfolio.positions) == 1


@PRIVATE_DATA_ONLY
def test_artifact_reconciles_summary_and_account_rows() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    artifact = build_artifact(portfolio, generated_at="2026-08-15T00:00:00+00:00")
    datasets = artifact["snapshot"]["datasets"]
    all_summary = next(row for row in datasets["summary"] if row["scope"] == "すべて")
    all_accounts = [row for row in datasets["account_allocation"] if row["scope"] == "すべて"]
    assert all_summary["total_value_jpy"] == pytest.approx(48_298_433)
    assert sum(row["market_value_jpy"] for row in all_accounts) == pytest.approx(48_298_433)


@PRIVATE_DATA_ONLY
def test_cash_and_foreign_currency_ratios_are_data_backed() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    artifact = build_artifact(portfolio, generated_at="2026-08-15T00:00:00+00:00")
    summary = next(
        row for row in artifact["snapshot"]["datasets"]["summary"] if row["scope"] == "すべて"
    )
    assert summary["cash_ratio"] == pytest.approx(9_420_854.55 / 48_298_433)
    assert summary["foreign_currency_ratio"] == pytest.approx(12_651_147.44 / 48_298_433)


@PRIVATE_DATA_ONLY
def test_stress_scenarios_are_ordered_by_severity() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    artifact = build_artifact(portfolio, generated_at="2026-08-15T00:00:00+00:00")
    rows = [row for row in artifact["snapshot"]["datasets"]["stress"] if row["scope"] == "すべて"]
    impacts = {row["scenario"]: row["impact_jpy"] for row in rows}
    assert impacts["深いリスクオフ"] < impacts["株式20%下落"] < impacts["軽い調整"] < 0


@PRIVATE_DATA_ONLY
def test_filter_targets_every_scoped_dataset() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    artifact = build_artifact(portfolio, generated_at="2026-08-15T00:00:00+00:00")
    dataset_names = set(artifact["snapshot"]["datasets"])
    filter_spec = artifact["manifest"]["filters"][0]
    target_names = {target["dataset"] for target in filter_spec["targets"]}
    assert target_names == dataset_names - {"summary"}


@pytest.mark.parametrize("path", [EXAMPLE_REFERENCE])
def test_analysis_references_are_valid(path: Path) -> None:
    reference = load_analysis_reference(path)
    assert validate_analysis_reference(reference) == []


def test_lookthrough_reconciles_to_each_scope_total() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    datasets = artifact["snapshot"]["datasets"]

    for summary in datasets["summary"]:
        scope = summary["scope"]
        lookthrough_total = sum(
            row["market_value_jpy"]
            for row in datasets["lookthrough_allocation"]
            if row["scope"] == scope
        )
        assert lookthrough_total == pytest.approx(summary["total_value_jpy"])


def test_sample_factor_sensitivity_matches_linear_assumptions() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    rows = [
        row
        for row in artifact["snapshot"]["datasets"]["factor_sensitivity"]
        if row["scope"] == "すべて"
    ]
    impacts = {row["scenario"]: row["impact_jpy"] for row in rows}

    assert impacts["株式全体 -10%"] == pytest.approx(-440_000)
    assert impacts["情報技術 -20%"] == pytest.approx(-300_000)
    assert impacts["日本金利 +100bp"] == pytest.approx(-97_500)


def test_sample_valuation_uses_harmonic_pe_and_explicit_coverage() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    summary = next(
        row for row in artifact["snapshot"]["datasets"]["summary"] if row["scope"] == "すべて"
    )

    assert summary["mixed_basis_pe"] == pytest.approx(18.5)
    assert summary["valuation_coverage_ratio"] == pytest.approx(3_500_000 / 4_400_000)
    assert summary["fresh_valuation_coverage_ratio"] == pytest.approx(3_500_000 / 4_400_000)
    assert summary["high_pe_equity_ratio"] == pytest.approx(0)


@PRIVATE_ANALYSIS_ONLY
def test_private_reference_exposes_valuation_freshness() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    summary = next(
        row for row in artifact["snapshot"]["datasets"]["summary"] if row["scope"] == "すべて"
    )

    assert summary["fresh_valuation_coverage_ratio"] < summary["valuation_coverage_ratio"]
    qualities = {
        row["position"].split(" · ", 1)[0]: row["quality"]
        for row in artifact["snapshot"]["datasets"]["valuation_detail"]
        if row["scope"] == "すべて"
    }
    stale_positions = {
        row["position"].split(" · ", 1)[0]
        for row in artifact["snapshot"]["datasets"]["valuation_detail"]
        if row["scope"] == "すべて" and row["quality"] == "要更新"
    }
    assert stale_positions == set()
    assert qualities["QQQ"] == "推定"
    assert qualities["SMH"] == "現行"
