from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from portfolio_analyzer import (
    FactorRisk,
    apply_proposal,
    build_artifact,
    load_analysis_reference,
    load_factor_risk,
    load_portfolio,
    most_plausible_shock,
    validate_analysis_reference,
    validate_factor_risk,
    validate_portfolio,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DATA = PROJECT_ROOT / "data/portfolio.private.json"
EXAMPLE_DATA = PROJECT_ROOT / "data/portfolio.example.json"
PRIVATE_REFERENCE = PROJECT_ROOT / "data/analysis_reference.private.json"
PRIVATE_PROPOSAL = PROJECT_ROOT / "data/rebalancing-proposal.private.json"
EXAMPLE_REFERENCE = PROJECT_ROOT / "data/analysis_reference.example.json"
EXAMPLE_PROPOSAL = PROJECT_ROOT / "data/rebalancing-proposal.example.json"
FACTOR_ESTIMATES = PROJECT_ROOT / "data/factor_estimates.json"
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


def test_event_calendar_links_scenarios_and_counts_days_from_reference_date() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    datasets = artifact["snapshot"]["datasets"]
    event = next(row for row in datasets["event_calendar"] if row["scope"] == "すべて")
    linked = next(
        row
        for row in datasets["factor_sensitivity"]
        if row["scope"] == "すべて" and row["scenario"] == event["scenario"]
    )
    table_ids = {table["id"] for table in artifact["manifest"]["tables"]}

    # days_until counts from the reference as_of (2026-08-14), not from the build time.
    assert reference.as_of == "2026-08-14"
    assert event["event_date"] == "2026-09-01"
    assert event["days_until"] == 18
    assert event["impact_ratio"] == pytest.approx(linked["impact_ratio"])
    assert "event_calendar" in table_ids


def test_event_pointing_at_unknown_scenario_is_rejected() -> None:
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    broken = replace(
        reference,
        events=(replace(reference.events[0], scenario_id="no_such_scenario"),),
    )

    assert any(
        issue.startswith("unknown scenario for event")
        for issue in validate_analysis_reference(broken)
    )


def test_missing_events_key_produces_no_calendar_widget() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = replace(load_analysis_reference(EXAMPLE_REFERENCE), events=())
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )

    assert artifact["snapshot"]["datasets"]["event_calendar"] == []
    assert "event_calendar" not in {table["id"] for table in artifact["manifest"]["tables"]}
    assert "event_calendar" not in {
        target["dataset"] for target in artifact["manifest"]["filters"][0]["targets"]
    }


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
    assert impacts["株式全体 -10%"] == pytest.approx(-0.07934, rel=1e-4)
    assert impacts["円10%上昇（外貨バスケット）"] == pytest.approx(-0.05323, rel=1e-4)
    assert summary["worst_compound_drawdown"] == pytest.approx(0.17661, rel=1e-4)
    # Replayed history is worse than every hand-set compound scenario.
    assert summary["worst_historical_drawdown"] == pytest.approx(0.23459, rel=1e-4)
    assert summary["worst_historical_drawdown"] > summary["worst_compound_drawdown"]
    assert issuers["Advantest"] == pytest.approx(0.16588, rel=1e-4)
    smh_market_loading = next(
        row["loading"]
        for row in datasets["factor_loadings"]
        if row["scope"] == "すべて"
        and row["position"].startswith("SMH ·")
        and row["factor"] == "株式全体"
    )
    assert smh_market_loading == pytest.approx(1.9)


@PRIVATE_ANALYSIS_ONLY
def test_phase_a_scenarios_are_registered_and_linear_in_their_components() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    impacts = {
        row["scenario"]: row["impact_jpy"]
        for row in artifact["snapshot"]["datasets"]["factor_sensitivity"]
        if row["scope"] == "すべて"
    }

    for label in (
        "A1 複合: スタグフレーション型（株安＋金利上昇）",
        "A2 複合: 台湾サプライチェーン混乱",
        "A3 複合: 円高ショック大（介入・金利差収斂）",
        "A4 複合: AI決算失望",
        "A5 複合: 原油供給ショック",
    ):
        assert label in impacts

    # A1 shocks equity -10%, JGB +75bp, foreign rates +50bp, real estate -10%.
    # Each component must equal the matching single-factor scenario, scaled linearly.
    expected_a1 = (
        impacts["株式全体 -10%"]
        + impacts["日本金利 +100bp"] * 0.75
        + impacts["海外金利 +100bp"] * 0.5
        + impacts["不動産 -20%"] * 0.5
    )
    assert impacts["A1 複合: スタグフレーション型（株安＋金利上昇）"] == pytest.approx(expected_a1)
    # A5 lifts energy, so the oil sleeve must offset part of the equity and rate damage.
    assert impacts["A5 複合: 原油供給ショック"] > impacts["A1 複合: スタグフレーション型（株安＋金利上昇）"]


@PRIVATE_ANALYSIS_ONLY
def test_replayed_history_is_tracked_separately_from_hand_set_scenarios() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
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
    kinds = {row["scenario"]: row["scenario_kind"] for row in rows}
    measured = {row["scenario"]: row["impact_ratio"] for row in rows if row["scenario_kind"] == "実測"}

    assert kinds["株式全体 -10%"] == "単一"
    assert kinds["A1 複合: スタグフレーション型（株安＋金利上昇）"] == "複合"
    assert len(measured) == 4
    # 2022 was an inflation regime: the energy sleeve carried the portfolio up.
    assert measured["実測 2022 インフレ・金利ショック"] > 0
    assert measured["実測 2020-03 コロナ・ショック"] < -0.2


def test_historical_scenarios_do_not_feed_the_compound_drawdown_metric() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    compound_only = build_artifact(
        portfolio,
        analysis_reference=reference,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    with_history = build_artifact(
        portfolio,
        analysis_reference=replace(
            reference,
            scenarios=(
                *reference.scenarios,
                replace(
                    reference.scenarios[0],
                    id="historical_sample",
                    label="実測サンプル",
                    kind="historical",
                    shocks={"株式全体": Decimal("-0.30")},
                ),
            ),
        ),
        generated_at="2026-08-15T00:00:00+00:00",
    )
    before = next(r for r in compound_only["snapshot"]["datasets"]["summary"] if r["scope"] == "すべて")
    after = next(r for r in with_history["snapshot"]["datasets"]["summary"] if r["scope"] == "すべて")

    assert before["worst_historical_drawdown"] is None
    assert after["worst_compound_drawdown"] == pytest.approx(before["worst_compound_drawdown"])
    assert after["worst_historical_drawdown"] > after["worst_compound_drawdown"]


def _diagonal_risk(variances: dict[str, str]) -> FactorRisk:
    factors = tuple(variances)
    return FactorRisk(
        factors=factors,
        covariance=tuple(
            tuple(Decimal(variances[row]) if row == column else Decimal() for column in factors)
            for row in factors
        ),
        observations=100,
        frequency="weekly",
        estimated_at="2026-08-15T00:00:00+00:00",
        window_start="2023-08-15",
    )


def test_most_plausible_shock_matches_the_analytic_solution() -> None:
    risk = _diagonal_risk({"a": "0.04", "b": "0.01"})
    exposures = {"a": Decimal("100"), "b": Decimal("100")}

    shocks, distance = most_plausible_shock(exposures, risk, Decimal("10"))

    # Sigma b = (4, 1) and b'Sigma b = 500, so s = -10 * (4, 1) / 500.
    assert shocks["a"] == pytest.approx(Decimal("-0.08"))
    assert shocks["b"] == pytest.approx(Decimal("-0.02"))
    assert float(distance) == pytest.approx(10 / 500**0.5)


def test_most_plausible_shock_satisfies_the_loss_constraint() -> None:
    risk = _diagonal_risk({"a": "0.04", "b": "0.01", "c": "0.0009"})
    exposures = {"a": Decimal("3000000"), "b": Decimal("-500000"), "c": Decimal("1200000")}
    target = Decimal("2500000")

    shocks, _ = most_plausible_shock(exposures, risk, target)
    realised = sum(exposures[factor] * shock for factor, shock in shocks.items())

    assert float(realised) == pytest.approx(float(-target))


def test_most_plausible_shock_loads_the_factor_that_moves_the_portfolio_most() -> None:
    risk = _diagonal_risk({"loud": "0.04", "quiet": "0.04"})
    shocks, _ = most_plausible_shock(
        {"loud": Decimal("1000"), "quiet": Decimal("10")}, risk, Decimal("100")
    )

    assert abs(shocks["loud"]) > abs(shocks["quiet"]) * 50


def test_most_plausible_shock_returns_nothing_without_exposure() -> None:
    risk = _diagonal_risk({"a": "0.04"})

    assert most_plausible_shock({"a": Decimal()}, risk, Decimal("100")) == ({}, Decimal())


def test_validate_factor_risk_rejects_an_asymmetric_covariance() -> None:
    risk = FactorRisk(
        factors=("a", "b"),
        covariance=(
            (Decimal("0.04"), Decimal("0.01")),
            (Decimal("0.02"), Decimal("0.04")),
        ),
        observations=100,
        frequency="weekly",
        estimated_at="",
        window_start="",
    )

    assert any(issue.startswith("covariance is not symmetric") for issue in validate_factor_risk(risk))


def test_tracked_factor_estimates_load_and_validate() -> None:
    risk = load_factor_risk(FACTOR_ESTIMATES)

    assert validate_factor_risk(risk) == []
    assert risk.frequency == "weekly"
    assert "株式全体" in risk.factors


def test_reverse_stress_appears_only_when_measured_risk_is_supplied() -> None:
    portfolio = load_portfolio(EXAMPLE_DATA)
    reference = load_analysis_reference(EXAMPLE_REFERENCE)
    risk = load_factor_risk(FACTOR_ESTIMATES)
    without = build_artifact(
        portfolio, analysis_reference=reference, generated_at="2026-08-15T00:00:00+00:00"
    )
    with_risk = build_artifact(
        portfolio,
        analysis_reference=reference,
        factor_risk=risk,
        generated_at="2026-08-15T00:00:00+00:00",
    )

    assert "reverse_stress" not in without["snapshot"]["datasets"]
    assert "reverse_stress" not in {table["id"] for table in without["manifest"]["tables"]}
    assert "reverse_stress" in with_risk["snapshot"]["datasets"]


@PRIVATE_ANALYSIS_ONLY
def test_reverse_stress_reproduces_each_policy_drawdown_limit() -> None:
    portfolio = load_portfolio(PRIVATE_DATA)
    reference = load_analysis_reference(PRIVATE_REFERENCE)
    risk = load_factor_risk(FACTOR_ESTIMATES)
    artifact = build_artifact(
        portfolio,
        analysis_reference=reference,
        factor_risk=risk,
        generated_at="2026-08-15T00:00:00+00:00",
    )
    summary = next(
        row for row in artifact["snapshot"]["datasets"]["summary"] if row["scope"] == "すべて"
    )
    rows = [row for row in artifact["snapshot"]["datasets"]["reverse_stress"] if row["scope"] == "すべて"]

    assert rows
    for limit in {row["limit"] for row in rows}:
        group = [row for row in rows if row["limit"] == limit]
        # Every solved shock set must add back up to exactly the target loss.
        assert sum(row["loss_share"] for row in group) == pytest.approx(1.0)
        assert len({row["distance_sigma"] for row in group}) == 1
    assert summary["nearest_limit_distance_sigma"] == pytest.approx(
        min(row["distance_sigma"] for row in rows)
    )
    assert summary["factor_annual_volatility"] == pytest.approx(
        summary["factor_period_volatility"] * 52**0.5
    )


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
