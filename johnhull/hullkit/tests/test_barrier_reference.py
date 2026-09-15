"""Independent §26.9 reference: integrate a GBM terminal density and bridge hit law.

No Hull barrier formula, BGK shift or in/out complement is used in the oracle.
All values here use synthetic parameters, not a printed Hull numerical example.
"""

import math
from itertools import pairwise

import pytest
from hullkit import bsm, exotics
from scipy.integrate import quad
from scipy.stats import norm


def _bridge_reference(S, K, H, r, sigma, T, q, direction, knock, kind):
    variance = sigma**2 * T
    drift = (r - q - sigma**2 / 2) * T
    scale = math.sqrt(variance)
    barrier = math.log(H / S)
    breached = (direction == "down" and S <= H) or (direction == "up" and S >= H)

    def integrand(z):
        terminal_log = drift + scale * z
        payoff = max((1 if kind == "call" else -1) * (S * math.exp(terminal_log) - K), 0)
        beyond = terminal_log <= barrier if direction == "down" else terminal_log >= barrier
        # Conditional bridge survival between time 0 and T; equality means a touch.
        survival = (
            0.0
            if breached or beyond
            else -math.expm1(-2 * barrier * (barrier - terminal_log) / variance)
        )
        weight = survival if knock == "out" else 1 - survival
        return math.exp(-r * T) * payoff * weight * norm.pdf(z)

    # Twelve standard deviations make the discarded lognormal tail negligible
    # for this explicit parameter grid. Split at both non-smooth payoff levels.
    points = sorted(
        {
            -12.0,
            12.0,
            max(-12.0, min(12.0, (barrier - drift) / scale)),
            max(-12.0, min(12.0, (math.log(K / S) - drift) / scale)),
        }
    )
    return sum(quad(integrand, a, b, epsabs=2e-11, epsrel=2e-11)[0] for a, b in pairwise(points))


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("knock", ["in", "out"])
@pytest.mark.parametrize(("direction", "S", "H"), [("down", 110.0, 95.0), ("up", 90.0, 105.0)])
@pytest.mark.parametrize("strike_ratio", [0.85, 1.0, 1.15])
@pytest.mark.parametrize(
    ("r", "q", "sigma", "T"), [(0.05, 0.0, 0.2, 1.0), (-0.01, 0.03, 0.4, 0.75)]
)
def test_all_eight_barriers_match_independent_integral(
    kind, knock, direction, S, H, strike_ratio, r, q, sigma, T
):
    K = H * strike_ratio
    expected = _bridge_reference(S, K, H, r, sigma, T, q, direction, knock, kind)
    pricer = exotics.barrier_call if kind == "call" else exotics.barrier_put
    actual = pricer(S, K, H, r, sigma, T, q, barrier=f"{direction}-and-{knock}")
    assert actual == pytest.approx(expected, abs=2e-8)
    vanilla = (bsm.call_price if kind == "call" else bsm.put_price)(S, K, r, sigma, T, q)
    assert -1e-10 <= actual <= vanilla + 1e-10


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("direction", ["up", "down"])
@pytest.mark.parametrize("knock", ["in", "out"])
@pytest.mark.parametrize("n_observations", [None, 52])
def test_touch_at_inception_is_observed(kind, direction, knock, n_observations):
    # The implementation assumes t=0 is observed, including for discrete contracts.
    pricer = exotics.barrier_call if kind == "call" else exotics.barrier_put
    value = pricer(
        100,
        105,
        100,
        0.05,
        0.2,
        1,
        0.02,
        barrier=f"{direction}-and-{knock}",
        n_observations=n_observations,
    )
    expected = _bridge_reference(100, 105, 100, 0.05, 0.2, 1, 0.02, direction, knock, kind)
    assert value == pytest.approx(expected, abs=2e-8)


def test_up_out_call_can_have_negative_vega():
    lower = exotics.barrier_call(99, 90, 100, 0.05, 0.20, 1, barrier="up-and-out")
    higher = exotics.barrier_call(99, 90, 100, 0.05, 0.21, 1, barrier="up-and-out")
    assert higher < lower
    assert bsm.call_price(99, 90, 0.05, 0.21, 1) > bsm.call_price(99, 90, 0.05, 0.20, 1)


@pytest.mark.parametrize(("direction", "kind"), [("up", "call"), ("down", "put")])
@pytest.mark.parametrize("knock", ["in", "out"])
@pytest.mark.parametrize("observations", [None, 4, 52])
@pytest.mark.parametrize("strike_offset", [0.0, 1.0])
def test_terminal_observation_preserves_impossible_out_payoff(
    direction, kind, knock, observations, strike_offset
):
    # T is always a fixing date: a positive intrinsic value implies a barrier
    # touch at T, so the out contract is exactly worthless even with sparse fixing.
    # Check H=K and nearby H<K (up call) / H>K (down put), where BGK crosses K.
    S, H = (100.0, 110.0) if direction == "up" else (100.0, 90.0)
    K = H + strike_offset if direction == "up" else H - strike_offset
    pricer = exotics.barrier_call if kind == "call" else exotics.barrier_put
    vanilla = (bsm.call_price if kind == "call" else bsm.put_price)(S, K, 0.05, 0.3, 1)
    value = pricer(
        S, K, H, 0.05, 0.3, 1, barrier=f"{direction}-and-{knock}", n_observations=observations
    )
    assert value == (vanilla if knock == "in" else 0.0)


@pytest.mark.parametrize(
    ("S", "K", "r", "sigma", "T"),
    [
        (100.0, 100.0, 0.05, 0.2, 1.0),
        (200.0, 180.0, 0.035, 0.28, 0.6),
    ],
)
def test_displayed_barrier_prices_match_independent_integral(S, K, r, sigma, T):
    from hullkit import plotly_viz

    figure = plotly_viz.plotly_barrier_knockout(S, K, r, sigma, T)
    for button in figure.layout.updatemenus[0].buttons:
        visible = [
            trace
            for trace, show in zip(figure.data, button.args[0]["visible"], strict=True)
            if show
        ]
        selected = visible[0]
        kind, contract = button.label.split(" / ")
        direction, _, knock = contract.split("-")
        indices = {0, len(selected.x) // 3, 2 * len(selected.x) // 3, len(selected.x) - 1}
        for index in indices:
            H = float(selected.x[index])
            expected = _bridge_reference(S, K, H, r, sigma, T, 0, direction, knock, kind)
            assert selected.y[index] == pytest.approx(expected, abs=2e-8)
