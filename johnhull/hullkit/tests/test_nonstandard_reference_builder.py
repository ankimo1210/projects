"""Independent stopping-time references for Hull GE §26.3."""

import math
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_nonstandard_reference as ref  # noqa: E402

SMALL = dict(spot=100.0, r=math.log(1.1), sigma=math.log(2.0), maturity=2.0, steps=2, q=0.0)


def test_full_path_enumeration_matches_hand_derived_put_values():
    assert ref.exhaustive_price("put", **SMALL, exercise_strikes={2: 100}) == pytest.approx(
        2700 / 121
    )
    assert ref.exhaustive_price("put", **SMALL, exercise_strikes={1: 100, 2: 100}) == pytest.approx(
        300 / 11
    )
    assert ref.exhaustive_price("put", **SMALL, exercise_strikes={1: 120, 2: 100}) == pytest.approx(
        420 / 11
    )


def test_scalar_recombining_reference_agrees_with_full_path_enumeration():
    schedule = {1: 120, 2: 100}
    assert ref.scalar_tree_price("put", **SMALL, exercise_strikes=schedule) == pytest.approx(
        ref.exhaustive_price("put", **SMALL, exercise_strikes=schedule)
    )


def test_warrant_contract_schedule_is_explicit_on_seven_year_grid():
    data = ref.build()
    warrant = data["warrant"]
    assert warrant["steps"] == 70
    assert warrant["exercise_strikes"] == {
        "30": 30.0,
        "40": 30.0,
        "50": 32.0,
        "60": 32.0,
        "70": 33.0,
    }
    assert 0.0 < warrant["price"] < warrant["spot"]


def test_figure_reference_prices_and_exercise_points_follow_schedule():
    data = ref.build()
    figure = data["figure"]
    ladder = figure["exercise_frequency"]
    assert ladder["date_counts"] == [1, 2, 4, 8, 16, 64]
    assert ladder["prices"] == sorted(ladder["prices"])
    allowed = set(figure["exercise_lattice"]["allowed_steps"])
    assert {row["step"] for row in figure["exercise_lattice"]["points"]} <= allowed
    assert 0 not in allowed


def test_check_mode_rejects_stale_saved_reference(monkeypatch, tmp_path):
    output = tmp_path / "reference.json"
    monkeypatch.setattr(ref, "OUT", output)
    monkeypatch.setattr(sys, "argv", ["build_nonstandard_reference.py"])
    ref.main()
    monkeypatch.setattr(sys, "argv", ["build_nonstandard_reference.py", "--check"])
    ref.main()
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing or stale"):
        ref.main()
