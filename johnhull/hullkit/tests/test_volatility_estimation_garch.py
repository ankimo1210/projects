"""Hull Example23.2, finite GARCH history and EWMA limit."""

import numpy as np
import pytest
from hullkit import _volatility_estimation as v


def test_example_23_2_long_run_and_daily_update():
    info = v.garch_characteristics(0.000002, 0.13, 0.86)
    assert info["long_weight"] == pytest.approx(0.01)
    assert info["long_variance"] == pytest.approx(0.0002)
    assert np.sqrt(info["long_variance"]) == pytest.approx(0.014, abs=0.0005)
    update = v.garch_forecasts([-0.01], 0.000002, 0.13, 0.86, initial=0.016**2)[1]
    assert update == pytest.approx(0.00023516)
    assert np.sqrt(update) == pytest.approx(0.0153, abs=0.00005)
    assert info["diffusion_mean_reversion"] == pytest.approx(0.01)
    assert info["diffusion_vol_of_variance"] == pytest.approx(0.13 * np.sqrt(2))


def test_beta_history_expansion_is_not_persistence_power():
    u = np.array([0.01, -0.025, 0.005, 0.02])
    omega, alpha, beta, initial = 0.000002, 0.13, 0.86, 0.0003
    n = len(u)
    independent = beta**n * initial + sum(beta**j * omega for j in range(n))
    independent += sum(alpha * beta ** (n - i - 1) * x * x for i, x in enumerate(u))
    assert v.garch_forecasts(u, omega, alpha, beta, initial=initial)[-1] == pytest.approx(
        independent
    )
    assert v.garch_expanded(u, omega, alpha, beta, initial=initial) == pytest.approx(independent)
    assert v.garch_characteristics(omega, alpha, beta)["persistence"] == pytest.approx(0.99)


def test_ewma_limit_has_no_finite_long_run_value():
    u = [0.01, -0.02, 0.03]
    ewma = v.ewma_forecasts(u, initial=0.0004, decay=0.94)
    garch = v.garch_forecasts(u, 0, 0.06, 0.94, initial=0.0004)
    assert ewma == pytest.approx(garch)
    assert v.garch_characteristics(0, 0.06, 0.94)["long_variance"] is None
    with pytest.raises(ValueError):
        v.garch_forecasts(u, -0.00001, 0.1, 0.8, initial=0.0004)
