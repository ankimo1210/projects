"""Offline tests for the chart screenshot helper (no browser)."""

from __future__ import annotations

import pytest
from portfolio_analyzer import chartshot


def test_parse_box_reads_the_published_geometry() -> None:
    dom = '<html><body data-chart-box="120,1480"><div>…</div></body></html>'
    assert chartshot.parse_box(dom) == (120, 1480)


def test_parse_box_raises_when_the_page_never_published_one() -> None:
    with pytest.raises(RuntimeError, match="chart box"):
        chartshot.parse_box("<html><body></body></html>")


def test_crop_box_pads_and_clamps_to_the_image() -> None:
    assert chartshot.crop_box(100, 500, width=1100, height=2000, pad=12) == (0, 88, 1100, 512)
    assert chartshot.crop_box(4, 2400, width=1100, height=2000, pad=12) == (0, 0, 1100, 2000)


def test_retheme_forces_the_root_theme() -> None:
    page = '<!doctype html>\n<html lang="ja" data-theme="dark">\n<head></head>'
    out = chartshot.retheme(page, "light")
    assert 'data-theme="light"' in out and 'data-theme="dark"' not in out
    assert chartshot.retheme('<html lang="ja">', "light") == '<html lang="ja">'


def test_parse_pieces_reads_the_boxes_the_page_published() -> None:
    dom = '<body data-pieces="{&quot;nav&quot;:[10,20,540,190],&quot;price:XLE@gb&quot;:[10,300,520,120]}">'
    assert chartshot.parse_pieces(dom) == {
        "nav": (10, 20, 540, 190),
        "price:XLE@gb": (10, 300, 520, 120),
    }


def test_parse_pieces_raises_when_the_page_never_published_them() -> None:
    with pytest.raises(RuntimeError, match="pieces"):
        chartshot.parse_pieces("<html><body></body></html>")


def test_piece_box_pads_scales_and_clamps() -> None:
    assert chartshot.piece_box((10, 20, 540, 190), scale=2, pad=4, size=(2200, 9000)) == (
        12,
        32,
        1108,
        428,
    )
    assert chartshot.piece_box((0, 0, 100, 50), scale=2, pad=4, size=(150, 90)) == (0, 0, 150, 90)
