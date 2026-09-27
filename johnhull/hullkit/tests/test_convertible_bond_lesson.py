"""The independent §27.4 reference backs the four shared teaching figures."""

import pytest
from hullkit._convertible_bond_lesson import _figures, _load_reference


def test_saved_reference_matches_textbook_and_public_tree():
    from hullkit.convertible_bond import convertible_bond_tree

    data = _load_reference()
    assert data["textbook"]["price"] == pytest.approx(107.44, abs=0.005)
    assert data["textbook"]["nodes"]["B"]["decision"] == "call-convert"
    assert data["textbook"]["nodes"]["E"]["decision"] == "hold"
    assert convertible_bond_tree(**data["parameters"]).price == pytest.approx(
        data["textbook"]["price"], abs=1e-12
    )


def test_four_shared_figures_have_section_metadata_and_reference_values():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == ["cb_tree", "cb_decisions", "cb_credit", "cb_convergence"]
    assert all(fig.layout.meta["section"] == "27.4" for fig in figures.values())
    assert float(figures["cb_tree"].data[0].customdata[0][0]) == pytest.approx(
        data["textbook"]["nodes"]["A"]["value"]
    )
    assert list(figures["cb_tree"].data[3].y) == [-3, -1, 1, 3]
