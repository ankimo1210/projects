"""Offline tests for the daily-report email (no network, no SMTP)."""

from __future__ import annotations

import base64
from email import message_from_bytes

from portfolio_analyzer import mailer


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
        "series": {
            "dates": ["2025-09-11", "2026-03-11", "2026-09-11"],
            "nav": [24000000.0, 25000000.0, 25427872.0],
            "pnl": [-100000.0, 500000.0, 405823.0],
            "deposits": [24100000.0, 24500000.0, 25022049.0],
            "daily_pnl": [-50000.0, 120000.0, 57559.0],
        },
    }


def test_subject_carries_date_and_day_pnl() -> None:
    assert mailer.subject(payload()) == "日次損益 2026-09-11 · 46,257,970 円（−450,566）"


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
    body = mailer.html_body(payload(), image_cid="charts")
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
    body = mailer.html_body(payload(), image_cid="charts")
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


def test_html_body_shows_the_rendered_chart_instead_of_the_drawn_one() -> None:
    # A real rendered chart beats the table-cell fallback, so it replaces it.
    withimg = mailer.html_body(payload(), image_cid="charts")
    assert "cid:charts" in withimg
    assert "上げた日" not in withimg  # the drawn figures stand down
    assert "cid:" not in mailer.html_body(payload())


def test_html_body_draws_a_sparkline_beside_every_position() -> None:
    data = payload()
    with_spark = mailer.html_body(data)
    for p in data["positions"]:
        p["spark"] = []
    without = mailer.html_body(data)
    # one stroke per point of every sparkline
    assert with_spark.count("solid #C05C33") >= without.count("solid #C05C33") + 6


def test_html_body_stays_under_gmails_clip_limit_with_a_full_book() -> None:
    # Gmail clips a message past ~102 KB, and the charts are made of table cells
    data = payload()
    base = data["positions"][0]
    data["positions"] = [
        {**base, "sym": f"S{i:02d}", "spark": [float(v % 17) for v in range(i, i + 80)]}
        for i in range(12)
    ]
    n = 261
    data["series"] = {
        "dates": [f"2026-{1 + i // 22:02d}-{1 + i % 22:02d}" for i in range(n)],
        "nav": [1e7 + i * 1e4 for i in range(n)],
        "pnl": [(i % 40 - 20) * 1e4 for i in range(n)],
        "deposits": [1e7] * n,
        "daily_pnl": [(i % 7 - 3) * 1e4 for i in range(n)],
    }
    assert len(mailer.html_body(data).encode("utf-8")) < 95_000


def test_build_message_is_multipart_related_with_inline_png() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    msg = mailer.build_message(payload(), to=["me@example.com"], sender="me@example.com", png=png)
    raw = msg.as_bytes()
    parsed = message_from_bytes(raw)
    assert parsed["To"] == "me@example.com"
    assert "日次損益 2026-09-11" in mailer.decode_header_text(parsed["Subject"])
    types = [part.get_content_type() for part in parsed.walk()]
    assert "multipart/related" in types and "text/plain" in types and "text/html" in types
    image = next(p for p in parsed.walk() if p.get_content_type() == "image/png")
    assert image["Content-ID"] == "<charts>"
    assert image.get("Content-Disposition", "").startswith("inline")
    assert base64.b64decode(image.get_payload()) == png


def test_build_message_without_image_has_no_related_part() -> None:
    msg = mailer.build_message(payload(), to=["me@example.com"], sender="me@example.com", png=None)
    types = [part.get_content_type() for part in message_from_bytes(msg.as_bytes()).walk()]
    assert "image/png" not in types and "text/html" in types
