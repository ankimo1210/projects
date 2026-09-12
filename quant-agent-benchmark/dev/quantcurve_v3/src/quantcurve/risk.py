"""Receiver-fixed DV01 and key-rate sensitivities with finite-difference verification."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .curve import ZeroCurve, parallel_bump, tent_bump
from .instruments import Instrument
from .pricing import analytic_dv01, pv_receiver

KEY_TENORS = (2.0, 5.0, 10.0, 30.0)
BUMP_SHAPE_DOC = (
    "Key-rate bumps are piecewise-linear tents in the continuously compounded zero rate, "
    "centred at 2Y, 5Y, 10Y and 30Y, equal to one at the centre and zero at the neighbouring "
    "centres; the 2Y tent is flat (=1) before 2Y and the 30Y tent is flat after 30Y, so the "
    "four tents sum to one at every maturity (partition of unity) and the key-rate "
    "sensitivities aggregate to the parallel DV01 up to second-order convexity."
)


def _central(inst: Instrument, curve: ZeroCurve, shape, size: float) -> float:
    up = pv_receiver(inst, curve.bumped(lambda t, s=shape: size * s(t)))
    down = pv_receiver(inst, curve.bumped(lambda t, s=shape: -size * s(t)))
    return (down - up) / 2.0


def compute_risk(instruments: list[Instrument], curve: ZeroCurve, bump: float = 1e-4, key_tenors: tuple[float, ...] = KEY_TENORS) -> pd.DataFrame:
    """One row per instrument: DV01, key rates, and verification columns.

    ``dv01`` follows CONVENTIONS.md: ``(PV[-1bp] - PV[+1bp]) / 2`` for a
    parallel 1bp move of the zero curve, receiver-fixed, notional 1,000,000
    for deposits/swaps and face 100 for bonds.
    """
    centers = np.asarray(key_tenors, dtype=float)
    tents = [tent_bump(centers, k) for k in range(len(centers))]
    ones = parallel_bump(1.0)
    rows = []
    for inst in instruments:
        dv01 = _central(inst, curve, ones, bump)
        keys = [_central(inst, curve, tent, bump) for tent in tents]
        dv01_half = _central(inst, curve, ones, bump / 2.0) * 2.0
        analytic = analytic_dv01(inst, curve, bump)
        row = {
            "instrument_id": inst.instrument_id,
            "instrument_type": inst.instrument_type,
            "maturity_years": inst.maturity,
            "pv": pv_receiver(inst, curve),
            "dv01": dv01,
        }
        for tenor, value in zip(key_tenors, keys):
            row[f"key_{int(tenor)}y"] = value
        row["key_sum"] = float(np.sum(keys))
        row["analytic_dv01"] = analytic
        row["fd_vs_analytic_rel_diff"] = (dv01 - analytic) / analytic if analytic != 0 else np.nan
        row["key_sum_vs_dv01_rel_diff"] = (row["key_sum"] - dv01) / dv01 if dv01 != 0 else np.nan
        row["halfstep_vs_fullstep_rel_diff"] = (dv01_half - dv01) / dv01 if dv01 != 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def risk_verification_summary(risk: pd.DataFrame) -> dict:
    def maxabs(col: str) -> float | None:
        vals = risk[col].to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        return float(np.max(np.abs(vals))) if len(vals) else None

    return {
        "bump_shape": BUMP_SHAPE_DOC,
        "bump_size_bp": 1.0,
        "n_instruments": int(len(risk)),
        "max_abs_rel_diff_fd_vs_analytic": maxabs("fd_vs_analytic_rel_diff"),
        "max_abs_rel_diff_keysum_vs_dv01": maxabs("key_sum_vs_dv01_rel_diff"),
        "max_abs_rel_diff_halfstep_vs_fullstep": maxabs("halfstep_vs_fullstep_rel_diff"),
        "all_receiver_dv01_positive": bool((risk["dv01"] > 0).all()),
    }
