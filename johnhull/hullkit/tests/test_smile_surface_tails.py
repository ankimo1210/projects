"""Hull 20.2: normal historical benchmark and a synthetic moment-matched Q smile."""

import math

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from scipy.integrate import quad
from scipy.stats import lognorm, norm


def test_table_20_1_normal_exceedances_all_six_rows():
    actual = 100 * smile.normal_exceedance(np.arange(1, 7))
    assert actual == pytest.approx([31.73, 4.55, 0.27, 0.01, 0, 0], abs=0.005)
    reference = [100 * 2 * quad(norm.pdf, n, 12, epsabs=1e-15)[0] for n in range(1, 7)]
    assert actual == pytest.approx(reference, abs=1e-12)
    # Historical 2005-2015 real-world observations are unavailable; the
    # synthetic Q mixture below is not an empirical replication of that column.


def test_mixture_and_benchmark_same_mean_variance_against_independent_integrals():
    result = smile.mixture_lognormal_moments(1, 0.04, 0.02, 1, [0.85, 0.15], [0.1, 0.5])
    means = []
    seconds = []
    forward = math.exp(0.02)
    for sigma in [0.1, 0.5]:
        means.append(
            quad(
                lambda z, sigma=sigma: (
                    forward * math.exp(-sigma * sigma / 2 + sigma * z) * norm.pdf(z)
                ),
                -12,
                12,
                epsabs=1e-12,
            )[0]
        )
        seconds.append(
            quad(
                lambda z, sigma=sigma: (
                    (forward * math.exp(-sigma * sigma / 2 + sigma * z)) ** 2 * norm.pdf(z)
                ),
                -12,
                12,
                epsabs=1e-12,
            )[0]
        )
    mean = float(np.dot([0.85, 0.15], means))
    variance = float(np.dot([0.85, 0.15], seconds)) - mean**2
    assert result["mean"] == pytest.approx(mean, abs=1e-12)
    assert result["variance"] == pytest.approx(variance, abs=1e-12)
    benchmark = lognorm(
        s=result["matched_volatility"],
        scale=forward * math.exp(-(result["matched_volatility"] ** 2) / 2),
    )
    assert benchmark.mean() == pytest.approx(mean, abs=1e-12)
    assert benchmark.var() == pytest.approx(variance, abs=1e-12)


@pytest.mark.parametrize("kind,strike", [("put", 0.6), ("call", 1.7)])
def test_tail_option_price_against_direct_mixture_terminal_density_integral(kind, strike):
    result = smile.mixture_lognormal_option(
        1, strike, 0.04, 0.02, 1, [0.85, 0.15], [0.1, 0.5], kind=kind
    )
    forward = math.exp(0.02)

    def density(terminal):
        return sum(
            w * lognorm.pdf(terminal, s=sigma, scale=forward * math.exp(-sigma * sigma / 2))
            for w, sigma in zip([0.85, 0.15], [0.1, 0.5], strict=True)
        )

    low, high = (0, strike) if kind == "put" else (strike, math.inf)
    sign = -1 if kind == "put" else 1
    reference = (
        math.exp(-0.04)
        * quad(lambda x: sign * (x - strike) * density(x), low, high, epsabs=1e-11)[0]
    )
    assert result["price"] == pytest.approx(reference, abs=1e-11)
    assert result["price"] > result["matched_price"]


def test_both_deep_tails_have_higher_iv_than_atm_for_synthetic_q_mixture():
    implied = [
        smile.mixture_lognormal_option(1, k, 0.04, 0.02, 1, [0.85, 0.15], [0.1, 0.5])[
            "implied_volatility"
        ]
        for k in [0.6, 1, 1.7]
    ]
    assert implied[0] > implied[1] and implied[2] > implied[1]
    for strike in [0.6, 1, 1.7]:
        call = smile.mixture_lognormal_option(1, strike, 0.04, 0.02, 1, [0.85, 0.15], [0.1, 0.5])
        put = smile.mixture_lognormal_option(
            1, strike, 0.04, 0.02, 1, [0.85, 0.15], [0.1, 0.5], kind="put"
        )
        assert call["implied_volatility"] == pytest.approx(put["implied_volatility"], abs=1e-9)
        assert call["price"] - put["price"] == pytest.approx(
            math.exp(-0.02) - strike * math.exp(-0.04), abs=1e-12
        )


def test_one_nonzero_weight_returns_the_lognormal_benchmark_without_smile():
    result = smile.mixture_lognormal_option(1, 1.2, 0.04, 0.02, 1, [1, 0], [0.2, 0.5])
    assert result["matched_volatility"] == pytest.approx(0.2, abs=1e-12)
    assert result["price"] == pytest.approx(result["matched_price"], abs=1e-12)
    assert result["implied_volatility"] == pytest.approx(0.2, abs=1e-10)


@pytest.mark.parametrize(
    "weights,vols", [([-1, 2], [0.1, 0.5]), ([0.4, 0.4], [0.1, 0.5]), ([1], [0.1, 0.5])]
)
def test_probability_weights_must_match_nonnegative_components_and_sum_to_one(weights, vols):
    with pytest.raises(ValueError):
        smile.mixture_lognormal_moments(1, 0.04, 0.02, 1, weights, vols)
