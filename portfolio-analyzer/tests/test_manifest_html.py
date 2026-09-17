"""Offline tests for the self-contained renderer of the main dashboard artifact."""

from __future__ import annotations

import re
from pathlib import Path

from portfolio_analyzer import build_artifact, load_analysis_reference, load_portfolio
from portfolio_analyzer import manifest_html as mh

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_formats_follow_the_manifest_format_names() -> None:
    assert mh.fmt(45907922.28, "currency") == "45,907,922 円"
    assert mh.fmt(-580654.46, "currency") == "−580,654 円"
    assert mh.fmt(0.20521, "percent") == "20.5%"
    assert mh.fmt(-0.0431, "percent") == "−4.3%"
    assert mh.fmt(26.3501, "number") == "26.35"
    assert mh.fmt(304000.0, "number") == "304,000"
    assert mh.fmt(None, "currency") == "—"
    assert mh.fmt("海外証券口座", None) == "海外証券口座"
    assert mh.fmt(True, None) == "はい"


def test_compact_yen_for_axes_and_bar_labels() -> None:
    assert mh.compact_yen(45907922) == "4,591万"
    assert mh.compact_yen(-656000) == "−66万"
    assert mh.compact_yen(250_000_000) == "2.5億"
    assert mh.compact_yen(8200) == "8,200"


def test_markdown_subset() -> None:
    body = (
        "## 見出し\n\n"
        "本文に **太字** と `data/x.json`、[出典](https://example.com/a?b=1&c=2)。\n"
        "続きの行 <script>\n\n"
        "- **株式全体**: 目標損失 $L^*$ と $\\Sigma$\n"
        "- Brentが$105へ急伸\n"
        "- [悪い](javascript:alert(1))"
    )
    out = mh.markdown(body)
    assert "<h2>見出し</h2>" in out
    assert "<strong>太字</strong>" in out
    assert "<code>data/x.json</code>" in out
    assert '<a href="https://example.com/a?b=1&amp;c=2">出典</a>' in out
    assert "&lt;script&gt;" in out and "<script>" not in out
    assert out.count("<li>") == 3
    assert "<i class='m'>L<sup>*</sup></i>" in out
    assert "<i class='m'>Σ</i>" in out
    assert "$105" in out  # a price is not math
    assert "javascript:" not in out


def test_display_math_is_laid_out_not_left_as_tex() -> None:
    body = (
        "前文\n\n"
        "$$s^* = -L^* \\frac{\\Sigma b}{b^\\top \\Sigma b}, \\qquad "
        "d = \\frac{L^*}{\\sqrt{b^\\top \\Sigma b}}$$\n\n後文"
    )
    out = mh.markdown(body)
    assert "<div class='eq'>" in out
    assert out.count("<span class='fr'>") == 2
    assert "√" in out and "Σ" in out and "<sup>⊤</sup>" in out
    assert "\\" not in out and "$$" not in out


def test_a_reference_line_near_the_right_edge_labels_to_its_left() -> None:
    chart = {
        "id": "s",
        "type": "horizontalBar",
        "encodings": {"x": {"field": "k"}, "y": {"field": "v", "format": "currency"}},
        "referenceLines": [{"axis": "x", "value": 0, "label": "現在"}],
    }
    out = mh.horizontal_bar(chart, [{"k": "a", "v": -5.0}, {"k": "b", "v": -2.0}])
    assert "class='ref end'" in out


def test_horizontal_bar_sorts_labels_values_and_tooltips() -> None:
    chart = {
        "id": "stress",
        "title": "簡易ストレス",
        "type": "horizontalBar",
        "encodings": {
            "x": {"field": "scenario", "label": "シナリオ"},
            "y": {"field": "impact_jpy", "label": "評価額変化", "format": "currency"},
            "tooltip": [{"field": "impact_ratio", "label": "変化率", "format": "percent"}],
        },
        "valueFormat": "currency",
        "referenceLines": [{"axis": "x", "value": 0, "label": "現在"}],
        "settings": {"sort": "descending", "showValues": True},
    }
    rows = [
        {"scenario": "株安", "impact_jpy": -2_000_000, "impact_ratio": -0.04},
        {"scenario": "円安", "impact_jpy": 500_000, "impact_ratio": 0.01},
    ]
    out = mh.horizontal_bar(chart, rows)
    assert out.count("<span class='bar") == 2
    assert out.index("円安") < out.index("株安")  # descending
    assert "title='株安: −2,000,000 円 · 変化率 −4.0%'" in out
    assert "−200万" in out and "50万" in out
    assert "class='ref'" in out


def test_stacked_bar_100_has_a_legend_and_shares() -> None:
    chart = {
        "id": "currencies",
        "title": "通貨別",
        "type": "stackedBar100",
        "encodings": {
            "x": {"field": "scope", "label": "範囲"},
            "y": {"field": "market_value_jpy", "label": "評価額"},
            "color": {"field": "currency", "label": "通貨"},
        },
    }
    rows = [
        {"scope": "すべて", "currency": "JPY", "market_value_jpy": 750.0},
        {"scope": "すべて", "currency": "USD", "market_value_jpy": 250.0},
    ]
    out = mh.stacked_bar_100(chart, rows)
    assert "class='legend'" in out and "JPY" in out and "USD" in out
    assert "75.0%" in out and "25.0%" in out


def test_line_chart_draws_one_path_and_a_zero_line() -> None:
    chart = {
        "id": "corr",
        "title": "株債相関",
        "type": "line",
        "encodings": {
            "x": {"field": "date", "type": "temporal", "label": "週"},
            "y": {"field": "c", "label": "相関", "format": "number"},
            "tooltip": [{"field": "regime", "label": "判定"}],
        },
    }
    rows = [
        {"date": "2026-01-05", "c": -0.2, "regime": "ヘッジ"},
        {"date": "2026-01-12", "c": 0.1, "regime": "同時安"},
        {"date": "2026-01-19", "c": None, "regime": ""},
    ]
    svg = mh.line_chart(chart, rows)
    assert svg.count("<path class='line'") == 1
    assert "class='zero'" in svg
    assert "<title>2026-01-12: 0.10 · 判定 同時安</title>" in svg


def test_table_sorts_formats_and_scrolls() -> None:
    table = {
        "id": "t",
        "title": "表",
        "subtitle": "注記",
        "defaultSort": {"field": "v", "direction": "desc"},
        "columns": [
            {"field": "name", "label": "名前", "type": "text"},
            {"field": "v", "label": "評価額", "format": "currency"},
            {"field": "w", "label": "比率", "format": "percent"},
        ],
    }
    rows = [
        {"name": "A", "v": 100.0, "w": 0.1},
        {"name": "Z", "v": 0.0, "w": 0.0},
        {"name": "N", "v": None, "w": 0.0},
        {"name": "B", "v": 300.0, "w": None},
    ]
    out = mh.table(table, rows)
    assert out.index(">B<") < out.index(">A<") < out.index(">Z<") < out.index(">N<")
    assert "300 円" in out and "10.0%" in out and "—" in out
    assert "class='tw'" in out


def example_artifact() -> dict:
    portfolio = load_portfolio(PROJECT_ROOT / "data/portfolio.example.json")
    reference = load_analysis_reference(PROJECT_ROOT / "data/analysis_reference.example.json")
    return build_artifact(
        portfolio, analysis_reference=reference, generated_at="2026-08-15T00:00:00+00:00"
    )


def test_render_the_whole_example_artifact() -> None:
    artifact = example_artifact()
    manifest = artifact["manifest"]
    page = mh.render(artifact, tokens_css=":root{}")
    assert page.startswith("<!doctype html>")
    assert manifest["title"] in page
    scopes = [r["scope"] for r in artifact["snapshot"]["datasets"]["summary"]]
    for scope in scopes:
        assert f"<option value='{scope}'" in page
    # each block is on the page: filtered ones once per scope, the rest once
    targets = {t["dataset"] for t in manifest["filters"][0]["targets"]} | {"summary"}
    charts = {c["id"]: c for c in manifest["charts"]}
    tables = {t["id"]: t for t in manifest["tables"]}
    for block in manifest["blocks"]:
        count = page.count(f"data-block='{block['id']}'")
        dataset = (
            charts[block["chartId"]]["dataset"]
            if block["type"] == "chart"
            else tables[block["tableId"]]["dataset"]
            if block["type"] == "table"
            else "summary"
            if block["type"] == "metric-strip"
            else None
        )
        assert count == (len(scopes) if dataset in targets else 1), block["id"]
    # nothing is fetched at view time apart from the fonts
    assert not re.search(r"<script[^>]+src=", page)
    links = re.findall(r"<link[^>]+href=['\"]([^'\"]+)", page)
    assert all(href.startswith("https://fonts.") for href in links)
