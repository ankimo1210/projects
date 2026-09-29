"""Behavior pins for Hull GE §26.3 nonstandard American options."""

import math

import hullkit
import pytest

nonstandard_american = getattr(hullkit, "nonstandard_american", None)

SMALL = dict(spot=100.0, r=math.log(1.1), sigma=math.log(2.0), maturity=2.0, steps=2)


def test_public_entrypoint_exists():
    assert nonstandard_american is not None


def test_two_step_put_exercises_only_on_allowed_date():
    result = nonstandard_american.scheduled_option(
        "put", **SMALL, exercise_strikes={1: 100, 2: 100}
    )
    assert result.price == pytest.approx(300.0 / 11.0)
    assert result.exercise[0] == (False,)
    assert result.exercise[1] == (False, True)
    assert result.schedule == ((1, 100.0), (2, 100.0))


def test_lockout_and_bermudan_order_against_american():
    european = nonstandard_american.scheduled_option("put", **SMALL, exercise_strikes={2: 100})
    bermudan = nonstandard_american.scheduled_option(
        "put", **SMALL, exercise_strikes={1: 100, 2: 100}
    )
    american = nonstandard_american.scheduled_option(
        "put", **SMALL, exercise_strikes={0: 100, 1: 100, 2: 100}
    )
    assert european.price == pytest.approx(2700.0 / 121.0)
    assert european.price < bermudan.price <= american.price
    assert not any(any(row) for row in european.exercise[:-1])


def test_time_varying_strike_changes_early_exercise():
    low = nonstandard_american.scheduled_option("put", **SMALL, exercise_strikes={1: 90, 2: 100})
    high = nonstandard_american.scheduled_option("put", **SMALL, exercise_strikes={1: 120, 2: 100})
    assert low.price == pytest.approx(2700.0 / 121.0)
    assert not any(low.exercise[1])
    assert high.price == pytest.approx(420.0 / 11.0)
    assert high.exercise[1] == (False, True)


@pytest.mark.parametrize(
    "schedule",
    [
        {},
        {1: 100},
        {-1: 100, 2: 100},
        {3: 100, 2: 100},
        {True: 100, 2: 100},
        {1.0: 100, 2: 100},
        {1: 0, 2: 100},
        {2: math.inf},
    ],
)
def test_invalid_schedule_is_rejected(schedule):
    with pytest.raises(ValueError, match="exercise_strikes"):
        nonstandard_american.scheduled_option("put", **SMALL, exercise_strikes=schedule)


@pytest.mark.parametrize(
    "change",
    [
        {"spot": 0},
        {"sigma": 0},
        {"maturity": 0},
        {"steps": 0},
        {"steps": True},
        {"r": math.inf},
        {"q": math.nan},
    ],
)
def test_invalid_market_or_grid_is_rejected(change):
    args = dict(SMALL, q=0.0)
    args.update(change)
    with pytest.raises(ValueError):
        nonstandard_american.scheduled_option("put", **args, exercise_strikes={2: 100})


def test_kind_is_explicit():
    with pytest.raises(ValueError, match="kind"):
        nonstandard_american.scheduled_option("straddle", **SMALL, exercise_strikes={2: 100})
