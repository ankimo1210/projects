"""Dependency fingerprints for section evidence reuse (D1-preflight stages 2 and 4)."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from johnhull.scripts.evidence_fingerprint import (
    NORMALIZER_VERSION,
    book_section,
    compare_fingerprints,
    compute_fingerprint,
    decide,
    notebook_slice,
    page_assets,
    portal_cards,
    python_closure,
    runtime_mismatches,
)

UUID_A = "d94c3fe7-836c-4d93-85b7-ec59c746b1fc"
UUID_B = "0f0e0d0c-0b0a-4908-8706-050403020100"
BUNDLE = "<script>/**\n* plotly.js v3.7.0\n*/ var Plotly = {};</script>"


def _plot_output(uuid: str, value: float, bundle: str = "") -> dict:
    figure = {"data": [{"y": [value]}], "layout": {"meta": {"figure": "ivf_smile"}}}
    html = (
        f'{bundle}<div id="{uuid}" class="plotly-graph-div"></div>'
        f'<script>Plotly.newPlot("{uuid}", {json.dumps(figure["data"])})</script>'
    )
    return {
        "output_type": "display_data",
        "data": {"application/vnd.plotly.v1+json": figure, "text/html": [html]},
        "metadata": {},
    }


def _notebook(uuid: str = UUID_A, value: float = 1.0, prefix_cells: int = 0) -> dict:
    cells = [{"cell_type": "markdown", "id": "cell-000", "metadata": {}, "source": ["# Title"]}]
    cells += [
        {"cell_type": "markdown", "id": f"extra-{i}", "metadata": {}, "source": [f"extra {i}"]}
        for i in range(prefix_cells)
    ]
    cells += [
        {
            "cell_type": "code",
            "id": "cell-first",
            "execution_count": 1,
            "metadata": {},
            "source": ["plot()"],
            "outputs": [_plot_output(UUID_B, 0.5, bundle=BUNDLE)],
        },
        {
            "cell_type": "markdown",
            "id": "cell-h9",
            "metadata": {},
            "source": ["## 9. IVF\n", "text"],
        },
        {
            "cell_type": "code",
            "id": "cell-code",
            "execution_count": 7 + prefix_cells,
            "metadata": {},
            "source": ["ivf()"],
            "outputs": [_plot_output(uuid, value)],
        },
        {"cell_type": "markdown", "id": "cell-h10", "metadata": {}, "source": ["## 10. Next"]},
    ]
    return {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


# --- notebook slices --------------------------------------------------------------


def test_notebook_slice_ignores_plotly_div_ids():
    first, _ = notebook_slice(_notebook(uuid=UUID_A), "9. IVF")
    second, _ = notebook_slice(_notebook(uuid=UUID_B), "9. IVF")
    assert _digest(first) == _digest(second)


def test_cells_added_before_the_section_keep_the_slice():
    first, _ = notebook_slice(_notebook(), "9. IVF")
    second, _ = notebook_slice(_notebook(prefix_cells=3), "9. IVF")
    assert _digest(first) == _digest(second)


def test_notebook_slice_changes_with_the_figure_payload():
    first, _ = notebook_slice(_notebook(value=1.0), "9. IVF")
    second, _ = notebook_slice(_notebook(value=1.0 + 1e-12), "9. IVF")
    assert _digest(first) != _digest(second)


def test_notebook_slice_changes_with_the_explanation_text():
    changed = _notebook()
    changed["cells"][2]["source"] = ["## 9. IVF\n", "text, edited"]
    assert _digest(notebook_slice(_notebook(), "9. IVF")[0]) != _digest(
        notebook_slice(changed, "9. IVF")[0]
    )


def test_notebook_slice_stops_at_the_next_level_two_heading():
    changed = _notebook()
    changed["cells"][-1]["source"] = ["## 10. Next, edited"]
    assert _digest(notebook_slice(_notebook(), "9. IVF")[0]) == _digest(
        notebook_slice(changed, "9. IVF")[0]
    )


def test_embedded_plotly_bundle_becomes_a_shared_asset_digest():
    notebook = _notebook()
    notebook["cells"][1], notebook["cells"][3] = notebook["cells"][3], notebook["cells"][1]
    notebook["cells"][1]["outputs"] = [_plot_output(UUID_A, 1.0, bundle=BUNDLE)]
    content, bundles = notebook_slice(notebook, "9. IVF")
    assert "plotly.js v3.7.0" not in json.dumps(content)
    assert bundles == [hashlib.sha256(BUNDLE.encode()).hexdigest()]


def test_missing_heading_raises_lookup_error():
    with pytest.raises(LookupError, match="heading"):
        notebook_slice(_notebook(), "99. Missing")


# --- level-three slices (vol10 declares §26.11–§26.17 as ### subsections) --------


def _subsection_notebook(lookback: str = "lookback text", shout: str = "shout text") -> dict:
    def markdown(cell_id, source):
        return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": source}

    def code(cell_id, source):
        return {
            "cell_type": "code",
            "id": cell_id,
            "execution_count": 1,
            "metadata": {},
            "source": [source],
            "outputs": [],
        }

    cells = [
        markdown("h3", ["## 3. Barrier\n", "barrier text"]),
        markdown("h4", ["## 4. Paths\n", "\n", "### 4.1 Lookback\n", lookback]),
        code("c41", "lookback()"),
        markdown("h42", ["### 4.2 Shout\n", shout]),
        code("c42", "shout()"),
        markdown("h5", ["## 5. Martingales"]),
    ]
    return {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


def test_level_three_slice_starts_at_the_cell_holding_the_subsection_heading():
    content, _ = notebook_slice(_subsection_notebook(), "4.1 Lookback", level=3)
    assert [cell["source"] for cell in content] == [
        "## 4. Paths\n\n### 4.1 Lookback\nlookback text",
        "lookback()",
    ]


def test_level_three_slice_ignores_edits_to_the_next_subsection():
    edited = _subsection_notebook(shout="shout text, edited")
    assert _digest(notebook_slice(_subsection_notebook(), "4.1 Lookback", level=3)[0]) == _digest(
        notebook_slice(edited, "4.1 Lookback", level=3)[0]
    )


def test_last_level_three_slice_stops_at_the_next_level_two_heading():
    content, _ = notebook_slice(_subsection_notebook(), "4.2 Shout", level=3)
    assert [cell["source"] for cell in content] == ["### 4.2 Shout\nshout text", "shout()"]


def test_level_two_slice_keeps_its_subsections_and_ignores_later_lines():
    content, _ = notebook_slice(_subsection_notebook(), "4. Paths")
    assert len(content) == 4
    with pytest.raises(LookupError, match="matched 0"):
        notebook_slice(_subsection_notebook(), "4.1 Lookback")


def test_level_three_heading_must_match_exactly_one_cell():
    with pytest.raises(LookupError, match="matched 0"):
        notebook_slice(_subsection_notebook(), "4.9 Missing", level=3)


def test_unsupported_slice_level_is_rejected():
    with pytest.raises(ValueError, match="level"):
        notebook_slice(_subsection_notebook(), "4. Paths", level=4)


# --- Book sections ----------------------------------------------------------------

BOOK = """<html><head>
<link href="../_static/theme.css?digest=1" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head><body>
<section id="a"><h2>8. Before</h2><p>before</p></section>
<section id="ivf-27-3"><h2>9. IVF<a class="headerlink" href="#ivf-27-3">#</a></h2>
<p>body</p>
<section id="id10"><h3>9.1 Model</h3><div id="{uuid}" class="plotly-graph-div"></div>
<a href="#id10">link</a></section>
</section>
<section id="next"><h2>10. Next</h2></section>
</body></html>"""


def test_book_section_extracts_the_nested_section_for_the_heading():
    html = book_section(BOOK.replace("{uuid}", UUID_A), "9. IVF")
    assert html.startswith('<section id="ivf-27-3">')
    assert "9.1 Model" in html
    assert "10. Next" not in html and "8. Before" not in html


def test_book_section_normalizes_plotly_ids_and_sphinx_auto_ids():
    first = book_section(BOOK.replace("{uuid}", UUID_A), "9. IVF")
    second = book_section(
        BOOK.replace("{uuid}", UUID_B).replace("id10", "id14"),
        "9. IVF",
    )
    assert first == second


def test_book_section_keeps_explicit_anchor_ids():
    first = book_section(BOOK.replace("{uuid}", UUID_A), "9. IVF")
    second = book_section(BOOK.replace("{uuid}", UUID_A).replace("ivf-27-3", "ivf-27-3b"), "9. IVF")
    assert first != second


def test_book_section_changes_with_body_text():
    first = book_section(BOOK.replace("{uuid}", UUID_A), "9. IVF")
    second = book_section(BOOK.replace("{uuid}", UUID_A).replace("body", "body!"), "9. IVF")
    assert first != second


def test_book_section_level_three_returns_only_the_subsection():
    html = book_section(BOOK.replace("{uuid}", UUID_A), "9.1 Model", level=3)
    assert html.startswith('<section id="auto-id-0">')
    assert "9.1 Model" in html and "<p>body</p>" not in html


def test_book_section_level_three_ignores_level_two_headings():
    with pytest.raises(LookupError, match="matched 0"):
        book_section(BOOK.replace("{uuid}", UUID_A), "9. IVF", level=3)


# --- portal cards ----------------------------------------------------------------

PORTAL = """<figure class="fig-card"><h3>Other</h3><div id="fig-other"></div></figure>
<figure class="fig-card"><h3>IVF smile</h3><div id="fig-ivf_smile"></div>
<script>Plotly.newPlot("fig-ivf_smile", [{"y": [1.0]}])</script></figure>"""


def test_portal_cards_extract_each_requested_figure():
    cards = portal_cards(PORTAL, ["ivf_smile"])
    assert list(cards) == ["ivf_smile"]
    assert cards["ivf_smile"].startswith('<figure class="fig-card"><h3>IVF smile')


def test_portal_cards_ignore_changes_to_other_figures():
    changed = PORTAL.replace("<h3>Other</h3>", "<h3>Other, edited</h3>")
    assert portal_cards(PORTAL, ["ivf_smile"]) == portal_cards(changed, ["ivf_smile"])


def test_portal_cards_change_with_their_payload():
    changed = PORTAL.replace('[{"y": [1.0]}]', '[{"y": [1.5]}]')
    assert portal_cards(PORTAL, ["ivf_smile"]) != portal_cards(changed, ["ivf_smile"])


def test_missing_portal_figure_raises_lookup_error():
    with pytest.raises(LookupError, match="ivf_joint"):
        portal_cards(PORTAL, ["ivf_joint"])


# --- assets and python sources ---------------------------------------------------


def test_page_assets_hash_local_files_and_list_floating_urls(tmp_path):
    page = tmp_path / "book/notebooks/page.html"
    page.parent.mkdir(parents=True)
    page.write_text(BOOK, encoding="utf-8")
    static = tmp_path / "book/_static/theme.css"
    static.parent.mkdir(parents=True)
    static.write_text("body{}", encoding="utf-8")
    assets = page_assets(tmp_path, "book/notebooks/page.html")
    assert assets["local"] == {"book/_static/theme.css": hashlib.sha256(b"body{}").hexdigest()}
    assert assets["external"] == ["https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"]


def test_missing_local_asset_is_reported_as_unknown(tmp_path):
    page = tmp_path / "book/notebooks/page.html"
    page.parent.mkdir(parents=True)
    page.write_text(BOOK, encoding="utf-8")
    assets = page_assets(tmp_path, "book/notebooks/page.html")
    assert assets["local"] == {"book/_static/theme.css": None}


def test_python_closure_follows_package_imports_only(tmp_path):
    package = tmp_path / "hullkit/src/hullkit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "local_volatility.py").write_text(
        "import numpy as np\nfrom hullkit import bsm\nfrom . import _helper\n", encoding="utf-8"
    )
    (package / "bsm.py").write_text("import math\n", encoding="utf-8")
    (package / "_helper.py").write_text("from .bsm import call\n", encoding="utf-8")
    (package / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
    closure = python_closure(tmp_path, ["hullkit.local_volatility"])
    assert sorted(closure) == [
        "hullkit/src/hullkit/__init__.py",
        "hullkit/src/hullkit/_helper.py",
        "hullkit/src/hullkit/bsm.py",
        "hullkit/src/hullkit/local_volatility.py",
    ]


def test_python_closure_follows_package_initializer_imports(tmp_path):
    package = tmp_path / "hullkit/src/hullkit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from . import shared\n", encoding="utf-8")
    (package / "shared.py").write_text("value = 1\n", encoding="utf-8")
    (package / "local_volatility.py").write_text("value = 2\n", encoding="utf-8")
    before = python_closure(tmp_path, ["hullkit.local_volatility"])
    (package / "shared.py").write_text("value = 3\n", encoding="utf-8")
    after = python_closure(tmp_path, ["hullkit.local_volatility"])
    assert "hullkit/src/hullkit/shared.py" in before
    assert before != after


@pytest.mark.parametrize(
    "source",
    [
        '__import__("hullkit.dynamic")\n',
        'from importlib import import_module as load\nload("hullkit.dynamic")\n',
        'import importlib\nload = importlib.import_module\nload("hullkit.dynamic")\n',
    ],
)
def test_python_closure_rejects_dynamic_package_import(tmp_path, source):
    package = tmp_path / "hullkit/src/hullkit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "local_volatility.py").write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match="dynamic import"):
        python_closure(tmp_path, ["hullkit.local_volatility"])


# --- fingerprints and decisions --------------------------------------------------


@pytest.fixture
def mini_project(tmp_path):
    root = tmp_path
    (root / "volumes/06").mkdir(parents=True)
    (root / "volumes/06/numerical.ipynb").write_text(json.dumps(_notebook()), encoding="utf-8")
    (root / "book/_build/html/notebooks").mkdir(parents=True)
    (root / "book/_build/html/notebooks/06.html").write_text(
        BOOK.replace("{uuid}", UUID_A), encoding="utf-8"
    )
    (root / "book/_build/html/_static").mkdir(parents=True)
    (root / "book/_build/html/_static/theme.css").write_text("body{}", encoding="utf-8")
    (root / "report/site/assets").mkdir(parents=True)
    (root / "report/site/numerics.html").write_text(
        '<link href="assets/style.css" rel="stylesheet">' + PORTAL, encoding="utf-8"
    )
    (root / "report/site/assets/style.css").write_text(".fig-card{}", encoding="utf-8")
    package = root / "hullkit/src/hullkit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "local_volatility.py").write_text("x = 1\n", encoding="utf-8")
    (root / "docs/validation/section-27-3").mkdir(parents=True)
    (root / "docs/validation/section-27-3/reference.json").write_text("{}", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts/verify.cjs").write_text("// verifier", encoding="utf-8")
    config = {
        "schema_version": 1,
        "sections": {
            "27.3": {
                "notebook": {"path": "volumes/06/numerical.ipynb", "heading": "9. IVF"},
                "book": {"page": "book/_build/html/notebooks/06.html", "heading": "9. IVF"},
                "portal": {"page": "report/site/numerics.html", "figures": ["ivf_smile"]},
                "python_modules": ["hullkit.local_volatility"],
                "data": ["docs/validation/section-27-3/reference.json"],
                "verifier": "scripts/verify.cjs",
                "viewports": [[1440, 1050], [1000, 1050]],
            }
        },
    }
    return root, config


def _environment():
    return {"node": "v26.7.0", "playwright": "1.56.0", "fonts": {"Noto Sans JP": "abc"}}


def test_fingerprint_is_deterministic(mini_project):
    root, config = mini_project
    first = compute_fingerprint(root, "27.3", config, environment=_environment())
    second = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert first == second
    assert first["rules"]["normalizer_version"] == NORMALIZER_VERSION
    assert len(first["digest"]) == 64


def test_level_three_declaration_ignores_sibling_subsections(mini_project):
    root, config = mini_project
    spec = config["sections"]["27.3"]
    spec["notebook"] = {"path": "volumes/06/numerical.ipynb", "heading": "4.1 Lookback", "level": 3}
    spec["book"] = {
        "page": "book/_build/html/notebooks/06.html",
        "heading": "9.1 Model",
        "level": 3,
    }
    notebook = root / "volumes/06/numerical.ipynb"
    notebook.write_text(json.dumps(_subsection_notebook()), encoding="utf-8")
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert baseline["unknown"] == []
    notebook.write_text(json.dumps(_subsection_notebook(shout="edited")), encoding="utf-8")
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert decide(baseline, current)["decision"] == "reuse"
    notebook.write_text(json.dumps(_subsection_notebook(lookback="edited")), encoding="utf-8")
    changed = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert compare_fingerprints(baseline, changed) == ["notebook_slice"]


def test_unrelated_notebook_cells_allow_reuse(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    (root / "volumes/06/numerical.ipynb").write_text(
        json.dumps(_notebook(prefix_cells=4)), encoding="utf-8"
    )
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert decide(baseline, current) == {"decision": "reuse", "reasons": []}


@pytest.mark.parametrize(
    ("path", "old", "new", "component"),
    [
        ("volumes/06/numerical.ipynb", '"text"', '"text, edited"', "notebook_slice"),
        ("book/_build/html/notebooks/06.html", "<p>body</p>", "<p>body!</p>", "book_section"),
        ("report/site/numerics.html", "[1.0]", "[1.5]", "portal_cards"),
        ("report/site/assets/style.css", ".fig-card{}", ".fig-card{width:1px}", "portal_assets"),
        ("book/_build/html/_static/theme.css", "body{}", "body{margin:0}", "book_assets"),
        ("hullkit/src/hullkit/local_volatility.py", "x = 1", "x = 2", "python_sources"),
        ("docs/validation/section-27-3/reference.json", "{}", '{"a": 1}', "data_files"),
        ("scripts/verify.cjs", "// verifier", "// verifier v2", "verifier"),
    ],
)
def test_related_changes_force_a_redraw(mini_project, path, old, new, component):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    target = root / path
    text = target.read_text(encoding="utf-8")
    assert old in text
    target.write_text(text.replace(old, new), encoding="utf-8")
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    result = decide(baseline, current)
    assert result["decision"] == "redraw"
    assert any(component in reason for reason in result["reasons"])


def test_environment_change_forces_a_redraw(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    changed = _environment() | {"fonts": {"Noto Sans JP": "def"}}
    current = compute_fingerprint(root, "27.3", config, environment=changed)
    assert decide(baseline, current)["decision"] == "redraw"


def test_package_initializer_change_forces_a_redraw(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    (root / "hullkit/src/hullkit/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert decide(baseline, current) == {
        "decision": "redraw",
        "reasons": ["python_sources changed"],
    }


def test_unknown_section_is_never_reused(mini_project):
    root, config = mini_project
    current = compute_fingerprint(root, "99.9", config, environment=_environment())
    assert current["unknown"] == ["section 99.9 has no dependency declaration"]
    result = decide(current, current)
    assert result["decision"] == "redraw"
    assert "unknown" in result["reasons"][0]


def test_missing_build_output_is_unknown_and_redraws(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    (root / "report/site/numerics.html").unlink()
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert any("report/site/numerics.html" in item for item in current["unknown"])
    assert decide(baseline, current)["decision"] == "redraw"


def test_normalizer_version_change_invalidates_the_baseline(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    older = copy.deepcopy(baseline)
    older["rules"]["normalizer_version"] = NORMALIZER_VERSION - 1
    result = decide(older, baseline)
    assert result["decision"] == "redraw"
    assert "rules" in result["reasons"][0]


def test_compare_lists_changed_components(mini_project):
    root, config = mini_project
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    current = copy.deepcopy(baseline)
    current["components"]["data_files"] = {"docs/x.json": "0" * 64}
    assert compare_fingerprints(baseline, current) == ["data_files"]


def test_runtime_mismatch_detects_browser_mathjax_and_font_changes():
    baseline = {
        "browser_version": "145.0.7632.6",
        "mathjax_version": "3.2.2",
        "mathjax_scripts": [{"url": "https://example/mathjax.js", "sha256": "a" * 64}],
        "fonts": {"portal_plot_text": ["Liberation Sans"]},
    }
    assert runtime_mismatches(baseline, dict(baseline)) == []
    assert runtime_mismatches(baseline, baseline | {"browser_version": "146.0"}) == [
        "browser_version"
    ]
    assert runtime_mismatches(baseline, baseline | {"fonts": {"portal_plot_text": ["X"]}}) == [
        "fonts"
    ]
    partial = {key: value for key, value in baseline.items() if key != "mathjax_version"}
    assert runtime_mismatches(baseline, partial) == ["mathjax_version"]
    changed_script = copy.deepcopy(baseline)
    changed_script["mathjax_scripts"][0]["sha256"] = "b" * 64
    assert runtime_mismatches(baseline, changed_script) == ["mathjax_scripts"]


def test_execute_result_counts_are_not_part_of_the_slice():
    first = _notebook()
    second = _notebook()
    for notebook, count in ((first, 3), (second, 9)):
        notebook["cells"][3]["outputs"].append(
            {
                "output_type": "execute_result",
                "execution_count": count,
                "data": {"text/plain": ["0.25"]},
                "metadata": {},
            }
        )
    assert _digest(notebook_slice(first, "9. IVF")[0]) == _digest(
        notebook_slice(second, "9. IVF")[0]
    )


def test_execute_result_value_is_part_of_the_slice():
    first = _notebook()
    second = _notebook()
    for notebook, value in ((first, "0.25"), (second, "0.26")):
        notebook["cells"][3]["outputs"].append(
            {
                "output_type": "execute_result",
                "execution_count": 1,
                "data": {"text/plain": [value]},
                "metadata": {},
            }
        )
    assert _digest(notebook_slice(first, "9. IVF")[0]) != _digest(
        notebook_slice(second, "9. IVF")[0]
    )


def test_an_input_missing_in_both_runs_still_forces_a_redraw(mini_project):
    root, config = mini_project
    (root / "report/site/numerics.html").unlink()
    baseline = compute_fingerprint(root, "27.3", config, environment=_environment())
    current = compute_fingerprint(root, "27.3", config, environment=_environment())
    assert compare_fingerprints(baseline, current) == []
    result = decide(baseline, current)
    assert result["decision"] == "redraw"
    assert all(reason.startswith("unknown dependency") for reason in result["reasons"])


def test_page_assets_treat_symlinked_directories_as_local(tmp_path):
    real = tmp_path / "real"
    (real / "book/notebooks").mkdir(parents=True)
    (real / "book/notebooks/page.html").write_text(BOOK, encoding="utf-8")
    (real / "book/_static").mkdir(parents=True)
    (real / "book/_static/theme.css").write_text("body{}", encoding="utf-8")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "book").symlink_to(real / "book", target_is_directory=True)
    assets = page_assets(overlay, "book/notebooks/page.html")
    assert assets["local"] == {"book/_static/theme.css": hashlib.sha256(b"body{}").hexdigest()}
