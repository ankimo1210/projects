"""Offline, structural and equation-rendering tests for the HTML report."""

import json
import re
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from rough_volatility.config import ProjectConfig
from rough_volatility.experiments import run_all
from rough_volatility.literature import PRIOR_WORKS
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
    # The interpolated skew value now sits inside build-time MathML, so assert
    # on the formatted digits (the sign becomes a MathML operator element).
    beta_digits = f"{abs(float(target['beta'])):.3f}"
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    assert "ボラティリティはラフである" in ja  # executive-summary callout prose
    assert beta_digits in ja  # interpolated skew value survives translation
    assert "H changes path regularity" not in ja  # EN callout fully replaced


def test_mathematical_definitions_define_every_gallery_variable(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    assert "<h3>Variable definitions</h3>" in en
    assert "<h3>変数の定義</h3>" in ja
    # One group header per gallery equation, in both editions.
    for text in (en, ja):
        assert text.count('class="variable-group"') == len(EQUATIONS)
        # Symbols and math-bearing prose are typeset as build-time MathML;
        # the 18 symbol cells alone guarantee many <math> elements.
        assert text.count("<math") >= 18
        assert "<merror" not in text
    # Spot-check localized descriptions.
    assert "Hurst exponent in" in en
    assert "Hurst 指数（" in ja
    assert "branching ratio" in en
    assert "分岐比" in ja


def test_practical_qanda_section_is_japanese_only(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    # Report-only Q&A: after the limitations section, before the margin note,
    # with several Q&A pairs and MathML-typeset formulas.
    assert 'id="practical-qanda"' in ja
    assert "実務Q&amp;A" in ja  # section heading (html.escape turns & into &amp;)
    assert ja.count('class="qa-item"') >= 6
    assert "<merror" not in ja
    assert (
        ja.index('id="limitations-next-steps"')
        < ja.index('id="practical-qanda"')
        < ja.index('id="edge-note"')
    )
    # The full handoff is referenced, not inlined.
    assert "HEDGING_HANDOFF.md" in ja
    # EN keeps the section gated off via the empty catalog body.
    assert 'id="practical-qanda"' not in en
    assert 'class="qa-item"' not in en


def test_edge_note_is_japanese_only_and_after_sections(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    # The margin note sits at the end of the content column: after the last
    # shared section and before the footer, with its math typeset as MathML.
    assert 'id="edge-note"' in ja
    assert "なぜ低い H は局所的にギザギザなのか" in ja
    assert ja.index('id="limitations-next-steps"') < ja.index('id="edge-note"')
    assert ja.index('id="edge-note"') < ja.index('class="footer"')
    assert "<merror" not in ja
    # EN keeps the note gated off via the empty catalog entry.
    assert 'id="edge-note"' not in en
    assert 'class="edge-note"' not in en


def test_prior_literature_section_is_japanese_only_for_now(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text(
        encoding="utf-8"
    )
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text(
        encoding="utf-8"
    )
    # The JA report carries the report-only literature section right after the
    # conceptual map, with the overview callout, the summary table, and one
    # card per registered prior work.
    assert 'id="prior-literature"' in ja
    assert "先行研究" in ja
    assert "Volatility is rough" in ja  # language-neutral citation text
    assert ja.count('class="lit-card"') == len(PRIOR_WORKS)
    assert (
        ja.index('id="conceptual-map"')
        < ja.index('id="prior-literature"')
        < ja.index('id="mathematical-definitions"')
    )
    # All 26 shared sections are still present alongside the inserted one.
    for section in SECTIONS:
        assert f'id="{section.anchor}"' in ja
    # The EN catalog keeps callout.prior-literature empty for now, which
    # disables the section: the EN report keeps exactly the 26 shared sections.
    assert 'id="prior-literature"' not in en
    assert 'class="lit-card"' not in en  # CSS rules remain, but no rendered cards


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

    # Helper-internal captions (previously hardcoded inside the drawing
    # helpers rather than in _build_figures) are localized the same way.
    assert _plotly_json_text("増分の自己相関") in ja  # figure.increment_acf.title
    assert "Increment autocorrelation" not in ja
    assert _plotly_json_text("IVスマイル") in ja  # figure.iv_smiles.title
    assert "Implied-volatility smiles" not in ja
    assert (
        _plotly_json_text("共通ショック下のrBergomiとHestonの比較") in ja
    )  # figure.heston_comparison.title
    assert "Rough Bergomi versus Heston under common shocks" not in ja
    # noise_bias subtitle interpolates the {estimator} name (stays EN) into JA prose.
    assert _plotly_json_text("variogram推定量。前処理モードセレクター") in ja
    assert "use the preprocessing-mode selector" not in ja
    # The shared fBM-selector subtitle (hardcoded in _fbm_selector before) is localized.
    assert _plotly_json_text("Hセレクターを使うこと") in ja  # figure.fbm_*.subtitle
    assert "Use the H selector" not in ja

    # EN report keeps the original captions untouched (plain ASCII, so no
    # escaping distinction applies).
    assert "Fractional Brownian-motion paths" in en
    assert "Hawkes event raster" in en
    assert "Increment autocorrelation" in en
    assert "variogram estimator; use the preprocessing-mode selector" in en


def test_bilingual_numeric_parity(tmp_path: Path) -> None:
    config = _report_config()
    manifest = run_all(config, tmp_path, force=True)
    from rough_volatility.report import build_reports

    outputs = build_reports(config, tmp_path, manifest)
    assert set(outputs) == {"en", "ja"}
    texts = {loc: p.read_text(encoding="utf-8") for loc, p in outputs.items()}
    assert "Rough Volatility Visual Lab" in texts["en"]
    assert "ラフボラティリティ・ビジュアルラボ" in texts["ja"]
    hashes = [re.search(r'"sha256": "([0-9a-f]+)"', t).group(1) for t in texts.values()]
    assert len(set(hashes)) == 1  # numbers identical across languages
    for t in texts.values():
        assert not re.search(r'(?:src|href)=["\']https?://', t, re.IGNORECASE)
