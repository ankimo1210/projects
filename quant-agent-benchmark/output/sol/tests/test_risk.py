from __future__ import annotations

import numpy as np
import pandas as pd

from quantcurve.curve import ZeroCurve
from quantcurve.pricing import fixed_receiver_pv
from quantcurve.risk import instrument_risk, key_rate_weights, risk_validation


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"instrument_id": "D", "instrument_type": "deposit", "maturity_years": 1.0, "normalized_quote": 0.02, "payment_frequency": 1, "coupon_rate": np.nan},
            {"instrument_id": "S", "instrument_type": "ois_swap", "maturity_years": 10.0, "normalized_quote": 0.02, "payment_frequency": 2, "coupon_rate": np.nan},
            {"instrument_id": "B", "instrument_type": "bond", "maturity_years": 8.25, "normalized_quote": 101.0, "payment_frequency": 2, "coupon_rate": 0.025},
        ]
    )


def test_key_rate_shapes_partition_parallel_shift() -> None:
    grid = np.linspace(0, 35, 1000)
    total = sum(key_rate_weights(grid, index) for index in range(4))
    assert np.max(np.abs(total - 1.0)) < 1e-14


def test_dv01_matches_direct_central_difference() -> None:
    curve = ZeroCurve(np.array([0.0, 30.0]), np.array([0.02, 0.02]), method="pchip")
    rows = _rows()
    risk = instrument_risk(rows, curve).set_index("instrument_id")
    row = rows.iloc[1]
    up = lambda t: np.full_like(np.asarray(t, dtype=float), 1e-4)
    down = lambda t: np.full_like(np.asarray(t, dtype=float), -1e-4)
    expected = (fixed_receiver_pv(row, curve, down) - fixed_receiver_pv(row, curve, up)) / 2
    assert np.isclose(risk.loc["S", "dv01"], expected, rtol=0, atol=1e-10)


def test_key_rate_sensitivities_and_half_bump_consistency() -> None:
    curve = ZeroCurve(np.array([0.0, 30.0]), np.array([0.02, 0.02]), method="pchip")
    checks = risk_validation(_rows(), curve)
    assert checks["key_sum_consistent"]
    assert checks["finite_difference_consistent"]
