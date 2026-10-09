"""Saved-only 18-state call-cache/fit boundary, without CF/PDE/SDE execution.

The observed Q and saved independent-PDE grid are inputs. Cache splines and
quote fits use the reviewed finance helpers; this is their saved arithmetic
replay, not a second independent interpolation/root algorithm. Earlier solver
accuracy, Asian/position/P&L/Q drift and formal pilot remain unqualified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from hullkit._dynamic_hedging_surfaces import evaluate_call, fit_quote_state
from scipy.interpolate import CubicSpline


def _same(actual, expected, name):
    if isinstance(expected, str):
        valid = str(np.asarray(actual)) == expected
    else:
        left = np.asarray(actual, float)
        right = np.asarray(np.nan if expected is None else expected, float)
        valid = left.shape == right.shape and np.allclose(
            left, right, rtol=2e-10, atol=2e-9, equal_nan=True
        )
    if not valid:
        raise ValueError("inconsistent saved " + name)


def check_selected_calls(metadata: dict, arrays: dict) -> dict:
    """Recalculate all18 state outcomes and absolute price comparisons."""
    dates = np.array([0.0, 1 / 12, 0.25, 0.5, 0.75, 11 / 12])
    rows = metadata["rows"]
    if metadata["original_states"] != 18 or len(rows) != 18:
        raise ValueError("original18 states required")
    caches = {}
    for model in ["heston", "local"]:
        cache = {
            key: np.asarray(arrays[model + "." + key])
            for key in ["dates", "spot_nodes", "state_nodes", "values", "support_mask"]
        }
        _same(cache["dates"], dates, model + " original dates")
        if cache["values"].shape != (6, len(cache["spot_nodes"]), len(cache["state_nodes"])):
            raise ValueError("original call cache shape")
        if cache["support_mask"].shape != cache["values"].shape:
            raise ValueError("original call support shape")
        cache.update(
            model=model,
            rate=metadata["parameters"]["rate"],
            dividend_yield=metadata["parameters"]["dividend_yield"],
            strike=100.0,
            maturity=1.25,
        )
        caches[model] = cache
    nodes = np.asarray(arrays["independent_local_base.log_spots"], float)
    values = np.asarray(arrays["independent_local_base.values"], float)
    if (
        nodes.ndim != 1
        or len(nodes) < 4
        or np.any(~np.isfinite(nodes))
        or np.any(np.diff(nodes) <= 0)
        or values.shape != (6, len(nodes))
        or not np.isfinite(values).all()
    ):
        raise ValueError("original independent local query grid")
    herrors, lerrors, unknowns = [], [], dict(heston=0, local=0)
    for i, row in enumerate(rows):
        j, scenario = divmod(i, 3)
        s = ([99.95, 100.0, 100.05] if j == 0 else [80.0, 100.0, 120.0])[scenario]
        v = [0.02, 0.04, 0.08][scenario]
        _same(
            [row["date"], row["scenario"], row["spot"], row["heston_state"]],
            [dates[j], scenario, s, v],
            "original state roster",
        )
        if set(row["models"]) != {"heston", "local"} or not np.isfinite(row["quote"]):
            raise ValueError("original model / observed quote roster")
        for model in ["heston", "local"]:
            saved = row["models"][model]
            fit = fit_quote_state(
                caches[model], j, s, row["quote"], state_scale=0.04 if model == "heston" else 1.0
            )
            for key in ["status", "reason", "state", "condition", "residual"]:
                _same(fit[key], saved[key], "fit " + model + " " + key)
            traded = evaluate_call(caches[model], j, s, fit["state"])
            for suffix, key in [
                ("price", "value"),
                ("spot_derivative", "spot_derivative"),
                ("state_derivative", "state_derivative"),
            ]:
                _same(traded[key], saved["call_" + suffix], "call " + model + " " + suffix)
            unknowns[model] += int(str(np.asarray(fit["status"])) != "ok")
        error = float(evaluate_call(caches["heston"], j, s, v)["value"]) - row["quote"]
        _same(error, row["models"]["heston"]["price_error_at_true_v"], "Heston true-state error")
        herrors.append(error)
        if not nodes[0] <= np.log(s) <= nodes[-1]:
            raise ValueError("independent local original query support")
        independent = float(CubicSpline(nodes, values[j])(np.log(s)))
        error = float(evaluate_call(caches["local"], j, s, 1.0)["value"]) - independent
        _same(
            independent,
            row["models"]["local"]["base_independent_price"],
            "independent saved grid query",
        )
        _same(error, row["models"]["local"]["base_price_error"], "local base price error")
        lerrors.append(error)
    return dict(
        integrity="pass",
        original_states=18,
        heston_true_state_max_price_error=float(np.max(np.abs(herrors))),
        local_base_max_price_error=float(np.max(np.abs(lerrors))),
        local_base_price_gate="pass" if np.max(np.abs(lerrors)) <= 0.001 else "fail",
        fit_unknown_counts=unknowns,
        formal_pilot_qualification="unknown",
        boundary="input Q / saved PDE nodes / saved cache nodes -> spline price, fits, derivatives and comparisons; earlier solvers not replayed",
    )


def main(argv=None):
    """Replay one original selected-state directory without RNG or training."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    metadata = json.loads((args.directory / "selected-calls.json").read_text())
    with np.load(args.directory / "reference.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    print(json.dumps(check_selected_calls(metadata, arrays), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
