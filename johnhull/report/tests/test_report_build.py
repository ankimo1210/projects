"""End-to-end test for the johnhull portal generator.

Rendering exercises every figure builder (so a broken ``plotly_*`` helper fails
here) and checks the output is self-contained and offline-safe — same contract
as ``analytics/report``.
"""

import re

from report_builder.figures import BOOKS, FIGURES, figures_for
from report_builder.render import render_site

PAGES = ("index", "gallery", "integration", *BOOKS)


def test_registry_is_consistent():
    assert set(BOOKS) == {
        "options_core",
        "numerics",
        "risk_credit",
        "stochastic",
        "volatility",
        "rates_swaps",
        "exotics",
        "ml_derivatives",
        "volatility_frontiers",
        "crypto_market",
        "climate_energy",
    }
    for f in FIGURES:
        assert f.book in BOOKS, f.id
    assert len(figures_for("options_core")) == 7
    assert len(figures_for("numerics")) == 5
    assert len(figures_for("risk_credit")) == 8
    assert len(figures_for("stochastic")) == 3
    assert len(figures_for("volatility")) == 10
    assert len(figures_for("rates_swaps")) == 7
    assert len(figures_for("exotics")) == 2
    assert len(figures_for("ml_derivatives")) == 12
    assert len(figures_for("volatility_frontiers")) == 8
    assert len(figures_for("crypto_market")) == 4
    assert len(figures_for("climate_energy")) == 4
    assert len(FIGURES) == 70


def test_every_figure_builds():
    for spec in FIGURES:
        fig = spec.build()
        assert fig.__class__.__name__ == "Figure"
        assert len(fig.data) >= 1


def test_render_site_is_offline_and_complete(tmp_path):
    stale = tmp_path / "johnhull_gallery_standalone.html"
    stale.write_text('<script src="https://cdn.example.invalid/plotly.js"></script>')
    out = render_site(output_dir=tmp_path, log=lambda *_a: None)

    assert not stale.exists()
    for name in PAGES:
        assert (out / f"{name}.html").exists(), name
    assert (out / "assets" / "plotly.min.js").exists()
    assert (out / "assets" / "style.css").exists()

    gallery = (out / "gallery.html").read_text(encoding="utf-8")
    # One interactive figure per registry entry.
    assert gallery.count("Plotly.newPlot") == len(FIGURES)
    assert 'src="assets/plotly.min.js"' in gallery
    # Fully offline: no external URLs anywhere in the rendered pages.
    for name in PAGES:
        text = (out / f"{name}.html").read_text(encoding="utf-8")
        assert not re.search(r"https?://", text), f"external URL leaked into {name}.html"
