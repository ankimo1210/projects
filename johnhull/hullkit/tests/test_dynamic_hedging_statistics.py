"""Independent moments and hand-enumerated bootstrap for hedge decisions."""

import importlib
import itertools

import numpy as np
import pytest


def statistics_module():
    """Make missing production behavior an explicit RED assertion."""
    name = "hullkit._dynamic_hedging_statistics"
    assert importlib.util.find_spec(name) is not None, "dynamic statistics is not implemented"
    return importlib.import_module(name)


def constant_indices(blocks=2, replicates=8):
    """Use deterministic saved selections; never call a production RNG."""
    return np.zeros((replicates, 3, blocks), dtype=np.int16)


def all_two_block_selections():
    """Enumerate eight distinct choices of one repeated block per seed."""
    return np.array(
        [[[j, j] for j in choice] for choice in itertools.product((0, 1), repeat=3)], dtype=np.int16
    )


def test_bootstrap_indices_are_local_reproducible_and_seed_stratified():
    statistics = statistics_module()
    state_before = np.random.get_state()
    first = statistics.make_bootstrap_indices(5, seed=123, replicates=25)
    second = statistics.make_bootstrap_indices(5, seed=123, replicates=25)
    third = statistics.make_bootstrap_indices(5, seed=124, replicates=25)
    assert first.shape == (25, 3, 5)
    assert first.dtype == np.int16
    assert first.min() >= 0 and first.max() < 5
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, third)
    assert not np.array_equal(first[:, 0], first[:, 1])
    state_after = np.random.get_state()
    assert state_before[0] == state_after[0]
    np.testing.assert_array_equal(state_before[1], state_after[1])
    assert state_before[2:] == state_after[2:]


@pytest.mark.parametrize("blocks,replicates", [(0, 2), (32769, 2), (2, 0), (2.5, 2)])
def test_bootstrap_indices_reject_impossible_sizes(blocks, replicates):
    with pytest.raises(ValueError):
        statistics_module().make_bootstrap_indices(blocks, seed=1, replicates=replicates)


def test_risk_summary_matches_numpy_individual_moments_and_seed_stratified_se():
    losses = np.array([[-2.0, -1.0, 1.0, 2.0], [0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0]])
    result = statistics_module().risk_summary(losses, block_size=2)
    assert result["status"] == "ok"
    assert result["original_count"] == 12
    assert result["counts"]["original_per_seed"].tolist() == [4, 4, 4]
    assert result["counts"]["unknown_per_seed"].tolist() == [0, 0, 0]
    assert result["mean_loss"] == pytest.approx(np.mean(losses))
    assert result["mse"] == pytest.approx(np.mean(losses**2))
    assert result["rmse"] == pytest.approx(np.sqrt(np.mean(losses**2)))
    assert result["variance"] == pytest.approx(np.var(losses, ddof=1))
    assert result["mean_loss_se"] == pytest.approx(
        np.sqrt(np.sum(np.var(losses, axis=1, ddof=1) / 4)) / 3
    )
    assert result["mse_se"] == pytest.approx(
        np.sqrt(np.sum(np.var(losses**2, axis=1, ddof=1) / 4)) / 3
    )
    assert result["pooled_mean_loss_se"] == pytest.approx(np.std(losses, ddof=1) / np.sqrt(12))
    assert result["pooled_mse_se"] == pytest.approx(np.std(losses**2, ddof=1) / np.sqrt(12))
    np.testing.assert_allclose(result["block_means"]["loss"], [[-1.5, 1.5], [0.5, 2.5], [2.0, 6.0]])
    np.testing.assert_allclose(
        result["block_means"]["squared_loss"], [[2.5, 2.5], [0.5, 6.5], [5.0, 37.0]]
    )


def test_es95_uses_top_ceil_individual_losses_not_block_means():
    losses = np.zeros((3, 64))
    losses[0, :10] = np.arange(91.0, 101.0)
    result = statistics_module().risk_summary(losses)
    assert result["es95"] == pytest.approx(95.5)
    assert result["es95_tail_count"] == 10
    assert result["es95_original_count"] == 192
    assert result["es95_ci_status"] == "not_evaluated"
    assert result["es95"] != pytest.approx(np.max(np.mean(losses, axis=1)))


def test_es95_fixed_tail_count_does_not_include_all_boundary_ties():
    result = statistics_module().risk_summary(np.full((3, 7), 2.0), block_size=3)
    assert result["es95"] == pytest.approx(2.0)
    assert result["es95_tail_count"] == 2
    assert result["block_means"] is None
    assert result["block_status"] == "not_divisible"


@pytest.mark.parametrize("poison", [np.nan, np.inf, -np.inf])
def test_original_nonfinite_loss_poison_keeps_denominator_and_separate_descriptive_subset(poison):
    losses = np.ones((3, 4))
    losses[1, 2] = poison
    result = statistics_module().risk_summary(losses, block_size=2)
    assert result["status"] == "unknown"
    assert result["original_count"] == 12
    assert result["counts"]["unknown_per_seed"].tolist() == [0, 1, 0]
    for name in ("mean_loss", "mse", "variance", "mean_loss_se", "mse_se", "es95"):
        assert np.isnan(result[name])
    assert result["finite_only"]["status"] == "descriptive_only"
    assert result["finite_only"]["count"] == 11
    assert result["finite_only"]["mean_loss"] == pytest.approx(1.0)
    assert result["es95_original_count"] == 12


def test_paired_statistics_matches_hand_enumerated_seed_bootstrap():
    baseline = np.repeat(np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]), 2, axis=1)
    candidate = np.sqrt(np.repeat(np.array([[0.5, 0.8], [2.0, 3.0], [6.0, 8.0]]), 2, axis=1))
    indices = all_two_block_selections()
    result = statistics_module().paired_statistics(
        baseline,
        candidate,
        indices,
        block_size=2,
        alpha=0.125,
        numerical_envelope={"absolute": 0.01, "relative": 0.02},
    )
    d_blocks = np.array([[-0.5, -0.2], [-2.0, -1.0], [-3.0, -1.0]])
    r_blocks = np.array([[-0.45, -0.15], [-1.8, -0.8], [-2.55, -0.55]])
    # Independent enumeration, starting from hand-derived squared-loss differences.
    expected_d = [
        sum(d_blocks[s, j] for s, j in enumerate(choice)) / 3
        for choice in itertools.product((0, 1), repeat=3)
    ]
    expected_r = [
        sum(r_blocks[s, j] for s, j in enumerate(choice)) / 3
        for choice in itertools.product((0, 1), repeat=3)
    ]
    np.testing.assert_allclose(result["scores"]["absolute"], np.repeat(d_blocks, 2, axis=1))
    np.testing.assert_allclose(result["scores"]["relative"], np.repeat(r_blocks, 2, axis=1))
    np.testing.assert_allclose(result["block_scores"]["absolute"], d_blocks)
    np.testing.assert_allclose(result["block_scores"]["relative"], r_blocks)
    np.testing.assert_allclose(result["bootstrap_scores"]["absolute"], expected_d)
    np.testing.assert_allclose(result["bootstrap_scores"]["relative"], expected_r)
    assert result["upper_bounds"]["absolute"] == pytest.approx(
        np.quantile(expected_d, 0.875, method="linear")
    )
    assert result["upper_bounds"]["relative"] == pytest.approx(
        np.quantile(expected_r, 0.875, method="linear")
    )
    assert result["iid_se"]["absolute"] == pytest.approx(
        np.sqrt(np.sum(np.var(np.repeat(d_blocks, 2, axis=1), axis=1, ddof=1) / 4)) / 3
    )
    np.testing.assert_array_equal(result["bootstrap_indices"], indices)
    assert result["alpha"] == 0.125
    assert result["original_count"] == 12
    assert result["counts"]["original_per_seed"].tolist() == [4, 4, 4]
    assert result["status"] == "supported"
    assert result["risk_improvement_supported"] is True


def test_default_family_alpha_is_applied_once_and_mean_loss_bootstrap_is_replayable():
    baseline = np.repeat(np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), 2, axis=1)
    candidate = 0.5 * baseline
    result = statistics_module().paired_statistics(
        baseline,
        candidate,
        all_two_block_selections(),
        block_size=2,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    reference_mean = [
        sum((1 + 2 * seed + choice[seed]) for seed in range(3)) / 3
        for choice in itertools.product((0, 1), repeat=3)
    ]
    np.testing.assert_allclose(result["bootstrap_mean_loss"]["baseline"], reference_mean)
    np.testing.assert_allclose(
        result["bootstrap_mean_loss"]["candidate"], np.array(reference_mean) / 2
    )
    assert result["alpha"] == pytest.approx(0.05 / 8)
    assert result["upper_bounds"]["absolute"] == pytest.approx(
        np.quantile(result["bootstrap_scores"]["absolute"], 1 - 0.05 / 8, method="linear")
    )


def test_random_baseline_uncertainty_changes_relative_threshold_decision():
    baseline_sq = np.repeat(np.array([[1.0, 3.0]] * 3), 64, axis=1)
    candidate_sq = baseline_sq - 0.1
    indices = all_two_block_selections()
    result = statistics_module().paired_statistics(
        np.sqrt(baseline_sq),
        np.sqrt(candidate_sq),
        indices,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    assert result["means"]["absolute"] == pytest.approx(-0.1)
    assert result["means"]["relative"] == pytest.approx(0.0, abs=1e-14)
    assert result["iid_se"]["absolute"] == pytest.approx(0.0, abs=1e-14)
    assert result["iid_se"]["relative"] > 0
    np.testing.assert_allclose(result["block_scores"]["relative"], [[-0.05, 0.05]] * 3, atol=1e-14)
    assert result["upper_bounds"]["relative"] > 0
    assert result["status"] == "not_supported"
    assert result["risk_improvement_supported"] is False


@pytest.mark.parametrize(
    "boundary,expected",
    [
        (None, "supported"),
        ("absolute", "not_supported"),
        ("relative", "not_supported"),
        ("above_absolute", "not_supported"),
    ],
)
def test_support_uses_strict_absolute_and_relative_envelope_boundaries(boundary, expected):
    baseline = np.sqrt(np.full((3, 4), 0.002))
    candidate = np.zeros((3, 4))
    # A NumPy reference square gives the constant score without calling production.
    # At this scale subtraction/addition represents the -.001 boundary exactly.
    base_sq = np.square(baseline[0, 0])
    envelope = {"absolute": 0.0, "relative": 0.0}
    if boundary == "absolute":
        envelope["absolute"] = base_sq - 0.001
        assert -base_sq + envelope["absolute"] == -0.001
    elif boundary == "relative":
        envelope["relative"] = 0.95 * base_sq
        assert -0.95 * base_sq + envelope["relative"] == 0.0
    elif boundary == "above_absolute":
        envelope["absolute"] = base_sq
    result = statistics_module().paired_statistics(
        baseline, candidate, constant_indices(), block_size=2, numerical_envelope=envelope
    )
    assert result["status"] == expected


@pytest.mark.parametrize(
    "envelope",
    [
        None,
        {"absolute": None, "relative": 0.0},
        {"absolute": 0.0},
        {"absolute": np.nan, "relative": 0.0},
        {"absolute": 0.0, "relative": np.inf},
    ],
)
def test_unmeasured_or_nonfinite_envelope_cannot_support(envelope):
    result = statistics_module().paired_statistics(
        np.ones((3, 4)),
        np.zeros((3, 4)),
        constant_indices(),
        block_size=2,
        numerical_envelope=envelope,
    )
    assert result["status"] == "unknown"
    assert result["risk_improvement_supported"] is None
    assert result["envelope_status"] == "unknown"


@pytest.mark.parametrize(
    "envelope", [{"absolute": -0.01, "relative": 0.0}, {"absolute": [0.0], "relative": 0.0}]
)
def test_envelope_requires_nonnegative_scalars(envelope):
    with pytest.raises(ValueError):
        statistics_module().paired_statistics(
            np.ones((3, 4)),
            np.zeros((3, 4)),
            constant_indices(),
            block_size=2,
            numerical_envelope=envelope,
        )


def test_paired_nonfinite_path_retains_raw_full_scores_and_unknown_primary():
    baseline = np.ones((3, 4))
    candidate = np.zeros((3, 4))
    candidate[2, 3] = np.nan
    result = statistics_module().paired_statistics(
        baseline,
        candidate,
        constant_indices(),
        block_size=2,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    assert result["status"] == "unknown"
    assert result["risk_improvement_supported"] is None
    assert result["original_count"] == 12
    assert result["counts"]["unknown_per_seed"].tolist() == [0, 0, 1]
    assert result["scores"]["absolute"].shape == (3, 4)
    assert np.isnan(result["scores"]["absolute"][2, 3])
    assert np.isnan(result["means"]["absolute"])
    assert np.isnan(result["upper_bounds"]["absolute"])
    assert result["finite_only"]["status"] == "descriptive_only"
    assert result["finite_only"]["count"] == 11
    assert result["finite_only"]["means"]["absolute"] == pytest.approx(-1.0)


@pytest.mark.filterwarnings("error")
@pytest.mark.parametrize("magnitude", [1e100, 1e154])
def test_finite_paths_with_overflowing_uncertainty_cannot_support(magnitude):
    baseline = np.repeat(np.array([[magnitude, 1.1 * magnitude]] * 3), 2, axis=1)
    result = statistics_module().paired_statistics(
        baseline,
        np.zeros((3, 4)),
        constant_indices(),
        block_size=2,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    assert result["counts"]["unknown"] == 0
    assert not np.isfinite(result["iid_se"]["absolute"])
    assert result["status"] == "unknown"
    assert result["risk_improvement_supported"] is None
    if magnitude == 1e154:
        assert np.isnan(result["finite_only"]["means"]["absolute"])
        assert result["finite_only"]["arithmetic_status"] == "unknown"
        assert np.isnan(result["baseline_summary"]["finite_only"]["mse"])
        assert result["baseline_summary"]["finite_only"]["arithmetic_status"] == "unknown"


def test_saved_paired_replay_uses_shared_indices_without_any_rng(monkeypatch):
    statistics = statistics_module()
    indices = all_two_block_selections()
    baseline = np.repeat(np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), 2, axis=1)
    candidate = 0.9 * baseline
    before = np.random.get_state()

    def forbidden(*args, **kwargs):
        pytest.fail("saved statistics replay requested an RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(np.random, "SeedSequence", forbidden)
    first = statistics.paired_statistics(
        baseline,
        candidate,
        indices,
        block_size=2,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    second = statistics.paired_statistics(
        baseline,
        -candidate,
        indices,
        block_size=2,
        numerical_envelope={"absolute": 0.0, "relative": 0.0},
    )
    np.testing.assert_array_equal(first["bootstrap_indices"], indices)
    np.testing.assert_allclose(
        first["bootstrap_scores"]["absolute"], second["bootstrap_scores"]["absolute"]
    )
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[0] == after[0] and before[2:] == after[2:]


def test_family_iut_requires_all_three_initializations_and_both_conditions():
    statistics = statistics_module()
    supported = {"status": "supported", "conditions": {"absolute": True, "relative": True}}
    results = {"11": supported, "29": supported, "47": supported}
    family = statistics.family_assessment(results)
    assert family["status"] == "supported"
    assert family["risk_improvement_supported"] is True
    assert family["initialization_statuses"] == {
        "11": "supported",
        "29": "supported",
        "47": "supported",
    }
    results["29"] = {"status": "not_supported", "conditions": {"absolute": True, "relative": False}}
    assert statistics.family_assessment(results)["status"] == "not_supported"
    results["47"] = {"status": "unknown", "conditions": {"absolute": None, "relative": None}}
    family = statistics.family_assessment(results)
    assert family["status"] == "unknown"
    assert family["risk_improvement_supported"] is None


def test_family_cannot_trust_supported_label_without_both_score_conditions():
    supported = {"status": "supported", "conditions": {"absolute": True, "relative": True}}
    deceptive = {"status": "supported", "conditions": {"absolute": True, "relative": False}}
    assert (
        statistics_module().family_assessment({11: supported, 29: supported, 47: deceptive})[
            "status"
        ]
        == "not_supported"
    )


@pytest.mark.parametrize("keys", [(11, 29), (11, 29, 47, 99), (11, 29, 48)])
def test_family_rejects_missing_or_selected_initialization_rosters(keys):
    with pytest.raises(ValueError):
        statistics_module().family_assessment({key: {"status": "supported"} for key in keys})


@pytest.mark.parametrize(
    "invalid",
    [
        "wrong_loss_shape",
        "unequal_pairs",
        "not_divisible",
        "wrong_seed_axis",
        "out_of_range",
        "noninteger_indices",
        "bad_alpha",
    ],
)
def test_statistics_reject_only_mathematically_invalid_inputs(invalid):
    statistics = statistics_module()
    base, candidate, indices, alpha = (
        np.ones((3, 4)),
        np.zeros((3, 4)),
        constant_indices(),
        0.05 / 8,
    )
    if invalid == "wrong_loss_shape":
        with pytest.raises(ValueError):
            statistics.risk_summary(np.ones((2, 4)))
        return
    if invalid == "unequal_pairs":
        candidate = np.zeros((3, 3))
    elif invalid == "not_divisible":
        base, candidate = np.ones((3, 3)), np.zeros((3, 3))
    elif invalid == "wrong_seed_axis":
        indices = np.zeros((8, 2, 2), dtype=np.int16)
    elif invalid == "out_of_range":
        indices[0, 0, 0] = 2
    elif invalid == "noninteger_indices":
        indices = indices.astype(float)
    elif invalid == "bad_alpha":
        alpha = 0.0
    with pytest.raises(ValueError):
        statistics.paired_statistics(base, candidate, indices, block_size=2, alpha=alpha)
