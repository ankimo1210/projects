"""Hull Example24.3: existing Merton calibration vs integrated terminal payoffs."""

import math

import numpy as np
import pytest
from hullkit import _credit_risk as c
from scipy.integrate import quad
from scipy.optimize import root
from scipy.stats import norm


def test_source_example_24_3_all_seven_values():
    result = c.merton_values(3, 0.8, 10, 0.05, 1)
    assert result["asset_value"] == pytest.approx(12.40, abs=0.005)
    assert result["asset_vol"] == pytest.approx(0.2123, abs=0.00005)
    assert result["d2"] == pytest.approx(1.1408, abs=0.00005)
    assert result["pricing_pd"] * 100 == pytest.approx(12.7, abs=0.05)
    assert result["debt_value"] == pytest.approx(9.40, abs=0.005)
    assert result["risk_free_debt"] == pytest.approx(9.51, abs=0.005)
    assert result["expected_loss_rate"] * 100 == pytest.approx(1.2, abs=0.05)


@pytest.mark.parametrize("maturity", [1, 2.5])
def test_equity_payoff_and_ito_delta_by_independent_quadrature_root(maturity):
    equity, eqvol, debt, rate = 3, 0.8, 10, 0.05

    def equations(log_parameters):
        asset, vol = np.exp(log_parameters)
        threshold = (math.log(debt / asset) - (rate - 0.5 * vol * vol) * maturity) / (
            vol * math.sqrt(maturity)
        )

        def terminal(z):
            return asset * math.exp(
                (rate - 0.5 * vol * vol) * maturity + vol * math.sqrt(maturity) * z
            )

        integrated = (
            math.exp(-rate * maturity)
            * quad(lambda z: (terminal(z) - debt) * norm.pdf(z), threshold, 12, epsabs=1e-10)[0]
        )
        delta = (
            math.exp(-rate * maturity)
            * quad(lambda z: terminal(z) / asset * norm.pdf(z), threshold, 12, epsabs=1e-11)[0]
        )
        return [integrated - equity, delta * vol * asset - eqvol * equity]

    independent = root(equations, np.log([13, 0.2]))
    assert independent.success
    result = c.merton_values(equity, eqvol, debt, rate, maturity)
    assert [result["asset_value"], result["asset_vol"]] == pytest.approx(
        np.exp(independent.x), rel=1e-8
    )
    asset, vol = np.exp(independent.x)
    cutoff = (math.log(debt / asset) - (rate - 0.5 * vol * vol) * maturity) / (
        vol * math.sqrt(maturity)
    )
    bond = math.exp(-rate * maturity) * (
        quad(
            lambda z: (
                asset
                * math.exp((rate - 0.5 * vol * vol) * maturity + vol * math.sqrt(maturity) * z)
                * norm.pdf(z)
            ),
            -12,
            cutoff,
        )[0]
        + debt * norm.sf(cutoff)
    )
    assert result["debt_value"] == pytest.approx(bond, rel=1e-8)


def test_terminal_default_mc_and_physical_drift_is_not_edf_calibration():
    result = c.merton_values(3, 0.8, 10, 0.05, 1, physical_drift=0.10)
    asset, vol = result["asset_value"], result["asset_vol"]
    z = np.random.default_rng(246).normal(size=150000)
    terminal = asset * np.exp(0.05 - 0.5 * vol * vol + vol * z)
    probability = result["pricing_pd"]
    assert np.mean(terminal < 10) == pytest.approx(
        probability, abs=6 * np.sqrt(probability * (1 - probability) / len(z))
    )
    assert result["physical_pd"] < probability
    assert result["edf"] is None
