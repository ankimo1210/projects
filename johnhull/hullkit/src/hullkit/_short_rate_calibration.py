"""Private Hull §32.6 single-curve Gaussian calibration and Bermudan basket.

All synthetic inputs must be labeled as such. Piecewise absolute short-rate
sigma differs from relative Black quote vol. The last sigma extends flat;
regularizers are discrete differences, not derivatives on an irregular grid.
"""

import math
from itertools import pairwise

import numpy as np
from scipy.optimize import brentq, least_squares

from ._calibrated_rate_tree import build_rate_tree, node_zero_bonds, rollback_option
from ._forward_black import forward_black_price
from ._short_rate_bond_options import gaussian_bond_option, jamshidian_coupon_option
from ._short_rate_models import mean_reversion_loading


def _vol_curve(knots, sigmas):
    t, s = np.asarray(knots, dtype=float), np.asarray(sigmas, dtype=float)
    if (
        t.ndim != 1
        or t.size < 2
        or t[0] != 0
        or np.any(np.diff(t) <= 0)
        or s.shape != (t.size - 1,)
        or np.any(s < 0)
    ):
        raise ValueError("increasing knots from zero and nonnegative interval sigmas required")
    return t, s


def piecewise_rate_variance(expiry, a, knots, sigmas):
    """Integral of sigma(u)^2 exp[-2a(expiry-u)]; last interval extends flat."""
    t, s = _vol_curve(knots, sigmas)
    if expiry < 0 or a < 0:
        raise ValueError("nonnegative expiry/a required")
    ends = np.r_[t[1:-1], max(t[-1], expiry)]
    result = 0.0
    for lo, hi, sigma in zip(t[:-1], ends, s, strict=True):
        hi = min(hi, expiry)
        if hi > lo:
            result += (
                sigma
                * sigma
                * math.exp(-2 * a * (expiry - hi))
                * mean_reversion_loading(2 * a, hi - lo)
            )
    return result


def diagonal_basket(
    exercise_times, final_maturity, fixed_rate, *, interval=1.0, kind="payer", notional=1.0
):
    """Single-curve co-terminal basket; §32.6 uses exercise 5..9, final 10."""
    if interval <= 0 or fixed_rate < 0 or notional <= 0 or kind not in ("payer", "receiver"):
        raise ValueError("positive period/notional, nonnegative coupon and valid kind required")
    rows = []
    for E in exercise_times:
        if E < 0 or final_maturity <= E:
            raise ValueError("exercise before final maturity required")
        count = math.ceil((final_maturity - E) / interval - 1e-12)
        pay = np.minimum(E + interval * np.arange(1, count + 1), final_maturity)
        rows.append(
            dict(
                expiry=float(E),
                payment_times=pay,
                accruals=np.diff(np.r_[E, pay]),
                fixed_rate=fixed_rate,
                kind=kind,
                notional=notional,
            )
        )
    return rows


def european_swaption(quote, discount_curve, a, knots, sigmas):
    """Positive coupon Jamshidian price under the expiry measure.

    Floating leg at exercise equals 1-P(E,end) for this single-curve par
    contract. critical_state is centered Gaussian state, not the short rate.
    """
    E = quote["expiry"]
    times = np.asarray(quote["payment_times"], dtype=float)
    alpha = np.asarray(quote["accruals"], dtype=float)
    K = quote["fixed_rate"]
    kind = quote.get("kind", "payer")
    N = quote.get("notional", 1.0)
    if (
        E < 0
        or times.ndim != 1
        or not times.size
        or alpha.shape != times.shape
        or np.any(np.diff(times) <= 0)
        or np.any(times <= E)
        or np.any(alpha <= 0)
        or K < 0
        or N <= 0
        or kind not in ("payer", "receiver")
    ):
        raise ValueError("valid positive future accruals, nonnegative coupon and notional required")
    q = piecewise_rate_variance(E, a, knots, sigmas)
    pe = float(discount_curve(E))
    ps = np.array([discount_curve(t) for t in times])
    if pe <= 0 or np.any(ps <= 0):
        raise ValueError("positive discounts required")
    bs = np.array([mean_reversion_loading(a, t - E) for t in times])
    cash = K * alpha
    cash[-1] += 1
    direction = "put" if kind == "payer" else "call"
    sign = -1 if kind == "payer" else 1
    if q == 0:
        return dict(
            price=N * pe * max(sign * (float(cash @ (ps / pe)) - 1), 0),
            variance=q,
            critical_state=None,
        )

    def bond(x, t):
        B = mean_reversion_loading(a, t - E)
        return discount_curve(t) / pe * math.exp(-B * x - 0.5 * q * B * B)

    def option(t, strike, option_kind):
        B = mean_reversion_loading(a, t - E)
        return forward_black_price(
            pe, discount_curve(t) / pe, strike, B * math.sqrt(q), 1, option_kind
        )

    keep = cash > 0
    row = jamshidian_coupon_option(E, times[keep], cash[keep], 1.0, bond, option, kind=direction)
    return dict(
        price=N * row["price"],
        variance=q,
        critical_state=row["critical_rate"],
        component_prices=N * row["component_prices"],
        bond_loadings=bs,
    )


def calibrate_gaussian(
    quotes,
    discount_curve,
    knots,
    initial_sigmas,
    a,
    *,
    fit_a=False,
    jump_weight=0.0,
    curvature_weight=0.0,
    quote_scale=None,
):
    """LM in log-positive parameters, squared price errors plus vol penalties.

    Price Jacobian diagnostics exclude penalty rows. Penalties do not make
    an underdetermined price basket identified. Start-dependent fits can be
    inspected by invoking this with several initial values.
    """
    t, s0 = _vol_curve(knots, initial_sigmas)
    count = s0.size + int(fit_a)
    if (
        np.any(s0 <= 0)
        or a < 0
        or (fit_a and a == 0)
        or min(jump_weight, curvature_weight) < 0
        or len(quotes) < count
    ):
        raise ValueError(
            "positive fitted parameters and at least as many prices as parameters required"
        )
    target = np.array([q["price"] for q in quotes])
    scale = float(max(np.max(abs(target)), 1e-12) if quote_scale is None else quote_scale)
    if scale <= 0:
        raise ValueError("positive quote price scale required")
    start = np.log(np.r_[a, s0] if fit_a else s0)

    def unpack(logs):
        values = np.exp(logs)
        return (float(values[0]), values[1:]) if fit_a else (a, values)

    def prices(logs):
        ar, ss = unpack(logs)
        return np.array([european_swaption(q, discount_curve, ar, t, ss)["price"] for q in quotes])

    def residual(logs):
        _, ss = unpack(logs)
        return np.r_[
            (prices(logs) - target) / scale,
            math.sqrt(jump_weight) * np.diff(ss / 0.01),
            math.sqrt(curvature_weight) * np.diff(ss / 0.01, n=2),
        ]

    result = least_squares(
        residual, start, method="lm", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=1000
    )
    ar, ss = unpack(result.x)
    pv = prices(result.x)
    h = 1e-5
    eye = np.eye(count) * h
    jac = np.column_stack(
        [(prices(result.x + d) - prices(result.x - d)) / (2 * h * scale) for d in eye]
    )
    return dict(
        a=ar,
        sigmas=ss,
        prices=pv,
        residuals=pv - target,
        price_sse=float(np.sum((pv - target) ** 2)),
        penalty_sse=float(
            jump_weight * np.sum(np.diff(ss / 0.01) ** 2)
            + curvature_weight * np.sum(np.diff(ss / 0.01, n=2) ** 2)
        ),
        price_jacobian_singular_values=np.linalg.svd(jac, compute_uv=False),
        success=bool(result.success),
        nfev=result.nfev,
    )


def implied_hw_caplet_sigma(expiry, payment, accrual, strike, black_vol, discount_curve, a):
    """Price roundtrip from Black quote to fixed-a constant HW absolute sigma."""
    if expiry <= 0 or payment <= expiry or accrual <= 0 or strike <= 0 or black_vol < 0 or a < 0:
        raise ValueError(
            "positive expiry/accrual/strike, later payment and nonnegative vol/a required"
        )
    pe, pu = discount_curve(expiry), discount_curve(payment)
    F = (pe / pu - 1) / accrual
    if F <= 0:
        raise ValueError("Black quote needs positive forward")
    target = accrual * forward_black_price(pu, F, strike, black_vol, expiry, "call")

    def price(s):
        return (1 + accrual * strike) * gaussian_bond_option(
            expiry, payment, a, s, pe, pu, 1 / (1 + accrual * strike), kind="put"
        )["price"]

    if abs(price(0) - target) < 1e-15:
        sigma = 0.0
    else:
        hi = 0.01
        while price(hi) < target:
            hi *= 2
            if hi > 100:
                raise ValueError("market price exceeds HW caplet attainable price")
        sigma = brentq(lambda s: price(s) - target, 0, hi, xtol=1e-14)
    return dict(sigma=sigma, black_price=target, hw_price=price(sigma), forward=F)


def bermudan_swaption(
    exercise_times,
    payment_times,
    accruals,
    fixed_rate,
    discount_curve,
    a,
    knots,
    sigmas,
    *,
    max_step=0.25,
    kind="payer",
    notional=1.0,
):
    """Single-curve co-terminal swaption with all cash/exercise/vol dates exact.

    Exercise at a reset uses only future fixed cashflows and a par floating
    leg. Off-reset exercise uses 1-P(t,end) too: this is a newly starting
    swap with the declared remaining fixed accruals, not a pre-existing swap
    with a known floating coupon. The finite-period tree is an approximation.
    """
    E = np.asarray(exercise_times, dtype=float)
    pay = np.asarray(payment_times, dtype=float)
    accr = np.asarray(accruals, dtype=float)
    t, s = _vol_curve(knots, sigmas)
    if (
        E.ndim != 1
        or not E.size
        or np.any(E < 0)
        or np.any(np.diff(E) <= 0)
        or pay.ndim != 1
        or not pay.size
        or pay.shape != accr.shape
        or np.any(np.diff(pay) <= 0)
        or np.any(accr <= 0)
        or E[-1] >= pay[-1]
        or max_step <= 0
        or fixed_rate < 0
        or notional <= 0
        or kind not in ("payer", "receiver")
    ):
        raise ValueError("increasing exercise/payment dates and valid accruals/contract required")
    events = np.unique(np.r_[0.0, E, pay, t[(t > 0) & (t < pay[-1])]])
    grid = [0.0]
    for lo, hi in pairwise(events):
        count = math.ceil((hi - lo) / max_step - 1e-12)
        grid.extend(lo + (hi - lo) * np.arange(1, count + 1) / count)

    def sigma(time):
        return float(s[min(np.searchsorted(t, time, side="right") - 1, s.size - 1)])

    tree = build_rate_tree(grid, discount_curve, a, sigma)
    end = int(np.argmin(abs(tree["times"] - E[-1])))
    zeros = node_zero_bonds(tree, pay, end)
    allowed = [int(np.argmin(abs(tree["times"] - e))) for e in E]
    intrinsic = [np.zeros(row["labels"].size) for row in tree["layers"][: end + 1]]
    for i in allowed:
        future = pay > tree["times"][i] + 1e-12
        cash = fixed_rate * accr[future]
        cash[-1] += 1
        bond = zeros[i][:, future] @ cash
        intrinsic[i] = notional * np.maximum((1 - bond) if kind == "payer" else (bond - 1), 0)
    row = rollback_option(tree, intrinsic, allowed)
    return dict(**row, tree=tree, exercise_times=E, intrinsic=intrinsic, exercise_indices=allowed)
