"""Fixed-driver monthly Heston/local-volatility path contracts for RB-F04."""

import importlib.util
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def parameters(**overrides):
    values = dict(
        spot=100.0,
        rate=0.03,
        dividend_yield=0.0,
        v0=0.04,
        kappa=2.0,
        theta=0.04,
        xi=0.3,
        rho=-0.7,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class ConstantVariance:
    """Analytical constant local variance with the declared initial state."""

    def __init__(self, variance):
        self.variance = variance

    def evaluate(self, t, spots):
        status = "initial_state" if t == 0.0 else "interior"
        return {
            "variance": np.full_like(spots, self.variance, dtype=float),
            "status": np.full(spots.shape, status),
        }


@pytest.fixture
def dynamics():
    return import_module("hullkit._model_dynamics")


def test_normal_aggregation_preserves_fine_brownian_increments(dynamics):
    fine = np.array([[[1.0, 2.0], [3.0, 4.0], [-1.0, 0.0], [1.0, 2.0]]])
    coarse = dynamics.aggregate_normals(fine, 2)
    np.testing.assert_allclose(
        coarse, [[[2.82842712474619, 4.242640687119285], [0.0, 1.4142135623730951]]]
    )
    np.testing.assert_allclose(coarse * np.sqrt(0.5), [[[2.0, 3.0], [0.0, 1.0]]])
    np.testing.assert_array_equal(fine[0, 0], [1.0, 2.0])


def test_gbm_limit_matches_constant_local_variance_at_only_monthly_dates(dynamics):
    params = parameters(xi=0.0, dividend_yield=0.01)
    normals = np.random.default_rng(209).standard_normal((8, 48, 2))
    heston = dynamics.heston_monthly(params, normals)
    local = dynamics.local_monthly(params, ConstantVariance(0.04), normals)
    times = np.arange(13) / 12.0
    brownian = np.cumsum(normals[:, :, 0], axis=1)[:, 3::4] / np.sqrt(48.0)
    expected = 100.0 * np.exp(0.2 * brownian)
    assert heston["observations"].shape == (8, 13)
    np.testing.assert_array_equal(heston["observations"][:, 0], np.full(8, 100.0))
    np.testing.assert_allclose(heston["observations"][:, 1:], expected, rtol=2e-14)
    np.testing.assert_allclose(local["observations"], heston["observations"], rtol=2e-14)
    np.testing.assert_array_equal(heston["observation_times"], times)
    np.testing.assert_array_equal(local["observation_times"], times)
    assert not np.any(heston["failures"])
    assert not np.any(local["failures"])


def test_expiry_rescales_monthly_clock_and_stock_drift(dynamics):
    params = parameters(xi=0.0, rate=-0.01, dividend_yield=0.02)
    result = dynamics.heston_monthly(params, np.zeros((1, 24, 2)), expiry=2.0)
    times = np.arange(13) / 6.0
    np.testing.assert_allclose(result["observations"][0], 100.0 * np.exp(-0.05 * times))
    np.testing.assert_array_equal(result["observation_times"], times)


@pytest.mark.parametrize(
    ("first_shock", "expected_variance"),
    [(0.0, 0.06771281292110204), (1.0, 0.0781051177665153)],
)
def test_variance_uses_correlated_second_brownian_shock(dynamics, first_shock, expected_variance):
    normals = np.zeros((1, 12, 2))
    normals[0, 0] = [first_shock, 2.0]
    result = dynamics.heston_monthly(parameters(rho=0.6), normals)
    assert result["variance_observations"][0, 1] == pytest.approx(expected_variance)
    assert result["observations"][0, 1] == pytest.approx(
        100.0 * np.exp(0.01 / 12.0 + 0.2 * first_shock / np.sqrt(12.0))
    )


def test_deterministic_variance_converges_to_analytic_mean_reversion(dynamics):
    params = parameters(xi=0.0, theta=0.09, kappa=1.3)
    exact_variance = 0.09 - 0.05 * np.exp(-1.3)
    integrated_variance = 0.09 - 0.05 * (1.0 - np.exp(-1.3)) / 1.3
    exact_stock = 100.0 * np.exp(0.03 - 0.5 * integrated_variance)
    coarse = dynamics.heston_monthly(params, np.zeros((1, 24, 2)))
    fine = dynamics.heston_monthly(params, np.zeros((1, 384, 2)))
    assert (
        abs(fine["variance_observations"][0, -1] - exact_variance)
        < abs(coarse["variance_observations"][0, -1] - exact_variance) / 12.0
    )
    assert (
        abs(fine["observations"][0, -1] - exact_stock)
        < abs(coarse["observations"][0, -1] - exact_stock) / 12.0
    )


@pytest.mark.parametrize("xi", [0.0, 0.3])
def test_dividend_discounted_terminal_stock_is_a_martingale_within_sampling_error(dynamics, xi):
    params = parameters(xi=xi, dividend_yield=0.07)
    normals = np.random.default_rng(111).standard_normal((30000, 48, 2))
    result = dynamics.heston_monthly(params, normals)
    stock = result["observations"][:, -1] * np.exp(-params.rate + params.dividend_yield)
    standard_error = stock.std(ddof=1) / np.sqrt(stock.size)
    assert abs(stock.mean() - params.spot) < 4.5 * standard_error
    assert not np.any(result["failures"])


def test_full_truncation_keeps_negative_variance_state_and_counts_it(dynamics):
    normals = np.zeros((1, 12, 2))
    normals[:, :, 1] = -10.0
    params = parameters(kappa=0.5, xi=1.0, rho=0.0)
    result = dynamics.heston_monthly(params, normals)
    first_variance = 0.04 - 2.0 / np.sqrt(12.0)
    assert result["variance_observations"][0, 1] == pytest.approx(first_variance)
    assert result["variance_observations"][0, -1] == pytest.approx(first_variance + 11.0 / 600.0)
    assert result["negative_variance_counts"][0] == 12
    assert result["observations"][0, -1] == pytest.approx(100.0 * np.exp(0.03 - 0.02 / 12.0))
    assert not result["failures"][0]


@pytest.mark.parametrize("unsupported_variance", [0.04, np.nan])
def test_local_surface_labels_are_preserved_and_unsupported_paths_stay_visible(
    dynamics, unsupported_variance
):
    class DiagnosedVariance(ConstantVariance):
        def evaluate(self, t, spots):
            result = super().evaluate(t, spots)
            if t > 0.0:
                label = "early_time_wing_left" if t < 0.25 else "wing_right"
                result["status"] = np.where(spots > 110.0, "unsupported_wing", label)
                result["variance"][spots > 110.0] = unsupported_variance
            return result

    normals = np.zeros((2, 12, 2))
    normals[1, 0, 0] = 3.0
    result = dynamics.local_monthly(parameters(), DiagnosedVariance(0.04), normals)
    assert result["failures"].tolist() == [False, True]
    assert np.isfinite(result["observations"][0]).all()
    assert np.isfinite(result["observations"][1, :2]).all()
    assert np.isnan(result["observations"][1, 2:]).all()
    assert "unsupported_wing" in result["failure_reasons"][1]
    if np.isnan(unsupported_variance):
        assert "nonfinite_variance" in result["failure_reasons"][1]
    np.testing.assert_array_equal(result["status_counts"]["initial_state"], [1, 1])
    np.testing.assert_array_equal(result["status_counts"]["early_time_wing_left"], [2, 0])
    np.testing.assert_array_equal(result["status_counts"]["wing_right"], [9, 0])
    np.testing.assert_array_equal(result["status_counts"]["unsupported_wing"], [0, 1])


def test_local_stock_consumes_only_the_first_normal_factor(dynamics):
    normals = np.zeros((1, 12, 2))
    normals[:, :, 1] = np.nan
    result = dynamics.local_monthly(parameters(), ConstantVariance(0.04), normals)
    assert not result["failures"][0]
    np.testing.assert_allclose(
        result["observations"][0], 100.0 * np.exp(0.01 * np.arange(13) / 12.0)
    )


@pytest.mark.parametrize("model", ["heston_monthly", "local_monthly"])
def test_nonfinite_driver_is_reported_per_path_without_dropping_rows(dynamics, model):
    normals = np.zeros((2, 12, 2))
    normals[1, 0, 0] = np.nan
    args = (
        (parameters(), normals)
        if model == "heston_monthly"
        else (parameters(), ConstantVariance(0.04), normals)
    )
    result = getattr(dynamics, model)(*args)
    assert result["observations"].shape == (2, 13)
    assert result["failures"].tolist() == [False, True]
    assert np.isnan(result["observations"][1, 1:]).all()
    assert "nonfinite_driver" in result["failure_reasons"][1]
    assert result["failure_reasons"][0] == ""


def test_nonfinite_stock_is_a_failed_path_instead_of_an_infinite_observation(dynamics):
    normals = np.zeros((2, 12, 2))
    normals[1, 0, 0] = 1e6
    result = dynamics.heston_monthly(parameters(xi=0.0), normals)
    assert result["failures"].tolist() == [False, True]
    assert np.isnan(result["observations"][1, 1:]).all()
    assert "nonfinite_stock" in result["failure_reasons"][1]


@pytest.mark.parametrize("variance", [-0.01, np.inf])
def test_invalid_local_variance_is_not_clipped_to_create_a_valid_path(dynamics, variance):
    result = dynamics.local_monthly(parameters(), ConstantVariance(variance), np.zeros((1, 12, 2)))
    assert result["failures"][0]
    assert np.isnan(result["observations"][0, 1:]).all()
    assert "variance" in result["failure_reasons"][0]


@pytest.mark.parametrize(
    "normals", [np.zeros((2, 13, 2)), np.zeros((2, 0, 2)), np.zeros((2, 12, 1))]
)
def test_invalid_monthly_driver_shape_is_rejected(dynamics, normals):
    with pytest.raises(ValueError):
        dynamics.heston_monthly(parameters(), normals)


@pytest.mark.parametrize("factor", [0, -1, 3, 1.5])
def test_invalid_brownian_aggregation_is_rejected(dynamics, factor):
    with pytest.raises(ValueError):
        dynamics.aggregate_normals(np.zeros((2, 4, 2)), factor)


@pytest.mark.parametrize("overrides", [{"spot": 0.0}, {"v0": -0.1}, {"xi": -0.1}, {"rho": 1.01}])
def test_mathematically_invalid_parameters_are_rejected(dynamics, overrides):
    with pytest.raises(ValueError):
        dynamics.heston_monthly(parameters(**overrides), np.zeros((1, 12, 2)))


@pytest.mark.parametrize("expiry", [0.0, -1.0, np.nan])
def test_invalid_expiry_is_rejected(dynamics, expiry):
    with pytest.raises(ValueError):
        dynamics.heston_monthly(parameters(), np.zeros((1, 12, 2)), expiry=expiry)


def _research_pilot():
    path = Path(__file__).resolve().parents[2] / "research" / "RB-F04" / "pilot.py"
    spec = importlib.util.spec_from_file_location("rb_f04_real_grid_integration", path)
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    return pilot


def _pilot_protocol():
    return {
        "contract": {"expiry": 1.0, "asian_strike": 100.0},
        "parameters": {"rate": 0.03},
        "quotes": {"times": [0.25, 0.5, 1.0], "strikes": [90.0, 100.0, 110.0]},
        "two_date": {
            "first": 0.5,
            "second": 1.0,
            "bins": [90.0, 100.0, 110.0],
            "conditional_threshold": 110.0,
            "minimum_count": 2,
        },
    }


def test_real_grid_stream_preserves_brownian_months_and_all_surface_visits():
    pilot = _research_pilot()
    surface = pilot.module("surface")
    params = surface.HestonParameters(**vars(parameters(xi=0.0, dividend_yield=0.01)))
    grid = surface.LocalVarianceGrid(
        np.array([0.1, 1.0]), np.array([-0.25, 0.25]), np.full((2, 2), 0.04), params
    )
    result = pilot.simulate(params, grid, paths=19, seed=17, steps=[12, 24, 48], block_size=7)
    arrays = result["arrays"]
    rng = np.random.default_rng(17)
    expected_blocks = []
    for count in [7, 7, 5]:
        fine = rng.standard_normal((count, 48, 2))
        monthly_brownian = fine[:, :, 0].reshape(count, 12, 4).sum(axis=2) / np.sqrt(48.0)
        monthly_stock = 100.0 * np.exp(0.2 * monthly_brownian.cumsum(axis=1))
        expected_blocks.append(np.column_stack([np.full(count, 100.0), monthly_stock]))
    expected = np.concatenate(expected_blocks)
    for level, early_visits in [(12, 1), (24, 2), (48, 4)]:
        for model in ["heston", "local"]:
            np.testing.assert_allclose(
                arrays[f"{level}.{model}.observations"], expected, rtol=2e-14
            )
            assert not arrays[f"{level}.{model}.failures"].any()
        prefix = f"{level}.local.status."
        counts = {
            key.removeprefix(prefix): value
            for key, value in arrays.items()
            if key.startswith(prefix)
        }
        np.testing.assert_array_equal(sum(counts.values()), np.full(19, level))
        np.testing.assert_array_equal(counts["initial_state"], np.ones(19, dtype=int))
        np.testing.assert_array_equal(
            sum(value for label, value in counts.items() if label.startswith("early_time")),
            np.full(19, early_visits),
        )
        assert sum(value.sum() for label, value in counts.items() if "wing" in label) > 0
    metrics = pilot.path_metrics(arrays, _pilot_protocol(), steps=[12, 24, 48])
    for row in metrics["levels"]:
        assert row["asian"]["difference"]["supported"]
        assert row["asian"]["difference"]["samples"] == 19
        assert row["asian"]["difference"]["mean"] == pytest.approx(0.0, abs=2e-13)
        assert sum(row["diagnostics"]["local"]["surface_visits"].values()) == 19 * row["steps"]
        assert row["two_date"]["joint_counts_heston"].sum() == 19
        assert row["two_date"]["joint_counts_local"].sum() == 19


def test_real_grid_stream_retains_every_unsupported_path_and_invalidates_asian_summary():
    pilot = _research_pilot()
    surface = pilot.module("surface")
    params = surface.HestonParameters(**vars(parameters(xi=0.0)))
    grid = surface.LocalVarianceGrid(
        np.array([0.1, 0.5]), np.array([-1.0, 1.0]), np.full((2, 2), 0.04), params
    )
    result = pilot.simulate(params, grid, paths=9, seed=18, steps=[12, 24], block_size=4)
    arrays = result["arrays"]
    for level in [12, 24]:
        assert arrays[f"{level}.local.observations"].shape == (9, 13)
        np.testing.assert_array_equal(
            arrays[f"{level}.local.observations"][:, 0], np.full(9, 100.0)
        )
        assert np.isnan(arrays[f"{level}.local.observations"][:, -1]).all()
        assert arrays[f"{level}.local.failures"].all()
        assert np.isfinite(arrays[f"{level}.heston.observations"]).all()
        assert not arrays[f"{level}.heston.failures"].any()
        assert all(
            "unsupported_time" in reason for reason in arrays[f"{level}.local.failure_reasons"]
        )
        assert all(
            "nonfinite_variance" in reason for reason in arrays[f"{level}.local.failure_reasons"]
        )
        np.testing.assert_array_equal(
            arrays[f"{level}.local.status.unsupported_time"], np.ones(9, dtype=int)
        )
        prefix = f"{level}.local.status."
        queries = sum(value for key, value in arrays.items() if key.startswith(prefix))
        np.testing.assert_array_equal(queries, np.full(9, level // 2 + 2))
    metrics = pilot.path_metrics(arrays, _pilot_protocol(), steps=[12, 24])
    for row in metrics["levels"]:
        assert row["asian"]["local"]["samples"] == 9
        assert not row["asian"]["local"]["supported"]
        assert not row["asian"]["difference"]["supported"]
        assert row["asian"]["heston"]["supported"]
        assert row["diagnostics"]["local"]["failed_paths"] == 9
        assert row["two_date"]["failed_pairs"] == 9
