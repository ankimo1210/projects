"""Saved-only arithmetic boundary of initial37 synthetic quote evidence.

Recalculate the two CF probability-integral prices, saved PDE-grid query
prices, all original quote errors and measured refinements. This does not
rerun earlier Fourier/PDE solves or qualify dynamic calls, Greeks, teachers,
Q drift, policy training or the formal pilot. Digests are provenance only.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def _same(actual, expected, label, *, atol=1e-9):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape or not np.allclose(a, b, rtol=1e-12, atol=atol, equal_nan=True):
        raise ValueError("inconsistent saved " + label)


def _roster():
    groups = [
        ("fit", t, np.array([80.0, 90.0, 100.0, 110.0, 120.0]))
        for t in [0.25, 0.5, 0.75, 1.0, 1.25]
    ]
    groups += [("holdout", t, np.array([85.0, 95.0, 105.0, 115.0])) for t in [1 / 3, 2 / 3, 1.125]]
    return groups


def _cf_prices(receipt, strikes, t, parameters):
    rows = receipt["integration_receipts"]
    if len(rows) != len(strikes):
        raise ValueError("CF original quote count")
    prices, errors = [], []
    for strike, pair in zip(strikes, rows, strict=True):
        if len(pair) != 2:
            raise ValueError("two CF probability integrals required")
        values, absolute_errors = [], []
        for row in pair:
            value, error = float(row["value"]), float(row["absolute_error"])
            if (
                row["status"] != "converged"
                or not math.isfinite(value)
                or not math.isfinite(error)
                or error < 0
            ):
                raise ValueError("unresolved CF integral")
            parts = np.asarray(row["subintervals"], float)
            if parts.ndim != 2 or parts.shape[1] != 4 or len(parts) != row["subinterval_count"]:
                raise ValueError("CF original subinterval count")
            _same(parts[:, 2].sum(), value, "CF integral sum")
            if np.any(~np.isfinite(parts)) or np.any(parts[:, 3] < 0):
                raise ValueError("CF invalid raw quadrature evidence")
            values.append(0.5 + value / math.pi)
            absolute_errors.append(error / math.pi)
        prepaid = parameters["spot"] * math.exp(-parameters["dividend_yield"] * t)
        strike_pv = float(strike) * math.exp(-parameters["rate"] * t)
        prices.append(prepaid * values[0] - strike_pv * values[1])
        errors.append(prepaid * absolute_errors[0] + strike_pv * absolute_errors[1])
    _same(receipt["price"], prices, "CF receipt prices")
    _same(receipt["price_unit_error"], errors, "CF receipt error")
    return np.asarray(prices), np.asarray(errors)


def check_initial_quotes(metadata: dict, arrays: dict) -> dict:
    """Check all original37 IDs and derive initial gates from raw price arrays."""
    groups = _roster()
    quotes = metadata["quotes"]
    expected = [(kind, t, k) for kind, t, ks in groups for k in ks]
    if len(quotes) != 37 or len(metadata["cf_receipts"]) != 8:
        raise ValueError("original37 quotes / eight maturity groups required")
    for actual, (kind, t, k) in zip(quotes, expected, strict=True):
        if actual["kind"] != kind:
            raise ValueError("quote kind/order")
        _same([actual["time"], actual["strike"]], [t, k], "quote time/strike")
    derived, error_values = {"truth250": [], "truth500": []}, []
    for receipt, (_, t, strikes) in zip(metadata["cf_receipts"], groups, strict=True):
        _same(receipt["time"], t, "CF maturity")
        _same(receipt["strikes"], strikes, "CF strike roster")
        for suffix in [250, 500]:
            values, errors = _cf_prices(
                receipt["upper" + str(suffix)], strikes, t, metadata["parameters"]
            )
            derived["truth" + str(suffix)].extend(values)
            if suffix == 500:
                error_values.extend(errors)
    for name, values in derived.items():
        _same(arrays[name], values, name)
    _same(arrays["truth500_error"], error_values, "CF error array")
    truth = np.asarray(arrays["truth500"], float)
    cf_names = ["truth250", "truth500", "cf1024_cutoff512", "cf2048_cutoff512", "cf2048_cutoff1024"]
    for name in cf_names:
        if np.asarray(arrays[name]).shape != (37,) or not np.isfinite(arrays[name]).all():
            raise ValueError("CF complete finite original37 required")
    cf_error = max(float(np.max(np.abs(np.asarray(arrays[name]) - truth))) for name in cf_names)
    cf_error = max(cf_error, float(np.max(error_values)))
    stages, fields = {}, {}
    for stage in metadata["stages"]:
        label = stage["id"]
        if "pde_receipts" not in stage and label + ".prices" not in arrays:
            continue
        if label in stages:
            raise ValueError("duplicate original PDE attempt ID")
        if any(label + suffix not in arrays for suffix in [".prices", ".quote_ids", ".errors"]):
            raise ValueError("missing original PDE attempt arrays")
        ids = np.asarray(arrays[label + ".quote_ids"])
        if stage["original_quote_count"] != 37 or not np.array_equal(ids, np.arange(37)):
            raise ValueError("PDE original37 roster cannot be filtered")
        receipts = stage["pde_receipts"]
        if len(receipts) != 8:
            raise ValueError("PDE eight original groups")
        reconstructed = np.full(37, np.nan)
        seen = set()
        for i, receipt in enumerate(receipts):
            if not receipt["supported"] or receipt["failure"] is not None:
                raise ValueError("PDE unsupported original group")
            maturity = float(receipt["time"])
            strike_roster = np.asarray(receipt["strikes"], float)
            matches = [j for j, (_, t, _) in enumerate(groups) if abs(t - maturity) <= 1e-12]
            if len(matches) != 1 or matches[0] in seen:
                raise ValueError("PDE duplicate / missing original maturity roster")
            group_index = matches[0]
            seen.add(group_index)
            _same(strike_roster, groups[group_index][2], "PDE original strike roster")
            prefix = f"{label}.group{i}"
            if prefix + ".log_spots" not in arrays:
                prefix = f"{label}.t{maturity:.17g}"
            if prefix + ".log_spots" not in arrays or prefix + ".values" not in arrays:
                raise ValueError("PDE original raw grid missing")
            nodes = np.asarray(arrays[prefix + ".log_spots"], float)
            values = np.asarray(arrays[prefix + ".values"], float)
            if (
                nodes.ndim != 1
                or len(nodes) < 2
                or not np.isfinite(nodes).all()
                or values.shape != (len(strike_roster), len(nodes))
                or not np.isfinite(values).all()
            ):
                raise ValueError("PDE grid query shape/nonfinite")
            if (
                np.any(np.diff(nodes) <= 0)
                or not nodes[0] <= math.log(metadata["parameters"]["spot"]) <= nodes[-1]
            ):
                raise ValueError("PDE ordered query support")
            offset = sum(len(group[2]) for group in groups[:group_index])
            reconstructed[offset : offset + len(strike_roster)] = [
                np.interp(math.log(metadata["parameters"]["spot"]), nodes, row) for row in values
            ]
        if len(seen) != 8 or not np.isfinite(reconstructed).all():
            raise ValueError("PDE original37 incomplete roster")
        _same(arrays[label + ".prices"], reconstructed, "PDE grid query " + label)
        price = np.asarray(reconstructed)
        delta = price - truth
        _same(arrays[label + ".errors"], delta, "PDE errors " + label, atol=1e-11)
        field = stage["field"]
        if field not in fields:
            times = np.asarray(arrays[field + ".surface.times"], float)
            raw = np.asarray(arrays[field + ".surface.local_variance"], float)
            supported = np.asarray(arrays[field + ".surface.supported"], bool)
            bounds = np.asarray(arrays[field + ".surface.wing_boundaries"])
            if times.ndim != 1 or len(times) != len(raw) or times[0] <= 0 or times[-1] < 1.25:
                raise ValueError("actual field must cover traded-call1.25 expiry")
            if (
                np.any(np.diff(times) <= 0)
                or raw.shape != supported.shape
                or bounds.shape != (len(times), 2)
            ):
                raise ValueError("field raw support shapes")
            interior = []
            for row, mask, (lo, hi) in zip(raw, supported, bounds, strict=True):
                if lo < 0 or hi >= len(row) or lo > hi or not mask[lo : hi + 1].all():
                    raise ValueError("field contiguous interior support")
                values = row[lo : hi + 1]
                if not np.isfinite(values).all() or np.any(values <= 0):
                    raise ValueError("field finite positive supported variance")
                interior.extend(values)
            fields[field] = dict(
                min_variance=float(np.min(interior)),
                max_variance=float(np.max(interior)),
                original_cells=int(raw.size),
                original_supported_cells=int(supported.sum()),
            )
        stages[label] = dict(
            original_quote_count=37,
            max_error=float(np.max(np.abs(delta))),
            gate="pass" if np.max(np.abs(delta)) <= 0.001 else "fail",
        )
    if not stages:
        raise ValueError("no original37 PDE result")
    refinement_sources = {
        "pde2401x1920": "pde1201x960",
        "pde_domain2p4": "pde2401x1920",
        "pde_field_refined": "pde2401x1920",
        "pde_space4801": "pde_field_refined",
        "pde_time3840": "pde_space4801",
        "pde_early_extended": "pde_field_refined",
        "pde_wing6": "pde_field_refined",
    }
    refinements = {}
    stage_by_id = {stage["id"]: stage for stage in metadata["stages"]}
    for label in stages:
        stage = stage_by_id[label]
        if stage.get("max_refinement") is None and label + ".refinement" not in arrays:
            continue
        if label not in refinement_sources:
            raise ValueError("unmapped original refinement reference")
        source = refinement_sources[label]
        if source not in stages or label + ".refinement" not in arrays:
            raise ValueError("missing original refinement arrays/reference")
        delta = np.asarray(arrays[label + ".prices"]) - np.asarray(arrays[source + ".prices"])
        _same(arrays[label + ".refinement"], delta, "refinement " + label, atol=1e-11)
        maximum = float(np.max(np.abs(delta)))
        if stage.get("max_refinement") is not None:
            _same(stage["max_refinement"], maximum, "reported refinement " + label, atol=1e-11)
        refinements[label] = {
            "reference": source,
            "original_quote_count": 37,
            "max_difference": maximum,
        }
    candidate = min(stages, key=lambda name: stages[name]["max_error"])
    return dict(
        integrity="pass",
        original_quote_count=37,
        cf_gate="pass" if cf_error <= 1e-8 else "fail",
        cf_max_difference_or_quad_error=cf_error,
        pde_stages=stages,
        fields=fields,
        refinements=refinements,
        initial_quote_gate="pass"
        if cf_error <= 1e-8 and any(s["gate"] == "pass" for s in stages.values())
        else "fail",
        best_measured_stage=candidate,
        formal_pilot_qualification="unknown",
        boundary="saved CF integrals / PDE nodes -> all37 query prices and errors; earlier solver work not replayed",
    )


def main(argv=None):
    """Read original receipts/arrays without RNG or solver execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    metadata = json.loads((args.directory / "initial-quotes.json").read_text())
    with np.load(args.directory / "reference.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    print(json.dumps(check_initial_quotes(metadata, arrays), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
