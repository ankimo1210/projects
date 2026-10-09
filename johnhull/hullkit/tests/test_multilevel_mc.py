"""Independent Euler coupling and statistical units for RB-F08."""

import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


def test_pair_uses_sum_of_fine_brownian_and_euler_not_exact():
    from hullkit import _multilevel_mc as m

    c = m.GBMCall(100, 100, 0.03, 0.2, 1, 0.01)
    z = np.array([[0.3, -0.2], [-3.0, 1.0], [0.4, 0.1]])
    result = m.gbm_level_samples(c, z, level=1, base_steps=1)
    zc = z.sum(axis=1) / np.sqrt(2)
    fine = 100 * np.prod(1 + 0.02 / 2 + 0.2 * np.sqrt(0.5) * z, axis=1)
    coarse = 100 * (1 + 0.02 + 0.2 * zc)
    expected = np.exp(-0.03) * (np.maximum(fine - 100, 0) - np.maximum(coarse - 100, 0))
    np.testing.assert_allclose(result["differences"], expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(m.coarse_normals(z), zc[:, None], rtol=0, atol=1e-12)
    np.testing.assert_array_equal(z, [[0.3, -0.2], [-3.0, 1.0], [0.4, 0.1]])


def test_negative_euler_path_retained_in_original_denominator():
    from hullkit import _multilevel_mc as m

    c = m.GBMCall(100, 100, 0, 1, 1)
    result = m.gbm_level_samples(c, np.array([[-4.0], [0.0], [2.0]]), level=0, base_steps=1)
    np.testing.assert_allclose(result["differences"], [0, 0, 200], rtol=0, atol=1e-12)
    assert result["negative_paths"] == 1
    assert m.block_moments(result["differences"])["count"] == 3


def test_mlmc_variance_uses_independent_level_sample_counts():
    from hullkit import _multilevel_mc as m

    levels = [
        m.block_moments(np.array([1.0, 2.0, 3.0, 4.0])),
        m.block_moments(np.array([-0.1, 0.1, -0.2, 0.2])),
    ]
    out = m.mlmc_summary(levels)
    expected = (5 / 3) / 4 + (0.1 / 3) / 4
    assert out["price"] == pytest.approx(2.5)
    assert out["variance"] == pytest.approx(expected)
    assert out["level_counts"] == [4, 4]


def test_merge_uses_centered_moments_at_large_offsets():
    from hullkit import _multilevel_mc as m

    blocks = [
        m.block_moments(1e12 + np.array([0.0, 1.0, 2.0])),
        m.block_moments(1e12 + np.array([3.0, 4.0, 5.0])),
    ]
    result = m.merge_moments(blocks)
    assert result["count"] == 6
    assert result["mean"] == pytest.approx(1e12 + 2.5, rel=0, abs=1e-5)
    assert result["m2"] == pytest.approx(17.5, rel=0, abs=1e-12)
    assert blocks[0]["count"] == 3
    assert blocks[0]["m2"] == pytest.approx(2.0)


def test_singleton_blocks_merge_without_a_sample_variance():
    from hullkit import _multilevel_mc as m

    result = m.merge_moments([m.block_moments(np.array([1.0])), m.block_moments(np.array([5.0]))])
    assert result["count"] == 2
    assert result["mean"] == pytest.approx(3.0)
    assert result["m2"] == pytest.approx(8.0)


def test_large_constant_block_avoids_overflow_from_raw_sample_sum():
    from hullkit import _multilevel_mc as m

    result = m.block_moments(np.array([1e308, 1e308]))
    assert result["count"] == 2
    assert result["mean"] == pytest.approx(1e308)
    assert result["m2"] == pytest.approx(0.0)


def test_singleton_record_cannot_have_nonzero_centered_sum_of_squares():
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.merge_moments([{"count": 1, "mean": 2.0, "m2": 1.0}])


def test_nonfinite_sum_of_level_means_fails_summary():
    from hullkit import _multilevel_mc as m

    levels = [{"count": 2, "mean": 1e308, "m2": 0.0}] * 2
    with pytest.raises(ValueError, match="nonfinite"):
        m.mlmc_summary(levels)


def test_allocation_solves_hand_checked_variance_budget():
    from hullkit import _multilevel_mc as m

    result = m.allocate_paths(
        np.array([4.0, 1.0]),
        np.array([1.0, 4.0]),
        sampling_variance=0.5,
        minimum=2,
        variance_floor=0,
    )
    np.testing.assert_array_equal(result, [16, 4])
    assert np.issubdtype(result.dtype, np.integer)
    assert np.sum(np.array([4.0, 1.0]) / result) == pytest.approx(0.5)


def test_allocation_ceil_and_minimum_preserve_variance_budget():
    from hullkit import _multilevel_mc as m

    result = m.allocate_paths(
        np.array([4.0, 1.0]),
        np.array([1.0, 4.0]),
        sampling_variance=0.45,
        minimum=5,
        variance_floor=0,
    )
    np.testing.assert_array_equal(result, [18, 5])
    assert np.sum(np.array([4.0, 1.0]) / result) <= 0.45


def test_allocation_keeps_zero_variance_levels_and_applies_floor():
    from hullkit import _multilevel_mc as m

    result = m.allocate_paths(np.zeros(2), np.ones(2), sampling_variance=1, minimum=32)
    np.testing.assert_array_equal(result, [32, 32])
    floored = m.allocate_paths(
        np.array([0.0, 1.0]), np.ones(2), sampling_variance=0.5, minimum=2, variance_floor=4
    )
    np.testing.assert_array_equal(floored, [16, 16])


def test_level_zero_payoff_and_exact_bias_use_separate_estimators():
    from hullkit import _multilevel_mc as m

    c = m.GBMCall(100, 80, 0.03, 0.2, 1, 0.02)
    z = np.array([[0.3], [-0.4], [1.2]])
    result = m.gbm_level_samples(c, z, level=0, base_steps=1)
    euler = 100 * (1 + 0.01 + 0.2 * z[:, 0])
    exact = 100 * np.exp(-0.01 + 0.2 * z[:, 0])
    euler_payoffs = np.exp(-0.03) * np.maximum(euler - 80, 0)
    exact_payoffs = np.exp(-0.03) * np.maximum(exact - 80, 0)
    np.testing.assert_allclose(result["fine_payoffs"], euler_payoffs, atol=1e-12)
    np.testing.assert_allclose(result["differences"], euler_payoffs, atol=1e-12)
    np.testing.assert_allclose(
        result["paired_exact_bias"], euler_payoffs - exact_payoffs, atol=1e-12
    )
    assert result["coarse_payoffs"] is None
    assert result["fine_negative_states"] == result["coarse_negative_states"] == 0
    assert result["cost_counts"] == {
        "stock_updates": 3,
        "normal_draws": 3,
        "payoff_evaluations": 3,
        "coarse_aggregations": 0,
    }
    assert result["diagnostic_cost_counts"] == {
        "stock_updates": 3,
        "normal_draws": 0,
        "payoff_evaluations": 3,
        "normal_sums": 3,
    }


def test_fine_and_coarse_negative_states_count_updates_and_union_of_paths():
    from hullkit import _multilevel_mc as m

    c = m.GBMCall(100, 100, 0, 1, 1)
    result = m.gbm_level_samples(
        c, np.array([[-4.0, 0.0], [-3.0, -3.0], [0.0, 0.0]]), level=1, base_steps=1
    )
    # Row 0 stays negative after both fine updates; row 1 becomes positive again.
    assert result["fine_negative_states"] == 3
    assert result["coarse_negative_states"] == 2
    assert result["negative_paths"] == 2
    assert result["fine_payoffs"].shape == result["differences"].shape == (3,)
    assert result["cost_counts"] == {
        "stock_updates": 9,
        "normal_draws": 6,
        "payoff_evaluations": 6,
        "coarse_aggregations": 3,
    }


def test_zero_volatility_keeps_euler_drift_and_its_exact_bias():
    from hullkit import _multilevel_mc as m

    result = m.gbm_level_samples(
        m.GBMCall(100, 90, 0.08, 0, 2, 0.02), np.zeros((3, 4)), level=1, base_steps=2
    )
    discount = math.exp(-0.16)
    fine = discount * (100 * 1.03**4 - 90)
    coarse = discount * (100 * 1.06**2 - 90)
    exact = discount * (100 * math.exp(0.12) - 90)
    np.testing.assert_allclose(result["fine_payoffs"], np.full(3, fine), atol=1e-12)
    np.testing.assert_allclose(result["coarse_payoffs"], np.full(3, coarse), atol=1e-12)
    np.testing.assert_allclose(result["paired_exact_bias"], np.full(3, fine - exact), atol=1e-12)


def test_nested_aggregation_preserves_total_brownian_increment():
    from hullkit import _multilevel_mc as m

    z = np.array([[1.0, 2.0, -3.0, 4.0], [0.5, -1.5, 2.0, 3.0]])
    aggregated = m.coarse_normals(m.coarse_normals(z))
    np.testing.assert_allclose(aggregated[:, 0], [2.0, 2.0], rtol=0, atol=1e-12)


def test_student_interval_uses_pair_variance_and_satterthwaite_degrees():
    from hullkit import _multilevel_mc as m
    from scipy.stats import t

    levels = [
        {"count": 4, "mean": 2.5, "m2": 5.0},
        {"count": 4, "mean": 0.0, "m2": 0.1},
    ]
    out = m.mlmc_summary(levels, confidence=0.9)
    variance = 17 / 40
    df = 7803 / 2501
    assert out["variance"] == pytest.approx(variance)
    assert out["standard_error"] == pytest.approx(math.sqrt(variance))
    assert out["df"] == pytest.approx(df)
    assert out["confidence_level"] == pytest.approx(0.9)
    np.testing.assert_allclose(
        out["interval"], 2.5 + np.array([-1, 1]) * t.ppf(0.95, df) * math.sqrt(variance)
    )
    assert out["degenerate"] is False


def test_zero_variance_interval_is_explicitly_degenerate():
    from hullkit import _multilevel_mc as m

    out = m.mlmc_summary([{"count": 8, "mean": 3.0, "m2": 0.0}])
    assert out["variance"] == pytest.approx(0.0)
    assert out["standard_error"] == pytest.approx(0.0)
    assert out["interval"] == pytest.approx((3.0, 3.0))
    assert out["df"] is None
    assert out["degenerate"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"spot": 0},
        {"strike": -1},
        {"maturity": 0},
        {"sigma": -0.1},
        {"rate": np.nan},
        {"yield_rate": np.inf},
    ],
)
def test_contract_rejects_undefined_coefficients(overrides):
    from hullkit import _multilevel_mc as m

    values = dict(spot=100, strike=100, rate=0.03, sigma=0.2, maturity=1)
    values.update(overrides)
    with pytest.raises(ValueError):
        m.GBMCall(**values)


@pytest.mark.parametrize(
    ("normals", "level", "base_steps"),
    [
        (np.zeros(4), 0, 4),
        (np.zeros((1, 4)), 0, 4),
        (np.zeros((2, 3)), 0, 4),
        (np.full((2, 4), np.nan), 0, 4),
        (np.zeros((2, 4)), -1, 4),
        (np.zeros((2, 4)), True, 4),
        (np.zeros((2, 4)), 0.0, 4),
        (np.zeros((2, 4)), 0, 0),
        (np.zeros((2, 4)), 0, True),
    ],
)
def test_level_rejects_undefined_grid_or_samples(normals, level, base_steps):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.gbm_level_samples(
            m.GBMCall(100, 100, 0.03, 0.2, 1), normals, level=level, base_steps=base_steps
        )


@pytest.mark.parametrize("normals", [np.zeros((2, 3)), np.zeros((0, 2)), np.array([[np.inf, 0]])])
def test_coarse_aggregation_rejects_unpaired_or_nonfinite_shocks(normals):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.coarse_normals(normals)


@pytest.mark.parametrize(
    ("contract", "normals"),
    [
        ((100, 100, 0, 1, 1), np.full((2, 1), 1e4)),
        ((1e308, 100, 0, 1, 1), np.full((2, 1), 100.0)),
        ((100, 100, -1000, 0, 1), np.zeros((2, 1))),
    ],
)
def test_nonfinite_results_fail_whole_run_instead_of_dropping_paths(contract, normals):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError, match="nonfinite"):
        m.gbm_level_samples(m.GBMCall(*contract), normals, level=0, base_steps=1)


@pytest.mark.parametrize("samples", [np.array([]), np.zeros((2, 1)), np.array([0.0, np.nan])])
def test_moment_blocks_require_nonempty_finite_one_dimensional_values(samples):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.block_moments(samples)


@pytest.mark.parametrize(
    "blocks",
    [[], [{"count": 0, "mean": 1, "m2": 0}], [{"count": 2, "mean": 1, "m2": -1}]],
)
def test_merge_rejects_invalid_centered_records(blocks):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.merge_moments(blocks)


@pytest.mark.parametrize(
    ("levels", "confidence"),
    [
        ([], 0.95),
        ([{"count": 1, "mean": 0, "m2": 0}], 0.95),
        ([{"count": 2, "mean": 0, "m2": 1}], 1),
        ([{"count": 2, "mean": 0, "m2": 1}], 0),
        ([{"count": 2, "mean": 0, "m2": 1}], np.nan),
    ],
)
def test_summary_requires_variance_defined_for_every_level(levels, confidence):
    from hullkit import _multilevel_mc as m

    with pytest.raises(ValueError):
        m.mlmc_summary(levels, confidence=confidence)


@pytest.mark.parametrize(
    ("variances", "costs", "options"),
    [
        ([], [], {}),
        ([1, 2], [1], {}),
        ([-1], [1], {}),
        ([np.nan], [1], {}),
        ([1], [0], {}),
        ([1], [np.inf], {}),
        ([1], [1], {"sampling_variance": 0}),
        ([1], [1], {"minimum": 0}),
        ([1], [1], {"variance_floor": -1}),
        ([1], [1], {"sampling_variance": 1e-320}),
    ],
)
def test_allocation_rejects_undefined_budget_or_unrepresentable_count(variances, costs, options):
    from hullkit import _multilevel_mc as m

    arguments = {"sampling_variance": 1, **options}
    with pytest.raises(ValueError):
        m.allocate_paths(np.asarray(variances), np.asarray(costs), **arguments)


def test_core_import_remains_torch_free_in_fresh_process():
    source = Path(__file__).resolve().parents[1] / "src"
    env = {**os.environ, "PYTHONPATH": str(source)}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import hullkit._multilevel_mc; assert 'torch' not in sys.modules",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
