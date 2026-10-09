"""Scramble-level RQMC uncertainty and frozen seed replay."""

from copy import deepcopy

import numpy as np
import pytest
from scipy.stats import t


def test_t_interval_uses_scrambles_not_raw_sobol_points():
    from hullkit import _rqmc_ci as r

    q = np.array([8.0, 10.0, 12.0, 14.0])
    original = q.copy()
    out = r.student_summary(q)
    se = np.std(q, ddof=1) / 2
    assert out["df"] == 3
    assert out["scrambles"] == 4
    assert out["price"] == pytest.approx(11)
    assert out["standard_error"] == pytest.approx(se)
    half = t.ppf(0.975, 3) * se
    assert out["interval"] == pytest.approx([11 - half, 11 + half])
    assert out["width"] == pytest.approx(2 * half)
    assert out["confidence_level"] == pytest.approx(0.95)
    assert out["approximate"] is True
    assert out["degenerate"] is False
    np.testing.assert_array_equal(q, original)


def test_student_accepts_custom_confidence():
    from hullkit import _rqmc_ci as r

    q = np.array([1.0, 3.0, 5.0])
    out = r.student_summary(q, confidence=0.80)
    half = t.ppf(0.90, 2) * np.std(q, ddof=1) / np.sqrt(3)
    assert out["interval"] == pytest.approx([3 - half, 3 + half])
    assert out["confidence_level"] == pytest.approx(0.80)


@pytest.mark.parametrize("value,count", [(0.0, 4), (5.0, 4), (0.1, 3)])
def test_identical_scrambles_have_degenerate_zero_width_interval(value, count):
    from hullkit import _rqmc_ci as r

    out = r.student_summary(np.full(count, value))
    assert out["standard_error"] == pytest.approx(0)
    assert out["width"] == pytest.approx(0)
    assert out["interval"] == pytest.approx([value, value])
    assert out["degenerate"] is True
    assert out["df"] is None
    assert out["approximate"] is True


@pytest.mark.parametrize("bad", [[1.0], [[1.0, 2.0]], [1.0, np.inf], [1.0, np.nan]])
def test_student_rejects_invalid_statistical_units(bad):
    from hullkit import _rqmc_ci as r

    with pytest.raises(ValueError):
        r.student_summary(bad)


@pytest.mark.parametrize("confidence", [0, 1, -0.1, 1.1, np.nan, np.inf])
def test_student_rejects_invalid_confidence(confidence):
    from hullkit import _rqmc_ci as r

    with pytest.raises(ValueError):
        r.student_summary([1.0, 2.0], confidence=confidence)


def _contract():
    from hullkit._multilevel_mc import GBMCall

    return GBMCall(50, 50, 0.05, 0.3, 0.5)


def test_existing_private_rqmc_estimates_are_preserved():
    from hullkit import _numerical_mc as old
    from hullkit import _rqmc_ci as r

    c = _contract()
    out = r.rqmc_gbm_call(c, power=4, scrambles=4, seed=21708)
    existing = old.randomized_qmc_price(50, 50, 0.05, 0.3, 0.5, power=4, scrambles=4, seed=21708)
    np.testing.assert_allclose(out["estimates"], existing["samples"], atol=1e-12, rtol=0)
    assert out["price"] == pytest.approx(existing["price"], abs=1e-12)
    assert out["standard_error"] == pytest.approx(existing["standard_error"], abs=1e-12)
    expected = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(21708).spawn(4)]
    assert out["child_seeds"] == expected
    assert out["child_spawn_keys"] == [[0], [1], [2], [3]]
    assert out["scrambles"] == 4
    assert out["points_per_scramble"] == 16
    assert out["payoff_evaluations"] == 64
    assert out["normal_dimensions"] == 1
    assert out["df"] == 3


def test_research_primitive_consumes_frozen_child_seeds_without_respawning():
    from hullkit import _numerical_mc as numerical
    from hullkit import _rqmc_ci as r

    seeds = [41, 43, 47, 53]
    out = r.rqmc_gbm_call_from_seeds(_contract(), power=4, child_seeds=seeds)
    manual = []
    for seed in seeds:
        z = numerical.sobol_normal_points(4, scramble=True, seed=seed)["normals"]
        terminal = numerical.gbm_paths_from_normals(50, 0.05, 0.3, 0.5, z, scheme="exact")[:, -1]
        manual.append(np.exp(-0.05 * 0.5) * np.maximum(terminal - 50, 0).mean())
    np.testing.assert_allclose(out["estimates"], manual, rtol=0, atol=1e-12)
    assert out["child_seeds"] == seeds
    assert out["child_spawn_keys"] == [None] * 4
    replay = r.rqmc_gbm_call_from_seeds(_contract(), power=4, child_seeds=seeds)
    np.testing.assert_allclose(out["estimates"], replay["estimates"], rtol=0, atol=1e-12)
    changed = r.rqmc_gbm_call_from_seeds(_contract(), power=4, child_seeds=[59, 61, 67, 71])
    assert not np.allclose(out["estimates"], changed["estimates"], rtol=0, atol=1e-12)


def test_child_metadata_is_preserved_without_mutating_input():
    from hullkit import _rqmc_ci as r

    metadata = [
        {
            "seed": 41,
            "raw_seed": 39,
            "retry_count": 1,
            "spawn_key": [0, 1],
            "candidate_seeds": [39, 41],
        },
        {
            "seed": 43,
            "raw_seed": 43,
            "retry_count": 0,
            "spawn_key": [1, 0],
            "candidate_seeds": [43],
        },
    ]
    saved = deepcopy(metadata)
    out = r.rqmc_gbm_call_from_seeds(
        _contract(), power=4, child_seeds=[41, 43], child_metadata=metadata
    )
    assert out["child_metadata"] == saved
    assert out["child_spawn_keys"] == [[0, 1], [1, 0]]
    out["child_metadata"][0]["spawn_key"].append(42)
    assert metadata == saved


@pytest.mark.parametrize("metadata", [[], [{"seed": 41}], [{"seed": 41}, {"seed": 44}]])
def test_metadata_length_or_seed_mismatch_is_rejected(metadata):
    from hullkit import _rqmc_ci as r

    with pytest.raises(ValueError):
        r.rqmc_gbm_call_from_seeds(
            _contract(), power=4, child_seeds=[41, 43], child_metadata=metadata
        )


def test_clip_and_endpoint_counts_are_recorded(monkeypatch):
    from hullkit import _numerical_mc as numerical
    from hullkit import _rqmc_ci as r
    from scipy.stats import norm

    uniform = np.array([[0.0], [0.25], [0.75], [1.0]])
    lo, hi = np.nextafter(0.0, 1.0), np.nextafter(1.0, 0.0)
    supplied = {"uniforms": uniform, "normals": norm.ppf(np.clip(uniform, lo, hi))}
    monkeypatch.setattr(numerical, "sobol_normal_points", lambda *args, **kwargs: supplied)
    out = r.rqmc_gbm_call_from_seeds(_contract(), power=2, child_seeds=[41, 43])
    assert out["uniform_clip"] == pytest.approx([lo, hi], abs=0, rel=0)
    assert out["uniform_clip_hex"] == [float(lo).hex(), float(hi).hex()]
    assert out["clipped_points"] == 4
    assert out["clipped_points_by_scramble"] == [2, 2]
    assert out["uniform_zero_points"] == 2
    assert out["uniform_one_points"] == 2
    assert out["uniform_zero_points_by_scramble"] == [1, 1]
    assert out["uniform_one_points_by_scramble"] == [1, 1]
    assert out["scipy_version"]
    assert np.all(np.isfinite(out["estimates"]))


def test_zero_volatility_and_nonzero_yield_are_replayed():
    from hullkit import _rqmc_ci as r
    from hullkit._multilevel_mc import GBMCall

    c = GBMCall(100, 90, 0.05, 0, 0.5, 0.02)
    out = r.rqmc_gbm_call_from_seeds(c, power=0, child_seeds=[0, 2**32 - 1])
    price = np.exp(-0.05 * 0.5) * max(100 * np.exp((0.05 - 0.02) * 0.5) - 90, 0)
    np.testing.assert_allclose(out["estimates"], price, rtol=0, atol=1e-12)
    assert out["degenerate"] is True
    assert out["width"] == pytest.approx(0)
    assert out["points_per_scramble"] == 1


@pytest.mark.parametrize(
    "keyword,bad",
    [
        ("power", -1),
        ("power", 21),
        ("power", True),
        ("power", 2.5),
        ("scrambles", 1),
        ("scrambles", 1025),
        ("scrambles", True),
        ("scrambles", 2.5),
        ("seed", -1),
        ("seed", 2**32),
        ("seed", True),
        ("seed", 3.5),
    ],
)
def test_legacy_wrapper_rejects_invalid_mathematical_controls(keyword, bad):
    from hullkit import _rqmc_ci as r

    kwargs = {"power": 4, "scrambles": 4, "seed": 21708}
    kwargs[keyword] = bad
    with pytest.raises(ValueError):
        r.rqmc_gbm_call(_contract(), **kwargs)


@pytest.mark.parametrize("seeds", [[41], [41, 41], [True, 43], [-1, 43], [2**32, 43], [3.5, 43]])
def test_direct_seam_rejects_insufficient_duplicate_or_invalid_child_seeds(seeds):
    from hullkit import _rqmc_ci as r

    with pytest.raises(ValueError):
        r.rqmc_gbm_call_from_seeds(_contract(), power=4, child_seeds=seeds)


def test_scramble_timings_separate_generation_payoff_and_statistics():
    from hullkit import _rqmc_ci as r
    from hullkit._multilevel_mc import GBMCall

    result = r.rqmc_gbm_call_from_seeds(
        GBMCall(100, 100, 0.03, 0.2, 1), power=3, child_seeds=[101, 103, 107, 109]
    )
    timing = result["timing"]
    assert all(
        np.isfinite(timing[k]) and timing[k] >= 0
        for k in ["rng_s", "engine_s", "summary_s", "overhead_s", "wall_s"]
    )
    total = sum(timing[k] for k in ["rng_s", "engine_s", "summary_s", "overhead_s"])
    assert total == pytest.approx(timing["wall_s"], rel=1e-12, abs=1e-12)
