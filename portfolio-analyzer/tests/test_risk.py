"""Offline tests for the daily risk monitor."""

from __future__ import annotations

import math

import pytest
from portfolio_analyzer import risk

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
    assert out[0]["impact_jpy"] <= out[-1]["impact_jpy"]


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
    # an episode the history does not reach is left out
    old = [{"id": "old", "label": "x", "start": "2025-01-01", "end": "2025-01-05"}]
    assert risk.episode_impacts({"SMH": 1.0}, old, dates, prices) == []


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
        "hist_dd_max": "ok",  # the historical scenario loses 308 of 2000 = 15.4%
        "na_metric": "na",
    }
    assert out["policy_breaches"] == 1
    assert out["stress"]["scenarios"][0]["id"] == "hist_x"
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
