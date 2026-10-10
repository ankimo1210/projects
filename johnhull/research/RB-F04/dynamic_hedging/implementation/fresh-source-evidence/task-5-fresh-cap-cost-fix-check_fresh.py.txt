"""Saved-only arithmetic verification of immutable reserved fresh evidence.

No RNG, CF/PDE solve, MC, teacher generation, optimizer or training is invoked.
All original paths, full call roots, paired samples and actual expenses remain.
This checks the saved boundary; earlier path generation and original artifact
byte authentication remain independent responsibilities. SHA is provenance,
never a substitute for the calculations below or financial qualification.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if __name__ == "__main__":
    sys.path[:0] = [str(ROOT / "johnhull/hullkit/src"), str(ROOT / "deep_hedge_price/src")]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _same(actual, saved, label):
    if isinstance(actual, dict):
        _require(
            isinstance(saved, dict) and set(actual) == set(saved), label + " saved keyset mismatch"
        )
        for key, value in actual.items():
            _same(value, saved[key], label + "." + key)
        return
    if actual is None or saved is None:
        _require(actual is None and saved is None, label + " unknown changed")
        return
    if isinstance(actual, (list, tuple)) and isinstance(saved, (list, tuple)):
        _require(len(actual) == len(saved), label + " sequence length changed")
        for i, (a, b) in enumerate(zip(actual, saved, strict=True)):
            _same(a, b, f"{label}[{i}]")
        return
    a, b = np.asarray(actual), np.asarray(saved)
    _require(a.shape == b.shape, label + " saved shape changed")
    equal = (
        np.allclose(a, b, rtol=2e-10, atol=2e-11, equal_nan=True)
        if a.dtype.kind in "buifc" and b.dtype.kind in "buifc"
        else np.array_equal(a, b)
    )
    _require(equal, label + " saved value changed")


def _clock(row, label, *, require_cpu=True):
    clock = row["clock"]
    start, stop = clock["wall_start"], clock["wall_stop"]
    _require(np.isfinite([start, stop]).all() and stop >= start, label + " wall clock invalid")
    elapsed = stop - start
    _require(
        np.isfinite(row["wall_seconds"]) and row["wall_seconds"] >= 0,
        label + " elapsed wall invalid",
    )
    _same(elapsed, row["wall_seconds"], label + " elapsed wall")
    if require_cpu:
        _require(
            {"cpu_start", "cpu_stop"} <= set(clock) and "cpu_seconds" in row,
            label + " measured CPU clock required",
        )
        cpu_start, cpu_stop, cpu_seconds = clock["cpu_start"], clock["cpu_stop"], row["cpu_seconds"]
        _require(
            np.isfinite([cpu_start, cpu_stop, cpu_seconds]).all()
            and cpu_stop >= cpu_start >= 0
            and cpu_seconds >= 0,
            label + " actual CPU measurement invalid",
        )
        _same(cpu_stop - cpu_start, cpu_seconds, label + " elapsed CPU")
    deadline = row.get("deadline_wall")
    if deadline is not None:
        _require(np.isfinite(deadline), label + " deadline invalid")
        _same(max(0.0, stop - deadline), row["overrun_seconds"], label + " actual overrun")
    return elapsed


def _clock_equal(actual, expected, label):
    _require(
        np.isfinite([actual, expected]).all()
        and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8),
        label + " clock binding changed",
    )


def _interval(child, parent, label, *, require_cpu=True):
    """Actual cost intervals are nested; wall caps do not supply CPU costs."""
    _clock(child, label, require_cpu=require_cpu)
    for kind in ["wall", "cpu"] if require_cpu else ["wall"]:
        c, p = child["clock"], parent["clock"]
        _require(
            p[kind + "_start"] <= c[kind + "_start"] <= c[kind + "_stop"] <= p[kind + "_stop"],
            label + " actual " + kind + " interval outside parent",
        )
    _require(child.get("deadline_wall") is not None, label + " actual enclosing deadline required")
    _clock_equal(child["deadline_wall"], parent["deadline_wall"], label + " enclosing deadline")


def _cap(row, *, statuses=None, labels=None, planned=None, completed=None):
    if row is None:
        return
    _require(
        row["financial_qualification"] == "unknown",
        "cap evidence may not claim financial qualification",
    )
    # A deadline receipt has wall clocks only; measured expense receipts also require CPU.
    _clock(row, "cap", require_cpu=False)
    cap = row["cap_seconds"]
    _require(np.isfinite(cap) and cap >= 0, "cap must retain actual nonnegative effective budget")
    _require(
        "budget_wall_start" in row and row.get("deadline_wall") is not None,
        "cap actual start/deadline binding required",
    )
    _clock_equal(row["budget_wall_start"] + cap, row["deadline_wall"], "cap budget deadline")
    _require(
        row["clock"]["wall_start"] >= row["budget_wall_start"], "cap actual start predates budget"
    )
    _same(
        max(0.0, row["clock"]["wall_stop"] - row["deadline_wall"]),
        row["overrun_seconds"],
        "cap actual overrun",
    )
    _require(
        row["cap_reached"] == (row["clock"]["wall_stop"] >= row["deadline_wall"]),
        "cap reached disagrees with actual clock",
    )
    if statuses is not None:
        status = np.asarray(statuses)
        remaining = np.zeros(status.shape[:-1], dtype=int)
        for value in ["unmeasured", "unmeasured_cap"]:
            if value in labels:
                remaining += np.count_nonzero(status == list(labels).index(value), axis=-1)
        _same(remaining, row["unexecuted_query_path_counts"], "cap original unexecuted paths")
        _require(
            not remaining.any() or row["cap_reached"], "missing paths without measured deadline"
        )
    if planned is not None:
        _same(planned, row["planned_cells"], "cap planned original cells")
        _same(completed, row["completed_cells"], "cap actual completed cells")
        _same(planned - completed, row["unexecuted_cell_count"], "cap missing original cells")
        _require(
            completed == planned or row["cap_reached"], "missing call cells without measured cap"
        )


def _bind_job_cap(raw, job, label):
    """Bind producer evidence to the pretest remaining job budget, without qualification."""
    cap = raw.get("cap_evidence")
    _require(cap is not None, label + " measured cap evidence required")
    _cap(cap)
    _clock_equal(cap["cap_seconds"], job["effective_wall_cap_seconds"], label + " effective cap")
    _clock_equal(cap["budget_wall_start"], job["clock"]["wall_start"], label + " budget start")
    _interval(cap, job, label + " cap", require_cpu=False)
    for expense in raw["expenses"]:
        _interval(expense, job, label + " expense")
    for driver in raw.get("driver_map", []):
        _interval(driver, job, label + " driver")
    if "cost" in raw:
        _interval(raw["cost"], job, label + " total cost")
        _clock_equal(
            cap["clock"]["wall_start"],
            raw["cost"]["clock"]["wall_start"],
            label + " measured function start",
        )
    refinement = raw.get("call_refinements")
    if refinement is not None:
        children = [e for e in raw["expenses"] if e["scope"] == "independent_call_refinement"]
        _require(len(children) == 1, label + " measured call refinement expense required")
        child, child_cap = children[0], refinement.get("cap_evidence")
        _require(child_cap is not None, label + " refinement remaining budget required")
        _cap(child_cap)
        _interval(child_cap, child, label + " refinement cap", require_cpu=False)
        budget_start = child_cap["budget_wall_start"]
        _require(
            child["clock"]["wall_start"] <= budget_start <= child_cap["clock"]["wall_start"],
            label + " refinement remaining budget start outside actual invocation",
        )
        _clock_equal(
            child_cap["cap_seconds"],
            max(0.0, job["deadline_wall"] - budget_start),
            label + " refinement remaining budget",
        )


def _statuses(record, shape):
    codes = np.asarray(record["path_status"])
    labels = np.asarray(record["path_status_labels"]).astype(str)
    _require(
        record["path_status_encoding"] == "uint16_dictionary"
        and codes.shape == shape
        and codes.dtype.kind in "ui"
        and len(labels) > 0
        and len(set(labels)) == len(labels)
        and codes.max(initial=0) < len(labels),
        "lossless original path status encoding invalid",
    )
    return codes, labels, labels[codes]


def _cf_value(row, maturity, parameters):

    # Saved zero-variance identities need no numerical quadrature.
    total = parameters["theta"] * maturity
    if parameters["kappa"] == 0:
        total = parameters["v0"] * maturity
    else:
        total += (
            (parameters["v0"] - parameters["theta"])
            * (-math.expm1(-parameters["kappa"] * maturity))
            / parameters["kappa"]
        )
    if total == 0:
        value = max(
            parameters["spot"] * math.exp(-parameters["dividend_yield"] * maturity)
            - 100.0 * math.exp(-parameters["rate"] * maturity),
            0.0,
        )
        _same([value], row["price"], "deterministic CF identity")
        _same([0.0], row["price_unit_error"], "deterministic CF error")
        _require(row["integration_receipts"] == [[]], "deterministic CF raw integral identity")
        return value, 0.0
    pairs = row["integration_receipts"]
    _require(len(pairs) == 1 and len(pairs[0]) == 2, "two saved CF probability integrals required")
    probabilities, absolute_errors = [], []
    converged = True
    for integral in pairs[0]:
        parts = np.asarray(integral["subintervals"], float)
        _require(
            parts.ndim == 2
            and parts.shape == (integral["subinterval_count"], 4)
            and len(parts) > 0,
            "actual CF adaptive subdivisions missing",
        )
        _same(parts[:, 2].sum(), integral["value"], "CF raw subdivision integral sum")
        _same(parts[:, 3].sum(), integral["absolute_error"], "CF raw subdivision error sum")
        order = np.argsort(parts[:, 0])
        ordered = parts[order]
        _require(
            np.isfinite(ordered[:, :2]).all() and np.all(ordered[:, 1] > ordered[:, 0]),
            "actual CF integration subdivisions invalid",
        )
        _same(0.0, ordered[0, 0], "CF integration lower boundary")
        _same(integral["upper"], ordered[-1, 1], "CF original integration upper boundary")
        _same(ordered[:-1, 1], ordered[1:, 0], "CF raw integration coverage/gaps")
        finite = np.isfinite(integral["value"] + integral["absolute_error"])
        _require(
            not np.isfinite(integral["absolute_error"]) or integral["absolute_error"] >= 0,
            "CF reported absolute error negative",
        )
        good = not integral["message"] and finite
        _require(
            integral["status"] == ("converged" if good else "nonconverged"),
            "CF convergence claim differs from raw diagnostics",
        )
        converged &= good
        probabilities.append(0.5 + integral["value"] / math.pi)
        absolute_errors.append(integral["absolute_error"] / math.pi)
    prepaid = parameters["spot"] * math.exp(-parameters["dividend_yield"] * maturity)
    strike_pv = 100.0 * math.exp(-parameters["rate"] * maturity)
    raw_value = prepaid * probabilities[0] - strike_pv * probabilities[1]
    error = prepaid * absolute_errors[0] + strike_pv * absolute_errors[1]
    value = raw_value if converged and np.isfinite(raw_value) else np.nan
    _same([raw_value], row["raw_prices"], "CF actual failed/converged raw estimate")
    _same([error], row["price_unit_error"], "CF raw price-unit error")
    _same([value], row["price"], "CF nonconvergence remains numerical unknown")
    _require(
        row["status"] == ("converged" if np.isfinite(value) else "unknown"),
        "CF numerical failure may not be promoted to measured",
    )
    return float(value), float(error)


def _pde_values(row, dates, spots):
    from scipy.interpolate import CubicSpline

    dates, spots = np.asarray(dates, float), np.asarray(spots, float)
    grid = np.asarray(row["spots"], float)
    values = np.asarray(row["values"], float)
    _same(dates, row["dates"], "PDE absolute snapshot dates")
    _require(
        grid.ndim == 1
        and len(grid) >= 3
        and np.all(np.diff(grid) > 0)
        and values.shape == (len(dates), len(grid)),
        "PDE raw grid/date shape",
    )
    _same(grid, row["grid"]["spots"], "PDE raw grid identity")
    _same(values, row["snapshots"][:, 0, :], "PDE primitive snapshots")
    result = np.full((len(dates), len(spots)), np.nan)
    if row["supported"] and row["failure"] is None:
        _require(np.isfinite(values).all(), "supported PDE raw snapshots must be finite")
        inside = (spots >= grid[0]) & (spots <= grid[-1])
        for d in range(len(dates)):
            result[d, inside] = CubicSpline(np.log(grid), values[d], extrapolate=False)(
                np.log(spots[inside])
            )
    return result


def _table(table, row, parameters, surface):
    from reference_methods import _field_binding, _parameters

    model = row["model"]
    _require(
        table["financial_qualification"] == "unchecked", "raw call table may not certify precision"
    )
    bounds = [1e-5, 0.5] if model == "heston" else [0.25, 4.0]
    _require(
        table["model"] == model and table["parameters"] == _parameters(parameters),
        "independent table fixed model/parameters differ",
    )
    descriptor, signature = _field_binding(surface)
    _same(descriptor, table["surface_descriptor"], "independent table full typed field")
    _same(signature, table["surface_signature"], "independent table field signature")
    nodes, dates, spots = map(
        np.asarray, (table["state_nodes"], table["dates"], table["query_spots"])
    )
    expected_spots = sorted(
        {row["spot"]}
        | {
            row["spot"] + sign * row["spot_bump"] * width
            for sign in (1, -1)
            for width in (1.0, 0.5, 2.0)
        }
    )
    _same(row["state_nodes"], nodes, "original full call domain nodes")
    _same([row["date"]], dates, "original call calendar")
    _same(expected_spots, spots, "original full S-bump spot roster")
    _same(row["call_controls"], table["controls"], "pretest call controls")
    _require(
        table["original_bounds"] == bounds and nodes[0] == bounds[0] and nodes[-1] == bounds[-1],
        "full original call domain bounds",
    )
    levels = 3 if model == "heston" else 4
    shape = (levels, len(dates), len(spots), len(nodes))
    _require(np.asarray(table["prices"]).shape == shape, "all original call cells must remain")
    rebuilt = np.full(shape, np.nan)
    error = np.full(shape, np.nan)
    seen = set()
    if model == "heston":
        for receipt in table["integration_receipts"]:
            index = tuple(
                receipt[key] for key in ("level", "date_index", "spot_index", "state_index")
            )
            _require(
                index not in seen and all(0 <= i < s for i, s in zip(index, shape, strict=True)),
                "duplicate/out-of-roster call cell",
            )
            seen.add(index)
            level, d, sp, st = index
            current = {**table["parameters"], "spot": float(spots[sp]), "v0": float(nodes[st])}
            rebuilt[index], error[index] = _cf_value(receipt, 1.25 - dates[d], current)
        completed = len(seen)
    else:
        for receipt in table["pde_receipts"]:
            level, st = receipt["level"], receipt["state_index"]
            _require(
                (level, st) not in seen and 0 <= level < levels and 0 <= st < len(nodes),
                "duplicate/out-of-roster PDE cell",
            )
            seen.add((level, st))
            rebuilt[level, :, :, st] = _pde_values(receipt, dates, spots)
        completed = len(seen) * len(dates) * len(spots)
    _same(rebuilt, table["prices"], "saved independent table prices")
    _same(error, table["price_unit_errors"], "saved independent table raw error")
    _cap(table["cap_evidence"], planned=rebuilt.size, completed=completed)
    _require(
        completed == rebuilt.size or table["cap_evidence"] is not None,
        "incomplete call table requires actual cap evidence",
    )
    expense_levels = set()
    for expense in table["expenses"]:
        _require(
            expense["level"] not in expense_levels and expense["level"] in range(levels),
            "call table actual expense levels duplicated",
        )
        expense_levels.add(expense["level"])
        _clock(expense, "call-table expense")
        _require(
            expense["scope"] == "independent_call_reference" and expense["path_steps"] == 0,
            "call table expense scope",
        )
    measured_levels = {index[0] for index in seen}
    _require(
        measured_levels <= expense_levels, "call table measured cells need original solver expenses"
    )
    return rebuilt


def _refinement(raw, row, base, parameters):
    """Reconstruct fixed three-width derivatives from saved CF/PDE receipts."""
    refinement = raw["call_refinements"]
    hv = 0.0001 if row["model"] == "heston" else 0.001
    status = raw["call_refinement_status"]
    if refinement is None:
        if base["solver_status"] == "unique_root" and base["state"] <= 2 * hv:
            _require(
                status["status"] == "unavailable_derivative_boundary",
                "positive-boundary derivative reference must remain unavailable",
            )
            _same(base["state"], status["state"], "boundary original root")
            _same(hv, status["fixed_state_bump"], "boundary original fixed bump")
            _same([1.0, 0.5, 2.0], status["width_multipliers"], "boundary all original widths")
        else:
            _require(
                status["status"] == "unmeasured",
                "unattempted reference has fabricated measured status",
            )
        return None
    _require(
        base["solver_status"] == "unique_root" and base["state"] > 2 * hv,
        "symmetric reference crosses the positive-state boundary",
    )
    inputs = dict(
        model=row["model"],
        date=row["date"],
        spot=row["spot"],
        state=base["state"],
        spot_bump=row["spot_bump"],
        state_bump=hv,
    )
    _same(inputs, refinement["inputs"], "fixed derivative-reference inputs")
    levels = 3 if row["model"] == "heston" else 4
    s, v, hs = row["spot"], base["state"], row["spot_bump"]
    queries = [(s, v)]  # no posttest width selection
    for w in (1.0, 0.5, 2.0):
        queries.extend([(s + hs * w, v), (s - hs * w, v), (s, v + hv * w), (s, v - hv * w)])
    values = np.full((levels, 13), np.nan)
    unit_errors = np.zeros_like(values)
    receipts = (
        refinement["integration_receipts"]
        if row["model"] == "heston"
        else refinement["pde_receipts"]
    )
    seen = set()
    for receipt in receipts:
        level = receipt["level"]
        matches = [
            j
            for j, (ss, vv) in enumerate(queries)
            if receipt["spot"] == ss and receipt["state"] == vv
        ]
        _require(
            0 <= level < levels and len(matches) == 1 and (level, matches[0]) not in seen,
            "original fixed call refinement query missing/duplicated",
        )
        j = matches[0]
        seen.add((level, j))
        if row["model"] == "heston":
            from reference_methods import _parameters

            current = {**_parameters(parameters), "spot": receipt["spot"], "v0": receipt["state"]}
            values[level, j], unit_errors[level, j] = _cf_value(
                receipt, 1.25 - row["date"], current
            )
        else:
            values[level, j] = _pde_values(receipt, [row["date"]], [receipt["spot"]])[0, 0]
    widths = np.empty((levels, 2, 3))
    error_widths = np.empty_like(widths)
    for i, w in enumerate((1.0, 0.5, 2.0)):
        widths[:, 0, i] = (values[:, 1 + 4 * i] - values[:, 2 + 4 * i]) / (2 * hs * w)
        widths[:, 1, i] = (values[:, 3 + 4 * i] - values[:, 4 + 4 * i]) / (2 * hv * w)
        error_widths[:, 0, i] = (unit_errors[:, 1 + 4 * i] + unit_errors[:, 2 + 4 * i]) / (
            2 * hs * w
        )
        error_widths[:, 1, i] = (unit_errors[:, 3 + 4 * i] + unit_errors[:, 4 + 4 * i]) / (
            2 * hv * w
        )
    prices, ds, dv = values[:, 0], widths[:, 0, 1], widths[:, 1, 1]
    measured = np.isfinite(prices).all() and np.isfinite(widths).all()
    computed = dict(
        status="measured" if measured else "unknown",
        price=prices[-1],
        spot_derivative=ds[-1],
        state_derivative=dv[-1],
        price_error=float(np.max(np.abs(prices - prices[0]))),
        spot_derivative_error=float(np.max(np.abs(ds - ds[0]))),
        state_derivative_error=float(np.max(np.abs(dv - dv[0]))),
        prices=prices,
        spot_derivatives=ds,
        state_derivatives=dv,
        three_width_derivatives=widths,
        finite_width_errors=np.max(np.abs(widths - widths[:, :, [1]]), axis=(0, 2)),
        price_unit_error=float(np.max(unit_errors)),
        integration_derivative_error=np.max(error_widths, axis=(0, 2)),
    )
    for key, value in computed.items():
        _same(value, refinement[key], "raw selected call " + key)
    _require(status["status"] == computed["status"], "selected call measured status differs")
    _cap(refinement["cap_evidence"], planned=levels * 13, completed=len(seen))
    _require(
        len(seen) == levels * 13 or refinement["cap_evidence"] is not None,
        "missing derivative-reference measurements require actual cap",
    )
    scale = 0.04 if row["model"] == "heston" else 1.0
    cv = computed["state_derivative"]
    diagnostic = dict(
        scope="baseline independent finite call curve versus direct CF/PDE",
        price_residual=float(computed["price"] - row["quote"]),
        state_derivative_difference=float(base["Ctheta"] - cv),
        scaled_state_derivative_difference=float(scale * abs(base["Ctheta"] - cv)),
        curve_condition_number=float(base["condition_number"]),
        direct_condition_number=0.01 / (scale * abs(cv)) if cv else np.inf,
        reference_kind="empirical_numerical_not_exact_truth",
    )
    _same(diagnostic, raw["independent_curve_diagnostics"], "direct call numerical discrepancy")
    return computed


def _query_fits(raw, row, prices):
    from reference_methods import fit_independent_quote

    queries = [(row["spot"], row["quote"])]
    for axis, bump in (("S", row["spot_bump"]), ("Q", row["quote_bump"])):
        for w in (1.0, 0.5, 2.0):
            for sign in (1, -1):
                queries.append(
                    (row["spot"] + sign * bump * w, row["quote"])
                    if axis == "S"
                    else (row["spot"], row["quote"] + sign * bump * w)
                )
    ids = ["base"] + [
        f"{a}{sign}.{w}" for a in ("S", "Q") for w in ("1", ".5", "2") for sign in ("+", "-")
    ]
    _require(
        raw["query_ids"] == ids and len(raw["query_fits"]) == 13,
        "all thirteen original call query IDs/order required",
    )
    spots = np.asarray(raw["call_table"]["query_spots"])
    nodes = raw["call_table"]["state_nodes"]
    result = []
    for identifier, (s, q), saved in zip(ids, queries, raw["query_fits"], strict=True):
        si = np.flatnonzero(np.isclose(spots, s, rtol=0, atol=1e-12))
        _require(len(si) == 1, "exact full call query spot missing")
        curves = prices[:, 0, si[0], :]
        expected = fit_independent_quote(
            nodes, curves[-1], q, model=row["model"], spot=s, query_id=identifier
        )
        for key, value in expected.items():
            _same(value, saved[key], "full-domain root " + key)
        _require(
            len(saved["refinement_fits"]) == len(curves),
            "all original call refinement fits required",
        )
        for curve, fit in zip(curves, saved["refinement_fits"], strict=True):
            computed = fit_independent_quote(
                nodes, curve, q, model=row["model"], spot=s, query_id=identifier
            )
            _same(computed, fit, "full-domain refinement roots/residual/brackets")
        _require(
            saved["residual_scope"] == "independent_full_domain_physical_state_cubic_interpolant",
            "interpolated root residual may not claim exact CF/PDE truth",
        )
        result.append(expected)
    return result


def _summary(raw, samples, *, exact=False):
    from reference_methods import _sample_summary

    expected = _sample_summary(samples, exact=exact)
    for key, value in expected.items():
        _same(value, raw[key], "original-N raw sample " + key)
    return expected


def _driver_and_expenses(raw, row):
    n = row["original_n"]
    fine_steps = round((1 - row["date"]) * row["steps_per_year"])
    end = 0
    drivers = {}
    for index, driver in enumerate(raw["driver_map"]):
        start, stop = driver["path_range"]
        _require(
            start == end and stop == min(start + row["chunk_paths"], n),
            "driver original path gap/reorder",
        )
        _require(
            driver["reserved_parent_seed"] == row["seed"] and driver["chunk_index"] == index,
            "driver reserved stream identity changed",
        )
        child = int(np.random.SeedSequence([row["seed"], 7426, index]).generate_state(1)[0])
        _require(driver["child_seed"] == child, "deterministic reserved child seed mapping changed")
        _same([stop - start, fine_steps, 2], driver["fine_shape"], "fine driver original shape")
        _same(
            [stop - start, fine_steps // 2, 2], driver["coarse_shape"], "paired coarse driver shape"
        )
        _require(
            driver["driver_source"] == "reserved_local_rng",
            "formal fresh may not substitute supplied drivers",
        )
        _require(
            driver["max_live_driver_bytes"] <= 256 * 1024**2 and (stop - start) * fine_steps <= 1e9,
            "driver original memory/path-step cap exceeded",
        )
        _clock(driver, "driver expense")
        drivers[start] = (start, stop)
        end = stop
    seen = set()
    query_jobs = {}
    driver_jobs = {}
    refinements = 0
    _codes, _legend, status = _statuses(raw["scheme_refinement"], (2, 13, n))
    for expense in raw["expenses"]:
        _clock(expense, "oracle expense")
        key = expense["job_id"]
        _require(key not in seen, "oracle expense job duplicated")
        seen.add(key)
        _require(expense["path_steps"] <= 1e9, "oracle job exceeds original path-step cap")
        _require(
            expense["scope"]
            in {
                "independent_asian_quote_oracle",
                "independent_oracle_driver",
                "independent_call_refinement",
            },
            "original oracle expense scope unknown",
        )
        if expense["scope"] == "independent_call_refinement":
            refinements += 1
        elif expense["scope"] == "independent_oracle_driver":
            start, stop = expense["path_range"]
            _require(
                start in drivers and start not in driver_jobs,
                "original driver expense missing/duplicated",
            )
            driver_jobs[start] = expense
            matching = next(d for d in raw["driver_map"] if d["path_range"][0] == start)
            for key, value in matching.items():
                _same(value, expense[key], "actual raw driver cost " + key)
            _same((stop - start) * fine_steps, expense["path_steps"], "driver actual path steps")
        if expense["scope"] == "independent_asian_quote_oracle":
            start, stop = expense["path_range"]
            _require(
                start in drivers
                and drivers[start] == (start, stop)
                and expense["original_path_count"] == n
                and expense["processed_path_count"] == stop - start,
                "oracle expense original driver/path scope changed",
            )
            index = raw["query_ids"].index(expense["query_id"])
            level_index = [row["steps_per_year"] // 2, row["steps_per_year"]].index(
                expense["level"]
            )
            identity = (start, expense["level"], index)
            _require(identity not in query_jobs, "original query job duplicated")
            query_jobs[identity] = expense
            executed = status[level_index, index, start:stop]
            _require(
                not np.isin(executed, ["unmeasured_cap", "unmeasured"]).any(),
                "executed query job lost original path evidence",
            )
            fit = raw["query_fits"][index]
            ran = fit["solver_status"] == "unique_root"
            _require(
                expense["attempt_status"] == ("measured" if ran else "rejected_quote_fit"),
                "solver status cannot substitute for a numerical measurement",
            )
            steps = round((1 - row["date"]) * expense["level"])
            _same(
                (stop - start) * steps if ran else 0,
                expense["path_steps"],
                "actual oracle path-step count",
            )
    _require(set(driver_jobs) == set(drivers), "all actual independent driver expenses required")
    _require(
        refinements == int(raw["call_refinements"] is not None),
        "actual call-refinement expense required",
    )
    for start, (first, last) in drivers.items():
        for k, level in enumerate([row["steps_per_year"] // 2, row["steps_per_year"]]):
            for j in range(13):
                used = ~np.isin(status[k, j, first:last], ["unmeasured_cap", "unmeasured"])
                _require(
                    not used.any() or used.all(), "query job may not silently filter original paths"
                )
                _require(
                    used.any() == ((start, level, j) in query_jobs),
                    "every measured/rejected query needs its actual expense",
                )
    return {"driver_prefix_count": end, "jobs": len(seen)}


def _oracle(raw, row, parameters, surface):
    from check_pilot import check_oracle_record
    from reference_methods import _blocks

    n = row["original_n"]
    expected_input = {k: row[k] for k in ("date", "spot", "quote", "memory_sum", "memory_count")}
    ids = ["base"] + [
        f"{a}{sign}.{w}" for a in ("S", "Q") for w in ("1", ".5", "2") for sign in ("+", "-")
    ]
    _require(
        raw["query_ids"] == ids and len(raw["query_fits"]) == 13,
        "all original query IDs must remain",
    )
    _same(expected_input, raw["input_state"], "fresh fixed restart input")
    _require(
        raw["model"] == row["model"] and raw["seed"] == row["seed"], "oracle original model/stream"
    )
    _same([1.0, 0.5, 2.0], raw["width_multipliers"], "original three widths")
    _require(raw["selected_width_index"] == 1, "pretest half-width derivative selection changed")
    _same(row["spot_bump"], raw["spot_bump"], "fixed S bump")
    _same(row["quote_bump"], raw["quote_bump"], "fixed Q bump")
    exact = row["memory_count"] == 12 or row["memory_sum"] >= 1200
    checked = check_oracle_record(raw, original_n=n)
    summary = _summary(raw, raw["samples"], exact=exact)
    _same(_blocks(raw["samples"]), raw["block_means"], "sixteen original oracle blocks")
    _same(
        _blocks(raw["payoff_samples"].T).T, raw["block_payoff_means"], "thirteen payoff block means"
    )
    widths = np.asarray(raw["width_position_samples"])
    _same(widths.mean(axis=1), raw["three_width_greek_means"], "three-width raw means")
    _same(
        np.cov(widths.transpose(1, 0, 2).reshape(n, 6), rowvar=False) / n,
        raw["width_covariance"],
        "three-width full paired covariance",
    )
    scheme = raw["scheme_refinement"]
    _same(raw["payoff_samples"], scheme["payoff_samples"][1], "original fine paired samples")
    _same(
        _blocks(scheme["paired_difference_samples"]),
        scheme["block_difference_means"],
        "sixteen paired SDE difference blocks",
    )
    codes, legend, status = _statuses(scheme, (2, 13, n))
    _same(codes[1], raw["path_status"], "fine raw path statuses")
    _same(scheme["first_failure_date"][1], raw["first_failure_date"], "fine original first failure")
    finite = np.isfinite(scheme["payoff_samples"])
    good = np.isin(status, ["supported", "exact_input_identity"])
    _require(
        np.array_equal(finite, good),
        "finite raw successes must retain exact support; bad paths may not be selected",
    )
    failure = np.asarray(scheme["first_failure_date"])
    _require(
        failure.shape == (2, 13, n)
        and np.isnan(failure[good]).all()
        and np.all((failure[~good] >= row["date"]) & (failure[~good] <= 1.0)),
        "first failure must preserve original path/calendar",
    )
    _cap(raw["cap_evidence"], statuses=codes, labels=legend)
    fits = refinement = None
    table_error = curve_cs = None
    if exact:
        p = parameters
        growth = sum(
            math.exp((p.rate - p.dividend_yield) * (d - row["date"]))
            for d in np.arange(row["memory_count"] + 1, 13) / 12
        )
        discount = math.exp(-p.rate * (1 - row["date"]))
        queries = (
            [row["spot"]]
            + [
                row["spot"] + sign * row["spot_bump"] * w
                for w in (1.0, 0.5, 2.0)
                for sign in (1, -1)
            ]
            + [row["spot"]] * 6
        )
        expected = np.array(
            [
                max(row["memory_sum"] / 12 - 100, 0.0)
                if row["memory_count"] == 12
                else discount * (row["memory_sum"] / 12 - 100 + s * growth / 12)
                for s in queries
            ]
        )
        _same(
            np.broadcast_to(expected[:, None], (13, n)),
            raw["payoff_samples"],
            "input analytic payoff proof",
        )
        _require(
            raw["call_table"] is None
            and raw["call_refinements"] is None
            and not raw["driver_map"]
            and not raw["expenses"],
            "exact branch may not fit or simulate",
        )
    else:
        prices = _table(raw["call_table"], row, parameters, surface)
        fits = _query_fits(raw, row, prices)
        refinement = _refinement(raw, row, fits[0], parameters)
        table_error = float(np.max(np.abs(prices - prices[-1])))
        if fits[0]["solver_status"] == "unique_root":
            from scipy.interpolate import CubicSpline

            spots = np.asarray(raw["call_table"]["query_spots"])
            ss = row["spot"]
            half = row["spot_bump"] * 0.5
            v = fits[0]["state"]
            ip = np.flatnonzero(np.isclose(spots, ss + half, rtol=0, atol=1e-12))[0]
            im = np.flatnonzero(np.isclose(spots, ss - half, rtol=0, atol=1e-12))[0]
            nodes = raw["call_table"]["state_nodes"]
            curve_cs = float(
                (
                    CubicSpline(nodes, prices[-1, 0, ip], extrapolate=False)(v)
                    - CubicSpline(nodes, prices[-1, 0, im], extrapolate=False)(v)
                )
                / (2 * half)
            )
        _driver_and_expenses(raw, row)
        for j, fit in enumerate(fits):
            if fit["solver_status"] != "unique_root":
                _require(
                    np.all(np.isin(status[:, j], ["unmeasured_cap", "unknown_quote_fit"])),
                    "nonunique/missing original roots may not simulate or qualify",
                )
    within = exact or all(f["operational_status"] == "within_envelope" for f in fits)
    _require(
        raw["operational_status"] == ("within_envelope" if within else "unknown")
        and raw["financial_qualification"] == "unknown",
        "root status may not become financial qualification",
    )
    checked.update(
        table_refinement_error=table_error,
        curve_spot_derivative=curve_cs,
        summary=summary,
        fits=fits,
        call_refinement=refinement,
        original_invalid_path_count=int((~np.all(good, axis=(0, 1))).sum()),
    )
    return checked


def _teacher_labels(record, parameters, surface):
    from deep_hedge_price import _dynamic_hedging_replay as replay

    p = record["primitives"]
    checked = replay.replay_teacher(p, record["thresholds"], parameters, surface)
    labels = checked["labels"]
    labels["shared_driver_id"] = record["global_driver_id"]
    labels["date_index"] = p["memory_count"]
    _same(labels, record["labels"], "production raw primitive-to-label values")
    _require(record["date_index"] == p["memory_count"], "original production fixing count")
    mapping = record["driver_mapping"]
    _require(
        mapping["original_n"] == p["original_path_count"]
        and mapping["global_steps"] == 768
        and mapping["start_step"] == round(p["calendar_times"][0] * 768)
        and mapping["stop_step"] == 768
        and mapping["aggregation_factor"] == 1
        and mapping["slice_sha256"] == p["shared_driver_id"],
        "original production full/slice driver mapping",
    )
    return checked


def _teacher(raw, row, parameters, surface):
    from reference_methods import _sample_summary
    from run_pilot import _merge_primitives
    from run_reference import payload_digest

    from deep_hedge_price import _dynamic_hedging_replay as replay

    n = row["original_n"]
    _require(
        raw["schema"] == "rb-f04-production-teacher-fresh-v1"
        and raw["original_path_count"] == n
        and raw["original_record_identity"] == row["original_record_identity"],
        "production teacher original record/N binding",
    )
    _same(row["original_teacher"], raw["original_teacher"], "locked original teacher raw anchor")
    _same(np.arange(n), raw["path_indices"], "teacher original absolute paths")
    old = row["original_teacher"]
    _teacher_labels(old, parameters, surface)
    keys = ["b", "c", "mu", "sigma", "aux_logG_prefix", "aux_last_loading"]
    _require(raw["primitive_keys"] == keys, "original primitive comparison coordinates")
    samples = np.full((n, 6), np.nan)
    statuses = np.full(n, "unmeasured_cap", dtype="U96")
    first = np.full(n, np.nan)
    parts = []
    stop = 0
    start_step = round(row["date"] * 768)
    times = np.arange(769) / 768
    expenses = raw["expenses"]
    _require(len(expenses) == len(raw["chunks"]), "teacher actual expenses per chunk missing")
    for index, (chunk, expense) in enumerate(zip(raw["chunks"], expenses, strict=True)):
        start, end = chunk["path_range"]
        _require(
            start == stop and end == min(start + row["chunk_paths"], n),
            "teacher original path gap/reorder",
        )
        driver = chunk["driver"]
        _same([start, end], driver["path_range"], "teacher original driver path range")
        child = int(np.random.SeedSequence([row["seed"], 7291, index]).generate_state(1)[0])
        _require(
            driver["reserved_parent_seed"] == row["seed"]
            and driver["child_seed"] == child
            and driver["global_steps"] == 768
            and driver["start_step"] == start_step,
            "teacher original reserved stream/global calendar mapping",
        )
        primitive = chunk["replay"]["primitives"]
        _require(
            primitive["original_path_count"] == end - start
            and primitive["model"] == row["model"]
            and primitive["spot"] == row["spot"]
            and primitive["state"] == old["primitives"]["state"],
            "production teacher restart state/N changed",
        )
        _same(
            times[start_step:], primitive["calendar_times"], "teacher original 768 restart calendar"
        )
        _same(
            old["thresholds"],
            chunk["replay"]["thresholds"],
            "production teacher original thresholds",
        )
        _teacher_labels(chunk["replay"], parameters, surface)
        _require(
            driver["fine_normal_sha256"] == chunk["replay"]["global_driver_id"],
            "production full driver fingerprint binding",
        )
        samples[start:end] = np.column_stack(
            [np.broadcast_to(primitive[k], (end - start,)) for k in keys]
        )
        mask = np.asarray(primitive["path_mask"])
        statuses[start:end] = np.where(mask, "supported", primitive["failure_reasons"])
        codes = np.asarray(primitive["local_step_status"])
        legend = np.asarray(primitive["local_step_status_labels"]).astype(str)
        for path in np.flatnonzero(~mask):
            used = np.flatnonzero(codes[path] != 0)
            if len(used):
                unsupported = np.flatnonzero(np.char.startswith(legend[codes[path]], "unsupported"))
                j = int(unsupported[0] if len(unsupported) else used[-1])
                at = start_step + j
                first[start + path] = (
                    (times[at] + times[at + 1]) / 2 if len(unsupported) else times[at + 1]
                )
        parts.append(primitive)
        _clock(expense, "teacher chunk actual cost")
        _require(
            expense["scope"] == "production_teacher_replay"
            and expense["original_path_count"] == n
            and expense["processed_path_count"] == end - start,
            "teacher expense original scope/count",
        )
        _same(
            (end - start) * (768 - start_step),
            expense["path_steps"],
            "teacher actual SDE path steps",
        )
        _same((end - start) * 768, expense["driver_path_steps"], "teacher full driver path steps")
        _require(
            expense["driver_path_steps"] <= 1e9
            and (end - start) * 768 * 16 * 3 + 16 * 1024**2 <= 256 * 1024**2,
            "teacher original path-step/memory cap",
        )
        stop = end
    _same(samples, raw["primitive_samples"], "teacher preserved individual primitives")
    _same(statuses, raw["path_status"], "teacher original support/failure/cap states")
    _same(first, raw["first_failure_date"], "teacher actual first failure date")
    _require(
        raw["executed_path_count"] == stop and raw["unexecuted_path_count"] == n - stop,
        "teacher original attempted/unexecuted path count",
    )
    expected = np.column_stack([np.broadcast_to(old["primitives"][k], (n,)) for k in keys])
    a, b = _sample_summary(samples), _sample_summary(expected)
    computed = dict(
        method="independent_reserved_stream_all_original_paths",
        fresh_mean=a["mean"],
        original_mean=b["mean"],
        difference=a["mean"] - b["mean"],
        combined_standard_errors=np.sqrt(a["standard_errors"] ** 2 + b["standard_errors"] ** 2),
        fresh_statistical_status=a["statistical_status"],
        original_statistical_status=b["statistical_status"],
        financial_qualification="unknown",
    )
    _same(computed, raw["comparison"], "fresh versus original teacher full-N statistics")
    _cap(
        raw["cap_evidence"],
        statuses=np.where(statuses == "unmeasured_cap", 0, 1),
        labels=["unmeasured_cap", "executed"],
    )
    _clock(raw["cost"], "teacher total actual cost")
    labels = None
    if stop == n:
        merged = _merge_primitives(parts, n, payload_digest([p["shared_driver_id"] for p in parts]))
        _same(merged, raw["global_primitives"], "teacher original global primitive merge")
        checked = replay.replay_teacher(
            merged, old["thresholds"], parameters, surface, saved_labels=raw["global_labels"]
        )
        labels = checked["labels"]
    else:
        _require(
            raw["global_primitives"] is None
            and raw["global_labels"] is None
            and raw["cap_evidence"] is not None,
            "partial teacher may not fabricate global labels",
        )
    return dict(
        original_n=n,
        executed_paths=stop,
        invalid_paths=int(np.count_nonzero(statuses != "supported")),
        comparison=computed,
        labels=labels,
        financial_qualification="unknown",
        unverified=["earlier_sde_generation", "original_artifact_byte_authentication"],
    )


def _premium(raw, candidate):
    from check_pilot import _moments, check_premium_record
    from reference_methods import _blocks

    expected = candidate["original_candidate"]["premium"]
    _require(
        raw["financial_qualification"] == "unknown", "premium cannot prequalify financial accuracy"
    )
    n = expected["original_n"]
    _require(
        raw["schema"] == "rb-f04-independent-premium-v1"
        and raw["model"] == "heston"
        and raw["N"] == n
        and raw["original_path_count"] == n
        and raw["price_only"] is True
        and raw["steps_per_year"] == 1536,
        "original price-only premium scope/N/grid",
    )
    _require(
        raw["parameters"]
        == dict(
            spot=100.0,
            rate=0.03,
            dividend_yield=0.0,
            v0=0.04,
            kappa=2.0,
            theta=0.04,
            xi=0.3,
            rho=-0.7,
        ),
        "premium original Heston market",
    )
    _same(np.arange(n), raw["path_indices"], "premium original path indices")
    samples = np.asarray(raw["samples"])
    checked = check_premium_record(raw, candidate=candidate)
    _summary(raw, samples[1])
    _same(raw["mean"], raw["value"], "premium original mean price")
    _same(raw["standard_errors"], raw["standard_error"], "premium original raw SE")
    diff = samples[1] - samples[0]
    pair = _moments(diff[:, None], n)
    _same(diff, raw["paired_difference_samples"], "premium paired SDE individual differences")
    _same(pair["mean"][0], raw["paired_difference_mean"], "premium paired mean")
    _same(pair["standard_errors"][0], raw["paired_difference_standard_error"], "premium paired SE")
    _same(abs(pair["mean"][0]), raw["scheme_error"], "premium raw scheme change")
    _same(_blocks(samples.T).T, raw["block_means"], "premium original sixteen paired blocks")
    codes, legend, status = _statuses(raw, (2, n))
    _require(
        np.array_equal(np.isfinite(samples), status == "supported"),
        "premium failed original paths cannot become finite",
    )
    _cap(raw["cap_evidence"], statuses=codes, labels=legend)
    premium_cap = raw["cap_evidence"]
    if premium_cap is not None:
        for expense in raw["expenses"] + raw["driver_map"]:
            _interval(expense, premium_cap, "premium actual cost", require_cpu=False)
    drivers = {}
    stop = 0
    for i, driver in enumerate(raw["driver_map"]):
        first, last = driver["path_range"]
        _require(
            first == stop
            and first < last <= n
            and driver["chunk_index"] == i
            and driver["original_path_count"] == n
            and driver["reserved_parent_seed"] == expected["seed"],
            "premium original reserved driver/path roster",
        )
        child = int(np.random.SeedSequence([expected["seed"], 7426, i]).generate_state(1)[0])
        _require(
            driver["child_seed"] == child and driver["driver_source"] == "reserved_local_rng",
            "premium reserved deterministic stream mapping",
        )
        _same([last - first, 1536, 2], driver["fine_shape"], "premium original fine driver")
        _same([last - first, 768, 2], driver["coarse_shape"], "premium paired coarse driver")
        _require(
            driver["max_live_driver_bytes"] <= 256 * 1024**2, "premium original driver memory cap"
        )
        _clock(driver, "premium actual driver cost")
        drivers[first] = (first, last, driver)
        stop = last
    driver_jobs = set()
    query_jobs = set()
    seen = set()
    for expense in raw["expenses"]:
        _clock(expense, "premium actual expense")
        _require(
            expense["job_id"] not in seen and expense["path_steps"] <= 1e9,
            "premium original job ID/path-step cap",
        )
        seen.add(expense["job_id"])
        first, last = expense["path_range"]
        _require(
            first in drivers and drivers[first][:2] == (first, last),
            "premium expense must bind actual original driver paths",
        )
        if expense["scope"] == "independent_premium_driver":
            _require(first not in driver_jobs, "premium driver expense duplicate")
            driver_jobs.add(first)
            for key, value in drivers[first][2].items():
                _same(value, expense[key], "premium driver expense " + key)
            _same((last - first) * 1536, expense["path_steps"], "premium actual driver steps")
        else:
            _require(
                expense["scope"] == "independent_premium_price_only"
                and expense["level"] in (768, 1536)
                and expense["original_path_count"] == n
                and expense["processed_path_count"] == last - first,
                "premium original price-only expense scope",
            )
            key = (first, expense["level"])
            _require(key not in query_jobs, "premium actual price job duplicated")
            query_jobs.add(key)
            _same(
                (last - first) * expense["level"], expense["path_steps"], "premium actual SDE steps"
            )
    _require(driver_jobs == set(drivers), "all original premium driver expenses required")
    for first, (start, last, _) in drivers.items():
        for k, level in enumerate((768, 1536)):
            used = ~np.isin(status[k, start:last], ["unmeasured", "unmeasured_cap"])
            _require(
                not used.any() or used.all(), "premium original paths may not be silently filtered"
            )
            _require(
                used.any() == ((first, level) in query_jobs),
                "all original premium executed jobs need costs",
            )
    checked["financial_qualification"] = "unknown"
    checked["unverified"] = ["independent_path_generation", "original_artifact_byte_authentication"]
    return checked


def _gate(value, threshold, reason=None):
    available = value is not None and np.isfinite(value) and value >= 0
    return dict(
        value=float(value) if available else None,
        threshold=threshold,
        outcome=("pass" if value <= threshold else "failed") if available else "unknown",
        reason=reason if not available else "saved numerical measurement only",
    )


def _case_gates(oracle, teacher, row, candidate):
    original = candidate["original_candidate"]["gates"]
    refin = oracle["call_refinement"]
    scheme = oracle["scheme_difference_statistics"]
    exact = row["memory_count"] == 12 or row["memory_sum"] >= 1200
    se = oracle["gate_standard_errors"]
    fits = oracle["fits"]
    condition = None
    if exact:
        condition = 0.0
    elif refin is not None and fits and all(np.isfinite(f["condition_number"]) for f in fits):
        cv = refin["state_derivative"]
        direct = 0.01 / ((0.04 if row["model"] == "heston" else 1.0) * abs(cv)) if cv else np.inf
        condition = max([f["condition_number"] for f in fits] + [direct])
    width = oracle["width_difference_statistics"]
    width_errors = [
        max(abs(d["mean"][i]) + 6 * d["standard_errors"][i] for d in width) for i in (0, 1)
    ]
    scheme_errors = (
        [abs(scheme["mean"][i]) + 6 * scheme["standard_errors"][i] for i in range(3)]
        if scheme
        else [None] * 3
    )
    missing = "unavailable/failed original precision reference; no financial promotion"
    values = {
        "call_price_error": 0.0
        if exact
        else None
        if refin is None
        else max(
            refin["price_error"],
            refin["price_unit_error"],
            oracle["table_refinement_error"],
            abs(refin["price"] - row["quote"]),
        ),
        "call_stock_derivative_error": 0.0
        if exact
        else None
        if refin is None
        else refin["spot_derivative_error"]
        + refin["finite_width_errors"][0]
        + refin["integration_derivative_error"][0]
        + abs(oracle["curve_spot_derivative"] - refin["spot_derivative"]),
        "call_scaled_state_derivative_error": 0.0
        if exact
        else None
        if refin is None
        else (0.04 if row["model"] == "heston" else 1.0)
        * (
            refin["state_derivative_error"]
            + refin["finite_width_errors"][1]
            + refin["integration_derivative_error"][1]
            + abs(fits[0]["Ctheta"] - refin["state_derivative"])
        ),
        "teacher_price_se": 0.0 if exact else None,
        "stock_position_se": se[1],
        "call_position_se": se[2],
        "quote_condition_number": condition,
        # Reference self-refinement cannot certify missing production comparisons.
        "asian_price_error": 0.0 if exact else None,
        "stock_position_error": 0.0 if exact else None,
        "call_position_error": 0.0 if exact else None,
    }
    # Production price can be compared only if the original threshold was saved.
    labels = teacher["labels"]
    target = (1200 - row["memory_sum"]) / row["spot"]
    at = np.flatnonzero(
        np.isclose(row["original_teacher"]["thresholds"], target, rtol=0, atol=1e-12)
    )
    production = None
    target_status = "unavailable_original_threshold"
    if labels is not None and len(at) == 1:
        j = at[0]
        target_status = str(np.asarray(labels["status"])[j])
        scale = math.exp(-0.03 * (1 - row["date"])) * row["spot"] / 12
        production = scale * labels["f"][j]
        if target_status in {"ready", "not_required_linear_claim", "not_required_settled_claim"}:
            values["teacher_price_se"] = scale * labels["f_se"][j]
            if scheme_errors[0] is not None:
                combined = math.sqrt(
                    (scale * labels["f_se"][j]) ** 2 + oracle["raw_standard_errors"][0] ** 2
                )
                values["asian_price_error"] = (
                    abs(production - oracle["mean"][0]) + 6 * combined + scheme_errors[0]
                )

    return dict(
        gates={key: _gate(value, original[key], missing) for key, value in values.items()},
        teacher_price=production,
        independent_price_raw_standard_error=oracle["raw_standard_errors"][0],
        teacher_threshold_status=target_status,
        production_position_comparison="not_saved; original stock/call position error gates remain unknown"
        if not exact
        else "exact input identity",
        independent_scheme_error_envelope=scheme_errors,
        independent_three_width_error_envelope=width_errors,
        financial_qualification="unknown",
        precision_scope="individual_saved_comparison_not_source_or_main_qualification",
    )


def check_fresh(
    payload,
    *,
    expected_plan,
    frozen,
    candidate,
    source,
    original_artifact_identity,
    parameters,
    surface,
    main_parent_receipt=None,
):
    """Recompute every locked fresh record, preserving all failures and expense scopes."""
    from run_fresh import _canonical_digest, _validate_inputs
    from run_reference import payload_digest

    _validate_inputs(
        plan=expected_plan,
        frozen=frozen,
        candidate=candidate,
        source=source,
        original_artifact_identity=original_artifact_identity,
        parameters=parameters,
        surface=surface,
    )
    _require(payload["schema"] == "rb-f04-fresh-evidence-v1", "fresh evidence schema required")
    _require(
        payload["raw_sha256"]
        == payload_digest({k: v for k, v in payload.items() if k != "raw_sha256"}),
        "fresh evidence provenance digest stale",
    )
    _same(expected_plan, payload["plan"], "unchanged pretest fresh plan")
    _require(
        payload["plan_sha256"]
        == payload_digest(expected_plan)
        == frozen["selection"]["fresh_plan_sha256"]
        and payload["frozen_sha256"] == frozen["frozen_sha256"]
        and payload["candidate_sha256"] == _canonical_digest(candidate)
        and payload["source_sha256"] == _canonical_digest(source)
        and payload["source"] == source
        and payload["original_artifact_identity"] == original_artifact_identity,
        "fresh immutable selection/source/original artifact binding",
    )
    _require(
        payload["surface_sha256"] == expected_plan["surface_sha256"]
        and payload["scope"] == "all_locked_selected_restarts"
        and payload["financial_qualification"] == "unknown",
        "fresh raw cannot certify financial qualification",
    )
    _same(
        expected_plan["wall_cap_seconds"],
        payload["phase_wall_cap_seconds"],
        "pretest phase wall cap",
    )
    _clock(payload["cost"], "fresh whole phase cost")
    phase_start = payload["cost"]["clock"]["wall_start"]
    phase_deadline = phase_start + expected_plan["wall_cap_seconds"]
    _same(phase_deadline, payload["cost"]["deadline_wall"], "original fresh phase deadline")
    records = payload["records"]
    _require(
        [r["id"] for r in records] == expected_plan["required_case_ids"],
        "all locked selected restart IDs/order required",
    )
    cases = []
    for row, record in zip(expected_plan["cases"], records, strict=True):
        _same(
            row["original_record_identity"],
            record["original_record_identity"],
            "original restart record anchor",
        )
        _require(row["stream_slot"] == record["stream_slot"], "original reserved fresh slot")
        _require(
            [job["id"] for job in record["jobs"]] == ["call_table", "oracle", "teacher_replay"],
            "all original fresh phase job attempts required",
        )
        previous = phase_start
        for job in record["jobs"]:
            start = job["clock"]["wall_start"]
            _require(start >= previous, "fresh phase jobs reordered/overlapping")
            planned = row["wall_caps"][job["id"]]
            expected_not_required = job["id"] == "call_table" and (
                row["memory_count"] == 12 or row["memory_sum"] >= 1200
            )
            _require(
                job["not_required"] == expected_not_required,
                "job exemption requires an exact input identity",
            )
            effective = min(planned, max(0.0, phase_deadline - start))
            _same(planned, job["planned_wall_cap_seconds"], "pretest job wall cap")
            _same(effective, job["effective_wall_cap_seconds"], "remaining phase job cap")
            _same(start + effective, job["deadline_wall"], "actual effective job deadline")
            _same(phase_deadline, job["phase_deadline_wall"], "immutable phase deadline")
            _clock(job, "fresh actual job cost")
            for kind in ("wall", "cpu"):
                _require(
                    payload["cost"]["clock"][kind + "_start"]
                    <= job["clock"][kind + "_start"]
                    <= job["clock"][kind + "_stop"]
                    <= payload["cost"]["clock"][kind + "_stop"],
                    "fresh actual job interval outside phase",
                )
            previous = job["clock"]["wall_stop"]
        table_job, oracle_job, teacher_job = record["jobs"]
        table = record["raw"]["call_table"]
        if table_job["not_required"]:
            _require(table is None, "exact-input table exemption may not hide measured evidence")
        else:
            _require(table is not None, "required call table measurement missing")
            _bind_job_cap(table, table_job, "call table")
        _bind_job_cap(record["raw"], oracle_job, "oracle")
        _bind_job_cap(record["teacher_replay"], teacher_job, "teacher replay")
        oracle = _oracle(record["raw"], row, parameters, surface)
        teacher = _teacher(record["teacher_replay"], row, parameters, surface)
        cases.append(
            dict(
                id=row["id"],
                original_n=row["original_n"],
                oracle=oracle,
                teacher=teacher,
                **_case_gates(oracle, teacher, row, candidate),
            )
        )
    premium = payload.get("premium_record")
    _same(expected_plan.get("premium_record"), premium, "unchanged pretest premium record")
    premium_checked = None if premium is None else _premium(premium, candidate)
    if main_parent_receipt is not None:
        _require(
            main_parent_receipt["fresh_plan_sha256"] == payload["plan_sha256"]
            and main_parent_receipt["fresh_raw_sha256"] == payload["raw_sha256"]
            and main_parent_receipt.get("main_artifact_identity"),
            "posttest main parent receipt must bind independently without modifying the pretest plan",
        )
    unresolved = ["earlier_sde_generation_unverified", "original_artifact_byte_authentication"]
    if premium is None:
        unresolved.append("premium_missing")
    for case in cases:
        if any(g["outcome"] != "pass" for g in case["gates"].values()):
            unresolved.append(case["id"] + ":failed_or_unknown_original_precision_gate")
    return dict(
        schema="rb-f04-saved-fresh-check-v1",
        original_case_count=len(cases),
        fresh_plan_sha256=payload["plan_sha256"],
        fresh_raw_sha256=payload["raw_sha256"],
        cases=cases,
        premium=premium_checked,
        main_parent_receipt=main_parent_receipt,
        financial_qualification="unknown",
        unresolved=unresolved,
        scope="saved_full_original_N_boundary",
        hard_cancel_limit="single CF/PDE/teacher query is not forcibly interrupted; measured overruns remain",
        counts=dict(full_main_evaluations=396, full_training_fits=12),
        counts_scope="required_original_obligations_not_a_claim_of_execution",
    )


def main():
    from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid
    from run_reference import load_bundle, save_bundle

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle, _inputs_receipt = load_bundle(args.inputs)
    params = HestonParameters(**bundle["parameters"])
    field = bundle.get("surface")
    surface = (
        None
        if field is None
        else LocalVarianceGrid(
            times=field["times"],
            z_nodes=field["z_nodes"],
            values=field["values"],
            parameters=HestonParameters(**field["parameters"]) if "parameters" in field else params,
            wing_boundaries=field.get("wing_boundaries"),
        )
    )
    result = check_fresh(
        bundle["payload"],
        expected_plan=bundle["plan"],
        frozen=bundle["frozen"],
        candidate=bundle["candidate"],
        source=bundle["source"],
        original_artifact_identity=bundle["original_artifact_identity"],
        parameters=params,
        surface=surface,
        main_parent_receipt=bundle.get("main_parent_receipt"),
    )
    save_bundle(args.output, result)


if __name__ == "__main__":
    main()
