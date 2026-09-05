"""Receiver-fixed DV01 and key-rate sensitivities via finite-difference bumps.

DV01 = (PV[-1bp] - PV[+1bp]) / 2 on a parallel shift, per CONVENTIONS.md.
Key-rate bumps use local "tent" shapes centred at 2Y/5Y/10Y/30Y that sum
to exactly 1.0 at every maturity (a partition of unity: flat at 1 below
the first key rate, flat at 1 beyond the last, linear tents in between),
so summing the four key-rate DV01s reproduces the parallel DV01 by
construction, as required by CONVENTIONS.md.
"""

from __future__ import annotations

import numpy as np

from .cashflows import bond_pv, deposit_pv, swap_pv
from .curve import ShiftedCurve
from .grids import KEY_RATE_POINTS

DEFAULT_BUMP = 0.0001  # 1 basis point


def _pv(row, discount_fn) -> float:
    if row.instrument_type == "deposit":
        return deposit_pv(discount_fn, row.maturity_years, row.normalized_quote / 100.0)
    if row.instrument_type == "ois_swap":
        return swap_pv(discount_fn, row.maturity_years, int(row.payment_frequency), row.normalized_quote / 100.0)
    if row.instrument_type == "bond":
        return bond_pv(discount_fn, row.maturity_years, row.coupon_rate, int(row.payment_frequency), row.normalized_quote)
    raise ValueError(f"unsupported instrument_type: {row.instrument_type}")


def _parallel_shift(bump: float):
    return lambda t: np.full_like(np.atleast_1d(np.asarray(t, dtype=float)), bump)


def key_rate_bump_shape(t, key_index: int, keys: tuple = KEY_RATE_POINTS) -> np.ndarray:
    """Tent-shaped bump for key rate ``keys[key_index]``; sums to 1 across all keys."""
    tt = np.atleast_1d(np.asarray(t, dtype=float))
    k = keys[key_index]
    val = np.ones_like(tt)
    if key_index > 0:
        left = keys[key_index - 1]
        ramp_up = (tt - left) / (k - left)
        val = np.where(tt < k, np.clip(ramp_up, 0.0, 1.0), val)
        val = np.where(tt < left, 0.0, val)
    if key_index < len(keys) - 1:
        right = keys[key_index + 1]
        ramp_down = (right - tt) / (right - k)
        val = np.where(tt > k, np.clip(ramp_down, 0.0, 1.0), val)
        val = np.where(tt > right, 0.0, val)
    return val


def dv01(row, curve, bump: float = DEFAULT_BUMP) -> float:
    up = ShiftedCurve(curve, _parallel_shift(bump))
    down = ShiftedCurve(curve, _parallel_shift(-bump))
    return (_pv(row, down.discount) - _pv(row, up.discount)) / 2.0


def key_rate_sensitivities(row, curve, keys: tuple = KEY_RATE_POINTS, bump: float = DEFAULT_BUMP) -> dict:
    out = {}
    for i, k in enumerate(keys):
        def shift_up(t, i=i):
            return bump * key_rate_bump_shape(t, i, keys)

        def shift_down(t, i=i):
            return -bump * key_rate_bump_shape(t, i, keys)

        up = ShiftedCurve(curve, shift_up)
        down = ShiftedCurve(curve, shift_down)
        out[k] = (_pv(row, down.discount) - _pv(row, up.discount)) / 2.0
    return out


def risk_table(df_usable, curve, keys: tuple = KEY_RATE_POINTS, bump: float = DEFAULT_BUMP):
    records = []
    for row in df_usable.itertuples():
        krs = key_rate_sensitivities(row, curve, keys, bump)
        records.append(
            {
                "instrument_id": row.instrument_id,
                "dv01": dv01(row, curve, bump),
                "key_2y": krs[2.0],
                "key_5y": krs[5.0],
                "key_10y": krs[10.0],
                "key_30y": krs[30.0],
            }
        )
    return records
