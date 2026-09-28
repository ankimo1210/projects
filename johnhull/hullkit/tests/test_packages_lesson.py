"""Hull §26.1 reference and four shared figures are checked together."""

import json

import pytest
from hullkit._packages_lesson import _figures, _load_reference


def test_reference_holds_the_section_17_2_anchor_and_the_risk_table():
    data = _load_reference()
    anchor = data["anchor_17_2"]
    assert round(anchor["call_strike"], 4) == 1.3414
    assert round(anchor["premium"], 4) == 0.0273
    assert data["figure_payoffs"]["put_strike"] == 1.3
    risk = data["risk_comparison"]
    assert set(risk) == {"forward", "range_forward", "break_forward"}
    assert len(data["strike_curve"]["points"]) == 70
    assert len(data["figure_payoffs"]["grid"]) == 141


def test_four_figures_use_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert list(figures) == [
        "packages_strikes",
        "packages_range_forward",
        "packages_deferred",
        "packages_risk",
    ]
    assert all(fig.layout.meta["section"] == "26.1" for fig in figures.values())
    assert [fig.layout.meta["figure"] for fig in figures.values()] == list(figures)

    strikes = figures["packages_strikes"]
    curve = data["strike_curve"]["points"]
    assert list(strikes.data[0].x) == [p["put_strike"] for p in curve]
    assert list(strikes.data[0].y) == [p["call_strike"] for p in curve]
    anchor = data["anchor_17_2"]
    marked = next(t for t in strikes.data if t.name and "§17.2" in t.name)
    assert list(marked.x) == [anchor["put_strike"]]
    assert list(marked.y) == [anchor["call_strike"]]

    payoff = data["figure_payoffs"]
    range_forward = figures["packages_range_forward"]
    assert list(range_forward.data[0].x) == payoff["grid"]
    assert list(range_forward.data[0].y) == payoff["payoffs"]["forward"]
    assert list(range_forward.data[1].y) == payoff["payoffs"]["range_forward"]

    deferred = figures["packages_deferred"]
    assert list(deferred.data[2].y) == payoff["payoffs"]["break_forward"]
    assert min(deferred.data[2].y) == pytest.approx(-payoff["amount"], abs=1e-15)
    breakeven = next(t for t in deferred.data if t.name and "損益分岐" in t.name)
    assert list(breakeven.x) == [payoff["breakeven"]]

    risk = figures["packages_risk"]
    rows = data["risk_comparison"]
    losses = {t.legendgroup: t.y[0] for t in risk.data if t.xaxis == "x"}
    assert losses == {name: rows[name]["loss_pv_quadrature"] for name in rows}
    caps = {t.legendgroup: t.y[0] for t in risk.data if t.xaxis == "x3"}
    assert caps == {name: rows[name]["max_loss"] for name in rows}


def test_hash_guard_rejects_a_changed_reference(tmp_path):
    data = _load_reference()
    data["anchor_17_2"]["call_strike"] += 0.01
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _load_reference(changed)
