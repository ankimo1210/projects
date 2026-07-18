"""Scale-balanced price, Greek, and differential-learning losses."""

from __future__ import annotations

import torch


def scale_balanced_mse(prediction, target, scale):
    scale = torch.clamp(
        torch.as_tensor(scale, dtype=prediction.dtype, device=prediction.device), min=1e-12
    )
    return torch.mean(((prediction - target) / scale) ** 2)


def direct_greek_loss(prediction, target, scales):
    if prediction.shape != target.shape:
        raise ValueError("direct Greek prediction/target shapes differ")
    scales = torch.clamp(
        torch.as_tensor(scales, dtype=prediction.dtype, device=prediction.device), min=1e-12
    )
    return torch.mean(((prediction - target) / scales) ** 2)


def differential_delta_loss(price, inputs, analytic_delta, scale=1.0, *, create_graph=True):
    """DML loss for ``d(C/K)/d(S/K) = delta``."""
    derivative = torch.autograd.grad(
        price.sum(), inputs, create_graph=create_graph, retain_graph=True
    )[0][:, 0]
    return scale_balanced_mse(derivative, analytic_delta, scale), derivative


def price_and_greek_loss(
    price,
    target_price,
    *,
    price_scale,
    direct_greeks=None,
    target_greeks=None,
    greek_scales=None,
    inputs=None,
    target_delta=None,
    price_weight=1.0,
    greek_weight=0.0,
    differential_weight=0.0,
):
    losses = {"price": scale_balanced_mse(price, target_price, price_scale)}
    total = price_weight * losses["price"]
    if direct_greeks is not None and greek_weight > 0:
        losses["direct_greeks"] = direct_greek_loss(direct_greeks, target_greeks, greek_scales)
        total = total + greek_weight * losses["direct_greeks"]
    if differential_weight > 0:
        if inputs is None or target_delta is None:
            raise ValueError("differential loss requires inputs and target_delta")
        losses["differential_delta"], _ = differential_delta_loss(
            price, inputs, target_delta, greek_scales[0]
        )
        total = total + differential_weight * losses["differential_delta"]
    losses["total"] = total
    return losses
