from __future__ import annotations

import numpy as np
import pytest
from jhrmbs.metrics import (
    combine_competing_monthly_rates,
    cpr_to_smm,
    factor_implied_total_smm,
    psj_cpr,
    smm_to_cpr,
)


def test_cpr_smm_round_trip() -> None:
    cpr = np.array([0.0, 0.06, 0.25, 1.0])
    np.testing.assert_allclose(smm_to_cpr(cpr_to_smm(cpr)), cpr, atol=1e-12)


def test_standard_psj_uses_sixty_month_ramp() -> None:
    np.testing.assert_allclose(
        psj_cpr([0.0, 30.0, 60.0, 90.0], 0.06),
        [0.0, 0.03, 0.06, 0.06],
    )


def test_factor_implied_total_smm_after_scheduled_amortization() -> None:
    implied = factor_implied_total_smm([1.0], [0.891], [1.0], [0.9])
    np.testing.assert_allclose(implied, [0.01])


def test_competing_rates_combine_survival_probabilities() -> None:
    combined = combine_competing_monthly_rates(0.01, 0.02, 0.03)
    assert float(combined) == pytest.approx(1.0 - 0.99 * 0.98 * 0.97)


def test_rate_units_are_validated() -> None:
    with pytest.raises(ValueError, match="decimal units"):
        cpr_to_smm(6.0)
