"""Reserved IID short-call pilot and saved-only numerical evidence replay.

Selection uses Brownian-conditioned teacher precision and observed Poisson
counts. Raw PW/LR and common-random-number diagnostics retain their own
original denominator and finite-width targets. Smoke evidence cannot freeze.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from dataclasses import asdict
from datetime import datetime, time, timedelta
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _short_maturity_teachers as core
from hullkit.zero_dte import TradingSession

DIRECTORY = Path(__file__).resolve().parent
RAW_METHODS = ("price", "pw_delta", "lr_delta", "lrpw_gamma", "lr2_gamma", "naive_gamma")
MOMENT_ARRAYS = ("mean", "m2_matrix", "covariance", "se")
COMPACT_ARRAYS = ("zero_values", "active_indices", "active_counts", "z_jump", "active_values")
COST_SCOPE = "all N counts/active marks/conditioned values, raw independent draws/engine/summary, references; serialization separate"
RUN_SCOPE = (
    "API entry through compressed NPZ and first JSON write; final accounting JSON write excluded"
)
REFERENCE_TIMERS = {
    "independent_mixture_s",
    "core_mixture_s",
    "density_quad_s",
    "density_quad_tight_s",
    "merton_s",
    "finite_differences_s",
}
STREAM_TIMERS = {
    "selection_generation_s": "selection_generation",
    "selection_summary_s": "selection_prefix_summary",
    "raw_rng_s": "raw_rng",
    "raw_engine_and_summary_s": "raw_engine_and_summary",
}


def _module(name):
    spec = importlib.util.spec_from_file_location(f"short_pilot_{name}", DIRECTORY / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


protocol = _module("protocol")
reference = _module("reference_methods")


def _plain(value):
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _store(arrays, prefix, name, value):
    key = f"{prefix}__{name}"
    a = np.asarray(value)
    if a.dtype.hasobject:
        raise ValueError("object arrays are not pilot evidence")
    arrays[key] = a.copy()
    return key


def _pack(values, arrays, prefix):
    return {
        f"{k}_key": _store(arrays, prefix, k, v) if isinstance(v, np.ndarray) else None
        for k, v in values.items()
        if isinstance(v, np.ndarray)
    } | {k: _plain(v) for k, v in values.items() if not isinstance(v, np.ndarray)}


def _unpack(saved, arrays):
    return {
        k[:-4]: np.asarray(arrays[v]) if k.endswith("_key") else v
        for k, v in saved.items()
        if k.endswith("_key")
    } | {k: v for k, v in saved.items() if not k.endswith("_key")}


def _equal(actual, expected, name):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape:
        raise ValueError(f"numerical shape mismatch: {name}")
    if np.issubdtype(b.dtype, np.integer):
        valid = np.issubdtype(a.dtype, np.integer) and np.array_equal(a, b)
    else:
        valid = (
            np.isfinite(a).all()
            and np.isfinite(b).all()
            and np.allclose(a, b, rtol=1e-10, atol=1e-12)
        )
    if not valid:
        raise ValueError(f"numerical mismatch: {name}")


def _compare(saved, expected, arrays, name):
    restored = _unpack(saved, arrays)
    _compare_tree(restored, expected, name)


def _compare_tree(restored, expected, name):
    if isinstance(expected, dict):
        if not isinstance(restored, dict) or set(restored) != set(expected):
            raise ValueError(f"saved fields changed: {name}")
        for key, value in expected.items():
            _compare_tree(restored[key], value, f"{name} {key}")
    elif isinstance(expected, (list, tuple)):
        if not isinstance(restored, (list, tuple)) or len(restored) != len(expected):
            raise ValueError(f"saved sequence changed: {name}")
        for i, (actual, value) in enumerate(zip(restored, expected, strict=True)):
            _compare_tree(actual, value, f"{name} {i}")
    elif isinstance(expected, np.ndarray) or isinstance(expected, (float, np.floating)):
        _equal(restored, expected, name)
    elif restored != _plain(expected):
        raise ValueError(f"saved metadata changed: {name}")


def _failure(exc):
    return dict(type=type(exc).__name__, message=str(exc))


def _not_run_streams(execution, reason):
    return [
        dict(replica=i, status="not_run", reason=reason, actual_random_draws=0)
        for i in range(execution["streams"])
    ]


def _confirm_failure(saved, exc, name):
    if saved != _failure(exc):
        raise ValueError(f"saved mathematical failure changed: {name}")


def _check_expenses(record):
    def measured(timers, keys, name):
        if not isinstance(timers, dict) or set(timers) != set(keys):
            raise ValueError(f"complete status-specific timing roster required: {name}")
        if any(not np.isfinite(value) or value < 0 for value in timers.values()):
            raise ValueError(f"finite nonnegative measured timing required: {name}")

    root = record.get("timings", {})
    if set(root) != {"setup_s", "serialization_s", "run_s", "scope"}:
        raise ValueError("complete root timing roster required")
    if root["scope"] != RUN_SCOPE or record.get("cost_scope") != COST_SCOPE:
        raise ValueError("measured cost scope changed")
    measured(
        {k: v for k, v in root.items() if k != "scope"},
        {"setup_s", "serialization_s", "run_s"},
        "root",
    )
    expected = []
    for row in record["cases"]:
        if "clock_failure_s" in row:
            if "reference_timings" in row:
                raise ValueError("clock-failed case cannot have reference timings")
            measured(
                {"clock_failure_s": row["clock_failure_s"]}, {"clock_failure_s"}, "clock failure"
            )
            _expense(expected, row["id"], "shared", "clock_failure", row["clock_failure_s"])
        else:
            keys = {"failed_attempt_s"} if "reference_failure" in row else REFERENCE_TIMERS
            timers = row.get("reference_timings", {})
            measured(timers, keys, f"{row['id']} reference")
            for name, seconds in timers.items():
                _expense(expected, row["id"], "shared", f"reference_{name}", seconds)
        for stream in row["streams"]:
            if stream.get("status") == "not_run":
                if "timings" in stream:
                    raise ValueError("unexecuted stream cannot have measured timings")
                continue
            timers = stream.get("timings", {})
            measured(timers, STREAM_TIMERS, f"{row['id']} stream {stream['replica']}")
            for field, kind in STREAM_TIMERS.items():
                _expense(expected, row["id"], stream["replica"], kind, timers[field])
    _compare_tree(
        {row["expense_id"]: row for row in record["expenses"]},
        {row["expense_id"]: row for row in expected},
        "expense/timing registry",
    )


def _validate_compact_cost(compact, state):
    n, active = compact["sample_count"], len(compact["active_indices"])
    analytic = state.jump_mean_count == 0
    status = (
        "analytic_deterministic"
        if analytic
        else "rare_event_unobserved"
        if active == 0
        else "rare_event_unresolved"
        if active < 100
        else "ready"
    )
    expected = dict(
        reserved_sample_count=n,
        observed_mc_count=0 if analytic else n,
        zero_count=0 if analytic else n - active,
        count_draws=0 if analytic else n,
        normal_draws=active,
        actual_random_draws=0 if analytic else n + active,
        normal_draw_policy="active_only",
        status=status,
    )
    if analytic and active:
        raise ValueError("analytic zero-Lambda branch cannot contain active count draws")
    _compare_tree({k: compact[k] for k in expected}, expected, "actual compact draw cost")


def _parameters(p):
    c = p["contract"]
    return core.CallParameters(c["rate"], c["dividend"], c["jump_mean"], c["jump_std"])


def _case_state(p, case):
    c = p["contract"]
    expiry = datetime.fromisoformat(c["expiry"])
    session = TradingSession(
        timezone=c["timezone"],
        open_time=time.fromisoformat(c["session_open"]),
        close_time=time.fromisoformat(c["session_close"]),
        settlement_time=time.fromisoformat(c["session_close"]),
    )
    clock = core.clock_state(
        expiry - timedelta(minutes=case["minutes"]),
        expiry,
        event=case["event"],
        session=session,
        volatility=p["clock"]["volatility"],
        weights=tuple(p["clock"]["weights"]),
    )
    distance = (
        case["distance"] * np.sqrt(clock.variance)
        if case["coordinate"] == "scaled"
        else case["distance"]
    )
    return float(c["strike"] * np.exp(distance)), float(c["strike"]), clock


def _execution(p, mode):
    if mode == "full":
        return dict(
            mode=mode,
            case_ids=[c["id"] for c in p["pilot"]["cases"]],
            streams=p["pilot"]["streams"],
            sample_candidates=p["pilot"]["sample_candidates"],
            raw_sample_count=p["pilot"]["raw_sample_count"],
        )
    if mode != "smoke":
        raise ValueError("mode must be full or smoke")
    # Both regimes at the primary 30-minute ATM contract, explicitly reduced.
    cases = [
        next(
            c["id"]
            for c in p["pilot"]["cases"]
            if c["minutes"] == 30
            and c["event"] == event
            and c["coordinate"] == "scaled"
            and c["distance"] == 0
        )
        for event in [0, 1]
    ]
    return dict(
        mode=mode, case_ids=cases, streams=1, sample_candidates=[128, 512], raw_sample_count=512
    )


def _tolerance(p, truth):
    return np.asarray(p["pilot"]["absolute_reference_tolerance"]) + np.asarray(
        p["pilot"]["relative_reference_tolerance"]
    ) * np.abs(truth)


def _reference_values(S, K, state, parameters, p):
    nmax = p["reference_nmax"]
    timers = {}
    start = perf_counter()
    mixture = reference.independent_mixture(S, K, state, parameters, nmax=nmax)
    timers["independent_mixture_s"] = perf_counter() - start
    start = perf_counter()
    production = core.mixture_values(S, K, state, parameters, nmax=nmax)
    timers["core_mixture_s"] = perf_counter() - start
    tol = _tolerance(p, mixture["values"])
    # Errors are numerical estimates, not certified bounds. Tightening is separate.
    epsabs = min(1e-10, float(np.min(tol)) * p["pilot"]["quadrature_budget_fraction"])
    start = perf_counter()
    quad = reference.density_quad(S, K, state, parameters, nmax=nmax, epsabs=epsabs, epsrel=1e-10)
    timers["density_quad_s"] = perf_counter() - start
    start = perf_counter()
    tight = reference.density_quad(
        S, K, state, parameters, nmax=nmax, epsabs=epsabs / 4, epsrel=2.5e-11
    )
    timers["density_quad_tight_s"] = perf_counter() - start
    start = perf_counter()
    merton = reference.merton_price_check(S, K, state, parameters, nmax=nmax)
    timers["merton_s"] = perf_counter() - start
    widths = tuple(
        sorted((x * np.sqrt(state.variance) for x in p["pilot"]["crn_scaled_bumps"]), reverse=True)
    )
    start = perf_counter()
    bumps = reference.spot_finite_differences(
        S, K, state, parameters, nmax=nmax, relative_steps=widths
    )
    timers["finite_differences_s"] = perf_counter() - start
    fraction = p["pilot"]["quadrature_budget_fraction"]
    primary_ok = (
        np.all(np.abs(production["values"] - mixture["values"]) <= tol)
        and np.all(np.abs(quad["values"] - mixture["values"]) <= tol)
        and np.all(np.abs(tight["values"] - quad["values"]) <= fraction * tol)
        and np.all(np.maximum(quad["error_estimates"], tight["error_estimates"]) <= fraction * tol)
        and np.all(production["tail_bounds"] <= fraction * tol)
        and np.all(mixture["tail_bounds"] <= fraction * tol)
        and abs(merton["difference"]) <= tol[0]
        and quad["status"] != "nonfinite"
        and tight["status"] != "nonfinite"
        and not any(t.get("primary_quadrature_messages") for t in quad["terms"] if t["weight"] > 0)
        and not any(t.get("primary_quadrature_messages") for t in tight["terms"] if t["weight"] > 0)
    )
    values = dict(
        values=mixture["values"],
        tail_bounds=mixture["tail_bounds"],
        core_values=production["values"],
        core_tail_bounds=production["tail_bounds"],
        quad_values=quad["values"],
        quad_errors=quad["error_estimates"],
        tight_values=tight["values"],
        tight_errors=tight["error_estimates"],
        tolerance=tol,
        quad_recalculation_difference=tight["values"] - quad["values"],
        count_ids=np.asarray([t["count"] for t in mixture["terms"]], dtype=np.int64),
        count_weights=np.asarray([t["weight"] for t in mixture["terms"]]),
        count_values=np.asarray([t["values"] for t in mixture["terms"]]),
        finite_steps=np.asarray([b["step"] for b in bumps]),
        finite_values=np.asarray([[b["delta"], b["gamma"]] for b in bumps]),
        finite_bias=np.asarray([[b["delta"], b["gamma"]] for b in bumps]) - mixture["values"][1:],
        quad_lr_gamma=float(quad["lr_gamma"]),
        quad_lr_gamma_error=float(quad["lr_gamma_error_estimate"]),
        tight_lr_gamma=float(tight["lr_gamma"]),
        tight_lr_gamma_error=float(tight["lr_gamma_error_estimate"]),
        quad_status=quad["status"],
        tight_status=tight["status"],
        quad_messages=quad["quadrature_messages"],
        tight_messages=tight["quadrature_messages"],
        merton_price=merton["price"],
        merton_difference=merton["difference"],
        nmax=nmax,
        epsabs=epsabs,
        epsrel=1e-10,
        primary_passed=bool(primary_ok),
        lr_gamma_diagnostic_supported=bool(
            abs(quad["lr_gamma"] - mixture["values"][2])
            <= 8 * quad["lr_gamma_error_estimate"] + tol[2]
        ),
    )
    return values, timers


def _selection_gate(moments, state, truth, K, p):
    settings = p["pilot"]
    rare_ok = (
        state.jump_mean_count == 0 or moments["active_count"] >= settings["minimum_active_count"]
    )
    limits = np.array(
        [
            settings["max_price_se"],
            settings["max_delta_se"],
            settings["max_scaled_gamma_se_fraction"] * max(1.0, abs(K * truth[2])) / K,
        ]
    )
    precision = moments["se"] <= limits
    agreement = np.abs(moments["mean"] - truth) <= settings["se_multiple"] * moments[
        "se"
    ] + _tolerance(p, truth)
    return dict(
        ready=bool(rare_ok and precision.all() and agreement.all()),
        rare_supported=bool(rare_ok),
        precision_passed=precision,
        reference_agreement=agreement,
        precision_limits=limits,
    )


def _joint(values):
    shifted = values - values[0]
    average = shifted.mean(0)
    deviations = shifted - average
    m2 = deviations.T @ deviations
    n = len(values)
    return dict(
        mean=values[0] + average,
        m2_matrix=m2,
        covariance=m2 / (n - 1),
        se=np.sqrt(np.maximum(np.diag(m2), 0) / (n * (n - 1))),
    )


def _raw_values(S, K, state, parameters, counts, zb, zj, ref, p):
    raw = core.path_values(S, K, state, parameters, counts, zb, zj)
    matrix = np.column_stack([raw[name] for name in RAW_METHODS])
    moments = _joint(matrix)
    target_components = [0, 1, 1, 2, 2, 2]
    methods = {}
    for i, name in enumerate(RAW_METHODS):
        target = float(ref["values"][target_components[i]])
        mean, se = float(moments["mean"][i]), float(moments["se"][i])
        tol = float(_tolerance(p, ref["values"])[target_components[i]])
        supported = abs(mean - target) <= p["pilot"]["se_multiple"] * se + tol
        status = (
            "negative_control"
            if name == "naive_gamma"
            else "diagnostic_inconclusive"
            if se == 0 and abs(target) > tol
            else "supported"
            if supported
            else "unsupported"
        )
        methods[name] = dict(
            mean=mean,
            se=se,
            target=target,
            difference=mean - target,
            supported=bool(supported and name != "naive_gamma"),
            status=status,
            nonzero_count=int(np.count_nonzero(matrix[:, i])),
        )
    multiplier = raw["terminal_spot"] / S
    discount = np.exp(-parameters.rate * state.carry_years)
    crn = []
    for scale in p["pilot"]["crn_scaled_bumps"]:
        h = S * np.sqrt(state.variance) * scale
        plus = discount * np.maximum((S + h) * multiplier - K, 0.0)
        minus = discount * np.maximum((S - h) * multiplier - K, 0.0)
        samples = np.column_stack(
            ((plus - minus) / (2 * h), (plus + minus - 2 * raw["price"]) / (h * h))
        )
        summary = _joint(samples)
        where = np.flatnonzero(np.isclose(ref["finite_steps"], h, rtol=1e-12, atol=1e-15))
        if len(where) != 1:
            raise ValueError("unique independent finite-h reference required")
        target = ref["finite_values"][where[0]]
        bias = target - ref["values"][1:]
        tolerance = _tolerance(p, ref["values"])[1:]
        supported = (
            np.abs(summary["mean"] - target)
            <= p["pilot"]["se_multiple"] * summary["se"] + tolerance
        )
        crossings = int(np.count_nonzero(((S - h) * multiplier < K) & ((S + h) * multiplier > K)))
        status = ["supported" if passed else "unsupported" for passed in supported]
        if crossings == 0 and abs(target[1]) > tolerance[1]:
            status[1] = "diagnostic_inconclusive"
            supported[1] = False
        crn.append(
            dict(
                scale=scale,
                step=h,
                target=target,
                finite_h_bias=bias,
                crossing_count=crossings,
                status=status,
                supported=supported,
                **summary,
            )
        )
    log_returns = np.log(raw["terminal_spot"] / S)
    centered_squared = (log_returns - log_returns.mean()) ** 2
    diagnostics = np.column_stack((raw["terminal_spot"], centered_squared))
    diag = _joint(diagnostics)
    expected = np.array(
        [
            S * reference.terminal_moment(1, state, parameters),
            state.variance
            + state.jump_mean_count * (parameters.jump_mean**2 + parameters.jump_std**2),
        ]
    )
    return dict(
        joint_mean=moments["mean"],
        joint_m2_matrix=moments["m2_matrix"],
        joint_covariance=moments["covariance"],
        joint_se=moments["se"],
        methods=methods,
        martingale_log_variance_mean=diag["mean"],
        martingale_log_variance_se=diag["se"],
        martingale_log_variance_target=expected,
        martingale_log_variance_supported=np.abs(diag["mean"] - expected)
        <= p["pilot"]["se_multiple"] * diag["se"] + np.array([1e-9, 1e-12]),
        crn=crn,
    )


def _seeds(p, case_id, replica, kind):
    base = f"pilot/{kind}/{case_id}/{replica}"
    names = ["count", "jump"] if kind == "selection" else ["count", "jump", "brown"]
    return {f"{name}_seed": protocol.seed_for(p, f"{base}/{name}") for name in names}


def _expense(expenses, case_id, replica, kind, seconds):
    expenses.append(
        dict(
            expense_id=f"pilot/{case_id}/{replica}/{kind}",
            seconds=float(seconds),
            methods=["price_only", "delta_dml"]
            if kind.startswith("selection")
            else ["research_diagnostics"],
            kind=kind,
        )
    )


def _raw_pack(raw, arrays, prefix):
    body = dict(raw)
    crn = body.pop("crn")
    saved = _pack(body, arrays, prefix)
    saved["crn"] = [_pack(row, arrays, f"{prefix}_crn{i}") for i, row in enumerate(crn)]
    return saved


def _raw_compare(saved, expected, arrays, name):
    original = dict(saved)
    original_crn = original.pop("crn")
    body = dict(expected)
    crn = body.pop("crn")
    _compare(original, body, arrays, name)
    if len(original_crn) != len(crn):
        raise ValueError("original CRN widths changed")
    for i, (stored, replayed) in enumerate(zip(original_crn, crn, strict=True)):
        _compare(stored, replayed, arrays, f"{name} CRN finite-h {i}")


def run_pilot(p, directory, mode="full"):
    """Run one explicit candidate pilot, save typed evidence and all original slots.

    Full generation requires all financial sources before drawing. Full selection
    draws max candidate N once per slot/stream and reuses nested prefixes. Raw
    diagnostics draw their own independent count/Brownian/mark streams. Existing
    JSON/NPZ evidence is never overwritten. This API does not freeze a protocol.
    """
    started = perf_counter()
    protocol.validate_protocol(p)
    if p["state"] != "candidate":
        raise ValueError("pilot requires an explicit candidate protocol")
    registry = protocol.source_registry(require_complete=mode == "full")
    execution = _execution(p, mode)
    directory = Path(directory)
    if (directory / "pilot.json").exists() or (directory / "pilot.npz").exists():
        raise FileExistsError("existing pilot evidence cannot be overwritten")
    record = dict(
        schema="RB-F05-short-pilot-v1",
        phase="pilot",
        smoke=mode == "smoke",
        complete=True,
        protocol=copy.deepcopy(p),
        protocol_digest=protocol.json_digest(p),
        source_registry=registry,
        execution=execution,
        cases=[],
        expenses=[],
        timings={"setup_s": perf_counter() - started},
        cost_scope=COST_SCOPE,
    )
    arrays = {}
    parameters = _parameters(p)
    roster = {c["id"]: c for c in p["pilot"]["cases"]}
    for case_id in execution["case_ids"]:
        definition = roster[case_id]
        began = perf_counter()
        try:
            S, K, state = _case_state(p, definition)
        except (ValueError, OverflowError, FloatingPointError) as exc:
            failed_s = perf_counter() - began
            row = dict(
                definition,
                clock_failure=_failure(exc),
                clock_failure_s=failed_s,
                streams=_not_run_streams(execution, "clock_failure"),
            )
            _expense(record["expenses"], case_id, "shared", "clock_failure", failed_s)
            record["cases"].append(row)
            record["complete"] = False
            continue
        row = dict(definition, S=S, K=K, state=asdict(state), streams=[])
        began = perf_counter()
        try:
            ref, reference_timers = _reference_values(S, K, state, parameters, p)
        except (ValueError, OverflowError, FloatingPointError) as exc:
            failed_s = perf_counter() - began
            row["reference_failure"] = _failure(exc)
            row["reference_timings"] = {"failed_attempt_s": failed_s}
            row["streams"] = _not_run_streams(execution, "reference_failure")
            _expense(record["expenses"], case_id, "shared", "reference_failed_attempt_s", failed_s)
            record["cases"].append(row)
            record["complete"] = False
            continue
        row["reference"] = _pack(ref, arrays, f"{case_id}_reference")
        row["reference_timings"] = reference_timers
        for name, seconds in reference_timers.items():
            _expense(record["expenses"], case_id, "shared", f"reference_{name}", seconds)
        for replica in range(execution["streams"]):
            name = f"{case_id}_{replica}"
            stream = dict(replica=replica, prefixes=[])
            selection_seeds = _seeds(p, case_id, replica, "selection")
            began = perf_counter()
            compact = core.compact_teacher(
                S,
                K,
                state,
                parameters,
                sample_count=max(execution["sample_candidates"]),
                **selection_seeds,
            )
            selection_s = perf_counter() - began
            stream["selection"] = _pack({**compact, **selection_seeds}, arrays, f"{name}_selection")
            _expense(record["expenses"], case_id, replica, "selection_generation", selection_s)
            began = perf_counter()
            for n in execution["sample_candidates"]:
                moments = core.compact_moments(compact, sample_count=n)
                gate = _selection_gate(moments, state, ref["values"], K, p)
                stream["prefixes"].append(
                    _pack(dict(sample_count=n, **moments, **gate), arrays, f"{name}_prefix{n}")
                )
            summary_s = perf_counter() - began
            _expense(record["expenses"], case_id, replica, "selection_prefix_summary", summary_s)
            n = execution["raw_sample_count"]
            raw_seeds = _seeds(p, case_id, replica, "raw")
            began = perf_counter()
            counts = np.random.default_rng(raw_seeds["count_seed"]).poisson(
                state.jump_mean_count, n
            )
            zj = np.random.default_rng(raw_seeds["jump_seed"]).standard_normal(n)
            zb = np.random.default_rng(raw_seeds["brown_seed"]).standard_normal(n)
            rng_s = perf_counter() - began
            began = perf_counter()
            try:
                raw = _raw_values(S, K, state, parameters, counts, zb, zj, ref, p)
                raw_status = "evaluated"
            except (ValueError, OverflowError, FloatingPointError) as exc:
                raw = dict(failure=_failure(exc), crn=[])
                raw_status = "mathematical_failure"
                record["complete"] = False
            engine_summary_s = perf_counter() - began
            stream["raw"] = _raw_pack(
                dict(
                    raw,
                    counts=counts,
                    z_brown=zb,
                    z_jump=zj,
                    **raw_seeds,
                    sample_count=n,
                    status=raw_status,
                    actual_random_draws=3 * n,
                    normal_draw_policy="full_N_diagnostic",
                ),
                arrays,
                f"{name}_raw",
            )
            stream["timings"] = dict(
                selection_generation_s=selection_s,
                selection_summary_s=summary_s,
                raw_rng_s=rng_s,
                raw_engine_and_summary_s=engine_summary_s,
            )
            _expense(record["expenses"], case_id, replica, "raw_rng", rng_s)
            _expense(
                record["expenses"], case_id, replica, "raw_engine_and_summary", engine_summary_s
            )
            row["streams"].append(stream)
        record["cases"].append(row)
    directory.mkdir(parents=True, exist_ok=True)
    began = perf_counter()
    np.savez_compressed(directory / "pilot.npz", **arrays)
    (directory / "pilot.json").write_text(
        json.dumps(_plain(record), sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    record["timings"]["serialization_s"] = perf_counter() - began
    record["timings"]["run_s"] = perf_counter() - started
    record["timings"]["scope"] = RUN_SCOPE
    record = _plain(record)
    (directory / "pilot.json").write_text(
        json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    return record, arrays


def load_result(directory):
    """Read saved JSON and non-object NPZ arrays without sampling or mutation."""
    directory = Path(directory)
    record = json.loads((directory / "pilot.json").read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as bundle:
        arrays = {key: bundle[key].copy() for key in bundle.files}
    return record, arrays


def check_record(record, arrays):
    """Numerically replay saved pilot evidence with no RNG, optimizer or learning.

    Malformed/corrupted values raise ValueError. Legitimate incomplete precision
    or raw diagnostic non-support remains in the returned readiness/unknown flags.
    Smoke can pass numerical replay but can never pass the full-pilot freeze gate.
    """
    if record.get("schema") != "RB-F05-short-pilot-v1" or record.get("phase") != "pilot":
        raise ValueError("unknown pilot evidence")
    p = protocol.validate_protocol(record["protocol"])
    if p["state"] != "candidate" or record["protocol_digest"] != protocol.json_digest(p):
        raise ValueError("candidate protocol binding changed")
    mode = "smoke" if record["smoke"] else "full"
    execution = _execution(p, mode)
    if record["execution"] != execution:
        raise ValueError("original execution roster changed")
    if record["source_registry"] != protocol.source_registry(require_complete=mode == "full"):
        raise ValueError("pilot financial source changed")
    if [row["id"] for row in record["cases"]] != execution["case_ids"]:
        raise ValueError("original case roster changed")
    if any(np.asarray(a).dtype.hasobject for a in arrays.values()):
        raise ValueError("object arrays are not evidence")
    if len({e["expense_id"] for e in record["expenses"]}) != len(record["expenses"]):
        raise ValueError("duplicate pilot expense")
    for expense in record["expenses"]:
        if not np.isfinite(expense["seconds"]) or expense["seconds"] < 0:
            raise ValueError("finite nonnegative measured expense required")
    for name, value in record["timings"].items():
        if name.endswith("_s") and (not np.isfinite(value) or value < 0):
            raise ValueError("finite nonnegative pilot timing required")
    parameters = _parameters(p)
    definitions = {c["id"]: c for c in p["pilot"]["cases"]}
    all_ready = {n: True for n in execution["sample_candidates"]}
    reference_passed = True
    raw_support = {}
    raw_replays = 0
    clock_failures = reference_failures = raw_failures = 0
    for row in record["cases"]:
        case_id = row["id"]
        definition = definitions[case_id]
        if any(row[k] != v for k, v in definition.items()):
            raise ValueError("original case definition changed")
        try:
            S, K, state = _case_state(p, definition)
        except (ValueError, OverflowError, FloatingPointError) as exc:
            _confirm_failure(row.get("clock_failure"), exc, "clock")
            _compare_tree(
                row["streams"],
                _not_run_streams(execution, "clock_failure"),
                "failed clock stream roster",
            )
            clock_failures += 1
            reference_passed = False
            continue
        if "clock_failure" in row:
            raise ValueError("saved clock failure cannot be reproduced")
        _equal([row["S"], row["K"]], [S, K], "case spot/strike")
        for field, value in asdict(state).items():
            if isinstance(value, str):
                if row["state"][field] != value:
                    raise ValueError("clock status changed")
            else:
                _equal(row["state"][field], value, f"clock {field}")
        try:
            ref, _ = _reference_values(S, K, state, parameters, p)
        except (ValueError, OverflowError, FloatingPointError) as exc:
            _confirm_failure(row.get("reference_failure"), exc, "reference")
            _compare_tree(
                row["streams"],
                _not_run_streams(execution, "reference_failure"),
                "failed reference stream roster",
            )
            reference_failures += 1
            reference_passed = False
            continue
        if "reference_failure" in row:
            raise ValueError("saved reference failure cannot be reproduced")
        _compare(row["reference"], ref, arrays, f"{case_id} reference")
        reference_passed &= ref["primary_passed"]
        if [s["replica"] for s in row["streams"]] != list(range(execution["streams"])):
            raise ValueError("original stream roster changed")
        for stream in row["streams"]:
            replica = stream["replica"]
            compact = _unpack(stream["selection"], arrays)
            seeds = _seeds(p, case_id, replica, "selection")
            if any(compact.get(k) != v for k, v in seeds.items()):
                raise ValueError("reserved selection seed changed")
            if compact["sample_count"] != max(execution["sample_candidates"]):
                raise ValueError("original maximum sample count changed")
            _validate_compact_cost(compact, state)
            indices = compact["active_indices"]
            counts = compact["active_counts"]
            marks = compact["z_jump"]
            if (
                indices.ndim != 1
                or counts.shape != indices.shape
                or marks.shape != indices.shape
                or not np.issubdtype(counts.dtype, np.integer)
                or np.any(counts <= 0)
                or not np.isfinite(marks).all()
            ):
                raise ValueError("invalid original active counts/marks")
            _equal(
                compact["zero_values"],
                core.conditional_values(S, K, state, parameters, 0, 0.0),
                "zero conditioned values",
            )
            _equal(
                compact["active_values"],
                core.conditional_values(S, K, state, parameters, counts, marks),
                "active conditioned values",
            )
            analytic = state.jump_mean_count == 0
            actual = 0 if analytic else compact["sample_count"] + len(indices)
            if (
                compact["actual_random_draws"] != actual
                or compact["normal_draw_policy"] != "active_only"
            ):
                raise ValueError("actual selection draw cost or policy changed")
            if compact["observed_mc_count"] != (0 if analytic else compact["sample_count"]):
                raise ValueError("observed MC count changed")
            if [x["sample_count"] for x in stream["prefixes"]] != execution["sample_candidates"]:
                raise ValueError("original prefix roster changed")
            for saved in stream["prefixes"]:
                n = saved["sample_count"]
                moments = core.compact_moments(compact, sample_count=n)
                gate = _selection_gate(moments, state, ref["values"], K, p)
                _compare(saved, dict(sample_count=n, **moments, **gate), arrays, "prefix moments")
                all_ready[n] &= gate["ready"]
            raw = _unpack({k: v for k, v in stream["raw"].items() if k != "crn"}, arrays)
            raw_seeds = _seeds(p, case_id, replica, "raw")
            if any(raw.get(k) != v for k, v in raw_seeds.items()):
                raise ValueError("reserved raw seed changed")
            n = execution["raw_sample_count"]
            if (
                raw["sample_count"] != n
                or raw["actual_random_draws"] != 3 * n
                or raw["counts"].shape != (n,)
                or raw["z_jump"].shape != (n,)
                or raw["z_brown"].shape != (n,)
            ):
                raise ValueError("original raw count/draw cost changed")
            try:
                values = _raw_values(
                    S, K, state, parameters, raw["counts"], raw["z_brown"], raw["z_jump"], ref, p
                )
                replay_status = "evaluated"
            except (ValueError, OverflowError, FloatingPointError) as exc:
                _confirm_failure(raw.get("failure"), exc, "raw")
                values = dict(failure=_failure(exc), crn=[])
                replay_status = "mathematical_failure"
                raw_failures += 1
            replay = dict(
                values,
                counts=raw["counts"],
                z_brown=raw["z_brown"],
                z_jump=raw["z_jump"],
                **raw_seeds,
                sample_count=n,
                status=replay_status,
                actual_random_draws=3 * n,
                normal_draw_policy="full_N_diagnostic",
            )
            _raw_compare(stream["raw"], replay, arrays, "raw")
            if replay_status == "mathematical_failure":
                continue
            for method, outcome in values["methods"].items():
                key = f"{method}/{outcome['status']}"
                raw_support[key] = raw_support.get(key, 0) + 1
            for crn in values["crn"]:
                for component, status in zip(["delta", "gamma"], crn["status"], strict=True):
                    key = f"crn_{component}/{status}"
                    raw_support[key] = raw_support.get(key, 0) + 1
            raw_replays += 1
    if record["complete"] != (clock_failures + reference_failures + raw_failures == 0):
        raise ValueError("original pilot completion/failure state changed")
    _check_expenses(record)
    ready = [n for n in execution["sample_candidates"] if all_ready[n] and reference_passed]
    selected = min(ready) if ready and not record["smoke"] and record["complete"] else None
    reasons = ["smoke_not_freezable"] if record["smoke"] else []
    if not reference_passed:
        reasons.append("independent_reference_precision_unresolved")
    if not ready:
        reasons.append("conditioned_precision_or_rare_event_unresolved")
    if not record["complete"]:
        reasons.append("incomplete_original_pilot")
    return dict(
        passed=selected is not None,
        selected_sample_count=selected,
        numerical_replay_passed=True,
        reasons=reasons,
        ready_sample_candidates=ready,
        case_count=len(record["cases"]),
        stream_count=execution["streams"],
        raw_replay_count=raw_replays,
        clock_failure_count=clock_failures,
        reference_failure_count=reference_failures,
        raw_failure_count=raw_failures,
        reference_precision_passed=bool(reference_passed),
        raw_diagnostic_status_counts=raw_support,
    )


def main():
    """CLI runs explicit candidate pilots or saved-only numerical checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--mode", choices=["full", "smoke"], default="full")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    if args.check:
        record, arrays = load_result(args.check)
        print(json.dumps(check_record(record, arrays), sort_keys=True))
    else:
        if not args.protocol or not args.output:
            parser.error("--protocol and --output are required for generation")
        record, arrays = run_pilot(protocol.load_protocol(args.protocol), args.output, args.mode)
        print(json.dumps(dict(cases=len(record["cases"]), mode=args.mode, output=str(args.output))))


if __name__ == "__main__":
    main()
