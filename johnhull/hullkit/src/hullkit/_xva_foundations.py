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


def funding_quote_arithmetic(
    receive_fixed,
    pay_fixed,
    funding_margin,
    collateral_margin,
    alternative_margin,
    risk_free_rate,
    bank_rate,
):
    """Four historical funding-rate arithmetic examples, not XVA present values."""
    if not np.isfinite(
        [
            receive_fixed,
            pay_fixed,
            funding_margin,
            collateral_margin,
            alternative_margin,
            risk_free_rate,
            bank_rate,
        ]
    ).all():
        raise ValueError("finite rates required")
    return {
        "swap_margin_bp": (receive_fixed - pay_fixed) * 1e4,
        "average_funding_bp": (funding_margin - collateral_margin) * 1e4,
        "marginal_funding_bp": (alternative_margin - collateral_margin) * 1e4,
        "merged_rate": (risk_free_rate + bank_rate) / 2,
    }


def funding_cash_costs(
    times,
    funding_balances,
    incremental_im,
    *,
    funding_spread,
    benefit_spread,
    im_spread,
    discounts=None,
):
    """Illustrative node-trapezoid FCA/FBA and signed incremental-IM funding cost.

    Positive funding balance needs borrowing; negative permits funding benefit.
    IM is a separate segregated account. A negative IM change can give negative
    MVA. These components are not automatically added to a fair derivative price;
    closeout, survival/default and funding-policy effects need a further model.
    """
    t = np.asarray(times, dtype=float)
    b = np.asarray(funding_balances, dtype=float)
    im = np.asarray(incremental_im, dtype=float)
    df = np.ones_like(t) if discounts is None else np.asarray(discounts, dtype=float)
    spreads = [
        np.broadcast_to(np.asarray(value, dtype=float), t.shape)
        for value in [funding_spread, benefit_spread, im_spread]
    ]
    if (
        t.ndim != 1
        or len(t) < 2
        or b.shape != t.shape
        or im.shape != t.shape
        or df.shape != t.shape
        or not all(np.isfinite(value).all() for value in [t, b, im, df, *spreads])
        or np.any(t < 0)
        or np.any(np.diff(t) <= 0)
        or np.any(df <= 0)
    ):
        raise ValueError(
            "aligned finite funding/IM profiles and positive ordered discount grid required"
        )
    integrands = [
        np.maximum(b, 0) * spreads[0] * df,
        np.maximum(-b, 0) * spreads[1] * df,
        im * spreads[2] * df,
    ]
    totals = [float(np.sum((value[:-1] + value[1:]) * 0.5 * np.diff(t))) for value in integrands]
    fca, fba, mva = totals
    return {"fca": fca, "fba": fba, "fva": fca - fba, "mva": mva}
