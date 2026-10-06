"""Hull GE 15.1: stock/log distributions, source rounding and Euler reference."""

import math

import numpy as np
import pytest
from hullkit import _bsm_foundations as foundations
from hullkit.sde import euler_maruyama
from scipy.integrate import quad
from scipy.stats import lognorm


def test_hull_examples_15_1_and_15_2_keep_price_and_log_moments_distinct():
    first = foundations.stock_distribution(40, .16, .2, .5)
    assert [first["log_mean"], first["log_variance"], first["log_sd"]] == pytest.approx([3.759, .02, .141], abs=.0005)
    second = foundations.stock_distribution(20, .2, .4, 1)
    assert [second["price_mean"], second["price_variance"], second["price_sd"]] == pytest.approx([24.43, 103.54, 10.18], abs=.005, rel=0)


def test_hull_interval_uses_printed_intermediate_rounding_and_raw_interval_is_separate():
    source = foundations.lognormal_interval(3.759, .141)
    assert source == pytest.approx([32.55, 56.56], abs=.005, rel=0)
    law = foundations.stock_distribution(40, .16, .2, .5)
    raw = foundations.lognormal_interval(law["log_mean"], law["log_sd"])
    assert raw == pytest.approx([32.514742, 56.603188], abs=.000001)
    assert abs(source[0]-raw[0]) > .02


def test_example_15_2_moments_against_independent_lognormal_density_integrals():
    density = lognorm(s=.4, scale=20*math.exp(.12))
    mean = quad(lambda s: s*density.pdf(s), 0, math.inf, epsabs=1e-9)[0]
    second = quad(lambda s: s*s*density.pdf(s), 0, math.inf, epsabs=1e-8)[0]
    law = foundations.stock_distribution(20, .2, .4, 1)
    assert law["price_mean"] == pytest.approx(mean, abs=1e-8)
    assert law["price_variance"] == pytest.approx(second-mean*mean, abs=1e-7)


@pytest.mark.parametrize("spot,mu,sigma,t", [(40, .16, .2, .5), (20, .2, .4, 1)])
def test_stock_euler_independently_approaches_both_source_distributions(spot, mu, sigma, t):
    paths = euler_maruyama(lambda x, time: mu*x, lambda x, time: sigma*x, spot, t, 400, 20000, rng=np.random.default_rng(151))
    terminal = paths[:, -1]
    assert np.all(terminal > 0)
    law = foundations.stock_distribution(spot, mu, sigma, t)
    for values, target in [(terminal, law["price_mean"]), (np.log(terminal), law["log_mean"])]:
        assert abs(values.mean()-target) < 6*values.std(ddof=1)/math.sqrt(len(values))
    squares = (terminal-law["price_mean"])**2
    assert abs(squares.mean()-law["price_variance"]) < 6*squares.std(ddof=1)/math.sqrt(len(squares))


def test_degenerate_interval_and_negative_standard_deviation():
    assert foundations.lognormal_interval(math.log(40), 0) == pytest.approx([40, 40], abs=1e-12)
    with pytest.raises(ValueError):
        foundations.lognormal_interval(3, -.1)
