"""Hull §27.6 reference and four shared figures are checked together."""

import json

import pytest
from hullkit._barrier_tree_lesson import _figures, _load_reference


def test_reference_contains_formula_pde_dense_lattice_and_limits():
    data = _load_reference()
    assert data["analytic"]["continuous"] == pytest.approx(0.432155, abs=1e-6)
    assert abs(data["analytic"]["pde"]["error"]) < 1e-5
    assert data["convergence"]["steps"][0] == 20
    assert data["convergence"]["steps"][-1] == 300
    assert data["hand_example"]["levels"] == 4
    assert data["lattice_example"]["on_barrier"]["levels"] == 1


def test_four_figures_use_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == [
        "barrier_lattice",
        "barrier_convergence",
        "barrier_errors",
        "barrier_near",
    ]
    assert all(fig.layout.meta["section"] == "27.6" for fig in figures.values())
    convergence = figures["barrier_convergence"]
    assert list(convergence.data[1].y) == data["convergence"]["trinomial_simple"]
    errors = figures["barrier_errors"]
    for index in (0, 140, 280):
        total = errors.data[0].y[index]
        assert total == pytest.approx(errors.data[1].y[index] + errors.data[2].y[index], abs=1e-12)
    near = figures["barrier_near"]
    assert list(near.data[0].y) == data["near_barrier"]["curves"]["100"]["p_middle"]


def test_hash_guard_rejects_a_changed_reference(tmp_path):
    data = _load_reference()
    data["analytic"]["continuous"] += 0.01
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(changed)
