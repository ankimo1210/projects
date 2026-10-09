"""Private saved-only finance replay for the dynamic Asian hedging study.

No RNG, training or PDE/CF solve is invoked. A successful replay checks the
declared saved boundary; it does not certify earlier SDE generation or missing
independent accuracy. The study owns source closure, expenses, training and
validation selections, pilot aggregation and final qualification.
"""

from __future__ import annotations

import math

import numpy as np
from hullkit._dynamic_hedging_conditional import primitive_labels
from hullkit._dynamic_hedging_core import asian_memory
from hullkit._dynamic_hedging_statistics import paired_statistics
from hullkit._dynamic_hedging_surfaces import build_asian_cache, evaluate_call
from hullkit._heston_local_surface import HestonParameters

_RTOL = 2e-10
_ATOL = 2e-11
_PATH_FIELDS = (
    "b",
    "c",
    "mu",
    "sigma",
    "last_z",
    "last_left_spot",
    "last_left_variance",
    "last_left_coefficient",
    "aux_logG_prefix",
)


def _same(expected, saved, name):
    """Compare numeric values by tolerance, preserving NaNs and shapes."""
    if isinstance(expected, dict):
        if not isinstance(saved, dict) or set(saved) != set(expected):
            raise ValueError(f"{name}: saved key set differs from recomputation")
        for key, value in expected.items():
            _same(value, saved[key], f"{name}.{key}")
        return
    if expected is None or saved is None:
        if expected is not None or saved is not None:
            raise ValueError(f"{name}: unknown value changed")
        return
    left, right = np.asarray(expected), np.asarray(saved)
    if left.shape != right.shape:
        raise ValueError(f"{name}: saved shape differs from original")
    if left.dtype.kind in "USb" or right.dtype.kind in "USb":
        equal = np.array_equal(left, right)
    else:
        equal = np.allclose(left, right, rtol=_RTOL, atol=_ATOL, equal_nan=True)
    if not equal:
        raise ValueError(f"{name}: saved value differs from recomputation")


def _original(value, name):
    if not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name}: original positive integer required")
    return int(value)


def _step_status(p, mask, last_step, model):
    """Validate a lossless status dictionary without expanding Unicode cubes."""
    status = np.asarray(p["local_step_status"])
    if status.shape != (len(mask), last_step):
        raise ValueError("local_step_status: original path/step shape required")
    encoding = p.get("local_step_status_encoding", "unicode")
    if encoding == "uint8_dictionary":
        labels = np.asarray(p["local_step_status_labels"]).astype(str)
        if (
            status.dtype != np.uint8
            or labels.ndim != 1
            or not 1 <= len(labels) <= 256
            or labels[0] != ""
            or len(set(labels)) != len(labels)
            or np.any(status >= len(labels))
        ):
            raise ValueError("local_step_status: invalid uint8 code/legend")
        empty = status == 0
        counts = np.bincount(status.ravel(), minlength=len(labels))
        label_counts = dict(zip(labels.tolist(), counts.tolist(), strict=True))
        last_labels = labels[status[:, -1]]
    elif encoding == "unicode" and status.dtype.kind in "US":
        if p.get("local_step_status_labels") is not None:
            raise ValueError("local_step_status: Unicode records must not redefine a legend")
        empty = status == ""
        labels, counts = np.unique(status, return_counts=True)
        label_counts = dict(zip(labels.tolist(), counts.tolist(), strict=True))
        last_labels = status[:, -1]
    else:
        raise ValueError("local_step_status: unsupported encoding")
    if np.any(empty[mask]):
        raise ValueError("local_step_status: valid paths contain unexecuted steps")
    # A failed path cannot restart after an unexecuted step.
    stopped = np.zeros(len(mask), dtype=bool)
    for j in range(last_step):
        if np.any(stopped & ~empty[:, j]):
            raise ValueError("local_step_status: executed step follows an unexecuted step")
        stopped |= empty[:, j]
    if model == "heston" and any(
        label not in ("", "heston_left_variance") for label in label_counts
    ):
        raise ValueError("local_step_status: Heston legend changed")
    return {
        "encoding": encoding,
        "original_evaluations": int(status.size),
        "not_executed": int(empty.sum()),
        "label_counts": label_counts,
    }, last_labels


def replay_teacher(primitives, thresholds, parameters, surface, *, saved_labels=None) -> dict:
    """Derive final-step metadata and replay original primitive-to-label values.

    b/c/mu/sigma/last_z/last_left_* and aux_logG_prefix have shape (original N,).
    The calendar declares all remaining monthly fixings. Invalid original paths
    retain NaNs and reasons. Analytic flags, auxiliary variance/loading and the
    final conditional coefficients are derived before primitive_labels replay.
    Complete saved_labels, when supplied, are checked numerically.

    Earlier generation of b/prefix and independent precision are not certified
    at this boundary, so qualification remains unknown even on numeric agreement.
    """
    if not isinstance(parameters, HestonParameters):
        raise ValueError("parameters: HestonParameters required")
    p = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in primitives.items()}
    model = p.get("model")
    if model not in ("heston", "local"):
        raise ValueError("model: heston/local required")
    n = _original(p["original_path_count"], "original_path_count")
    _same(n, p["N"], "N")
    times = np.asarray(p["calendar_times"], float)
    indices = np.asarray(p["fixing_indices"])
    count = p["memory_count"]
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.isfinite(times).all()
        or np.any(np.diff(times) <= 0)
        or times[0] < 0
        or not np.isclose(times[-1], 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("calendar_times: increasing absolute calendar ending at T1 required")
    if (
        indices.ndim != 1
        or indices.dtype.kind not in "iu"
        or not isinstance(count, (int, np.integer))
        or not 0 <= count <= 11
        or len(indices) != 12 - count
        or np.any(indices <= 0)
        or np.any(indices >= len(times))
        or np.any(np.diff(indices) <= 0)
    ):
        raise ValueError("fixing_indices/memory_count: all remaining monthly observations required")
    _same(12, p["total_fixings"], "total_fixings")
    _same(np.arange(count + 1, 13) / 12, times[indices], "fixing_indices")
    if math.floor(times[0] * 12 + 1e-9) != count:
        raise ValueError("memory_count: restart calendar mismatch")
    _same(times[indices] - times[0], p["fixing_delays"], "fixing_delays")
    expiry = float(times[-1] - times[0])
    _same(expiry, p["expiry_delay"], "expiry_delay")
    _same(parameters.rate, p["rate"], "rate")
    _same(parameters.dividend_yield, p["dividend_yield"], "dividend_yield")
    _same("normalized_undiscounted", p["f_units"], "f_units")
    spot, state = float(p["spot"]), float(p["state"])
    if not np.isfinite([spot, state]).all() or spot <= 0 or state < 0:
        raise ValueError("spot/state: finite positive spot and nonnegative state required")
    if model == "local" and (state <= 0 or surface is None):
        raise ValueError("surface/state: saved local field and positive multiplier required")
    mask = np.asarray(p["path_mask"])
    if mask.shape != (n,) or mask.dtype.kind != "b":
        raise ValueError("path_mask: boolean original-N array required")
    for key in _PATH_FIELDS:
        value = np.asarray(p[key], float)
        if value.shape != (n,):
            raise ValueError(f"{key}: original-N path shape required")
        p[key] = value.copy()
        if not np.isfinite(value[mask]).all() or not np.isnan(value[~mask]).all():
            raise ValueError(f"{key}: original valid/failure mask is inconsistent")
    reasons = np.asarray(p["failure_reasons"]).astype(str)
    if reasons.shape != (n,) or np.any(reasons[~mask] == "") or np.any(reasons[mask] != ""):
        raise ValueError("failure_reasons: every failed original path requires its reason")
    _same(np.where(mask, "ready", "invalid"), p["primitive_status"], "primitive_status")
    step_summary, last_status = _step_status(p, mask, int(indices[-1]), model)
    variance = p["last_left_variance"]
    if np.any(variance[mask] < 0) or np.any(p["last_left_spot"][mask] <= 0):
        raise ValueError("last_left_variance/spot: invalid final left state")
    if np.any(p["b"][mask] < 0):
        raise ValueError("b: preceding positive normalized fixing sum cannot be negative")
    dt = float(times[indices[-1]] - times[indices[-1] - 1])
    derived = {
        "c": p["last_left_spot"] / spot,
        "mu": (parameters.rate - parameters.dividend_yield - variance / 2) * dt,
        "sigma": np.sqrt(variance * dt),
        "last_left_coefficient": np.sqrt(variance),
    }
    for key, value in derived.items():
        _same(value, p[key], key)
        p[key] = value
    analytic = bool(indices[-1] == 1)
    if len(indices) == 1:
        _same(np.zeros(mask.sum()), p["b"][mask], "b")
    if analytic:
        _same(np.full(mask.sum(), spot), p["last_left_spot"][mask], "last_left_spot")
        if model == "heston":
            _same(np.full(mask.sum(), state), variance[mask], "last_left_variance")
    if model == "local" and np.any(mask):
        evaluated_left = surface.evaluate(
            float((times[indices[-1] - 1] + times[indices[-1]]) / 2), p["last_left_spot"][mask]
        )
        _same(state * np.asarray(evaluated_left["variance"]), variance[mask], "last_left_variance")
        _same(
            np.asarray(evaluated_left["status"]).astype(str), last_status[mask], "local_step_status"
        )
    # Positive-variance primary paths are stochastic. A terminal zero sigma
    # alone cannot prove that all earlier steps were deterministic.
    deterministic = bool(
        np.all(mask)
        and np.all(variance == 0)
        and (
            analytic
            or (model == "heston" and state == 0 and parameters.theta == 0 and parameters.xi == 0)
        )
    )
    _same(analytic, p["analytic_conditional"], "analytic_conditional")
    raw_metadata = {
        "analytic_conditional": p["analytic_conditional"],
        "deterministic_model": p["deterministic_model"],
    }
    if np.any(mask):
        _same(deterministic, p["deterministic_model"], "deterministic_model")
    midpoint = np.nan
    if model == "heston":
        control = parameters.theta + (state - parameters.theta) * (
            -np.expm1(-parameters.kappa * expiry) / (parameters.kappa * expiry)
        )
        control_status = "expected_average_variance"
    else:
        midpoint = float((times[0] + times[1]) / 2)
        evaluated = surface.evaluate(midpoint, np.array([spot]))
        control = state * float(np.asarray(evaluated["variance"])[0])
        control_status = str(np.asarray(evaluated["status"])[0])
    _same(float(control), p["control_variance"], "control_variance")
    _same(control_status, p["control_status"], "control_status")
    _same(midpoint, p["aux_first_midpoint"], "aux_first_midpoint")
    loading = float(np.sqrt(control * dt) / len(indices)) if np.any(mask) else 0.0
    _same(loading, p["aux_last_loading"], "aux_last_loading")
    if analytic:
        prefix = np.full(
            mask.sum(), (parameters.rate - parameters.dividend_yield - control / 2) * dt
        )
        _same(prefix, p["aux_logG_prefix"][mask], "aux_logG_prefix")
    p.update(
        analytic_conditional=analytic,
        deterministic_model=deterministic,
        control_variance=float(control),
        control_status=control_status,
        aux_first_midpoint=midpoint,
        aux_last_loading=loading,
        rate=float(parameters.rate),
        dividend_yield=float(parameters.dividend_yield),
        expiry_delay=expiry,
        total_fixings=12,
        path_mask=mask.copy(),
    )
    labels = primitive_labels(p, thresholds, blocks=16)
    if saved_labels is not None:
        _same(labels, saved_labels, "saved_labels")
    return {
        "integrity": "pass",
        "qualification": "unknown",
        "boundary": "last_primitives_to_labels",
        "earlier_sde_verified": False,
        "original_path_count": n,
        "valid_path_count": int(mask.sum()),
        "derived_primitives": p,
        "labels": labels,
        "raw_metadata": raw_metadata,
        "step_status_summary": step_summary,
        "unverified": ["earlier_sde", "independent_teacher_precision", "global_driver_generation"],
    }


def rebuild_asian_cache(rows, parameters, axes, *, model) -> dict:
    """Rebuild Cartesian curves from primitives and explicit global driver maps.

    Each row requires primitives, thresholds, date_index, global_driver_id,
    driver_mapping={original_n, global_steps, start_step, stop_step,
    aggregation_factor}, and surface for local. Calendar times are the uniform
    global year grid sliced and aggregated by that mapping. The original slice
    driver ID is retained separately from the declared shared global ID.
    Original N and global step count are common to every node; per-date slice
    boundaries and time aggregation may differ. Mapping checks do not
    authenticate earlier random values. Missing/failed nodes remain unknown;
    no RNG or simulation is invoked.
    """
    groups, bindings = [], []
    original_n, global_steps, global_id = None, None, None
    for row in rows:
        row_global = row["global_driver_id"]
        if not row_global or (global_id is not None and row_global != global_id):
            raise ValueError("global_driver_id: one explicit shared driver required")
        global_id = row_global
        raw = row["primitives"]
        if raw["model"] != model:
            raise ValueError("model: primitive/cache mismatch")
        mapping = row["driver_mapping"]
        for key in ("original_n", "global_steps", "aggregation_factor"):
            _original(mapping[key], "driver_mapping." + key)
        for key in ("start_step", "stop_step"):
            if not isinstance(mapping[key], (int, np.integer)):
                raise ValueError("driver_mapping: integer step boundaries required")
        a, b, factor = (mapping[k] for k in ("start_step", "stop_step", "aggregation_factor"))
        steps = mapping["global_steps"]
        if a < 0 or b > steps or b <= a or (b - a) % factor or a % factor or b % factor:
            raise ValueError("driver_mapping: invalid global slice/aggregation")
        _same(mapping["original_n"], raw["original_path_count"], "driver_mapping.original_n")
        _same(np.arange(a, b + 1, factor) / steps, raw["calendar_times"], "driver_mapping.calendar")
        if original_n is None:
            original_n = mapping["original_n"]
            global_steps = steps
        elif original_n != mapping["original_n"]:
            raise ValueError("original_n: same original driver rows required at every node")
        elif global_steps != steps:
            raise ValueError("driver_mapping.global_steps: one shared global grid length required")
        evaluated = replay_teacher(raw, row["thresholds"], parameters, row.get("surface"))
        # Preserve shared cluster curves, not every N x threshold sample at
        # every Cartesian node. Primitive chunks remain the original evidence.
        keep = (
            "spot",
            "state",
            "model",
            "memory_count",
            "total_fixings",
            "calendar_times",
            "fixing_indices",
            "fixing_delays",
            "expiry_delay",
            "rate",
            "dividend_yield",
            "original_path_count",
            "N",
            "shared_driver_id",
            "shared_driver_scope",
            "f_units",
            "thresholds",
            "f",
            "f_x",
            "f_se",
            "f_x_se",
            "status",
            "status_reasons",
            "component_order",
            "component_means",
            "component_se",
            "derivative_component_means",
            "derivative_component_se",
            "blocks",
            "block_path_count",
            "block_means",
            "f_x_block_means",
            "derivative_block_means",
        )
        labels = {key: evaluated["labels"][key] for key in keep}
        labels["date_index"] = row["date_index"]
        labels["slice_driver_id"] = labels["shared_driver_id"]
        labels["shared_driver_id"] = global_id
        labels["shared_driver_scope"] = (
            "declared global IID paths; explicit slice/aggregation mapping"
        )
        groups.append(labels)
        bindings.append(
            {
                "date_index": row["date_index"],
                "spot": raw["spot"],
                "state": raw["state"],
                "global_driver_id": global_id,
                "slice_driver_id": labels["slice_driver_id"],
                "driver_mapping": dict(mapping),
            }
        )
    if not groups:
        raise ValueError("rows: original primitive groups required")
    cache = build_asian_cache(
        {"groups": groups, "parameters": parameters, "N": original_n}, model=model, axes=axes
    )
    dates, states = np.asarray(axes["dates"]), np.asarray(axes["state"])
    expected = len(dates) * len(states)
    if model == "local":
        expected = len(states) * (
            (len(axes["t0_spot"]) if dates[0] == 0 else len(axes["spot"]))
            + (len(dates) - 1) * len(axes["spot"])
        )
    return {
        "integrity": "pass",
        "qualification": "unknown",
        "boundary": "declared_global_driver_mapping_and_primitives_to_cache",
        "earlier_sde_verified": False,
        "original_path_count": original_n,
        "original_group_count": int(expected),
        "saved_group_count": len(groups),
        "cache": cache,
        "driver_bindings": bindings,
        "unverified": ["earlier_sde", "global_driver_generation", "independent_surface_precision"],
    }


def _check_original_counts(record, n, name):
    """Bind all supplied population declarations to the unsliced raw path axis."""
    for key in ("original_n", "original_path_count"):
        if key in record and _original(record[key], f"{name}.{key}") != n:
            raise ValueError(f"{name}.{key}: declared original count differs from raw path axis")


def _market_arrays(dataset):
    times = np.asarray(dataset["times"], float)
    prices = np.asarray(dataset["prices"], float)
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.isfinite(times).all()
        or times[0] != 0
        or np.any(np.diff(times) <= 0)
        or prices.ndim != 3
        or prices.shape[0] < 1
        or prices.shape[1:] != (len(times), 2)
    ):
        raise ValueError("times/prices: original-N two-asset absolute calendar required")
    _check_original_counts(dataset, prices.shape[0], "dataset")
    if not np.isfinite(dataset["rate"]):
        raise ValueError("rate: finite discount convention required")
    cf = np.asarray(dataset.get("cashflows", np.zeros_like(prices)), float)
    if cf.shape != prices.shape:
        raise ValueError("cashflows: original market shape required")
    return times, prices, cf


def _mean_se(values, complete):
    if not complete:
        return np.full(values.shape[1:], np.nan), np.full(values.shape[1:], np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        mean = np.mean(values, axis=0)
        se = (
            np.std(values, axis=0, ddof=1) / np.sqrt(len(values))
            if len(values) > 1
            else np.full_like(mean, np.nan)
        )
    return mean, se


def check_market(dataset, *, fixing_times, call_cache, generator, latent_state=None) -> dict:
    """Recompute monthly observations, actual generator call quotes and gains.

    dataset contains times(D), prices(N,D,2), rate, memory_sum(N,D),
    memory_count(D or N,D), payoff(N), and optional cashflows(N,D,2).
    Extra hedge dates are allowed if all twelve claim fixings are recorded.
    Heston latent_state(N,D) is solely used for actual generator quotes; local
    uses multiplier one. Latent variance is not exported as policy information.

    Saved call tables are evaluated without CF/PDE solves. Raw discounted gains
    and IID SE keep all original paths. Earlier SDE and conditional/binned Q
    accuracy remain external gates, so financial qualification is unknown.
    """
    times, prices, cf = _market_arrays(dataset)
    generator = generator.lower()
    if generator not in ("heston", "local") or call_cache["model"] != generator:
        raise ValueError("generator: matching actual call cache required")
    _same(dataset["rate"], call_cache["rate"], "call.rate")
    fixings = np.asarray(fixing_times, float)
    _same(np.arange(1, 13) / 12, fixings, "fixing_times")
    _same(1.0, times[-1], "times.expiry")
    n, dates = prices.shape[:2]
    memory = asian_memory(prices[..., 0], times, fixings)
    _same(memory["A"], dataset["memory_sum"], "memory_sum")
    counts = np.asarray(dataset["memory_count"])
    _same(
        np.broadcast_to(memory["n"], (n, dates)),
        np.broadcast_to(counts, (n, dates)),
        "memory_count",
    )
    with np.errstate(invalid="ignore"):
        payoff = np.maximum(memory["A"][:, -1] / 12 - 100.0, 0.0)
    _same(payoff, dataset["payoff"], "payoff")
    if generator == "heston":
        if latent_state is None:
            raise ValueError("latent_state: actual Heston quote check requires generator state")
        states = np.asarray(latent_state, float)
        if states.shape != (n, dates):
            raise ValueError("latent_state: original-N calendar shape required")
    else:
        states = np.ones((n, dates))
    quotes = np.full((n, dates), np.nan)
    statuses = np.full((n, dates), "unknown", dtype="<U64")
    for date_index, t in enumerate(times):
        matches = np.flatnonzero(np.isclose(call_cache["dates"], t, rtol=0.0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError("call.dates: one exact snapshot per actual event required")
        values = evaluate_call(
            call_cache, int(matches[0]), prices[:, date_index, 0], states[:, date_index]
        )
        quotes[:, date_index] = values["value"]
        statuses[:, date_index] = values["status"]
    _same(quotes, prices[..., 1], "actual_call_prices")
    if "call_status" in dataset:
        _same(statuses, dataset["call_status"], "call_status")
    discount = np.exp(-float(dataset["rate"]) * times)
    with np.errstate(over="ignore", invalid="ignore"):
        gains = (
            discount[None, 1:, None] * (prices[:, 1:] + cf[:, 1:])
            - discount[None, :-1, None] * prices[:, :-1]
        )
        total = gains.sum(axis=1)
    valid = (
        np.isfinite(prices).all(axis=(1, 2))
        & (prices[..., 0] > 0).all(axis=1)
        & (prices[..., 1] >= 0).all(axis=1)
        & np.isfinite(cf).all(axis=(1, 2))
        & np.isfinite(payoff)
        & np.isfinite(total).all(axis=1)
        & np.all(statuses == "ok", axis=1)
    )
    if "path_mask" in dataset:
        _same(valid, dataset["path_mask"], "path_mask")
    complete = bool(valid.all())
    mean, se = _mean_se(gains, complete)
    total_mean, total_se = _mean_se(total, complete)
    recomputed = {
        "memory_sum": memory["A"],
        "memory_count": memory["n"],
        "payoff": payoff,
        "call_prices": quotes,
        "call_status": statuses,
        "path_mask": valid,
        "discounted_gains": gains,
        "mean_gains": mean,
        "gain_se": se,
        "mean_total_gains": total_mean,
        "total_gain_se": total_se,
    }
    for key in ("discounted_gains", "mean_gains", "gain_se", "mean_total_gains", "total_gain_se"):
        if key in dataset:
            _same(recomputed[key], dataset[key], key)
    return {
        "integrity": "pass",
        "qualification": "unknown",
        "boundary": "saved_market_states_and_call_table_to_observations_gains",
        "earlier_sde_verified": False,
        "original_path_count": n,
        "valid_path_count": int(valid.sum()),
        "recomputed": recomputed,
        "unverified": [
            "earlier_sde",
            "independent_call_accuracy",
            "conditional_one_step_Q_bias",
            "state_bin_Q_accuracy",
        ],
    }


def check_cash(dataset, cell) -> dict:
    """Independently recompute cash and discounted gains from saved holdings.

    dataset requires times/prices/payoff/premium/rate/cost_rates and optional
    cashflows. cell requires holdings(N,D-1,2); optional raw_holdings are checked
    against the legal clip at finite actions; failed whole actions retain NaN
    and supplied reasons. Supplied cash/costs/pnl/discounted_pnl/
    discounted_gain_pnl/path_mask and raw_account reasons are compared with
    recomputed values. Policy/risk reasons are separate from account reasons.
    Exact zero exposure/entitlement contributes zero even if that asset input
    is unknown; raw market prices/CF are preserved and supplied ignored-input
    masks are independently checked. Market qualification remains external.
    All initial, interim and final fees and one cash-settled claim are included.

    cash_account is deliberately not called: the cash recurrence and a separate
    gains expression are derived from event inputs. Policy selection and market
    accuracy remain external even when this accounting boundary is verified.
    """
    times, prices, cf = _market_arrays(dataset)
    n, dates, _ = prices.shape
    _check_original_counts(cell, n, "cell")
    holds = np.asarray(cell["holdings"], float)
    payoff = np.asarray(dataset["payoff"], float)
    fee = np.asarray(dataset["cost_rates"], float)
    premium, rate = float(dataset["premium"]), float(dataset["rate"])
    if (
        holds.shape != (n, dates - 1, 2)
        or payoff.shape != (n,)
        or fee.shape != (2,)
        or not np.isfinite(fee).all()
        or np.any(fee < 0)
        or not np.isfinite([premium, rate]).all()
    ):
        raise ValueError("holdings/payoff/cost_rates/premium: original finance shapes required")
    if np.any(np.abs(holds[np.isfinite(holds)]) > 2.0 + 1e-12):
        raise ValueError("holdings: declared legal constraint exceeded without repair")
    if cell.get("universe") == "U1" and np.any(holds[..., 1][np.isfinite(holds[..., 1])] != 0):
        raise ValueError("holdings: U1 cannot trade the call")
    if "raw_holdings" in cell:
        raw = np.asarray(cell["raw_holdings"], float)
        if raw.shape != holds.shape:
            raise ValueError("raw_holdings: original action shape required")
        finite_actions = np.isfinite(holds).all(axis=-1)
        finite_targets = np.isfinite(raw).all(axis=-1)
        if np.any(finite_actions & ~finite_targets):
            raise ValueError("raw_holdings: invalid target was repaired to finite action")
        _same(np.clip(raw[finite_actions], -2.0, 2.0), holds[finite_actions], "raw_holdings")
        failed_actions = ~finite_actions
        if np.any(failed_actions) and not np.isnan(holds[failed_actions]).all():
            raise ValueError("raw_holdings: failed legal action must remain wholly unknown")
        if "point_valid" in cell:
            _same(finite_actions, cell["point_valid"], "point_valid")
        if "reasons" in cell and np.any(failed_actions):
            action_reasons = np.asarray(cell["reasons"]).astype(str)
            if action_reasons.shape != (n,) or np.any(
                action_reasons[failed_actions.any(axis=1)] == ""
            ):
                raise ValueError("reasons: every failed action path requires its reason")
    zero = np.zeros((n, 1, 2))
    previous_events = np.concatenate([zero, holds], axis=1)
    current_events = np.concatenate([holds, zero], axis=1)
    inactive_prices = (previous_events == 0) & (current_events == 0)
    no_entitlement = previous_events == 0
    invalid_prices = ~np.isfinite(prices) | (prices < 0)
    unused_call_price = invalid_prices[..., 1] & inactive_prices[..., 1]
    unused_call_cashflow = ~np.isfinite(cf[..., 1]) & no_entitlement[..., 1]

    def contribution(exposure, value):
        # Raw unknown market values remain unchanged. Exact zero exposure has
        # an exact zero cash contribution; an unknown exposure is not zero.
        with np.errstate(over="ignore", invalid="ignore"):
            return np.where(exposure == 0, 0.0, exposure * value)

    cash = np.full((n, dates), np.nan)
    costs = np.full_like(cash, np.nan)
    previous = np.zeros((n, 2))
    balance = np.full(n, premium)
    mask = np.ones(n, dtype=bool)
    reasons = np.full(n, "ok", dtype="<U64")
    for j in range(dates):
        current = holds[:, j] if j < dates - 1 else np.zeros((n, 2))
        invalid = (invalid_prices[:, j] & ~inactive_prices[:, j]).any(axis=1) | ~np.isfinite(
            current
        ).all(axis=1)
        if j:
            invalid |= (~np.isfinite(cf[:, j]) & ~no_entitlement[:, j]).any(axis=1)
        if j == dates - 1:
            invalid |= ~np.isfinite(payoff)
        first = mask & invalid
        reasons[first] = "invalid_cash_event"
        mask &= ~invalid
        with np.errstate(over="ignore", invalid="ignore"):
            if j:
                balance *= np.exp(rate * (times[j] - times[j - 1]))
                balance += np.sum(contribution(previous, cf[:, j]), axis=1)
            trades = current - previous
            costs[:, j] = np.sum(contribution(np.abs(trades), fee * prices[:, j]), axis=1)
            balance -= np.sum(contribution(trades, prices[:, j]), axis=1) + costs[:, j]
            if j == dates - 1:
                balance -= payoff
        finite = np.isfinite(balance)
        reasons[mask & ~finite] = "nonfinite_cash_balance"
        mask &= finite
        balance[~mask] = np.nan
        cash[:, j] = balance
        costs[~mask, j] = np.nan
        previous = current
    discount = np.exp(-rate * times)
    trades = current_events - previous_events
    with np.errstate(over="ignore", invalid="ignore"):
        gain_costs = np.sum(contribution(np.abs(trades), fee * prices), axis=2)
        gains = (
            discount[None, 1:, None] * (prices[:, 1:] + cf[:, 1:])
            - discount[None, :-1, None] * prices[:, :-1]
        )
        gain_pnl = (
            premium
            + np.sum(contribution(holds, gains), axis=(1, 2))
            - np.sum(discount * gain_costs, axis=1)
            - discount[-1] * payoff
        )
        discounted_pnl = discount[-1] * cash[:, -1]
    finite = np.isfinite(gain_pnl) & np.isfinite(discounted_pnl)
    reasons[mask & ~finite] = "nonfinite_discounted_account"
    mask &= finite
    gain_pnl[~mask] = discounted_pnl[~mask] = cash[~mask, -1] = np.nan
    _same(gain_pnl, discounted_pnl, "independent_discounted_gain_identity")
    recomputed = {
        "cash": cash,
        "costs": costs,
        "pnl": cash[:, -1],
        "discounted_pnl": discounted_pnl,
        "discounted_gain_pnl": gain_pnl,
        "path_mask": mask,
        "reasons": reasons,
        "unused_call_price_mask": unused_call_price,
        "unused_call_cashflow_mask": unused_call_cashflow,
    }
    raw_account = cell.get("raw_account", {})
    for key, value in recomputed.items():
        # Study reasons include risk/precision or unavailable-policy diagnoses.
        # Saved raw account reasons belong to this accounting boundary.
        if key in cell and not (key == "reasons" and ("raw_holdings" in cell or raw_account)):
            _same(value, cell[key], key)
        if key in raw_account:
            _same(value, raw_account[key], "raw_account." + key)
    return {
        "integrity": "pass",
        "qualification": "verified" if mask.all() else "unknown",
        "boundary": "saved_market_and_holdings_to_cash_and_discounted_gains",
        "original_path_count": n,
        "valid_path_count": int(mask.sum()),
        "recomputed": recomputed,
        "unverified": ["policy_selection", "raw_target_origin", "market_accuracy"],
    }


def check_statistics(
    baseline_loss, candidate_loss, indices, saved, *, numerical_envelope=None
) -> dict:
    """Replay paired statistics from original losses and supplied saved indices.

    Uses 64-path blocks and alpha=.05/8. Complete saved paired_statistics values,
    including original counts, individual ES95, d/r, bootstrap scores and CI, are
    compared by tolerance. No bootstrap RNG is invoked. The numerical envelope
    is independently caller-assessed; missing/nonfinite values remain unknown.
    Training, Q accuracy and family IUT are external even when the conditional
    statistical result is supported.
    """
    result = paired_statistics(
        baseline_loss,
        candidate_loss,
        indices,
        block_size=64,
        alpha=0.05 / 8,
        numerical_envelope=numerical_envelope,
    )
    _same(result, saved, "statistics")
    return {
        "integrity": "pass",
        "qualification": result["status"],
        "boundary": "original_losses_and_saved_indices_to_conditional_statistics",
        "original_path_count": result["original_count"],
        "valid_path_count": result["counts"]["finite"],
        "recomputed": result,
        "unverified": [
            "numerical_envelope_measurement",
            "training_completeness",
            "Q_accuracy",
            "three_initialization_family",
        ],
    }
