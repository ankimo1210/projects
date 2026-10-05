"""D3 common acceptance must reject incomplete or stale section evidence."""

import copy
import json

import pytest

from johnhull.scripts import chapter_acceptance as gate


def config():
    return dict(
        sections=[
            dict(id="28.6", figures=["black"], heading="Black", requirements=[dict(id="B1")])
        ],
        viewports=[[1000, 1050]],
        book_page="book.html",
        portal_page="portal.html",
    )


def browser():
    page = dict(
        states=[
            dict(
                section="28.6",
                figure="black",
                width=1000,
                numeric_checked=True,
                layout_checked=True,
            )
        ],
        screenshots=["image.png"],
        numeric_mutation_rejected=True,
        page_errors=[],
        unapproved_requests=[],
    )
    return dict(
        status="PASS",
        pages=dict(
            book=dict(
                **page, headings=[dict(section="28.6", explanation_checked=True, math_checked=True)]
            ),
            portal=copy.deepcopy(page),
        ),
        book_math=dict(errors=0),
    )


@pytest.mark.parametrize("mutation", ["numeric", "layout", "heading", "surface", "control"])
def test_chapter_cannot_pass_with_missing_section_surface_or_explanation(monkeypatch, mutation):
    monkeypatch.setattr(gate, "fresh", lambda *args: None)
    data = browser()
    if mutation in ("numeric", "layout"):
        data["pages"]["portal"]["states"][0][mutation + "_checked"] = False
    elif mutation == "heading":
        data["pages"]["book"]["headings"] = []
    elif mutation == "surface":
        data["pages"].pop("portal")
    else:
        data["pages"]["portal"]["numeric_mutation_rejected"] = False
    with pytest.raises(ValueError):
        gate.check_browser(config(), data, [])


def test_complete_section_matrix_is_accepted(monkeypatch):
    monkeypatch.setattr(gate, "fresh", lambda *args: None)
    gate.check_browser(config(), browser(), [])


def test_provenance_cannot_remove_mandatory_source(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    (tmp_path / "input.py").write_text("original")
    record = dict(status="PASS", source_sha256={})
    with pytest.raises(ValueError, match="required provenance"):
        gate.fresh(record, ["input.py"])
    record["source_sha256"] = gate.hashes(["input.py"])
    gate.fresh(record, ["input.py"])
    (tmp_path / "input.py").write_text("changed")
    with pytest.raises(ValueError, match="input changed"):
        gate.fresh(record, ["input.py"])


def test_config_rejects_duplicate_section_or_requirement(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    cfg = dict(schema_version=1, **config())
    cfg["sections"].append(copy.deepcopy(cfg["sections"][0]))
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="unique IDs"):
        gate.load_config("config.json")
    cfg["sections"].pop()
    cfg["sections"][0]["requirements"] *= 2
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="requirement"):
        gate.load_config("config.json")


def test_new_notebook_figures_have_independent_values_and_explanations():
    import nbformat

    from johnhull.hullkit.tests import _chapter28_reference as teacher

    cfg = gate.load_config("docs/acceptance/chapters/ch28.json")
    notebook = nbformat.read(gate.path(cfg["notebook"]), as_version=4)
    names = {key for row in cfg["sections"] for key in row["figures"]}
    saved = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if data and (key := data["layout"].get("meta", {}).get("figure")) in names:
                assert key not in saved
                saved[key] = [
                    dict(role=t["meta"]["role"], x=t["x"], y=t["y"]) for t in data["data"]
                ]
    assert teacher.close_series(saved, teacher.build()["figures"]) < 1e-9
    text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
    for section in cfg["sections"]:
        assert text.count("## " + section["heading"]) == 1
