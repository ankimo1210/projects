"""Offline tests for the daily-report email (no network, no SMTP)."""

from __future__ import annotations

import base64
from email import message_from_bytes

from portfolio_analyzer import mailer
from risk_fixture import risk_block


def payload() -> dict:
    return {
        "as_of": "2026-09-11",
        "generated_at": "2026-09-12T07:30:00+09:00",
        "fx": {"last": 153.55, "chg_pct": -0.01, "date": "2026-09-11"},
        "window": {"start": "2025-09-11", "end": "2026-09-11", "days": 365},
        "headline": {
            "nav_total": 46257970.0,
            "nav_after_tax": 45000000.0,
            "day_after_tax": -380000.0,
            "unreal_after_tax": -131708.0,
            "quoted_value": 29170055.0,
            "quoted_share": 0.63,
            "day_pnl": -450566.0,
            "day_pnl_pct": -1.52,
            "day_stock": -470000.0,
            "day_fx": 19434.0,
            "unrealized_known": -165287.0,
            "unreal_stock": -100000.0,
            "unreal_fx": -65287.0,
            "pnl_window": 919773.0,
            "pnl_incept": 405823.0,
            "realized_cum": -580654.0,
            "dividends_net": 67706.0,
            "xirr": 0.0172,
            "max_dd_window": -0.104,
        },
        "accounts": [
            {
                "id": "dc",
                "name": "DC口座",
                "total": 7637840.0,
                "day_pnl": None,
                "unrealized": None,
                "total_after_tax": 7637840.0,
                "tax_rate": 0.0,
            },
            {
                "id": "gb",
                "name": "海外証券口座",
                "total": 25427872.0,
                "day_pnl": 57559.0,
                "day_stock": 38125.0,
                "day_fx": 19434.0,
                "unrealized": -165287.0,
                "unreal_stock": -100000.0,
                "unreal_fx": -65287.0,
                "total_after_tax": 25461450.0,
                "day_after_tax": 45866.0,
                "unreal_after_tax": -131708.0,
                "tax_rate": 0.20315,
            },
        ],
        "positions": [
            {
                "key": "XLE@gb",
                "sym": "XLE",
                "acct": "海外証券口座",
                "name": "Energy",
                "cls": "米国株",
                "cur": "USD",
                "qty": 500.0,
                "last": 65.14,
                "chg1d": 0.32,
                "chg1w": 1.0,
                "chg1m": 6.7,
                "chg1y": 46.2,
                "value": 5001254.0,
                "weight": 10.8,
                "day_pnl": 15506.0,
                "day_stock": 12000.0,
                "day_fx": 3506.0,
                "avg_cost": 53.865,
                "unreal": 648558.0,
                "unreal_stock": 700000.0,
                "unreal_fx": -51442.0,
                "day_after_tax": 12356.0,
                "unreal_after_tax": 516803.0,
                "tax_rate": 0.20315,
                "unreal_pct": 14.9,
                "spark": [60.0, 62.0, 65.14],
            },
            {
                "key": "2561@gb",
                "sym": "2561",
                "acct": "海外証券口座",
                "name": "US bond",
                "cls": "ETF",
                "cur": "JPY",
                "qty": 1500.0,
                "last": 1979.0,
                "chg1d": -0.55,
                "chg1w": -0.3,
                "chg1m": -1.1,
                "chg1y": -9.3,
                "value": 2968500.0,
                "weight": 6.4,
                "day_pnl": -16500.0,
                "day_stock": -16500.0,
                "day_fx": 0.0,
                "avg_cost": 1991.65,
                "unreal": -18979.0,
                "unreal_stock": -18979.0,
                "unreal_fx": 0.0,
                "day_after_tax": -13148.0,
                "unreal_after_tax": -15123.0,
                "tax_rate": 0.20315,
                "unreal_pct": -0.6,
                "spark": [2100.0, 2000.0, 1979.0],
            },
        ],
        "tax_note": "税引後は口座ごとの税率で見込んだ値（テスト）",
        "tape": [{"sym": "SMH", "cur": "USD", "last": 568.53, "chg_pct": 1.47}],
        "allocation": [
            {"label": "日本株", "value": 13386570.0, "pct": 29.0},
            {"label": "現金", "value": 9420855.0, "pct": 20.4},
        ],
        "attribution": {
            "window": {
                "unrealized": -158210.0,
                "realized": 0.0,
                "dividends": 7172.0,
                "fees": -674.0,
                "fx_translation": 1077796.0,
                "forex": 766.0,
                "total": 926850.0,
            },
            "incept": {
                "unrealized": -158210.0,
                "realized": -580654.0,
                "dividends": 67706.0,
                "fees": -839.0,
                "fx_translation": 1077796.0,
                "forex": 7102.0,
                "total": 412901.0,
            },
        },
        "closed": [
            {
                "sym": "LLY",
                "first": "2024-11-01",
                "last": "2025-06-04",
                "trades": 2,
                "realized": -175786.0,
            }
        ],
        "notes": ["時価が取れず据え置き: CASH_JPY（合計 9,450,075 円）"],
        "risk": risk_block(),
        "series": {
            "dates": ["2025-09-11", "2026-03-11", "2026-09-11"],
            "nav": [24000000.0, 25000000.0, 25427872.0],
            "pnl": [-100000.0, 500000.0, 405823.0],
            "deposits": [24100000.0, 24500000.0, 25022049.0],
            "daily_pnl": [-50000.0, 120000.0, 57559.0],
            "symbols": {
                "XLE@gb": {
                    "mode": "pnl",
                    "label": "含み損益（取得原価比）",
                    "cur": "USD",
                    "price": [60.0, 62.0, 65.14],
                    "pnl": [100000.0, 300000.0, 648558.0],
                    "trades": [{"i": 1, "qty": 100.0, "price": 62.0}],
                    "avg_cost": 53.865,
                }
            },
        },
    }


def test_subject_carries_date_and_day_pnl() -> None:
    assert mailer.subject(payload()) == "日次損益 2026-09-11 · 46,257,970 円（−450,566）"


def test_subject_and_body_name_the_edition_when_given() -> None:
    data = payload()
    data["edition"] = "東京引け"
    assert mailer.subject(data) == "日次損益 2026-09-11 · 東京引け · 46,257,970 円（−450,566）"
    assert "日次損益 2026-09-11 · 東京引け" in mailer.html_body(data)
    assert mailer.text_body(data).startswith("日次損益 2026-09-11 · 東京引け")


def test_text_body_lists_headline_and_positions() -> None:
    text = mailer.text_body(payload())
    assert "46,257,970" in text and "−450,566" in text and "XLE" in text and "海外証券口座" in text
    assert "+648,558" in text


def test_text_body_splits_pnl_into_stock_and_fx() -> None:
    text = mailer.text_body(payload())
    assert "株 −470,000" in text and "FX +19,434" in text  # day, total
    assert "株 −100,000" in text and "FX −65,287" in text  # unrealised, total
    assert "株 +12,000" in text and "FX +3,506" in text  # day, XLE
    assert "株 +700,000" in text and "FX −51,442" in text  # unrealised, XLE


def test_html_body_splits_pnl_into_stock_and_fx_for_totals_accounts_and_positions() -> None:
    body = mailer.html_body(payload())
    for value in (
        "株 −470,000",  # headline day
        "FX +19,434",
        "株 −100,000",  # headline unrealised, and the account row
        "FX −65,287",
        "株 +38,125",  # account day
        "株 +12,000",  # XLE day
        "FX +3,506",
        "株 +700,000",  # XLE unrealised
        "FX −51,442",
        "株 −16,500",  # yen holding: all stock
        "FX ±0",
    ):
        assert value in body, value


def test_text_body_carries_the_after_tax_estimate() -> None:
    text = mailer.text_body(payload())
    assert "税引後 45,000,000" in text
    assert "税引後 −380,000" in text and "税引後 −131,708" in text
    assert "税後 +12,356" in text and "税後 +516,803" in text  # XLE
    assert "税引後は口座ごとの税率で見込んだ値（テスト）" in text


def test_html_body_carries_the_after_tax_estimate_for_totals_accounts_and_positions() -> None:
    body = mailer.html_body(payload())
    for value in (
        "税引後 45,000,000",  # headline total
        "税引後 −380,000",  # headline day
        "税引後 −131,708",  # headline unrealised
        "税後 +45,866",  # account day
        "税後 −131,708",  # account unrealised
        "税後 +12,356",  # XLE day
        "税後 +516,803",  # XLE unrealised
        "税後 −13,148",  # 2561 day
        "税引後は口座ごとの税率で見込んだ値（テスト）",
    ):
        assert value in body, value


def test_usd_converts_at_the_day_s_rate_with_the_sign_before_the_dollar() -> None:
    assert mailer.usd(46257970.0, 153.55) == "$301,257"
    assert mailer.usd(-450566.0, 153.55, True) == "−$2,934"
    assert mailer.usd(15506.0, 153.55, True) == "+$101"
    assert mailer.usd(None, 153.55) == "" and mailer.usd(1.0, None) == ""


def test_text_body_shows_usd_beside_the_yen() -> None:
    text = mailer.text_body(payload())
    assert "$301,257" in text  # total assets
    assert "−$2,934" in text  # day
    assert "−$1,076" in text  # unrealised
    assert "$32,571" in text  # XLE value


def test_html_body_shows_usd_under_yen_for_totals_accounts_and_positions() -> None:
    body = mailer.html_body(payload())
    for value in (
        "$301,257",  # headline total
        "税引後 45,000,000 · $293,064",
        "−$2,934",  # headline day
        "税引後 −380,000 · −$2,475",
        "−$1,076",  # headline unrealised
        "+$5,990",  # window
        "$165,600",  # account total
        "+$375",  # account day
        "$32,571",  # XLE value
        "+$101",  # XLE day
        "+$4,224",  # XLE unrealised
        "$19,332",  # 2561 value
    ):
        assert value in body, value


def test_html_body_leaves_the_split_out_when_the_payload_has_none() -> None:
    data = payload()
    for p in data["positions"]:
        for k in ("day_stock", "day_fx", "unreal_stock", "unreal_fx"):
            del p[k]
    body = mailer.html_body(data)
    assert "株 +12,000" not in body and "+15,506" in body


def test_html_body_draws_the_charts_in_the_body_without_an_image() -> None:
    body = mailer.html_body(payload())
    assert "cid:" not in body and "<img" not in body
    assert "<script" not in body and "<svg" not in body
    assert "累計損益" in body and "日次損益" in body
    # the columns are table cells, so they survive a client that strips everything else
    assert body.count("<td") > 20


def test_html_body_paints_every_fill_with_an_attribute() -> None:
    # Gmail's send path strips the CSS background shorthand, which would leave the charts colourless.
    assert "background:" not in mailer.html_body(payload())


def test_html_body_still_renders_when_the_payload_carries_no_series() -> None:
    data = payload()
    del data["series"]
    body = mailer.html_body(data)
    assert "46,257,970" in body and "XLE" in body


def test_html_body_uses_the_attached_drawing_of_a_chart_instead_of_table_cells() -> None:
    images = {"daily": ("chart0@pl", 560, 170), "price:XLE@gb": ("chart1@pl", 540, 140)}
    body = mailer.html_body(payload(), images)
    assert '<img src="cid:chart0@pl" width="560" height="170"' in body
    assert '<img src="cid:chart1@pl" width="540" height="140"' in body
    assert "▲ 買 ▼ 売" in body and "点線 平均取得" in body
    # the sparkline keeps to a narrow fixed width so the holdings table fits the column
    spark = mailer.html_body(payload(), {"spark:XLE@gb": ("chart2@pl", 100, 30)})
    assert '<img src="cid:chart2@pl" width="64" height="19"' in spark
    # a chart with no drawing attached is still drawn with cells
    assert "累計損益" in body and "cid:" not in mailer.html_body(payload())


def test_html_body_draws_a_sparkline_beside_every_position() -> None:
    data = payload()
    with_spark = mailer.html_body(data)
    for p in data["positions"]:
        p["spark"] = []
    without = mailer.html_body(data)
    # one stroke per point of every sparkline
    assert with_spark.count("solid #C05C33") >= without.count("solid #C05C33") + 6


def test_build_message_attaches_each_chart_inline_under_its_content_id() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    pieces = {"nav": (png, 560, 210), "spark:XLE@gb": (png + b"1", 116, 46)}
    msg = mailer.build_message(
        payload(), to=["me@example.com"], sender="me@example.com", pieces=pieces
    )
    parsed = message_from_bytes(msg.as_bytes())
    assert parsed["To"] == "me@example.com"
    assert "日次損益 2026-09-11" in mailer.decode_header_text(parsed["Subject"])
    types = [part.get_content_type() for part in parsed.walk()]
    assert "multipart/related" in types and "text/plain" in types and "text/html" in types
    images = [p for p in parsed.walk() if p.get_content_type() == "image/png"]
    assert len(images) == 2
    assert all(p.get("Content-Disposition", "").startswith("inline") for p in images)
    html_part = next(p for p in parsed.walk() if p.get_content_type() == "text/html")
    body = html_part.get_payload(decode=True).decode("utf-8")
    for image in images:
        cid = image["Content-ID"].strip("<>")
        assert f"cid:{cid}" in body
    assert base64.b64decode(images[0].get_payload()) == png


def test_build_message_without_image_has_no_related_part() -> None:
    msg = mailer.build_message(payload(), to=["me@example.com"], sender="me@example.com")
    types = [part.get_content_type() for part in message_from_bytes(msg.as_bytes()).walk()]
    assert "image/png" not in types and "text/html" in types


def test_html_body_carries_every_section_of_the_dashboard() -> None:
    body = mailer.html_body(payload())
    for value in (
        "SMH",  # tape
        "568.53",
        "+1.47%",
        "開設来損益",
        "+405,823",
        "実現 −580,654 · 配当 +67,706",
        "資金加重リターン",
        "+1.72%",
        "最大DD（期間内） −10.4%",
        "資産配分",  # allocation
        "日本株",
        "29.0%",
        "損益の内訳",  # attribution
        "為替換算 現金",
        "+1,077,796",
        "+412,901",
        "決済済み",  # closed
        "LLY",
        "2024-11-01 → 2025-06-04",
        "−175,786",
        "NAV と累計入金",  # time series
        "時価が取れず据え置き: CASH_JPY（合計 9,450,075 円）",  # notes
    ):
        assert value in body, value


def test_html_body_draws_a_card_for_every_charted_position() -> None:
    body = mailer.html_body(payload())
    card = body[body.index("銘柄ごとの推移") :]
    for value in (
        "XLE",
        "65.14",
        "Energy · 海外証券口座",
        "数量 <b>500</b>",
        "平均 <b>53.87</b>",
        "比率 <b>10.8%</b>",
        "1W <b",
        "+1.0%",
        "1M <b",
        "+6.7%",
        "含み <b",
        "+14.9%",
        "含み損益（取得原価比） ¥",
        "+648,558",
    ):
        assert value in card, value
    # a position with no series gets no card
    assert "2561" not in card


def test_html_body_marks_the_trades_and_the_average_cost_on_the_price_chart() -> None:
    data = payload()
    with_marks = mailer.html_body(data)
    sym = data["series"]["symbols"]["XLE@gb"]
    sym["trades"], sym["avg_cost"] = [], None
    without = mailer.html_body(data)
    assert with_marks.count(f"solid {mailer.DN}") > without.count(f"solid {mailer.DN}")


def test_html_body_draws_the_daily_pnl_over_the_whole_window() -> None:
    data = payload()
    data["series"]["dates"] = [f"2026-{m:02d}-01" for m in range(1, 10)] * 10
    data["series"]["daily_pnl"] = [1000.0] * 90
    assert "90 営業日" in mailer.html_body(data)


def test_html_body_does_not_count_a_flat_day_as_a_down_day() -> None:
    data = payload()
    data["series"]["daily_pnl"] = [0.0, 120000.0, -57559.0]
    assert "上げた日 1 日 / 下げた日 1 日（変化なし 1 日）" in mailer.html_body(data)


def test_text_body_carries_the_inception_figures_and_the_notes() -> None:
    text = mailer.text_body(payload())
    assert "開設来損益" in text and "+405,823" in text and "+1.72%" in text
    assert "時価が取れず据え置き: CASH_JPY（合計 9,450,075 円）" in text


def test_html_body_shows_the_totals_across_accounts_with_a_row_per_account() -> None:
    data = payload()
    data["headline"]["xirr_scope"] = "海外証券口座・国内証券口座"
    data["attribution"]["accounts"] = {
        "gb": {
            "window": {**data["attribution"]["window"], "total": 926850.0},
            "incept": {**data["attribution"]["incept"], "total": 412901.0},
        },
        "dc": {
            "window": {**data["attribution"]["window"], "total": 863802.0},
            "incept": {**data["attribution"]["incept"], "total": 2340897.0},
        },
    }
    body = mailer.html_body(data)
    assert "全口座 · 2025-09-11 → 2026-09-11" in body and "海外証券口座 · 2025-09-11" not in body
    assert "全口座 2025-09-11 以降・入金控除後" in body
    assert "海外証券口座・国内証券口座 · 最大DD" in body
    table = body.split("損益の内訳")[1].split("評価額の大きい順")[0]
    assert "　海外証券口座" in table and "　DC口座" in table and "+2,340,897" in table
    text = mailer.text_body(data)
    assert "(全口座・入金控除後)" in text and "(海外証券口座・国内証券口座)" in text


def test_html_and_text_body_carry_the_risk_section() -> None:
    body = mailer.html_body(payload())
    for text in (
        "リスク",
        "限度 · 超過 2 件",
        "超過 単一銘柄は総資産の10%以下 · 16.4% / &lt;= 10.0%",
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
        "2024-08 円キャリー巻き戻し",
        "カバー率 100%",
        "Advantest",
        "6857 · 1329",
    ):
        assert text in body, text
    assert "background:" not in body
    text = mailer.text_body(payload())
    assert "リスク: ボラ 18.0%, VaR(1日95%) 690,000, ES(97.5%) 920,000, 外貨 32.3%" in text
    assert "最大ルックスルー銘柄 Advantest 14.6%, 超過 2" in text
    data = payload()
    data["risk"] = None
    assert "年率ボラティリティ" not in mailer.html_body(data) and "リスク:" not in mailer.text_body(
        data
    )


def test_warnings_lead_both_bodies() -> None:
    data = payload()
    data["warnings"] = ["図を画像にできませんでした（ヘッドレスブラウザが見つからない）"]
    html_text = mailer.html_body(data)
    head = html_text.index("図を画像にできませんでした")
    assert head < html_text.index("総資産 ¥")  # before the figures (the hidden preview line aside)
    assert "background:" not in html_text[head - 400 : head]  # Gmail strips the shorthand
    text = mailer.text_body(data)
    assert text.index("! 図を画像にできませんでした") < text.index("総資産")
    assert "図を画像にできませんでした" not in mailer.html_body(payload())


def test_limit_values_are_shares_unless_the_metric_is_a_count() -> None:
    # "country" contains "count": the foreign-country limit is a share like the others
    assert mailer._limit_value("largest_foreign_country_ratio", 0.2712) == "27.1%"
    assert mailer._limit_value("worst_compound_drawdown", 0.17) == "17.0%"
    assert mailer._limit_value("sector_effective_count", 3.2177) == "3.2"


def test_mail_shows_regions_under_country_and_region() -> None:
    body = mailer.html_body(payload())
    assert "新興国" in body  # the region table and its risk share
    assert "台湾" not in body  # a country row would mix the two taxonomies


def test_the_inbox_preview_carries_the_numbers_and_stays_hidden() -> None:
    data = payload()
    line = mailer.preheader(data)
    assert line.startswith("総資産 46,257,970 円 · 日次 −450,566 円")
    body = mailer.html_body(data)
    hidden = body.index('<div style="display:none;')
    assert body.index(line) > hidden and body.index(line) < body.index("DAILY MARK-TO-MARKET")


def test_the_heading_is_sized_for_a_mail_client_not_a_page() -> None:
    body = mailer.html_body(payload())
    assert "Georgia" not in body and "font:700 20px" not in body and "font:600 21px" not in body
    assert "font:700 15px" in body  # the date line
    assert "font:600 17px" in body  # the headline figures


def test_holdings_wrap_two_by_two_on_a_narrow_screen() -> None:
    body = mailer.html_body(payload())
    # the four blocks of each holding fit a 600px column in one row and pair up below that
    assert sum(mailer.HOLDING_WIDTHS) <= 580
    assert mailer.HOLDING_WIDTHS[0] + mailer.HOLDING_WIDTHS[1] <= 300
    assert mailer.HOLDING_WIDTHS[2:] == mailer.HOLDING_WIDTHS[:2]  # so the pairs line up
    for label in ("銘柄 · 1D · 1Y", "評価額 ¥", "日次 ¥", "含み ¥"):
        assert label in body
    assert "値動き 1Y" not in body  # the old seven-column head
