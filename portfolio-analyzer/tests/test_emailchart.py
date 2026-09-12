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
    assert f'bgcolor="{emailchart.UP}"' in html and f'bgcolor="{emailchart.DN}"' in html
    assert "<script" not in html and "<svg" not in html


def test_columns_carries_colour_as_an_attribute_not_a_style() -> None:
    # Gmail's send path strips every CSS background; the bgcolor attribute survives it.
    assert "background:" not in emailchart.columns([10.0, -10.0])
    assert "background:" not in emailchart.hbars([("A", 5.0, "+5%"), ("B", -5.0, "−5%")])


def test_columns_escapes_label_text() -> None:
    assert "&lt;b&gt;" in emailchart.columns([1.0], labels=["<b>"])


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
