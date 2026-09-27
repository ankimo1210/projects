"""Saved IVF figures must match the independently recomputed §27.3 values."""

import json

import pytest
from hullkit._local_volatility_lesson import _figures, _load_reference


def test_four_figures_match_reference_and_metadata():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == ["ivf_smile", "ivf_local", "ivf_repricing", "ivf_joint"]
    assert all(fig.layout.meta["section"] == "27.3" for fig in figures.values())
    assert list(figures["ivf_smile"].data[1].y) == pytest.approx(
        [100 * x for x in data["slices"]["1.0"]["implied_vols"]]
    )
    assert list(figures["ivf_local"].data[1].y) == pytest.approx(
        [100 * x for x in data["slices"]["1.0"]["local_vols"]]
    )
    assert list(figures["ivf_repricing"].data[0].y) == pytest.approx(
        [row["local_vol_pde_call"] for row in data["pde_repricing"]]
    )
    joint = data["two_date_models"]["both_dates_up"]
    assert list(figures["ivf_joint"].data[0].y) == pytest.approx(
        [joint["latent_probability"], joint["local_probability"]]
    )


def test_changed_saved_reference_is_rejected(tmp_path):
    from hullkit._local_volatility_lesson import _DATA, _RECORD

    altered = json.loads(_DATA.read_text(encoding="utf-8"))
    altered["slices"]["1.0"]["local_vols"][0] += 0.1
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(path, _RECORD)
