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
            "quoted_value": 29170055.0,
            "quoted_share": 0.63,
            "day_pnl": -450566.0,
            "day_pnl_pct": -1.52,
            "unrealized_known": -165287.0,
            "pnl_window": 919773.0,
            "pnl_incept": 405823.0,
            "realized_cum": -580654.0,
            "dividends_net": 67706.0,
            "xirr": 0.0172,
            "max_dd_window": -0.104,
        },
        "accounts": [
            {"id": "dc", "name": "DC口座", "total": 7637840.0, "day_pnl": None, "unrealized": None},
            {
                "id": "gb",
                "name": "海外証券口座",
                "total": 25427872.0,
                "day_pnl": 57559.0,
                "unrealized": -165287.0,
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
                "avg_cost": 53.865,
                "unreal": 648558.0,
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
                "avg_cost": 1991.65,
                "unreal": -18979.0,
                "unreal_pct": -0.6,
                "spark": [2100.0, 2000.0, 1979.0],
            },
        ],
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


def test_html_body_draws_the_charts_in_the_body_without_an_image() -> None:
    body = mailer.html_body(payload())
    assert "cid:" not in body and "<img" not in body
    assert "<script" not in body and "<svg" not in body
    assert "累計損益" in body and "日次損益" in body and "騰落率" in body
    # the columns are table cells, so they survive a client that strips everything else
    assert body.count("<td") > 20


def test_html_body_paints_every_fill_with_an_attribute() -> None:
    # Gmail's send path strips CSS backgrounds, which would leave the charts colourless.
    assert "background:" not in mailer.html_body(payload())


def test_html_body_still_renders_when_the_payload_carries_no_series() -> None:
    data = payload()
    del data["series"]
    body = mailer.html_body(data)
    assert "46,257,970" in body and "XLE" in body


def test_html_body_references_the_inline_image_only_when_one_is_attached() -> None:
    assert "cid:charts" in mailer.html_body(payload(), image_cid="charts")
    assert "cid:" not in mailer.html_body(payload())


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
