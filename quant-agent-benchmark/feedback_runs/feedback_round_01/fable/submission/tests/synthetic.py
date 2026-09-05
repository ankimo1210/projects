"""Synthetic market generator for tests (known smooth curve, documented conventions)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantcurve.conventions import schedule_times

VALUATION = "2026-01-15"


def true_zero(t: np.ndarray, level: float = 0.02) -> np.ndarray:
    """Nelson-Siegel-like continuously compounded zero curve (can be negative)."""
    t = np.asarray(t, dtype=float)
    tau = 2.5
    x = np.where(t > 0, (1 - np.exp(-t / tau)) / np.maximum(t / tau, 1e-12), 1.0)
    return level + 0.012 * (1 - x) - 0.006 * (x - np.exp(-t / tau))


def true_discount(t, level: float = 0.02) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    return np.exp(-true_zero(t, level) * t)


def synthetic_frame(level: float = 0.02, noise_bp: float = 0.0, seed: int = 1, stub_rule: str = "forward") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    val = pd.Timestamp(VALUATION)

    def add(inst_type, T, quote, freq=1, coupon=np.nan, spread=0.002, liq=0.95, obs_prefix="OBS", src="VENUE_A", ts="2026-01-15T15:00:00Z", unit="PERCENT"):
        k = len(rows) + 1
        rows.append(
            {
                "obs_id": f"{obs_prefix}{k:04d}",
                "instrument_id": f"INS{k:04d}",
                "source": src,
                "timestamp": ts,
                "currency": "USD",
                "instrument_type": inst_type,
                "maturity_date": (val + pd.Timedelta(int(round(T * 365)), unit="D")).strftime("%Y-%m-%d"),
                "maturity_years": T,
                "start_years": 0,
                "coupon_rate": coupon,
                "payment_frequency": freq,
                "day_count": "ACT/365F",
                "quote_type": {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}[inst_type],
                "quote_value": quote,
                "quote_unit": unit,
                "bid": quote - spread / 2,
                "ask": quote + spread / 2,
                "liquidity_score": liq,
                "settlement_days": 2,
            }
        )

    for T in (1 / 12, 0.25, 0.5, 0.75, 1.0):
        for _ in range(2):
            r = (1 / true_discount(T, level) - 1) / T * 100
            add("deposit", T, r + rng.standard_normal() * noise_bp / 100)
    for T in (1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30):
        f = 1 if T <= 2 else 2
        times = schedule_times(T, f, stub_rule)
        par = (1 - true_discount(T, level)) / np.sum(true_discount(times, level) / f) * 100
        for _ in range(2):
            add("ois_swap", T, par + rng.standard_normal() * noise_bp / 100, freq=f, spread=0.003 if T < 20 else 0.01, liq=0.9 if T < 20 else 0.3)
    for T in np.linspace(1.6, 29.5, 20):
        c = 0.015 + 0.02 * rng.random()
        times = schedule_times(T, 2, stub_rule)
        price = np.sum(100 * c / 2 * true_discount(times, level)) + 100 * true_discount(T, level)
        add("bond", float(T), price + rng.standard_normal() * noise_bp / 100 * 0.08 * T, freq=2, coupon=c, spread=0.05, liq=0.7, unit="PRICE_POINTS")
    return pd.DataFrame(rows)
