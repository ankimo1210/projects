"""Semantic contracts for the shared Hull §26.11 lookback lesson figures."""

import math

import numpy as np
import pytest
from hullkit._lookback_lesson import _figures, _path_payoffs

from .test_lookback_reference import Market, _reference_price

PATH = np.array([100.0, 112.0, 94.0, 121.0, 90.0, 105.0, 84.0, 116.0, 108.0])
CONTRACTS = ("floating_call", "floating_put", "fixed_call", "fixed_put")
MARKET = Market(100.0, 0.05, 0.20, 1.0, 0.02)


def _traces(figure, **metadata):
    """Select traces using the metadata consumed by the browser checks."""
    return [
        trace
        for trace in figure.data
        if trace.meta is not None
        and all(trace.meta.get(key) == value for key, value in metadata.items())
    ]


def _linear_trace_value(trace, time):
    """Evaluate the line Plotly draws between the trace's stored breakpoints."""
    return float(
        np.interp(time, np.asarray(trace.x, dtype=float), np.asarray(trace.y, dtype=float))
    )


def _assert_menu_states_match_trace_metadata(figure, state_key, states, layout_key=None):
    """Each button must reveal only its precomputed state and update layout meta."""
    buttons = figure.layout.updatemenus[0].buttons
    for button, state in zip(buttons, states, strict=True):
        visible = list(button.args[0]["visible"])
        assert visible == [trace.meta[state_key] == state for trace in figure.data]
        assert button.args[1]["meta"][layout_key or state_key] == state


def test_new_and_seasoned_path_payoffs_are_literal_contract_values():
    # Catches a swapped extreme, omission of expiry, or use of current prices.
    new = _path_payoffs(PATH)
    seasoned = _path_payoffs(PATH, minimum_to_date=80.0, maximum_to_date=130.0)
    assert list(new) == list(CONTRACTS)
    assert list(new.values()) == [24.0, 13.0, 21.0, 16.0]
    assert list(seasoned.values()) == [28.0, 22.0, 30.0, 20.0]


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        (1, [8.0, 0.0, 8.0, 0.0]),
        (2, [18.0, 0.0, 8.0, 10.0]),
        (4, [24.0, 0.0, 8.0, 16.0]),
        (8, [24.0, 13.0, 21.0, 16.0]),
    ],
)
def test_nested_monitoring_payoffs_include_today_and_expiry(intervals, expected):
    fixing_indices = range(0, 9, 8 // intervals)
    actual = _path_payoffs(PATH, fixing_indices=fixing_indices)
    assert list(actual.values()) == expected


def test_path_payoffs_add_missing_endpoint_fixings():
    # A caller-provided interior fixing never removes today's or expiry's fixing.
    actual = _path_payoffs(PATH, fixing_indices=[4])
    assert list(actual.values()) == [18.0, 0.0, 8.0, 10.0]


def test_figure_order_default_metadata_and_single_menus_are_stable():
    figures = _figures()
    assert list(figures) == [
        "lookback_payoffs",
        "lookback_history",
        "lookback_replication",
        "lookback_monitoring",
    ]
    for key, figure in figures.items():
        assert figure.__class__.__name__ == "Figure"
        assert figure.layout.meta["section"] == "26.11"
        assert figure.layout.meta["figure"] == key
        assert len(figure.layout.updatemenus) == 1
    assert figures["lookback_payoffs"].layout.meta["scenario"] == "new"
    assert figures["lookback_history"].layout.meta["K"] == 100.0
    assert figures["lookback_replication"].layout.meta["kind"] == "call"
    assert figures["lookback_monitoring"].layout.meta["intervals"] == 8


def test_payoff_figure_exposes_path_extremes_and_payoffs_for_both_histories():
    figure = _figures()["lookback_payoffs"]
    assert [button.label for button in figure.layout.updatemenus[0].buttons] == [
        "新規契約",
        "過去の極値あり",
    ]
    _assert_menu_states_match_trace_metadata(figure, "scenario", ("new", "seasoned"))

    scenarios = {
        "new": (100.0, 100.0, [24.0, 13.0, 21.0, 16.0]),
        "seasoned": (80.0, 130.0, [28.0, 22.0, 30.0, 20.0]),
    }
    for scenario, (past_minimum, past_maximum, expected_payoffs) in scenarios.items():
        spot = _traces(figure, role="spot", scenario=scenario)
        running_minimum = _traces(figure, role="running_min", scenario=scenario)
        running_maximum = _traces(figure, role="running_max", scenario=scenario)
        payoffs = _traces(figure, role="payoffs", scenario=scenario)
        assert len(spot) == len(running_minimum) == len(running_maximum) == len(payoffs) == 1
        np.testing.assert_array_equal(spot[0].y, PATH)
        np.testing.assert_array_equal(
            np.interp(np.linspace(0.0, 1.0, 9), running_minimum[0].x, running_minimum[0].y),
            np.minimum.accumulate(np.minimum(PATH, past_minimum)),
        )
        np.testing.assert_array_equal(
            np.interp(np.linspace(0.0, 1.0, 9), running_maximum[0].x, running_maximum[0].y),
            np.maximum.accumulate(np.maximum(PATH, past_maximum)),
        )
        assert list(payoffs[0].x) == list(CONTRACTS)
        np.testing.assert_array_equal(payoffs[0].y, expected_payoffs)


def test_running_extrema_wait_for_piecewise_linear_crossings_and_follow_afterward():
    figure = _figures()["lookback_payoffs"]
    new_minimum = _traces(figure, role="running_min", scenario="new")[0]
    new_maximum = _traces(figure, role="running_max", scenario="new")[0]

    minimum_crossing = 5.0 / 24.0
    maximum_crossing = 1.0 / 3.0
    assert np.any(np.isclose(new_minimum.x, minimum_crossing, rtol=0.0, atol=1e-12))
    assert np.any(np.isclose(new_maximum.x, maximum_crossing, rtol=0.0, atol=1e-12))
    assert _linear_trace_value(new_minimum, 3.0 / 16.0) == pytest.approx(100.0)
    assert _linear_trace_value(new_minimum, minimum_crossing) == pytest.approx(100.0)
    assert _linear_trace_value(new_minimum, 11.0 / 48.0) == pytest.approx(97.0)
    assert _linear_trace_value(new_maximum, 5.0 / 16.0) == pytest.approx(112.0)
    assert _linear_trace_value(new_maximum, maximum_crossing) == pytest.approx(112.0)
    assert _linear_trace_value(new_maximum, 17.0 / 48.0) == pytest.approx(116.5)

    seasoned_minimum = _traces(figure, role="running_min", scenario="seasoned")[0]
    seasoned_maximum = _traces(figure, role="running_max", scenario="seasoned")[0]
    for time in (3.0 / 16.0, minimum_crossing, 11.0 / 48.0, 5.0 / 16.0, maximum_crossing):
        assert _linear_trace_value(seasoned_minimum, time) == pytest.approx(80.0)
        assert _linear_trace_value(seasoned_maximum, time) == pytest.approx(130.0)


def test_history_figure_all_curve_points_match_independent_extrema_tail_oracle():
    figure = _figures()["lookback_history"]
    strikes = (80.0, 100.0, 125.0)
    assert [button.label for button in figure.layout.updatemenus[0].buttons] == [
        "K=80",
        "K=100",
        "K=125",
    ]
    _assert_menu_states_match_trace_metadata(figure, "strike", strikes, layout_key="K")

    for strike in strikes:
        for contract in CONTRACTS:
            traces = _traces(figure, role="price", contract=contract, strike=strike)
            assert len(traces) == 1
            trace = traces[0]
            for history_extreme, plotted in zip(trace.x, trace.y, strict=True):
                if contract in ("floating_call", "fixed_put"):
                    history = (float(history_extreme) / MARKET.spot, 1.0)
                else:
                    history = (1.0, float(history_extreme) / MARKET.spot)
                strike_ratio = strike / MARKET.spot if contract.startswith("fixed") else 1.0
                expected = _reference_price(MARKET, contract, history, strike_ratio)
                assert float(plotted) == pytest.approx(expected, abs=2e-9, rel=2e-11)

    fixed_put_k80 = _traces(figure, role="price", contract="fixed_put", strike=80.0)[0]
    fixed_call_k125 = _traces(figure, role="price", contract="fixed_call", strike=125.0)[0]
    put_flat = np.asarray(fixed_put_k80.y)[np.asarray(fixed_put_k80.x) >= 80.0]
    call_flat = np.asarray(fixed_call_k125.y)[np.asarray(fixed_call_k125.x) <= 125.0]
    np.testing.assert_allclose(put_flat, put_flat[0], atol=2e-12, rtol=0.0)
    np.testing.assert_allclose(call_flat, call_flat[0], atol=2e-12, rtol=0.0)


def test_replication_figure_all_raw_legs_match_independent_values():
    figure = _figures()["lookback_replication"]
    assert [button.label for button in figure.layout.updatemenus[0].buttons] == [
        "fixed call",
        "fixed put",
    ]
    _assert_menu_states_match_trace_metadata(figure, "kind", ("call", "put"))

    for kind in ("call", "put"):
        traces = {
            role: _traces(figure, role=role, kind=kind)
            for role in ("floating_leg", "stock_leg", "cash_leg", "reconstructed", "fixed")
        }
        assert all(len(selected) == 1 for selected in traces.values())
        strike_grid = np.asarray(traces["fixed"][0].x, dtype=float)
        assert {80.0, 100.0, 125.0}.issubset(set(strike_grid))
        for index, strike in enumerate(strike_grid):
            if kind == "call":
                adjusted_maximum = max(120.0, strike)
                expected_floating = _reference_price(
                    MARKET, "floating_put", (1.0, adjusted_maximum / 100.0)
                )
                expected_stock = 100.0 * math.exp(-0.02)
                expected_cash = -strike * math.exp(-0.05)
                expected_fixed = _reference_price(
                    MARKET, "fixed_call", (0.85, 1.20), strike / 100.0
                )
            else:
                adjusted_minimum = min(85.0, strike)
                expected_floating = _reference_price(
                    MARKET, "floating_call", (adjusted_minimum / 100.0, 1.0)
                )
                expected_stock = -100.0 * math.exp(-0.02)
                expected_cash = strike * math.exp(-0.05)
                expected_fixed = _reference_price(MARKET, "fixed_put", (0.85, 1.20), strike / 100.0)
            expected_reconstructed = expected_floating + expected_stock + expected_cash
            expected_by_role = {
                "floating_leg": expected_floating,
                "stock_leg": expected_stock,
                "cash_leg": expected_cash,
                "reconstructed": expected_reconstructed,
                "fixed": expected_fixed,
            }
            for role, expected in expected_by_role.items():
                plotted = float(np.asarray(traces[role][0].y, dtype=float)[index])
                assert plotted == pytest.approx(expected, abs=2e-9, rel=2e-11)

    teaching = " ".join(annotation.text for annotation in figure.layout.annotations)
    assert all(term in teaching for term in ("M*", "m*", "ペイオフ恒等式", "現在価値"))


def test_monitoring_figure_has_full_path_fixings_and_monotonic_nested_payoffs():
    figure = _figures()["lookback_monitoring"]
    intervals = (1, 2, 4, 8)
    assert [button.label for button in figure.layout.updatemenus[0].buttons] == [
        "1区間",
        "2区間",
        "4区間",
        "8区間",
    ]
    _assert_menu_states_match_trace_metadata(figure, "intervals", intervals)

    expected = {
        1: [8.0, 0.0, 8.0, 0.0],
        2: [18.0, 0.0, 8.0, 10.0],
        4: [24.0, 0.0, 8.0, 16.0],
        8: [24.0, 13.0, 21.0, 16.0],
    }
    payoff_rows = []
    for count in intervals:
        spot = _traces(figure, role="spot", intervals=count)
        fixings = _traces(figure, role="fixings", intervals=count)
        payoffs = _traces(figure, role="payoffs", intervals=count)
        assert len(spot) == len(fixings) == len(payoffs) == 1
        np.testing.assert_array_equal(spot[0].y, PATH)
        indices = np.arange(0, 9, 8 // count)
        np.testing.assert_array_equal(fixings[0].x, indices / 8.0)
        np.testing.assert_array_equal(fixings[0].y, PATH[indices])
        assert list(payoffs[0].x) == list(CONTRACTS)
        np.testing.assert_array_equal(payoffs[0].y, expected[count])
        payoff_rows.append(np.asarray(payoffs[0].y, dtype=float))

    assert np.all(np.diff(np.asarray(payoff_rows), axis=0) >= 0.0)
    teaching = " ".join(annotation.text for annotation in figure.layout.annotations)
    assert "区分線形" in teaching
    assert "GBM" in teaching
    assert "価格精度" in teaching
