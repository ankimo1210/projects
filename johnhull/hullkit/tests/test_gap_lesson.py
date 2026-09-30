"""The §26.4 Book and portal plots use the saved independent values."""

import json

import pytest
from hullkit._gap_lesson import _figures, _load_reference

KEYS = {"gap_payoff", "gap_settlement_line", "gap_insurance", "gap_transfer_cost"}


def _without_gap(values):
    return [value for value in values if value is not None]


def test_four_shared_figures_are_exactly_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert set(figures) == KEYS
    for key, figure in figures.items():
        assert figure.layout.meta["section"] == "26.4"
        assert figure.layout.meta["figure"] == key
    payoff = data["figure"]["payoff"]
    traces = figures["gap_payoff"].data
    assert list(traces[0].y) == payoff["regular_call"]
    assert _without_gap(traces[1].x) == payoff["grid"]
    assert _without_gap(traces[1].y) == payoff["gap_call_K1_90"]
    assert _without_gap(traces[2].y) == payoff["gap_call_K1_110"]
    line = data["figure"]["settlement_line"]
    assert list(figures["gap_settlement_line"].data[0].y) == pytest.approx(line["call"])
    assert list(figures["gap_settlement_line"].data[1].y) == pytest.approx(line["put"])
    means = figures["gap_settlement_line"].data[3]
    assert list(means.x) == pytest.approx(
        [
            data["conditional_mean"]["call"]["closed_form"],
            data["conditional_mean"]["put"]["closed_form"],
        ]
    )
    insurance = data["figure"]["insurance"]
    assert _without_gap(figures["gap_insurance"].data[1].y) == insurance["insurer_gap_put"]
    rows = data["figure"]["transfer_cost"]["rows"]
    assert list(figures["gap_transfer_cost"].data[0].y) == pytest.approx(
        [r["insurer_cost"] for r in rows]
    )
    printed = figures["gap_transfer_cost"].data[3]
    assert list(printed.y) == pytest.approx(
        [data["example_26_1"]["regular_put"], data["example_26_1"]["insurer_gap_put"]]
    )


def test_payoff_lines_break_exactly_once_at_the_trigger():
    figures = _figures()
    for key, trigger, kind in (("gap_payoff", 100.0, "call"), ("gap_insurance", 350_000.0, "put")):
        x = list(figures[key].data[1].x)
        y = list(figures[key].data[1].y)
        cut = x.index(None)
        assert x.count(None) == 1
        if kind == "call":
            assert x[cut - 1] <= trigger < x[cut + 1]
            assert y[cut - 1] == 0.0 and y[cut + 1] != 0.0
        else:
            assert x[cut - 1] < trigger <= x[cut + 1]
            assert y[cut - 1] > 0.0 and y[cut + 1] == 0.0


def test_reference_hash_rejects_changed_price(tmp_path):
    data = _load_reference()
    data["cases"][0]["price"] += 1.0
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        _load_reference(path=path)


def test_open_markers_sit_at_the_one_sided_limits_of_each_jump():
    data = _load_reference()
    figures = _figures()
    payoff = data["figure"]["payoff"]
    after = payoff["grid"].index(100.5)
    markers = figures["gap_payoff"].data[3]
    assert list(markers.x) == [100.0, 100.0]
    assert list(markers.y) == pytest.approx(
        [payoff["gap_call_K1_90"][after] - 0.5, payoff["gap_call_K1_110"][after] - 0.5]
    )
    example = data["example_26_1"]
    insurance = data["figure"]["insurance"]
    before = insurance["grid"].index(example["K2"]) - 1
    limit = figures["gap_insurance"].data[2]
    assert list(limit.x) == [example["K2"]]
    assert list(limit.y) == pytest.approx([insurance["insurer_gap_put"][before] - 2_500.0])
    assert insurance["insurer_gap_put"][before + 1] == 0.0
