"""Hull GE §27.8 Monte Carlo for American options: Tables 27.4-27.7 and the boundary example."""

import math

import numpy as np
import pytest
from hullkit.american_mc import (
    apply_boundary,
    apply_least_squares,
    exercise_boundary,
    least_squares,
)

PATHS = np.array(
    [
        [1.00, 1.09, 1.08, 1.34],
        [1.00, 1.16, 1.26, 1.54],
        [1.00, 1.22, 1.07, 1.03],
        [1.00, 0.93, 0.97, 0.92],
        [1.00, 1.11, 1.56, 1.52],
        [1.00, 0.76, 0.77, 0.90],
        [1.00, 0.92, 0.84, 1.01],
        [1.00, 0.88, 1.22, 1.34],
    ]
)
TIMES = (1.0, 2.0, 3.0)
RATE = 0.06
STRIKE = 1.10


def put(states):
    return np.maximum(STRIKE - states, 0.0)


def _bermudan_crr(spot, strike, rate, sigma, dates, steps_per_date):
    """A CRR put that may be exercised only on ``dates`` (equally spaced years)."""
    dt = dates[0] / steps_per_date
    up = math.exp(sigma * math.sqrt(dt))
    p = (math.exp(rate * dt) - 1 / up) / (up - 1 / up)
    steps = steps_per_date * len(dates)
    prices = spot * up ** np.arange(-steps, steps + 1, 2)
    value = np.maximum(strike - prices, 0.0)
    for n in range(steps - 1, -1, -1):
        prices = prices[1:] / up
        value = math.exp(-rate * dt) * (p * value[1:] + (1 - p) * value[:-1])
        if n and n % steps_per_date == 0:
            value = np.maximum(value, strike - prices)
    return float(value[0])


def test_least_squares_reproduces_tables_27_5_to_27_7():
    result = least_squares(PATHS, put, RATE, TIMES)
    first, second = result.steps
    assert (first.time, second.time) == (1.0, 2.0)
    assert list(second.paths) == [0, 2, 3, 5, 6]
    assert list(first.paths) == [0, 3, 5, 6, 7]
    # Hull prints a = -1.070, b = 2.983, c = -1.813 and 2.038, -3.335, 1.356.
    assert second.coefficients == pytest.approx([-1.069988, 2.983411, -1.813576], abs=1e-6)
    assert first.coefficients == pytest.approx([2.037512, -3.335443, 1.356457], abs=1e-6)
    assert second.coefficients == pytest.approx([-1.070, 2.983, -1.813], abs=1e-3)
    assert first.coefficients == pytest.approx([2.038, -3.335, 1.356], abs=1e-3)
    # Hull's continuation values use the printed coefficients (c = -1.813, though -1.813576
    # rounds to -1.814), so the unrounded fit differs from them by up to 5.4e-4.
    assert second.continuation == pytest.approx(
        [0.0367406, 0.0458983, 0.1175268, 0.1519692, 0.1564179], abs=1e-7
    )
    assert first.continuation == pytest.approx(
        [0.0134851, 0.1087493, 0.2860647, 0.1170093, 0.1527621], abs=1e-7
    )
    printed_second = [0.0369, 0.0461, 0.1176, 0.1520, 0.1565]
    printed_first = [0.0139, 0.1092, 0.2866, 0.1175, 0.1533]
    assert second.continuation == pytest.approx(printed_second, abs=5.4e-4)
    assert first.continuation == pytest.approx(printed_first, abs=5.4e-4)
    assert second.exercise_values == pytest.approx([0.02, 0.03, 0.13, 0.33, 0.26], abs=1e-12)
    assert list(second.exercised) == [3, 5, 6]
    assert list(first.exercised) == [3, 5, 6, 7]
    table_27_7 = np.zeros((8, 3))
    table_27_7[2, 2] = 0.07
    table_27_7[[3, 5, 6, 7], 0] = [0.17, 0.34, 0.18, 0.22]
    assert result.cash_flows == pytest.approx(table_27_7, abs=1e-12)
    assert result.continuation_value == pytest.approx(0.1144343, abs=1e-7)
    assert round(result.continuation_value, 4) == 0.1144
    discounted = result.cash_flows @ np.exp(-RATE * np.array(TIMES))
    assert result.standard_error == pytest.approx(discounted.std(ddof=1) / math.sqrt(8), abs=1e-15)
    assert result.exercise_now == pytest.approx(0.10, abs=1e-12)
    assert result.price == result.continuation_value


def test_printed_coefficients_give_hulls_printed_continuation_values():
    rounded = {2: (-1.070, 2.983, -1.813), 1: (2.038, -3.335, 1.356)}
    printed = {
        2: [0.0369, 0.0461, 0.1176, 0.1520, 0.1565],
        1: [0.0139, 0.1092, 0.2866, 0.1175, 0.1533],
    }
    result = least_squares(PATHS, put, RATE, TIMES)
    for step in result.steps:
        spots = PATHS[step.paths, int(step.time)]
        a, b, c = rounded[int(step.time)]
        assert a + b * spots + c * spots**2 == pytest.approx(printed[int(step.time)], abs=7e-5)


def test_boundary_parameterization_reproduces_the_worked_example():
    result = exercise_boundary(PATHS, put, RATE, TIMES)
    first, second = result.steps
    assert second.candidates[0] == -math.inf
    assert list(second.candidates[1:]) == [0.77, 0.84, 0.97, 1.07, 1.08]
    assert second.averages == pytest.approx(
        [0.0636, 0.0813, 0.1032, 0.0982, 0.0938, 0.0963], abs=5e-5
    )
    assert second.threshold == 0.84
    assert second.interval == (0.84, 0.97)
    assert second.values == pytest.approx([0, 0, 0.0659, 0.1695, 0, 0.33, 0.26, 0], abs=5e-5)
    assert list(first.candidates[1:]) == [0.76, 0.88, 0.92, 0.93, 1.09]
    assert first.averages == pytest.approx(
        [0.0972, 0.1008, 0.1283, 0.1202, 0.1215, 0.1228], abs=5e-5
    )
    assert first.threshold == 0.88
    assert first.interval == (0.88, 0.92)
    assert result.boundary == (0.88, 0.84)
    # Hull's 0.1208 discounts the rounded 0.1283; unrounded it is 0.12085.
    assert result.continuation_value == pytest.approx(0.1208506, abs=1e-7)
    assert round(0.1283 * math.exp(-0.06), 4) == 0.1208
    assert result.price == result.continuation_value


def test_problem_27_15_policies_differ_on_paths_4_and_7():
    lsm = least_squares(PATHS, put, RATE, TIMES)
    boundary = exercise_boundary(PATHS, put, RATE, TIMES)
    assert list(np.nonzero(lsm.cash_flows[:, 0])[0]) == [3, 5, 6, 7]
    assert list(np.nonzero(boundary.cash_flows[:, 0])[0]) == [5, 7]
    assert boundary.cash_flows[6, 1] == pytest.approx(0.26)
    assert boundary.cash_flows[3, 2] == pytest.approx(0.18)
    assert boundary.continuation_value > lsm.continuation_value


def test_policies_applied_to_their_own_paths_reproduce_the_fitted_values():
    rng = np.random.default_rng(11)
    z = rng.standard_normal((4000, 6))
    dt = 0.5
    log_paths = np.cumsum((RATE - 0.02) * dt + 0.2 * math.sqrt(dt) * z, axis=1)
    paths = np.column_stack([np.ones(4000), np.exp(log_paths)])
    times = tuple(dt * (k + 1) for k in range(6))
    for degree in (2, 3):
        fitted = least_squares(paths, put, RATE, times, degree=degree)
        again = apply_least_squares(fitted, paths, put, RATE, times)
        assert again.continuation_value == pytest.approx(fitted.continuation_value, abs=1e-14)
        assert again.cash_flows == pytest.approx(fitted.cash_flows, abs=1e-14)
    boundary = exercise_boundary(paths, put, RATE, times)
    again = apply_boundary(boundary, paths, put, RATE, times)
    assert again.continuation_value == pytest.approx(boundary.continuation_value, abs=1e-14)


def test_out_of_sample_values_stay_near_the_bermudan_lattice():
    rng = np.random.default_rng(5)
    sigma, dt, n = 0.2, 0.5, 40_000
    times = tuple(dt * (k + 1) for k in range(6))

    def simulate():
        z = rng.standard_normal((n, 6))
        steps = (RATE - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z
        return np.column_stack([np.ones(n), np.exp(np.cumsum(steps, axis=1))])

    exact = _bermudan_crr(1.0, STRIKE, RATE, sigma, times, 400)
    fit, fresh = simulate(), simulate()
    for fitted, apply in (
        (least_squares(fit, put, RATE, times), apply_least_squares),
        (exercise_boundary(fit, put, RATE, times), apply_boundary),
    ):
        value = apply(fitted, fresh, put, RATE, times)
        assert abs(value.continuation_value - exact) < 4 * value.standard_error
        assert value.continuation_value < exact + 2 * value.standard_error


def test_two_state_variables_use_all_monomials():
    rng = np.random.default_rng(3)
    first = np.exp(np.cumsum(0.2 * rng.standard_normal((500, 3)), axis=1))
    second = np.exp(np.cumsum(0.3 * rng.standard_normal((500, 3)), axis=1))
    states = np.stack(
        [np.column_stack([np.ones(500), first]), np.column_stack([np.ones(500), second])], axis=2
    )

    def exchange(s):
        return np.maximum(s[:, 0] - s[:, 1], 0.0)

    result = least_squares(states, exchange, 0.05, (1.0, 2.0, 3.0))
    assert all(step.coefficients.shape == (6,) for step in result.steps)
    assert result.degree == 2


def test_a_constant_second_state_reproduces_the_one_dimensional_fit():
    rng = np.random.default_rng(8)
    paths = np.column_stack(
        [np.ones(300), np.exp(np.cumsum(0.25 * rng.standard_normal((300, 3)), axis=1))]
    )
    states = np.stack([paths, np.full_like(paths, 2.0)], axis=2)
    result = least_squares(states, lambda s: put(s[:, 0]), RATE, TIMES)
    one = least_squares(paths, put, RATE, TIMES)
    for step, base in zip(result.steps, one.steps, strict=True):
        assert step.coefficients.shape == (6,)
        assert step.continuation == pytest.approx(base.continuation, abs=1e-10)
        assert list(step.exercised) == list(base.exercised)
    assert result.continuation_value == pytest.approx(one.continuation_value, abs=1e-12)


def test_cubic_basis_has_four_coefficients():
    result = least_squares(PATHS, put, RATE, TIMES, degree=3)
    assert all(step.coefficients.shape == (4,) for step in result.steps)


def test_too_few_in_the_money_paths_skip_the_regression():
    paths = PATHS[[0, 1, 4]]
    result = least_squares(paths, put, RATE, TIMES)
    assert all(step.exercised.size == 0 for step in result.steps)
    assert result.steps[1].paths.size == 1
    assert result.steps[1].coefficients.size == 0


def test_call_boundary_mirrors_the_put_on_negated_states():
    put_result = exercise_boundary(PATHS, put, RATE, TIMES)
    call_result = exercise_boundary(
        -PATHS, lambda s: np.maximum(s + STRIKE, 0.0), RATE, TIMES, kind="call"
    )
    for mirrored, base in zip(call_result.steps, put_result.steps, strict=True):
        assert mirrored.averages == pytest.approx(base.averages, abs=1e-14)
        assert mirrored.threshold == -base.threshold
    assert call_result.continuation_value == pytest.approx(put_result.continuation_value, abs=1e-14)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"paths": PATHS[:, :3]}, "one column per exercise time"),
        ({"times": (1.0, 1.0, 3.0)}, "strictly increasing"),
        ({"times": (0.0, 2.0, 3.0)}, "strictly increasing"),
        ({"rate": math.nan}, "finite"),
        ({"paths": np.where(PATHS == 0.93, np.nan, PATHS)}, "finite"),
        ({"paths": np.column_stack([np.linspace(1, 2, 8), PATHS[:, 1:]])}, "same initial state"),
        ({"payoff": lambda s: np.zeros(3)}, "one value per path"),
        ({"payoff": lambda s: np.full(s.shape[0], np.inf)}, "finite"),
    ],
)
def test_invalid_inputs_are_rejected(kwargs, message):
    args = {"paths": PATHS, "payoff": put, "rate": RATE, "times": TIMES} | kwargs
    for function in (least_squares, exercise_boundary):
        with pytest.raises(ValueError, match=message):
            function(args["paths"], args["payoff"], args["rate"], args["times"])


def test_degree_and_kind_are_validated():
    with pytest.raises(ValueError, match="degree"):
        least_squares(PATHS, put, RATE, TIMES, degree=0)
    with pytest.raises(ValueError, match="kind"):
        exercise_boundary(PATHS, put, RATE, TIMES, kind="straddle")
    states = np.stack([PATHS, PATHS], axis=2)
    with pytest.raises(ValueError, match="one state variable"):
        exercise_boundary(states, lambda s: put(s[:, 0]), RATE, TIMES)


UNEVEN = (0.25, 1.0, 1.1, 2.5, 3.0)


def _gbm(n, times, seed, sigma=0.25):
    rng = np.random.default_rng(seed)
    dt = np.diff(np.concatenate([[0.0], times]))
    steps = (RATE - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rng.standard_normal(
        (n, len(times))
    )
    return np.column_stack([np.ones(n), np.exp(np.cumsum(steps, axis=1))])


def _direct_least_squares(paths, times):
    """Path-by-path backward induction with each cash flow's own time and numpy.polyfit."""
    cash, when = put(paths[:, -1]), np.full(len(paths), times[-1])
    rules = []
    for column in range(len(times) - 1, 0, -1):
        now_time, spots = times[column - 1], paths[:, column]
        exercise = put(spots)
        itm = exercise > 0
        c, b, a = np.polyfit(spots[itm], cash[itm] * np.exp(-RATE * (when[itm] - now_time)), 2)
        rules.append((a, b, c))
        now = itm & (exercise > a + b * spots + c * spots**2)
        cash, when = np.where(now, exercise, cash), np.where(now, now_time, when)
    return float((cash * np.exp(-RATE * when)).mean()), rules[::-1]


def _direct_boundary(paths, times):
    """Hull's boundary search, trying every critical price on the discounted path values."""
    value, thresholds = put(paths[:, -1]), []
    for column in range(len(times) - 1, 0, -1):
        continuation = value * np.exp(-RATE * (times[column] - times[column - 1]))
        spots = paths[:, column]
        exercise = put(spots)
        itm = exercise > 0
        candidates = [-math.inf, *np.unique(spots[itm])]
        averages = [np.where(itm & (spots <= c), exercise, continuation).mean() for c in candidates]
        best = candidates[int(np.argmax(averages))]
        thresholds.append(float(best))
        value = np.where(itm & (spots <= best), exercise, continuation)
    return float(value.mean() * np.exp(-RATE * times[0])), thresholds[::-1]


def _direct_apply(paths, times, rule):
    """First date where the path is in the money and ``rule`` says exercise, discounted to 0."""
    value, alive = np.zeros(len(paths)), np.ones(len(paths), dtype=bool)
    for column, time in enumerate(times, start=1):
        exercise = put(paths[:, column])
        now = alive & (exercise > 0) & rule(column, paths[:, column], exercise)
        value[now] = exercise[now] * math.exp(-RATE * time)
        alive &= ~now
    return float(value.mean())


def test_uneven_exercise_times_match_a_direct_backward_induction():
    fit, fresh = _gbm(3000, UNEVEN, 31), _gbm(3000, UNEVEN, 32)
    last = len(UNEVEN)
    value, rules = _direct_least_squares(fit, UNEVEN)
    lsm = least_squares(fit, put, RATE, UNEVEN)
    assert lsm.continuation_value == pytest.approx(value, abs=1e-12)
    for step, rule in zip(lsm.steps, rules, strict=True):
        assert step.coefficients == pytest.approx(rule, rel=1e-8, abs=1e-8)

    def regression(column, spots, exercise):
        if column == last:
            return np.ones_like(spots, dtype=bool)
        a, b, c = lsm.steps[column - 1].coefficients
        return exercise > a + b * spots + c * spots**2

    applied = apply_least_squares(lsm, fresh, put, RATE, UNEVEN)
    assert applied.continuation_value == pytest.approx(
        _direct_apply(fresh, UNEVEN, regression), abs=1e-12
    )

    value, thresholds = _direct_boundary(fit, UNEVEN)
    boundary = exercise_boundary(fit, put, RATE, UNEVEN)
    assert list(boundary.boundary) == thresholds
    assert boundary.continuation_value == pytest.approx(value, abs=1e-12)
    critical = [*thresholds, math.inf]
    applied = apply_boundary(boundary, fresh, put, RATE, UNEVEN)
    assert applied.continuation_value == pytest.approx(
        _direct_apply(fresh, UNEVEN, lambda column, spots, _: spots <= critical[column - 1]),
        abs=1e-12,
    )


def test_tied_boundary_averages_keep_the_first_critical_price():
    # With no discounting, exercising the second path gains exactly zero, so the
    # critical prices 0.5 and 0.75 tie; the lower one (the first maximum) is kept.
    paths = np.array([[1.0, 0.5, 1.5], [1.0, 0.75, 0.75], [1.0, 0.875, 0.25]])
    put_result = exercise_boundary(paths, lambda s: np.maximum(1.0 - s, 0.0), 0.0, (1.0, 2.0))
    step = put_result.steps[0]
    assert list(step.averages) == pytest.approx([1 / 3, 0.5, 0.5, 0.875 / 3], abs=1e-15)
    assert step.averages[1] == step.averages[2]
    assert (step.threshold, step.interval) == (0.5, (0.5, 0.75))
    call_result = exercise_boundary(
        -paths, lambda s: np.maximum(s + 1.0, 0.0), 0.0, (1.0, 2.0), kind="call"
    )
    assert (call_result.steps[0].threshold, call_result.steps[0].interval) == (-0.5, (-0.75, -0.5))


def test_problem_27_22_interval_is_unbounded_when_every_in_the_money_path_is_exercised():
    put_result = exercise_boundary(PATHS, lambda s: np.maximum(1.13 - s, 0.0), RATE, TIMES)
    assert put_result.steps[0].interval == (1.11, math.inf)
    call_result = exercise_boundary(
        -PATHS, lambda s: np.maximum(s + 1.13, 0.0), RATE, TIMES, kind="call"
    )
    assert call_result.steps[0].interval == (-math.inf, -1.11)


def test_a_regression_needs_only_as_many_in_the_money_paths_as_coefficients():
    result = least_squares(PATHS[:5], put, RATE, TIMES)
    assert result.steps[1].paths.size == 3
    assert result.steps[1].coefficients.size == 3


def test_a_skipped_regression_never_exercises_on_new_paths():
    fitted = least_squares(PATHS[[0, 1, 4]], put, RATE, TIMES)
    applied = apply_least_squares(fitted, PATHS, put, RATE, TIMES)
    assert not applied.cash_flows[:, :2].any()
    assert applied.cash_flows[:, 2] == pytest.approx(put(PATHS[:, 3]), abs=1e-15)


def test_numpy_integer_degree_is_accepted():
    base = least_squares(PATHS, put, RATE, TIMES)
    same = least_squares(PATHS, put, RATE, TIMES, degree=np.int64(2))
    assert same.continuation_value == base.continuation_value
    assert type(same.degree) is int and same.degree == 2
    for bad in (True, 2.0, 0):
        with pytest.raises(ValueError, match="degree"):
            least_squares(PATHS, put, RATE, TIMES, degree=bad)


def test_applied_times_may_differ_from_the_fitted_ones_only_by_rounding():
    lsm = least_squares(PATHS, put, RATE, TIMES)
    boundary = exercise_boundary(PATHS, put, RATE, TIMES)
    nearly = (1.0 + 1e-15, 2.0, 3.0)
    assert apply_least_squares(lsm, PATHS, put, RATE, nearly).continuation_value == pytest.approx(
        lsm.continuation_value, abs=1e-14
    )
    assert apply_boundary(boundary, PATHS, put, RATE, nearly).continuation_value == pytest.approx(
        boundary.continuation_value, abs=1e-14
    )
    for apply, fitted in ((apply_least_squares, lsm), (apply_boundary, boundary)):
        with pytest.raises(ValueError, match="fitted exercise times"):
            apply(fitted, PATHS, put, RATE, (1.0 + 1e-9, 2.0, 3.0))


@pytest.mark.parametrize("kind", ["put", "call"])
def test_boundary_averages_match_the_direct_definition_with_ties(kind):
    rng = np.random.default_rng(21)
    paths = np.column_stack([np.ones(400), np.round(rng.lognormal(0.0, 0.2, (400, 3)), 2)])
    strike = STRIKE if kind == "put" else 0.95

    def payoff(s):
        return np.maximum(strike - s, 0.0) if kind == "put" else np.maximum(s - strike, 0.0)

    result = exercise_boundary(paths, payoff, RATE, TIMES, kind=kind)
    value = payoff(paths[:, 3])
    for column in (2, 1):
        step = result.steps[column - 1]
        continuation = value * math.exp(-RATE)
        exercise = payoff(paths[:, column])
        itm = exercise > 0
        direct = []
        for threshold in step.candidates:
            chosen = itm & (
                paths[:, column] <= threshold if kind == "put" else paths[:, column] >= threshold
            )
            direct.append(np.where(chosen, exercise, continuation).mean())
        assert step.averages == pytest.approx(direct, abs=1e-14)
        assert np.unique(paths[itm, column]).size == step.candidates.size - 1
        value = step.values
