"""The §26.3 Book and portal plots use the saved independent values."""

import json

import pytest
from hullkit._nonstandard_american_lesson import _figures, _load_reference

KEYS = {"scheduled_ordering", "scheduled_warrant", "scheduled_exercise", "scheduled_frequency"}


def test_four_shared_figures_are_exactly_the_saved_reference():
    data = _load_reference()
    figures = _figures()
    assert set(figures) == KEYS
    for key, figure in figures.items():
        assert figure.layout.meta["section"] == "26.3"
        assert figure.layout.meta["figure"] == key
    rows = data["cases"][:4]
    assert list(figures["scheduled_ordering"].data[0].x) == [row["label"] for row in rows]
    assert list(figures["scheduled_ordering"].data[0].y) == pytest.approx(
        [row["price"] for row in rows]
    )
    assert list(figures["scheduled_warrant"].data[0].x) == data["figure"]["warrant_years"]
    assert list(figures["scheduled_warrant"].data[0].y) == data["figure"]["warrant_strikes"]
    assert (
        list(figures["scheduled_frequency"].data[0].x)
        == data["figure"]["exercise_frequency"]["date_counts"]
    )
    assert list(figures["scheduled_frequency"].data[0].y) == pytest.approx(
        data["figure"]["exercise_frequency"]["prices"]
    )


def test_reference_hash_rejects_changed_price(tmp_path):
    data = _load_reference()
    data["cases"][0]["price"] += 1.0
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        _load_reference(path=path)
