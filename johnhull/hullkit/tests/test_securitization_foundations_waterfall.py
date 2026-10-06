"""Hull Table8.1 all loss fractions and independent dollar-priority ledgers."""

import numpy as np
import pytest
from hullkit import _securitization_foundations as s


def test_source_all_sixteen_values_and_seven_relations():
    a = s.abs_cdo_losses([0.10, 0.13, 0.17, 0.20])
    assert 100 * a["abs_losses"][:, 1] == pytest.approx([33.3, 53.3, 80, 100], abs=0.05)
    assert 100 * a["cdo_losses"][:, 0] == pytest.approx([100] * 4)
    assert 100 * a["cdo_losses"][:, 1] == pytest.approx([93.3, 100, 100, 100], abs=0.05)
    assert 100 * a["cdo_losses"][:, 2] == pytest.approx([0, 28.2, 69.2, 100], abs=0.05)
    assert 100 * a["aaa_fraction"] == pytest.approx(90, abs=0.5)
    assert 100 * a["senior_asset_attachment"] == pytest.approx(10.25)
    mezz_threshold = a["senior_asset_attachment"] - 0.05
    assert [100 * mezz_threshold, 100 * mezz_threshold / 0.15] == pytest.approx([5.25, 35])
    assert [100 * (0.17 - 0.05), 100 * (0.17 - 0.05) / 0.15] == pytest.approx([12, 80])
    assert 100 * (0.8 - 0.35) / 0.65 == pytest.approx(69.2, abs=0.05)


def test_independent_dollar_losses_and_payment_priority():
    losses = [0.1, 0.13, 0.17, 0.2]
    a = s.abs_cdo_losses(losses)
    for i, loss in enumerate(losses):
        remaining = 100e6 * loss
        first = []
        for principal in [5e6, 15e6, 80e6]:
            assigned = min(remaining, principal)
            first.append(assigned)
            remaining -= assigned
        assert a["abs_losses"][i] == pytest.approx(np.array(first) / np.array([5e6, 15e6, 80e6]))
        second = []
        remaining = first[1]
        for principal in [1.5e6, 3.75e6, 9.75e6]:
            assigned = min(remaining, principal)
            second.append(assigned)
            remaining -= assigned
        assert a["cdo_losses"][i] == pytest.approx(
            np.array(second) / np.array([1.5e6, 3.75e6, 9.75e6])
        )
        assert sum(second) == pytest.approx(first[1])
    p = s.priority_payments(12, [8, 3, 2])
    assert p["payments"] == pytest.approx([8, 3, 1])
    assert sum(p["payments"]) + p["excess"] == pytest.approx(12)
    all_losses = s.abs_cdo_losses(np.linspace(0, 1, 101))
    assert all_losses["abs_losses"] @ np.array([0.05, 0.15, 0.8]) == pytest.approx(
        np.linspace(0, 1, 101)
    )
