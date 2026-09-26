"""Independent PDE, Gil-Pelaez and SABR-transcription references for Hull GE §27.2."""

import math
import sys
from pathlib import Path

import pytest
from hullkit import sabr
from hullkit import stochastic_volatility as sv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def test_time_dependent_pde_prices_the_average_variance_bsm():
    from build_stochastic_volatility_reference import term_structure_pde

    for strike in (90.0, 110.0):
        pde = term_structure_pde(100.0, strike, 0.05, [0.5, 0.5], [0.2, 0.3], 800, 800)
        library = sv.time_dependent_bsm_price(100.0, strike, 0.05, (0.5, 0.5), (0.2, 0.3))
        assert pde == pytest.approx(library, abs=2e-3)


def test_gil_pelaez_matches_library_cos_under_dividends():
    from build_stochastic_volatility_reference import HESTON, heston_gil_pelaez_call

    market = {**HESTON, "dividend_yield": 0.02, "rate": 0.03}
    for rho in (-0.7, 0.4):
        for strike in (70.0, 100.0, 140.0):
            reference = heston_gil_pelaez_call(strike, rho, market)
            library = sv.heston_price(
                100.0, strike, 0.03, 1.0, 0.04, 1.5, 0.04, 0.6, rho, dividend_yield=0.02
            )
            assert library == pytest.approx(reference, abs=1e-8)


def test_hull_sabr_transcription_equals_library_and_atm_limit():
    from build_stochastic_volatility_reference import hull_sabr_vol

    sigma0 = 0.2 * 0.03**0.5
    for rho in (-0.6, 0.0, 0.6):
        for nu in (0.2, 0.8):
            for strike in (0.015, 0.025, 0.03, 0.041, 0.05):
                assert sabr.sabr_implied_vol(
                    0.03, strike, 1.0, sigma0, 0.5, rho, nu
                ) == pytest.approx(
                    hull_sabr_vol(0.03, strike, 1.0, sigma0, 0.5, rho, nu), abs=1e-14
                )
    atm = hull_sabr_vol(0.03, 0.03, 1.0, sigma0, 0.5, -0.3, 0.4)
    near = hull_sabr_vol(0.03, 0.03 * (1 + 1e-6), 1.0, sigma0, 0.5, -0.3, 0.4)
    assert near == pytest.approx(atm, abs=1e-6)
    x = 0.03**0.5
    b = 1 + (
        0.25 * sigma0**2 / (24 * x * x)
        + (-0.3) * 0.5 * 0.4 * sigma0 / (4 * x)
        + (2 - 3 * 0.09) / 24 * 0.16
    )
    assert atm == pytest.approx(sigma0 * b / 0.03**0.5, abs=1e-15)


def test_small_sabr_monte_carlo_brackets_the_formula_near_the_money():
    from build_stochastic_volatility_reference import hull_sabr_vol, sabr_monte_carlo

    sigma0 = 0.2 * 0.03**0.5
    result = sabr_monte_carlo(0.03, 1.0, sigma0, 0.5, 0.0, 0.4, [0.03], 100, 40_000, 7)
    row = result["rows"][0]
    formula = hull_sabr_vol(0.03, 0.03, 1.0, sigma0, 0.5, 0.0, 0.4)
    assert abs(row["implied_vol"] - formula) < 4 * row["implied_vol_standard_error"] + 1e-3
    assert math.isclose(result["mean_terminal_forward"], 0.03, abs_tol=2e-4)
