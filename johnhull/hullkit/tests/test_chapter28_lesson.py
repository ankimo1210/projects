"""Shared chapter-28 delivery must preserve independently computed trace values."""

import copy

import pytest
from hullkit import _chapter28_lesson as lesson

from johnhull.hullkit.tests import _chapter28_reference as teacher


def test_six_shared_figures_match_independent_quadrature_and_covariance():
    expected = teacher.build()["figures"]
    figures = lesson._figures()
    actual = {
        key: [dict(role=t.meta["role"], x=list(t.x), y=list(t.y)) for t in fig.data]
        for key, fig in figures.items()
    }
    assert teacher.close_series(actual, expected) < 1e-9
    assert {fig.layout.meta["section"] for fig in figures.values()} == {"28.6", "28.7", "28.8"}
    assert all(fig.layout.meta["synthetic"] for fig in figures.values())


@pytest.mark.parametrize("mutation", ["value", "role", "missing"])
def test_display_rejects_material_price_change_reversed_direction_or_missing_figure(mutation):
    expected = teacher.build()["figures"]
    changed = copy.deepcopy(expected)
    if mutation == "value":
        changed["martingale_black_forward_prices"][0]["y"][0] += 0.001
    elif mutation == "role":
        changed["martingale_numeraire_drift_shift"][1]["role"] = "old_over_new"
    else:
        changed.pop("martingale_exchange_ratio_means")
    with pytest.raises(ValueError):
        teacher.close_series(changed, expected)


def test_numerical_reference_allows_roundoff():
    expected = teacher.build()["figures"]
    changed = copy.deepcopy(expected)
    changed["martingale_black_forward_prices"][0]["y"][0] += 1e-13
    assert teacher.close_series(changed, expected) < 1e-9


def test_notebook_has_each_source_requirement_and_display_once():
    cells = lesson._cells()
    text = "\n".join("".join(c["source"]) for c in cells)
    for heading in ("6E. Black", "6F. 一つの資産", "6G. ニュメレール"):
        assert text.count("## " + heading) == 1
    for key in lesson.FIGURES:
        assert text.count(f'chapter28_plots["{key}"].show()') == 1
    for required in ("28.26", "28.32", "28.35", "非取引", "絶対loading", "合成例", "標準誤差"):
        assert required in text
