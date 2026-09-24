"""Saved-data figures make the §26.17 boundary and Hull table inspectable."""

import json
from pathlib import Path

import pytest
from hullkit._static_replication_lesson import _figures, _load_reference

REFERENCE = Path(__file__).resolve().parents[2] / "docs/validation/section-26-17/reference.json"


def test_four_figures_show_printed_legs_and_convergence():
    saved = json.loads(REFERENCE.read_text(encoding="utf-8"))
    figures = _figures()
    assert list(figures) == [
        "static_boundary",
        "static_ladder",
        "static_boundary_error",
        "static_convergence",
    ]
    for key, figure in figures.items():
        assert figure.layout.meta["section"] == "26.17"
        assert figure.layout.meta["figure"] == key
    assert list(figures["static_ladder"].data[0].y) == pytest.approx(
        saved["ladders"]["3"]["leg_values"]
    )
    convergence = figures["static_convergence"]
    assert list(convergence.data[0].y) == pytest.approx(
        [saved["ladders"][str(n)]["initial_value"] for n in (3, 18, 100)]
    )
    assert list(convergence.data[1].y) == pytest.approx([saved["analytic_barrier_price"]] * 3)


def test_each_boundary_menu_state_uses_saved_curve():
    saved = json.loads(REFERENCE.read_text(encoding="utf-8"))
    figure = _figures()["static_boundary_error"]
    assert len(figure.layout.updatemenus[0].buttons) == 3
    for trace, steps in zip(figure.data, (3, 18, 100), strict=True):
        assert list(trace.x) == pytest.approx(
            [point["time"] for point in saved["ladders"][str(steps)]["boundary_curve"]]
        )
        assert list(trace.y) == pytest.approx(
            [point["value"] for point in saved["ladders"][str(steps)]["boundary_curve"]]
        )


def test_tampered_saved_reference_is_rejected(tmp_path):
    record = REFERENCE.with_name("numerical-check.json")
    changed = json.loads(REFERENCE.read_text(encoding="utf-8"))
    changed["ladders"]["3"]["initial_value"] += 0.5
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        _load_reference(path, record)
