"""Private Hull Ch9 XVA conventions and illustrative funding/incremental calculations.

No unconditional claim that all adjustment components belong in a fair price.
"""

import numpy as np


def _conditional_loss_sum(default_probs, losses):
    """Sum unconditional interval PD times discounted conditional loss, with no extra LGD."""
    q = np.asarray(default_probs, dtype=float)
    v = np.asarray(losses, dtype=float)
    if (
        q.ndim != 1
        or q.shape != v.shape
        or not np.isfinite(q).all()
        or not np.isfinite(v).all()
        or np.any(q < 0)
        or q.sum() > 1 + 1e-10
        or np.any(v < 0)
    ):
        raise ValueError(
            "paired nonnegative losses and interval probabilities totalling at most one required"
        )
    return float(q @ v)


def credit_adjustments(
    default_probs,
    discounted_conditional_losses,
    *,
    own_default_probs=None,
    own_losses=None,
    risk_free_value=0,
):
    """CVA/DVA and risk-free-CVA+DVA using already discounted loss-given-default inputs.

    q values are unconditional interval default probabilities; v values are expected
    losses conditional on default in that interval, with LGD and discount embedded.
    Conditional loss permits wrong-way risk; unconditional EE substitution needs
    an independence model. No first-to-default bilateral model is inferred.
    """
    if not np.isfinite(risk_free_value) or (own_default_probs is None) != (own_losses is None):
        raise ValueError("finite base value and paired own-credit inputs required")
    cva = _conditional_loss_sum(default_probs, discounted_conditional_losses)
    dva = 0 if own_default_probs is None else _conditional_loss_sum(own_default_probs, own_losses)
    return {"cva": cva, "dva": dva, "adjusted_value": risk_free_value - cva + dva}


def credit_rate_offsets(fair_rate, payer_quote, receiver_quote):
    """Hull's negotiation rate differences in bp; these are not CVA currency amounts."""
    if not np.isfinite([fair_rate, payer_quote, receiver_quote]).all():
        raise ValueError("finite rate quotes required")
    return ((fair_rate - payer_quote) * 1e4, (receiver_quote - fair_rate) * 1e4)
