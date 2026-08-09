import numpy as np
import pytest
from quant_textbook import (
    DistributionSpec,
    draw_distribution,
    hoeffding_two_sided_bound,
    normal_mean_coverage,
    running_sample_mean,
    sample_mean_experiment,
)


def test_distribution_moments_are_explicit() -> None:
    gaussian = DistributionSpec("gaussian", location=2.0, scale=3.0)
    student = DistributionSpec("student_t", degrees_of_freedom=1.5)
    pareto = DistributionSpec("pareto", tail_index=3.0, minimum=2.0)
    mixture = DistributionSpec(
        "mixture",
        scale=2.0,
        mixture_probability=0.1,
        outlier_scale=5.0,
    )

    assert gaussian.theoretical_mean == 2.0
    assert gaussian.theoretical_variance == 9.0
    assert student.theoretical_mean == 0.0
    assert np.isinf(student.theoretical_variance)
    assert pareto.theoretical_mean == pytest.approx(3.0)
    assert pareto.theoretical_variance == pytest.approx(3.0)
    assert mixture.theoretical_variance == pytest.approx(13.6)


def test_sampling_experiment_is_reproducible_and_lln_error_shrinks() -> None:
    specification = DistributionSpec("gaussian", location=1.0, scale=2.0)
    first = sample_mean_experiment(
        specification,
        [8, 64, 512],
        2_000,
        rng=np.random.default_rng(31),
    )
    second = sample_mean_experiment(
        specification,
        [8, 64, 512],
        2_000,
        rng=np.random.default_rng(31),
    )

    np.testing.assert_array_equal(first.estimates, second.estimates)
    assert first.estimates.shape == (3, 2_000)
    assert first.root_mean_squared_error[2] < first.root_mean_squared_error[0] / 6.0
    expected_ratio = np.sqrt(512 / 8)
    observed_ratio = first.root_mean_squared_error[0] / first.root_mean_squared_error[2]
    assert observed_ratio == pytest.approx(expected_ratio, rel=0.08)


def test_heavy_tail_makes_sample_mean_extremes_unstable() -> None:
    gaussian = sample_mean_experiment(
        DistributionSpec("gaussian"),
        [256],
        3_000,
        rng=np.random.default_rng(41),
    )
    heavy = sample_mean_experiment(
        DistributionSpec("student_t", degrees_of_freedom=1.5),
        [256],
        3_000,
        rng=np.random.default_rng(42),
    )
    gaussian_extreme = np.quantile(np.abs(gaussian.estimates[0]), 0.99)
    heavy_extreme = np.quantile(np.abs(heavy.estimates[0]), 0.99)
    assert heavy_extreme > 8.0 * gaussian_extreme


def test_normal_interval_coverage_includes_monte_carlo_uncertainty() -> None:
    result = normal_mean_coverage(
        DistributionSpec("gaussian", location=-0.5, scale=1.3),
        n_samples=50,
        n_replications=5_000,
        rng=np.random.default_rng(52),
    )
    assert result.coverage_probability == pytest.approx(0.95, abs=0.015)
    assert result.monte_carlo_standard_error < 0.004
    assert result.average_width > 0.0


def test_running_mean_and_hoeffding_bound() -> None:
    np.testing.assert_allclose(running_sample_mean([1.0, 3.0, 2.0]), [1.0, 2.0, 2.0])
    loose = hoeffding_two_sided_bound(0.1, 10, lower_bound=0.0, upper_bound=1.0)
    tight = hoeffding_two_sided_bound(0.1, 1_000, lower_bound=0.0, upper_bound=1.0)
    assert 0.0 < tight < loose <= 1.0


def test_coverage_rejects_distribution_without_a_mean() -> None:
    specification = DistributionSpec("pareto", tail_index=0.9)
    with pytest.raises(ValueError, match="mean does not exist"):
        normal_mean_coverage(
            specification,
            20,
            100,
            rng=np.random.default_rng(1),
        )


def test_draw_distribution_requires_generator() -> None:
    with pytest.raises(TypeError, match="Generator"):
        draw_distribution(DistributionSpec(), 5, rng=None)  # type: ignore[arg-type]
