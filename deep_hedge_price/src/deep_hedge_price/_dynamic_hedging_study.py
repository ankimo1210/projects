"""Private observable connectors for the fixed dynamic-hedging study.

Callers supply all drivers, caches and checkpoints. This module creates no
market/replay RNG and never opens a test stream. Protocol authorization and the
independent financial checker remain caller responsibilities. Local numerical
qualification is not study acceptance or a rigorous complete bias certificate.
"""

from time import perf_counter, process_time

import numpy as np
from hullkit._dynamic_hedging_core import asian_memory, cash_account, heston_records, local_records
from hullkit._dynamic_hedging_risk import (
    band_holdings,
    price_covariance,
    quote_positions,
    stock_only_target,
)
from hullkit._dynamic_hedging_surfaces import evaluate_asian, evaluate_call, fit_quote_state

from ._dynamic_hedging_policy import fit_policy, numpy_policy, observable_features
from ._dynamic_hedging_protocol import study_roster

_MODELS = ("heston", "local")
_NAMES = {"heston": "Heston", "local": "local"}


def _model(model):
    result = "heston" if model == "Heston" else model
    if result not in _MODELS:
        raise ValueError("model must be Heston/heston or local")
    return result


def _universe(universe):
    if universe not in ("U1", "U2"):
        raise ValueError("universe must be U1 or U2")


def _date_indices(cache, times):
    axis = np.asarray(cache["dates"], dtype=float)
    result = []
    for time in times:
        matches = np.flatnonzero(axis == time)
        if len(matches) != 1:
            raise ValueError("cache dates must contain each exact recorded date once")
        result.append(int(matches[0]))
    return np.asarray(result, dtype=int)


def _scalar_error(cache, name):
    array = np.asarray(cache.get(name, np.nan), dtype=float)
    if array.size == 0 or np.any(~np.isfinite(array)) or np.any(array < 0):
        return np.nan
    return float(np.max(array))


def _dataset_shape(dataset):
    times = np.asarray(dataset["times"], dtype=float)
    prices = np.asarray(dataset["prices"], dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or times[0] != 0
        or times[-1] != 1
        or np.any(~np.isfinite(times))
        or np.any(np.diff(times) <= 0)
        or prices.ndim != 3
        or prices.shape[1:] != (len(times), 2)
        or len(prices) < 1
    ):
        raise ValueError("fixed-claim dataset requires N x dates x two prices from t0 to T1")
    n, dates, _ = prices.shape
    memory = np.asarray(dataset["memory_sum"], dtype=float)
    counts = np.asarray(dataset["memory_count"], dtype=float)
    if memory.shape != (n, dates) or counts.shape not in ((dates,), (n, dates)):
        raise ValueError("memory_sum/count must match all recorded dates")
    if np.asarray(dataset["payoff"]).shape != (n,):
        raise ValueError("payoff must retain all original paths")
    if np.asarray(dataset.get("cashflows", np.zeros_like(prices))).shape != prices.shape:
        raise ValueError("cashflows must match original prices")
    fees = np.asarray(dataset["cost_rates"], dtype=float)
    if fees.shape != (2,) or np.any(~np.isfinite(fees)) or np.any(fees < 0):
        raise ValueError("two finite nonnegative cost rates required")
    if dataset.get("original_n", n) != n:
        raise ValueError("original denominator differs from dataset rows")
    return times, prices, memory, np.broadcast_to(counts, (n, dates))


def market_dataset(
    model,
    parameters,
    surface,
    normals,
    calendar_times,
    record_indices,
    fixing_times,
    call_cache,
    *,
    premium,
    cost_rates,
) -> dict:
    """Connect supplied adapted drivers to observed S/Q and monthly Asian memory.

    The original path axis is never filtered. Actual generator variance is
    retained under market for diagnostics and actual Heston quote generation;
    risk and NN features consume only S/Q/time/A/n. Local market quotes use
    multiplier one. Fixings precede actions. No temporal interpolation, rolling
    call, numerical price clipping or unsupported-state fallback is performed.
    """
    start, cpu_start = perf_counter(), process_time()
    model = _model(model)
    times = np.asarray(calendar_times, dtype=float)[np.asarray(record_indices)]
    if times[0] != 0 or times[-1] != 1 or parameters.dividend_yield != 0:
        raise ValueError("fixed study requires t0/T1 records and zero dividend yield")
    fixings = np.asarray(fixing_times, dtype=float)
    if fixings.shape != (12,) or not np.allclose(
        fixings, np.arange(1, 13) / 12, rtol=0, atol=1e-12
    ):
        raise ValueError("fixed Asian requires twelve monthly fixings excluding S0")
    if _model(call_cache["model"]) != model:
        raise ValueError("actual call cache must use the market generator")
    call_indices = _date_indices(call_cache, times)
    if model == "heston":
        records = heston_records(parameters, normals, calendar_times, record_indices)
        actual_state = records["variance"]
    else:
        records = local_records(parameters, surface, normals, calendar_times, record_indices)
        actual_state = np.ones_like(records["spot"])
    memory = asian_memory(records["spot"], times, fixings)
    n, dates = records["spot"].shape
    quote = np.full((n, dates), np.nan)
    quote_status = np.full((n, dates), "unknown", dtype="<U64")
    quote_reason = np.full((n, dates), "", dtype="<U96")
    raw_calls = []
    for j, index in enumerate(call_indices):
        call = evaluate_call(call_cache, int(index), records["spot"][:, j], actual_state[:, j])
        quote[:, j], quote_status[:, j], quote_reason[:, j] = (
            call["value"],
            call["status"],
            call["reason"],
        )
        raw_calls.append(call)
    payoff = np.maximum(memory["A"][:, -1] / 12 - 100.0, 0.0)
    prices = np.stack([records["spot"], quote], axis=-1)
    valid = records["path_mask"] & np.isfinite(payoff) & np.isfinite(prices).all(axis=(1, 2))
    reasons = np.where(valid, "ok", "market_or_actual_call_failure").astype("<U96")
    reasons[~records["path_mask"]] = records["reasons"][~records["path_mask"]]
    error = _scalar_error(call_cache, "price_error")
    measured = np.isfinite(error) and error <= 0.001
    result = {
        "times": times.copy(),
        "prices": prices,
        "memory_sum": memory["A"],
        "memory_count": memory["n"],
        "memory_remaining": memory["m"],
        "payoff": payoff,
        "cashflows": np.zeros_like(prices),
        "cost_rates": np.asarray(cost_rates, dtype=float).copy(),
        "premium": float(premium),
        "rate": float(parameters.rate),
        "original_n": n,
        "path_ids": np.arange(n, dtype=np.int64),
        "path_mask": valid,
        "reasons": reasons,
        "market": records,
        "primitives": {
            "normals": np.asarray(normals),
            "calendar_times": np.asarray(calendar_times),
            "record_indices": np.asarray(record_indices),
            "fixing_times": fixings.copy(),
        },
        "actual_call": {
            "value": quote,
            "status": quote_status,
            "reason": quote_reason,
            "raw": raw_calls,
            "date_indices": call_indices,
            "price_error": error,
            "reference_status": call_cache.get("reference_status", "unmeasured"),
            "actual_state_use": "generator quote and diagnostic only",
        },
        "model": model,
        "qualification": "qualified" if valid.all() and measured else "unknown",
        "diagnostics": {
            "original_n": n,
            "failed_count": int(np.sum(~valid)),
            "actual_call_unknown_count": int(np.sum(quote_status != "ok")),
            "driver": "caller supplied, no RNG created",
            "fixing_before_rebalance": True,
            "initial_spot_is_fixing": False,
        },
    }
    _dataset_shape(result)
    if not np.isfinite([premium, parameters.rate]).all():
        raise ValueError("finite premium and rate required")
    result["expense"] = {
        "scope": "market_records/memory/actual_call",
        "wall_seconds": perf_counter() - start,
        "cpu_seconds": process_time() - cpu_start,
        "original_n": n,
        "includes_children": True,
    }
    return result


def _block_position_stats(vs, vt, cs, ct, model, spot, parameters):
    blocks = quote_positions(vs, vt, cs[..., None], ct[..., None])
    u2 = np.stack([blocks["stock"], blocks["call"]], axis=-1)
    u1 = stock_only_target(
        blocks,
        cs[..., None],
        ct[..., None],
        model=model,
        spot=spot[..., None],
        xi=parameters.xi,
        rho=parameters.rho,
    )
    centered = u2 - np.mean(u2, axis=-2, keepdims=True)
    covariance = np.einsum("...bi,...bj->...ij", centered, centered) / (15 * 16)
    return (
        u2,
        u1,
        covariance,
        np.sqrt(np.diagonal(covariance, axis1=-2, axis2=-1)),
        np.std(u1, axis=-1, ddof=1) / 4,
    )


def _position_errors(
    vs_error, vt_error, cs_error, ct_error, hq, cs, ct, *, model, spot, parameters
):
    denominator = np.abs(ct) - ct_error
    stable = np.isfinite(denominator) & (denominator > 0)
    hq_error = np.full(ct.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        np.divide(vt_error + np.abs(hq) * ct_error, denominator, out=hq_error, where=stable)
        hs_error = vs_error + np.abs(cs) * hq_error + (np.abs(hq) + hq_error) * cs_error
        coefficient = parameters.rho * parameters.xi / spot if model == "heston" else 0.0
        u1_error = vs_error + np.abs(coefficient) * vt_error
    return np.stack([hs_error, hq_error], axis=-1), u1_error


def quote_risk_dataset(parameters, surface, dataset, caches) -> dict:
    """Fit states only from observable S/Q and propagate shared label curves.

    caches has heston/local call/asian dictionaries. A call copy receives
    Asian state bounds, enforcing joint support without changing caller data.
    Actual market variance is never read. call price_error/spot_derivative_error/
    derivative_error and Asian deterministic_error.{value,spot_derivative,
    state_derivative} are absolute physical-coordinate errors. Missing values
    leave arithmetic targets available but qualification unknown.

    Sixteen shared block curves pass through the same IFT before covariance/16.
    Position error is a conservative frozen-state ratio perturbation conditional
    on supplied derivative errors. It does not bound root-state error or entire
    model bias; the independent checker must assess these additional errors.
    Exact linear claims retain known stock/zero-call targets without a quote
    fit. Their band covariance qualification is recorded separately. Local
    covariance uses the current calendar field; unsupported t0 restarts use
    only the supplied original first internal midpoint, explicitly recorded.
    """
    start, cpu_start = perf_counter(), process_time()
    times, prices, memory, counts = _dataset_shape(dataset)
    n, dates = prices.shape[:2]
    m = dates - 1
    spot, quote = prices[:, :m, 0], prices[:, :m, 1]
    models = {}
    for model in _MODELS:
        supplied = caches[model]
        call, asian = dict(supplied["call"]), supplied["asian"]
        if _model(call["model"]) != model or _model(asian["model"]) != model:
            raise ValueError("valuation cache model identity mismatch")
        call["asian_state_bounds"] = [
            float(asian["state_nodes"][0]),
            float(asian["state_nodes"][-1]),
        ]
        call_indices, asian_indices = (
            _date_indices(call, times[:m]),
            _date_indices(asian, times[:m]),
        )
        shape = (n, m)
        row = {
            name: np.full(shape, np.nan)
            for name in [
                "state",
                "root",
                "fit_residual",
                "fit_condition",
                "call_value",
                "call_spot_derivative",
                "call_state_derivative",
                "asian_value",
                "asian_spot_derivative",
                "asian_state_derivative",
            ]
        }
        for name in [
            "fit_status",
            "fit_reason",
            "asian_status",
            "asian_reason",
            "call_status",
            "call_reason",
        ]:
            row[name] = np.full(shape, "", dtype="<U96")
        row["asian_block_values"] = np.full((*shape, 16, 3), np.nan)
        row["asian_covariance"] = np.full((*shape, 3, 3), np.nan)
        row["asian_standard_errors"] = np.full((*shape, 3), np.nan)
        row["fit_state_bounds"] = np.full((*shape, 2), np.nan)
        fit_raw, asian_raw, call_raw, roots, root_offsets = [], [], [], [], [0]
        for j, (ci, ai) in enumerate(zip(call_indices, asian_indices, strict=True)):
            fit = fit_quote_state(
                call,
                int(ci),
                spot[:, j],
                quote[:, j],
                state_scale=0.04 if model == "heston" else 1.0,
            )
            state = np.asarray(fit["state"])
            claim = evaluate_asian(asian, int(ai), spot[:, j], state, memory[:, j], counts[:, j])
            traded = evaluate_call(call, int(ci), spot[:, j], state)
            fit_raw.append(fit)
            asian_raw.append(claim)
            call_raw.append(traded)
            for target, key in [
                ("state", "state"),
                ("root", "root"),
                ("fit_residual", "residual"),
                ("fit_condition", "condition"),
            ]:
                row[target][:, j] = fit[key]
            for prefix, value in [("fit", fit), ("asian", claim), ("call", traded)]:
                row[prefix + "_status"][:, j], row[prefix + "_reason"][:, j] = (
                    value["status"],
                    value["reason"],
                )
            for prefix, value in [("asian", claim), ("call", traded)]:
                for suffix in ["value", "spot_derivative", "state_derivative"]:
                    row[prefix + "_" + suffix][:, j] = value[suffix]
            for sk, dk in [
                ("block_values", "asian_block_values"),
                ("covariance", "asian_covariance"),
                ("standard_errors", "asian_standard_errors"),
            ]:
                if sk in claim:
                    row[dk][:, j] = claim[sk]
            linear = np.asarray(claim["status"]) == "not_required_linear_claim"
            if np.any(linear):
                exact = np.stack(
                    [claim["value"], claim["spot_derivative"], claim["state_derivative"]], axis=-1
                )
                row["asian_block_values"][linear, j] = exact[linear, None, :]
                row["asian_covariance"][linear, j] = 0.0
                row["asian_standard_errors"][linear, j] = 0.0
            if "state_bounds" in fit:
                row["fit_state_bounds"][:, j] = fit["state_bounds"]
            root_table = np.asarray(fit["roots"])
            for path in range(n):
                values = np.atleast_1d(root_table[path])
                roots.extend(values[np.isfinite(values)].tolist())
                root_offsets.append(len(roots))
        row["fit_roots_flat"] = np.asarray(roots)
        row["fit_roots_offsets_date_major"] = np.asarray(root_offsets, dtype=np.int64)
        row["raw"] = {"fit": fit_raw, "asian": asian_raw, "call": call_raw}
        cs, ct = row["call_spot_derivative"], row["call_state_derivative"]
        vs, vt = row["asian_spot_derivative"], row["asian_state_derivative"]
        raw_positions = quote_positions(vs, vt, cs, ct)
        linear = row["asian_status"] == "not_required_linear_claim"
        # The exact linear claim has zero state exposure; do not manufacture
        # an unavailable 0/Ctheta or use latent generator state to rescue it.
        raw_positions["stock"][linear] = vs[linear]
        raw_positions["call"][linear] = 0.0
        raw_positions["valid"][linear] = np.isfinite(vs[linear])
        row["linear_claim"] = linear
        row["u2_target"] = np.stack([raw_positions["stock"], raw_positions["call"]], axis=-1)
        row["u1_target"] = stock_only_target(
            raw_positions, cs, ct, model=model, spot=spot, xi=parameters.xi, rho=parameters.rho
        )
        row["u1_target"][linear] = vs[linear]
        if model == "local":
            base_variance, local_status = np.full(shape, np.nan), np.full(shape, "", dtype="<U64")
            local_original_status = np.full(shape, "", dtype="<U64")
            local_source_time = np.broadcast_to(times[:m], shape).copy()
            local_early_proxy = np.zeros(shape, dtype=bool)
            calendar = np.asarray(
                dataset.get("primitives", {}).get("calendar_times", []), dtype=float
            )
            first_midpoint = (
                float((calendar[0] + calendar[1]) / 2)
                if calendar.ndim == 1
                and len(calendar) >= 2
                and calendar[0] == 0
                and np.isfinite(calendar[:2]).all()
                and calendar[1] > 0
                else np.nan
            )
            for j in range(m):
                local = surface.evaluate(float(times[j]), spot[:, j])
                base_variance[:, j], local_status[:, j] = local["variance"], local["status"]
                local_original_status[:, j] = local_status[:, j]
                unsupported = np.char.startswith(local_status[:, j], "unsupported")
                if times[j] == 0 and np.any(unsupported) and np.isfinite(first_midpoint):
                    # The approved t0 closure uses the original first internal
                    # SDE step, never the much larger hedge-interval midpoint.
                    retry = surface.evaluate(first_midpoint, spot[unsupported, j])
                    base_variance[unsupported, j] = retry["variance"]
                    local_status[unsupported, j] = retry["status"]
                    local_source_time[unsupported, j] = first_midpoint
                    local_early_proxy[unsupported, j] = True
                unsupported = np.char.startswith(local_status[:, j], "unsupported")
                base_variance[unsupported, j] = np.nan
            row.update(
                local_base_variance=base_variance,
                local_base_status=local_status,
                local_base_original_status=local_original_status,
                local_base_source_time=local_source_time,
                local_base_early_proxy=local_early_proxy,
            )
        else:
            base_variance = None
        cov = price_covariance(
            model,
            spot,
            row["state"],
            cs,
            ct,
            np.diff(times),
            xi=parameters.xi,
            rho=parameters.rho,
            base_variance=base_variance,
        )
        row["price_covariance"], row["price_covariance_rank"], row["price_covariance_status"] = (
            cov["covariance"],
            cov["rank"],
            cov["status"],
        )
        u2_blocks, u1_blocks, u2_cov, u2_se, u1_se = _block_position_stats(
            row["asian_block_values"][..., 1],
            row["asian_block_values"][..., 2],
            cs,
            ct,
            model,
            spot,
            parameters,
        )
        u2_blocks[linear] = np.stack(
            [
                row["asian_block_values"][..., 1][linear],
                np.zeros_like(row["asian_block_values"][..., 1][linear]),
            ],
            axis=-1,
        )
        u1_blocks[linear] = row["asian_block_values"][..., 1][linear]
        u2_cov[linear] = 0.0
        u2_se[linear] = 0.0
        u1_se[linear] = 0.0
        row.update(
            u2_block_positions=u2_blocks,
            u1_block_positions=u1_blocks,
            u2_position_covariance=u2_cov,
            u2_position_se=u2_se,
            u1_position_se=u1_se,
        )
        cp_error, cs_error, ct_error = (
            _scalar_error(call, key)
            for key in ["price_error", "spot_derivative_error", "derivative_error"]
        )
        deterministic = asian.get("deterministic_error", {})
        vp_error, vs_error, vt_error = (
            _scalar_error(deterministic, key)
            for key in ["value", "spot_derivative", "state_derivative"]
        )
        linear = row["asian_status"] == "not_required_linear_claim"
        point_vp_error, point_vs_error, point_vt_error = (
            np.where(linear, 0.0, error) for error in [vp_error, vs_error, vt_error]
        )
        row["asian_deterministic_error"] = np.stack(
            [point_vp_error, point_vs_error, point_vt_error], axis=-1
        )
        row["denominator_error"] = np.full(shape, ct_error)
        row["u2_deterministic_error"], row["u1_deterministic_error"] = _position_errors(
            point_vs_error,
            point_vt_error,
            cs_error,
            ct_error,
            raw_positions["call"],
            cs,
            ct,
            model=model,
            spot=spot,
            parameters=parameters,
        )
        row["u2_deterministic_error"][linear] = 0.0
        row["u1_deterministic_error"][linear] = 0.0
        measured_call = np.isfinite([cp_error, cs_error, ct_error]).all()
        measured_asian = np.isfinite(row["asian_deterministic_error"]).all(axis=-1)
        fitted = (row["fit_status"] == "ok") & (row["call_status"] == "ok")
        finite = raw_positions["valid"] & (linear | (fitted & (row["asian_status"] == "ok")))
        qualified = finite.copy()
        qualified &= measured_call and cp_error <= 0.001 and cs_error <= 0.002
        qualified &= measured_asian & (point_vp_error <= 0.05)
        qualified &= (np.abs(ct) > 3 * ct_error) & (
            ct_error * (0.04 if model == "heston" else 1.0) <= 0.01
        )
        qualified &= row["asian_standard_errors"][..., 0] <= 0.03
        qualified &= (u2_se[..., 0] <= 0.002) & (u2_se[..., 1] <= 0.005) & (u1_se <= 0.002)
        qualified &= np.isfinite(row["u2_deterministic_error"]).all(axis=-1)
        qualified &= np.all(row["u2_deterministic_error"] <= 0.01, axis=-1) & (
            row["u1_deterministic_error"] <= 0.01
        )
        qualified[linear] = finite[linear]
        covariance_qualified = cov["valid"] & fitted
        covariance_qualified &= measured_call and cp_error <= 0.001 and cs_error <= 0.002
        covariance_qualified &= (np.abs(ct) > 3 * ct_error) & (
            ct_error * (0.04 if model == "heston" else 1.0) <= 0.01
        )
        row["arithmetic_valid"] = finite
        row["band_arithmetic_valid"] = finite & cov["valid"]
        row["qualification"] = np.where(qualified, "qualified", "unknown")
        row["band_qualification"] = np.where(
            qualified & covariance_qualified, "qualified", "unknown"
        )
        row["qualification_reason"] = np.where(
            qualified, "", "unmeasured_or_failed_support/fit/precision/error"
        )
        row["errors"] = {
            "call_price": cp_error,
            "call_spot_derivative": cs_error,
            "call_state_derivative": ct_error,
            "asian_price": vp_error,
            "asian_spot_derivative": vs_error,
            "asian_state_derivative": vt_error,
            "position_error_scope": "frozen-state conditional derivative perturbation only",
        }
        row["diagnostics"] = {
            "original_n": n,
            "original_dates": m,
            "unknown_points": int(np.sum(~qualified)),
            "fit_unknown_points": int(np.sum(row["fit_status"] != "ok")),
            "state_source": "observed spot and traded call quote only",
            "call_date_indices": call_indices,
            "asian_date_indices": asian_indices,
            "shared_blocks": 16,
        }
        models[model] = row
    return {
        "models": models,
        "times": times[:m].copy(),
        "original_n": n,
        "expense": {
            "scope": "all_model_quote_fit/asian/covariance/position_uncertainty",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        },
    }


def _unknown_rollout(dataset, reason):
    start, cpu_start = perf_counter(), process_time()
    _times, prices, _, _ = _dataset_shape(dataset)
    n, dates = prices.shape[:2]
    return {
        "status": "unknown",
        "reason": str(reason),
        "original_n": n,
        "holdings": np.full((n, dates - 1, 2), np.nan),
        "raw_target": np.full((n, dates - 1, 2), np.nan),
        "raw_holdings": np.full((n, dates - 1, 2), np.nan),
        "cash": np.full((n, dates), np.nan),
        "costs": np.full((n, dates), np.nan),
        "discounted_pnl": np.full(n, np.nan),
        "discounted_gain_pnl": np.full(n, np.nan),
        "discounted_gross_pnl": np.full(n, np.nan),
        "loss": np.full(n, np.nan),
        "path_mask": np.zeros(n, dtype=bool),
        "qualified_path_mask": np.zeros(n, dtype=bool),
        "reasons": np.full(n, str(reason), dtype="<U192"),
        "diagnostics": {"original_n": n, "unknown_count": n},
        "expense": {
            "scope": "unavailable_policy_attempt",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        },
    }


def policy_rollout(dataset, risk, *, universe, policy, model=None, width=0.0, fit=None) -> dict:
    """Replay none/Greek/band/NN and independent cash accounts on all original paths.

    Chronological old holdings enter band/NN actions. Legal [-2,2] constraints
    are recorded with raw targets/actions. Numerical failures propagate NaN,
    never an implicit holding/zero action. Terminal has one liquidation and
    one claim payment. Net cash, independent discounted gains and zero-fee
    same-holding cash are returned. U1 keeps Q observable but trades no call.
    Zero call exposure/entitlement is evaluated as an exact zero contribution,
    with masks retained; raw unknown quotes/CF remain in the input dataset.
    """
    start, cpu_start = perf_counter(), process_time()
    _universe(universe)
    if policy not in ("none", "greek", "band", "nn"):
        raise ValueError("policy must be none/greek/band/nn")
    times, prices, memory, counts = _dataset_shape(dataset)
    n, dates = prices.shape[:2]
    m = dates - 1
    old, shape = np.zeros((n, 2)), (n, m, 2)
    holdings, raw_targets, raw_holdings = (np.full(shape, np.nan) for _ in range(3))
    features, constrained = np.full((n, m, 9), np.nan), np.zeros(shape, dtype=bool)
    point_valid, point_qualified = np.ones((n, m), dtype=bool), np.ones((n, m), dtype=bool)
    roundoff, roundoff_raw, roundoff_bound = (
        np.zeros((n, m), dtype=bool),
        np.full((n, m), np.nan),
        np.full((n, m), np.nan),
    )
    if policy in ("greek", "band"):
        model = _model(model)
        row = risk["models"][model]
        if risk.get("original_n") != n or row["u2_target"].shape != shape:
            raise ValueError("risk original axes must match dataset")
        if not np.array_equal(risk["times"], times[:m]):
            raise ValueError("risk exact dates must match dataset")
        point_qualified = row["qualification"] == "qualified"
        if policy == "band":
            point_qualified &= row["band_qualification"] == "qualified"
    if policy == "nn" and (
        fit is None
        or fit.get("status") != "completed"
        or fit.get("complete", True) is not True
        or not fit.get("weights")
        or not fit.get("scaler")
    ):
        result = _unknown_rollout(dataset, "NN fit incomplete or unavailable")
        result["raw_fit"] = fit
        result["expense"] = {
            "scope": "failed_NN_replay_attempt",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        }
        return result
    for j in range(m):
        if policy == "none":
            target, action = np.zeros((n, 2)), np.zeros((n, 2))
        elif policy == "nn":
            features[:, j] = observable_features(
                prices[:, j, 0],
                times[j],
                memory[:, j],
                counts[:, j],
                prices[:, j, 1],
                old,
                dataset["cost_rates"],
            )
            action = numpy_policy(fit["weights"], features[:, j], fit["scaler"], universe=universe)
            target = action.copy()
        else:
            target = row["u2_target"][:, j].copy()
            covariance = row["price_covariance"][:, j]
            if universe == "U1":
                target[:, 0], target[:, 1] = row["u1_target"][:, j], 0.0
                selected_target, selected_old, selected_covariance = (
                    target[:, :1],
                    old[:, :1],
                    covariance[:, :1, :1],
                )
            else:
                selected_target, selected_old, selected_covariance = target, old, covariance
            if policy == "band":
                band = band_holdings(selected_old, selected_target, selected_covariance, width)
                action = np.zeros((n, 2)) if universe == "U1" else band["holdings"].copy()
                raw = np.zeros((n, 2)) if universe == "U1" else band["raw_holdings"].copy()
                if universe == "U1":
                    action[:, :1], raw[:, :1] = band["holdings"], band["raw_holdings"]
                roundoff[:, j], roundoff_raw[:, j], roundoff_bound[:, j] = (
                    band["roundoff_corrected"],
                    band["raw_squared_sd"],
                    band["squared_sd_roundoff_bound"],
                )
            else:
                raw, action = target.copy(), np.clip(target, -2.0, 2.0)
        if policy != "band":
            raw = target.copy()
        if universe == "U1":
            target[:, 1] = action[:, 1] = raw[:, 1] = 0.0
        valid = np.isfinite(action).all(axis=1) & np.isfinite(old).all(axis=1)
        if policy in ("greek", "band"):
            valid &= row["arithmetic_valid"][:, j]
        if policy == "band":
            valid &= row["band_arithmetic_valid"][:, j]
        action[~valid] = np.nan
        point_valid[:, j], constrained[:, j] = valid, valid[:, None] & (action != raw)
        holdings[:, j], raw_targets[:, j], raw_holdings[:, j], old = action, target, raw, action
    cf = dataset.get("cashflows")
    stock_account = universe == "U1" or policy == "none"
    ap = prices[..., :1] if stock_account else prices
    ah = holdings[..., :1] if stock_account else holdings
    acf = None if cf is None else (cf[..., :1] if stock_account else cf)
    fees = np.asarray(dataset["cost_rates"])[:1] if stock_account else dataset["cost_rates"]
    previous = np.concatenate([np.zeros((n, 1, 2)), holdings], axis=1)
    current = np.concatenate([holdings, np.zeros((n, 1, 2))], axis=1)
    invalid_call_price = ~np.isfinite(prices[..., 1]) | (prices[..., 1] < 0)
    original_cf = np.zeros_like(prices) if cf is None else np.asarray(cf)
    invalid_call_cf = ~np.isfinite(original_cf[..., 1])
    unused_call_price = invalid_call_price & (previous[..., 1] == 0) & (current[..., 1] == 0)
    unused_call_cashflow = invalid_call_cf & (previous[..., 1] == 0)
    if not stock_account:
        # Zero entitlement/exposure contributes exactly zero. Preserve the raw
        # unknown quote/CF in dataset; a nonzero trade/liquidation still needs it.
        ap = ap.copy()
        ap[..., 1][unused_call_price] = 0.0
        if acf is not None:
            acf = np.asarray(acf).copy()
            acf[..., 1][unused_call_cashflow] = 0.0
    net = cash_account(
        times,
        ap,
        ah,
        dataset["payoff"],
        premium=dataset["premium"],
        rate=dataset["rate"],
        cashflows=acf,
        cost_rates=fees,
    )
    gross = cash_account(
        times,
        ap,
        ah,
        dataset["payoff"],
        premium=dataset["premium"],
        rate=dataset["rate"],
        cashflows=acf,
        cost_rates=np.zeros_like(fees),
    )
    path_valid = net["path_mask"] & point_valid.all(axis=1)
    path_qualified = path_valid & point_qualified.all(axis=1)
    if dataset.get("qualification", "unknown") != "qualified":
        path_qualified[:] = False
    reasons = np.where(path_valid, "", "arithmetic_market/risk/policy/cash_failure").astype("<U192")
    reasons[path_valid & ~path_qualified] = "numerical_precision_not_qualified"
    return {
        "status": "completed" if path_qualified.all() else "unknown",
        "reason": None if path_qualified.all() else "one or more original paths unqualified",
        "original_n": n,
        "policy": policy,
        "model": model,
        "universe": universe,
        "width": float(width),
        "holdings": holdings,
        "raw_target": raw_targets,
        "raw_holdings": raw_holdings,
        "constrained": constrained,
        "constraint_counts": constrained.sum(axis=-1),
        "constraint_count": int(constrained.sum()),
        "features": features,
        "point_valid": point_valid,
        "point_qualification": point_qualified,
        "roundoff_corrected": roundoff,
        "raw_squared_sd": roundoff_raw,
        "squared_sd_roundoff_bound": roundoff_bound,
        "cash": net["cash"],
        "costs": net["costs"],
        "pnl": net["pnl"],
        "discounted_pnl": net["discounted_pnl"],
        "discounted_gain_pnl": net["discounted_gain_pnl"],
        "discounted_gross_pnl": gross["discounted_pnl"],
        "loss": -net["discounted_pnl"],
        "path_mask": path_valid,
        "qualified_path_mask": path_qualified,
        "reasons": reasons,
        "raw_account": net,
        "gross_account": gross,
        "unused_call_price_mask": unused_call_price,
        "unused_call_cashflow_mask": unused_call_cashflow,
        "diagnostics": {
            "original_n": n,
            "unknown_count": int(np.sum(~path_qualified)),
            "failed_count": int(np.sum(~path_valid)),
            "terminal_liquidations": 1,
            "claim_payments": 1,
            "no_numerical_fallback": True,
        },
        "expense": {
            "scope": "policy/holdings/net_cash/independent_gain/zero_fee_counterfactual",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        },
    }


def select_validation(dataset, risk, *, generator, universe, widths) -> dict:
    """Select complete original-N validation bands/baseline in fixed tie order.

    All fourteen candidates retain raw MSE/arrays/reasons. Unqualified/failed
    candidates cannot be selected. No NN checkpoint or test receipt is invented.
    """
    _universe(universe)
    start, cpu_start = perf_counter(), process_time()
    generator = _NAMES[_model(generator)]
    if _model(dataset["model"]) != _model(generator):
        raise ValueError("dataset generator annotation differs from requested generator")
    widths = sorted(float(w) for w in widths)
    if (
        len(widths) != 6
        or len(set(widths)) != 6
        or any(not np.isfinite(w) or w < 0 for w in widths)
    ):
        raise ValueError("six distinct finite nonnegative original width candidates required")
    candidates, rollouts = [], {}
    for model in _MODELS:
        configurations = [("greek", None)] + [("band", width) for width in widths]
        for policy, width in configurations:
            identifier = (
                f"greek:{_NAMES[model]}"
                if policy == "greek"
                else f"band:{_NAMES[model]}:width{width:g}"
            )
            rollout = policy_rollout(
                dataset,
                risk,
                universe=universe,
                policy=policy,
                model=model,
                width=0.0 if width is None else width,
            )
            with np.errstate(over="ignore", invalid="ignore"):
                raw_mse = float(np.mean(rollout["loss"] ** 2))
            complete = rollout["status"] == "completed" and np.isfinite(raw_mse)
            row = {
                "id": identifier,
                "status": "completed" if complete else "failed",
                "original_n": rollout["original_n"],
                "mse": raw_mse if complete else None,
                "raw_mse": raw_mse,
                "reason": None if complete else rollout["reason"],
            }
            if not complete and not row["reason"]:
                row["reason"] = "nonfinite original-N MSE"
            candidates.append(row)
            rollouts[identifier] = rollout
    valid = [row for row in candidates if row["status"] == "completed"]
    selected = min(valid, key=lambda row: row["mse"])["id"] if valid else None
    bands, failures = {}, {}
    for model in _MODELS:
        name = _NAMES[model]
        rows = [row for row in valid if row["id"].startswith(f"band:{name}:")]
        bands[name] = min(rows, key=lambda row: row["mse"])["id"] if rows else None
        if not rows:
            failures[name] = "all original width candidates failed or unqualified"
    return {
        "id": f"selection:{generator}:{universe}",
        "generator": generator,
        "universe": universe,
        "status": "completed" if valid else "failed",
        "reason": None if valid else "all original candidates failed",
        "original_n": len(dataset["prices"]),
        "candidates": candidates,
        "selected_bands": bands,
        "selected_baseline": selected,
        "band_failures": failures,
        "rollouts": rollouts,
        "information": "validation only; no test stream opened",
        "expense": {
            "scope": "all_validation_candidates_and_selection",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        },
    }


def fit_roster(train_datasets, *, candidate) -> dict:
    """Attempt all twelve slots, retaining original N, failures, batches and caps.

    Only training data/scales are consumed. Dataset generator identity must
    match its slot. Actual seed/universe/original N and fixed checkpoint identity
    are retained with raw_fit. No validation completion or financial approval is
    recorded. Last finite weights and update events stay in raw_fit.
    Tiny source-fixture candidates are allowed here; main must enforce its exact
    frozen candidate at the caller-owned protocol boundary.
    """
    rows, expenses = [], []
    training = candidate["training"]
    for slot in study_roster()["fits"]:
        start, cpu_start = perf_counter(), process_time()
        row = dict(slot)
        n = int(training["original_n"])
        row.update(attempted=True, original_n=n, requested_updates=int(training["updates"]))
        raw = None
        try:
            dataset = train_datasets[slot["training_generator"]]
            _dataset_shape(dataset)
            if _model(dataset["model"]) != _model(slot["training_generator"]):
                raise ValueError("training dataset generator differs from original fit slot")
            if len(dataset["prices"]) != n:
                raise ValueError("training original N differs from candidate")
            raw = fit_policy(
                dataset,
                universe=slot["universe"],
                seed=slot["initialization"],
                updates=training["updates"],
                batch_size=training["batch_size"],
                learning_rate=training["learning_rate"],
                cap_seconds=training["cap_seconds"],
            )
            if (
                raw.get("universe") != slot["universe"]
                or raw.get("seed") != slot["initialization"]
                or raw.get("original_path_count") != n
            ):
                raise ValueError("returned raw fit identity differs from original attempt")
            complete = raw["status"] == "completed" and raw["complete"]
            raw.update(
                training_generator=_NAMES[_model(dataset["model"])],
                fit_id=slot["id"],
                checkpoint_id=candidate["hedging"]["checkpoint_rule"] if complete else None,
            )
            row.update(
                status="completed" if complete else "failed",
                reason=raw["reason"],
                updates=raw["updates"],
                raw_fit=raw,
                checkpoint_id=candidate["hedging"]["checkpoint_rule"] if complete else None,
            )
        except (ValueError, KeyError, FloatingPointError, RuntimeError) as error:
            row.update(
                status="failed",
                reason=f"{type(error).__name__}: {error}",
                updates=0,
                raw_fit=raw,
                checkpoint_id=None,
            )
        elapsed = perf_counter() - start
        row.update(
            elapsed_seconds=elapsed,
            cap_seconds=float(training["cap_seconds"]),
            overrun_seconds=max(0.0, elapsed - training["cap_seconds"]),
            validation_status="not_run",
        )
        if row["status"] == "completed" and elapsed > training["cap_seconds"]:
            row.update(
                status="failed",
                reason="fit connector including setup exceeded cap",
                checkpoint_id=None,
            )
        expense = {
            "id": row["id"],
            "scope": "training",
            "status": row["status"],
            "wall_seconds": elapsed,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
            "parent_id": None,
            "reason": row["reason"],
            "overrun_seconds": row["overrun_seconds"],
        }
        row["expense"] = expense
        rows.append(row)
        expenses.append(expense)
    return {"fits": rows, "expenses": expenses, "original_fit_slots": 12, "test_opened": False}


def test_roster(dataset, risk, fits, validation, *, generator, universe) -> dict:
    """Replay eleven supplied-data slots, preserving failed fits and selections.

    This function is not test-opening authorization: the caller must pass the
    protocol boundary before loading data. No failed NN, band width or original
    denominator is replaced. Outer/raw training generator, universe, seed,
    original N and checkpoint identities must agree before NN replay; mismatched
    slots remain reason-bearing unknown cells. Four generator/universe calls
    cover all 44 cells.
    """
    _universe(universe)
    start, cpu_start = perf_counter(), process_time()
    generator = _NAMES[_model(generator)]
    if _model(dataset["model"]) != _model(generator):
        raise ValueError("dataset generator annotation differs from requested generator")
    if validation.get("generator") != generator or validation.get("universe") != universe:
        raise ValueError("validation must match generator/universe")
    fit_rows = fits["fits"] if isinstance(fits, dict) else fits
    fit_by_id = {}
    for row in fit_rows:
        if row["id"] in fit_by_id:
            raise ValueError("duplicate original fit slot")
        fit_by_id[row["id"]] = row
    fit_slots = {row["id"]: row for row in study_roster()["fits"]}
    cells = []
    for slot in study_roster()["primary_cells"]:
        if slot["generator"] != generator or slot["universe"] != universe:
            continue
        if slot["policy"] == "no_hedge":
            result = policy_rollout(dataset, risk, universe=universe, policy="none")
        elif slot["policy"] in ("greek", "band"):
            model = _model(slot["valuation"])
            selected = validation.get("selected_bands", {}).get(slot["valuation"])
            if slot["policy"] == "band" and selected is None:
                result = _unknown_rollout(dataset, "all original band width candidates failed")
            else:
                width = 0.0
                if slot["policy"] == "band":
                    prefix = f"band:{slot['valuation']}:width"
                    if not selected.startswith(prefix):
                        raise ValueError("selected width identity differs from valuation model")
                    width = float(selected[len(prefix) :])
                    completed = {
                        row["id"]
                        for row in validation["candidates"]
                        if row["status"] == "completed"
                    }
                    if selected not in completed:
                        raise ValueError(
                            "selected width lacks completed original validation candidate"
                        )
                result = policy_rollout(
                    dataset,
                    risk,
                    universe=universe,
                    policy=slot["policy"],
                    model=model,
                    width=width,
                )
        else:
            fit_id = f"fit:{slot['training_generator']}:{universe}:init{slot['initialization']}"
            fitted = fit_by_id.get(fit_id)
            if fitted is None or fitted.get("status") != "completed" or not fitted.get("raw_fit"):
                result = _unknown_rollout(dataset, "original NN fit missing or failed")
            else:
                expected = fit_slots[fit_id]
                raw_fit = fitted["raw_fit"]
                identity_valid = all(fitted.get(key) == value for key, value in expected.items())
                identity_valid &= (
                    isinstance(fitted.get("original_n"), (int, np.integer))
                    and fitted["original_n"] > 0
                    and raw_fit.get("original_path_count") == fitted["original_n"]
                    and raw_fit.get("universe") == expected["universe"]
                    and raw_fit.get("seed") == expected["initialization"]
                    and raw_fit.get("training_generator") == expected["training_generator"]
                    and raw_fit.get("fit_id") == expected["id"]
                    and fitted.get("checkpoint_id") == "last_finite_completed"
                    and raw_fit.get("checkpoint_id") == fitted.get("checkpoint_id")
                )
                if not identity_valid:
                    result = _unknown_rollout(dataset, "original NN checkpoint identity mismatch")
                    result["raw_fit_slot"] = fitted
                else:
                    result = policy_rollout(
                        dataset, risk, universe=universe, policy="nn", fit=raw_fit
                    )
        cells.append(
            {
                **slot,
                "status": result["status"],
                "reason": result["reason"],
                "original_n": result["original_n"],
                "result": result,
            }
        )
    return {
        "cells": cells,
        "original_cell_slots": 11,
        "original_n": len(dataset["prices"]),
        "generator": generator,
        "universe": universe,
        "authorization": "caller-owned protocol boundary; supplied-data replay only",
        "expense": {
            "scope": "all_eleven_supplied_data_policy_attempts",
            "wall_seconds": perf_counter() - start,
            "cpu_seconds": process_time() - cpu_start,
            "includes_children": True,
        },
    }
