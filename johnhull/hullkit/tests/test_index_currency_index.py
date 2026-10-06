"""Hull 17.4 index prices, printed precision, forward and yield recovery."""

import math

import pytest
from hullkit import _index_currency as index
from hullkit.trees import crr_price
from scipy.integrate import quad
from scipy.stats import norm


def test_example_17_1_price_details_and_printed_truncation():
    result = index.carry_option_details(930, 900, 0.08, 0.03, 0.2, 2 / 12)
    assert result["call"] == pytest.approx(51.83, abs=0.005)
    assert result["d1"] == pytest.approx(0.544478575, abs=5e-10)
    assert math.trunc(result["d1"] * 10000) / 10000 == pytest.approx(0.5444)
    assert [result["d2"], result["N_d1"]] == pytest.approx([0.4628, 0.7069], abs=5e-5)
    # The printed CDF uses the displayed d2=0.4628.
    assert norm.cdf(0.4628) == pytest.approx(0.6782, abs=5e-5)
    assert result["N_d2"] == pytest.approx(norm.cdf(result["d2"]), abs=1e-14)
    assert 100 * round(result["call"], 2) == pytest.approx(5183)
    assert 100 * result["call"] == pytest.approx(5183.2957, abs=5e-5)


def test_business_snapshot_long_term_guarantee_against_payoff_density():
    result = index.carry_option_details(1000, 1492, 0.05, 0.01, 0.15, 10)
    assert result["put"] == pytest.approx(169.7, abs=0.05)
    log_mean = math.log(1000) + (0.05 - 0.01 - 0.15**2 / 2) * 10
    width = 0.15 * math.sqrt(10)
    cutoff = (math.log(1492) - log_mean) / width
    reference = (
        math.exp(-0.05 * 10)
        * quad(
            lambda z: (1492 - math.exp(log_mean + width * z)) * norm.pdf(z),
            -12,
            cutoff,
            epsabs=1e-9,
        )[0]
    )
    assert result["put"] == pytest.approx(reference, abs=1e-9)
    assert round(1000 * math.exp(0.4)) == 1492


@pytest.mark.parametrize("kind", ["call", "put"])
def test_index_example_against_independent_crr(kind):
    result = index.carry_option_details(930, 900, 0.08, 0.03, 0.2, 2 / 12)
    reference = crr_price(930, 900, 0.08, 0.2, 2 / 12, 1600, q=0.03, kind=kind)
    assert result[kind] == pytest.approx(reference, abs=0.01)


def test_forward_and_yield_from_multiple_strikes_including_negative_yield():
    for yield_rate in [-0.02, 0.03, 0.12]:
        forwards = []
        for strike in [70, 100, 140]:
            price = index.carry_option_details(103, strike, 0.05, yield_rate, 0.27, 0.8)
            recovered = index.carry_from_option_quotes(
                103, strike, 0.05, 0.8, price["call"], price["put"]
            )
            forwards.append(recovered["forward"])
            assert recovered["yield_rate"] == pytest.approx(yield_rate, abs=1e-14)
        assert forwards == pytest.approx([103 * math.exp((0.05 - yield_rate) * 0.8)] * 3, abs=1e-11)


def test_implied_carry_requires_positive_forward_and_time():
    with pytest.raises(ValueError):
        index.carry_from_option_quotes(103, 100, 0.05, 0, 8, 5)
    with pytest.raises(ValueError):
        index.carry_from_option_quotes(103, 100, 0.05, 1, 0, 200)
