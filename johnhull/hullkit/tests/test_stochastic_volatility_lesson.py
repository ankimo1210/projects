"""Saved §27.2 figures have checked inputs and the plotted values of the reference."""

import json

import pytest
from hullkit._stochastic_volatility_lesson import _figures, _load_reference


def test_four_saved_figures_match_reference_values():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == [
        "stochvol_term",
        "stochvol_mixing",
        "stochvol_correlation",
        "stochvol_sabr",
    ]
    assert all(figure.layout.meta["section"] == "27.2" for figure in figures.values())
    assert list(figures["stochvol_term"].data[1].y) == pytest.approx(
        [100 * v for v in data["term_structure"]["remaining_rms_vol"]]
    )
    assert list(figures["stochvol_mixing"].data[0].y) == pytest.approx(
        [100 * v for v in data["heston"]["smiles"]["+0.0"]["implied_vol"]]
    )
    assert [trace.name for trace in figures["stochvol_correlation"].data] == [
        "ρ=−0.7（株式型）",
        "ρ=0",
        "ρ=+0.7",
    ]
    sabr = figures["stochvol_sabr"]
    assert [bool(trace.visible) for trace in sabr.data] == [True] * 3 + [False] * 3 + [True]
    states = [button.args[0]["visible"] for button in sabr.layout.updatemenus[0].buttons]
    assert states == [[True] * 3 + [False] * 3 + [True], [False] * 3 + [True] * 3 + [True]]
    assert list(sabr.data[3].y) == pytest.approx([100 * v for v in data["sabr"]["nu_group"]["0.2"]])


def test_altered_reference_rejected(tmp_path):
    from hullkit._stochastic_volatility_lesson import _DATA, _RECORD

    altered = json.loads(_DATA.read_text(encoding="utf-8"))
    altered["heston"]["smiles"]["+0.0"]["implied_vol"][0] = 0.9
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(path, _RECORD)
