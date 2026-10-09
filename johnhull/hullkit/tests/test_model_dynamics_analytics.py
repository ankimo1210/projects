"""Sampling and contract checks for the RB-F04 model comparison."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research" / "RB-F04" / "analytics.py"


def _analytics():
    assert PATH.is_file(), "RB-F04 paired sampling analytics are not implemented"
    spec = importlib.util.spec_from_file_location("rb_f04_analytics", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asian_uses_only_twelve_monthly_observations_and_maturity_discount():
    analytics = _analytics()
    observations = np.array([[1000.0] + [110.0] * 12, [1000.0] + [90.0] * 12])
    result = analytics.asian_payoffs(observations, strike=100, rate=0.03, expiry=1)
    assert result == pytest.approx([10 * np.exp(-0.03), 0])


def test_vanilla_payoffs_use_contractual_month_not_all_internal_steps():
    analytics = _analytics()
    observations = np.tile(np.arange(100, 113), (2, 1))
    result = analytics.vanilla_payoffs(
        observations, times=[0.25, 0.5, 1], strikes=[100, 110], rate=0.03, expiry=1
    )
    expected = (
        np.array([[3, 0], [6, 0], [12, 2]], dtype=float)
        * np.exp(-0.03 * np.array([0.25, 0.5, 1]))[:, None]
    )
    assert result == pytest.approx(np.tile(expected, (2, 1, 1)))
    with pytest.raises(ValueError, match="monthly"):
        analytics.vanilla_payoffs(observations, [0.1], [100], 0.03, 1)


def test_paired_standard_error_uses_actual_model_difference_covariance():
    analytics = _analytics()
    heston = np.array([1, 3, 5, 7], dtype=float)
    local = heston + np.array([1, -1, 1, -1])
    result = analytics.paired_summary(heston, local)
    assert result["heston"]["mean"] == pytest.approx(4)
    assert result["local"]["mean"] == pytest.approx(4)
    assert result["difference"]["mean"] == pytest.approx(0)
    assert result["difference"]["standard_error"] == pytest.approx(np.sqrt(1 / 3))
    # An unpaired SE would be much larger.
    assert result["difference"]["standard_error"] < result["heston"]["standard_error"]


def test_failed_path_is_counted_and_not_filtered_from_mean():
    analytics = _analytics()
    result = analytics.paired_summary(np.array([1, np.nan, 3]), np.array([2, 2, 4]))
    assert result["heston"]["samples"] == 3
    assert not result["heston"]["supported"]
    assert np.isnan(result["heston"]["mean"])
    assert not result["difference"]["supported"]
    assert np.isnan(result["difference"]["standard_error"])
    assert result["local"]["mean"] == pytest.approx(8 / 3)


def test_joint_histogram_covers_tails_and_uses_paired_cell_indicators():
    analytics = _analytics()
    heston = np.array([[20, 130], [80, 100], [100, 80], [150, 50]], dtype=float)
    local = np.array([[50, 150], [90, 100], [100, 80], [130, 20]], dtype=float)
    result = analytics.two_date_summary(heston, local, bins=[80, 100, 120], minimum_count=1)
    assert result["joint_counts_heston"].sum() == 4
    assert result["joint_counts_local"].sum() == 4
    assert result["joint_difference"].sum() == pytest.approx(0)
    # heston (80,100) moves one first-date bin under local (90,100):
    # these two lie in the same bin, hence all joint differences are zero.
    assert result["joint_standard_error"] == pytest.approx(np.zeros((4, 4)))


def test_conditional_ratios_have_own_denominator_and_full_paired_delta_method_se():
    analytics = _analytics()
    rng = np.random.default_rng(77)
    heston = np.column_stack([rng.choice([90, 110], 180), rng.choice([90, 130], 180)])
    local = heston.copy()
    local[:37, 0] = 200 - heston[:37, 0]
    local[20:70, 1] = 220 - heston[20:70, 1]
    result = analytics.two_date_summary(
        heston, local, bins=[100], conditional_threshold=110, minimum_count=20
    )
    for j, upper in enumerate([False, True]):
        ah = (heston[:, 0] >= 100) == upper
        al = (local[:, 0] >= 100) == upper
        yh = ah & (heston[:, 1] > 110)
        yl = al & (local[:, 1] > 110)
        ph = yh.sum() / ah.sum()
        pl = yl.sum() / al.sum()
        assert result["conditional_heston"][j] == pytest.approx(ph)
        assert result["conditional_local"][j] == pytest.approx(pl)
        assert result["conditional_difference"][j] == pytest.approx(pl - ph)
        # Independent multivariate delta method on four primitive sample means.
        primitive = np.column_stack([yh, ah, yl, al]).astype(float)
        means = primitive.mean(axis=0)
        gradient = np.array(
            [-1 / means[1], means[0] / means[1] ** 2, 1 / means[3], -means[2] / means[3] ** 2]
        )
        variance = gradient @ np.cov(primitive, rowvar=False, ddof=1) @ gradient / 180
        assert result["conditional_standard_error"][j] == pytest.approx(np.sqrt(variance))


def test_conditional_sparse_bins_are_explicitly_unsupported():
    analytics = _analytics()
    paths = np.array([[90, 130], [90, 80], [110, 130]], dtype=float)
    result = analytics.two_date_summary(paths, paths, bins=[100], minimum_count=2)
    assert result["conditional_supported"].tolist() == [True, False]
    assert result["conditional_difference"][0] == pytest.approx(0)
    assert np.isnan(result["conditional_heston"][1])
    assert result["conditional_counts_heston"].tolist() == [2, 1]


def test_two_date_failed_paths_make_all_distribution_claims_unsupported():
    analytics = _analytics()
    paths = np.array([[90, 110], [np.nan, 120], [100, 100]])
    result = analytics.two_date_summary(paths, paths, bins=[100])
    assert not result["supported"]
    assert result["failed_pairs"] == 1
    assert result["samples"] == 3
    assert np.isnan(result["joint_difference"]).all()


def test_single_sample_has_no_sampling_standard_error():
    analytics = _analytics()
    result = analytics.sample_summary(np.array([2.0]))
    assert not result["supported"]
    assert np.isnan(result["standard_error"])


@pytest.mark.parametrize("threshold", [np.nan, np.inf, -np.inf])
def test_nonfinite_conditional_threshold_is_not_a_supported_zero_event(threshold):
    paths = np.array([[90, 110], [110, 130]], dtype=float)
    with pytest.raises(ValueError, match="threshold"):
        _analytics().two_date_summary(paths, paths, bins=[100], conditional_threshold=threshold)


def test_nonzero_joint_cell_se_matches_independent_bernoulli_difference():
    paths = np.tile([90.0, 90.0], (4, 1))
    local = paths.copy()
    local[0, 0] = 110.0
    result = _analytics().two_date_summary(paths, local, bins=[100], minimum_count=1)
    assert result["joint_difference"] == pytest.approx(np.array([[-0.25, 0], [0.25, 0]]))
    assert result["joint_standard_error"] == pytest.approx(np.array([[0.25, 0], [0.25, 0]]))
