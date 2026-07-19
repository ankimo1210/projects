"""Automatic-differentiation Greeks for dimensionless pricing policies."""

from __future__ import annotations

import torch

from .pricing_policy import GREEK_NAMES


def autodiff_greeks(model, inputs: torch.Tensor, *, create_graph=False):
    """Return delta/gamma/vega/theta/rho from a scalar price head."""
    values = inputs.detach().clone().requires_grad_(True)
    price = model(values)
    first = torch.autograd.grad(price.sum(), values, create_graph=True)[0]
    delta = first[:, 0]
    gamma = torch.autograd.grad(delta.sum(), values, create_graph=create_graph, retain_graph=True)[
        0
    ][:, 0]
    result = {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "vega": first[:, 4],
        "theta": -first[:, 1],
        "rho": first[:, 2],
    }
    if not create_graph:
        result = {name: value.detach() for name, value in result.items()}
    return result


def direct_autodiff_consistency(model, inputs: torch.Tensor):
    """Mean absolute gap between direct Greek heads and autodiff Greeks."""
    price, direct = model.components(inputs)
    if direct is None:
        raise ValueError("model has no direct Greek heads")
    auto = autodiff_greeks(model, inputs)
    direct_map = {name: direct[:, index] for index, name in enumerate(GREEK_NAMES)}
    return {
        name: float(torch.mean(torch.abs(direct_map[name].detach() - auto[name])).cpu())
        for name in GREEK_NAMES
    } | {"price_mean": float(price.detach().mean().cpu())}
