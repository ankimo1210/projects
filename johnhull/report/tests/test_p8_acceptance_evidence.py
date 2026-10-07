"""Raw P8 evidence must support a gate even when aggregate flags are forged."""

import json
from pathlib import Path

import numpy as np
import pytest

from johnhull.scripts.build_frontier_artifacts import FILES
from johnhull.scripts.frontier_acceptance import evaluate_acceptance

ROOT = Path(__file__).resolve().parents[3] / "johnhull/volumes"


def load_volume(volume):
    slug, metrics_file, arrays_file = (
        ("18_ml_surrogates", "pricing_metrics.json", "pricing_slices.npz")
        if volume == 18
        else FILES[volume]
    )
    folder = ROOT / slug / "reference"
    metrics = json.loads((folder / metrics_file).read_text())["metrics"]
    with np.load(folder / arrays_file, allow_pickle=False) as stored:
        arrays = {name: stored[name].copy() for name in stored.files}
    return metrics, arrays


def failures(volume, metrics, arrays):
    return {
        check["name"]
        for check in evaluate_acceptance(volume, metrics, arrays)["checks"]
        if not check["passed"]
    }


@pytest.mark.parametrize("volume", [18, 19, 20, 21, 22])
def test_raw_evidence_baseline(volume):
    metrics, arrays = load_volume(volume)
    assert not failures(volume, metrics, arrays)


def test_residual_fake_aggregate_is_rejected():
    metrics, arrays = load_volume(18)
    metrics["heston_bsm_residual_mae"] = 0
    metrics["heston_raw_price_mae"] = 1
    assert "residual_baseline" in failures(18, metrics, arrays)


def test_hard_prediction_tamper_is_recomputed():
    metrics, arrays = load_volume(18)
    # Zero stored violations cannot excuse a price beyond the upper bound.
    arrays["hard_strike_prices"][:] = 2
    assert "hard_check_violations" in failures(18, metrics, arrays)


@pytest.mark.parametrize(
    "name",
    [
        "calibration_optimizer_status",
        "calibration_optimizer_nfev",
        "calibration_optimizer_residuals",
    ],
)
def test_calibration_aggregate_success_does_not_hide_raw_failure(name):
    metrics, arrays = load_volume(19)
    arrays[name][:] = 0
    assert metrics["forward_calibration"]["all_starts_successful"]
    assert "multi_start_calibration" in failures(19, metrics, arrays)


def test_timing_flag_cannot_hide_negative_raw_sample():
    metrics, arrays = load_volume(21)
    arrays["nested_mc_repeats_ns"][0, 0] = -1
    assert metrics["timing_nondeterministic"]
    assert "measured_cpu_timing" in failures(21, metrics, arrays)


def test_calendar_zero_count_cannot_hide_wrong_holiday():
    metrics, arrays = load_volume(22)
    arrays["calendar_holiday_ordinal"][:] += 1
    assert metrics["calendar_violations"] == 0
    assert "expiry_consistency" in failures(22, metrics, arrays)


def test_event_effect_standard_error_is_recomputed_from_pairs():
    metrics, arrays = load_volume(22)
    arrays["event_effect_paired_se"][:] = 0
    assert "event_teacher_uncertainty" in failures(22, metrics, arrays)


@pytest.mark.parametrize(
    "name",
    [
        "economic_forecast_volatility",
        "economic_stock_positions",
        "economic_pnl",
    ],
)
def test_model_horizon_economics_is_connected_to_forecasts_and_trades(name):
    metrics, arrays = load_volume(20)
    arrays[name].flat[0] += 0.1
    assert "economic_comparison_controls" in failures(20, metrics, arrays)


@pytest.mark.parametrize(
    ("volume", "key"),
    [
        (18, "heston_raw_prediction"),
        (18, "hard_spot_gamma"),
        (19, "calibration_optimizer_status"),
        (20, "economic_shocks"),
        (21, "nested_mc_repeats_ns"),
        (22, "calendar_probe_seconds"),
    ],
)
def test_missing_audit_evidence_fails_gate(volume, key):
    metrics, arrays = load_volume(volume)
    del arrays[key]
    assert failures(volume, metrics, arrays)
