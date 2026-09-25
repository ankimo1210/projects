"""Saved §27.1 figures have checked inputs and meaningful plotted values."""

import json

import pytest
from hullkit._alternative_models_lesson import _figures, _load_reference


def test_four_saved_figures_match_reference_values():
    data = _load_reference()
    figures = _figures()
    assert set(figures) == {
        "alternative_cev",
        "alternative_merton",
        "alternative_poisson",
        "alternative_vg",
    }
    assert all(figure.layout.meta["section"] == "27.1" for figure in figures.values())
    assert list(figures["alternative_poisson"].data[0].y) == pytest.approx(
        data["poisson_table"]["probability"]
    )
    assert list(figures["alternative_merton"].data[0].y) == pytest.approx(
        [100 * value for value in data["merton"]["implied_vol"]]
    )
    assert list(figures["alternative_vg"].data[0].y) == pytest.approx(
        data["variance_gamma"]["sample_density"]
    )


def test_altered_reference_rejected(tmp_path):
    from hullkit._alternative_models_lesson import _DATA, _RECORD

    altered = json.loads(_DATA.read_text(encoding="utf-8"))
    altered["poisson_table"]["probability"][0] = 0.9
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(path, _RECORD)
