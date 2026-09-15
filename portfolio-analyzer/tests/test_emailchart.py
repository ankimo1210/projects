"""Offline tests for the table-based charts that ride inside the email body.

Mail clients drop <script>, inline SVG and (in Gmail's case) rewrite the
Content-ID of an attached image, so the figures are drawn with table cells.
"""

from __future__ import annotations

from portfolio_analyzer import emailchart


def test_scale_maps_the_peak_to_the_plot_and_keeps_one_factor_for_both_signs() -> None:
    assert emailchart.scale([100.0, -50.0, 0.0], up_px=80, dn_px=40) == [80, -40, 0]
    assert emailchart.scale([100.0, -50.0], up_px=80, dn_px=80) == [80, -40]


def test_scale_survives_an_all_zero_or_empty_series() -> None:
    assert emailchart.scale([0.0, 0.0], up_px=80, dn_px=80) == [0, 0]
    assert emailchart.scale([], up_px=80, dn_px=80) == []
    assert emailchart.scale([None, 5.0, None], up_px=80, dn_px=80) == [0, 80, 0]


def test_columns_draws_one_cell_per_point_and_colors_by_sign() -> None:
    html = emailchart.columns([10.0, -10.0], labels=["1月", "2月"])
    assert html.count("<td") >= 2
    assert f"solid {emailchart.UP}" in html and f"solid {emailchart.DN}" in html
    assert "<script" not in html and "<svg" not in html


def test_marks_never_rely_on_a_css_background() -> None:
    # Gmail's send path strips the CSS background shorthand (measured); borders,
    # padding and the bgcolor attribute survive it, so every mark is one of those.
    assert "background" not in emailchart.columns([10.0, -10.0])
    assert "background" not in emailchart.line([10.0, -10.0])
    assert "background" not in emailchart.hbars([("A", 5.0, "+5%"), ("B", -5.0, "−5%")])


def test_columns_escape_the_axis_text() -> None:
    assert "&lt;b&gt;" in emailchart.columns([1.0], fmt=lambda v: "<b>")


def test_columns_merge_the_empty_stretch_but_not_the_bars_when_there_is_a_gap() -> None:
    html = emailchart.columns([1.0, 1.0, -1.0, -1.0], total_px=20, col_w=10, gap=2)
    assert html.count("solid #C05C33") == 2  # two bars, drawn apart
    assert '<td width="22"' in html  # the empty run beneath them is one cell


def test_line_merges_a_flat_run_into_one_column() -> None:
    flat = emailchart.line([5.0] * 10, total_px=20, col_w=10, zero=False)
    assert flat.count("solid #C05C33") == 1  # one stroke for the whole run
    assert 'width="100"' in flat


def test_hbars_are_proportional_and_signed() -> None:
    html = emailchart.hbars([("XLE", 46.2, "+648,558"), ("2561", -9.3, "−18,979")])
    assert "XLE" in html and "2561" in html
    assert f'bgcolor="{emailchart.UP}"' in html and f'bgcolor="{emailchart.DN}"' in html


def test_hbars_handles_a_single_row_without_dividing_by_zero() -> None:
    assert "QQQ" in emailchart.hbars([("QQQ", 0.0, "—")])


def test_split_allocates_the_plot_in_proportion_to_the_two_extents() -> None:
    assert emailchart.split([100.0, -100.0], total=80) == (40, 40)
    assert emailchart.split([300.0, -100.0], total=80) == (60, 20)


def test_split_gives_the_whole_plot_to_a_one_sided_series() -> None:
    assert emailchart.split([5.0, 2.0], total=80) == (80, 0)
    assert emailchart.split([-5.0, -2.0], total=80) == (0, 80)
    assert emailchart.split([], total=80) == (80, 0)


def test_columns_sizes_its_halves_from_the_data_when_asked() -> None:
    html = emailchart.columns([300.0, -100.0], total_px=80)
    assert 'height="60"' in html and 'height="20"' in html


def test_columns_drops_the_half_that_holds_nothing() -> None:
    html = emailchart.columns([5.0, 2.0], total_px=80)
    assert emailchart.DN not in html
    assert html.count('style="height:') == 1  # one half wrapper, not an empty second one


def test_columns_merge_equal_neighbours_when_the_bars_touch() -> None:
    # An area chart (no gap) should not draw a seam through a flat run.
    flat = emailchart.columns([5.0, 5.0, 5.0, 1.0], total_px=40, col_w=10, gap=0)
    assert flat.count("solid #C05C33") == 2  # one cell for the run, one for the step
    assert 'width="30"' in flat


def test_columns_keep_every_bar_separate_when_there_is_a_gap() -> None:
    bars = emailchart.columns([5.0, 5.0, 5.0], total_px=40, col_w=10, gap=3)
    assert bars.count("solid #C05C33") == 3


def test_columns_print_the_axis_when_given_a_formatter() -> None:
    html = emailchart.columns([5.0, -5.0], total_px=40, fmt=lambda v: f"{v:+.0f}")
    assert "+5" in html and "-5" in html and ">0<" in html


def test_ticks_can_fall_on_every_month_start() -> None:
    labels = ["2026-07-30", "2026-07-31", "2026-08-03", "2026-08-04", "2026-09-01"]
    assert emailchart.ticks(labels, months=None) == [(2, "26/08"), (4, "26/09")]


def test_line_connects_each_point_to_the_previous_one() -> None:
    # a rising step draws the vertical connector, not a floating dash
    html = emailchart.line([0.0, 10.0], total_px=20, col_w=10, thickness=2, zero=False)
    assert html.count(f"solid {emailchart.UP}") == 3  # start, riser, end
    # the flat start (its riser merged into it) sits at the foot: 18px of padding, then the stroke
    assert (
        f'<td width="10" valign="top" style="padding-top:18px"><div style="border-top:2px solid {emailchart.UP}">'
        in html
    )
    # the riser is stroke-wide and runs the whole 18px of rise plus the stroke, from the top
    assert f'<td width="2" valign="top"><div style="border-top:20px solid {emailchart.UP}">' in html
    # the level beside it sits at the top
    assert f'<td width="8" valign="top"><div style="border-top:2px solid {emailchart.UP}">' in html


def test_line_fills_under_the_line_with_a_tint_by_sign() -> None:
    html = emailchart.line([10.0, 10.0, -10.0, -10.0], total_px=40, zero=True)
    assert f"solid {emailchart.UP_TINT}" in html
    assert f"solid {emailchart.DN_TINT}" in html
    bare = emailchart.line([10.0, 10.0, -10.0, -10.0], total_px=40, zero=True, fill=False)
    assert emailchart.UP_TINT not in bare and emailchart.DN_TINT not in bare


def test_line_skips_a_missing_point_and_carries_on_from_the_last_known() -> None:
    html = emailchart.line([5.0, None, 5.0], total_px=20, col_w=10, zero=False)
    assert html.count(f"solid {emailchart.UP}") == 2


def test_sparkline_has_no_zero_rule_and_no_axis() -> None:
    html = emailchart.line([3.0, 4.0, 2.0], total_px=20, zero=False)
    assert f'bgcolor="{emailchart.RULE}"' not in html


def test_line_prints_the_axis_when_given_a_formatter() -> None:
    html = emailchart.line([10.0, -4.0], total_px=40, zero=True, fmt=lambda v: f"{v:+.0f}")
    assert "+10" in html and "-4" in html and ">0<" in html


def test_ticks_fall_on_quarter_starts() -> None:
    labels = ["2025-09-11", "2025-09-30", "2025-10-01", "2025-10-02", "2026-01-05", "2026-02-02"]
    assert emailchart.ticks(labels) == [(2, "25/10"), (4, "26/01")]


def test_line_draws_a_second_series_in_its_own_colour_under_the_first() -> None:
    html = emailchart.line(
        [0.0, 10.0], total_px=20, col_w=10, zero=False, overlay=[5.0, 5.0], overlay_color="#123456"
    )
    assert f"solid {emailchart.UP}" in html and "solid #123456" in html
    # the gap between the two strokes is painted in the ground colour, not dropped
    assert f"solid {emailchart.CARD}" in html


def test_line_range_takes_in_the_overlay_so_neither_series_is_clipped() -> None:
    html = emailchart.line([5.0, 5.0], total_px=20, col_w=10, zero=False, overlay=[0.0, 10.0])
    # the primary sits mid-plot, not at the foot as it would on its own range
    assert 'style="padding-top:9px"><div style="border-top:2px solid #C05C33">' in html


def test_line_draws_a_level_across_the_plot() -> None:
    html = emailchart.line(
        [0.0, 0.0], total_px=20, col_w=10, zero=False, level=10.0, level_color="#654321"
    )
    # a flat line under a constant level is one merged column: level on top, line at the foot
    assert html.count("solid #654321") == 1
    assert 'style="padding-top:1px"><div style="border-top:1px solid #654321">' in html


def test_line_puts_trade_marks_in_a_strip_under_the_plot() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    plain = emailchart.line(values, total_px=20, col_w=10, zero=False)
    marked = emailchart.line(values, total_px=20, col_w=10, zero=False, marks=[(1, 1), (3, -1)])
    assert marked.count(f"solid {emailchart.UP}") == plain.count(f"solid {emailchart.UP}") + 1
    assert emailchart.DN not in plain and f"solid {emailchart.DN}" in marked


def test_line_without_a_zero_rule_prints_the_high_and_the_low() -> None:
    html = emailchart.line([100.0, 250.0], total_px=40, zero=False, fmt=lambda v: f"{v:.0f}")
    assert ">250<" in html and ">100<" in html and ">0<" not in html


def test_shares_draws_one_proportional_bar_per_row() -> None:
    html = emailchart.shares([("日本株", 60.0, "29%"), ("現金", 30.0, "20%")], width=200)
    assert "日本株" in html and "現金" in html and "29%" in html
    assert '<td width="200"' in html and '<td width="100"' in html
    assert "background" not in html


def test_line_writes_the_ticks_under_the_plot() -> None:
    labels = ["2025-09-30", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", "2025-10-07"]
    html = emailchart.line([1.0] * 6, labels=labels, total_px=20, col_w=10, zero=False)
    assert "25/10" in html


def test_strips_are_proportional_to_the_magnitude_and_coloured_by_sign() -> None:
    html = emailchart.strips([("A", -10.0, "−10%"), ("B", 5.0, "+5%"), ("C", 0.0, "0%")], width=100)
    assert 'width="100" bgcolor="#2A6DA6"' in html  # the loss, full length, in the down colour
    assert 'width="50" bgcolor="#C05C33"' in html  # half as long, in the up colour
    assert 'width="0" style' in html and "background" not in html
    assert html.count("<tr>") == 3 + 3  # one row each, and one bar table each
