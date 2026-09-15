"""Semantic contracts for the shared Hull §26.10 lesson figures."""

import math

import numpy as np
import pytest
from hullkit._binary_lesson import _cash_delta, _figures, _payoffs
from scipy.integrate import quad


def _discounted_cash_call(spot, strike, rate, volatility, expiry, dividend, payout):
    """Integrate a cash-call payoff against the terminal lognormal density."""
    drift = (rate - dividend - 0.5 * volatility**2) * expiry
    scale = volatility * math.sqrt(expiry)
    threshold = (math.log(strike / spot) - drift) / scale

    def density(z):
        return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    probability, error = quad(density, threshold, math.inf, epsabs=1e-12, epsrel=1e-12)
    assert error * payout * math.exp(-rate * expiry) < 1e-9
    return payout * math.exp(-rate * expiry) * probability


def _finite_difference_cash_delta(spot, strike, rate, volatility, expiry, dividend, payout):
    """Differentiate independently integrated cash-call values in spot."""
    bump = spot * 1e-5

    def price(bumped_spot):
        return _discounted_cash_call(
            bumped_spot, strike, rate, volatility, expiry, dividend, payout
        )

    return (price(spot + bump) - price(spot - bump)) / (2.0 * bump)


def _trace_value(trace, x_value):
    """Return a trace value at one exact semantic probe."""
    x = np.asarray(trace.x, dtype=float)
    matches = np.flatnonzero(np.isclose(x, x_value, rtol=0.0, atol=1e-12))
    assert len(matches) == 1, (trace.name, x_value, x[matches])
    return float(np.asarray(trace.y, dtype=float)[matches[0]])


def _traces(fig, **metadata):
    """Select traces by their browser-facing semantic metadata."""
    return [
        trace
        for trace in fig.data
        if trace.meta is not None
        and all(trace.meta.get(key) == value for key, value in metadata.items())
    ]


@pytest.mark.parametrize(
    ("strike", "payout", "terminal", "expected"),
    [
        (
            100.0,
            100.0,
            [80.0, 100.0, 120.0],
            {
                "cash_call": [0.0, 100.0, 100.0],
                "cash_put": [100.0, 0.0, 0.0],
                "asset_call": [0.0, 100.0, 120.0],
                "asset_put": [80.0, 0.0, 0.0],
            },
        ),
        (
            75.0,
            12.5,
            [70.0, 75.0, 90.0],
            {
                "cash_call": [0.0, 12.5, 12.5],
                "cash_put": [12.5, 0.0, 0.0],
                "asset_call": [0.0, 75.0, 90.0],
                "asset_put": [70.0, 0.0, 0.0],
            },
        ),
    ],
)
def test_payoffs_pin_each_contract_and_the_strike_tie(strike, payout, terminal, expected):
    # This catches swapping >=/< at K or deriving individual legs only by parity.
    actual = _payoffs(terminal, strike=strike, payout=payout)
    assert list(actual) == ["cash_call", "cash_put", "asset_call", "asset_put"]
    for contract, values in expected.items():
        assert isinstance(actual[contract], np.ndarray)
        np.testing.assert_array_equal(actual[contract], values)


def test_payoffs_are_exact_complements_for_cash_and_asset_binaries():
    terminal = np.array([1.0, 74.999, 75.0, 75.001, 180.0])
    payoffs = _payoffs(terminal, strike=75.0, payout=12.5)
    np.testing.assert_array_equal(payoffs["cash_call"] + payoffs["cash_put"], 12.5)
    np.testing.assert_array_equal(payoffs["asset_call"] + payoffs["asset_put"], terminal)


@pytest.mark.parametrize(
    ("spot", "strike", "rate", "volatility", "expiry", "dividend", "payout"),
    [
        (107.0, 101.0, 0.04, 0.27, 1.3, 0.065, 37.0),
        (100.0, 100.0, 0.03, 0.15, 1.0 / 365.0, 0.01, 123.0),
    ],
)
def test_cash_delta_matches_finite_difference_of_density_integrals(
    spot, strike, rate, volatility, expiry, dividend, payout
):
    # This catches a d1/d2 mix-up, missing q carry, or omitted cash discounting.
    expected = _finite_difference_cash_delta(
        spot, strike, rate, volatility, expiry, dividend, payout
    )
    actual = float(_cash_delta(spot, strike, rate, volatility, expiry, dividend, payout))
    assert actual == pytest.approx(expected, rel=3e-7, abs=2e-9)


def test_cash_delta_is_vectorized_over_positive_spots():
    spots = np.array([80.0, 100.0, 120.0])
    actual = _cash_delta(spots, 100.0, 0.05, 0.20, 1.0, 0.02, 100.0)
    assert isinstance(actual, np.ndarray)
    assert actual.shape == spots.shape
    assert np.all(actual > 0.0)


def test_figure_order_and_layout_metadata_are_stable_browser_contracts():
    figures = _figures()
    assert list(figures) == [
        "binary_payoffs",
        "binary_replication",
        "binary_spreads",
        "binary_delta",
    ]
    expected_market = {
        "S0": 100.0,
        "K": 100.0,
        "r": 0.05,
        "sigma": 0.20,
        "T": 1.0,
        "q": 0.02,
        "payout": 100.0,
    }
    for key, fig in figures.items():
        assert fig.__class__.__name__ == "Figure"
        assert fig.layout.meta == {"section": "26.10", "figure": key, **expected_market}


def test_payoff_figure_preserves_actual_probes_and_separates_one_sided_limits():
    fig = _figures()["binary_payoffs"]
    expected = {
        "cash_call": [0.0, 100.0, 100.0],
        "cash_put": [100.0, 0.0, 0.0],
        "asset_call": [0.0, 100.0, 120.0],
        "asset_put": [80.0, 0.0, 0.0],
    }
    for contract, values in expected.items():
        traces = _traces(fig, role="payoff", contract=contract)
        assert traces
        assert all(
            not (np.min(np.asarray(trace.x)) < 100.0 < np.max(np.asarray(trace.x)))
            for trace in traces
        )
        for probe, wanted in zip((80.0, 100.0, 120.0), values, strict=True):
            hits = []
            for trace in traces:
                x = np.asarray(trace.x, dtype=float)
                where = np.flatnonzero(np.isclose(x, probe, rtol=0.0, atol=1e-12))
                hits.extend(float(np.asarray(trace.y)[i]) for i in where)
            assert wanted in hits, (contract, probe, hits)

    limits = _traces(fig, role="one_sided_limit")
    assert len(limits) == 4
    assert all(trace.marker.symbol == "circle-open" for trace in limits)
    annotation = " ".join(item.text for item in fig.layout.annotations)
    assert "call: S_T ≥ K" in annotation
    assert "put: S_T < K" in annotation
    assert "実際の決済" in annotation and "片側極限" in annotation


def test_custom_strike_payoff_segments_do_not_cross_the_jump():
    # This catches assigning fixed browser probes to the wrong side of a custom K.
    strike = 75.0
    fig = _figures(K=strike, payout=12.5)["binary_payoffs"]
    for trace in _traces(fig, role="payoff"):
        x = np.asarray(trace.x, dtype=float)
        assert not (np.min(x) < strike < np.max(x))


def test_replication_dropdown_exposes_each_signed_leg_and_total_at_the_tie():
    fig = _figures()["binary_replication"]
    buttons = fig.layout.updatemenus[0].buttons
    assert [button.label for button in buttons] == ["call", "put"]
    assert "call" in fig.layout.title.text
    expected = {
        "call": {
            "cash_leg": [0.0, -100.0, -100.0],
            "asset_leg": [0.0, 100.0, 120.0],
            "reconstructed": [0.0, 0.0, 20.0],
            "vanilla": [0.0, 0.0, 20.0],
        },
        "put": {
            "cash_leg": [100.0, 0.0, 0.0],
            "asset_leg": [-80.0, 0.0, 0.0],
            "reconstructed": [20.0, 0.0, 0.0],
            "vanilla": [20.0, 0.0, 0.0],
        },
    }
    for kind, roles in expected.items():
        for role, values in roles.items():
            traces = _traces(fig, role=role, kind=kind)
            assert len(traces) == 1
            for probe, wanted in zip((80.0, 100.0, 120.0), values, strict=True):
                assert _trace_value(traces[0], probe) == wanted

    for index, kind in enumerate(("call", "put")):
        visible = list(buttons[index].args[0]["visible"])
        assert visible == [trace.meta["kind"] == kind for trace in fig.data]
        assert kind in str(buttons[index].args[1])


def test_spread_figure_matches_independent_payoff_calculations_for_every_width():
    fig = _figures()["binary_spreads"]

    def call_payoff(terminal, strike):
        return max(terminal - strike, 0.0)

    for width in (1.0, 5.0, 15.0):
        spread = _traces(fig, role="spread", width=width)
        butterfly = _traces(fig, role="butterfly", width=width)
        assert len(spread) == len(butterfly) == 1
        probes = (
            100.0 - width,
            100.0 - width / 2.0,
            100.0,
            100.0 + width / 2.0,
            100.0 + width,
        )
        for terminal in probes:
            expected_spread = (
                call_payoff(terminal, 100.0 - width / 2.0)
                - call_payoff(terminal, 100.0 + width / 2.0)
            ) / width
            expected_butterfly = (
                call_payoff(terminal, 100.0 - width)
                - 2.0 * call_payoff(terminal, 100.0)
                + call_payoff(terminal, 100.0 + width)
            ) / width**2
            assert _trace_value(spread[0], terminal) == pytest.approx(expected_spread)
            assert _trace_value(butterfly[0], terminal) == pytest.approx(expected_butterfly)

    annotation = " ".join(item.text for item in fig.layout.annotations)
    assert "K では 1/2" in annotation
    assert "不連続点を除いて" in annotation
    assert "割引終端密度" in annotation
    assert "ペイオフ曲線" in annotation


def test_delta_figure_points_match_independent_integral_finite_differences():
    fig = _figures()["binary_delta"]
    expiries = (1.0, 30.0 / 365.0, 1.0 / 365.0)
    assert {trace.meta["T"] for trace in fig.data} == set(expiries)
    for expiry in expiries:
        traces = _traces(fig, role="cash_delta", T=expiry)
        assert len(traces) == 1
        plotted = _trace_value(traces[0], 100.0)
        expected = _finite_difference_cash_delta(100.0, 100.0, 0.05, 0.20, expiry, 0.02, 100.0)
        assert plotted == pytest.approx(expected, rel=3e-7, abs=2e-9)

    annotation = " ".join(item.text for item in fig.layout.annotations)
    assert "有限の正の T" in annotation
    assert "満期接近" in annotation
