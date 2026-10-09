"""Independent error, coverage and resource-accounting contracts for RB-F08."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


def analytics():
    path = Path(__file__).resolve().parents[2] / "research/RB-F08/analytics.py"
    spec = importlib.util.spec_from_file_location("rbf08_analytics", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_rmse_across_original_runs_and_mse_decomposition():
    r = analytics().error_summary(np.array([9.0, 10.0, 11.0, 12.0]), 10.0)
    assert r["bias"] == pytest.approx(0.5)
    assert r["rmse"] == pytest.approx(np.sqrt(1.5))
    assert r["mse"] == pytest.approx(r["bias"] ** 2 + r["empirical_variance"])
    assert r["sample_variance"] == pytest.approx(5 / 3)
    assert r["trials"] == 4


def test_coverage_inclusive_endpoints_and_degenerate_trials():
    r = analytics().coverage_summary(
        np.array([[8.0, 9.0], [9.0, 11.0], [10.0, 10.0], [11.0, 13.0]]), 10.0
    )
    assert r["hits"] == 2 and r["trials"] == 4
    assert r["coverage"] == pytest.approx(0.5)
    assert r["mean_width"] == pytest.approx(1.25)
    assert r["degenerate"] == 1
    z = 1.959963984540054
    half = z * np.sqrt(0.25 / 4 + z * z / (4 * 16)) / (1 + z * z / 4)
    assert r["wilson95"] == pytest.approx([0.5 - half, 0.5 + half])


@pytest.mark.parametrize("hits", [0, 4])
def test_wilson_all_misses_and_all_hits(hits):
    intervals = np.repeat([[0.0, 1.0]] if hits else [[2.0, 3.0]], 4, axis=0)
    r = analytics().coverage_summary(intervals, 0.5)
    assert r["hits"] == hits
    assert 0 <= r["wilson95"][0] < r["wilson95"][1] <= 1
    if hits == 0:
        assert r["wilson95"][1] > 0
    else:
        assert r["wilson95"][0] < 1


def test_shared_pilot_not_multiplied_by_runs():
    p = dict(pilot_s=2.0, calibration_s=1.0, allocation_s=0.5, freeze_validation_s=0.25)
    r = analytics().cost_account(p, [dict(main_s=4.0), dict(main_s=6.0)])
    assert r["experiment_s"] == pytest.approx(13.75)
    assert r["cold_mean_s"] == pytest.approx(8.75)
    assert r["amortized_mean_s"]["10"] == pytest.approx(5.375)


def test_expenses_unique_and_method_specific():
    p = {
        "expenses": [
            dict(expense_id="euler", seconds=3.0, methods=["mlmc", "plain_euler"], epsilons=[0.1]),
            dict(expense_id="beta", seconds=1.0, methods=["exact_cv"], epsilons=[0.1]),
            dict(expense_id="shared", seconds=0.5, methods=["mlmc", "exact_cv"], epsilons=[0.1]),
            dict(expense_id="shared", seconds=0.5, methods=["mlmc", "exact_cv"], epsilons=[0.1]),
        ]
    }
    runs = [
        dict(main_s=2.0, method="mlmc", epsilon=0.1),
        dict(main_s=4.0, method="exact_cv", epsilon=0.1),
    ]
    total = analytics().cost_account(p, runs)
    assert total["experiment_s"] == pytest.approx(10.5)
    mlmc = analytics().cost_account(p, runs, method="mlmc", epsilon=0.1)
    cv = analytics().cost_account(p, runs, method="exact_cv", epsilon=0.1)
    assert mlmc["cold_mean_s"] == pytest.approx(5.5)
    assert cv["cold_mean_s"] == pytest.approx(5.5)
    assert mlmc["expense_ids"] == ["euler", "shared"]


@pytest.mark.parametrize(
    "p",
    [
        dict(pilot_s=-1.0, calibration_s=1.0, allocation_s=0.0, freeze_validation_s=0.0),
        dict(pilot_s=1.0, calibration_s=1.0),
        {
            "expenses": [
                dict(expense_id="a", seconds=1.0, methods=["mlmc"]),
                dict(expense_id="a", seconds=2.0, methods=["mlmc"]),
            ]
        },
    ],
)
def test_invalid_offline_account_rejected(p):
    with pytest.raises(ValueError):
        analytics().cost_account(p, [dict(main_s=1.0)])


@pytest.mark.parametrize("values", [[np.nan, 1.0], [], [np.inf]])
def test_missing_error_trials_are_not_filtered(values):
    with pytest.raises(ValueError):
        analytics().error_summary(np.array(values), 1.0)


@pytest.mark.parametrize("intervals", [[[np.nan, 1.0]], [[2.0, 1.0]], []])
def test_missing_or_reversed_intervals_are_not_filtered(intervals):
    with pytest.raises(ValueError):
        analytics().coverage_summary(np.array(intervals), 1.0)


@pytest.mark.parametrize("ratio,supported", [(0.5, True), (1.2, False)])
def test_paired_ratio_bootstrap_uses_all_runs_and_fixed_seed(ratio, supported):
    r = analytics().paired_ratio_bootstrap(
        np.full(8, ratio), np.ones(8), seed=83701, resamples=2000
    )
    assert r["median_ratio"] == pytest.approx(ratio)
    assert r["interval95"] == pytest.approx([ratio, ratio])
    assert (r["interval95"][1] < 1) is supported
    replay = analytics().paired_ratio_bootstrap(
        np.full(8, ratio), np.ones(8), seed=83701, resamples=2000
    )
    assert replay == r


def decision_fixture(ratio):
    parameters = dict(spot=100.0, strike=100.0, rate=0.03, sigma=0.2, maturity=1.0, yield_rate=0.02)
    fine = np.array([[0.3, -0.2], [-3.0, 1.0], [0.4, 0.1], [0.0, 0.0]])
    coarse = fine.sum(axis=1, keepdims=True) / np.sqrt(2)
    discount = np.exp(-0.03)
    pf = discount * np.maximum(
        100 * np.prod(1 + 0.01 / 2 + 0.2 * np.sqrt(0.5) * fine, axis=1) - 100, 0
    )
    pc = discount * np.maximum(100 * (1 + 0.01 + 0.2 * coarse[:, 0]) - 100, 0)
    a = dict(zf=fine, zc=coarse, pf=pf, pc=pc)
    cells = []
    for index, epsilon in enumerate([0.4, 0.2, 0.1]):
        methods = {}
        for method, cost in [
            ("mlmc", ratio),
            ("plain_euler", 1.0),
            ("exact_plain", 0.1),
            ("exact_cv", 0.08),
        ]:
            key = f"{index}_{method}"
            a[key + "_prices"] = np.full(4, 10.0)
            a[key + "_seconds"] = np.full(4, cost)
            methods[method] = dict(prices_key=key + "_prices", seconds_key=key + "_seconds")
        cells.append(
            dict(
                epsilon=epsilon,
                status="valid",
                truth=10.0,
                bootstrap_seed=83701 + index,
                methods=methods,
            )
        )
    r = dict(
        offline_expenses=[dict(expense_id="fixture_setup", seconds=0.0, methods=["all"])],
        main_repetitions=4,
        bootstrap_resamples=2000,
        epsilons=[0.4, 0.2, 0.1],
        budget_cells=cells,
        coupling_diagnostic=dict(
            parameters=parameters,
            fine_normals_key="zf",
            coarse_normals_key="zc",
            fine_payoffs_key="pf",
            coarse_payoffs_key="pc",
        ),
    )
    return r, a


@pytest.mark.parametrize("ratio,supported", [(0.5, True), (1.2, False)])
def test_decision_recomputed_from_raw_cost_and_price_arrays(ratio, supported):
    r, a = decision_fixture(ratio)
    r["decision"] = {"speedup_supported_vs_euler": not supported}
    out = analytics().decision(r, a)
    assert out["speedup_supported_vs_euler"] is supported
    assert out["coupling_verified"] is True
    assert out["standard_accelerator_rejected"] is True
    assert out["supported_epsilon_count"] == (3 if supported else 0)


def test_decision_coupling_and_roster_tamper_rejected():
    r, a = decision_fixture(0.5)
    a["zc"] = a["zc"] + 0.01
    with pytest.raises(ValueError, match="coupling"):
        analytics().decision(r, a)
    r, a = decision_fixture(0.5)
    a["0_mlmc_prices"] = np.full(3, 10.0)
    with pytest.raises(ValueError, match="roster"):
        analytics().decision(r, a)


def test_failed_budget_kept_with_reason():
    r, a = decision_fixture(0.5)
    r["budget_cells"][0] = dict(epsilon=0.4, status="failed", reason="bias_unresolved")
    out = analytics().decision(r, a)
    assert out["failed_cells"] == {"bias_unresolved": 1}
    assert out["speedup_supported_vs_euler"] is True
    r["budget_cells"][0].pop("reason")
    with pytest.raises(ValueError, match="reason"):
        analytics().decision(r, a)


def test_speed_comparison_requires_plain_euler_accuracy_too():
    r, a = decision_fixture(0.5)
    for cell in r["budget_cells"]:
        a[cell["methods"]["plain_euler"]["prices_key"]] = np.full(4, 20.0)
    out = analytics().decision(r, a)
    assert out["speedup_supported_vs_euler"] is False


def test_cold_pilot_disadvantage_is_not_hidden_by_main_speed():
    r, a = decision_fixture(0.1)
    for cell in r["budget_cells"]:
        a[cell["methods"]["exact_plain"]["seconds_key"]] = np.full(4, 2.0)
        a[cell["methods"]["exact_cv"]["seconds_key"]] = np.full(4, 2.0)
    r["offline_expenses"] = [
        dict(expense_id="euler_all_levels", seconds=100.0, methods=["mlmc", "plain_euler"]),
        dict(expense_id="exact_pilot", seconds=0.1, methods=["exact_plain", "exact_cv"]),
    ]
    out = analytics().decision(r, a)
    assert out["speedup_supported_vs_euler"] is True
    assert out["standard_accelerator_rejected"] is True
    assert any("cold" in reason for reason in out["rejection_reasons"])
    assert out["cells"][0]["cost_accounts"]["mlmc"]["cold_mean_s"] == pytest.approx(100.1)


def test_duplicate_epsilon_and_repeated_cell_do_not_count_as_three_successes():
    r, a = decision_fixture(0.5)
    r["epsilons"] = [0.4, 0.4, 0.4]
    r["budget_cells"] = [r["budget_cells"][0]] * 3
    with pytest.raises(ValueError, match=r"epsilon|roster"):
        analytics().decision(r, a)


def test_method_with_missing_required_offline_expenses_is_rejected():
    p = {"expenses": [dict(expense_id="beta", seconds=1.0, methods=["exact_cv"])]}
    with pytest.raises(ValueError, match=r"offline|expense"):
        analytics().cost_account(p, [dict(main_s=1.0, method="mlmc")], method="mlmc")
    r, a = decision_fixture(0.5)
    r.pop("offline_expenses", None)
    with pytest.raises(ValueError, match=r"offline|expense"):
        analytics().decision(r, a)


def test_inaccurate_exact_comparator_not_declared_faster_at_same_error():
    r, a = decision_fixture(0.5)
    for cell in r["budget_cells"]:
        for name in ["exact_plain", "exact_cv"]:
            a[cell["methods"][name]["prices_key"]] = np.full(4, 1000.0)
    out = analytics().decision(r, a)
    assert not any("faster" in reason or "cold" in reason for reason in out["rejection_reasons"])
    assert any("accuracy" in reason for reason in out["rejection_reasons"])


def test_saved_bootstrap_indices_recompute_without_new_randomness(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("artifact statistics must use saved bootstrap indices")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    indices = np.tile(np.arange(4), (8, 1))
    out = analytics().paired_ratio_bootstrap(
        np.array([0.2, 0.4, 0.6, 0.8]), np.ones(4), seed=83701, resamples=8, indices=indices
    )
    assert out["median_ratio"] == pytest.approx(0.5)
    assert out["interval95"] == pytest.approx([0.5, 0.5])


@pytest.mark.parametrize(
    "indices",
    [
        np.zeros((2, 3), dtype=int),
        np.full((2, 4), -1),
        np.full((2, 4), 4),
        np.zeros((2, 4), dtype=float),
    ],
)
def test_invalid_saved_bootstrap_indices_rejected(indices):
    with pytest.raises(ValueError, match="indices"):
        analytics().paired_ratio_bootstrap(
            np.ones(4), np.ones(4), seed=83701, resamples=2, indices=indices
        )
