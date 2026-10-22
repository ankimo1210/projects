"""Parse the TSE-format summary page of Japanese earnings releases (決算短信)."""

from __future__ import annotations

from pathlib import Path

import pytest
from portfolio_analyzer.ai_bubble.inputs import audit_inputs, select_as_of
from portfolio_analyzer.ai_bubble.jp import parse_summary

FIXTURES = Path(__file__).parent / "fixtures" / "ai_bubble"


def parse(name, **kw):
    text = (FIXTURES / name).read_text()
    return parse_summary(
        text,
        issuer_id="6857.T",
        source_url=f"https://example.test/{name}",
        retrieved_at="2026-10-21T02:00:00Z",
        **kw,
    )


def value(rows, metric, start, end):
    hits = [
        r for r in rows if (r["metric"], r["period_start"], r["period_end"]) == (metric, start, end)
    ]
    assert len(hits) == 1, (metric, start, end, hits)
    return hits[0]["value"]


def test_ifrs_quarter_reads_cumulative_results_and_the_comparative_row():
    rows = parse("tanshin_ifrs_q1.txt")
    assert value(rows, "revenue", "2026-04-01", "2026-06-30") == 367_473e6
    assert value(rows, "revenue", "2025-04-01", "2025-06-30") == 263_776e6
    assert value(rows, "operating_income", "2026-04-01", "2026-06-30") == 189_990e6
    assert value(rows, "pretax_income", "2026-04-01", "2026-06-30") == 234_082e6
    assert value(rows, "net_income_parent", "2026-04-01", "2026-06-30") == 174_780e6
    assert value(rows, "eps_diluted", "2026-04-01", "2026-06-30") == 239.89


def test_ifrs_quarter_balance_sheet_rows_are_instants():
    rows = parse("tanshin_ifrs_q1.txt")
    assert value(rows, "total_assets", "2026-06-30", "2026-06-30") == 1_514_652e6
    assert value(rows, "equity_parent", "2026-03-31", "2026-03-31") == 795_726e6


def test_full_year_cash_flow_keeps_the_triangle_sign():
    rows = parse("tanshin_ifrs_fn.txt")
    span = ("2025-04-01", "2026-03-31")
    assert value(rows, "operating_cf", *span) == 335_182e6
    assert value(rows, "investing_cf", *span) == -34_552e6
    assert value(rows, "financing_cf", *span) == -230_550e6
    assert value(rows, "cash_end", "2026-03-31", "2026-03-31") == 339_966e6
    assert value(rows, "revenue", *span) == 1_128_610e6


def test_heisei_us_gaap_release_reads_losses_and_dates():
    rows = parse("tanshin_usgaap_fn.txt")
    span = ("2008-04-01", "2009-03-31")
    assert value(rows, "revenue", *span) == 76_652e6
    assert value(rows, "operating_income", *span) == -49_457e6
    assert value(rows, "net_income", *span) == -74_902e6
    assert value(rows, "eps_diluted", *span) == -419.09
    assert value(rows, "total_assets", "2009-03-31", "2009-03-31") == 202_059e6
    assert {r["accounting_basis"] for r in rows} == {"US-GAAP"}


def test_release_date_sets_publication_and_next_business_day_availability():
    rows = parse("tanshin_usgaap_fn.txt")
    # 平成21年4月27日 (Mon) 00:00 JST, usable from Tue 00:00 JST
    assert {r["published_at"] for r in rows} == {"2009-04-26T15:00:00Z"}
    assert {r["available_at"] for r in rows} == {"2009-04-27T15:00:00Z"}
    wednesday = parse("tanshin_ifrs_q1.txt")  # 2026-07-29 -> Thu 00:00 JST
    assert {r["available_at"] for r in wednesday} == {"2026-07-29T15:00:00Z"}


def test_rows_are_in_yen_and_pass_the_audit():
    rows = parse("tanshin_ifrs_fn.txt")
    assert audit_inputs(rows)["ok"] is True
    assert {r["unit"] for r in rows if r["metric"] == "revenue"} == {"JPY"}
    assert {r["unit"] for r in rows if r["metric"] == "eps_diluted"} == {"JPY/shares"}
    assert {r["accounting_basis"] for r in rows} == {"IFRS"}
    assert len(select_as_of(rows, "2026-10-21T00:00:00Z")) == len(rows)


def test_dash_means_not_reported_not_zero():
    rows = parse("tanshin_usgaap_fn.txt")
    assert all(r["value"] != 0 for r in rows)
    assert not [r for r in rows if r["metric"].endswith("_yoy")]


def test_missing_summary_block_is_an_error_not_an_empty_success():
    with pytest.raises(ValueError, match="連結経営成績"):
        parse_summary(
            "2026年7月29日\n決算短信〔IFRS〕(連結)\n",
            issuer_id="X",
            source_url="u",
            retrieved_at="2026-10-21T02:00:00Z",
        )


def test_full_width_digits_and_markers_are_normalised():
    rows = parse("tanshin_ifrs_fullwidth_q1.txt")
    assert value(rows, "revenue", "2025-04-01", "2025-06-30") == 263_776e6
    assert value(rows, "operating_income", "2024-04-01", "2024-06-30") == 31_325e6
    assert value(rows, "total_assets", "2025-06-30", "2025-06-30") == 889_869e6
    assert {r["accounting_basis"] for r in rows} == {"IFRS"}


def test_spaced_heisei_labels_and_parent_net_income_column():
    rows = parse("tanshin_usgaap_spaced_fn.txt")
    span = ("2011-04-01", "2012-03-31")
    assert value(rows, "revenue", *span) == 141_048e6
    assert value(rows, "operating_income", *span) == 837e6
    assert value(rows, "pretax_income", *span) == -3_442e6
    # the fourth column is 当社株主に帰属する当期純利益
    assert value(rows, "net_income_parent", *span) == -2_195e6
    assert not [r for r in rows if r["metric"] == "net_income"]
    assert value(rows, "eps_diluted", *span) == -12.67
    assert value(rows, "operating_cf", *span) == 12_302e6
    assert value(rows, "investing_cf", "2010-04-01", "2011-03-31") == -5_828e6
    assert value(rows, "operating_cf", "2010-04-01", "2011-03-31") == -693e6


def test_five_column_us_gaap_balance_sheet_keeps_parent_equity():
    rows = parse("tanshin_usgaap_spaced_fn.txt")
    assert value(rows, "total_assets", "2012-03-31", "2012-03-31") == 219_226e6
    assert value(rows, "equity_total", "2012-03-31", "2012-03-31") == 131_552e6
    assert value(rows, "equity_parent", "2012-03-31", "2012-03-31") == 131_552e6
    assert value(rows, "equity_ratio_pct", "2012-03-31", "2012-03-31") == 60.0
    assert value(rows, "bps", "2012-03-31", "2012-03-31") == 759.22


def test_spaced_release_date_is_read():
    rows = parse("tanshin_usgaap_spaced_fn.txt")
    # 平成24年4月26日 (Thu) -> Fri 00:00 JST
    assert {r["available_at"] for r in rows} == {"2012-04-26T15:00:00Z"}


def test_quarterly_us_gaap_balance_sheet_has_parent_equity_but_no_bps():
    rows = parse("tanshin_usgaap_q1_2011.txt")
    assert value(rows, "total_assets", "2011-03-31", "2011-03-31") == 180_312e6
    assert value(rows, "equity_parent", "2011-03-31", "2011-03-31") == 138_132e6
    assert value(rows, "equity_ratio_pct", "2011-03-31", "2011-03-31") == 76.6
    assert value(rows, "equity_ratio_pct", "2011-06-30", "2011-06-30") == 60.8
    assert not [r for r in rows if r["metric"] == "bps"]


def test_pre_2010_balance_sheet_without_a_parent_column_keeps_its_order():
    rows = parse("tanshin_usgaap_fn.txt")
    assert value(rows, "equity_total", "2009-03-31", "2009-03-31") == 163_616e6
    assert value(rows, "equity_ratio_pct", "2009-03-31", "2009-03-31") == 81.0
    assert value(rows, "bps", "2009-03-31", "2009-03-31") == 915.47
    assert not [r for r in rows if r["metric"] == "equity_parent"]


def test_interim_label_without_a_quarter_number_is_the_half_year():
    # From April 2024 the second-quarter release is labelled 中間期, not 第2四半期
    rows = parse("tanshin_ifrs_interim.txt")
    assert value(rows, "revenue", "2025-04-01", "2025-09-30") == 526_733e6
    assert value(rows, "revenue", "2024-04-01", "2024-09-30") == 329_206e6
    assert value(rows, "eps_diluted", "2025-04-01", "2025-09-30") == 231.49
    assert value(rows, "total_assets", "2025-09-30", "2025-09-30") == 971_541e6
    assert value(rows, "total_assets", "2025-03-31", "2025-03-31") == 854_210e6
    assert not [r for r in rows if r["period_end"] == "2026-03-31"]


def test_release_without_a_basis_marker_is_japanese_gaap_with_yen_and_sen_columns():
    # Before the 2010 template only US-GAAP filers printed their basis; yen and
    # sen of per-share values sat in separate columns.
    rows = parse("tanshin_jpgaap_nomarker_fn.txt")
    span = ("2007-04-01", "2008-03-31")
    assert {r["accounting_basis"] for r in rows} == {"JP-GAAP"}
    assert {r["basis_printed"] for r in rows} == {False}
    assert value(rows, "revenue", *span) == 906_091e6
    assert value(rows, "ordinary_income", *span) == 172_713e6
    assert value(rows, "net_income", *span) == 106_271e6
    assert value(rows, "eps_basic", *span) == 594.01
    assert value(rows, "eps_diluted", *span) == 592.71
    assert value(rows, "eps_basic", "2006-04-01", "2007-03-31") == 511.27
    assert value(rows, "total_assets", "2008-03-31", "2008-03-31") == 792_817e6
    assert value(rows, "equity_ratio_pct", "2008-03-31", "2008-03-31") == 67.5
    assert value(rows, "bps", "2008-03-31", "2008-03-31") == 2_989.70
    assert value(rows, "investing_cf", *span) == -30_186e6
    assert value(rows, "cash_end", "2008-03-31", "2008-03-31") == 193_492e6
    assert {r["available_at"] for r in rows} == {"2008-05-13T15:00:00Z"}


def test_parenthesised_us_gaap_title_is_not_defaulted_to_japanese_gaap():
    text = (FIXTURES / "tanshin_jpgaap_nomarker_fn.txt").read_text()
    text = text.replace("決算短信", "決算短信（米国会計基準）", 1)
    rows = parse_summary(text, issuer_id="X", source_url="u", retrieved_at="2026-10-21T02:00:00Z")
    assert {r["accounting_basis"] for r in rows} == {"US-GAAP"}
    assert {r["basis_printed"] for r in rows} == {True}


@pytest.mark.parametrize("text", ["", "\x0c", "㻞㻜㻞㻡ᖺ㻟᭶ᮇ ➨㻟ᅄ༙ᮇỴ⟬▷ಙ"])
def test_image_only_or_unmapped_font_page_says_so(text):
    with pytest.raises(ValueError, match="no 決算短信 title"):
        parse_summary(text, issuer_id="X", source_url="u", retrieved_at="2026-10-21T02:00:00Z")


def test_correction_notice_is_not_read_as_a_release():
    # 2016-10-28: orders and backlog of past releases corrected (a US subsidiary's count)
    notice = "平成 28 年 10 月 28 日\n(訂正) 過年度決算短信等の一部訂正に関するお知らせ\n当社米国子会社 Tokyo Electron America, Inc.\n"
    with pytest.raises(ValueError, match="連結経営成績"):
        parse_summary(notice, issuer_id="X", source_url="u", retrieved_at="2026-10-21T02:00:00Z")


def test_pre_2008_quarterly_title_is_a_release():
    # FY2008/3 quarterly summaries were titled 四半期財務・業績の概況
    text = (FIXTURES / "tanshin_jpgaap_nomarker_fn.txt").read_text()
    text = text.replace("決算短信", "第1四半期財務 ・ 業績の概況", 1)
    assert "決算短信" not in text
    rows = parse_summary(text, issuer_id="X", source_url="u", retrieved_at="2026-10-21T02:00:00Z")
    assert value(rows, "revenue", "2007-04-01", "2008-03-31") == 906_091e6


def test_share_counts_from_the_notes_page():
    notes = (FIXTURES / "tanshin_ifrs_q1_notes.txt").read_text()
    rows = parse("tanshin_ifrs_q1.txt", notes=notes)
    assert value(rows, "shares_issued", "2026-06-30", "2026-06-30") == 732_000_000
    assert value(rows, "shares_issued", "2026-03-31", "2026-03-31") == 732_000_000
    assert value(rows, "treasury_shares", "2026-06-30", "2026-06-30") == 8_033_510
    assert value(rows, "treasury_shares", "2026-03-31", "2026-03-31") == 6_484_224
    assert value(rows, "shares_average", "2026-04-01", "2026-06-30") == 724_402_054
    assert value(rows, "shares_average", "2025-04-01", "2025-06-30") == 732_364_731
    assert {r["unit"] for r in rows if r["metric"].startswith("shares")} == {"shares"}
    assert audit_inputs(rows)["ok"] is True


def test_a_footnote_naming_trust_shares_is_not_a_share_count():
    notes = (FIXTURES / "tanshin_ifrs_q1_notes.txt").read_text() + (
        "  (注)期末自己株式数には、「役員報酬BIP信託」が保有する当社株式(2027年3月期1Q 1,308,766株)を含めております。\n"
    )
    rows = parse("tanshin_ifrs_q1.txt", notes=notes)
    assert value(rows, "treasury_shares", "2026-06-30", "2026-06-30") == 8_033_510


def test_heisei_two_digit_quarter_labels_in_share_counts():
    notes = (
        "(4) 発行済株式数（普通株式）\n"
        "  ① 期末発行済株式数（自己株式を含む）  21年3月期第2四半期 180,610,911株  20年3月期  180,610,911株\n"
        "  ② 期末自己株式数  21年3月期第2四半期 1,661,218株  20年3月期  1,678,927株\n"
    )
    rows = parse("tanshin_usgaap_fn.txt", notes=notes)  # a 平成 document
    assert value(rows, "shares_issued", "2008-09-30", "2008-09-30") == 180_610_911
    assert value(rows, "treasury_shares", "2008-03-31", "2008-03-31") == 1_678_927


from portfolio_analyzer.ai_bubble.jp import parse_summary_ixbrl  # noqa: E402

IXBRL = Path(__file__).parent / "fixtures" / "ai_bubble" / "tdnet_summary_ifrs_q1.htm"


def _ixbrl_rows():
    return parse_summary_ixbrl(
        IXBRL.read_bytes(),
        issuer_id="285A.T",
        source_url="https://www2.jpx.co.jp/disc/285A0/x-ixbrl.htm",
        retrieved_at="2026-10-21T03:00:00Z",
    )


def _one(rows, metric, end):
    found = [r for r in rows if r["metric"] == metric and r["period_end"] == end]
    assert len(found) == 1, found
    return found[0]


def test_ixbrl_summary_reads_tagged_results_with_their_context_periods():
    rows = _ixbrl_rows()
    revenue = _one(rows, "revenue", "2026-06-30")
    assert revenue["value"] == 1_767_117e6
    assert revenue["period_start"] == "2026-04-01"
    assert revenue["accounting_basis"] == "IFRS"
    # released Friday 2026-07-31: usable from Monday 00:00 JST
    assert revenue["published_at"] == "2026-07-30T15:00:00Z"
    assert revenue["available_at"] == "2026-08-02T15:00:00Z"
    assert _one(rows, "revenue", "2025-06-30")["value"] == 342_799e6
    assert _one(rows, "eps_basic", "2026-06-30")["unit"] == "JPY/shares"
    assert _one(rows, "eps_basic", "2026-06-30")["value"] == pytest.approx(1539.91)


def test_ixbrl_summary_applies_the_sign_attribute():
    assert _one(_ixbrl_rows(), "investing_cf", "2025-06-30")["value"] == -221_512e6


def test_ixbrl_summary_skips_forecasts_parent_only_figures_and_change_rates():
    rows = _ixbrl_rows()
    assert not [r for r in rows if r["period_end"] == "2026-09-30"]
    assert {r["metric"] for r in rows} == {
        "revenue",
        "operating_income",
        "pretax_income",
        "net_income",
        "investing_cf",
        "eps_basic",
        "equity_parent",
        "equity_total",
        "shares_issued",
        "treasury_shares",
    }
    assert len([r for r in rows if r["metric"] == "revenue"]) == 2


def test_ixbrl_summary_takes_share_counts_from_the_company_context():
    rows = _ixbrl_rows()
    issued = _one(rows, "shares_issued", "2026-06-30")
    assert (issued["value"], issued["unit"], issued["period_start"]) == (
        548_015_088,
        "shares",
        "2026-06-30",
    )


def test_ixbrl_nil_is_an_explained_gap():
    equity = _one(_ixbrl_rows(), "equity_total", "2026-06-30")
    assert equity["value"] is None
    assert equity["quality"] == "missing:nil_in_release"
