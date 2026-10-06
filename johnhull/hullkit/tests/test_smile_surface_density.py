"""Hull Appendix20A: density recovery, finite-width error and raw mass."""

import math

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from scipy.integrate import quad
from scipy.stats import lognorm, norm


def density_price(spot, strike, rate, yield_rate, sigma, time, kind):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-14,
        )[0]
    )


STRIKES = np.arange(6, 14.01, 0.5)
VOLS = 0.30 - 0.01 * (STRIKES - 6)


def example():
    return smile.smile_density_grid(10, 0.03, 0, 0.25, STRIKES, VOLS)


def test_example_20a_1_prices_all_eight_densities_and_unrenormalized_mass():
    result = example()
    assert result["call_prices"][:3] == pytest.approx([4.045, 3.549, 3.055], abs=0.0005)
    assert result["strikes"][::2] == pytest.approx(np.arange(6.5, 14, 1), abs=1e-12)
    assert result["density"][::2] == pytest.approx(
        [0.0057, 0.0444, 0.1545, 0.2781, 0.2813, 0.1659, 0.0573, 0.0113], abs=0.00005
    )
    summary = smile.density_bin_summary(np.arange(6, 15), result["density"][::2])
    assert summary["mass_sum"] == pytest.approx(0.998473283, abs=5e-10)
    assert summary["mass_residual"] == pytest.approx(0.001526717, abs=5e-10)
    assert summary["mass_sum"] == pytest.approx(0.9985, abs=0.00005)
    assert summary["mass_residual"] == pytest.approx(0.0015, abs=0.00005)
    assert not result["has_negative_density"]


def test_example_densities_against_independent_per_strike_payoff_integral():
    independent = np.array(
        [density_price(10, k, 0.03, 0, v, 0.25, "call") for k, v in zip(STRIKES, VOLS, strict=True)]
    )
    expected = math.exp(0.03 * 0.25) * np.diff(independent, n=2) / 0.5**2
    assert example()["density"] == pytest.approx(expected, abs=2e-12)


def test_textbook_rounded_prices_amplify_first_density_error():
    rounded = smile.implied_density_grid([6, 6.5, 7], [4.045, 3.549, 3.055], 0.03, 0.25)
    assert rounded["density"][0] == pytest.approx(0.008060226, abs=1e-9)
    assert abs(rounded["density"][0] - example()["density"][0]) > 0.002


@pytest.mark.parametrize("rate,yield_rate", [(0.03, 0), (-0.02, 0.04)])
def test_flat_iv_density_converges_quadratically_to_analytic_lognormal(rate, yield_rate):
    mean = math.log(10) + (rate - yield_rate - 0.26**2 / 2) * 0.25
    law = lognorm(s=0.26 * math.sqrt(0.25), scale=math.exp(mean))
    errors = []
    for width in [0.4, 0.2, 0.1]:
        k = 10 + np.array([-width, 0, width])
        result = smile.smile_density_grid(10, rate, yield_rate, 0.25, k, np.full(3, 0.26))
        errors.append(abs(result["density"][0] - law.pdf(10)))
    assert errors[0] / errors[1] > 3.8 and errors[1] / errors[2] > 3.8
    assert errors[-1] < 0.0002


def test_butterfly_payoff_area_is_wing_width_squared():
    for width in [0.1, 0.5, 1]:

        def triangle(s, w=width):
            return max(w - abs(s - 10), 0)

        area = quad(triangle, 10 - width, 10 + width, points=[10], epsabs=1e-13)[0]
        assert area == pytest.approx(width**2, abs=1e-12)


@pytest.mark.parametrize("yield_rate", [0, 0.04])
def test_difference_prices_against_independent_discounted_triangle_payoff(yield_rate):
    width = 0.5
    k = np.array([9.5, 10, 10.5])
    result = smile.smile_density_grid(10, 0.03, yield_rate, 0.25, k, np.full(3, 0.26))
    mean = math.log(10) + (0.03 - yield_rate - 0.26**2 / 2) * 0.25
    law = lognorm(s=0.26 * math.sqrt(0.25), scale=math.exp(mean))
    pv = (
        math.exp(-0.03 * 0.25)
        * quad(
            lambda s: max(width - abs(s - 10), 0) * law.pdf(s), 9.5, 10.5, points=[10], epsabs=1e-13
        )[0]
    )
    assert pv == pytest.approx(
        result["call_prices"][0] - 2 * result["call_prices"][1] + result["call_prices"][2],
        abs=1e-12,
    )
    assert result["density"][0] == pytest.approx(math.exp(0.03 * 0.25) * pv / width**2, abs=1e-12)


@pytest.mark.parametrize("low,high,printed", [(6, 7, 0.0031), (13, 14, 0.0167)])
def test_textbook_flat_26percent_interval_probabilities_independent_pdf_integral(
    low, high, printed
):
    width = 0.26 * math.sqrt(0.25)
    mean = math.log(10) + (0.03 - 0.26**2 / 2) * 0.25
    exact = norm.cdf((math.log(high) - mean) / width) - norm.cdf((math.log(low) - mean) / width)
    integrated = quad(
        lambda s: (
            math.exp(-0.5 * ((math.log(s) - mean) / width) ** 2)
            / (s * width * math.sqrt(2 * math.pi))
        ),
        low,
        high,
        epsabs=1e-13,
    )[0]
    assert exact == pytest.approx(integrated, abs=1e-12)
    assert exact == pytest.approx(printed, abs=0.00005)
    index = 0 if low == 6 else -1
    actual = example()["density"][::2][index]
    assert actual > exact if low == 6 else actual < exact


def test_negative_curvature_is_returned_and_flagged_without_clipping():
    result = smile.implied_density_grid([8, 9, 10], [3, 2.5, 1], 0.03, 0.25)
    assert result["density"][0] < 0
    assert result["has_negative_density"]


def test_bin_mass_retains_negative_density_and_unequal_interval_widths():
    result = smile.density_bin_summary([0, 1, 3], [-0.1, 0.4])
    assert result["interval_masses"] == pytest.approx([-0.1, 0.8], abs=1e-12)
    assert result["mass_sum"] == pytest.approx(0.7, abs=1e-12)
    assert result["has_negative_density"]


def test_over_unit_mass_retains_negative_residual():
    result = smile.density_bin_summary([0, 1, 2], [0.7, 0.8])
    assert result["mass_sum"] == pytest.approx(1.5, abs=1e-12)
    assert result["mass_residual"] == pytest.approx(-0.5, abs=1e-12)


def test_nonuniform_butterfly_grid_is_mathematically_incompatible():
    with pytest.raises(ValueError):
        smile.implied_density_grid([8, 9, 10.5], [3, 2.5, 1], 0.03, 0.25)


def test_currency_unit_rescaling_density_and_mass_units():
    a = example()
    b = smile.smile_density_grid(1000, 0.03, 0, 0.25, STRIKES * 100, VOLS)
    assert b["density"] == pytest.approx(a["density"] / 100, abs=1e-12)
    summary = smile.density_bin_summary(np.arange(6, 15) * 100, b["density"][::2])
    assert summary["mass_sum"] == pytest.approx(0.998473283, abs=5e-10)
