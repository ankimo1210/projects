"""Private Hull Ch8 waterfall fractions, separated from credit/default probabilities."""

import numpy as np


def _loss_fractions(pool_loss, sizes):
    """Junior-to-senior loss fractions at a given pool loss, using attachment widths."""
    widths = np.asarray(sizes, dtype=float)
    loss = np.asarray(pool_loss, dtype=float)
    if (
        widths.shape != (3,)
        or not np.isfinite(widths).all()
        or np.any(widths <= 0)
        or not np.isclose(widths.sum(), 1)
        or not np.isfinite(loss).all()
        or np.any((loss < 0) | (loss > 1))
    ):
        raise ValueError("three positive sizes summing to one and losses in [0,1] required")
    attach = np.r_[0, np.cumsum(widths)[:-1]]
    return np.clip((loss[..., None] - attach) / widths, 0, 1)


def abs_cdo_losses(asset_loss, *, abs_sizes=(0.05, 0.15, 0.8), cdo_sizes=(0.1, 0.25, 0.65)):
    """First ABS and resecuritized mezzanine losses, each normalized by its own pool.

    Sizes are junior/mezzanine/senior. All ABS pools share the same underlying
    loss fraction, a strong illustrative assumption with no rating/PD inference.
    """
    first = _loss_fractions(asset_loss, abs_sizes)
    second = _loss_fractions(first[..., 1], cdo_sizes)
    return {
        "abs_losses": first,
        "cdo_losses": second,
        "aaa_fraction": abs_sizes[2] + abs_sizes[1] * cdo_sizes[2],
        "senior_asset_attachment": abs_sizes[0] + abs_sizes[1] * (cdo_sizes[0] + cdo_sizes[1]),
    }


def priority_payments(available_cash, seniority_claims):
    """Distribute cash senior-first, retaining excess beyond all stated claims."""
    claims = np.asarray(seniority_claims, dtype=float)
    if (
        claims.ndim != 1
        or not np.isfinite(claims).all()
        or np.any(claims < 0)
        or not np.isfinite(available_cash)
        or available_cash < 0
    ):
        raise ValueError("nonnegative finite cash/claims required")
    prior = np.cumsum(claims) - claims
    paid = np.clip(available_cash - prior, 0, claims)
    return {"payments": paid, "excess": max(available_cash - float(claims.sum()), 0)}
