"""Finite-difference DV01 and partition-of-unity key-rate risk."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from .curve import ZeroCurve
from .pricing import fixed_receiver_pv


KEY_NODES = np.array([2.0, 5.0, 10.0, 30.0])


def key_rate_weights(maturity_years: np.ndarray, key_index: int) -> np.ndarray:
    """Piecewise-linear hats that sum to one, with flat endpoint tails."""
    t = np.asarray(maturity_years, dtype=float)
    if not 0 <= key_index < len(KEY_NODES):
        raise IndexError("invalid key-rate index")
    weights = np.zeros_like(t)
    if key_index == 0:
        weights[t <= KEY_NODES[0]] = 1.0
        mask = (t > KEY_NODES[0]) & (t < KEY_NODES[1])
        weights[mask] = (KEY_NODES[1] - t[mask]) / (KEY_NODES[1] - KEY_NODES[0])
        return weights
    if key_index == len(KEY_NODES) - 1:
        weights[t >= KEY_NODES[-1]] = 1.0
        mask = (t > KEY_NODES[-2]) & (t < KEY_NODES[-1])
        weights[mask] = (t[mask] - KEY_NODES[-2]) / (KEY_NODES[-1] - KEY_NODES[-2])
        return weights
    left, center, right = KEY_NODES[key_index - 1 : key_index + 2]
    left_mask = (t > left) & (t <= center)
    right_mask = (t > center) & (t < right)
    weights[left_mask] = (t[left_mask] - left) / (center - left)
    weights[right_mask] = (right - t[right_mask]) / (right - center)
    return weights


def _sensitivity(row: pd.Series, curve: ZeroCurve, shape: Callable[[np.ndarray], np.ndarray], bump: float = 1e-4) -> float:
    down = lambda t: -bump * shape(t)
    up = lambda t: bump * shape(t)
    return (fixed_receiver_pv(row, curve, down) - fixed_receiver_pv(row, curve, up)) / 2.0


def instrument_risk(rows: pd.DataFrame, curve: ZeroCurve, bump: float = 1e-4) -> pd.DataFrame:
    records = []
    parallel = lambda t: np.ones_like(np.asarray(t, dtype=float))
    for _, row in rows.iterrows():
        keys = [_sensitivity(row, curve, lambda t, i=i: key_rate_weights(t, i), bump) for i in range(4)]
        records.append(
            {
                "instrument_id": row["instrument_id"],
                "dv01": _sensitivity(row, curve, parallel, bump),
                "key_2y": keys[0],
                "key_5y": keys[1],
                "key_10y": keys[2],
                "key_30y": keys[3],
            }
        )
    return pd.DataFrame(records)


def risk_validation(rows: pd.DataFrame, curve: ZeroCurve) -> dict[str, float | bool]:
    full = instrument_risk(rows, curve, 1e-4)
    half = instrument_risk(rows, curve, 0.5e-4)
    key_sum = full[["key_2y", "key_5y", "key_10y", "key_30y"]].sum(axis=1).to_numpy()
    dv01 = full["dv01"].to_numpy()
    half_equivalent = 2.0 * half["dv01"].to_numpy()
    scale = np.maximum(np.abs(dv01), 1e-8)
    key_error = float(np.max(np.abs(key_sum - dv01) / scale))
    half_error = float(np.max(np.abs(half_equivalent - dv01) / scale))
    return {
        "max_key_sum_relative_error": key_error,
        "max_half_bump_relative_error": half_error,
        "key_sum_consistent": key_error < 5e-4,
        "finite_difference_consistent": half_error < 5e-4,
    }
