"""Black--Scholes call price and delta utilities."""

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
) -> float | np.ndarray:
    """Return the Black--Scholes price of a non-dividend-paying call."""
    s, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(maturity, dtype=float))
    intrinsic = np.maximum(s - strike, 0.0)
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    sqrt_tau = np.sqrt(safe_tau)
    d1 = (
        np.log(s / strike) + (risk_free_rate + 0.5 * volatility**2) * safe_tau
    ) / (volatility * sqrt_tau)
    d2 = d1 - volatility * sqrt_tau
    live_price = s * ndtr(d1) - strike * np.exp(-risk_free_rate * safe_tau) * ndtr(d2)
    result = np.where(tau > 0, live_price, intrinsic)
    return float(result) if result.ndim == 0 else result


def call_delta(
    spot: float | np.ndarray,
    strike: float,
    maturity: float | np.ndarray,
    risk_free_rate: float,
    volatility: float,
) -> float | np.ndarray:
    """Return Black--Scholes call delta, explicitly handling expiry."""
    s, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(maturity, dtype=float))
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    d1 = (
        np.log(s / strike) + (risk_free_rate + 0.5 * volatility**2) * safe_tau
    ) / (volatility * np.sqrt(safe_tau))
    result = np.where(tau > 0, ndtr(d1), _expiry_delta_numpy(s, strike))
    return float(result) if result.ndim == 0 else result


def torch_call_delta(
    spot: torch.Tensor,
    strike: float,
    maturity: float | torch.Tensor,
    risk_free_rate: float,
    volatility: float,
) -> torch.Tensor:
    """Torch-vectorized Black--Scholes call delta."""
    tau = torch.as_tensor(maturity, dtype=spot.dtype, device=spot.device)
    tau = torch.broadcast_to(tau, spot.shape)
    safe_tau = torch.clamp(tau, min=torch.finfo(spot.dtype).eps)
    d1 = (
        torch.log(torch.clamp(spot, min=torch.finfo(spot.dtype).tiny) / strike)
        + (risk_free_rate + 0.5 * volatility**2) * safe_tau
    ) / (volatility * torch.sqrt(safe_tau))
    live_delta = torch.special.ndtr(d1)
    expiry_delta = torch.where(
        spot > strike,
        torch.ones_like(spot),
        torch.where(spot < strike, torch.zeros_like(spot), torch.full_like(spot, 0.5)),
    )
    return torch.where(tau > 0, live_delta, expiry_delta)
