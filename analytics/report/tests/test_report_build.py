"""End-to-end test for the portal generator.

Rendering exercises every figure builder (so a broken ``plotly_*`` helper fails
here) and checks the output is self-contained and offline-safe.
"""

import re

from report_builder.figures import FIGURES, figures_for
from report_builder.render import render_site


def test_registry_covers_books():
    # At least these books are represented (more may be added by other textbooks).
    expected = {"linear_algebra", "neural_net", "bayesian", "laplace"}
    assert expected <= {f.book for f in FIGURES}
    for book in expected:
        assert len(figures_for(book)) >= 5
    # Inequalities (not exact counts) so concurrently-added books don't break this.
    assert sum(1 for f in FIGURES if f.is_new) >= 15
    assert len(FIGURES) >= 22


def test_every_figure_builds():
    for spec in FIGURES:
        fig = spec.build()
        assert fig.__class__.__name__ == "Figure"
        assert len(fig.data) >= 1


def test_render_site_is_offline_and_complete(tmp_path):
    out = render_site(output_dir=tmp_path, log=lambda *_a: None)

    for name in (
        "index",
        "gallery",
        "integration",
        "linear_algebra",
        "neural_net",
        "bayesian",
        "laplace",
    ):
        assert (out / f"{name}.html").exists(), name
    assert (out / "assets" / "plotly.min.js").exists()
    assert (out / "assets" / "style.css").exists()

    gallery = (out / "gallery.html").read_text(encoding="utf-8")
    # One interactive figure per registry entry.
    assert gallery.count("Plotly.newPlot") == len(FIGURES)
    assert 'src="assets/plotly.min.js"' in gallery
    # Fully offline: no external URLs anywhere in the rendered pages.
    for name in (
        "index",
        "gallery",
        "integration",
        "linear_algebra",
        "neural_net",
        "bayesian",
        "laplace",
    ):
        text = (out / f"{name}.html").read_text(encoding="utf-8")
        assert not re.search(r"https?://", text), f"external URL leaked into {name}.html"
