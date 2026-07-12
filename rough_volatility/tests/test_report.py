"""Offline, structural and equation-rendering tests for the HTML report."""

import json
import re
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from rough_volatility.config import ProjectConfig
from rough_volatility.experiments import run_all
from rough_volatility.notebook import SECTIONS
from rough_volatility.report import (
    EQUATIONS,
    REPORT_FIGURE_ANCHORS,
    build_standalone_report,
    render_equation_svg,
)


def _report_config() -> ProjectConfig:
    base = ProjectConfig(profile="report-test", seed=1210)
    return replace(
        base,
        fbm=replace(
            base.fbm, h_values=(0.1, 0.5), n_steps=96, n_paths=8, n_display_paths=2, n_lags=7
        ),
        hurst=replace(
            base.hurst, h_values=(0.1, 0.5), sample_sizes=(64, 96), n_replications=3, n_lags=7
        ),
        ou=replace(base.ou, n_steps=96, n_paths=5, burn_in_steps=24),
        bergomi=replace(
            base.bergomi, n_steps=20, n_paths=300, chunk_size=150, keep_paths=4, h_grid=(0.1, 0.5)
        ),
        options=replace(
            base.options, maturities=(0.25, 0.5, 1.0), n_strikes=7, skew_maturity_steps=16
        ),
        hawkes=replace(
            base.hawkes, horizon=40.0, target_rate=2.0, max_events=2000, intensity_grid_points=100
        ),
        microstructure=replace(base.microstructure, rv_window=5, intensity_window=5),
        noise=replace(
            base.noise,
            n_steps=128,
            n_replications=3,
            noise_stds=(0.0, 0.1),
            strides=(1, 2),
            estimators=("variogram",),
        ),
    )


@pytest.mark.parametrize("equation", EQUATIONS.values())
def test_every_equation_renders_to_svg_data_uri(equation: str) -> None:
    rendered = render_equation_svg(equation)
    assert rendered.startswith("data:image/svg+xml;base64,")
    assert len(rendered) > 500


def test_report_is_self_contained_interactive_and_complete(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    output = build_standalone_report(config, tmp_path, manifest)
    html = output.read_text(encoding="utf-8")
    assert output.name == "rough_volatility_report_en.html"
    assert 1_000_000 < output.stat().st_size < 25_000_000
    assert not re.search(r"(?:src|href)=[\"']https?://", html, flags=re.IGNORECASE)
    assert "cdn.plot.ly" not in html.lower()
    assert html.lower().count("plotly.js v") == 1
    assert html.count("Plotly.newPlot") >= len(REPORT_FIGURE_ANCHORS)
    assert "metric-card" in html
    assert "Monte Carlo" in html
    assert len(SECTIONS) == 26
    for section in SECTIONS:
        assert f'id="{section.anchor}"' in html


def test_locale_controls_language_and_filename(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja")
    assert ja.name == "rough_volatility_report_ja.html"
    text = ja.read_text(encoding="utf-8")
    assert '<html lang="ja">' in text
    assert "ラフボラティリティ・ビジュアルラボ" in text


def test_section_headings_are_localized(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    assert "From rough paths to option skew and order flow" in en
    assert "ラフパスからオプション・スキューと注文フローへ" in ja
    assert "From rough paths to option skew and order flow" not in ja


def test_callouts_are_localized_and_interpolated(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    powers = pd.read_csv(manifest["skew_power_law"])
    target = powers.iloc[(powers["h"] - config.bergomi.h).abs().argmin()]
    beta_text = f"β={float(target['beta']):.3f}"
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    assert "合成ラボは市場データを用いずに" in ja  # executive-summary callout prose
    assert beta_text in ja  # interpolated skew value survives translation
    assert "H changes path regularity" not in ja  # EN callout fully replaced


def _plotly_json_text(value: str) -> str:
    """Encode a string the way Plotly's `to_html()` embeds figure titles:
    as JSON with `ensure_ascii=True`, so non-ASCII characters appear as
    `\\uXXXX` escapes inside the inline `Plotly.newPlot(...)` payload rather
    than as literal UTF-8 text."""
    return json.dumps(value)[1:-1]


def test_captions_and_evidence_note_localized(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    assert "根拠:" in ja  # evidence note prefix, JA
    assert "Evidence: locally generated" not in ja
    assert "<h3>検証ゲート</h3>" in ja  # validation_gates_heading, JA
    assert "<h3>Validation gates</h3>" not in ja
    # "Validation gates" also appears verbatim as a _metric_cards label, which
    # stays English by design; only the <h3> heading text is localized.

    # Figure titles/subtitles are rendered by Plotly's `to_html()`, which
    # serializes the figure layout as `ensure_ascii=True` JSON, so the
    # translated Japanese text shows up as `\uXXXX` escapes in the HTML
    # source rather than literal characters.
    assert _plotly_json_text("Hawkesイベント・ラスター") in ja  # figure.hawkes_events.title
    assert "Hawkes event raster" not in ja
    assert _plotly_json_text("条件付きHawkes強度") in ja  # figure.hawkes_intensity.title
    assert "Conditional Hawkes intensity" not in ja
    assert _plotly_json_text("フラクショナル・ブラウン運動のパス") in ja  # figure.fbm_paths.title
    assert _plotly_json_text("フラクショナル・ガウスノイズの増分") in ja  # figure.fgn_increments.title
    assert _plotly_json_text("拡大時の局所的なラフネス") in ja  # figure.fbm_zoom.title
    # EN report keeps the original captions untouched (plain ASCII, so no
    # escaping distinction applies).
    assert "Fractional Brownian-motion paths" in en
    assert "Hawkes event raster" in en
