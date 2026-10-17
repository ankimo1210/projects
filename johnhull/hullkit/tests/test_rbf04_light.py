"""RB-F04 light hedging study: simulator, tangents, deltas, and accounting."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit import _model_dynamics

PATH = Path(__file__).resolve().parents[2] / "research/RB-F04/light/hedge_light.py"


@pytest.fixture(scope="module")
def light():
    spec = importlib.util.spec_from_file_location("rbf04_light_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def surface(light):
    return light.local_grid()


def test_paths_match_the_rbf04_v1_simulators_at_every_observation(light, surface):
    z = light.normals(64, 99)
    obs = np.r_[0, light.observation_steps()]
    heston = light.simulate("heston", z)
    reference = _model_dynamics.heston_monthly(light.PARAMS, z)
    np.testing.assert_allclose(heston["spot"][:, obs], reference["observations"], rtol=1e-12)
    np.testing.assert_allclose(
        heston["state"][:, obs], reference["variance_observations"], rtol=1e-12, atol=1e-15
    )
    local = light.simulate("local", z, surface)
    reference = _model_dynamics.local_monthly(light.PARAMS, surface, z)
    np.testing.assert_allclose(local["spot"][:, obs], reference["observations"], rtol=1e-12)


def test_heston_tangent_is_the_spot_ratio(light):
    paths = light.simulate("heston", light.normals(32, 98))
    np.testing.assert_allclose(paths["tangent"], paths["spot"] / light.PARAMS.spot, rtol=1e-12)


def test_heston_variance_tangent_matches_a_finite_difference(light):
    z = light.normals(256, 93)
    v0, bump = light.PARAMS.v0, 1e-6
    base = light.simulate("heston", z)
    bumped = light.simulate("heston", z, start_variance=v0 + bump)
    for m in (48, 192):
        finite = (np.log(bumped["spot"][:, m]) - np.log(base["spot"][:, m])) / bump
        pathwise = base["vega_level"][:, m] - base["vega_level"][:, 0]
        np.testing.assert_allclose(finite, pathwise, rtol=2e-3, atol=1e-4)


def test_local_tangent_matches_a_finite_difference_of_the_scheme(light, surface):
    z = light.normals(256, 97)
    base = light.simulate("local", z, surface)
    n, bump = 48, 1e-4
    restarted = light.simulate(
        "local", z, surface, start_step=n, start_spot=base["spot"][:, n] * (1 + bump)
    )
    for m in (96, 192):
        finite = (restarted["spot"][:, m] - base["spot"][:, m]) / (bump * base["spot"][:, n])
        pathwise = base["tangent"][:, m] / base["tangent"][:, n]
        relative = np.abs(finite - pathwise) / np.abs(pathwise)
        # Piecewise-linear interpolation of the grid makes the map kinked at
        # nodes; the median path is smooth over the bump.
        assert np.median(relative) < 1e-3
        assert np.quantile(relative, 0.9) < 2e-2


def test_delta_is_exact_once_the_option_is_certainly_in_the_money(light):
    paths = light.simulate("bs", light.normals(512, 96))
    model = light.DeltaModel("bs", paths, np.arange(0, light.STEPS, 16))
    n = 160
    spot = np.array([100.0, 100.0])
    realized = np.array([12 * light.STRIKE + 1.0, 50.0])
    delta = model.delta(n, spot, realized, np.full(2, light.PARAMS.theta))
    dt = light.EXPIRY / light.STEPS
    future = light.observation_steps()[light.observation_steps() > n]
    expected = (
        np.exp(-light.PARAMS.rate * (light.EXPIRY - n * dt))
        * np.exp(light.PARAMS.rate * (future * dt - n * dt)).sum()
        / 12
    )
    assert delta[0] == pytest.approx(expected)
    assert 0 <= delta[1] <= expected


def test_bs_delta_at_zero_matches_a_bumped_price(light):
    z = light.normals(4096, 95)
    paths = light.simulate("bs", z)
    model = light.DeltaModel("bs", paths, np.array([0]))
    bump = 0.01
    up = light.discounted_payoff(paths["spot"] * (1 + bump)).mean()
    down = light.discounted_payoff(paths["spot"] * (1 - bump)).mean()
    finite = (up - down) / (2 * bump * light.PARAMS.spot)
    assert model.initial == pytest.approx(finite, abs=5e-3)


def test_hedge_accounting_without_trades_is_the_premium_minus_the_payoff(light):
    world = light.simulate("bs", light.normals(256, 94))

    class Zero:
        def delta(self, n, spot, realized, variance):
            return np.zeros_like(spot)

    price = float(light.discounted_payoff(world["spot"]).mean())
    result = light.hedge(world, Zero(), 4, price, cost=0.01)
    assert result["mean"] == pytest.approx(0.0, abs=1e-12)
    assert result["mean_cost"] == 0.0


def test_small_run_hedges_better_with_more_frequent_rebalancing(light):
    results = light.run(2048)
    in_model = results["hedging_no_cost"]["heston"]
    assert in_model["weekly"]["heston"]["std"] < in_model["monthly"]["heston"]["std"]
    complete = results["hedging_no_cost"]["local"]
    assert complete["twice_weekly"]["local"]["std"] < complete["weekly"]["local"]["std"]
    assert results["prices"]["heston"]["price"] > 0
    costs = results["hedging_weekly_cost_10bp"]["heston"]
    assert costs["band_0.1"]["heston"]["mean_cost"] < costs["band_0"]["heston"]["mean_cost"]
