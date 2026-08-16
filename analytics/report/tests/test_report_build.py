"""End-to-end test for the portal generator.

Rendering exercises every figure builder (so a broken ``plotly_*`` helper fails
here) and checks the output is self-contained and offline-safe.
"""

import pathlib
import re

from report_builder.figures import BOOKS, FIGURES, LINK_BOOKS, figures_for
from report_builder.render import render_site

# Fixed pages plus one showcase page per book with figures. Derived rather than
# listed so a newly registered book cannot slip past the offline checks below --
# statistics and machine_learning both did, under a hand-maintained list.
PAGES = ("index", "gallery", "integration", *BOOKS)


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


def test_every_textbook_reaches_the_portal():
    """No book may exist in the analytics tree without a route into the portal.

    statistics, quant_research and the SDE book were all finished and none of
    them appeared here; the gap was invisible because the portal's coverage was
    only ever asserted against a hand-written list of the books it already had.
    This walks the tree instead.
    """
    analytics = pathlib.Path(__file__).resolve().parents[2]
    on_disk = {p.parent.parent.name for p in analytics.glob("*/book/_toc.yml")} | {
        p.parent.parent.name for p in analytics.glob("*/*/book/_toc.yml")
    }
    on_disk.discard("report")

    routed = set(BOOKS) | {b.key for b in LINK_BOOKS}
    # LINK_BOOKS renames the two differential-equation volumes.
    aliases = {"ode-book": "diffeq_ode", "pde-book": "diffeq_pde"}
    missing = {d for d in on_disk if aliases.get(d, d) not in routed}
    assert not missing, f"textbooks with no portal route: {sorted(missing)}"


def test_the_sde_book_is_absent_on_purpose():
    """It is a server-rendered Next.js app with no static index.html, so an
    offline portal has no file to link. Recorded as a decision rather than an
    oversight -- if it ever gains a static export, add it to LINK_BOOKS."""
    sde = pathlib.Path(__file__).resolve().parents[2] / "differential_equation" / "sde-book"
    assert sde.exists(), "the SDE book moved; revisit this exemption"
    assert not (sde / "dist" / "index.html").exists(), (
        "the SDE book now emits a static index.html -- route it into the portal"
    )
    assert "diffeq_sde" not in {b.key for b in LINK_BOOKS}
