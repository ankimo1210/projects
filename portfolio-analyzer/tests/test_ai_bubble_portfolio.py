"""Holdings impact of the AI-bubble scenarios (spec 8.1) and the registered labels (spec 8)."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.funding import f_classify
from portfolio_analyzer.ai_bubble.history import s_classify
from portfolio_analyzer.ai_bubble.portfolio import (
    fx_compose,
    idiosyncratic_layer,
    issuer_exposure,
    lookthrough_paths,
    parse_h10,
    repricing_change,
    systematic_layer,
)
from portfolio_analyzer.ai_bubble.valuation import v_classify


def path(symbol, issuer, value, currency="USD", hedge=0.0):
    return {
        "position_symbol": symbol,
        "issuer_id": issuer,
        "value_jpy": value,
        "economic_currency": currency,
        "fx_hedge_ratio": hedge,
        "as_of": "2026-10-20",
    }


def test_a_direct_holding_and_a_fund_stake_add_up_by_issuer_without_renormalising():
    paths = [
        path("A", "A", 20.0),
        *lookthrough_paths(
            "ETF",
            80.0,
            {"A": 0.25, "B": 0.55},
            economic_currency="USD",
            fx_hedge_ratio=0.0,
            as_of="2026-07-31",
        ),
    ]
    out = issuer_exposure(paths)
    assert out["issuers"]["A"]["value_jpy"] == pytest.approx(40.0)
    assert out["issuers"]["B"]["value_jpy"] == pytest.approx(44.0)
    assert out["unknown_jpy"] == pytest.approx(16.0)
    assert out["total_jpy"] == pytest.approx(100.0)
    assert sorted(p["position_symbol"] for p in out["issuers"]["A"]["paths"]) == ["A", "ETF"]


def test_local_and_currency_returns_compound_into_yen():
    assert fx_compose(-0.30, -0.10) == pytest.approx(-0.37)
    assert fx_compose(-0.30, 0.0) == pytest.approx(-0.30)


def test_repricing_changes_equity_with_net_debt_held_fixed():
    assert repricing_change(125.0, 25.0, 80.0) == pytest.approx(-0.45)
    assert repricing_change(125.0, 25.0, 125.0) == 0.0
    assert repricing_change(20.0, 25.0, 30.0) is None
    assert repricing_change(125.0, 25.0, 10.0) == -1.0  # equity cannot go below zero


def test_the_layer_discounts_every_scenario_at_the_central_implied_rate():
    flows = {"central": 10.0, "optimistic": 12.5, "stress": 8.0}

    def value_at(kind, r):
        return flows[kind] / r  # perpetuity, g = 0

    out = idiosyncratic_layer(125.0, 25.0, value_at, shift=0.02, bounds=(0.04, 0.30))
    assert out["status"] == "ok"
    assert out["r_star"] == pytest.approx(0.08)
    assert out["change"]["central"] == pytest.approx(0.0)
    assert out["change"]["optimistic"] == pytest.approx((12.5 / 0.08 - 25) / 100 - 1)
    assert out["change"]["stress"] == pytest.approx(-0.45)


def test_a_rate_outside_the_bounds_leaves_the_layer_unevaluated():
    out = idiosyncratic_layer(125.0, 25.0, lambda kind, r: 1.0 / r, shift=0.02, bounds=(0.04, 0.30))
    assert out["status"] == "unevaluated"
    assert out["change"] is None


def test_a_proxy_replays_the_episode_and_a_holding_without_one_is_unevaluated():
    episodes = [
        {"id": "dotcom", "label": "ITバブル崩壊", "start": "2000-03-24", "end": "2002-10-09"}
    ]
    out = systematic_layer(
        {"SEMI": 100.0, "BOND": 50.0},
        {"SEMI": "^SOX"},
        {"^SOX": [100.0, 60.0]},
        ["2000-03-23", "2002-10-09"],
        episodes,
    )
    assert out[0]["impact_jpy"] == pytest.approx(-40.0)
    assert out[0]["complete"] is False
    assert "BOND" in out[0]["reason"]


@pytest.mark.parametrize(
    ("central", "optimistic", "observed", "label"),
    [
        (90.0, 95.0, 100.0, "弱める"),
        (89.9, 89.9, 100.0, "支持"),
        (89.9, 90.0, 100.0, "混在"),
        (50.0, 50.0, 0.0, "保留"),
    ],
)
def test_the_v_boundary_is_ninety_percent_of_the_observed_ev(central, optimistic, observed, label):
    assert v_classify(central, optimistic, observed) == label


def test_f_and_s_put_missing_data_first():
    ok = {"status": "ok", "max_intra_shortfall": 5.0}
    assert f_classify({"status": "unevaluated"}, ok) == "データ不足"
    assert f_classify(ok, {"status": "ok", "max_intra_shortfall": 0.0}) == "支持"
    assert s_classify(None, 0.1, 0.2, crash_ci_low=0.3, unconditional=0.1) == "データ不足"


H10 = """<table><tr><th scope=col>Date</th><th scope=col>Rate</th></tr>
<tr>
<th id="r1" headers="a1"> 3-JAN-00 </th>
<td headers="a2 a1 r1">            101.7000                                                  </td>
</tr>
<tr>
<th id="r1" headers="a1"> 17-JAN-00 </th>
<td headers="a2 a1 r1">            ND                                                  </td>
</tr>
<tr>
<th id="r1" headers="a1"> 20-OCT-26 </th>
<td headers="a2 a1 r1">            151.2300                                                  </td>
</tr></table>"""


def test_the_fed_h10_table_gives_dated_yen_rates_with_holidays_missing():
    assert parse_h10(H10) == [("2000-01-03", 101.7), ("2000-01-17", None), ("2026-10-20", 151.23)]


def test_a_holding_falls_back_to_the_index_where_its_own_history_does_not_cover_the_episode():
    episodes = [
        {"id": "dotcom", "label": "ITバブル崩壊", "start": "2000-03-24", "end": "2002-10-09"},
        {"id": "rates2022", "label": "金利上昇", "start": "2021-11-19", "end": "2022-10-12"},
    ]
    out = systematic_layer(
        {"JP": 100.0},
        {"JP": "OWN"},
        {"OWN": [None, None, 50.0, 40.0], "IDX": [100.0, 80.0, 60.0, 30.0]},
        ["2000-03-23", "2002-10-09", "2021-11-18", "2022-10-12"],
        episodes,
        fallback_map={"JP": "IDX"},
    )
    by_id = {row["id"]: row for row in out}
    assert by_id["dotcom"]["impact_jpy"] == pytest.approx(-20.0)
    assert by_id["dotcom"]["proxies"] == {"JP": "IDX"}
    assert by_id["rates2022"]["impact_jpy"] == pytest.approx(-20.0)
    assert by_id["rates2022"]["proxies"] == {"JP": "OWN"}
