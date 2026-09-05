"""Spread- and liquidity-aware observation scales shared by both models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .curve import ZeroCurve
from .instruments import Instrument
from .pricing import dollar_duration

MIN_LIQUIDITY = 0.05


def base_scales(table: pd.DataFrame, instruments: list[Instrument], reference: ZeroCurve, tau_bp: float = 0.5) -> np.ndarray:
    """Per-instrument noise scale in yield-equivalent decimal rate units.

    ``scale_i^2 = (hs_i^2 + tau^2) / (liq_i * rule_factor_i)`` where ``hs_i`` is
    the bid/ask half-spread expressed as a rate (bond half-spreads are divided
    by the dollar duration under ``reference``), ``tau`` is a floor that stops
    a zero spread from implying an infinitely precise quote, ``liq_i`` is the
    liquidity score (floored) and ``rule_factor_i`` collects rule-based
    down-weights from the cleaning stage. The inverse square of the scale is
    the base weight.
    """
    tau = tau_bp * 1e-4
    hs = table["half_spread_norm"].to_numpy(dtype=float).copy()
    types = table["instrument_type"].to_numpy()
    for j, inst in enumerate(instruments):
        if types[j] == "bond":
            hs[j] = hs[j] / max(dollar_duration(inst, reference), 1e-6)
        else:
            hs[j] = hs[j] / 100.0
    liq = np.maximum(table["liquidity"].to_numpy(dtype=float), MIN_LIQUIDITY)
    rule = np.clip(table["rule_factor"].to_numpy(dtype=float), 1e-3, 1.0)
    return np.sqrt((hs**2 + tau**2) / (liq * rule))
