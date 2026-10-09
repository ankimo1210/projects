"""Frozen, CPU-only Heston/local-volatility comparison and raw-evidence checker.

Main execution needs an independently reviewed full numerical pilot. Saved
monthly observations, failed paths, source surface cells and independent PDE
evidence are retained. Checking a bundle never estimates a claim by filtering
failed paths. Hashes identify stored blobs; statistics use the original arrays.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
_MODULES = {}
_SCHEMA = "RB-F04-reference-v1"
_MODELS = ("heston", "local")
_PRECISION_KEYS = (
    "sampling_95_half_width",
    "heston_step_empirical_refinement",
    "local_step_empirical_refinement",
    "pilot_surface_empirical_refinement",
    "pde_vanilla_residual",
    "fourier_vanilla_residual",
    "vanilla_mc_sampling_multiplier",
    "vanilla_mc_empirical_step_allowance",
)


def _module(name):
    if name not in _MODULES:
        path = (
            HERE.parents[0] / "RB-F05/discrete/artifacts.py"
            if name == "artifacts"
            else HERE / (name + ".py")
        )
        spec = importlib.util.spec_from_file_location("rbf04_reference_" + name, path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = loaded
        spec.loader.exec_module(loaded)
        _MODULES[name] = loaded
    return _MODULES[name]


def _json(value):
    """Represent unsupported nonfinite values explicitly as JSON null."""
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json(value.tolist())
    if isinstance(value, np.generic):
        return _json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _snapshot(value):
    return np.asarray(json.dumps(_json(value), sort_keys=True, separators=(",", ":")))


def _read_snapshot(arrays, name):
    value = arrays[name]
    if value.shape != () or value.dtype.kind not in "US":
        raise ValueError(name + ": scalar JSON metadata required")
    return json.loads(value.item())


def _integer(value, minimum, label):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(label + ": integer outside input dimensions")


def _precision_contract(p):
    precision = p.get("numerical_precision")
    if precision is None:
        return None
    if (
        not isinstance(precision, dict)
        or set(precision) != set(_PRECISION_KEYS)
        or any(
            isinstance(precision[k], bool)
            or not isinstance(precision[k], (float, int))
            or not np.isfinite(precision[k])
            or precision[k] < 0
            for k in _PRECISION_KEYS
        )
    ):
        raise ValueError("complete finite nonnegative frozen numerical_precision budget required")
    if precision["vanilla_mc_sampling_multiplier"] != 6.0:
        raise ValueError("frozen vanilla MC guard multiplier must be six")
    return precision


def _validate_protocol(p):
    """Validate physical contracts and independent, nested simulation dimensions."""
    if p.get("study") != "RB-F04-dynamics-v1" or p.get("schema") != 1:
        raise ValueError("unknown protocol schema/study")
    parameters = _module("pilot").module("surface").HestonParameters(**p["parameters"])
    contract = p["contract"]
    expiry = contract["expiry"]
    if (
        not np.isfinite(expiry)
        or expiry <= 0
        or contract["asian_strike"] <= 0
        or contract["include_initial"] is not False
        or contract["payment"] != "expiry"
        or not np.allclose(
            contract["observations"], np.arange(1, 13) * expiry / 12, rtol=0, atol=1e-14
        )
    ):
        raise ValueError("fixed twelve monthly observations and expiry payment required")
    main = p["main"]
    _integer(main["paths"], 2, "paths")
    _integer(main["block_size"], 1, "block size")
    seeds = main["seeds"]
    if len(seeds) != 3 or len(set(seeds)) != 3:
        raise ValueError("three distinct independent seed streams required")
    for seed in seeds:
        _integer(seed, 0, "seed")
    levels = main["steps"]
    if len(levels) < 3 or levels != sorted(set(levels)):
        raise ValueError("at least three ordered nested monthly levels required")
    for level in levels:
        _integer(level, 12, "steps")
        if level % 12 or levels[-1] % level:
            raise ValueError("nested monthly steps must divide the finest level")
    s = main["surface"]
    _integer(s["time_nodes"], 2, "surface time nodes")
    _integer(s["z_nodes"], 2, "surface z nodes")
    _integer(s["order"], 16, "Fourier order")
    if (
        not all(
            np.isfinite(s[k]) and s[k] > 0
            for k in ("z_width", "times_min", "frequency_scale", "density_floor")
        )
        or s["times_min"] >= expiry
        or not isinstance(s["allow_row_wings"], bool)
    ):
        raise ValueError("finite positive surface settings and explicit wing choice required")
    for key in ("times", "holdout_times"):
        values = np.asarray(p["quotes"][key], dtype=float)
        if (
            values.ndim != 1
            or not len(values)
            or not np.isfinite(values).all()
            or np.any(values <= 0)
            or np.any(values > expiry)
            or not np.allclose(
                values * 12 / expiry, np.rint(values * 12 / expiry), rtol=0, atol=1e-12
            )
        ):
            raise ValueError("quote times must be within the fixed monthly contract")
    for key in ("strikes", "holdout_strikes"):
        values = np.asarray(p["quotes"][key], dtype=float)
        if (
            values.ndim != 1
            or not len(values)
            or not np.isfinite(values).all()
            or np.any(values <= 0)
        ):
            raise ValueError("finite positive quote strikes required")
    two = p["two_date"]
    dates = np.asarray([two["first"], two["second"]])
    bins = np.asarray(two["bins"], dtype=float)
    if (
        not np.isfinite(dates).all()
        or not (0 < dates[0] < dates[1] <= expiry)
        or not np.allclose(dates * 12 / expiry, np.rint(dates * 12 / expiry))
        or bins.ndim != 1
        or not bins.size
        or not np.isfinite(bins).all()
        or np.any(np.diff(bins) <= 0)
        or not np.isfinite(two["conditional_threshold"])
    ):
        raise ValueError("ordered monthly two-date events and increasing bins required")
    _integer(two.get("minimum_count", 32), 1, "conditional minimum count")
    if p.get("constraints") != {
        "cpu": True,
        "torch": False,
        "public_api_changes": False,
        "production_dependencies": False,
        "drop_unsupported_paths": False,
    }:
        raise ValueError("fixed CPU/dependency/retained-failure constraints required")
    _precision_contract(p)
    return parameters


def _surface_settings(p):
    s = p["main"]["surface"]
    return {
        "times": np.geomspace(s["times_min"], p["contract"]["expiry"], s["time_nodes"]),
        "z_nodes": np.linspace(-s["z_width"], s["z_width"], s["z_nodes"]),
        **{key: s[key] for key in ("order", "frequency_scale", "density_floor", "allow_row_wings")},
    }


def _close(actual, expected, name):
    aa, bb = np.asarray(actual), np.asarray(expected)
    if aa.shape != bb.shape:
        raise ValueError(name + ": shapes differ")
    if aa.dtype.kind in "USbiu" or bb.dtype.kind in "USbiu":
        good = np.array_equal(aa, bb)
    else:
        good = np.allclose(aa, bb, rtol=1e-9, atol=1e-10, equal_nan=True)
    if not good:
        raise ValueError(name + ": evidence differs from recomputation")


def _compare(actual, expected, name, *, exact=False):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(name + ": keys differ")
        for key, value in expected.items():
            _compare(actual[key], value, name + "." + key, exact=exact)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(name + ": lengths differ")
        for index, value in enumerate(expected):
            _compare(actual[index], value, f"{name}[{index}]", exact=exact)
    elif isinstance(expected, bool):
        if not isinstance(actual, bool) or actual != expected:
            raise ValueError(name + ": boolean status differs")
    elif exact and isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or actual != expected:
            raise ValueError(name + ": approved numeric contract differs")
    elif isinstance(expected, float):
        if actual is None:
            raise ValueError(name + ": missing numeric claim")
        _close(actual, expected, name)
    elif actual != expected:
        raise ValueError(name + ": metadata/status differs")


def _review_evidence(p, pilot_record, pilot_arrays, review_record):
    """Verify numeric pilot evidence and the exact reviewed surface selection."""
    freeze = p.get("freeze", {})
    if (
        freeze.get("reviewed") is not True
        or freeze.get("pilot_mode") != "full"
        or not freeze.get("reviewed_by")
        or review_record.get("status") != "approved"
        or review_record.get("pilot_sha256") != freeze.get("pilot_sha256")
        or review_record.get("selected_surface") != freeze.get("selected_surface")
    ):
        raise ValueError("approved full pilot review and matching reviewed selection required")
    for key in ("numerical_precision", "main"):
        if key not in p or key not in review_record:
            raise ValueError("reviewed " + key + ": explicit approved contract required")
        _compare(p[key], review_record[key], "reviewed " + key, exact=True)
    checked = _module("pilot").check_record(pilot_record, pilot_arrays)
    if not checked["passed"] or pilot_record.get("state") != "candidate_pilot":
        raise ValueError("full numerical pilot check failed")
    previous = pilot_record["protocol"]
    for key in ("parameters", "contract", "quotes", "two_date", "pilot", "constraints"):
        _compare(p[key], previous[key], "reviewed pilot protocol." + key, exact=True)
    if pilot_record["settings"]["paths"] != p["pilot"]["paths"]:
        raise ValueError("full pilot path dimensions required")
    selected = freeze["selected_surface"]
    spec = pilot_record["settings"]["surface_specs"][selected]
    expected = _surface_settings(p)
    for key in ("times", "z_nodes", "order", "frequency_scale", "density_floor", "allow_row_wings"):
        _close(spec[key], expected[key], "selected surface " + key)
    prefix = "surface_pde." + selected + "."
    for key in ("quote_times", "quote_strikes", "price", "supported"):
        if prefix + key not in pilot_arrays:
            raise ValueError("independent PDE for selected surface is required")
    if not np.asarray(pilot_arrays[prefix + "supported"]).all():
        raise ValueError("selected surface PDE is unsupported")
    expected_times = np.concatenate(
        [
            np.repeat(p["quotes"][tk], len(p["quotes"][sk]))
            for tk, sk in (("times", "strikes"), ("holdout_times", "holdout_strikes"))
        ]
    )
    expected_strikes = np.concatenate(
        [
            np.tile(p["quotes"][sk], len(p["quotes"][tk]))
            for tk, sk in (("times", "strikes"), ("holdout_times", "holdout_strikes"))
        ]
    )
    _close(pilot_arrays[prefix + "quote_times"], expected_times, "selected PDE quote dates")
    _close(pilot_arrays[prefix + "quote_strikes"], expected_strikes, "selected PDE quote strikes")
    if pilot_arrays[prefix + "price"].shape != expected_times.shape:
        raise ValueError("selected PDE must retain every quote and holdout price")
    return checked["recomputed"]


def _review_files(p):
    freeze = p.get("freeze", {})
    needed = ("pilot_path", "pilot_sha256", "review_record", "review_sha256")
    if not all(freeze.get(key) for key in needed):
        raise ValueError("full pilot review files must be recorded before main execution")
    paths = {}
    for key in ("pilot_path", "review_record"):
        relative = Path(freeze[key])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("review and pilot paths must be relative to the study")
        paths[key] = HERE / relative
    for pathkey, hashkey in (("pilot_path", "pilot_sha256"), ("review_record", "review_sha256")):
        if hashlib.sha256(paths[pathkey].read_bytes()).hexdigest() != freeze[hashkey]:
            raise ValueError("reviewed " + pathkey + " blob provenance differs")
    pilot_record, pilot_arrays = _module("artifacts").load_bundle(
        paths["pilot_path"].parent, stem=paths["pilot_path"].stem
    )
    review_record = json.loads(paths["review_record"].read_text())
    _review_evidence(p, pilot_record, pilot_arrays, review_record)
    provenance = {
        "pilot_blob": paths["pilot_path"].read_bytes().decode("utf-8"),
        "review_blob": paths["review_record"].read_bytes().decode("utf-8"),
    }
    return pilot_record, pilot_arrays, review_record, provenance


def _check_review_provenance(arrays, p):
    """Check original JSON blobs without assigning hashes numerical meaning."""
    for name, key in (("pilot", "pilot_sha256"), ("review", "review_sha256")):
        blob = arrays["metadata." + name + "_blob"]
        if blob.shape != () or blob.dtype.kind not in "US":
            raise ValueError("original reviewed JSON blob provenance must be retained")
        original = blob.item()
        if isinstance(original, bytes):
            original = original.decode("utf-8")
        if hashlib.sha256(original.encode("utf-8")).hexdigest() != p["freeze"][key]:
            raise ValueError("reviewed " + name + " blob provenance differs")
        _compare(
            _read_snapshot(arrays, "metadata." + name + "_record"),
            json.loads(original),
            name + " original JSON evidence",
            exact=True,
        )


def _quote_references(parameters, p):
    arrays = {}
    financial, refs = _module("pilot").module("surface"), _module("reference_methods")
    for group, timekey, strikekey in (
        ("quotes", "times", "strikes"),
        ("holdouts", "holdout_times", "holdout_strikes"),
    ):
        times, strikes = p["quotes"][timekey], p["quotes"][strikekey]
        prefix = "reference." + group + "."
        arrays[prefix + "times"] = np.repeat(times, len(strikes))
        arrays[prefix + "strikes"] = np.tile(strikes, len(times)).astype(float)
        prices, independent = [], []
        for t in times:
            source = financial.fourier_surface(
                strikes,
                t,
                parameters,
                order=p["main"]["surface"]["order"],
                max_frequency=p["main"]["surface"]["frequency_scale"] / np.sqrt(t),
                density_floor=p["main"]["surface"]["density_floor"],
            )
            prices.extend(source["price"])
            independent.extend(refs.independent_heston_call(strikes, t, parameters, upper=500))
        arrays[prefix + "fourier"] = np.asarray(prices)
        arrays[prefix + "independent"] = np.asarray(independent)
    return arrays


def _seed_arrays(arrays, seed):
    prefix = f"seed.{seed}."
    return {
        key.removeprefix(prefix): value for key, value in arrays.items() if key.startswith(prefix)
    }


def _combined_arrays(arrays, p):
    seeds = [_seed_arrays(arrays, seed) for seed in p["main"]["seeds"]]
    keys = set().union(*(s.keys() for s in seeds))
    combined = {}
    for key in keys:
        chunks = []
        for seed in seeds:
            if key not in seed and ".status." not in key:
                raise ValueError("missing original seed evidence: " + key)
            chunks.append(seed.get(key, np.zeros(p["main"]["paths"], dtype=np.int64)))
        combined[key] = np.concatenate(chunks)
    return combined


def _surface_summary(arrays, p):
    support = arrays["surface.supported"]
    density = arrays["surface.density"]
    variance = arrays["surface.local_variance"]
    return {
        "time_nodes": len(arrays["surface.times"]),
        "z_nodes": len(arrays["surface.z_nodes"]),
        "supported_cells": int(support.sum()),
        "unsupported_cells": int((~support).sum()),
        "minimum_supported_density": float(np.min(density[support])),
        "minimum_supported_variance": float(np.min(variance[support])),
        "maximum_supported_variance": float(np.max(variance[support])),
        "allow_row_wings": p["main"]["surface"]["allow_row_wings"],
        "early_time_extension": "first positive time row, status-labelled",
        "initial_state": "v0 only at t=0 and S0",
    }


def _pilot_components(arrays, p):
    """Empirical refinements are diagnostics, never certified bias bounds."""
    if p["state"] == "test":
        return {"pilot_surface_empirical_refinement": None, "pde_vanilla_residual": None}
    freeze, expiry = p["freeze"], p["contract"]["expiry"]
    selected = freeze["selected_surface"]
    original = {
        key.removeprefix("pilot."): value
        for key, value in arrays.items()
        if key.startswith("pilot.")
    }
    settings = _read_snapshot(arrays, "metadata.pilot_record")["settings"]
    finest = max(settings["steps"])
    analytic = _module("pilot").module("analytics")
    strike, rate = p["contract"]["asian_strike"], p["parameters"]["rate"]
    selected_payoff = analytic.asian_payoffs(
        original[f"paths.{selected}.{finest}.local.observations"], strike, rate, expiry
    )
    changes = []
    change_rows = []
    for variant in settings["surface_specs"]:
        key = f"paths.{variant}.{finest}.local.observations"
        if key in original:
            other = analytic.asian_payoffs(original[key], strike, rate, expiry)
            summary = analytic.sample_summary(other - selected_payoff)
            changes.append(summary)
            change_rows.append({"variant": variant, **summary})
    surface_change = (
        max(abs(float(row["mean"])) + 1.96 * float(row["standard_error"]) for row in changes)
        if changes and all(row["supported"] for row in changes)
        else np.nan
    )
    prefix = f"surface_pde.{selected}."
    times, strikes, price = (
        original[prefix + key] for key in ("quote_times", "quote_strikes", "price")
    )
    reference = np.concatenate(
        [arrays[f"reference.{group}.independent"] for group in ("quotes", "holdouts")]
    )
    quote_times, quote_strikes = (
        np.concatenate([arrays[f"reference.{group}.{key}"] for group in ("quotes", "holdouts")])
        for key in ("times", "strikes")
    )
    residuals = []
    for t, k, value in zip(np.ravel(times), np.ravel(strikes), np.ravel(price), strict=True):
        mask = np.isclose(quote_times, t) & np.isclose(quote_strikes, k)
        if mask.sum() == 1:
            residuals.append(abs(value - reference[mask][0]))
        else:
            raise ValueError("selected PDE quote coverage differs from frozen reference")
    return {
        "pilot_surface_empirical_refinement": surface_change,
        "pde_vanilla_residual": max(residuals) if residuals else np.nan,
        "pilot_surface_changes": change_rows,
    }


def _vanilla_guard(metrics, p, *, pde_residual):
    """Per-model pointwise MC guards; six SE is not a global confidence interval."""
    precision = p["numerical_precision"]
    multiplier = precision["vanilla_mc_sampling_multiplier"]
    allowance = precision["vanilla_mc_empirical_step_allowance"]
    row = metrics["levels"][-1]
    last = metrics["step_changes"][-1]
    result = {}
    for group, statkey, residualkey, stepkey in (
        ("quotes", "vanilla", "vanilla_residuals", "_vanilla"),
        ("holdouts", "holdout_vanilla", "holdout_vanilla_residuals", "_holdout_vanilla"),
    ):
        result[group] = {}
        for model in _MODELS:
            residual = np.asarray(row[residualkey][model], dtype=float)
            se = np.asarray(row[statkey][model]["standard_error"], dtype=float)
            tolerance = multiplier * se + allowance + pde_residual
            supported = np.asarray(row[statkey][model]["supported"], dtype=bool)
            result[group][model] = {
                "residual": residual,
                "standard_error": se,
                "tolerance": tolerance,
                "supported": supported,
                "passed": supported & np.isfinite(tolerance) & (np.abs(residual) <= tolerance),
                "empirical_step_mean": last[model + stepkey]["mean"],
                "empirical_step_standard_error": last[model + stepkey]["standard_error"],
            }
    return _json(result)


def _decision(combined, arrays, p, seeds):
    finest = combined["levels"][-1]
    difference = finest["asian"]["difference"]
    last = combined["step_changes"][-1]
    components = {
        "sampling_95_half_width": 1.96 * difference["standard_error"],
        **{
            model + "_step_empirical_refinement": abs(last[model + "_asian"]["mean"])
            + 1.96 * last[model + "_asian"]["standard_error"]
            for model in _MODELS
        },
        "difference_step_empirical_refinement": abs(last["difference_asian"]["mean"])
        + 1.96 * last["difference_asian"]["standard_error"],
        "step_changes": {model: last[model + "_asian"] for model in (*_MODELS, "difference")},
        **_pilot_components(arrays, p),
    }
    precision = _precision_contract(p)
    result = {
        "status": "pending_precision_budget",
        "error_components": components,
        "precision_checks": {},
        "difference_identified": None,
        "sampling_interval": "combined Asian local-minus-Heston approximate pointwise 95% normal interval; sampling only",
        "joint_intervals": "pointwise descriptive SE; no global confidence claim across bins",
        "empty_joint_cells": "zero observed count/SE is not proof of probability zero",
        "refinement_interpretation": "empirical two-level changes, not rigorous bias bounds",
        "refinement_sampling": "absolute paired change mean plus 1.96 change SE; no global confidence claim",
        "pde_interpretation": "vanilla diagnostic; not an Asian price error bound",
        "model_ranking": "synthetic descriptive comparison; no market performance ranking",
    }
    if precision is None:
        return result
    quote_residual = max(
        np.max(
            np.abs(arrays[f"reference.{group}.fourier"] - arrays[f"reference.{group}.independent"])
        )
        for group in ("quotes", "holdouts")
    )
    components["fourier_vanilla_residual"] = float(quote_residual)
    for key in _PRECISION_KEYS[:6]:
        value = components[key]
        result["precision_checks"][key] = bool(
            value is not None and np.isfinite(value) and value <= precision[key]
        )
    pde_residual = components["pde_vanilla_residual"]
    pde_value = pde_residual if pde_residual is not None else np.nan
    guards = [
        {"seed": row["seed"], "guard": _vanilla_guard(row["metrics"], p, pde_residual=pde_value)}
        for row in seeds
    ]
    pooled_guard = _vanilla_guard(combined, p, pde_residual=pde_value)
    result["vanilla_mc_guard"] = {
        "seeds": guards,
        "combined": pooled_guard,
        "interpretation": "per model/seed/quote stochastic implementation guard; not proof of entire surface equality or global CI",
        "sampling_multiplier": precision["vanilla_mc_sampling_multiplier"],
        "empirical_step_allowance": precision["vanilla_mc_empirical_step_allowance"],
        "pde_residual_allowance": pde_residual,
    }
    result["precision_checks"]["vanilla_mc_guard"] = all(
        np.asarray(guard[group][model]["passed"]).all()
        for guard in [*(row["guard"] for row in guards), pooled_guard]
        for group in ("quotes", "holdouts")
        for model in _MODELS
    )
    if not difference["supported"]:
        result["status"] = "unsupported_paths"
    elif not all(result["precision_checks"].values()):
        result["status"] = "numerical_precision_insufficient"
    else:
        envelope = sum(
            components[k]
            for k in (
                "sampling_95_half_width",
                "heston_step_empirical_refinement",
                "local_step_empirical_refinement",
                "pilot_surface_empirical_refinement",
            )
        )
        result["empirical_identification_threshold"] = envelope
        result["difference_identified"] = bool(abs(difference["mean"]) > envelope)
        result["status"] = (
            "difference_identified"
            if result["difference_identified"]
            else "difference_not_identified"
        )
    return result


def _summarize(arrays, p):
    """Recompute all descriptive numeric claims from original monthly paths."""
    pilot = _module("pilot")
    seeds = [
        {
            "seed": seed,
            "metrics": pilot.path_metrics(_seed_arrays(arrays, seed), p, steps=p["main"]["steps"]),
        }
        for seed in p["main"]["seeds"]
    ]
    analytic = pilot.module("analytics")
    rate, contract = p["parameters"]["rate"], p["contract"]
    pooled = _combined_arrays(arrays, p)
    combined = pilot.path_metrics(pooled, p, steps=p["main"]["steps"])
    quote_shape = (len(p["quotes"]["times"]), len(p["quotes"]["strikes"]))
    holdout_shape = (len(p["quotes"]["holdout_times"]), len(p["quotes"]["holdout_strikes"]))
    for metrics, raw in [
        *((seed["metrics"], _seed_arrays(arrays, seed["seed"])) for seed in seeds),
        (combined, pooled),
    ]:
        for row in metrics["levels"]:
            holdout = {
                model: analytic.vanilla_payoffs(
                    raw[f"{row['steps']}.{model}.observations"],
                    p["quotes"]["holdout_times"],
                    p["quotes"]["holdout_strikes"],
                    rate,
                    contract["expiry"],
                )
                for model in _MODELS
            }
            row["holdout_vanilla"] = analytic.paired_summary(holdout["heston"], holdout["local"])
            row["asian_sampling_95_half_width"] = {
                model: 1.96 * row["asian"][model]["standard_error"]
                for model in (*_MODELS, "difference")
            }
            row["vanilla_residuals"] = {
                model: row["vanilla"][model]["mean"]
                - arrays["reference.quotes.independent"].reshape(quote_shape)
                for model in _MODELS
            }
            row["holdout_vanilla_residuals"] = {
                model: row["holdout_vanilla"][model]["mean"]
                - arrays["reference.holdouts.independent"].reshape(holdout_shape)
                for model in _MODELS
            }
        for change in metrics["step_changes"]:
            for model in _MODELS:
                high, low = [
                    analytic.vanilla_payoffs(
                        raw[f"{level}.{model}.observations"],
                        p["quotes"]["holdout_times"],
                        p["quotes"]["holdout_strikes"],
                        rate,
                        contract["expiry"],
                    )
                    for level in (change["fine"], change["coarse"])
                ]
                change[model + "_holdout_vanilla"] = analytic.sample_summary(high - low)
    decision = _decision(combined, arrays, p, seeds)
    failures = sum(
        row["diagnostics"][m]["failed_paths"] for row in combined["levels"] for m in _MODELS
    )
    return _json(
        {
            "seeds": seeds,
            "combined": combined,
            "surface": _surface_summary(arrays, p),
            "decision": decision,
            "status": "failed_paths" if failures else "complete",
            "research_acceptance": bool(
                p["state"] == "frozen"
                and not failures
                and decision["status"] in ("difference_identified", "difference_not_identified")
            ),
        }
    )


def _compute_reference(
    p, pilot_record=None, pilot_arrays=None, review_record=None, provenance=None
):
    """Compute internal evidence; the production entry point enforces review first."""
    p = copy.deepcopy(p)
    parameters = _validate_protocol(p)
    if p["state"] not in ("test", "frozen"):
        raise ValueError("internal computation requires frozen protocol or explicit test fixture")
    if p["state"] == "frozen":
        if (
            pilot_record is None
            or pilot_arrays is None
            or review_record is None
            or provenance is None
        ):
            raise ValueError("reviewed full pilot evidence required")
        _review_evidence(p, pilot_record, pilot_arrays, review_record)
    pilot = _module("pilot")
    surface = pilot.build_surface(parameters, **_surface_settings(p))
    if surface["grid"] is None:
        raise ValueError("selected surface cannot support path simulation: " + surface["failure"])
    arrays = dict(surface["arrays"])
    arrays["metadata.protocol"] = _snapshot(p)
    arrays["metadata.mode"] = np.asarray("main" if p["state"] == "frozen" else "test_fixture")
    timings = {"surface_wall_s": surface["wall_s"], "seeds": []}
    if pilot_record is not None:
        arrays.update({"pilot." + key: value.copy() for key, value in pilot_arrays.items()})
        arrays["metadata.pilot_record"] = _snapshot(pilot_record)
        arrays["metadata.review_record"] = _snapshot(review_record)
        arrays.update({"metadata." + name: np.asarray(value) for name, value in provenance.items()})
        _check_review_provenance(arrays, p)
        selected = p["freeze"]["selected_surface"]
        for key, value in surface["arrays"].items():
            suffix = key.removeprefix("surface.")
            _close(
                value, pilot_arrays[f"surface.{selected}.{suffix}"], "reviewed surface " + suffix
            )
    arrays.update(_quote_references(parameters, p))
    main = p["main"]
    for seed in main["seeds"]:
        run = pilot.simulate(
            parameters,
            surface["grid"],
            paths=main["paths"],
            seed=seed,
            steps=main["steps"],
            block_size=main["block_size"],
            expiry=p["contract"]["expiry"],
        )
        arrays.update({f"seed.{seed}." + key: value for key, value in run["arrays"].items()})
        timings["seeds"].append({"seed": seed, "wall_s": run["wall_s"]})
    record = {
        "schema": _SCHEMA,
        "protocol": p,
        "mode": arrays["metadata.mode"].item(),
        "timings": timings,
        **_summarize(arrays, p),
    }
    if pilot_record is not None:
        record["pilot_summary"] = _json(
            _review_evidence(p, pilot_record, pilot_arrays, review_record)
        )
    return record, arrays


def run_reference(output, protocol=None):
    """Run and save a frozen main experiment after independently reviewed full pilot."""
    p = (
        copy.deepcopy(protocol)
        if protocol is not None
        else json.loads((HERE / "protocol.json").read_text())
    )
    existing = Path(output) / "reference.json"
    if existing.exists():
        prior = json.loads(existing.read_text())
        if prior.get("protocol") != p:
            raise ValueError("existing reference protocol differs; refreeze cannot overwrite it")
        raise ValueError("existing reference already saved; check it or select a new directory")
    if p.get("state") != "frozen":
        raise ValueError("main protocol must be frozen before execution")
    _validate_protocol(p)
    evidence = _review_files(p)
    record, arrays = _compute_reference(p, *evidence)
    save_result(output, record, arrays)
    return record, arrays


def _check_paths(arrays, p):
    count, spot, v0 = p["main"]["paths"], p["parameters"]["spot"], p["parameters"]["v0"]
    expected = {
        (seed, level, model)
        for seed in p["main"]["seeds"]
        for level in p["main"]["steps"]
        for model in _MODELS
    }
    found = set()
    for key in arrays:
        if key.startswith("seed."):
            parts = key.split(".")
            found.add((int(parts[1]), int(parts[2]), parts[3]))
    if found != expected:
        raise ValueError("frozen seed/model/level roster differs")
    for seed, level, model in sorted(expected):
        prefix = f"seed.{seed}.{level}.{model}."
        obs, failed, reasons = (
            arrays[prefix + k] for k in ("observations", "failures", "failure_reasons")
        )
        if (
            obs.shape != (count, 13)
            or failed.shape != (count,)
            or failed.dtype.kind != "b"
            or reasons.shape != (count,)
            or reasons.dtype.kind not in "US"
        ):
            raise ValueError("all original paths and per-path failure evidence must be retained")
        _close(obs[:, 0], np.full(count, spot), "initial spot")
        invalid = ~np.all(np.isfinite(obs) & (obs > 0), axis=1)
        if not np.array_equal(invalid, failed) or not np.array_equal(reasons != "", failed):
            raise ValueError("failure mask/reasons must identify every failed original path")
        for row in obs[failed]:
            bad = np.flatnonzero(~np.isfinite(row) | (row <= 0))
            if not len(bad) or not np.isnan(row[bad[0] :]).all():
                raise ValueError("failed paths retain prior values and an explicit NaN suffix")
        if model == "heston":
            variance = arrays[prefix + "variance_observations"]
            negative = arrays[prefix + "negative_variance_counts"]
            if variance.shape != obs.shape or not np.array_equal(
                np.isfinite(variance), np.isfinite(obs)
            ):
                raise ValueError("raw monthly Heston variance states must be retained")
            _close(variance[:, 0], np.full(count, v0), "initial variance")
            _counts(negative, count, level, "negative variance states")
            if np.any(negative < np.sum(variance < 0, axis=1)):
                raise ValueError("negative monthly states exceed retained negative step counts")
        else:
            labelled_statuses = {
                key.removeprefix(prefix + "status."): value
                for key, value in arrays.items()
                if key.startswith(prefix + "status.")
            }
            statuses = list(labelled_statuses.values())
            if not statuses:
                raise ValueError("local surface visits must be retained")
            for label, value in labelled_statuses.items():
                _counts(value, count, level, "surface status visits")
                if label.startswith("unsupported") and np.any((value > 0) & ~failed):
                    raise ValueError("every unsupported surface visit must fail its original path")
            total = np.sum(statuses, axis=0)
            if np.any(total[~failed] != level) or np.any((total < 1) | (total > level)):
                raise ValueError("surface status visit accounting differs from retained steps")
            initial = arrays.get(prefix + "status.initial_state")
            if initial is None or not np.array_equal(initial, np.ones(count)):
                raise ValueError("only the initial S0 state is defined at time zero")


def _counts(value, count, maximum, name):
    if (
        value.shape != (count,)
        or value.dtype.kind not in "iu"
        or np.any((value < 0) | (value > maximum))
    ):
        raise ValueError(name + ": bounded integer per-path counts required")


def _check_surface(arrays, p, parameters):
    settings = _surface_settings(p)
    for key in ("times", "z_nodes"):
        _close(arrays["surface." + key], settings[key], "frozen surface " + key)
    times, z = settings["times"], settings["z_nodes"]
    shape = (len(times), len(z))
    for key in (
        "price",
        "ck",
        "ckk",
        "ct",
        "density",
        "weighted_density",
        "local_variance",
        "supported",
        "strikes",
    ):
        if arrays["surface." + key].shape != shape:
            raise ValueError("frozen surface source dimensions differ: " + key)
    strikes = parameters.spot * np.exp(
        (parameters.rate - parameters.dividend_yield) * times[:, None]
        + z[None, :] * np.sqrt([parameters.integrated_variance(float(t)) for t in times])[:, None]
    )
    _close(arrays["surface.strikes"], strikes, "standardized source strikes")
    density, weighted, variance = (
        arrays["surface." + key] for key in ("density", "weighted_density", "local_variance")
    )
    if arrays["surface.supported"].dtype.kind != "b":
        raise ValueError("source surface support must be a boolean mask")
    support = (
        np.isfinite(density)
        & np.isfinite(weighted)
        & (density > settings["density_floor"])
        & (weighted > 0)
    )
    for key in ("price", "ck", "ckk", "ct"):
        support &= np.isfinite(arrays["surface." + key])
    half_density, half_weighted = (
        arrays["surface." + key] for key in ("half_density", "half_weighted_density")
    )
    if half_density.shape != shape or half_weighted.shape != shape:
        raise ValueError("source half-order diagnostics shape differs")
    cutoff, cutoff_weighted = (
        arrays["surface." + key] for key in ("cutoff_cf_abs", "cutoff_weighted_cf_abs")
    )
    if cutoff.shape != (len(times),) or cutoff_weighted.shape != (len(times),):
        raise ValueError("source cutoff diagnostics shape differs")
    if (
        not np.isfinite(cutoff).all()
        or not np.isfinite(cutoff_weighted).all()
        or np.any(cutoff < 0)
        or np.any(cutoff_weighted < 0)
    ):
        raise ValueError("source Fourier cutoff amplitudes must be finite and nonnegative")
    if parameters.xi != 0:
        support &= np.abs(density - half_density) <= 1e-3 * np.abs(density)
        support &= np.abs(weighted - half_weighted) <= 1e-3 * np.abs(weighted)
        support &= (cutoff[:, None] <= 1e-10) & (
            cutoff_weighted[:, None] <= 1e-10 * max(parameters.v0, parameters.theta)
        )
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ratio = np.divide(weighted, density, out=np.full(shape, np.nan), where=support)
    support &= np.isfinite(ratio) & (ratio > 0)
    # This is the conditional-variance support contract of fourier_surface.
    _close(arrays["surface.supported"], support, "source density support")
    _close(variance, np.where(support, ratio, np.nan), "raw conditional local variance")
    bounds = arrays["surface.wing_boundaries"]
    if bounds.shape != (len(times), 2):
        raise ValueError("source wing boundaries differ")
    for i, row in enumerate(support):
        indices = np.flatnonzero(row)
        if len(indices) < 2 or np.any(np.diff(indices) != 1):
            raise ValueError("supported source interval must be contiguous with two nodes")
        _close(bounds[i], [indices[0], indices[-1]], "source supported wings")
    if not settings["allow_row_wings"] and not support.all():
        raise ValueError("unsupported source cells cannot be silently substituted")
    discount = np.exp(-parameters.rate * times)[:, None]
    _close(arrays["surface.ckk"], discount * density / strikes, "discounted source log density")
    _close(
        arrays["surface.ct"]
        + parameters.dividend_yield * arrays["surface.price"]
        + (parameters.rate - parameters.dividend_yield) * strikes * arrays["surface.ck"],
        0.5 * strikes * discount * weighted,
        "Dupire time/strike derivative identity",
    )
    grid_options = {"wing_boundaries": bounds} if not support.all() else {}
    return (
        _module("pilot")
        .module("surface")
        .LocalVarianceGrid(times, z, variance, parameters, **grid_options)
    )


def _check_quotes(arrays, p):
    for group, tk, sk in (
        ("quotes", "times", "strikes"),
        ("holdouts", "holdout_times", "holdout_strikes"),
    ):
        prefix = f"reference.{group}."
        times, strikes = p["quotes"][tk], p["quotes"][sk]
        _close(arrays[prefix + "times"], np.repeat(times, len(strikes)), "fixed reference dates")
        _close(arrays[prefix + "strikes"], np.tile(strikes, len(times)), "fixed reference strikes")
        for key in ("fourier", "independent"):
            value = arrays[prefix + key]
            if value.shape != arrays[prefix + "times"].shape or not np.isfinite(value).all():
                raise ValueError("flat finite reference quote prices required")


def check_record(record, arrays, *, fresh=False):
    """Recompute saved claims and statuses; fresh additionally regenerates original paths."""
    failures, recomputed = [], {}
    try:
        if record.get("schema") != _SCHEMA:
            raise ValueError("unknown reference schema")
        allowed = {
            "schema",
            "protocol",
            "mode",
            "timings",
            "seeds",
            "combined",
            "surface",
            "decision",
            "status",
            "research_acceptance",
            "pilot_summary",
            "artifact",
        }
        if not set(record) <= allowed:
            raise ValueError("unknown saved claims outside the reference schema")
        p = record["protocol"]
        _compare(
            p,
            _read_snapshot(arrays, "metadata.protocol"),
            "protocol/contract/parameters",
            exact=True,
        )
        mode = "main" if p["state"] == "frozen" else "test_fixture"
        if p["state"] not in ("test", "frozen") or record["mode"] != mode:
            raise ValueError("saved mode must distinguish frozen main from test fixture")
        _close(arrays["metadata.mode"], np.asarray(mode), "mode metadata")
        parameters = _validate_protocol(p)
        grid = _check_surface(arrays, p, parameters)
        _check_paths(arrays, p)
        _check_quotes(arrays, p)
        if mode == "main":
            _check_review_provenance(arrays, p)
            pilot_arrays = {
                key.removeprefix("pilot."): value
                for key, value in arrays.items()
                if key.startswith("pilot.")
            }
            pilot_record = _read_snapshot(arrays, "metadata.pilot_record")
            review_record = _read_snapshot(arrays, "metadata.review_record")
            checked = _review_evidence(p, pilot_record, pilot_arrays, review_record)
            _compare(record["pilot_summary"], _json(checked), "recomputed pilot evidence")
            selected = p["freeze"]["selected_surface"]
            for key, value in arrays.items():
                if key.startswith("surface."):
                    suffix = key.removeprefix("surface.")
                    _close(
                        value,
                        pilot_arrays[f"surface.{selected}.{suffix}"],
                        "reviewed source " + key,
                    )
        recomputed = _summarize(arrays, p)
        for key, value in recomputed.items():
            _compare(record[key], value, "saved " + key)
        # Costs are measurements, not reproducible financial evidence.
        timing = record.get("timings", {})
        if not np.isfinite(timing["surface_wall_s"]) or timing["surface_wall_s"] < 0:
            raise ValueError("nonnegative descriptive surface wall cost required")
        if [row["seed"] for row in timing["seeds"]] != p["main"]["seeds"] or any(
            not np.isfinite(row["wall_s"]) or row["wall_s"] < 0 for row in timing["seeds"]
        ):
            raise ValueError("finite descriptive seed timings required")
        if fresh:
            pilot = _module("pilot")
            surface = pilot.build_surface(parameters, **_surface_settings(p))
            for key, value in surface["arrays"].items():
                _close(arrays[key], value, "fresh " + key)
            for key, value in _quote_references(parameters, p).items():
                _close(arrays[key], value, "fresh " + key)
            for seed in p["main"]["seeds"]:
                run = pilot.simulate(
                    parameters,
                    grid,
                    paths=p["main"]["paths"],
                    seed=seed,
                    steps=p["main"]["steps"],
                    block_size=p["main"]["block_size"],
                    expiry=p["contract"]["expiry"],
                )
                saved = _seed_arrays(arrays, seed)
                if set(run["arrays"]) != set(saved):
                    raise ValueError("fresh path/status roster differs")
                for key, value in run["arrays"].items():
                    _close(saved[key], value, f"fresh seed {seed}." + key)
    except (ValueError, KeyError, TypeError, IndexError, AssertionError, OSError) as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    return {
        "passed": not failures,
        "failures": failures,
        "recomputed": recomputed,
        "research_acceptance": bool(not failures and recomputed.get("research_acceptance", False)),
        "fresh_regenerated": bool(fresh and not failures),
    }


def save_result(output, record, arrays):
    """Save original arrays and use existing verified dual CAS above the Git size cap."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "reference.npz", **arrays)
    saved = _json(copy.deepcopy(record))
    filename = output / "reference.json"
    filename.write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
    saved["artifact"] = _module("artifacts").store_large(output, stem="reference")
    saved["artifact"]["arrays"] = {
        key: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in arrays.items()
    }
    filename.write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
    return filename, output / "reference.npz"


def load_result(output=HERE):
    """Load or restore the saved bundle with pickle disabled and verify blob provenance."""
    record, arrays = _module("artifacts").load_bundle(output, stem="reference")
    expected = {
        key: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in arrays.items()
    }
    if record.get("artifact", {}).get("arrays") != expected:
        raise ValueError("saved array registry differs")
    return record, arrays


def check(saved=HERE, *, fresh=False):
    """Check a saved directory from raw arrays, optionally by fresh numeric replay."""
    try:
        path = Path(saved)
        record, arrays = load_result(path.parent if path.is_file() else path)
    except (ValueError, AssertionError, OSError) as exc:
        return {
            "passed": False,
            "failures": [f"{type(exc).__name__}: {exc}"],
            "recomputed": {},
            "research_acceptance": False,
            "fresh_regenerated": False,
        }
    return check_record(record, arrays, fresh=fresh)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.refresh:
        run_reference(args.output)
    elif not args.check:
        parser.error("choose --refresh or --check")
    result = check(args.output, fresh=args.fresh)
    print(json.dumps(_json(result), ensure_ascii=False, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
