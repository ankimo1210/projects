"""Hull Ex24.7 default-time bands, one-factor dependence and indicator correlation."""

import math

import numpy as np
import pytest
from hullkit import _credit_risk as c
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


def test_source_all_seven_thresholds_by_integrating_and_inverting_normal_density():
    for probability, printed, tolerance in [
        (0.05, -1.645, 0.0005),
        (0.1, -1.282, 0.0005),
        (0.01, -2.33, 0.005),
        (0.03, -1.88, 0.005),
        (0.06, -1.55, 0.005),
        (0.10, -1.28, 0.005),
        (0.15, -1.04, 0.005),
    ]:
        threshold = c.default_thresholds([probability])[0]
        reference = brentq(
            lambda x, probability=probability: quad(lambda z: norm.pdf(z), -12, x)[0] - probability,
            -8,
            8,
        )
        assert threshold == pytest.approx(reference, abs=1e-10)
        assert threshold == pytest.approx(printed, abs=tolerance)


def test_source_default_year_bins_and_censored_survival():
    probabilities = [0.01, 0.03, 0.06, 0.10, 0.15]
    normals = norm.ppf([0.005, 0.02, 0.04, 0.08, 0.12, 0.2, 0.9])
    assert c.default_years(normals, probabilities) == pytest.approx([1, 2, 3, 4, 5, 0, 0])
    # 0 is survival past year5, not an assertion of never defaulting.
    assert norm.cdf(c.default_thresholds(probabilities)) == pytest.approx(probabilities)


def test_source_ten_obligors_correlated_latents_marginals_and_joint_six_se():
    normals = c.one_factor_latents(np.full(10, np.sqrt(0.2)), samples=100000, seed=2470)
    assert np.corrcoef(normals, rowvar=False)[0, 1] == pytest.approx(0.2, abs=0.02)
    years = c.default_years(normals, [0.01, 0.03, 0.06, 0.10, 0.15])
    for year, pd in enumerate([0.01, 0.03, 0.06, 0.10, 0.15], start=1):
        occurred = (years[:, 0] > 0) & (years[:, 0] <= year)
        assert occurred.mean() == pytest.approx(pd, abs=6 * np.sqrt(pd * (1 - pd) / len(normals)))
    joint = c.joint_default_probability(0.15, 0.15, np.sqrt(0.2), np.sqrt(0.2))
    observed = np.mean((normals[:, 0] < norm.ppf(0.15)) & (normals[:, 1] < norm.ppf(0.15)))
    assert observed == pytest.approx(joint, abs=6 * np.sqrt(joint * (1 - joint) / len(normals)))
    rho = 0.2
    # Independent integration conditional on the first latent, rather than common F.
    independent = quad(
        lambda x: norm.pdf(x) * norm.cdf((norm.ppf(0.15) - rho * x) / np.sqrt(1 - rho * rho)),
        -12,
        norm.ppf(0.15),
        epsabs=1e-11,
    )[0]
    assert joint == pytest.approx(independent, abs=1e-10)
    indicator_rho = c.default_indicator_correlation(0.15, 0.15, joint)
    assert 0 < indicator_rho < rho


def test_signed_loadings_and_factor_integral_restores_marginal_pd():
    factor = np.array([-1, 0, 2])
    idiosyncratic = np.array([[1, 2], [3, 4], [5, 6]])
    assert c.one_factor_latents(
        [0.5, -0.3], factor=factor, idiosyncratic=idiosyncratic
    ) == pytest.approx(
        factor[:, None] * [0.5, -0.3] + idiosyncratic * np.sqrt(1 - np.array([0.5, -0.3]) ** 2)
    )
    probability = quad(
        lambda f: float(c.conditional_event_weights([0.06], [f], -0.3)[0, 0]) * norm.pdf(f), -12, 12
    )[0]
    assert probability == pytest.approx(0.06, abs=1e-10)
    with pytest.raises(ValueError):
        c.default_thresholds([0.1, 0.05])
