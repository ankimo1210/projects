"""Offline smoke tests for the dashboard renderer."""

from __future__ import annotations

from portfolio_analyzer import dashboard
from risk_fixture import risk_block


def sample() -> dict:
    dates = ["2026-09-09", "2026-09-10", "2026-09-11"]
    return {
        "as_of": "2026-09-11",
        "generated_at": "2026-09-12T07:30:00+09:00",
        "fx": {"last": 153.55, "chg_pct": -0.4, "date": "2026-09-11"},
        "window": {"start": "2025-09-11", "end": "2026-09-11", "days": 3},
        "headline": {
            "nav_total": 46257970,
            "quoted_value": 29170055,
            "day_pnl": -450566,
            "day_pnl_pct": -1.52,
            "unrealized_known": -165287,
            "pnl_window": 123456,
            "pnl_incept": 840870,
            "realized_cum": -580654,
            "dividends_net": 67706,
            "xirr": 0.0366,
            "max_dd_window": -0.05,
            "quoted_share": 0.63,
        },
        "accounts": [
            {
                "id": "gb",
                "name": "海外証券口座",
                "total": 25427872,
                "day_pnl": 57559,
                "unrealized": -165287,
            }
        ],
        "allocation": [
            {"label": "米国株", "value": 12210000, "pct": 26.4},
            {"label": "現金", "value": 9420000, "pct": 20.4},
        ],
        "tape": [{"sym": "XLE", "last": 65.14, "chg_pct": 0.32}],
        "positions": [
            {
                "sym": "XLE",
                "acct": "海外証券口座",
                "name": "Energy Select Sector SPDR Fund",
                "cls": "米国株",
                "cur": "USD",
                "qty": 500,
                "last": 65.14,
                "chg1d": 0.32,
                "chg1w": 1.0,
                "chg1m": 2.0,
                "chg1y": 20.0,
                "value": 5001254,
                "weight": 10.8,
                "day_pnl": 15506,
                "unreal": 648558,
                "unreal_pct": 14.9,
                "avg_cost": 53.865,
                "spark": [60, 62, 65.14],
            }
        ],
        "series": {
            "dates": dates,
            "nav": [25.0e6, 25.2e6, 25.4e6],
            "pnl": [0.0, 2.0e5, 4.0e5],
            "deposits": [25e6, 25e6, 25e6],
            "daily_pnl": [0.0, 2.0e5, 2.0e5],
            "symbols": {
                "XLE": {
                    "mode": "pnl",
                    "label": "含み損益",
                    "price": [60, 62, 65.14],
                    "pnl": [600000, 620000, 648558],
                    "trades": [{"i": 0, "qty": 500, "price": 53.865}],
                    "avg_cost": 53.865,
                    "cur": "USD",
                }
            },
        },
        "attribution": {
            "incept": {
                "unrealized": -165287,
                "realized": -580654,
                "dividends": 67706,
                "fees": -839,
                "fx_translation": 1077796,
                "forex": 7102,
                "total": 405724,
            },
            "window": {
                "unrealized": -165287,
                "realized": 0,
                "dividends": 30000,
                "fees": -100,
                "fx_translation": 0,
                "forex": 0,
                "total": -135387,
            },
        },
        "closed": [
            {
                "sym": "LLY",
                "first": "2024-11-01",
                "last": "2025-06-04",
                "realized": -175786,
                "trades": 2,
            }
        ],
        "notes": ["国内証券口座は取得原価未入力"],
        "risk": risk_block(),
    }


def test_render_dashboard_carries_headline_and_positions() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}")
    assert html.lower().startswith("<!doctype html>")
    assert (
        "46,257,970" in html and "2026-09-11" in html and "XLE" in html and "海外証券口座" in html
    )
    assert 'id="data"' in html and "--ink" in html
    assert "#" not in html.split("<style>")[0]  # no stray hex before the tokens block


def test_render_dashboard_splits_pnl_into_stock_and_fx() -> None:
    data = sample()
    data["headline"].update(day_stock=-470000, day_fx=19434, unreal_stock=-100000, unreal_fx=-65287)
    data["accounts"][0].update(
        day_stock=38125, day_fx=19434, unreal_stock=-100000, unreal_fx=-65287
    )
    data["positions"][0].update(day_stock=12000, day_fx=3506, unreal_stock=700000, unreal_fx=-51442)
    html = dashboard.render(data, ":root{--ink:#000}")
    for value in (
        "株 −470,000",
        "FX +19,434",
        "株 −100,000",
        "FX −65,287",
        "株 +38,125",
        "株 +12,000",
        "FX +3,506",
        "株 +700,000",
        "FX −51,442",
    ):
        assert value in html, value


def test_render_dashboard_carries_the_after_tax_estimate() -> None:
    data = sample()
    data["headline"].update(nav_after_tax=45000000, day_after_tax=-380000, unreal_after_tax=-131708)
    data["accounts"][0].update(day_after_tax=45866, unreal_after_tax=-131708, tax_rate=0.20315)
    data["positions"][0].update(day_after_tax=12356, unreal_after_tax=516803, tax_rate=0.20315)
    html = dashboard.render(data, ":root{--ink:#000}")
    for value in (
        "税引後 45,000,000",
        "税引後 −380,000",
        "税引後 −131,708",
        "税後 +45,866",
        "税後 +12,356",
        "税後 +516,803",
    ):
        assert value in html, value


def test_render_dashboard_shows_usd_under_yen() -> None:
    data = sample()
    data["headline"].update(nav_after_tax=45000000)
    html = dashboard.render(data, ":root{--ink:#000}")
    for value in (
        "$301,257",  # total assets at 153.55
        "税引後 45,000,000 · $293,064",
        "−$2,934",  # day
        "$165,600",  # account total
        "+$375",  # account day
        "$32,571",  # XLE value
        "+$101",  # XLE day
        "+$4,224",  # XLE unrealised
    ):
        assert value in html, value


def test_page_exposes_the_chart_box_for_the_screenshot() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}")
    assert 'id="charts-top"' in html and 'id="charts-end"' in html
    assert "chartBox" in html  # the drawing pass publishes the crop box


def test_render_marks_every_chart_as_a_piece_the_mail_can_cut_out() -> None:
    data = sample()
    html = dashboard.render(data, ":root{--ink:#000}")
    for piece in ("nav", "pnl", "daily"):
        assert f'data-piece="{piece}"' in html, piece
    for key in data["series"]["symbols"]:
        assert f"data-piece='price:{key}'" in html and f"data-piece='pnlc:{key}'" in html
    assert "data-piece='spark:" in html
    assert "dataset.pieces" in html
    # on screen the charts keep their width and scale with the page
    assert 'viewBox="0 0 860 220"' in html and 'width="540"' not in html


def test_render_for_capture_sizes_the_charts_for_the_mail_column() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}", capture=True)
    assert 'viewBox="0 0 540 190" width="540" height="190" data-piece="nav"' in html
    assert "viewBox='0 0 520 120' width='520' height='120'" in html
    assert "grid-template-columns:1fr!important" in html


def test_render_labels_the_series_as_all_accounts_and_lists_each_account_s_attribution() -> None:
    data = sample()
    data["headline"]["xirr_scope"] = "海外証券口座・国内証券口座"
    data["attribution"]["accounts"] = {
        "gb": {
            "window": {**data["attribution"]["window"], "total": -135387},
            "incept": {**data["attribution"]["incept"], "total": 405724},
        }
    }
    html = dashboard.render(data, ":root{--ink:#000}")
    assert "全口座 NAV と損益" in html and "海外証券口座 NAV と損益" not in html
    assert "日次損益 <small>全口座" in html
    assert "全口座 2025-09-11 以降・入金控除後" in html
    assert "海外証券口座・国内証券口座 · 最大DD" in html
    assert (
        "<td>海外証券口座</td><td class='n dn'>−135,387</td><td class='n up'>+405,724</td>" in html
    )


def test_render_shows_the_risk_section() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}")
    for text in (
        "リスク",
        "限度",
        "超過 2 件",
        "超過 単一銘柄は総資産の10%以下 · 16.4% / &lt;= 10.0%",
        "実効セクター数は4以上 · 3.2 / &gt;= 4.0",
        "エクスポージャー",
        "外貨エクスポージャー",
        "年率ボラティリティ",
        "18.0%",
        "前日比 +1.0pt",
        "VaR 1日 95%",
        "690,000",
        "ベータ TOPIX",
        "リスク寄与",
        "56.5%",
        "ストレス",
        "株式全体 -10%",
        "2020-03 コロナ暴落",
        "2024-08 円キャリー巻き戻し",
        "カバー率 100%",
        "Advantest",
        "6857 · 1329",
    ):
        assert text in html, text
    data = sample()
    data["risk"] = None
    assert "年率ボラティリティ" not in dashboard.render(data, ":root{--ink:#000}")


def test_overview_uses_existing_risk_and_series_without_changing_mail_pieces() -> None:
    data = sample()
    data["notes"].insert(0, "基準日より前の終値: SMH（2026-09-10）")
    page = dashboard.render(data, "")
    overview = page.split('id="general"')[1].split('id="risk"')[0]
    for text in (
        'id="overview-nav"',
        'id="overview-pnl"',
        "18.0%",
        "690,000",
        "32.3%",
        "超過 2 件",
        "6857",
        "56.5%",
        "SMH",
        "17.9%",
        'href="#risk"',
        'href="#charts-top"',
    ):
        assert text in overview
    assert page.index("基準日より前の終値: SMH") < page.index('id="general"')
    assert page.count('data-piece="nav"') == 1
    assert page.count('data-piece="pnl"') == 1
    capture = dashboard.render(data, "", capture=True)
    assert 'id="overview-nav"' not in capture
    assert 'id="overview-pnl"' not in capture


def test_overview_handles_unavailable_risk_and_escapes_freshness() -> None:
    data = sample()
    data["risk"] = None
    data["notes"] = ["基準日より前の終値: <script>oops</script>"]
    page = dashboard.render(data, "")
    overview = page.split('id="general"')[1].split('<div class="tw">')[0]
    assert "リスク指標は未取得" in overview
    assert 'href="#risk"' not in overview
    assert "&lt;script&gt;oops&lt;/script&gt;" in page
    assert "<script>oops</script>" not in dashboard._freshness(data)


def test_overview_sorts_risk_contributors_and_does_not_call_missing_policy_zero() -> None:
    data = sample()
    data["risk"]["contributions"]["positions"].reverse()
    data["risk"].pop("policy_breaches")
    overview = dashboard._overview(data)
    assert overview.index("6857") < overview.index("SMH")
    assert "未取得" in overview
    assert "超過 0 件" not in overview


def test_limit_values_are_shares_unless_the_metric_is_a_count() -> None:
    # "country" contains "count": the foreign-country limit is a share like the others
    assert dashboard._limit_value("largest_foreign_country_ratio", 0.2712) == "27.1%"
    assert dashboard._limit_value("worst_compound_drawdown", 0.17) == "17.0%"
    assert dashboard._limit_value("sector_effective_count", 3.2177) == "3.2"


def test_dashboard_shows_regions_under_country_and_region() -> None:
    from test_mailer import payload

    page = dashboard.render(payload(), tokens_css="")
    assert "新興国" in page
    assert "台湾" not in page.split('id="data"')[0]  # the embedded payload still carries countries
