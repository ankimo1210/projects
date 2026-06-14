"""Render the static portal: figures -> HTML fragments -> templated pages.

Offline self-contained: plotly.min.js is written once to ``assets/`` and each
page references it relatively, so the site works with no network access.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import jinja2
import plotly.io as pio
from plotly.offline import get_plotlyjs

from .figures import BOOKS, FIGURES, figures_for
from .theme import apply_theme

PKG_DIR = Path(__file__).resolve().parent
REPORT_DIR = PKG_DIR.parent
TEMPLATES_DIR = REPORT_DIR / "templates"
ASSETS_SRC = REPORT_DIR / "assets"
SITE_DIR = REPORT_DIR / "site"


def _env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _fragment(spec, log) -> dict:
    """Build one figure and return its embeddable HTML + metadata."""
    log(f"  building {spec.id} ...")
    fig = apply_theme(spec.build())
    html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        include_mathjax=False,
        div_id=f"fig-{spec.id}",
        default_width="100%",
        config={
            "displaylogo": False,
            "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )
    return {
        "id": spec.id,
        "book": spec.book,
        "title": spec.title,
        "blurb": spec.blurb,
        "practice": spec.practice,
        "is_new": spec.is_new,
        "tags": list(spec.tags),
        "html": html,
    }


def render_site(output_dir: Path | None = None, log=print) -> Path:
    out = Path(output_dir) if output_dir is not None else SITE_DIR
    out.mkdir(parents=True, exist_ok=True)
    assets_out = out / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)

    log("Writing offline plotly.min.js ...")
    (assets_out / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    if (ASSETS_SRC / "style.css").exists():
        shutil.copyfile(ASSETS_SRC / "style.css", assets_out / "style.css")

    log(f"Building {len(FIGURES)} figures ...")
    fragments = [_fragment(spec, log) for spec in FIGURES]
    by_book = {key: [fr for fr in fragments if fr["book"] == key] for key in BOOKS}
    n_new = sum(1 for fr in fragments if fr["is_new"])

    env = _env()
    books = list(BOOKS.values())
    counts = {key: len(figures_for(key)) for key in BOOKS}

    common = {"books": books, "counts": counts, "n_figures": len(fragments), "n_new": n_new}

    log("Rendering pages ...")
    (out / "index.html").write_text(
        env.get_template("index.html.j2").render(active="index", **common), encoding="utf-8"
    )
    (out / "gallery.html").write_text(
        env.get_template("gallery.html.j2").render(active="gallery", fragments=fragments, **common),
        encoding="utf-8",
    )
    (out / "integration.html").write_text(
        env.get_template("integration.html.j2").render(active="integration", **common),
        encoding="utf-8",
    )
    for meta in books:
        (out / f"{meta.key}.html").write_text(
            env.get_template("book.html.j2").render(
                active=meta.key, book=meta, fragments=by_book[meta.key], **common
            ),
            encoding="utf-8",
        )

    log(f"Done. Site at {out / 'index.html'}")
    return out


def render_standalone(out_file: Path, log=print) -> Path:
    """Render ONE fully self-contained HTML file (plotly + CSS inlined).

    Unlike the multi-page site (which references ``assets/`` relatively), this
    single file renders anywhere — convenient to share or open from any path.
    """
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    log(f"Building {len(FIGURES)} figures (standalone) ...")
    fragments = [_fragment(spec, log) for spec in FIGURES]
    css = (ASSETS_SRC / "style.css").read_text(encoding="utf-8")

    html = (
        _env()
        .get_template("standalone.html.j2")
        .render(
            books=list(BOOKS.values()),
            fragments=fragments,
            plotly_js=get_plotlyjs(),
            css=css,
            n_figures=len(fragments),
            n_new=sum(1 for fr in fragments if fr["is_new"]),
        )
    )
    out_file.write_text(html, encoding="utf-8")
    log(f"Done. Standalone report at {out_file}")
    return out_file
