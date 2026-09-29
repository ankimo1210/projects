"""Saved independent §26.2 data drives the four shared lesson figures."""

import json
from pathlib import Path

import pytest
from hullkit._perpetual_american_lesson import _figures, _load_reference


def _case(data, label):
    return next(case for case in data["cases"] if case["label"] == label)


def test_reference_is_checked_and_exposes_both_exercise_boundaries():
    data = _load_reference()
    assert data["section"] == "26.2"
    symmetric = _case(data, "symmetric")
    assert symmetric["a1"] == pytest.approx(2.0)
    assert symmetric["a2"] == pytest.approx(1.0)
    assert symmetric["call"]["boundary"] == pytest.approx(200.0)
    assert symmetric["put"]["boundary"] == pytest.approx(50.0)
    zero_yield = _case(data, "zero_yield")
    assert zero_yield["call"]["boundary_kind"] == "infinite"
    assert zero_yield["call"]["boundary"] is None
    assert zero_yield["call"]["value"] == zero_yield["parameters"]["spot"]


def test_four_figures_take_their_series_from_saved_reference():
    data = _load_reference()
    figures = _figures()
    keys = [
        "perpetual_value",
        "perpetual_boundaries",
        "perpetual_zero_dividend",
        "perpetual_convergence",
    ]
    assert list(figures) == keys
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "26.2"
        assert fig.layout.meta["figure"] == key
        assert "saved independent reference" in fig.layout.meta["source"]

    curve = data["figure"]
    value = figures["perpetual_value"]
    for trace, field in zip(
        value.data[:4], ("call", "put", "call_intrinsic", "put_intrinsic"), strict=True
    ):
        assert list(trace.x) == curve["spot_grid"]
        assert list(trace.y) == curve[field]
    assert list(value.data[4].x) == [curve["call_boundary"]]
    assert list(value.data[5].x) == [curve["put_boundary"]]

    cases = data["cases"]
    boundaries = figures["perpetual_boundaries"]
    assert list(boundaries.data[0].y) == [
        case["call"]["boundary"] / case["parameters"]["strike"]
        if case["call"]["boundary"] is not None
        else None
        for case in cases
    ]
    assert list(boundaries.data[1].y) == [
        case["put"]["boundary"] / case["parameters"]["strike"] for case in cases
    ]

    no_yield = figures["perpetual_zero_dividend"]
    assert list(no_yield.data[0].x) == curve["spot_grid"]
    assert list(no_yield.data[0].y) == curve["spot_grid"]
    assert list(no_yield.data[1].y) == [
        max(spot - _case(data, "zero_yield")["parameters"]["strike"], 0.0)
        for spot in curve["spot_grid"]
    ]

    symmetric = _case(data, "symmetric")
    rows = symmetric["lattice"]["rows"]
    convergence = figures["perpetual_convergence"]
    assert list(convergence.data[0].x) == [row["maturity"] for row in rows]
    assert list(convergence.data[0].y) == [row["call"] for row in rows]
    assert list(convergence.data[1].y) == [row["put"] for row in rows]
    assert list(convergence.data[2].y) == [symmetric["call"]["value"]] * len(rows)
    assert list(convergence.data[3].y) == [symmetric["put"]["value"]] * len(rows)


def test_hash_guard_rejects_changed_reference(tmp_path):
    data = _load_reference()
    data["figure"]["call"][0] += 1.0
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(changed)


def test_builder_has_six_subsections_and_uses_each_figure_once():
    project = Path(__file__).resolve().parents[2]
    source = (project / "volumes/10_exotics_martingales/build_exotics_notebook.py").read_text(
        encoding="utf-8"
    )
    assert source.count("### 4.9 ") == 1
    assert [f"#### 4.9.{n} " in source for n in range(1, 7)] == [True] * 6
    for key in (
        "perpetual_value",
        "perpetual_boundaries",
        "perpetual_zero_dividend",
        "perpetual_convergence",
    ):
        assert source.count(f'perpetual_figures["{key}"].show()') == 1
