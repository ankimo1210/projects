"""End-to-end test for the johnhull portal generator.

Rendering exercises every figure builder (so a broken ``plotly_*`` helper fails
here) and checks the output is self-contained and offline-safe — same contract
as ``analytics/report``.
"""

import re

from report_builder.figures import BOOKS, FIGURES, figures_for
from report_builder.render import render_site

PAGES = ("index", "gallery", "integration", "options_core", "numerics", "risk_credit", "stochastic")


def test_registry_is_consistent():
    assert set(BOOKS) == {"options_core", "numerics", "risk_credit", "stochastic"}
    for f in FIGURES:
        assert f.book in BOOKS, f.id
    assert len(figures_for("options_core")) == 3
    assert len(figures_for("numerics")) == 1
    assert len(figures_for("risk_credit")) == 2
    assert len(figures_for("stochastic")) == 3
    assert len(FIGURES) == 9


def test_every_figure_builds():
    for spec in FIGURES:
        fig = spec.build()
        assert fig.__class__.__name__ == "Figure"
        assert len(fig.data) >= 1


def test_render_site_is_offline_and_complete(tmp_path):
    out = render_site(output_dir=tmp_path, log=lambda *_a: None)

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
