"""Hull §27.8 reference and four shared figures are checked together."""

import json

import pytest
from hullkit._american_mc_lesson import _figures, _load_reference


def test_reference_holds_the_eight_paths_exact_values_and_studies():
    data = _load_reference()
    hand = data["hand_example"]
    assert hand["least_squares"]["value"] == pytest.approx(0.1144343, abs=1e-7)
    assert hand["boundary"]["value"] == pytest.approx(0.1208506, abs=1e-7)
    assert [row["dates"] for row in data["exact"]["bermudan"]] == [3, 6, 12, 24, 48]
    assert data["exact"]["american"]["value"] == pytest.approx(0.133844, abs=1e-6)
    assert data["exact"]["bermudan"][0]["value"] == pytest.approx(0.1219882, abs=1e-7)
    assert data["bias"]["sizes"][0] == 250
    assert data["bias"]["replications"] == 200
    assert data["exchange"]["exact"] == pytest.approx(8.71903, abs=1e-5)


def test_four_figures_use_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == [
        "american_mc_regression",
        "american_mc_boundary",
        "american_mc_bias",
        "american_mc_dates",
    ]
    assert all(fig.layout.meta["section"] == "27.8" for fig in figures.values())
    regression = figures["american_mc_regression"]
    late = data["hand_example"]["least_squares"]["steps"]["2"]
    assert list(regression.data[0].x) == late["spots"]
    assert list(regression.data[0].y) == late["discounted_continuation"]
    a, b, c = late["coefficients"]
    assert regression.data[1].y[0] == pytest.approx(a + b * 0.74 + c * 0.74**2, abs=1e-15)
    assert list(regression.data[5].x) == [0.97, 0.77, 0.84]
    assert list(regression.data[6].x) == [0.93, 0.76, 0.92, 0.88]
    assert regression.data[5].marker.color != regression.data[6].marker.color
    boundary = figures["american_mc_boundary"]
    step = data["hand_example"]["boundary"]["steps"]["2"]
    assert list(boundary.data[0].y) == [*step["averages"], step["averages"][-1]]
    assert list(boundary.data[1].x) == [0.84, 0.97]
    bias = figures["american_mc_bias"]
    assert list(bias.data[3].y) == [
        m - data["bias"]["exact"] for m in data["bias"]["boundary_out"]["mean"]
    ]
    dates = figures["american_mc_dates"]
    assert list(dates.data[0].y) == data["dates"]["exact"]
    assert list(dates.data[2].y) == data["dates"]["lsm3"]["value"]
    counts = data["dates"]["counts"]
    assert list(dates.data[2].x) == counts and list(dates.data[2].customdata) == counts
    assert dates.data[1].x[0] < counts[0] < dates.data[3].x[0]


def test_hash_guard_rejects_a_changed_reference(tmp_path):
    data = _load_reference()
    data["exact"]["american"]["value"] += 0.01
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(changed)
