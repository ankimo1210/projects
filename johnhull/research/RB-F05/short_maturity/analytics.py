"""Saved-only physical Greeks, strong C2 interpolation and study accounting.

No sampling, training or optimizer runs here. Raw errors retain original
rows; expiry ATM ordinary Greeks remain undefined. Hashes do not compare
financial values. The synthetic contract is fixed by the reviewed protocol.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from hullkit import _short_maturity_teachers as core
from scipy.interpolate import BPoly


def parameters(p):
    """Read the four fixed risk-neutral call parameters."""
    c = p["contract"]
    return core.CallParameters(c["rate"], c["dividend"], c["jump_mean"], c["jump_std"])


def states(inputs, p):
    """Build fixed UTC carry, trading variance and pulse states per plain row."""
    a = np.asarray(inputs, dtype=float)
    if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all():
        raise ValueError("finite [spot,seconds,event] rows required")
    if np.any(a[:, 0] <= 0) or np.any((a[:, 2] != 0) & (a[:, 2] != 1)):
        raise ValueError("positive spot and binary event required")
    expiry = datetime.fromisoformat(p["contract"]["expiry"])
    return [
        core.clock_state(
            expiry - timedelta(seconds=float(row[1])),
            expiry,
            event=bool(row[2]),
            volatility=p["clock"]["volatility"],
            weights=tuple(p["clock"]["weights"]),
        )
        for row in a
    ]


def oracle(inputs, p):
    """Return core count-mixture C/physical Delta/Gamma, preserving expiry NaN."""
    a = np.asarray(inputs, dtype=float)
    ps = parameters(p)
    return np.asarray(
        [
            core.mixture_values(
                row[0], p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
            )["values"]
            for row, state in zip(a, states(a, p), strict=True)
        ]
    ).reshape(-1, 3)


def spot_domain(p):
    """Cover fixed tails and full-session scaled ATM training/test geometry."""
    state = states([[p["contract"]["strike"], 390 * 60, 0]], p)[0]
    distance = max(0.05, 4 * np.sqrt(state.variance))
    return -float(distance), float(distance)


def build_hermite(p):
    """Tabulate C,C_x,C_xx for a C2 quintic spline in log spot.

    Time blending is affine in log seconds; this does not provide a Theta
    smoothness guarantee. Gamma uses the same interpolated scalar price.
    """
    g = p["hermite"]
    xs = np.linspace(*spot_domain(p), g["spot_nodes"])
    base_seconds = np.exp(np.linspace(np.log(60), np.log(390 * 60), g["time_nodes"]))
    # Fix known endpoints before union: exp(log(endpoint)) can round to a
    # distinct float whose log is identical, yielding a zero blend denominator.
    base_seconds[0], base_seconds[-1] = 60.0, 390 * 60.0
    seconds = np.unique(np.r_[base_seconds, np.asarray(g["include_minutes"]) * 60])
    ss = p["contract"]["strike"] * np.exp(xs)
    table = np.empty((2, len(seconds), len(xs), 3))
    ps = parameters(p)
    for event in [0, 1]:
        for j, t in enumerate(seconds):
            state = states([[ss[0], t, event]], p)[0]
            values = core.mixture_values(
                ss, p["contract"]["strike"], state, ps, nmax=p["reference_nmax"]
            )["values"]
            table[event, j, :, 0] = values[:, 0]
            table[event, j, :, 1] = ss * values[:, 1]
            table[event, j, :, 2] = ss**2 * values[:, 2] + ss * values[:, 1]
    return {"log_spot_nodes": xs, "seconds_nodes": seconds, "derivatives": table}


@dataclass
class PreparedHermite:
    """Offline spline objects separated from online prediction cost."""

    log_spot_nodes: np.ndarray
    seconds_nodes: np.ndarray
    splines: list


def prepare_hermite(grid):
    """Construct the two regime/time spline rosters from saved node derivatives."""
    xs = np.asarray(grid["log_spot_nodes"])
    ts = np.asarray(grid["seconds_nodes"])
    ds = np.asarray(grid["derivatives"])
    if (
        xs.ndim != 1
        or ts.ndim != 1
        or len(xs) < 2
        or len(ts) < 2
        or not np.all(np.diff(xs) > 0)
        or not np.all(np.diff(ts) > 0)
        or not np.all(np.diff(np.log(ts)) > 0)
        or np.any(ts <= 0)
        or ds.shape != (2, len(ts), len(xs), 3)
        or not np.isfinite(ds).all()
    ):
        raise ValueError("ordered finite Hermite grid required")
    splines = [
        [BPoly.from_derivatives(xs, row, extrapolate=False) for row in ds[e]] for e in [0, 1]
    ]
    return PreparedHermite(xs, ts, splines)


def hermite_predict(grid, inputs, p):
    """Evaluate the same C2 scalar price and its physical first two spot Greeks."""
    g = grid if isinstance(grid, PreparedHermite) else prepare_hermite(grid)
    a = np.asarray(inputs, dtype=float)
    if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all():
        raise ValueError("finite [spot,seconds,event] inputs required")
    if np.any(a[:, :2] <= 0) or np.any((a[:, 2] != 0) & (a[:, 2] != 1)):
        raise ValueError("positive spot/seconds and binary event required")
    xx = np.log(a[:, 0] / p["contract"]["strike"])
    t = a[:, 1]
    # Permit only arithmetic endpoint roundoff, never extrapolated queries.
    eps = 1e-12
    if (
        np.any(xx < g.log_spot_nodes[0] - eps)
        or np.any(xx > g.log_spot_nodes[-1] + eps)
        or np.any(t < g.seconds_nodes[0] - eps)
        or np.any(t > g.seconds_nodes[-1] + eps)
    ):
        raise ValueError("Hermite query outside frozen domain")
    xx = np.minimum(np.maximum(xx, g.log_spot_nodes[0]), g.log_spot_nodes[-1])
    t = np.minimum(np.maximum(t, g.seconds_nodes[0]), g.seconds_nodes[-1])
    j = np.minimum(np.searchsorted(g.seconds_nodes, t, side="right") - 1, len(g.seconds_nodes) - 2)
    j = np.maximum(j, 0)
    fraction = (np.log(t) - np.log(g.seconds_nodes[j])) / (
        np.log(g.seconds_nodes[j + 1]) - np.log(g.seconds_nodes[j])
    )
    deriv = np.empty((len(a), 3))
    for event in [0, 1]:
        for node in np.unique(j[a[:, 2] == event]):
            ids = (a[:, 2] == event) & (j == node)
            for order in range(3):
                left = g.splines[event][node](xx[ids], nu=order)
                right = g.splines[event][node + 1](xx[ids], nu=order)
                deriv[ids, order] = (1 - fraction[ids]) * left + fraction[ids] * right
    return np.column_stack(
        [
            deriv[:, 0],
            deriv[:, 1] / a[:, 0],
            (deriv[:, 2] - deriv[:, 1]) / a[:, 0] ** 2,
        ]
    )


def error_summary(predicted, reference, *, strike):
    """Price/Delta/KGamma errors; a failed row makes full-roster metrics unknown."""
    a, b = np.asarray(predicted), np.asarray(reference)
    if (
        a.shape != b.shape
        or a.ndim != 2
        or a.shape[1] != 3
        or not np.isfinite(strike)
        or strike <= 0
    ):
        raise ValueError("matching Nx3 values and positive strike required")
    with np.errstate(over="ignore", invalid="ignore"):
        errors = (a - b) * np.array([1.0, 1.0, strike])
    finite = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
    finite &= np.isfinite(errors).all(axis=1)
    count = len(a)
    result = {
        "original_count": count,
        "failed_rows": int((~finite).sum()),
        "units": ["currency", "currency/spot", "K*currency/spot^2"],
    }
    if count == 0 or not finite.all():
        return {
            **result,
            "status": "empty" if count == 0 else "nonfinite",
            "rmse": None,
            "p99": None,
            "max": None,
        }
    magnitude = np.max(np.abs(errors), axis=0)
    divisor = np.where(magnitude > 0, magnitude, 1.0)
    stable_rmse = magnitude * np.sqrt(np.mean((errors / divisor) ** 2, axis=0))
    return {
        **result,
        "status": "complete",
        "rmse": stable_rmse.tolist(),
        "p99": np.quantile(np.abs(errors), 0.99, axis=0).tolist(),
        "max": np.max(np.abs(errors), axis=0).tolist(),
    }


def bucket_errors(predicted, reference, inputs, p):
    """Keep fixed time/event/ATM buckets and each original weight."""
    x = np.asarray(inputs)
    rows = []
    for event in [0, 1]:
        for minutes in p["remaining_minutes"]:
            mask = (x[:, 1] == minutes * 60) & (x[:, 2] == event)
            for geometry in ["all", "atm", "tail"]:
                if geometry != "all":
                    w = states([[p["contract"]["strike"], minutes * 60, event]], p)[0].variance
                    near = np.abs(np.log(x[:, 0] / p["contract"]["strike"])) <= 2 * np.sqrt(w)
                    mask2 = mask & (near if geometry == "atm" else ~near)
                else:
                    mask2 = mask
                rows.append(
                    {
                        "event": event,
                        "minutes": minutes,
                        "geometry": geometry,
                        **error_summary(
                            np.asarray(predicted)[mask2],
                            np.asarray(reference)[mask2],
                            strike=p["contract"]["strike"],
                        ),
                    }
                )
    return rows


def safe_route(raw, inputs, p):
    """Route domain/bound failures to mixture; retain raw and expiry/invalid NaN.

    Passing these checks does not detect unknown pricing or Greek error. The
    returned result never certifies an NN that merely respects scalar bounds.
    """
    x, a = np.asarray(inputs, dtype=float), np.asarray(raw, dtype=float)
    if x.ndim != 2 or x.shape[1] != 3 or a.shape != x.shape:
        raise ValueError("Nx3 input/raw rows required")
    result = a.copy()
    routes = []
    bounds = spot_domain(p)
    k = p["contract"]["strike"]
    for i, row in enumerate(x):
        spot, seconds, event = row
        if (
            not np.isfinite(row).all()
            or spot <= 0
            or event not in [0, 1]
            or seconds < 0
            or seconds > 390 * 60
        ):
            routes.append("invalid_contract")
            result[i] = np.nan
            continue
        if seconds == 0:
            result[i] = oracle(row[None], p)[0]
            routes.append("expiry_undefined_atm" if spot == k else "expiry_exact")
            continue
        if seconds < 60:
            route = "fallback_time"
        elif not bounds[0] - 1e-12 <= np.log(spot / k) <= bounds[1] + 1e-12:
            route = "fallback_spot"
        elif not np.isfinite(a[i]).all():
            route = "fallback_nonfinite"
        else:
            tau = seconds / (365 * 86400)
            bound = np.exp(-p["contract"]["dividend"] * tau)
            lower = max(spot * bound - k * np.exp(-p["contract"]["rate"] * tau), 0.0)
            money_roundoff = 64 * np.finfo(float).eps * max(1.0, spot, k)
            delta_roundoff = 64 * np.finfo(float).eps * max(1.0, bound)
            bad = a[i, 0] < lower - money_roundoff or a[i, 0] > spot * bound + money_roundoff
            bad |= a[i, 1] < -delta_roundoff or a[i, 1] > bound + delta_roundoff or a[i, 2] < 0
            route = "fallback_bound" if bad else "raw"
        if route != "raw":
            result[i] = oracle(row[None], p)[0]
        routes.append(route)
    return {
        "values": result,
        "routes": np.array(routes, dtype="U32"),
        "original_count": len(x),
        "raw_count": routes.count("raw"),
    }


def expense_totals(expenses):
    """Sum measured uniquely charged receipts, retaining unmeasured categories."""
    ids = [row["id"] for row in expenses]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate expense id")
    rows = {row["id"]: row for row in expenses}
    totals = {}
    pending = []
    for row in expenses:
        sec = row["seconds"]
        if sec is not None and (not np.isfinite(sec) or sec < 0):
            raise ValueError("nonnegative measured seconds required")
        parent = row.get("parent")
        visited = {row["id"]}
        while parent is not None:
            if parent not in rows:
                raise ValueError("missing expense parent")
            if parent in visited:
                raise ValueError("cycle in expense parents")
            visited.add(parent)
            if row["charged"] and rows[parent]["charged"]:
                raise ValueError("nested expense double charge")
            parent = rows[parent].get("parent")
        if not row["charged"]:
            continue
        if sec is None:
            pending.append(row["id"])
        else:
            category = row["category"]
            totals[category] = totals.get(category, 0.0) + sec
    return {
        "measured_seconds": float(sum(totals.values())),
        "categories": totals,
        "pending_ids": pending,
    }


def break_even(nn_offline, baseline_offline, nn_online, baseline_online):
    """Return queries only for positive measured per-query saving."""
    values = np.asarray([nn_offline, baseline_offline, nn_online, baseline_online])
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("finite nonnegative expense measurements required")
    saving = baseline_online - nn_online
    incremental = nn_offline - baseline_offline
    return {
        "queries": max(0.0, incremental / saving) if saving > 0 else None,
        "status": "recoverable" if saving > 0 else "no_online_saving",
        "incremental_offline_s": float(incremental),
        "online_saving_s": float(saving),
    }
