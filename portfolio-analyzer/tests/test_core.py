from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from portfolio_analyzer import (
    apply_proposal,
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
PRIVATE_PROPOSAL = PROJECT_ROOT / "data/rebalancing-proposal.private.json"
EXAMPLE_REFERENCE = PROJECT_ROOT / "data/analysis_reference.example.json"
EXAMPLE_PROPOSAL = PROJECT_ROOT / "data/rebalancing-proposal.example.json"
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


def test_position_value_reconciliation_rejects_silent_drift() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    changed = replace(
        portfolio.positions[0],
        market_value_jpy=portfolio.positions[0].market_value_jpy + Decimal("100"),
    )
    invalid = replace(portfolio, positions=(changed, *portfolio.positions[1:]))

    issues = validate_portfolio(invalid)

    assert any(issue.startswith("position value mismatch:") for issue in issues)
    assert any(issue.startswith("account total mismatch:") for issue in issues)


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


def test_nested_market_and_region_shocks_are_rejected() -> None:
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    scenario = replace(
        reference.scenarios[0],
        shocks={"株式全体": Decimal("-0.1"), "日本株": Decimal("-0.1")},
    )
    invalid = replace(reference, scenarios=(scenario, *reference.scenarios[1:]))

    assert any(
        issue.startswith("mutually exclusive factors")
        for issue in validate_analysis_reference(invalid)
    )


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


def test_example_proposal_preserves_total_and_moves_sale_proceeds_to_cash() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    proposal = apply_proposal(portfolio, EXAMPLE_PROPOSAL)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        proposal=proposal,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    comparison = {
        row["metric"]: row for row in artifact["snapshot"]["datasets"]["proposal_comparison"]
    }

    assert validate_portfolio(proposal.portfolio) == []
    assert sum(account.total_value_jpy for account in proposal.portfolio.accounts) == Decimal(
        "8000000"
    )
    assert comparison["現金比率"]["after"] > comparison["現金比率"]["before"]


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


def test_sample_valuation_keeps_provider_pe_separate_and_reports_coverage() -> None:
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

    assert summary["provider_pe"] == pytest.approx(18.5)
    assert summary["valuation_coverage_ratio"] == pytest.approx(3_500_000 / 4_400_000)
    assert summary["fresh_valuation_coverage_ratio"] == pytest.approx(3_500_000 / 4_400_000)
    assert "mixed_basis_pe" not in summary


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


@PRIVATE_ANALYSIS_ONLY
def test_private_risk_model_exposes_compound_and_lookthrough_risk() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    datasets = artifact["snapshot"]["datasets"]
    summary = next(row for row in datasets["summary"] if row["scope"] == "すべて")
    impacts = {
        row["scenario"]: row["impact_ratio"]
        for row in datasets["factor_sensitivity"]
        if row["scope"] == "すべて"
    }
    issuers = {
        row["issuer"]: row["portfolio_weight"]
        for row in datasets["issuer_exposure"]
        if row["scope"] == "すべて"
    }

    assert summary["position_effective_count"] == pytest.approx(6.8636, rel=1e-4)
    assert summary["sector_effective_count"] == pytest.approx(3.0001, rel=1e-4)
    assert summary["policy_breach_count"] == 4
    assert impacts["株式全体 -10%"] == pytest.approx(-0.07818, rel=1e-4)
    assert impacts["円10%上昇（外貨バスケット）"] == pytest.approx(-0.05323, rel=1e-4)
    assert summary["worst_compound_drawdown"] == pytest.approx(0.17498, rel=1e-4)
    assert issuers["Advantest"] == pytest.approx(0.16588, rel=1e-4)
    smh_market_loading = next(
        row["loading"]
        for row in datasets["factor_loadings"]
        if row["scope"] == "すべて"
        and row["position"].startswith("SMH ·")
        and row["factor"] == "株式全体"
    )
    assert smh_market_loading == pytest.approx(1.9)


@PRIVATE_DATA_ONLY
def test_dc_account_pnl_is_arithmetically_reconciled_but_caveated() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    artifact = build_artifact(portfolio, generated_at="2026-08-15T00:00:00+00:00")
    dc = next(
        row
        for row in artifact["snapshot"]["datasets"]["account_allocation"]
        if row["scope"] == "すべて" and row["account"] == "DC口座"
    )

    assert dc["implied_cost_basis_jpy"] == pytest.approx(5_129_000)
    assert dc["unrealized_return"] == pytest.approx(0.489148, rel=1e-5)
    assert "元画面未確認" in dc["quality_note"]


@PRIVATE_ANALYSIS_ONLY
def test_private_valuation_is_split_by_basis() -> None:
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

    assert summary["trailing_pe"] == pytest.approx(38.7205, rel=1e-4)
    assert summary["forward_pe"] == pytest.approx(23.4029, rel=1e-4)
    assert summary["provider_pe"] == pytest.approx(19.8451, rel=1e-4)
    assert summary["trailing_valuation_coverage_ratio"] < 0.25
    assert summary["forward_valuation_coverage_ratio"] < 0.41


@pytest.mark.skipif(
    not (PRIVATE_DATA.is_file() and PRIVATE_REFERENCE.is_file() and PRIVATE_PROPOSAL.is_file()),
    reason="private proposal inputs are not available",
)
def test_private_proposal_is_reproducible_and_tax_caveated() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
    proposal = apply_proposal(portfolio, PRIVATE_PROPOSAL)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        proposal=proposal,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    datasets = artifact["snapshot"]["datasets"]
    comparison = {row["metric"]: row for row in datasets["proposal_comparison"]}
    smh_trade = next(row for row in proposal.trade_details if row["symbol"] == "SMH")

    assert validate_portfolio(proposal.portfolio) == []
    assert comparison["実効セクター数"]["after"] > 4
    assert comparison["暫定ルール超過"]["after"] == 2
    assert smh_trade["native_realized_gain_estimate"] == pytest.approx(-174)
    assert "円換算取得原価は未確認" in smh_trade["tax_status"]
