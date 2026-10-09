"""Offline tests for the daily risk monitor."""

from __future__ import annotations

import math

import pytest
from portfolio_analyzer import risk


def test_missing_fitted_factor_is_unknown_instead_of_an_implicit_zero_loading() -> None:
    from decimal import Decimal

    from portfolio_analyzer.core import FactorRisk, validate_factor_risk

    model = FactorRisk(
        factors=("equity", "fx"),
        covariance=((Decimal("0.01"), Decimal(0)), (Decimal(0), Decimal("0.01"))),
        observations=10,
        frequency="weekly",
        estimated_at="2026-10-08",
        window_start="2023-10-08",
        measured_basis="joint-jpy-excess-v1",
        instrument_loadings={"TEST": {"equity": Decimal(1)}},
    )
    holding = risk.Holding("TEST", "broker", 1000.0, "USD", "米国株", "TEST")
    reference = {"scenarios": [{"id": "fx", "kind": "historical", "shocks": {"fx": 0.1}}]}
    result = risk.scenario_impacts([holding], reference, factor_risk=model)[0]
    assert result["impact_jpy"] is None
    assert result["coverage"] == 0.0 and result["reason"]
    assert validate_factor_risk(model)


def test_missing_fund_history_does_not_become_zero_risk_for_the_whole_portfolio() -> None:
    book = [
        risk.Holding("A", "broker", 100.0, "JPY", "日本株", "A"),
        risk.Holding("FUND", "dc", 100.0, "JPY", "バランス型", None),
    ]
    dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
    result = risk.assemble(
        book,
        {},
        {"A": [0.1, -0.1, 0.1, -0.1]},
        {},
        dates,
        {"A": [100.0, 90.0, 99.0, 89.1]},
        dates[-1],
    )
    assert result["stats"]["var_1d_95"] is None
    assert result["stats"]["vol_annual"] is None
    assert result["stats"]["coverage_ratio"] == 0.5
    assert "FUND" in result["stats"]["reason"]
    assert result["contributions"]["positions"] == []


REFERENCE = {
    "instruments": [
        {
            "symbol": "SMH",
            "country_default": "米国",
            "factor_loadings": {"株式全体": 1.9, "海外株": 1, "情報技術": 1.0, "外貨対円": 1},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 1.0},
                {"group": "issuer", "category": "Nvidia", "weight": 0.2, "country": "米国"},
                {
                    "group": "issuer",
                    "category": "Taiwan Semiconductor Manufacturing",
                    "weight": 0.1,
                    "country": "台湾",
                },
            ],
        },
        {
            "symbol": "1329",
            "country_default": "日本",
            "factor_loadings": {"株式全体": 1.0, "日本株": 1, "情報技術": 0.35},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 0.35},
                {"group": "sector", "category": "その他・未分類株式", "weight": 0.65},
                {"group": "issuer", "category": "Advantest", "weight": 0.12, "country": "日本"},
            ],
        },
        {
            "symbol": "6857",
            "country_default": "日本",
            "factor_loadings": {"株式全体": 1.5, "日本株": 1, "情報技術": 1.0},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 1.0},
                {"group": "issuer", "category": "Advantest", "weight": 1.0, "country": "日本"},
            ],
        },
        {
            "symbol": "FUND",
            "asset_mix": {"日本株": 0.3, "海外株": 0.2, "日本債券": 0.5},
            "currency_mix": {"JPY": 0.8, "USD": 0.2},
            "country_mix": {"日本": 0.8, "米国": 0.2},
            "factor_loadings": {"株式全体": 0.5, "日本金利": -2.0, "外貨対円": 0.2},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 0.1},
                {"group": "sector", "category": "その他・未分類株式", "weight": 0.4},
                {"group": "asset", "category": "日本債券", "weight": 0.5},
            ],
        },
    ],
    "scenarios": [
        {"id": "global_equity_down_10", "label": "株式全体 -10%", "shocks": {"株式全体": -0.1}},
        {
            "id": "compound_x",
            "label": "複合",
            "kind": "compound",
            "shocks": {"株式全体": -0.1, "外貨対円": -0.1},
        },
        {"id": "hist_x", "label": "過去", "kind": "historical", "shocks": {"株式全体": -0.2}},
    ],
    "policy": {
        "limits": [
            {
                "id": "single_position_max",
                "label": "単一10%",
                "metric": "largest_position_ratio",
                "operator": "<=",
                "threshold": 0.1,
            },
            {
                "id": "cash_min",
                "label": "現金15%",
                "metric": "cash_ratio",
                "operator": ">=",
                "threshold": 0.15,
            },
            {
                "id": "sectors_min",
                "label": "実効セクター数 1.4 以上",
                "metric": "sector_effective_count",
                "operator": ">=",
                "threshold": 1.4,
            },
            {
                "id": "hist_dd_max",
                "label": "過去局面の下落 20% 以下",
                "metric": "worst_historical_drawdown",
                "operator": "<=",
                "threshold": 0.2,
            },
        ],
        "daily_limits": [
            {
                "id": "na_metric",
                "label": "無い指標",
                "metric": "does_not_exist",
                "operator": "<=",
                "threshold": 1,
            },
        ],
    },
    "episodes": [{"id": "ep", "label": "局面", "start": "2026-01-03", "end": "2026-01-05"}],
}


def holdings():
    return [
        risk.Holding("SMH", "gb", 600.0, "USD", "米国株", "SMH"),
        risk.Holding("1329", "sec", 200.0, "JPY", "日本株", "1329.T"),
        risk.Holding("6857", "sec", 100.0, "JPY", "日本株", "6857.T"),
        risk.Holding("FUND", "dc", 100.0, "JPY", "バランス型", "F:1"),
        risk.Holding("CASH_JPY", "sec", 1000.0, "JPY", "現金"),
    ]


def _value(rows, label):
    return next(r["value"] for r in rows if r["label"] == label)


def test_lookthrough_sums_back_to_the_total_in_every_dimension() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert x["total"] == 2000.0
    for key in ("asset_class", "currency", "country", "sector"):
        assert math.isclose(sum(r["value"] for r in x[key]), 2000.0), key


def test_lookthrough_currency_and_country_use_the_mixes_and_the_issuers() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["currency"], "USD") == 600.0 + 20.0  # SMH plus the fund's dollar part
    assert _value(x["currency"], "JPY") == 2000.0 - 620.0
    assert _value(x["country"], "台湾") == 60.0  # TSMC through SMH
    assert _value(x["country"], "米国") == 600.0 * 0.9 + 20.0  # the rest of SMH plus the fund
    assert _value(x["country"], "日本") == 200.0 + 100.0 + 80.0 + 1000.0


def test_lookthrough_sector_puts_bonds_and_cash_in_their_own_bucket() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["sector"], risk.NON_EQUITY_SECTOR) == 1000.0 + 50.0
    assert _value(x["sector"], "情報技術") == 600.0 + 70.0 + 100.0 + 10.0


def test_lookthrough_asset_class_uses_the_fund_s_mix_and_the_snapshot_class_otherwise() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["asset_class"], "日本債券") == 50.0
    assert _value(x["asset_class"], "日本株") == 300.0 + 30.0
    assert _value(x["asset_class"], "現金") == 1000.0


def test_lookthrough_merges_an_issuer_held_directly_and_through_a_fund() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    adv = next(r for r in x["issuers"] if r["label"] == "Advantest")
    assert adv["value"] == 100.0 + 24.0 and adv["via"] == ["6857", "1329"]
    assert x["issuers"][0]["label"] == "Advantest"  # the largest look-through name
    assert x["mix"]["SMH"]["country"] == pytest.approx({"米国": 0.9, "台湾": 0.1})


def test_the_same_symbol_in_two_accounts_is_one_position() -> None:
    # 1329 held at two brokers is one name's worth of concentration, not two
    rows = [*holdings(), risk.Holding("1329", "gb", 200.0, "JPY", "日本株", "1329.T")]
    x = risk.lookthrough(rows, REFERENCE)
    c = risk.concentration(rows, x)
    assert c["largest_position_ratio"] == 600.0 / 2200.0  # SMH, still the largest
    assert math.isclose(c["top5_ratio"], (600.0 + 400.0 + 100.0 + 100.0) / 2200.0)
    merged = 1.0 / sum((v / 1200.0) ** 2 for v in (600.0, 400.0, 100.0, 100.0))
    split = 1.0 / sum((v / 1200.0) ** 2 for v in (600.0, 200.0, 200.0, 100.0, 100.0))
    assert math.isclose(c["effective_positions"], merged)
    assert merged < split  # counting the two lots apart would look more diversified than it is


def test_concentration_metrics() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    c = risk.concentration(holdings(), x)
    assert c["largest_position_ratio"] == 0.3 and c["top5_ratio"] == 0.5
    assert c["cash_ratio"] == 0.5
    assert math.isclose(c["foreign_currency_ratio"], 620.0 / 2000.0)
    assert c["largest_foreign_country"] == "米国"
    assert math.isclose(c["largest_foreign_country_ratio"], 560.0 / 2000.0)
    assert c["largest_issuer"] == "Advantest"
    assert math.isclose(c["largest_issuer_lookthrough_ratio"], 124.0 / 2000.0)
    assert c["max_sector"] == "情報技術" and math.isclose(c["max_sector_ratio"], 780.0 / 2000.0)
    # effective sectors: 1 / HHI over the equity sectors only
    tech, other = 780.0, 150.0 + 20.0
    equity = tech + other
    assert math.isclose(c["effective_sectors"], 1 / ((tech / equity) ** 2 + (other / equity) ** 2))


def test_portfolio_returns_weight_each_day_and_skip_tickers_without_returns() -> None:
    rs = risk.portfolio_returns(
        {"A": 0.5, "B": 0.25, "CASH": 0.25}, {"A": [0.02, -0.01], "B": [0.0, 0.04]}
    )
    assert rs == pytest.approx([0.01, 0.005])


def test_volatility_var_and_es_on_a_known_sample() -> None:
    rs = [0.01, -0.02, 0.015, -0.03, 0.005, 0.0, -0.01, 0.02, -0.005, 0.025]
    # mean 0.001, sum of squared deviations 0.00279, sample variance over n−1 = 9
    assert risk.volatility(rs) == pytest.approx(math.sqrt(0.00279 / 9 * 252))
    assert risk.quantile(sorted(rs), 0.5) == pytest.approx(0.0025)
    # the 5% quantile sits between the worst two days (pos 0.45), interpolated
    assert risk.value_at_risk(rs, 0.95) == pytest.approx(0.0255)
    # the 10% quantile is −0.021, so only the worst day is in the tail
    assert risk.expected_shortfall(rs, 0.90) == pytest.approx(0.03)
    assert risk.volatility([0.01]) is None and risk.value_at_risk([], 0.95) is None


def test_beta_recovers_a_known_slope() -> None:
    bench = [0.01, -0.02, 0.03, 0.0, -0.01]
    port = [2 * b + 0.001 for b in bench]
    assert risk.beta(port, bench) == pytest.approx(2.0)
    assert risk.beta(port, [0.0] * 5) is None


def test_risk_contributions_sum_to_one_and_follow_the_covariance() -> None:
    returns = {
        "A": [0.01, -0.01, 0.02, -0.02],
        "B": [0.01, -0.01, 0.02, -0.02],
        "C": [0.0, 0.0, 0.0, 0.0],
    }
    rc = risk.risk_contributions({"A": 0.5, "B": 0.25, "C": 0.25}, returns)
    assert sum(rc.values()) == pytest.approx(1.0)
    assert rc["A"] == pytest.approx(2 / 3) and rc["B"] == pytest.approx(1 / 3) and rc["C"] == 0.0


def test_scenario_impacts_apply_the_factor_loadings() -> None:
    out = risk.scenario_impacts(holdings(), REFERENCE)
    by_id = {r["id"]: r for r in out}
    # 株式全体 −10%: SMH 600×1.9 + 1329 200×1.0 + 6857 100×1.5 + FUND 100×0.5 = 1540 → −154
    assert by_id["global_equity_down_10"]["impact_jpy"] == pytest.approx(-154.0)
    assert by_id["global_equity_down_10"]["impact_pct"] == pytest.approx(-154.0 / 2000.0)
    assert by_id["compound_x"]["kind"] == "compound"
    assert by_id["compound_x"]["impact_jpy"] == pytest.approx(-154.0 - 0.1 * (600 * 1 + 100 * 0.2))
    calculated = [r for r in out if r["impact_jpy"] is not None]
    assert calculated[0]["impact_jpy"] <= calculated[-1]["impact_jpy"]
    assert out[-1]["impact_jpy"] is None


def test_episode_impacts_replay_the_move_from_the_close_before_the_start() -> None:
    dates = ["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06"]
    prices = {
        "SMH": [100.0, 90.0, 85.0, 80.0, 95.0],
        "1329.T": [10.0, 10.0, 9.0, 9.5, 9.0],
        "F:1": [None] * 5,
    }
    values = {"SMH": 600.0, "1329.T": 200.0, "F:1": 100.0}
    out = risk.episode_impacts(values, REFERENCE["episodes"], dates, prices)
    (ep,) = out
    assert ep["impact_jpy"] == pytest.approx(600.0 * (80 / 100 - 1) + 200.0 * (9.5 / 10 - 1))
    assert ep["coverage"] == pytest.approx(800.0 / 900.0)
    # A configured episode outside the history stays visibly uncalculated.
    old = [{"id": "old", "label": "x", "start": "2025-01-01", "end": "2025-01-05"}]
    (unknown,) = risk.episode_impacts({"SMH": 1.0}, old, dates, prices)
    assert unknown["impact_jpy"] is None and unknown["complete"] is False
    assert unknown["reason"]


def test_evaluate_limits_reports_ok_breach_and_na() -> None:
    limits = [*REFERENCE["policy"]["limits"][:2], *REFERENCE["policy"]["daily_limits"]]
    rows = risk.evaluate_limits(limits, {"largest_position_ratio": 0.3, "cash_ratio": 0.5})
    status = {r["id"]: r["status"] for r in rows}
    assert status == {"single_position_max": "breach", "cash_min": "ok", "na_metric": "na"}
    assert rows[0]["value"] == 0.3 and rows[0]["threshold"] == 0.1


def test_assemble_builds_the_payload_block() -> None:
    dates = [f"2026-01-{d:02d}" for d in range(1, 11)]
    returns = {
        "SMH": [0.01, -0.02, 0.015, -0.03, 0.005, 0.0, -0.01, 0.02, -0.005, 0.025],
        "1329.T": [0.0] * 10,
        "6857.T": [0.0] * 10,
        "F:1": [0.0] * 10,
    }
    bench = {
        "topix": [0.0] * 10,
        "sp500": [0.005, -0.01, 0.0075, -0.015, 0.0025, 0.0, -0.005, 0.01, -0.0025, 0.0125],
        "usdjpy": [0.0] * 10,
    }
    prices = {t: [100.0] * 10 for t in returns}
    out = risk.assemble(
        holdings(),
        REFERENCE,
        returns,
        bench,
        dates,
        prices,
        "2026-01-10",
        previous={"vol_annual": 0.10},
    )
    assert out["as_of"] == "2026-01-10" and out["total"] == 2000.0
    assert out["exposures"]["currency"][0]["label"] in ("JPY", "USD")
    # SMH is 30% of assets and moves 2× the index; nothing else moves
    assert out["stats"]["beta"]["sp500"] == pytest.approx(2.0 * 0.3, rel=1e-6)
    assert out["stats"]["vol_annual"] > 0 and out["stats"]["var_1d_95_jpy"] > 0
    assert out["stats"]["prev"]["vol_annual"] == 0.10
    assert sum(r["risk_share"] for r in out["contributions"]["positions"]) == pytest.approx(1.0)
    assert sum(r["risk_share"] for r in out["contributions"]["currency"]) == pytest.approx(1.0)
    assert sum(r["risk_share"] for r in out["contributions"]["region"]) == pytest.approx(1.0)
    assert out["exposures"]["region"][0]["label"] == "日本"
    # policy.limits (the main dashboard's, under its metric names) plus policy.daily_limits
    status = {r["id"]: r["status"] for r in out["policy"]}
    assert status == {
        "single_position_max": "breach",
        "cash_min": "ok",
        "sectors_min": "ok",  # 1 / (0.821² + 0.179²) = 1.42 effective equity sectors
        "hist_dd_max": "na",  # measured replay requires compatible joint coefficients
        "na_metric": "na",
    }
    assert out["policy_breaches"] == 1
    assert out["stress"]["scenarios"][0]["id"] == "compound_x"
    assert out["stress"]["measured_factor_reason"]
    assert out["history"]["vol_annual"] == out["stats"]["vol_annual"]


def test_region_rolls_countries_and_fund_regions_into_one_taxonomy() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    # TSMC's Taiwan is an emerging market, as the fund's own 新興国 counts it
    assert _value(x["region"], "新興国") == 60.0
    assert _value(x["region"], "米国") == 600.0 * 0.9 + 20.0
    assert _value(x["region"], "日本") == 200.0 + 100.0 + 80.0 + 1000.0
    assert math.isclose(sum(r["value"] for r in x["region"]), 2000.0)
    assert {r["label"] for r in x["region"]} <= set(risk.REGIONS) | {"その他"}
    assert x["mix"]["SMH"]["region"] == pytest.approx({"米国": 0.9, "新興国": 0.1})


def test_the_single_country_limit_reads_countries_not_regions() -> None:
    reference = {
        "instruments": [
            {
                "symbol": "WORLD",
                "country_mix": {"日本": 0.2, "米国": 0.3, "欧州": 0.5},
                "exposures": [{"group": "sector", "category": "その他・未分類株式", "weight": 1.0}],
            },
            {
                "symbol": "ASML",
                "country_default": "オランダ",
                "exposures": [
                    {"group": "issuer", "category": "ASML", "weight": 1.0, "country": "オランダ"}
                ],
            },
        ]
    }
    hs = [
        risk.Holding("WORLD", "a", 1000.0, "JPY", "バランス型"),
        risk.Holding("ASML", "a", 100.0, "USD", "海外株"),
    ]
    c = risk.concentration(hs, risk.lookthrough(hs, reference))
    # 欧州 (550) is the largest foreign row but not a country: 米国 (300) is
    assert c["largest_foreign_country"] == "米国"
    assert math.isclose(c["largest_foreign_country_ratio"], 300.0 / 1100.0)
    # the effective count uses the regions, where the Netherlands has joined 欧州
    shares = [200.0 / 1100.0, 300.0 / 1100.0, 600.0 / 1100.0]
    assert math.isclose(c["effective_countries"], 1 / sum(s * s for s in shares))


def test_episode_replay_reports_losses_as_a_fraction_of_total_nav() -> None:
    hs = [
        risk.Holding("A", "a", 100.0, "JPY", "日本株", "A"),
        risk.Holding("CASH_JPY", "a", 100.0, "JPY", "現金"),
    ]
    reference = {"episodes": [{"id": "ep", "start": "2026-01-02", "end": "2026-01-03"}]}
    result = risk.assemble(
        hs,
        reference,
        {"A": [0.0, -0.05, -0.0526315789]},
        {},
        ["2026-01-01", "2026-01-02", "2026-01-03"],
        {"A": [100.0, 95.0, 90.0]},
        "2026-01-03",
    )
    episode = result["stress"]["episodes"][0]
    assert episode["impact_jpy"] == pytest.approx(-10.0)
    assert episode["impact_pct"] == pytest.approx(-0.05)


@pytest.mark.parametrize("returns", [[], [0.01]])
def test_risk_contribution_is_unavailable_without_two_observations(returns) -> None:
    assert risk.risk_contributions({"A": 1.0}, {"A": returns}) == {}


def test_historical_factor_replay_requires_compatible_joint_loadings() -> None:
    result = risk.scenario_impacts(holdings(), REFERENCE)
    historical = next(row for row in result if row["kind"] == "historical")
    assert historical["impact_jpy"] is None
    assert historical["impact_pct"] is None
    assert historical["reason"]
    assert next(row for row in result if row["id"] == "global_equity_down_10")["impact_jpy"] == -154


def test_joint_loadings_do_not_reapply_the_marginal_market_beta() -> None:
    from decimal import Decimal

    from portfolio_analyzer.core import FactorRisk

    factor_risk = FactorRisk(
        factors=("株式全体", "情報技術"),
        covariance=((Decimal(".01"), Decimal()), (Decimal(), Decimal(".01"))),
        observations=10,
        frequency="weekly",
        estimated_at="",
        window_start="",
        measured_basis="joint-jpy-excess-v1",
        instrument_loadings={"SMH": {"株式全体": Decimal(1), "情報技術": Decimal(1)}},
    )
    reference = {
        "instruments": REFERENCE["instruments"],
        "scenarios": [
            {
                "id": "measured",
                "kind": "historical",
                "shocks": {"株式全体": -0.1, "情報技術": -0.09},
            }
        ],
    }
    result = risk.scenario_impacts(
        [risk.Holding("SMH", "a", 100, "USD", "米国株")], reference, factor_risk=factor_risk
    )
    assert result[0]["impact_jpy"] == pytest.approx(-19)
    assert result[0]["impact_pct"] == pytest.approx(-0.19)


def _measured_test_model(loadings=None):
    from decimal import Decimal

    from portfolio_analyzer.core import FactorRisk

    return FactorRisk(
        factors=("market",),
        covariance=((Decimal(".01"),),),
        observations=10,
        frequency="weekly",
        estimated_at="",
        window_start="",
        series=((Decimal("-.1"),), (Decimal(".05"),)),
        measured_basis="joint-jpy-excess-v1",
        instrument_loadings=loadings if loadings is not None else {"A": {"market": Decimal(1)}},
    )


def test_reconciliation_is_static_in_measured_shocks_and_price_statistics() -> None:
    from decimal import Decimal

    book = [
        risk.Holding("A", "broker", 100, "JPY", "日本株", "A"),
        risk.Holding("RECONCILIATION", "broker", 50, "JPY", "未分類", "ADJ"),
        risk.Holding("CASH_JPY", "broker", 50, "JPY", "現金"),
    ]
    reference = {"scenarios": [{"id": "history", "kind": "historical", "shocks": {"market": -0.1}}]}
    model = _measured_test_model(
        {"A": {"market": Decimal(1)}, "RECONCILIATION": {"market": Decimal(9)}}
    )
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    result = risk.assemble(
        book,
        reference,
        {"A": [0.1, -0.1, 0.1], "ADJ": [None] * 3},
        {},
        dates,
        {},
        dates[-1],
        factor_risk=model,
    )
    assert result["stress"]["scenarios"][0]["impact_jpy"] == pytest.approx(-10)
    assert result["stress"]["scenarios"][0]["impact_pct"] == pytest.approx(-0.05)
    assert result["stats"]["var_1d_95"] == pytest.approx(0.04)  # existing interpolated 95% quantile
    assert [row["ticker"] for row in result["contributions"]["positions"]] == ["A"]


@pytest.mark.parametrize("with_cash", [False, True])
def test_only_static_balances_need_no_measured_calibration(with_cash) -> None:
    book = [risk.Holding("RECONCILIATION", "broker", 50, "JPY", "未分類")]
    if with_cash:
        book.append(risk.Holding("CASH_JPY", "broker", 50, "JPY", "現金"))
    result = risk.scenario_impacts(
        book, {"scenarios": [{"id": "history", "kind": "historical", "shocks": {"market": -0.5}}]}
    )[0]
    assert result["impact_jpy"] == 0 and result["impact_pct"] == 0
    assert result["reason"] == ""


def test_foreign_cash_is_not_a_static_jpy_balance() -> None:
    book = [risk.Holding("CASH_USD", "broker", 100, "USD", "現金")]
    result = risk.scenario_impacts(
        book,
        {"scenarios": [{"id": "fx", "kind": "historical", "shocks": {"market": -0.1}}]},
        factor_risk=_measured_test_model(),
    )[0]
    assert result["impact_jpy"] is None and "CASH_USD" in result["reason"]


@pytest.mark.parametrize("known_loss, expected_status", [(0.1, "na"), (0.3, "breach")])
def test_unknown_historical_scenario_prevents_safe_policy_but_preserves_proven_breach(
    known_loss, expected_status
) -> None:
    reference = {
        "scenarios": [
            {"id": "known", "kind": "historical", "shocks": {"market": -known_loss}},
            {"id": "unknown", "kind": "historical", "shocks": {"unavailable": -0.9}},
        ],
        "policy": {
            "limits": [
                {
                    "id": "dd",
                    "metric": "worst_historical_drawdown",
                    "operator": "<=",
                    "threshold": 0.2,
                }
            ]
        },
    }
    book = [risk.Holding("A", "broker", 100, "JPY", "日本株", "A")]
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    result = risk.assemble(
        book,
        reference,
        {"A": [0.1, -0.1, 0.1]},
        {},
        dates,
        {},
        dates[-1],
        factor_risk=_measured_test_model(),
    )
    check = result["policy"][0]
    assert check["value"] is None and check["status"] == expected_status
    assert check["lower_bound_value"] == pytest.approx(known_loss)
    assert check["reason"]


@pytest.mark.parametrize("ratios", [[-0.1, None], [None, None]])
def test_worst_requires_every_configured_scenario(ratios) -> None:
    assert (
        risk._worst([{"kind": "historical", "impact_pct": value} for value in ratios], "historical")
        is None
    )


def test_partial_episode_profit_and_total_loss_are_distinct() -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    episode = {"id": "partial", "start": dates[1], "end": dates[-1]}
    row = risk.episode_impacts(
        {"A": 100, "B": 100}, [episode], dates, {"A": [100, 90, 90], "B": [None] * 3}, total_nav=250
    )[0]
    assert row["impact_jpy"] == pytest.approx(-10)  # existing partial-price contract
    assert row["coverage"] == 0.5 and row["priced_nav_ratio"] == 0.4
    assert row["total_impact_jpy"] is None and row["total_impact_pct"] is None
    assert row["complete"] is False and row["reason"]


@pytest.mark.parametrize("known_loss, expected_status", [(0.1, "na"), (0.3, "breach")])
def test_unknown_episode_is_retained_with_unknown_total_loss(known_loss, expected_status) -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    reference = {
        "episodes": [
            {"id": "known", "start": dates[1], "end": dates[-1]},
            {"id": "old", "start": "2025-01-01", "end": "2025-01-03"},
        ],
        "policy": {
            "limits": [
                {
                    "id": "dd",
                    "metric": "worst_historical_drawdown",
                    "operator": "<=",
                    "threshold": 0.2,
                }
            ]
        },
    }
    book = [risk.Holding("A", "broker", 100, "JPY", "日本株", "A")]
    result = risk.assemble(
        book,
        reference,
        {"A": [0.1, -0.1, 0.1]},
        {},
        dates,
        {"A": [100, 90, 100 * (1 - known_loss)]},
        dates[-1],
    )
    episodes = {row["id"]: row for row in result["stress"]["episodes"]}
    assert episodes["old"]["complete"] is False and episodes["old"]["reason"]
    assert episodes["old"]["total_impact_pct"] is None
    assert episodes["known"]["complete"] is True
    assert episodes["known"]["total_impact_pct"] == pytest.approx(-known_loss)
    assert result["policy"][0]["status"] == "na"  # policy uses configured factor scenarios only


@pytest.mark.parametrize("bad_history", [[0.1, None, -0.1], [0.1, math.nan, -0.1], [0.1, -0.1]])
def test_missing_or_short_returns_invalidate_the_requested_risk_window(bad_history) -> None:
    book = [
        risk.Holding("A", "broker", 100, "JPY", "日本株", "A"),
        risk.Holding("B", "broker", 100, "JPY", "日本株", "B"),
    ]
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    result = risk.assemble(
        book, {}, {"A": [0.1, -0.1, 0.1], "B": bad_history}, {}, dates, {}, dates[-1]
    )
    assert result["stats"]["vol_annual"] is None and result["stats"]["es_1d_975"] is None
    assert result["stats"]["coverage_ratio"] == 0.5 and "B" in result["stats"]["reason"]
    assert result["contributions"]["positions"] == []


def test_missing_benchmark_is_unknown_without_hiding_valid_price_risk() -> None:
    book = [risk.Holding("A", "broker", 100, "JPY", "日本株", "A")]
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    result = risk.assemble(
        book,
        {},
        {"A": [0.1, -0.1, 0.1]},
        {"broken": [0.1, None, 0.1], "valid": [0.1, -0.1, 0.1]},
        dates,
        {},
        dates[-1],
    )
    assert result["stats"]["var_1d_95"] == pytest.approx(0.08)
    assert result["stats"]["beta"]["broken"] is None
    assert result["stats"]["beta"]["valid"] == pytest.approx(1)
    assert result["stats"]["beta_reasons"]["broken"]


def test_episode_with_no_observed_price_is_unknown_instead_of_zero_pnl() -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    episode = {"id": "empty", "start": dates[1], "end": dates[-1]}
    row = risk.episode_impacts({"A": 100}, [episode], dates, {"A": [None] * 3})[0]
    assert row["impact_jpy"] is None and row["impact_pct"] is None
    assert row["total_impact_jpy"] is None and row["complete"] is False
    assert row["reason"]
