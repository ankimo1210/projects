"""Hull §27.5 reference and four shared figures are checked together."""

import pytest
from hullkit._path_dependent_lesson import _figures, _load_reference


def test_reference_contains_printed_interpolation_and_exact_small_trees():
    data = _load_reference()
    assert data["printed"]["x_value"] == pytest.approx(6.206, abs=0.001)
    assert data["interpolation"]["up_value"] == pytest.approx(8.247, abs=0.001)
    assert data["interpolation"]["down_value"] == pytest.approx(4.182, abs=0.001)
    assert len(data["exact_small_trees"]) == 5


def test_four_figures_use_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == ["path_grids", "path_interpolation", "path_prices", "path_exact"]
    assert all(fig.layout.meta["section"] == "27.5" for fig in figures.values())
    assert list(figures["path_grids"].data[0].x) == data["figure_27_3"]["X"]["averages"]
