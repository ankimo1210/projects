"""Differentiable soft constraints and the hullkit hard-check adapter."""

from __future__ import annotations

from typing import Any

import torch


def price_bound_penalty(prices, inputs):
    """Squared soft penalty for Merton lower/upper bound violations."""
    x, tau, rate, dividend, _sigma = inputs.unbind(dim=-1)
    discounted_spot = x * torch.exp(-dividend * tau)
    discounted_strike = torch.exp(-rate * tau)
    lower = torch.clamp(discounted_spot - discounted_strike, min=0.0)
    return torch.mean(torch.relu(lower - prices) ** 2 + torch.relu(prices - discounted_spot) ** 2)


def structured_surface_penalty(prices, *, spots=None, strikes=None, maturities=None):
    """Penalty on an explicitly structured 1D/2D tensor; no implicit sorting."""
    penalty = prices.new_zeros(())
    if spots is not None:
        if not torch.all(torch.diff(spots) > 0):
            raise ValueError("spot grid must be strictly increasing")
        penalty = penalty + torch.mean(torch.relu(-torch.diff(prices, dim=-1)) ** 2)
    if strikes is not None:
        if not torch.all(torch.diff(strikes) > 0):
            raise ValueError("strike grid must be strictly increasing")
        slopes = torch.diff(prices, dim=-1) / torch.diff(strikes)
        penalty = penalty + torch.mean(torch.relu(torch.diff(prices, dim=-1)) ** 2)
        penalty = penalty + torch.mean(torch.relu(-torch.diff(slopes, dim=-1)) ** 2)
    if maturities is not None:
        if not torch.all(torch.diff(maturities) > 0):
            raise ValueError("maturity grid must be strictly increasing")
        penalty = penalty + torch.mean(torch.relu(-torch.diff(prices, dim=-1)) ** 2)
    return penalty


def hard_validation_report(**kwargs: Any):
    """Evaluate via hullkit, with a clear optional-integration error."""
    try:
        from hullkit.surrogate_validation import (
            check_calendar_monotonicity,
            check_price_bounds,
            check_strike_convexity,
            check_strike_monotonicity,
            validation_report,
        )
    except ImportError as exc:  # pragma: no cover - exercised in isolated installs
        raise RuntimeError(
            "hullkit is required for hard pricing validation; install the hullkit workspace package"
        ) from exc
    tolerance = float(kwargs.pop("tolerance", 1e-8))
    checks = [
        check_price_bounds(
            kwargs["prices"],
            kwargs["spots"],
            kwargs["strikes"],
            kwargs["rates"],
            kwargs["maturities"],
            kwargs.get("dividends", 0.0),
            tolerance=tolerance,
        )
    ]
    if "strike_grid" in kwargs:
        checks.extend(
            (
                check_strike_monotonicity(
                    kwargs["surface_by_strike"], kwargs["strike_grid"], tolerance=tolerance
                ),
                check_strike_convexity(
                    kwargs["surface_by_strike"], kwargs["strike_grid"], tolerance=tolerance
                ),
            )
        )
    if "maturity_grid" in kwargs:
        checks.append(
            check_calendar_monotonicity(
                kwargs["surface_by_maturity"], kwargs["maturity_grid"], tolerance=tolerance
            )
        )
    return validation_report(*checks).to_dict()
