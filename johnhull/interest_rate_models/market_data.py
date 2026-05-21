"""
market_data.py — Common market yield curve data for interest rate model comparison.

Four stylized curve patterns:
    - normal   : upward-sloping (typical expansion)
    - inverted : downward-sloping (rate-hike / recession fears)
    - flat     : nearly flat (transition / QE environment)
    - humped   : peak at 2-3Y (uncertainty / policy pivot)
"""
import numpy as np
import pandas as pd

# Tenors in years
TENORS = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])

# Zero rates (annualized, in decimal, e.g. 0.03 = 3%)
ZERO_RATES: dict[str, np.ndarray] = {
    "normal": np.array([
        0.0175, 0.0200, 0.0230, 0.0270, 0.0300,
        0.0340, 0.0365, 0.0390, 0.0430, 0.0450,
    ]),
    "inverted": np.array([
        0.0510, 0.0500, 0.0480, 0.0450, 0.0420,
        0.0380, 0.0355, 0.0330, 0.0310, 0.0300,
    ]),
    "flat": np.array([
        0.0290, 0.0295, 0.0300, 0.0305, 0.0308,
        0.0310, 0.0312, 0.0315, 0.0318, 0.0320,
    ]),
    "humped": np.array([
        0.0220, 0.0260, 0.0310, 0.0380, 0.0400,
        0.0390, 0.0375, 0.0355, 0.0330, 0.0320,
    ]),
}

CURVE_LABELS = {
    "normal":   "通常型（右肩上がり）",
    "inverted": "逆イールド（右肩下がり）",
    "flat":     "フラット型",
    "humped":   "ハンプト型（中期ピーク）",
}

CURVE_COLORS = {
    "normal":   "#1f77b4",
    "inverted": "#d62728",
    "flat":     "#2ca02c",
    "humped":   "#ff7f0e",
}


def discount_factors(pattern: str) -> np.ndarray:
    """Return discount factors P(0,T) = exp(-r(T)*T) for the given curve pattern."""
    r = ZERO_RATES[pattern]
    return np.exp(-r * TENORS)


def instantaneous_forward(pattern: str) -> np.ndarray:
    """
    Return instantaneous forward rate f(0,T) at each tenor using finite differences.
    f(0,T) ≈ -d/dT [log P(0,T)] = r(T) + T * dr(T)/dT
    Gradient is computed with numpy.gradient on TENORS.
    """
    r = ZERO_RATES[pattern]
    dr_dT = np.gradient(r, TENORS)
    return r + TENORS * dr_dT


def to_dataframe(pattern: str | None = None) -> pd.DataFrame:
    """
    Return a DataFrame with columns: tenor, zero_rate, discount_factor, fwd_rate.
    If pattern is None, return all four patterns stacked with a 'pattern' column.
    """
    if pattern is not None:
        df = pd.DataFrame({
            "tenor": TENORS,
            "zero_rate": ZERO_RATES[pattern],
            "discount_factor": discount_factors(pattern),
            "fwd_rate": instantaneous_forward(pattern),
        })
        df["pattern"] = pattern
        return df

    frames = []
    for p in ZERO_RATES:
        frames.append(to_dataframe(p))
    return pd.concat(frames, ignore_index=True)
