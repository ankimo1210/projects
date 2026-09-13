"""Tests for hullkit.credit_metrics: Hull Table 24.4 thresholds and correlated migrations."""

import numpy as np
import pytest
from hullkit import credit_metrics as cm


def test_hull_table_rows_sum_to_100_within_rounding():
    sums = cm.HULL_TABLE_24_4.sum(axis=1)
    np.testing.assert_allclose(sums, 100.0, atol=0.05)
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    assert matrix.probabilities.shape == (8, 8)
    assert matrix.probabilities[-1, -1] == 1.0  # default is absorbing


def test_thresholds_match_hull_page_582():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    aaa = cm.rating_thresholds(matrix, "AAA")
    np.testing.assert_allclose(aaa[:3], [1.2719, 2.4089, 2.8070], atol=2e-4)
    bbb = cm.rating_thresholds(matrix, "BBB")
    np.testing.assert_allclose(bbb[:3], [-3.7190, -3.0618, -1.7866], atol=2e-4)
    assert bbb[-1] == pytest.approx(2.9290, abs=2e-4)  # default when x > 2.9290


def test_migrate_uses_thresholds_in_column_order():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    x = np.array([1.0, 1.5, 2.5, 2.85, 9.0])
    # Hull: "The AAA never defaults during the year" (p_default = 0.00 ⇒ boundary +inf)
    np.testing.assert_array_equal(cm.migrate(matrix, "AAA", x), [0, 1, 2, 3, 6])
    x = np.array([-4.0, -3.5, -2.0, 0.0, 3.0])
    np.testing.assert_array_equal(cm.migrate(matrix, "BBB", x), [0, 1, 2, 3, 7])


def test_multi_period_matrix_is_a_matrix_power():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    two_year = matrix.multi_period(2)
    np.testing.assert_allclose(
        two_year.probabilities, matrix.probabilities @ matrix.probabilities, atol=1e-15
    )
    assert two_year.default_probability("CCC/C") > matrix.default_probability("CCC/C")


def test_simulation_default_frequency_matches_row_and_correlation_fattens_tail():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    initial = ["BBB"] * 200
    exposures = np.full(200, 1.0)
    independent = cm.simulate_rating_migrations(
        matrix, initial, rho=0.0, n_sims=20_000, rng=np.random.default_rng(1)
    )
    correlated = cm.simulate_rating_migrations(
        matrix, initial, rho=0.2, n_sims=20_000, rng=np.random.default_rng(1)
    )
    default_index = matrix.index("Default")
    freq = (independent == default_index).mean()
    p = matrix.default_probability("BBB")
    assert abs(freq - p) < 4 * np.sqrt(p * (1 - p) / (200 * 20_000))
    loss_ind = cm.credit_loss_distribution(independent, exposures, recovery=0.4)
    loss_cor = cm.credit_loss_distribution(correlated, exposures, recovery=0.4)
    assert cm.expected_loss(loss_ind) == pytest.approx(cm.expected_loss(loss_cor), rel=0.1)
    assert cm.credit_var(loss_cor, 0.999) > cm.credit_var(loss_ind, 0.999)


def test_rating_values_add_downgrade_losses():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    new_ratings = np.array([[3, 4, 7]])  # BBB stays, BBB→BB, BBB→Default
    exposures = np.array([100.0, 100.0, 100.0])
    values = {"AAA": 1.02, "AA": 1.01, "A": 1.005, "BBB": 1.0, "BB": 0.97, "B": 0.93, "CCC/C": 0.85}
    losses = cm.credit_loss_distribution(
        new_ratings, exposures, recovery=0.4, rating_values=values, initial_ratings=["BBB"] * 3
    )
    assert losses[0] == pytest.approx(0.0 + 3.0 + 60.0, abs=1e-12)
    without = cm.credit_loss_distribution(new_ratings, exposures, recovery=0.4)
    assert without[0] == pytest.approx(60.0, abs=1e-12)
    assert matrix.index("BB") == 4


def test_validation_errors():
    bad = cm.HULL_TABLE_24_4.copy()
    bad[0, 0] += 1.0
    with pytest.raises(ValueError):
        cm.TransitionMatrix.from_percent(bad)
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    with pytest.raises(ValueError):
        cm.rating_thresholds(matrix, "Default")
    with pytest.raises(ValueError):
        cm.simulate_rating_migrations(matrix, ["AAA"], rho=1.0, n_sims=10)
    with pytest.raises(ValueError):
        cm.credit_var(np.array([1.0, 2.0]), confidence=1.0)
