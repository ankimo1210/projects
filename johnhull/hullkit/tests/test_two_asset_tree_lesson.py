"""Hull §27.7 reference and four shared figures are checked together."""

import json
import math

import pytest
from hullkit._two_asset_tree_lesson import _figures, _load_reference


def test_reference_contains_formulas_one_dimensional_value_and_sweeps():
    data = _load_reference()
    assert data["analytic"]["max_call"]["stulz"] == pytest.approx(15.926819, abs=1e-6)
    assert data["analytic"]["american_exchange"]["value"] == pytest.approx(8.76368, abs=1e-5)
    assert data["convergence"]["steps"][0] == 20
    assert data["convergence"]["steps"][-1] == 200
    assert data["errors"]["steps"] == [25, 50, 100, 200, 400, 800]
    assert data["correlation"]["rho"][0] == -1.0
    assert data["correlation"]["rho"][-1] == 1.0


def test_four_figures_use_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == [
        "two_asset_nodes",
        "two_asset_convergence",
        "two_asset_errors",
        "two_asset_correlation",
    ]
    assert all(fig.layout.meta["section"] == "27.7" for fig in figures.values())
    nodes = figures["two_asset_nodes"]
    hand = data["hand_example"]
    root = math.sqrt(hand["dt"])
    for trace, method in zip(nodes.data[:3], ("transform", "rubinstein", "adjusted"), strict=True):
        moves = hand[method]["moves"]
        assert list(trace.x) == pytest.approx([m[0] / (0.20 * root) for m in moves], abs=1e-12)
        assert list(trace.y) == pytest.approx([m[1] / (0.30 * root) for m in moves], abs=1e-12)
    convergence = figures["two_asset_convergence"]
    assert list(convergence.data[1].y) == data["convergence"]["american"]["rubinstein"]
    errors = figures["two_asset_errors"]
    assert list(errors.data[0].y) == [abs(e) for e in data["errors"]["transform_max_call"]]
    correlation = figures["two_asset_correlation"]
    assert list(correlation.data[2].y) == data["correlation"]["adjusted"]


def test_hash_guard_rejects_a_changed_reference(tmp_path):
    data = _load_reference()
    data["analytic"]["exchange"] += 0.01
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(changed)
