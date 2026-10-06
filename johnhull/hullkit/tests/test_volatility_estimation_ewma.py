"""Hull Example23.1 and finite-history EWMA expansion."""

import numpy as np
import pytest
from hullkit import _volatility_estimation as v


def test_example_23_1_one_day_update():
    forecasts = v.ewma_forecasts([0.02], decay=0.9, initial=0.01**2)
    assert forecasts == pytest.approx([0.0001, 0.00013])
    assert np.sqrt(forecasts[-1]) == pytest.approx(0.0114, abs=0.00005)


def test_finite_geometric_history_preserves_initial_term():
    history = np.array([0.01, -0.03, 0.02, 0.005])
    for decay in [0, 0.5, 0.94, 1]:
        initial = 0.0002
        recurrence = v.ewma_forecasts(history, decay=decay, initial=initial)[-1]
        n = len(history)
        independent = decay**n * initial + (1 - decay) * sum(
            decay ** (n - i - 1) * value**2 for i, value in enumerate(history)
        )
        assert recurrence == pytest.approx(independent)
        assert v.ewma_expanded(history, decay=decay, initial=initial) == pytest.approx(independent)


def test_forecast_before_return_and_faster_response_with_smaller_decay():
    old = v.ewma_forecasts([0.01, 0.01, 0.05, 0.01], initial=0.0001)
    new = v.ewma_forecasts([0.01, 0.01, 5, 0.01], initial=0.0001)
    assert old[:3] == pytest.approx(new[:3])
    fast = v.ewma_forecasts([0.05], decay=0.5, initial=0.0001)[-1]
    slow = v.ewma_forecasts([0.05], decay=0.99, initial=0.0001)[-1]
    assert fast > slow
