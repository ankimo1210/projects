import numpy as np
import pytest
from quant_textbook import (
    benjamini_hochberg,
    bonferroni_adjust,
    bootstrap_statistic,
    parametric_bootstrap_statistic,
    permutation_test_two_sample,
)


def test_nonparametric_bootstrap_is_reproducible_and_calibrates_mean_se() -> None:
    rng = np.random.default_rng(201)
    samples = rng.normal(0.5, 2.0, 500)
    first = bootstrap_statistic(
        samples,
        np.mean,
        2_000,
        rng=np.random.default_rng(202),
    )
    second = bootstrap_statistic(
        samples,
        np.mean,
        2_000,
        rng=np.random.default_rng(202),
    )

    np.testing.assert_array_equal(first.replicates, second.replicates)
    assert first.estimate == pytest.approx(samples.mean())
    assert first.bootstrap_standard_error == pytest.approx(
        samples.std(ddof=1) / np.sqrt(samples.size), rel=0.08
    )
    assert first.confidence_interval[0] < samples.mean() < first.confidence_interval[1]
    assert first.method == "nonparametric"


def test_parametric_bootstrap_uses_explicit_sampler_and_generator() -> None:
    samples = np.array([-0.5, 0.1, 0.2, 0.8, 1.4])
    fitted_mean = float(samples.mean())
    fitted_scale = float(samples.std(ddof=0))

    def sampler(rng, n_samples):
        return rng.normal(fitted_mean, fitted_scale, n_samples)

    result = parametric_bootstrap_statistic(
        samples,
        sampler,
        np.mean,
        1_000,
        rng=np.random.default_rng(203),
    )
    assert result.method == "parametric"
    assert result.replicates.shape == (1_000,)
    assert result.bootstrap_bias == pytest.approx(0.0, abs=0.03)


def test_randomized_permutation_test_detects_signal_and_never_returns_zero() -> None:
    first = np.arange(20.0)
    second = np.arange(20.0) + 10.0

    def mean_difference(left, right):
        return float(left.mean() - right.mean())

    result = permutation_test_two_sample(
        first,
        second,
        mean_difference,
        999,
        rng=np.random.default_rng(204),
        alternative="less",
    )
    repeated = permutation_test_two_sample(
        first,
        second,
        mean_difference,
        999,
        rng=np.random.default_rng(204),
        alternative="less",
    )

    assert result.observed_statistic == pytest.approx(-10.0)
    assert 0.0 < result.p_value <= 0.01
    assert result.p_value >= 1.0 / 1_000.0
    np.testing.assert_array_equal(result.null_distribution, repeated.null_distribution)


def test_bonferroni_and_bh_adjustments_preserve_original_order() -> None:
    p_values = np.array([0.03, 0.001, 0.2, 0.01])
    bonferroni = bonferroni_adjust(p_values)
    fdr = benjamini_hochberg(p_values)

    np.testing.assert_allclose(bonferroni.adjusted_p_values, [0.12, 0.004, 0.8, 0.04])
    np.testing.assert_array_equal(bonferroni.rejected, [False, True, False, True])
    np.testing.assert_allclose(fdr.adjusted_p_values, [0.04, 0.004, 0.2, 0.02])
    np.testing.assert_array_equal(fdr.rejected, [True, True, False, True])
    assert bonferroni.number_rejected == 2
    assert fdr.number_rejected == 3
    assert fdr.critical_raw_p_value == pytest.approx(0.03)


@pytest.mark.parametrize(
    ("function", "error_type", "message"),
    [
        (
            lambda: bootstrap_statistic([1.0, 2.0], np.mean, 10, rng=1),
            TypeError,
            "Generator",
        ),
        (
            lambda: bootstrap_statistic(
                [1.0, 2.0], lambda values: values, 10, rng=np.random.default_rng(1)
            ),
            ValueError,
            "finite scalar",
        ),
        (
            lambda: permutation_test_two_sample(
                [1.0, 2.0],
                [3.0, 4.0],
                lambda left, right: left.mean() - right.mean(),
                10,
                rng=np.random.default_rng(1),
                alternative="up",
            ),
            ValueError,
            "alternative",
        ),
        (
            lambda: benjamini_hochberg([0.1, 1.2]),
            ValueError,
            "between zero and one",
        ),
    ],
)
def test_resampling_rejects_invalid_contracts(function, error_type, message) -> None:
    with pytest.raises(error_type, match=message):
        function()
