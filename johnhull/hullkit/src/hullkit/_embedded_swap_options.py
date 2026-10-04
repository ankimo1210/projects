"""Private Hull §34.5 daily binaries, cancelable swaps and compound state.

Known daily equality belongs to the binary complement (>= cutoff).
Black timing uses a declared frozen signed numeraire-ratio loading.
Compounding exercise immediately settles accumulated net interest. A small
full-history tree retains that state; the four-step spread proxy is separate.
"""

import math

import numpy as np
from scipy.special import ndtr

from ._compounding_swaps import compound_balances, compound_growth


def known_accrual_coupon(days, fixings, annual_coupon, notional, cutoff, basis, *, calendar):
    """Calendar-day coupon below cutoff, carrying preceding business fixing."""
    if basis <= 0 or notional < 0:
        raise ValueError("positive year basis/nonnegative notional required")
    refs = tuple(calendar.preceding(d) for d in days)
    rates = np.array([fixings(d) if callable(fixings) else fixings[d] for d in refs])
    count = int(np.sum(rates < cutoff))
    amount = annual_coupon * notional / basis
    return dict(
        coupon=amount * count,
        binary_savings=amount * (len(refs) - count),
        ordinary_coupon=amount * len(refs),
        accruing_days=count,
        reference_dates=refs,
    )


def rate_binary(
    amount,
    forward,
    strike,
    volatility,
    fixing,
    actual_discount,
    *,
    ratio_loading=0.0,
    correlation=0.0,
    below=False,
):
    """Pay amount at actual payment, using its DF and adjusted Black d2.

    ratio_loading belongs to the actual-vs-natural-payment measure change,
    and may have either sign. The drift adjustment is sigma*corr*loading*T.
    At zero vol/time the known indicator has strict < / complementary >=.
    """
    if (
        min(forward, strike, actual_discount) <= 0
        or min(amount, volatility, fixing) < 0
        or abs(correlation) > 1
    ):
        raise ValueError(
            "positive Black rates/discount, nonnegative amount/vol/time and valid correlation required"
        )
    adjusted = forward * math.exp(correlation * volatility * ratio_loading * fixing)
    w = volatility * math.sqrt(fixing)
    probability = (
        float(forward >= strike)
        if w == 0
        else float(ndtr((math.log(adjusted / strike) - 0.5 * w * w) / w))
    )
    if below:
        probability = 1 - probability
    return dict(
        price=amount * actual_discount * probability,
        probability=probability,
        adjusted_forward=adjusted,
    )


def cancellation_option_terms(receive_fixed, holder, exercise_times, final_maturity):
    """Opposite identical swap: own right long, counterparty right short."""
    E = np.asarray(exercise_times, dtype=float)
    if (
        holder not in ("owner", "counterparty")
        or E.ndim != 1
        or not E.size
        or np.any(E < 0)
        or np.any(E > final_maturity)
        or np.any(np.diff(E) <= 0)
    ):
        raise ValueError("valid holder and increasing exercise dates within tenor required")
    payer = receive_fixed if holder == "owner" else not receive_fixed
    return dict(
        kind="payer" if payer else "receiver",
        position="long" if holder == "owner" else "short",
        exercise_times=E,
        tenors=final_maturity - E,
    )


def cancelable_cashflow_tree(
    discounts,
    successors,
    probabilities,
    coupons,
    exercise_indices,
    *,
    holder="owner",
    terminal_payoff=None,
    exercise_settlements=None,
):
    """Cashflow then post-payment cancellation, max for owner/min for opponent.

    Coupons at the end of each interval are known at its start node (for
    child-dependent coupons supply their conditional probability-weighted expectation).
    Exercise settlements can include unpaid accrued balances. No cashflow is
    re-paid at exercise: continuation is valued after the preceding coupon.
    """
    n = len(discounts)
    allowed = set(exercise_indices)
    if (
        holder not in ("owner", "counterparty")
        or not n
        or len(successors) != n
        or len(probabilities) != n
        or len(coupons) != n
        or any(i < 0 or i > n for i in allowed)
    ):
        raise ValueError("matching tree intervals and valid holder/exercise indices required")
    last_size = int(np.max(successors[-1])) + 1
    values = [None] * (n + 1)
    decisions = [None] * (n + 1)
    values[-1] = (
        np.zeros(last_size) if terminal_payoff is None else np.asarray(terminal_payoff, dtype=float)
    )
    if values[-1].shape != (last_size,):
        raise ValueError("terminal payoff shape must match final nodes")
    settlements = (
        [np.zeros(np.asarray(d).size) for d in discounts] + [np.zeros(last_size)]
        if exercise_settlements is None
        else exercise_settlements
    )
    for i in reversed(range(n)):
        d = np.asarray(discounts[i], dtype=float)
        ch = np.asarray(successors[i], dtype=int)
        p = np.asarray(probabilities[i], dtype=float)
        cash = np.asarray(coupons[i], dtype=float)
        if np.any(d <= 0) or np.any(p < 0) or not np.allclose(p.sum(axis=1), 1, atol=1e-12):
            raise ValueError(
                "positive discounts and nonnegative probability rows summing to one required"
            )
        continuation = d * (cash + np.sum(p * values[i + 1][ch], axis=1))
        if i in allowed:
            exercise = np.asarray(settlements[i], dtype=float)
            values[i] = (
                np.maximum(continuation, exercise)
                if holder == "owner"
                else np.minimum(continuation, exercise)
            )
            decisions[i] = exercise > continuation if holder == "owner" else exercise < continuation
        else:
            values[i] = continuation
            decisions[i] = np.zeros(d.size, dtype=bool)
    return dict(price=float(values[0][0]), values=values, exercise_decisions=decisions)


def compounding_cancellation_tree(
    times,
    rate_at_history,
    notional,
    fixed_coupon,
    fixed_compound,
    exercise_indices,
    *,
    compound_spread=0.0,
    holder="owner",
    probability_up=0.5,
):
    """Small binary Q full-history tree; rates are annual simple interval rates.

    Receive floating/pay fixed; exercise pays Af-Afixed. Full history avoids
    combining different accrued balances that share the same current rate.
    At most 16 intervals; this is an independent-state teaching calculation,
    not a calibrated large Bermudan engine or continuous-time convergence.
    """
    ts = np.asarray(times, dtype=float)
    n = ts.size - 1
    if ts.ndim != 1 or n < 1 or n > 16 or ts[0] != 0 or np.any(np.diff(ts) <= 0) or notional <= 0:
        raise ValueError(
            "one to sixteen increasing intervals from zero and positive notional required"
        )
    if any(i < 0 or i > n for i in exercise_indices):
        raise ValueError("exercise indices must be on the tree")
    levels = [{(): dict(floating_balance=0.0, fixed_balance=0.0, settlement=0.0)}]
    discounts = []
    children = []
    probabilities = []
    cash = []
    settlements = []
    for i in range(n):
        prefixes = list(levels[i])
        delta = ts[i + 1] - ts[i]
        ds = []
        ps = []
        next_level = {}
        settlements.append(np.array([levels[i][p]["settlement"] for p in prefixes]))
        for prefix in prefixes:
            r = float(rate_at_history(prefix))
            up = float(probability_up(prefix) if callable(probability_up) else probability_up)
            if (
                not 0 <= up <= 1
                or min(1 + r * delta, 1 + (r + compound_spread) * delta, 1 + fixed_compound * delta)
                <= 0
            ):
                raise ValueError("valid Q branch probability and positive accrual factors required")
            state = levels[i][prefix]
            af = (
                state["floating_balance"] * (1 + (r + compound_spread) * delta)
                + notional * r * delta
            )
            ax = (
                state["fixed_balance"] * (1 + fixed_compound * delta)
                + notional * fixed_coupon * delta
            )
            for bit in (0, 1):
                next_level[(*prefix, bit)] = dict(
                    floating_balance=af, fixed_balance=ax, settlement=af - ax
                )
            ds.append(1 / (1 + r * delta))
            ps.append([1 - up, up])
        levels.append(next_level)
        discounts.append(np.array(ds))
        probabilities.append(np.array(ps))
        children.append(np.arange(2 ** (i + 1)).reshape(-1, 2))
        cash.append(np.zeros(2**i))
    terminal = np.array([s["settlement"] for s in levels[-1].values()])
    settlements.append(terminal)
    row = cancelable_cashflow_tree(
        discounts,
        children,
        probabilities,
        cash,
        exercise_indices,
        holder=holder,
        terminal_payoff=terminal,
        exercise_settlements=settlements,
    )
    return dict(**row, states=levels, times=ts)


def compounding_spread_proxy(
    forwards,
    accruals,
    notional,
    fixed_coupon,
    fixed_compound,
    final_discount,
    *,
    compound_spread=0.0,
    floating_balance=0.0,
    fixed_balance=0.0,
):
    """Hull four-step forward approximation; spread can change optimal exercise.

    Separate known accrued balances before comparing remaining fixed value
    with par. This approximation alone is not an exact Bermudan price.
    """
    r, a = np.asarray(forwards, dtype=float), np.asarray(accruals, dtype=float)
    if r.ndim != 1 or not r.size or r.shape != a.shape or notional <= 0 or final_discount <= 0:
        raise ValueError("matching forwards/accruals and positive notional/discount required")
    coupons = notional * r * a
    actual = (
        compound_balances(
            coupons, compound_growth(r, a, spread=compound_spread), initial_balance=floating_balance
        )[-1]
        * final_discount
    )
    no_spread = (
        compound_balances(coupons, compound_growth(r, a), initial_balance=floating_balance)[-1]
        * final_discount
    )
    spread = actual - no_spread
    fixed_final = compound_balances(
        notional * fixed_coupon * a,
        compound_growth(np.full(r.shape, fixed_compound), a),
        initial_balance=fixed_balance,
    )[-1]
    fixed_augmented = final_discount * (notional + fixed_final)
    proxy = fixed_augmented - fixed_balance - spread
    return dict(
        step1_floating_pv=actual,
        step2_no_spread_pv=no_spread,
        spread_pv=spread,
        fixed_remaining_proxy=proxy,
        continue_minus_cancel=notional - proxy,
        exercise_settlement=floating_balance - fixed_balance,
        method="four-step forward approximation; exercise spread impact omitted",
    )


def binary_payment_loading(
    fixing,
    natural_payment,
    actual_payment,
    rate_forward,
    rate_relative_volatility,
    *,
    frequency=1.0,
):
    """Frozen natural-to-actual ratio loading; actual payment may be earlier."""
    if (
        fixing < 0
        or min(natural_payment, actual_payment) < fixing
        or rate_relative_volatility < 0
        or frequency <= 0
        or 1 + rate_forward / frequency <= 0
    ):
        raise ValueError(
            "future payments, nonnegative rate vol and positive compounding base required"
        )
    return (
        -rate_relative_volatility
        * rate_forward
        * (actual_payment - natural_payment)
        / (1 + rate_forward / frequency)
    )
