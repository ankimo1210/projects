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
