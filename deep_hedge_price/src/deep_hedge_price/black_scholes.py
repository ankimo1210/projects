"""Vectorized Black--Scholes call price and analytic Greeks."""

from __future__ import annotations

import numpy as np
import torch
from scipy.special import ndtr


def _expiry_delta_numpy(spot: np.ndarray, strike: float) -> np.ndarray:
    return np.where(spot > strike, 1.0, np.where(spot < strike, 0.0, 0.5))


def call_price(
    spot: float | np.ndarray,
    strike: float,
    maturity: float | np.ndarray,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> float | np.ndarray:
    """Return a call price with explicit expiry and zero-volatility limits."""
    s, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(maturity, dtype=float))
    intrinsic = np.maximum(s - strike, 0.0)
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    sqrt_tau = np.sqrt(safe_tau)
    safe_vol = np.maximum(np.asarray(volatility, dtype=float), np.finfo(float).eps)
    d1 = (np.log(s / strike) + (risk_free_rate - dividend_yield + 0.5 * safe_vol**2) * safe_tau) / (
        safe_vol * sqrt_tau
    )
    d2 = d1 - safe_vol * sqrt_tau
    live_price = s * np.exp(-dividend_yield * safe_tau) * ndtr(d1) - strike * np.exp(
        -risk_free_rate * safe_tau
    ) * ndtr(d2)
    deterministic = np.maximum(
        s * np.exp(-dividend_yield * safe_tau) - strike * np.exp(-risk_free_rate * safe_tau),
        0.0,
    )
    live_price = np.where(volatility > 0, live_price, deterministic)
    result = np.where(tau > 0, live_price, intrinsic)
    return float(result) if result.ndim == 0 else result


def call_delta(
    spot: float | np.ndarray,
    strike: float,
    maturity: float | np.ndarray,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> float | np.ndarray:
    """Return Black--Scholes call delta, explicitly handling expiry."""
    s, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(maturity, dtype=float))
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    safe_vol = np.maximum(np.asarray(volatility, dtype=float), np.finfo(float).eps)
    d1 = (np.log(s / strike) + (risk_free_rate - dividend_yield + 0.5 * safe_vol**2) * safe_tau) / (
        safe_vol * np.sqrt(safe_tau)
    )
    live = np.exp(-dividend_yield * safe_tau) * ndtr(d1)
    deterministic = np.where(
        s * np.exp(-dividend_yield * safe_tau) > strike * np.exp(-risk_free_rate * safe_tau),
        np.exp(-dividend_yield * safe_tau),
        0.0,
    )
    live = np.where(volatility > 0, live, deterministic)
    result = np.where(tau > 0, live, _expiry_delta_numpy(s, strike))
    return float(result) if result.ndim == 0 else result


def _live_terms(spot, strike, maturity, risk_free_rate, volatility, dividend_yield):
    s, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(maturity, dtype=float))
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    safe_vol = np.maximum(np.asarray(volatility, dtype=float), np.finfo(float).eps)
    sqrt_tau = np.sqrt(safe_tau)
    d_1 = (
        np.log(s / strike) + (risk_free_rate - dividend_yield + 0.5 * safe_vol**2) * safe_tau
    ) / (safe_vol * sqrt_tau)
    d_2 = d_1 - safe_vol * sqrt_tau
    density = np.exp(-0.5 * d_1**2) / np.sqrt(2.0 * np.pi)
    return s, tau, safe_tau, sqrt_tau, safe_vol, d_1, d_2, density


def call_gamma(spot, strike, maturity, risk_free_rate, volatility, dividend_yield=0.0):
    """Return ``d²C/dS²`` in currency per spot squared."""
    s, tau, safe_tau, sqrt_tau, safe_vol, _d_1, _d_2, density = _live_terms(
        spot, strike, maturity, risk_free_rate, volatility, dividend_yield
    )
    value = np.exp(-dividend_yield * safe_tau) * density / (s * safe_vol * sqrt_tau)
    result = np.where((tau > 0) & (volatility > 0), value, 0.0)
    return float(result) if result.ndim == 0 else result


def call_vega(spot, strike, maturity, risk_free_rate, volatility, dividend_yield=0.0):
    """Return ``dC/dsigma`` per unit volatility."""
    s, tau, safe_tau, sqrt_tau, _safe_vol, _d_1, _d_2, density = _live_terms(
        spot, strike, maturity, risk_free_rate, volatility, dividend_yield
    )
    value = s * np.exp(-dividend_yield * safe_tau) * density * sqrt_tau
    result = np.where((tau > 0) & (volatility > 0), value, 0.0)
    return float(result) if result.ndim == 0 else result


def call_theta(spot, strike, maturity, risk_free_rate, volatility, dividend_yield=0.0):
    """Return calendar theta ``dC/dt`` per year."""
    s, tau, safe_tau, sqrt_tau, safe_vol, d_1, d_2, density = _live_terms(
        spot, strike, maturity, risk_free_rate, volatility, dividend_yield
    )
    value = (
        -s * np.exp(-dividend_yield * safe_tau) * density * safe_vol / (2 * sqrt_tau)
        - risk_free_rate * strike * np.exp(-risk_free_rate * safe_tau) * ndtr(d_2)
        + dividend_yield * s * np.exp(-dividend_yield * safe_tau) * ndtr(d_1)
    )
    deterministic_itm = s * np.exp(-dividend_yield * safe_tau) > strike * np.exp(
        -risk_free_rate * safe_tau
    )
    deterministic = np.where(
        deterministic_itm,
        dividend_yield * s * np.exp(-dividend_yield * safe_tau)
        - risk_free_rate * strike * np.exp(-risk_free_rate * safe_tau),
        0.0,
    )
    value = np.where(volatility > 0, value, deterministic)
    result = np.where(tau > 0, value, 0.0)
    return float(result) if result.ndim == 0 else result


def call_rho(spot, strike, maturity, risk_free_rate, volatility, dividend_yield=0.0):
    """Return ``dC/dr`` per unit continuously compounded rate."""
    s, tau, safe_tau, _sqrt_tau, _safe_vol, _d_1, d_2, _density = _live_terms(
        spot, strike, maturity, risk_free_rate, volatility, dividend_yield
    )
    value = strike * safe_tau * np.exp(-risk_free_rate * safe_tau) * ndtr(d_2)
    deterministic = np.where(
        s * np.exp(-dividend_yield * safe_tau) > strike * np.exp(-risk_free_rate * safe_tau),
        strike * safe_tau * np.exp(-risk_free_rate * safe_tau),
        0.0,
    )
    value = np.where(volatility > 0, value, deterministic)
    result = np.where(tau > 0, value, 0.0)
    return float(result) if result.ndim == 0 else result


def torch_call_delta(
    spot: torch.Tensor,
    strike: float,
    maturity: float | torch.Tensor,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> torch.Tensor:
    """Torch-vectorized Black--Scholes call delta."""
    tau = torch.as_tensor(maturity, dtype=spot.dtype, device=spot.device)
    tau = torch.broadcast_to(tau, spot.shape)
    safe_tau = torch.clamp(tau, min=torch.finfo(spot.dtype).eps)
    d1 = (
        torch.log(torch.clamp(spot, min=torch.finfo(spot.dtype).tiny) / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility**2) * safe_tau
    ) / (volatility * torch.sqrt(safe_tau))
    live_delta = torch.exp(-dividend_yield * safe_tau) * torch.special.ndtr(d1)
    expiry_delta = torch.where(
        spot > strike,
        torch.ones_like(spot),
        torch.where(spot < strike, torch.zeros_like(spot), torch.full_like(spot, 0.5)),
    )
    return torch.where(tau > 0, live_delta, expiry_delta)
