"""Offline tests for the defined-contribution (DC) plan's fund prices and holding."""

from __future__ import annotations

from decimal import Decimal

from portfolio_analyzer import dcplan

D = Decimal

NAV_CSV = """基準日,基準価額(円),基準価額(税引前分配金再投資)(円),純資産総額(百万円),分配金(円),設定来分配金(円)
"2026/08/25","26,446","26,446","39,626","0","0"
"2026/08/26","26,503","26,503","39,737","0","0"
"2026/08/27","26,502","26,502","39,701","0","0"
"""

# Pasted from the DC site: the header wraps over several lines and repeats per page.
TRADES_PASTE = """約定日	受渡日	運用商品名	数量
(円・口)	約定単価
(円・１口当り)	受渡金額
(円)	取引区分
2026/08/26	2026/08/28	ハッピーエイジング４０	20,753	2.6502	55,000	買 掛金
2026/07/27	2026/07/29	ハッピーエイジング４０	20,934	2.6273	55,000	買 掛金

約定日	受渡日	運用商品名	数量
2025/08/26	2025/08/28	ハッピーエイジング４０	24,477	2.2470	55,000	買 掛金
"""

HOLDING = {
    "account_id": "dc",
    "symbol": "HAPPY_AGING_40",
    "ticker": "SOMPO_AM:0885",
    "anchor": {"as_of": "2026-09-12", "units": 2901109, "contributions_jpy": 5184000},
}


def test_decode_reads_the_fund_company_s_cp932_csv() -> None:
    assert dcplan.decode(NAV_CSV.encode("cp932")) == NAV_CSV


def test_parse_nav_reads_dates_and_prices_per_ten_thousand_units() -> None:
    assert dcplan.parse_nav(NAV_CSV) == [
        ("2026-08-25", D("26446")),
        ("2026-08-26", D("26503")),
        ("2026-08-27", D("26502")),
    ]


def test_parse_trades_skips_wrapped_and_repeated_headers() -> None:
    trades = dcplan.parse_trades(TRADES_PASTE)
    assert [t.trade_date for t in trades] == ["2025-08-26", "2026-07-27", "2026-08-26"]
    t = trades[-1]
    assert t.settle_date == "2026-08-28" and t.units == D("20753")
    assert t.price == D("2.6502") and t.amount == D("55000") and t.kind == "買 掛金"


def test_ledger_holds_the_anchor_in_ten_thousand_units_at_contributed_cost() -> None:
    ledger = dcplan.ledger(HOLDING, dcplan.parse_trades(TRADES_PASTE))
    assert ledger["account_id"] == "dc"
    (h,) = ledger["holdings"]
    assert h["symbol"] == "HAPPY_AGING_40" and h["currency"] == "JPY"
    assert h["quantity"] == D("290.1109")
    assert h["cost_basis_jpy"] == D("5184000")
    assert h["average_cost"] == D("5184000") / D("290.1109")
    assert h["average_trade_fx"] == D("1") and h["commission_jpy"] == D("0")


def test_ledger_adds_contributions_made_after_the_anchor() -> None:
    later = (
        TRADES_PASTE
        + "2026/09/28\t2026/09/30\tハッピーエイジング４０\t21,000\t2.6190\t55,000\t買 掛金\n"
    )
    (h,) = dcplan.ledger(HOLDING, dcplan.parse_trades(later))["holdings"]
    assert h["quantity"] == D("292.2109")
    assert h["cost_basis_jpy"] == D("5239000")


def test_replay_walks_the_anchor_back_through_the_contributions() -> None:
    dates = ["2025-08-25", "2025-08-26", "2026-07-27", "2026-08-25", "2026-08-26", "2026-09-11"]
    path = dcplan.replay(HOLDING, dcplan.parse_trades(TRADES_PASTE), dates)["HAPPY_AGING_40"]
    now_units, now_cost = D("2901109"), D("5184000")
    assert path["quantity"][-1] == now_units / 10000
    assert path["cost_basis_jpy"][-1] == now_cost
    # before the 2026-08-26 contribution
    assert path["quantity"][3] == (now_units - 20753) / 10000
    assert path["cost_basis_jpy"][3] == now_cost - 55000
    # a contribution counts from its trade date on
    assert path["quantity"][2] == (now_units - 20753) / 10000
    # on the day of the oldest contribution the history knows
    assert path["quantity"][1] == (now_units - 20753 - 20934) / 10000
    # before it, an unlisted contribution could be missing, so the path says nothing
    assert path["quantity"][0] is None and path["cost_basis_jpy"][0] is None
    # markers in ten-thousand units at the price per ten thousand units
    assert path["trades"][-1] == ("2026-08-26", D("2.0753"), D("26502"))


def test_apply_to_snapshot_marks_the_fund_by_its_own_ticker_without_editing_the_input() -> None:
    snapshot = {
        "accounts": [{"id": "dc"}],
        "positions": [
            {
                "account_id": "dc",
                "symbol": "HAPPY_AGING_40",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "market_value_jpy": 7637840,
            }
        ],
    }
    ledger = dcplan.ledger(HOLDING, dcplan.parse_trades(TRADES_PASTE))
    out = dcplan.apply_to_snapshot(snapshot, HOLDING, ledger)
    pos = out["positions"][0]
    assert pos["ticker"] == "SOMPO_AM:0885" and pos["quantity"] == D("290.1109")
    assert snapshot["positions"][0]["quantity"] is None
