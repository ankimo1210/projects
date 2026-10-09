"""Numerical-pilot wiring for RB-F04, using fixed monthly contracts and paired drivers."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from itertools import pairwise
from pathlib import Path
from time import perf_counter

import numpy as np

HERE = Path(__file__).resolve().parent
_MODULES = {}


def module(name):
    """Load this study or an explicitly private financial module from this checkout."""
    if name not in _MODULES:
        if name in ("surface", "paths"):
            filename = {"surface": "_heston_local_surface", "paths": "_model_dynamics"}[name]
            path = HERE.parents[1] / "hullkit/src/hullkit" / (filename + ".py")
        else:
            path = HERE / (name + ".py")
        spec = importlib.util.spec_from_file_location("rbf04_" + name, path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = loaded
        spec.loader.exec_module(loaded)
        _MODULES[name] = loaded
    return _MODULES[name]


def simulate(parameters, surface, *, paths, seed, steps, block_size, expiry=1.0):
    """Stream shared fine normals and retain each model/level's monthly path and failures.

    A coarser normal is the standardized sum of the fine normals, and both stock
    processes consume the same first factor. Random generation occurs only here.
    No path is dropped. Wall time covers driver generation plus both simulations,
    and is descriptive pilot cost rather than an isolated engine benchmark.
    """
    levels = sorted(set(steps))
    if (
        not levels
        or min(levels) <= 0
        or any(int(s) != s or s % 12 for s in levels)
        or any(max(levels) % s for s in levels)
        or paths < 2
        or block_size < 1
    ):
        raise ValueError("positive nested monthly levels, paths >=2 and block size >=1 required")
    levels = [int(s) for s in levels]
    engine = module("paths")
    rng = np.random.default_rng(seed)
    blocks = []
    start = perf_counter()
    for first in range(0, paths, block_size):
        count = min(block_size, paths - first)
        normals = rng.standard_normal((count, max(levels), 2))
        block = {}
        for level in levels:
            driver = engine.aggregate_normals(normals, max(levels) // level)
            results = {
                "heston": engine.heston_monthly(parameters, driver, expiry),
                "local": engine.local_monthly(parameters, surface, driver, expiry),
            }
            for model, values in results.items():
                prefix = f"{level}.{model}."
                for key in (
                    "observations",
                    "failures",
                    "failure_reasons",
                    "variance_observations",
                    "negative_variance_counts",
                ):
                    if key in values:
                        block[prefix + key] = values[key]
                for label, counts in values.get("status_counts", {}).items():
                    block[prefix + "status." + label] = counts
        blocks.append((count, block))
    elapsed = perf_counter() - start
    keys = set().union(*(set(block) for _, block in blocks))
    arrays = {}
    for key in sorted(keys):
        arrays[key] = np.concatenate(
            [block.get(key, np.zeros(count, dtype=int)) for count, block in blocks]
        )
    return {
        "arrays": arrays,
        "levels": levels,
        "paths": paths,
        "seed": seed,
        "block_size": block_size,
        "wall_s": elapsed,
        "cost_scope": "normal generation plus both models at all retained levels",
    }


def path_metrics(arrays, protocol, *, steps):
    """Separate paired model sampling uncertainty from each model's step changes."""
    analytics = module("analytics")
    rate = protocol["parameters"]["rate"]
    contract = protocol["contract"]
    expiry, strike = contract["expiry"], contract["asian_strike"]
    quotes, two = protocol["quotes"], protocol["two_date"]
    months = np.rint(np.array([two["first"], two["second"]]) / expiry * 12).astype(int)
    if not np.allclose(months * expiry / 12, [two["first"], two["second"]]):
        raise ValueError("two-date contract must use exact monthly dates")
    asian, vanilla, rows = {}, {}, []
    for level in sorted(steps):
        observations = {m: arrays[f"{level}.{m}.observations"] for m in ("heston", "local")}
        asian[level] = {
            m: analytics.asian_payoffs(x, strike, rate, expiry) for m, x in observations.items()
        }
        vanilla[level] = {
            m: analytics.vanilla_payoffs(x, quotes["times"], quotes["strikes"], rate, expiry)
            for m, x in observations.items()
        }
        diagnostics = {}
        for model in ("heston", "local"):
            prefix = f"{level}.{model}."
            diagnostics[model] = {
                "failed_paths": int(arrays[prefix + "failures"].sum()),
                "negative_variance_states": int(
                    arrays.get(prefix + "negative_variance_counts", np.array([0])).sum()
                ),
                "surface_visits": {
                    key.removeprefix(prefix + "status."): int(value.sum())
                    for key, value in arrays.items()
                    if key.startswith(prefix + "status.")
                },
                "surface_visited_paths": {
                    key.removeprefix(prefix + "status."): int(np.count_nonzero(value))
                    for key, value in arrays.items()
                    if key.startswith(prefix + "status.")
                },
            }
        rows.append(
            {
                "steps": level,
                "asian": analytics.paired_summary(asian[level]["heston"], asian[level]["local"]),
                "vanilla": analytics.paired_summary(
                    vanilla[level]["heston"], vanilla[level]["local"]
                ),
                "two_date": analytics.two_date_summary(
                    observations["heston"][:, months],
                    observations["local"][:, months],
                    two["bins"],
                    two["conditional_threshold"],
                    two.get("minimum_count", 32),
                ),
                "diagnostics": diagnostics,
            }
        )
    changes = []
    levels = sorted(steps)
    for coarse, fine in pairwise(levels):
        row = {"coarse": coarse, "fine": fine}
        for model in ("heston", "local"):
            row[model + "_asian"] = analytics.sample_summary(
                asian[fine][model] - asian[coarse][model]
            )
            row[model + "_vanilla"] = analytics.sample_summary(
                vanilla[fine][model] - vanilla[coarse][model]
            )
            row[model + "_two_date"] = _two_date_comparison(
                arrays[f"{coarse}.{model}.observations"][:, months],
                arrays[f"{fine}.{model}.observations"][:, months],
                protocol,
                first_label="coarse",
                second_label="fine",
            )
        row["difference_asian"] = analytics.sample_summary(
            (asian[fine]["local"] - asian[fine]["heston"])
            - (asian[coarse]["local"] - asian[coarse]["heston"])
        )
        changes.append(row)
    return {"levels": rows, "step_changes": changes}


def build_surface(
    parameters,
    *,
    times,
    z_nodes,
    order=1024,
    frequency_scale=512,
    density_floor=1e-10,
    allow_row_wings=False,
):
    """Construct a diagnosed variance grid, retaining every unsupported source cell.

    Explicit row wings require a contiguous supported interval with at least two
    nodes per row. Values outside it remain NaN in the saved arrays and the grid;
    evaluation extends the supported edge value and labels that use.
    """
    financial = module("surface")
    times = np.asarray(times, dtype=float)
    z_nodes = np.asarray(z_nodes, dtype=float)
    if (
        times.ndim != 1
        or len(times) == 0
        or np.any(times <= 0)
        or not np.all(np.isfinite(times))
        or np.any(np.diff(times) <= 0)
        or z_nodes.ndim != 1
        or len(z_nodes) < 2
        or not np.all(np.isfinite(z_nodes))
        or np.any(np.diff(z_nodes) <= 0)
    ):
        raise ValueError("positive increasing times and finite increasing z nodes required")
    arrays = {"surface.times": times, "surface.z_nodes": z_nodes}
    rows, strikes, half_rows, cutoff_cf, cutoff_weighted = [], [], [], [], []
    start = perf_counter()
    for t in times:
        k = parameters.spot * np.exp(
            (parameters.rate - parameters.dividend_yield) * t
            + z_nodes * np.sqrt(parameters.integrated_variance(float(t)))
        )
        rows.append(
            financial.fourier_surface(
                k,
                float(t),
                parameters,
                order=order,
                max_frequency=frequency_scale / np.sqrt(t),
                density_floor=density_floor,
            )
        )
        half_rows.append(
            financial.fourier_surface(
                k,
                float(t),
                parameters,
                order=max(2, order // 2) if order > 2 else 4,
                max_frequency=frequency_scale / np.sqrt(t),
                density_floor=density_floor,
            )
        )
        phi, _, weighted = financial._characteristic_terms(
            np.array([frequency_scale / np.sqrt(t)]), float(t), parameters
        )
        cutoff_cf.append(abs(phi[0]))
        cutoff_weighted.append(abs(weighted[0]))
        strikes.append(k)
    arrays["surface.half_density"] = np.array([row["density"] for row in half_rows])
    arrays["surface.half_weighted_density"] = np.array(
        [row["weighted_density"] for row in half_rows]
    )
    arrays["surface.cutoff_cf_abs"] = np.array(cutoff_cf)
    arrays["surface.cutoff_weighted_cf_abs"] = np.array(cutoff_weighted)
    arrays["surface.strikes"] = np.array(strikes)
    for key in rows[0]:
        arrays["surface." + key] = np.stack([row[key] for row in rows])
    supported = arrays["surface.supported"]
    bounds = np.full((len(times), 2), -1, dtype=int)
    contiguous = True
    for i, mask in enumerate(supported):
        indices = np.flatnonzero(mask)
        if len(indices) < 2 or np.any(np.diff(indices) != 1):
            contiguous = False
        elif len(indices):
            bounds[i] = [indices[0], indices[-1]]
    arrays["surface.wing_boundaries"] = bounds
    missing = int((~supported).sum())
    failure = None
    grid = None
    if not contiguous:
        failure = "noncontiguous or too short supported interval"
    elif missing and not allow_row_wings:
        failure = "unsupported source cells; explicit row wings were not enabled"
    else:
        options = {"wing_boundaries": bounds} if missing else {}
        grid = financial.LocalVarianceGrid(
            times, z_nodes, arrays["surface.local_variance"], parameters, **options
        )
    return {
        "grid": grid,
        "arrays": arrays,
        "unsupported_cells": missing,
        "failure": failure,
        "wall_s": perf_counter() - start,
        "settings": {
            "order": order,
            "frequency_scale": frequency_scale,
            "density_floor": density_floor,
            "allow_row_wings": allow_row_wings,
        },
    }


def _two_date_comparison(first, second, protocol, *, first_label, second_label):
    two = protocol["two_date"]
    result = module("analytics").two_date_summary(
        first, second, two["bins"], two["conditional_threshold"], two.get("minimum_count", 32)
    )
    result = {
        key.replace("_heston", "_" + first_label).replace("_local", "_" + second_label): value
        for key, value in result.items()
    }
    result["direction"] = second_label + "-minus-" + first_label
    result["uncertainty_scope"] = (
        "paired sampling only; joint low-count SE is descriptive, zero is not proof of zero probability"
    )
    return result


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _json(value):
    return json.dumps(_plain(value), sort_keys=True, indent=2, allow_nan=False) + "\n"


def _protocol(source=None):
    if source is None:
        source = HERE / "protocol.json"
    if isinstance(source, (str, Path)):
        source = json.loads(Path(source).read_text())
    protocol = json.loads(_json(source))
    contract = protocol["contract"]
    expiry = contract["expiry"]
    observations = np.asarray(contract["observations"], dtype=float)
    if (
        expiry <= 0
        or not np.isfinite(expiry)
        or observations.shape != (12,)
        or not np.allclose(observations, np.arange(1, 13) * expiry / 12, rtol=0, atol=1e-12)
        or contract["include_initial"] is not False
        or contract["payment"] != "expiry"
        or contract["asian_strike"] <= 0
    ):
        raise ValueError(
            "contract requires twelve monthly observations, excludes initial, expiry payment"
        )
    module("surface").HestonParameters(**protocol["parameters"])
    for t in [
        *protocol["quotes"]["times"],
        *protocol["quotes"]["holdout_times"],
        protocol["two_date"]["first"],
        protocol["two_date"]["second"],
    ]:
        if (
            t <= 0
            or t > expiry
            or not np.isclose(t * 12 / expiry, round(t * 12 / expiry), rtol=0, atol=1e-12)
        ):
            raise ValueError("contract quotes and two-date events require monthly dates")
    return protocol


def _settings(protocol, smoke):
    candidate = protocol["pilot"]
    expiry = protocol["contract"]["expiry"]
    minimum = candidate.get("times_min", 1 / 4096)
    time_count, z_count = (9, 41) if smoke else (65, 81)
    order, scale = (512, 256) if smoke else (1024, 512)
    times = np.geomspace(minimum, expiry, time_count)
    z = np.linspace(-5, 5, z_count)

    def spec(t, nodes):
        return {
            "time_nodes": len(t),
            "z_count": len(nodes),
            "z_width": float(max(abs(nodes))),
            "times_min": float(t[0]),
            "times": t.tolist(),
            "z_nodes": nodes.tolist(),
            "order": order,
            "frequency_scale": scale,
            "density_floor": 1e-10,
            "allow_row_wings": True,
        }

    spacing = float(z[1] - z[0])
    surfaces = {
        "baseline": spec(times, z),
        "time_refined": spec(np.geomspace(minimum, expiry, 2 * time_count - 1), z),
        "z_refined": spec(times, np.linspace(-5, 5, 2 * z_count - 1)),
        "joint_refined": spec(
            np.geomspace(minimum, expiry, 2 * time_count - 1), np.linspace(-5, 5, 2 * z_count - 1)
        ),
        "wing4": spec(times, np.linspace(-4, 4, round(8 / spacing) + 1)),
        "wing6": spec(times, np.linspace(-6, 6, round(12 / spacing) + 1)),
        "early_min": spec(np.concatenate(([minimum / 4], times)), z),
    }
    space_nodes, time_steps = (61, 24) if smoke else (601, 384)
    pde = {
        "baseline": {"space_nodes": space_nodes, "time_steps": time_steps, "log_half_width": 1.5},
        "space_refined": {
            "space_nodes": 2 * space_nodes - 1,
            "time_steps": time_steps,
            "log_half_width": 1.5,
        },
        "time_refined": {
            "space_nodes": space_nodes,
            "time_steps": 2 * time_steps,
            "log_half_width": 1.5,
        },
        "domain_refined": {
            "space_nodes": 2 * space_nodes - 1,
            "time_steps": time_steps,
            "log_half_width": 3.0,
        },
        "joint_fine": {
            "space_nodes": 2 * space_nodes - 1,
            "time_steps": 2 * time_steps,
            "log_half_width": 1.5,
        },
    }
    return {
        "paths": 128 if smoke else int(candidate.get("paths", 8192)),
        "seed": int(candidate.get("seed", 8117)),
        "block_size": 64 if smoke else 2048,
        "steps": [24, 48, 96] if smoke else list(candidate.get("steps", [192, 384, 768])),
        "surface_specs": surfaces,
        "pde_specs": pde,
        "fourier": {
            "times": [minimum, 0.001, 0.01, 0.1, 0.25, 0.5, 1.0],
            "z_nodes": [-6, -5, -4, -2, 0, 2, 4, 5, 6],
            "specs": {
                "baseline": {"order": order, "frequency_scale": scale},
                "order_refined": {"order": 2 * order, "frequency_scale": scale},
                "cutoff_refined": {"order": 2 * order, "frequency_scale": 2 * scale},
            },
        },
        "fresh_tolerance": {"rtol": 1e-8, "atol": 1e-10},
        "wing_policy": "constant extension from each contiguous supported row edge; NaNs retained",
        "early_time_policy": "minimum-positive-time proxy; t=0 only S0 has variance v0",
    }


def _unavailable_surface():
    class Unavailable:
        def evaluate(self, t, spots):
            return {
                "variance": np.full_like(spots, np.nan),
                "status": np.full(spots.shape, "unsupported_surface", dtype="<U32"),
            }

    return Unavailable()


def _surface_kwargs(spec):
    return {
        key: spec[key]
        for key in (
            "times",
            "z_nodes",
            "order",
            "frequency_scale",
            "density_floor",
            "allow_row_wings",
        )
    }


def _quote_groups(protocol):
    quotes = protocol["quotes"]
    return [
        (float(t), np.array(quotes[k], dtype=float))
        for dates, k in (("times", "strikes"), ("holdout_times", "holdout_strikes"))
        for t in quotes[dates]
    ]


def _pde_arrays(parameters, grid, groups, spec):
    reference = module("reference_methods")
    results = [
        reference.pde_call(
            parameters.spot,
            strikes,
            t,
            grid.evaluate,
            parameters.rate,
            parameters.dividend_yield,
            **spec,
        )
        for t, strikes in groups
    ]
    arrays = {
        "quote_times": np.concatenate([np.full(len(k), t) for t, k in groups]),
        "quote_strikes": np.concatenate([k for _, k in groups]),
        "price": np.concatenate([result["price"] for result in results]),
        "supported": np.concatenate(
            [
                np.full(len(k), result["supported"], dtype=bool)
                for (_, k), result in zip(groups, results, strict=True)
            ]
        ),
        "failure": np.concatenate(
            [
                np.full(len(k), result["failure"] or "", dtype="<U64")
                for (_, k), result in zip(groups, results, strict=True)
            ]
        ),
        "group_times": np.array([t for t, _ in groups]),
    }
    labels = sorted(set().union(*(result["status_counts"] for result in results)))
    for label in labels:
        arrays["status." + label] = np.array(
            [result["status_counts"].get(label, 0) for result in results], dtype=np.int64
        )
    for index, result in enumerate(results):
        for key, value in result["grid"].items():
            arrays[f"grid.{index}.{key}"] = np.asarray(value)
    return arrays


def _audit(array):
    value = np.asarray(array)
    result = {"shape": list(value.shape), "dtype": value.dtype.str}
    if value.dtype.kind in "biufc":
        flat = value.reshape(-1)
        finite = np.isfinite(flat)
        real = flat[finite].astype(float)
        result.update(
            finite=int(finite.sum()),
            missing=int(np.isnan(flat).sum()),
            positive_infinity=int(np.isposinf(flat).sum()),
            negative_infinity=int(np.isneginf(flat).sum()),
            sum=float(real.sum()),
            squared_sum=float(np.dot(real, real)),
            minimum=float(real.min()) if len(real) else None,
            maximum=float(real.max()) if len(real) else None,
        )
    else:
        values, counts = np.unique(value.astype(str), return_counts=True)
        result["counts"] = dict(zip(values.tolist(), counts.tolist(), strict=True))
    return result


def _surface_summary(arrays, prefix, parameters):
    supported = arrays[prefix + "supported"]
    k = arrays[prefix + "strikes"]
    lv = arrays[prefix + "local_variance"]
    price, ck, ckk, ct = [arrays[prefix + key] for key in ("price", "ck", "ckk", "ct")]
    with np.errstate(invalid="ignore", divide="ignore"):
        dupire = (
            2
            * (
                ct
                + parameters.dividend_yield * price
                + (parameters.rate - parameters.dividend_yield) * k * ck
            )
            / (k * k * ckk)
        )
    residual = dupire - lv
    finite = supported & np.isfinite(residual)
    return {
        "cells": int(supported.size),
        "supported_cells": int(supported.sum()),
        "unsupported_cells": int((~supported).sum()),
        "supported_per_time": supported.sum(axis=1),
        "wing_boundaries": arrays[prefix + "wing_boundaries"],
        "dupire_conditional_max_abs": float(np.max(np.abs(residual[finite])))
        if finite.any()
        else None,
        "local_variance_min": float(lv[supported].min()) if supported.any() else None,
        "local_variance_max": float(lv[supported].max()) if supported.any() else None,
    }


def summarize(record, arrays):
    """Recompute every pilot metric and array audit from retained raw evidence."""
    protocol, settings = record["protocol"], record["settings"]
    parameters = module("surface").HestonParameters(**protocol["parameters"])
    levels = settings["steps"]
    fine = max(levels)
    analytics = module("analytics")
    path_summaries, surface_summaries, changes = {}, {}, {}
    expiry, strike = [protocol["contract"][key] for key in ("expiry", "asian_strike")]
    rate = parameters.rate
    quotes, two = protocol["quotes"], protocol["two_date"]
    months = np.rint(np.array([two["first"], two["second"]]) * 12 / expiry).astype(int)
    baseline = arrays[f"paths.baseline.{fine}.local.observations"]
    for variant in settings["surface_specs"]:
        prefix = "paths." + variant + "."
        subset = {
            key.removeprefix(prefix): value
            for key, value in arrays.items()
            if key.startswith(prefix)
        }
        path_summaries[variant] = path_metrics(
            subset, protocol, steps=levels if variant == "baseline" else [fine]
        )
        surface_summaries[variant] = _surface_summary(
            arrays, "surface." + variant + ".", parameters
        )
        if variant != "baseline":
            observations = subset[f"{fine}.local.observations"]
            changes[variant] = {
                "direction": "variant-minus-baseline",
                "asian": analytics.sample_summary(
                    analytics.asian_payoffs(observations, strike, rate, expiry)
                    - analytics.asian_payoffs(baseline, strike, rate, expiry)
                ),
                "vanilla": analytics.sample_summary(
                    analytics.vanilla_payoffs(
                        observations, quotes["times"], quotes["strikes"], rate, expiry
                    )
                    - analytics.vanilla_payoffs(
                        baseline, quotes["times"], quotes["strikes"], rate, expiry
                    )
                ),
                "two_date": _two_date_comparison(
                    baseline[:, months],
                    observations[:, months],
                    protocol,
                    first_label="baseline",
                    second_label="variant",
                ),
            }
    fourier = {}
    for name, first, second in (
        ("order_change", "baseline", "order_refined"),
        ("cutoff_change", "order_refined", "cutoff_refined"),
    ):
        a, b = "fourier." + first + ".", "fourier." + second + "."
        fourier[name] = {
            "first": first,
            "second": second,
            "common_support": arrays[a + "supported"] & arrays[b + "supported"],
            "support_changes": int(
                np.count_nonzero(arrays[a + "supported"] != arrays[b + "supported"])
            ),
            "difference": {
                key: arrays[b + key] - arrays[a + key]
                for key in (
                    "price",
                    "ck",
                    "ckk",
                    "ct",
                    "density",
                    "weighted_density",
                    "local_variance",
                )
            },
        }
    base_prices = arrays["pde.baseline.price"]
    pde, surface_pde = {}, {}
    for variant in settings["pde_specs"]:
        prefix = "pde." + variant + "."
        pde[variant] = {
            "price": arrays[prefix + "price"],
            "supported": arrays[prefix + "supported"],
            "failure": arrays[prefix + "failure"],
            "status_counts": {
                key.removeprefix(prefix + "status."): int(value.sum())
                for key, value in arrays.items()
                if key.startswith(prefix + "status.")
            },
            "residual_fourier": arrays[prefix + "price"] - arrays["reference.fourier_price"],
            "residual_independent_cf": arrays[prefix + "price"] - arrays["cf.upper500"],
            "change_from_baseline": arrays[prefix + "price"] - base_prices,
        }
    for variant in settings["surface_specs"]:
        prefix = "surface_pde." + variant + "."
        surface_pde[variant] = {
            "direction": "variant-minus-baseline",
            "price": arrays[prefix + "price"],
            "supported": arrays[prefix + "supported"],
            "failure": arrays[prefix + "failure"],
            "status_counts": {
                key.removeprefix(prefix + "status."): int(value.sum())
                for key, value in arrays.items()
                if key.startswith(prefix + "status.")
            },
            "residual_fourier": arrays[prefix + "price"] - arrays["reference.fourier_price"],
            "residual_independent_cf": arrays[prefix + "price"] - arrays["cf.upper500"],
            "change_from_baseline": arrays[prefix + "price"] - arrays["pde.joint_fine.price"],
            "pde_settings": settings["pde_specs"]["joint_fine"],
        }
    return _plain(
        {
            "surface_pde": surface_pde,
            "paths": path_summaries,
            "surfaces": surface_summaries,
            "surface_changes": changes,
            "fourier": fourier,
            "pde": pde,
            "cf": {
                "upper_change": arrays["cf.upper500"] - arrays["cf.upper250"],
                "fourier_residual": arrays["reference.fourier_price"] - arrays["cf.upper500"],
            },
            "array_audits": {key: _audit(value) for key, value in sorted(arrays.items())},
            "uncertainty_scope": (
                "paired sampling standard errors exclude surface, PDE and path discretization bias"
            ),
        }
    )


def _compute(protocol, smoke):
    start = perf_counter()
    settings = _settings(protocol, smoke)
    parameters = module("surface").HestonParameters(**protocol["parameters"])
    arrays = {
        "metadata.protocol": np.array(_json(protocol)),
        "metadata.settings": np.array(_json(settings)),
        "metadata.mode": np.array("smoke" if smoke else "full"),
    }
    timing, surface_failures = {"surfaces": {}, "paths": {}, "pde": {}, "surface_pde": {}}, {}
    grids = {}
    for variant, spec in settings["surface_specs"].items():
        result = build_surface(parameters, **_surface_kwargs(spec))
        grids[variant] = result["grid"]
        surface_failures[variant] = result["failure"]
        timing["surfaces"][variant] = result["wall_s"]
        arrays.update(
            {
                key.replace("surface.", "surface." + variant + ".", 1): value
                for key, value in result["arrays"].items()
            }
        )
        paths = simulate(
            parameters,
            result["grid"] or _unavailable_surface(),
            paths=settings["paths"],
            seed=settings["seed"],
            steps=settings["steps"] if variant == "baseline" else [max(settings["steps"])],
            block_size=settings["block_size"],
            expiry=protocol["contract"]["expiry"],
        )
        arrays.update(
            {"paths." + variant + "." + key: value for key, value in paths["arrays"].items()}
        )
        timing["paths"][variant] = paths["wall_s"]
    diagnostic = settings["fourier"]
    for variant, spec in diagnostic["specs"].items():
        result = build_surface(
            parameters,
            times=diagnostic["times"],
            z_nodes=diagnostic["z_nodes"],
            **spec,
            density_floor=1e-10,
            allow_row_wings=True,
        )
        arrays.update(
            {
                key.replace("surface.", "fourier." + variant + ".", 1): value
                for key, value in result["arrays"].items()
            }
        )
    groups = _quote_groups(protocol)
    arrays["reference.quote_times"] = np.concatenate([np.full(len(k), t) for t, k in groups])
    arrays["reference.quote_strikes"] = np.concatenate([k for _, k in groups])
    baseline_spec = settings["surface_specs"]["baseline"]
    arrays["reference.fourier_price"] = np.concatenate(
        [
            module("surface").fourier_surface(
                k,
                t,
                parameters,
                order=baseline_spec["order"],
                max_frequency=baseline_spec["frequency_scale"] / np.sqrt(t),
                density_floor=baseline_spec["density_floor"],
            )["price"]
            for t, k in groups
        ]
    )
    for upper in (250, 500):
        arrays[f"cf.upper{upper}"] = np.concatenate(
            [
                module("reference_methods").independent_heston_call(k, t, parameters, upper=upper)
                for t, k in groups
            ]
        )
    baseline_grid = grids["baseline"] or _unavailable_surface()
    for variant, spec in settings["pde_specs"].items():
        pde_start = perf_counter()
        results = _pde_arrays(parameters, baseline_grid, groups, spec)
        arrays.update({"pde." + variant + "." + key: value for key, value in results.items()})
        timing["pde"][variant] = perf_counter() - pde_start
    for variant, grid in grids.items():
        if variant == "baseline":
            prefix = "pde.joint_fine."
            values = {
                key.removeprefix(prefix): value
                for key, value in arrays.items()
                if key.startswith(prefix)
            }
            timing["surface_pde"][variant] = 0.0
        else:
            pde_start = perf_counter()
            values = _pde_arrays(
                parameters,
                grid or _unavailable_surface(),
                groups,
                settings["pde_specs"]["joint_fine"],
            )
            timing["surface_pde"][variant] = perf_counter() - pde_start
        arrays.update(
            {"surface_pde." + variant + "." + key: value for key, value in values.items()}
        )
    record = {
        "schema": 1,
        "study": "RB-F04-numerical-pilot-v1",
        "state": "smoke" if smoke else "candidate_pilot",
        "mode": "smoke" if smoke else "full",
        "research_acceptance": False,
        "freeze_eligible": False,
        "review_required": "independent review and explicit protocol freeze before main comparison",
        "protocol": protocol,
        "settings": settings,
        "surface_failures": surface_failures,
        "timing": timing,
    }
    record["summary"] = summarize(record, arrays)
    record["timing"]["total_wall_s"] = perf_counter() - start
    return record, arrays


def _artifacts():
    name = "rbf04_shared_artifacts"
    if name not in _MODULES:
        path = HERE.parent / "RB-F05/discrete/artifacts.py"
        spec = importlib.util.spec_from_file_location(name, path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        _MODULES[name] = loaded
    return _MODULES[name]


def run_pilot(output, smoke=False, protocol=None):
    """Save a candidate numerical pilot; smoke output never authorizes research acceptance.

    All raw paths, source surface cells, support flags and PDE solutions are
    retained. The candidate protocol is loaded by default; this routine does
    not freeze it or decide whether a model difference was identified.
    Archives over 20 MB use the existing research evidence store.
    """
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    record, arrays = _compute(_protocol(protocol), bool(smoke))
    np.savez_compressed(directory / "pilot.npz", **arrays)
    record["artifact"] = _artifacts().store_large(directory, stem="pilot")
    (directory / "pilot.json").write_text(_json(record))
    return record


def _mismatches(expected, actual, prefix="", *, rtol=1e-8, atol=1e-10):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            return [prefix + " keys"]
        return [
            failure
            for key in expected
            for failure in _mismatches(
                expected[key], actual[key], prefix + "." + key, rtol=rtol, atol=atol
            )
        ]
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            return [prefix + " length"]
        return [
            failure
            for index, (first, second) in enumerate(zip(expected, actual, strict=True))
            for failure in _mismatches(first, second, prefix + f"[{index}]", rtol=rtol, atol=atol)
        ]
    if isinstance(expected, int) and not isinstance(expected, bool):
        return [] if type(actual) is int and expected == actual else [prefix + " count/value"]
    if isinstance(expected, float):
        if not isinstance(actual, (float, int)) or isinstance(actual, bool):
            return [prefix + " type"]
        return [] if np.isclose(expected, actual, rtol=rtol, atol=atol) else [prefix + " value"]
    return [] if expected == actual else [prefix + " value"]


def _raw_surface_support(arrays, prefix, floor, parameters):
    density, weighted = arrays[prefix + "density"], arrays[prefix + "weighted_density"]
    supported = (density > floor) & (weighted > 0)
    if parameters["xi"] != 0:
        supported &= np.abs(density - arrays[prefix + "half_density"]) <= 1e-3 * abs(density)
        supported &= np.abs(weighted - arrays[prefix + "half_weighted_density"]) <= (
            1e-3 * abs(weighted)
        )
        supported &= arrays[prefix + "cutoff_cf_abs"][:, None] <= 1e-10
        supported &= arrays[prefix + "cutoff_weighted_cf_abs"][:, None] <= (
            1e-10 * max(parameters["v0"], parameters["theta"])
        )
    for key in ("price", "ck", "ckk", "ct", "density", "weighted_density"):
        supported &= np.isfinite(arrays[prefix + key])
    with np.errstate(invalid="ignore", divide="ignore"):
        variance = weighted / density
    return supported & np.isfinite(variance) & (variance > 0)


def _invariants(record, arrays):
    failures = []
    parameters, settings = record["protocol"]["parameters"], record["settings"]
    paths = settings["paths"]
    fine = max(settings["steps"])
    for variant, spec in settings["surface_specs"].items():
        prefix = "surface." + variant + "."
        supported = arrays[prefix + "supported"]
        local = arrays[prefix + "local_variance"]
        expected_support = _raw_surface_support(arrays, prefix, spec["density_floor"], parameters)
        if not np.array_equal(supported, expected_support):
            failures.append(prefix + "raw support resolution mismatch")
        expected_bounds = np.full((supported.shape[0], 2), -1, dtype=int)
        contiguous = True
        for index, row in enumerate(supported):
            indices = np.flatnonzero(row)
            if len(indices) < 2 or np.any(np.diff(indices) != 1):
                contiguous = False
            else:
                expected_bounds[index] = [indices[0], indices[-1]]
        if not np.array_equal(expected_bounds, arrays[prefix + "wing_boundaries"]):
            failures.append(prefix + "supported wing boundaries mismatch")
        expected_failure = (
            "noncontiguous or too short supported interval"
            if not contiguous
            else "unsupported source cells; explicit row wings were not enabled"
            if (~supported).any() and not spec["allow_row_wings"]
            else None
        )
        if record["surface_failures"][variant] != expected_failure:
            failures.append(prefix + "surface failure mismatch")
        if not np.array_equal(supported, np.isfinite(local) & (local > 0)):
            failures.append(prefix + "support/NaN mismatch")
        if not np.isnan(local[~supported]).all():
            failures.append(prefix + "unsupported values were filled")
        if not np.allclose(arrays[prefix + "times"], spec["times"], rtol=0, atol=1e-15):
            failures.append(prefix + "time axis mismatch")
        if not np.allclose(arrays[prefix + "z_nodes"], spec["z_nodes"], rtol=0, atol=1e-15):
            failures.append(prefix + "z axis mismatch")
        for level in settings["steps"] if variant == "baseline" else [fine]:
            for model in ("heston", "local"):
                p = f"paths.{variant}.{level}.{model}."
                observed, failed = arrays[p + "observations"], arrays[p + "failures"]
                reasons = arrays[p + "failure_reasons"]
                if observed.shape != (paths, 13) or failed.shape != (paths,):
                    failures.append(p + "path shape mismatch")
                    continue
                if not np.allclose(observed[:, 0], parameters["spot"], rtol=0, atol=1e-12):
                    failures.append(p + "initial spot mismatch")
                if not np.array_equal(
                    failed, (~np.isfinite(observed) | (observed <= 0)).any(axis=1)
                ):
                    failures.append(p + "failure mask mismatch")
                if not np.array_equal(failed, reasons != ""):
                    failures.append(p + "failure reason mismatch")
                if model == "local":
                    counts = [
                        value for key, value in arrays.items() if key.startswith(p + "status.")
                    ]
                    total = np.sum(counts, axis=0)
                    if (
                        np.any(total < 1)
                        or np.any(total > level)
                        or np.any(total[~failed] != level)
                    ):
                        failures.append(p + "surface visit count mismatch")
                elif variant != "baseline":
                    reference = arrays[f"paths.baseline.{fine}.heston.observations"]
                    if not np.allclose(observed, reference, rtol=1e-12, atol=1e-12, equal_nan=True):
                        failures.append(p + "shared driver mismatch")
    for variant in settings["fourier"]["specs"]:
        prefix = "fourier." + variant + "."
        support = _raw_surface_support(arrays, prefix, 1e-10, parameters)
        if not np.array_equal(support, arrays[prefix + "supported"]):
            failures.append(prefix + "raw support resolution mismatch")
        local = arrays[prefix + "local_variance"]
        if not np.array_equal(support, np.isfinite(local) & (local > 0)):
            failures.append(prefix + "support/NaN mismatch")
    pde_prefixes = ["pde." + variant + "." for variant in settings["pde_specs"]] + [
        "surface_pde." + variant + "." for variant in settings["surface_specs"]
    ]
    for prefix in pde_prefixes:
        price, supported = arrays[prefix + "price"], arrays[prefix + "supported"]
        if not np.array_equal(np.isfinite(price), supported):
            failures.append(prefix + "support/price mismatch")
        if not np.array_equal(supported, arrays[prefix + "failure"] == ""):
            failures.append(prefix + "support/failure mismatch")
        for index, (t, strikes) in enumerate(_quote_groups(record["protocol"])):
            mask = arrays[prefix + "quote_times"] == t
            grid = prefix + f"grid.{index}."
            if supported[mask].all():
                expected = np.array(
                    [
                        np.interp(np.log(parameters["spot"]), arrays[grid + "log_spots"], row)
                        for row in arrays[grid + "values"]
                    ]
                )
                if len(expected) != len(strikes) or not np.allclose(
                    price[mask], expected, rtol=1e-10, atol=1e-10
                ):
                    failures.append(grid + "price/interpolation mismatch")
    return failures


def check_record(record, arrays):
    """Verify an in-memory pilot bundle by rebuilding summaries and contract invariants.

    Blob hashes only establish provenance; raw numerical evidence determines
    consistency. This entry point also verifies a pilot embedded in main
    comparison evidence without requiring another artifact on disk.
    """
    failures, recomputed = [], None
    try:
        if record["schema"] != 1 or record["study"] != "RB-F04-numerical-pilot-v1":
            failures.append("pilot schema/study mismatch")
        protocol = _protocol(record["protocol"])
        settings = _settings(protocol, record["mode"] == "smoke")
        for label, expected in (
            ("protocol", _json(protocol)),
            ("settings", _json(settings)),
            ("mode", record["mode"]),
        ):
            if str(arrays["metadata." + label].item()) != expected:
                failures.append(label + " metadata mismatch")
        if _mismatches(_plain(settings), record["settings"], "settings"):
            failures.append("settings protocol mismatch")
        if record["state"] != ("smoke" if record["mode"] == "smoke" else "candidate_pilot"):
            failures.append("pilot state mismatch")
        if record["mode"] not in ("smoke", "full"):
            failures.append("pilot mode mismatch")
        if record["research_acceptance"] is not False or record["freeze_eligible"] is not False:
            failures.append("pilot cannot assert research acceptance or freeze")
        failures.extend(_invariants(record, arrays))
        recomputed = summarize(record, arrays)
        failures.extend(_mismatches(recomputed, record["summary"], "summary"))
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as exc:
        failures.append("pilot evidence evaluation: " + str(exc))
    return {
        "passed": not failures,
        "failures": failures,
        "recomputed": recomputed,
        "research_acceptance": False,
        "fresh_regenerated": False,
    }


def check(saved, fresh=False):
    """Check saved raw evidence; optionally regenerate with declared numerical tolerances."""
    directory = Path(saved)
    if directory.suffix == ".json":
        directory = directory.parent
    try:
        record, arrays = _artifacts().load_bundle(directory, stem="pilot")
    except (OSError, AssertionError, ValueError) as exc:
        return {
            "passed": False,
            "failures": ["artifact provenance/load: " + str(exc)],
            "recomputed": None,
            "research_acceptance": False,
            "fresh_regenerated": False,
        }
    result = check_record(record, arrays)
    if fresh and result["passed"]:
        regenerated, raw = _compute(_protocol(record["protocol"]), record["mode"] == "smoke")
        tolerance = record["settings"]["fresh_tolerance"]
        if arrays.keys() != raw.keys():
            result["failures"].append("fresh array keys mismatch")
        for key in arrays.keys() & raw.keys():
            first, second = np.asarray(arrays[key]), np.asarray(raw[key])
            if first.shape != second.shape or first.dtype.kind != second.dtype.kind:
                result["failures"].append("fresh " + key + " shape/type mismatch")
            elif first.dtype.kind in "fc":
                if not np.allclose(first, second, **tolerance, equal_nan=True):
                    result["failures"].append("fresh " + key + " numerical mismatch")
            elif not np.array_equal(first, second):
                result["failures"].append("fresh " + key + " mismatch")
        result["failures"].extend(
            _mismatches(regenerated["summary"], record["summary"], "fresh summary", **tolerance)
        )
        result["fresh_regenerated"] = True
        result["passed"] = not result["failures"]
    return result


def main(argv=None):
    """Run or inspect numerical pilot evidence from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        result = check(args.output, fresh=args.fresh)
        print(_json({key: value for key, value in result.items() if key != "recomputed"}))
        return 0 if result["passed"] else 1
    if args.fresh:
        parser.error("--fresh requires --check")
    record = run_pilot(args.output, smoke=args.smoke, protocol=args.protocol)
    print(
        _json(
            {
                "state": record["state"],
                "mode": record["mode"],
                "research_acceptance": record["research_acceptance"],
                "total_wall_s": record["timing"]["total_wall_s"],
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
