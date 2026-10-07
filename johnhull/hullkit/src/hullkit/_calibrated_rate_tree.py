"""Private Hull §32.5 HW/BK two-stage trinomial curves and bond exercise.

Native tree rates are continuous finite-period R, not instantaneous r.
DG201 geometry matches Euler means/variances without negative-probability
fallback. Original benchmark mesh/date conventions are named separately.
"""

import math

import numpy as np
from scipy.optimize import brentq

from ._rate_tree import discounted_rollback, trinomial_branch
from ._short_rate_models import mean_reversion_loading


def _coefficient(value, time):
    return float(value(time) if callable(value) else value)


def _geometry(labels, spacing, a, sigma, delta, method, total_steps):
    if a < 0 or sigma < 0 or a * delta >= 1:
        raise ValueError("nonnegative a/sigma and Euler step a*dt<1 required")
    if sigma == 0:
        if labels.size != 1 or labels[0] != 0:
            raise ValueError("zero-vol step needs a deterministic state")
        return np.array([0]), 0.0, np.array([[0]]), np.array([[1.0]]), 0.0, 0.0
    next_spacing = sigma * math.sqrt(3 * delta)
    if method == "textbook":
        if spacing and not math.isclose(spacing, next_spacing, rel_tol=1e-12):
            raise ValueError("textbook geometry needs constant spacing; use dg201")
        jmax = math.floor(0.184 / (a * delta)) + 1 if a else total_steps + 1
        rows = [trinomial_branch(int(j), a, delta, jmax) for j in labels]
        child = np.array([row["successors"] for row in rows])
        p = np.array([row["probabilities"] for row in rows])
        bound = int(np.max(np.abs(child)))
        next_labels = np.arange(-bound, bound + 1)
        return next_labels, next_spacing, child + bound, p, 0.0, 0.0
    positive = labels[labels >= 0]
    mean = positive * spacing * (1 - a * delta)
    centers = np.floor(mean / next_spacing + 0.5).astype(int)
    candidate = centers[-1] - 1
    epsilon = mean[-1] / next_spacing - candidate
    pu = 0.5 * (1 / 3 + epsilon * epsilon + epsilon)
    pd = 0.5 * (1 / 3 + epsilon * epsilon - epsilon)
    if min(pu, 1 - pu - pd, pd) >= 0:
        centers[-1] = candidate
    if centers.size > 1:
        centers[-1] = max(centers[-1], centers[-2])
    epsilon = mean / next_spacing - centers
    pu = 0.5 * (1 / 3 + epsilon * epsilon + epsilon)
    pd = 0.5 * (1 / 3 + epsilon * epsilon - epsilon)
    probability = np.column_stack([pu, 1 - pu - pd, pd])
    if np.any(probability < -1e-12):
        raise ValueError("grid cannot represent nonnegative DG201 branch probabilities")
    probability = np.maximum(probability, 0)
    probability /= probability.sum(axis=1)[:, None]
    children = centers[:, None] + np.array([1, 0, -1])
    bound = int(centers[-1]) + 1
    next_labels = np.arange(-bound, bound + 1)
    successors = np.empty((labels.size, 3), dtype=int)
    p = np.empty((labels.size, 3))
    current_bound = int(labels[-1])
    positive_positions = positive + current_bound
    negative_positions = -positive + current_bound
    successors[positive_positions] = children + bound
    p[positive_positions] = probability
    successors[negative_positions] = -children + bound
    p[negative_positions] = probability
    mean_error = float(np.max(abs(np.sum(probability * children * next_spacing, axis=1) - mean)))
    variance_error = float(
        np.max(
            abs(
                np.sum(probability * (children * next_spacing - mean[:, None]) ** 2, axis=1)
                - sigma * sigma * delta
            )
        )
    )
    return next_labels, next_spacing, successors, p, mean_error, variance_error


def build_rate_tree(
    times,
    discount_curve,
    mean_reversion,
    volatility,
    *,
    model="hw",
    rate_shift=0.0,
    terminal_delta=None,
    geometry="dg201",
):
    """Centered geometry followed by exact Arrow-Debreu curve-shift fitting.

    Coefficients may be constants or time callbacks (frozen each interval).
    HW R=alpha+x allows negative rates. BK R=exp(alpha+x)-rate_shift needs
    every forward discount above its rate floor. No clipping changes that
    feasible domain. terminal_delta fits rates at the final row using the
    explicitly supplied next original curve knot without adding an unused
    branch. This matters for the DG201 Table32.3 terminal period (one day).
    """
    t = np.asarray(times, dtype=float)
    if (
        t.ndim != 1
        or t.size < 2
        or t[0] != 0
        or np.any(np.diff(t) <= 0)
        or model not in ("hw", "bk")
        or rate_shift < 0
        or geometry not in ("dg201", "textbook")
    ):
        raise ValueError("increasing grid starting at zero and valid model/geometry/shift required")
    if terminal_delta is not None and terminal_delta <= 0:
        raise ValueError("positive terminal period required")
    if not math.isclose(discount_curve(0), 1, abs_tol=1e-12):
        raise ValueError("initial discount must equal one")
    q = np.array([1.0])
    labels = np.array([0])
    spacing = 0.0
    layers = []
    residuals = []
    min_probability = 1.0
    mean_error = variance_error = 0.0
    steps = t.size - 1
    for i, time in enumerate(t):
        row = {
            "time": float(time),
            "labels": labels.copy(),
            "spacing": spacing,
            "states": labels * spacing,
            "state_prices": q.copy(),
        }
        if i == steps and terminal_delta is None:
            layers.append(row)
            break
        delta = float(t[i + 1] - time) if i < steps else terminal_delta
        target = float(discount_curve(time + delta))
        if target <= 0:
            raise ValueError("positive curve discounts required")
        states = row["states"]
        if model == "hw":
            alpha = math.log(float(q @ np.exp(-states * delta)) / target) / delta
            rates = alpha + states
        else:
            if target >= float(q.sum()) * math.exp(rate_shift * delta):
                raise ValueError("BK forward must be above minus the supplied rate shift")

            def residual(alpha, states=states, delta=delta, q=q, target=target):
                with np.errstate(over="ignore", under="ignore"):
                    discounts = np.exp(-(np.exp(alpha + states) - rate_shift) * delta)
                return float(q @ discounts) - target

            lo, hi = -40.0, 10.0
            while residual(lo) < 0:
                lo *= 2
            while residual(hi) > 0:
                hi *= 2
            alpha = brentq(residual, lo, hi, xtol=1e-14)
            rates = np.exp(alpha + states) - rate_shift
        discounts = np.exp(-rates * delta)
        row.update({"dt": delta, "alpha": alpha, "rates": rates, "discounts": discounts})
        residuals.append(float(q @ discounts) - target)
        if i < steps:
            a = _coefficient(mean_reversion, time)
            sigma = _coefficient(volatility, time)
            next_labels, next_spacing, successors, p, em, ev = _geometry(
                labels, spacing, a, sigma, delta, geometry, steps
            )
            row.update({"successors": successors, "probabilities": p})
            next_q = np.zeros(next_labels.size)
            np.add.at(next_q, successors.ravel(), ((q * discounts)[:, None] * p).ravel())
            q, labels, spacing = next_q, next_labels, next_spacing
            min_probability = min(min_probability, float(p.min()))
            mean_error = max(mean_error, em)
            variance_error = max(variance_error, ev)
        layers.append(row)
    return {
        "times": t,
        "layers": layers,
        "model": model,
        "rate_shift": rate_shift,
        "max_curve_residual": max(abs(x) for x in residuals),
        "min_probability": min_probability,
        "max_mean_error": mean_error,
        "max_variance_error": variance_error,
    }


def finite_period_gaussian_bond(
    time, maturity, period_rate, period_length, a, sigma, discount_curve
):
    """Hull32.15–17: unit bond from period R via A-tilde/B-tilde.

    Directly substituting R for instantaneous r in the Gaussian bond formula
    is incorrect. The given period must refer to P(time,time+period_length).
    """
    if min(time, a, sigma) < 0 or maturity < time or period_length <= 0:
        raise ValueError("valid nonnegative time/a/sigma and positive period required")
    B = mean_reversion_loading(a, maturity - time)
    Bd = mean_reversion_loading(a, period_length)
    variance = sigma * sigma * mean_reversion_loading(2 * a, time)
    p0 = float(discount_curve(time))
    pT = float(discount_curve(maturity))
    pd = float(discount_curve(time + period_length))
    if min(p0, pT, pd) <= 0:
        raise ValueError("positive discounts required")
    logA = math.log(pT / p0) - B / Bd * math.log(pd / p0) - 0.5 * variance * B * (B - Bd)
    value = np.exp(logA - period_length * B / Bd * np.asarray(period_rate, dtype=float))
    return float(value) if value.ndim == 0 else value


def bond_option_source_mesh(expiry, steps, payment_dates, *, post_step_limit=0.125):
    """DG201 equal-user-step benchmark convention, keeping actual cashflow dates.

    Rate dates up to expiry move to the nearest user node (earlier on ties).
    Post-expiry coupon gaps have floor(gap/limit)+1 subdivisions. Returned
    rate-date knots are separate from actual payment dates; moving one does
    not move the other. This is the declared benchmark convention, not a
    complete implementation of every source DataSetUp date option.
    """
    payments = np.asarray(payment_dates, dtype=float)
    if (
        expiry <= 0
        or steps < 1
        or post_step_limit <= 0
        or payments.ndim != 1
        or not payments.size
        or np.any(np.diff(payments) <= 0)
        or not np.any(payments > expiry)
    ):
        raise ValueError("valid expiry/steps and increasing payments beyond expiry required")
    user = np.arange(steps + 1, dtype=float) * (expiry / steps)
    rate_dates = sorted(
        set(float(user[np.argmin(abs(user - t))]) if t <= expiry else float(t) for t in payments)
    )
    times = list(user)
    previous = expiry
    for date in payments[payments > expiry]:
        count = math.floor((float(date) - previous) / post_step_limit) + 1
        delta = (float(date) - previous) / count
        times.extend(previous + k * delta for k in range(1, count + 1))
        previous = float(date)
    return np.array(times), np.array(rate_dates)


def node_zero_bonds(tree, maturities, until_row):
    """Conditional unit ZCBs by complete-tree rollback to matched grid maturities."""
    layers = tree["layers"]
    times = tree["times"]
    dates = np.asarray(maturities, dtype=float)
    if until_row < 0 or until_row >= len(layers):
        raise ValueError("valid output row required")
    result = [np.full((layers[i]["labels"].size, dates.size), np.nan) for i in range(until_row + 1)]
    for k, date in enumerate(dates):
        index = int(np.argmin(abs(times - date)))
        if abs(times[index] - date) > 1e-9:
            raise ValueError("zero bond maturity must be on the pricing grid")
        value = np.ones(layers[index]["labels"].size)
        for i in range(index, -1, -1):
            if i <= until_row:
                result[i][:, k] = value
            if i:
                row = layers[i - 1]
                value = row["discounts"] * np.sum(
                    row["probabilities"] * value[row["successors"]], axis=1
                )
    return result


def coupon_node_prices(tree, exercise_row, rate_dates, payment_dates, coupons, *, principal=100.0):
    """DG201 local-zero interpolation, with actual ex-coupon cashflow dates.

    Future ZCBs come from the full BK/HW tree, not an unrelated analytic
    surrogate. Each local curve adds the next-step finite-period R. Actual
    coupon dates remain unchanged even when its rate-date knot was moved.
    """
    pay, coupon = np.asarray(payment_dates, dtype=float), np.asarray(coupons, dtype=float)
    if (
        pay.ndim != 1
        or not pay.size
        or pay.shape != coupon.shape
        or np.any(np.diff(pay) <= 0)
        or principal < 0
    ):
        raise ValueError("matching increasing cashflow dates and nonnegative principal required")
    dates = np.asarray(rate_dates, dtype=float)
    zero_bonds = node_zero_bonds(tree, dates, exercise_row)
    rows = []
    for i in range(exercise_row + 1):
        row = tree["layers"][i]
        time = row["time"]
        next_date = tree["times"][i + 1]
        valid = dates >= time - 1e-12
        knots = dates[valid]
        remaining = knots - time
        yields = np.empty((row["labels"].size, knots.size))
        for k, h in enumerate(remaining):
            yields[:, k] = -np.log(zero_bonds[i][:, valid][:, k]) / h if h > 1e-12 else row["rates"]
        future = pay > time + 1e-12
        cash = coupon.copy()
        cash[-1] += principal
        cash = cash[future]
        payments = pay[future]
        prices = []
        for j, rate in enumerate(row["rates"]):
            curve = dict(zip(knots, yields[j], strict=True))
            curve[next_date] = rate
            local_dates = np.array(sorted(curve))
            local_rates = np.array([curve[d] for d in local_dates])
            rates = np.interp(payments, local_dates, local_rates)
            prices.append(float(cash @ np.exp(-rates * (payments - time))))
        rows.append(np.array(prices))
    return rows


def coupon_accrual(time, payment_dates, coupons, *, previous_coupon_date=0.0):
    """Cash strike accrual: coupon at the current date has already been paid."""
    dates = np.asarray(payment_dates, dtype=float)
    cash = np.asarray(coupons, dtype=float)
    if (
        dates.ndim != 1
        or dates.shape != cash.shape
        or not dates.size
        or np.any(np.diff(dates) <= 0)
        or time < previous_coupon_date
    ):
        raise ValueError("matching increasing coupon dates and valid current time required")
    next_index = int(np.searchsorted(dates, time + 1e-12, side="right"))
    if next_index == dates.size:
        return 0.0
    previous = previous_coupon_date if next_index == 0 else dates[next_index - 1]
    return float(cash[next_index] * (time - previous) / (dates[next_index] - previous))


def rollback_option(tree, intrinsic_values, exercise_indices):
    """European/Bermudan/American obstacle on the same fitted period-rate tree."""
    count = len(intrinsic_values) - 1
    allowed = set(exercise_indices)
    if count < 0 or count >= len(tree["layers"]) or any(i < 0 or i > count for i in allowed):
        raise ValueError("valid payoff levels and exercise indices required")
    layers = tree["layers"][: count + 1]
    payoff = (
        np.asarray(intrinsic_values[-1], dtype=float)
        if count in allowed
        else np.zeros(layers[-1]["labels"].size)
    )
    exercise = [
        np.asarray(intrinsic_values[i], dtype=float)
        if i in allowed
        else np.full(layers[i]["labels"].size, -np.inf)
        for i in range(count)
    ]
    values = discounted_rollback(
        [x["rates"] for x in layers[:-1]],
        [x["successors"] for x in layers[:-1]],
        [x["probabilities"] for x in layers[:-1]],
        [x["dt"] for x in layers[:-1]],
        payoff,
        exercise_values=exercise,
    )
    early = []
    for i, row in enumerate(layers[:-1]):
        continuation = row["discounts"] * np.sum(
            row["probabilities"] * values[i + 1][row["successors"]], axis=1
        )
        early.append(exercise[i] > continuation + 1e-12)
    early.append(np.zeros(layers[-1]["labels"].size, dtype=bool))
    return {"price": float(values[0][0]), "values": values, "early_exercise": early}
