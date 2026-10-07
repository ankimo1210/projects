"""Hull §24.9: Vasicek amount/capital, source thresholds and bond migration marks."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _credit_risk as c
from hullkit.credit_metrics import HULL_TABLE_24_4, TransitionMatrix, rating_thresholds
from scipy.stats import norm


def test_source_example_24_8_total_loss_vs_expected_loss_capital():
    result = c.large_pool_risk(0.02, 0.1, 0.999, 100e6, 0.6)
    assert result["worst_default_fraction"] == pytest.approx(0.128, abs=0.0005)
    assert result["var"] == pytest.approx(5.13e6, abs=5000)
    assert result["expected_loss"] == pytest.approx(0.8e6)
    assert result["capital"] == pytest.approx(result["var"] - 0.8e6)


def test_source_table_24_4_all_seven_printed_boundaries():
    matrix = TransitionMatrix.from_percent(HULL_TABLE_24_4)
    assert rating_thresholds(matrix, "AAA")[:3] == pytest.approx(
        [1.2719, 2.4089, 2.8070], abs=0.00005
    )
    bbb = rating_thresholds(matrix, "BBB")
    assert bbb[:3] == pytest.approx([-3.7190, -3.0618, -1.7866], abs=0.00005)
    assert bbb[-1] == pytest.approx(2.9290, abs=0.00005)
    assert norm.sf(bbb[-1]) == pytest.approx(0.0017)
    assert bbb[1] < bbb[2]  # printed BBB->A interval has endpoints reversed


def test_large_pool_quantile_and_finite_pool_against_factor_distribution_six_se():
    q, rho, confidence = 0.02, 0.1, 0.99
    result = c.large_pool_risk(q, rho, confidence, 1, 0.6)
    rng = np.random.default_rng(249)
    factor = rng.normal(size=180000)
    conditional = norm.cdf((norm.ppf(q) - np.sqrt(rho) * factor) / np.sqrt(1 - rho))
    loss = 0.4 * conditional
    reference = result["var"]
    z = norm.ppf(reference / 0.4)
    f = (norm.ppf(q) - np.sqrt(1 - rho) * z) / np.sqrt(rho)
    density = np.sqrt((1 - rho) / rho) * norm.pdf(f) / (0.4 * norm.pdf(z))
    se = np.sqrt(confidence * (1 - confidence) / len(factor)) / density
    assert np.quantile(loss, confidence) == pytest.approx(reference, abs=6 * se)
    finite = 0.4 * rng.binomial(5000, conditional) / 5000
    assert np.quantile(finite, confidence) == pytest.approx(reference, abs=6 * se + 0.4 / 5000)


def test_migration_bond_repricing_default_and_upgrade_loss_sign():
    values = c.rating_bond_values(100, 0.05, 3, 0.03, [0.001, 0.003, 0.007], 0.4)
    cash = [5, 5, 105]
    for i, spread in enumerate([0.001, 0.003, 0.007]):
        reference = sum(
            amount * math.exp(-(0.03 + spread) * year) for year, amount in enumerate(cash, start=1)
        )
        assert values[i] == pytest.approx(reference)
    assert values[-1] == 40
    migrations = np.array([[0], [1], [2], [3]])
    loss = c.migration_losses(migrations, [values[1]], values[None, :])
    assert loss[0] < 0
    assert loss[1] == pytest.approx(0)
    assert loss[2] > 0
    assert loss[3] == pytest.approx(values[1] - 40)  # default accounted exactly once


def test_two_independent_obligors_against_exact_state_enumeration():
    probabilities = np.array([[0.6, 0.3, 0.1], [0.1, 0.7, 0.2], [0, 0, 1]])
    matrix = TransitionMatrix(probabilities, ratings=("A", "B", "Default"))
    state_values = np.array([[105, 98, 40], [210, 196, 80]])
    start = np.array([98, 210])
    result = c.rating_loss_distribution(
        matrix, ["B", "A"], start, state_values, rho=0, samples=100000, seed=2491
    )
    expected = 0
    for first, second in product(range(3), repeat=2):
        probability = probabilities[1, first] * probabilities[0, second]
        loss = (start[0] - state_values[0, first]) + (start[1] - state_values[1, second])
        expected += probability * loss
    se = np.std(result["losses"], ddof=1) / np.sqrt(len(result["losses"]))
    assert result["expected_loss"] == pytest.approx(expected, abs=6 * se)
    assert np.any(result["losses"] < 0)
