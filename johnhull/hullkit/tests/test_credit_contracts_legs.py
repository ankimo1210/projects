"""Hull Tables25.1–5 all printed cells; independent default-state cashflow enumeration."""

import math

import numpy as np
import pytest
from hullkit import _credit_contracts as c

PRINTED = {
    "survival": [0.9802, 0.9608, 0.9418, 0.9231, 0.9048],
    "interval_pd": [0.0198, 0.0194, 0.0190, 0.0186, 0.0183],
    "end_discount": [0.9512, 0.9048, 0.8607, 0.8187, 0.7788],
    "annuity_rows": [0.9324, 0.8694, 0.8106, 0.7558, 0.7047],
    "protection_expected": [0.0119, 0.0116, 0.0114, 0.0112, 0.0110],
    "mid_discount": [0.9753, 0.9277, 0.8825, 0.8395, 0.7985],
    "protection_rows": [0.0116, 0.0108, 0.0101, 0.0094, 0.0088],
    "accrual_expected": [0.0099, 0.0097, 0.0095, 0.0093, 0.0091],
    "accrual_rows": [0.0097, 0.0090, 0.0084, 0.0078, 0.0073],
    "binary_rows": [0.0193, 0.0180, 0.0168, 0.0157, 0.0146],
}


def test_source_all_61_printed_values():
    table = c.cds_leg_table(0.02, 0.4, 0.05, 5)
    for key, printed in PRINTED.items():
        assert table[key] == pytest.approx(printed, abs=0.00005)
    assert table["annuity"] == pytest.approx(4.0728, abs=0.00005)
    assert table["accrual"] == pytest.approx(0.0422, abs=0.00005)
    assert table["protection"] == pytest.approx(0.0506, abs=0.00005)
    assert table["binary_protection"] == pytest.approx(0.0844, abs=0.00005)
    assert table["risky_duration"] == pytest.approx(4.1150, abs=0.00005)
    assert table["par_spread"] * 10000 == pytest.approx(123, abs=0.5)
    premium = table["risky_duration"] * 0.015
    assert premium == pytest.approx(0.0617, abs=0.00005)
    assert premium - table["protection"] == pytest.approx(0.0111, abs=0.00005)
    assert table["protection"] - premium == pytest.approx(-0.0111, abs=0.00005)
    calibrated = c.calibrated_cds(0.01, 0.4, 0.05, 5)
    assert calibrated["hazard"] * 100 == pytest.approx(1.63, abs=0.005)
    assert table["binary_protection"] / table["risky_duration"] * 10000 == pytest.approx(
        205, abs=0.5
    )


def test_default_year_enumeration_reconstructs_premium_and_protection_legs():
    table = c.cds_leg_table(0.02, 0.4, 0.05, 5)
    duration, protection = 0, 0
    for year in range(1, 6):
        probability = math.exp(-0.02 * (year - 1)) - math.exp(-0.02 * year)
        premium_path = sum(math.exp(-0.05 * j) for j in range(1, year)) + 0.5 * math.exp(
            -0.05 * (year - 0.5)
        )
        duration += probability * premium_path
        protection += probability * 0.6 * math.exp(-0.05 * (year - 0.5))
    duration += math.exp(-0.1) * sum(math.exp(-0.05 * j) for j in range(1, 6))
    assert table["risky_duration"] == pytest.approx(duration)
    assert table["protection"] == pytest.approx(protection)


def test_exponential_default_time_mc_with_midpoint_settlement_six_se():
    table = c.cds_leg_table(0.02, 0.4, 0.05, 5)
    tau = np.random.default_rng(252).exponential(50, size=120000)
    mid = np.floor(tau) + 0.5
    default = tau < 5
    protection = np.where(default, 0.6 * np.exp(-0.05 * mid), 0)
    premiums = (tau[:, None] > np.arange(1, 6)) * np.exp(-0.05 * np.arange(1, 6))
    duration = premiums.sum(axis=1) + np.where(default, 0.5 * np.exp(-0.05 * mid), 0)
    for sample, exact in [(protection, table["protection"]), (duration, table["risky_duration"])]:
        assert sample.mean() == pytest.approx(
            exact, abs=6 * np.std(sample, ddof=1) / np.sqrt(len(tau))
        )


def test_recovery_recalibration_keeps_quote_and_changes_binary_spread():
    result = c.recovery_recalibration(0.01, [0, 0.4, 0.8], 0.05, 5, contract_spread=0.015)
    assert result["par_spreads"] == pytest.approx([0.01] * 3, abs=1e-12)
    assert result["binary_spreads"] == pytest.approx([0.01, 0.01 / 0.6, 0.05], rel=1e-10)
    assert np.all(np.diff(result["hazards"]) > 0)
    assert np.ptp(result["buyer_values"]) / abs(result["buyer_values"][1]) < 0.15
    assert np.ptp(result["buyer_values"]) > 0  # near-insensitivity is not exact invariance
