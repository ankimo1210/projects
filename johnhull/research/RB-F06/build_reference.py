"""Resumable synthetic Hagan identifiability study and saved numerical audit.

Fit ndarray fields live in NPZ under fit['array_keys']; unpack_fit restores them.
Every original dataset, optimizer attempt, profile point and failure is retained.
The saved checker reprices observations but creates no RNG or optimizer unless
fresh=True is explicitly requested. Fixture data never constitute main evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import os
import platform
import sys
from functools import lru_cache
from pathlib import Path
from time import perf_counter, process_time

import numpy as np
import scipy
from hullkit import _sabr_identifiability as core

HERE = Path(__file__).resolve().parent


@lru_cache(None)
def module(name):
    """Load the small, project-local protocol/reference/analytics module."""
    spec = importlib.util.spec_from_file_location(f"rbf06_runner_{name}", HERE / f"{name}.py")
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


def fixture_protocol():
    """Explicit small candidate fixture; shares pilot streams, never main draws."""
    p = copy.deepcopy(module("protocol").load_protocol())
    p["forward"], p["maturity"] = 80.0, 0.5
    p["truths"][0] = {"name": "fixture_toy", "theta": [0.18, -0.25, 0.30]}
    p["fixture"] = {
        "truth_indices": [0],
        "groups": ["full", "sparse"],
        "reps": 1,
        "start_indices": [0, 8],
        "profile_grids": [[0.12, 0.20, 0.28], [-0.6, -0.3, 0.3], [0, 0.2, 0.4]],
        "refinement_per_bracket": 1,
        "refinement_per_curve": 0,
        "profiles": True,
    }
    return p


def _json(value):
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _digest(value):
    return module("protocol").json_digest(_json(value))


def _equal(actual, expected, name, rtol=2e-6, atol=1e-8):
    try:
        good = (
            np.isfinite(actual).all()
            and np.isfinite(expected).all()
            and np.allclose(actual, expected, rtol=rtol, atol=atol, equal_nan=False)
        )
    except (ValueError, TypeError):
        good = False
    if not good:
        raise ValueError(f"numerical mismatch: {name}")


def _invalid_equal(actual, expected, name, rtol=2e-6, atol=1e-8):
    """Match invalid-slot NaN/+Inf/-Inf masks, then compare only finite entries."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape:
        raise ValueError(f"invalid-slot shape mismatch: {name}")
    for classify in (np.isnan, np.isposinf, np.isneginf):
        if not np.array_equal(classify(actual), classify(expected)):
            raise ValueError(f"invalid-slot nonfinite classification mismatch: {name}")
    finite = np.isfinite(expected)
    _equal(actual[finite], expected[finite], name, rtol=rtol, atol=atol)


def unpack_fit(fit, arrays):
    """Restore core numeric arrays and integer fixed-axis keys from fit metadata."""
    result = {key: value for key, value in fit.items() if key != "array_keys"}
    result.update({name: arrays[key] for name, key in fit.get("array_keys", {}).items()})
    result["fixed"] = {int(axis): value for axis, value in result.get("fixed", {}).items()}
    return result


def _pack_fit(fit, arrays, fit_id):
    result = {"array_keys": {}}
    for name, value in fit.items():
        if isinstance(value, np.ndarray):
            key = f"{fit_id}_{name}"
            arrays[key] = value.copy()
            result["array_keys"][name] = key
        else:
            result[name] = _json(value)
    return result


def _roster(p, phase):
    if phase == "fixture":
        config = p.get("fixture")
        if not config:
            raise ValueError("explicit fixture configuration required")
        truths, groups, reps, starts = (
            config["truth_indices"],
            config["groups"],
            config["reps"],
            config["start_indices"],
        )
    else:
        # Dictionary insertion order is not retained by canonical JSON storage.
        truths, groups = range(len(p["truths"])), sorted(p["groups"])
        reps, starts = p[f"{phase}_reps"], range(len(p["starts"]))
    return [(t, g, r, list(starts)) for t in truths for r in range(-1, reps) for g in groups]


def _binding(p, phase):
    if phase not in {"pilot", "main", "fixture"}:
        raise ValueError("phase must be pilot/main/fixture")
    module("protocol").validate_protocol(p, require_frozen=phase == "main")
    if phase == "main":
        module("protocol").verify_frozen_evidence(p)
        if (
            p.get("state") != "frozen"
            or p.get("frozen", {}).get("pilot_review", {}).get("decision") != "approved"
        ):
            raise ValueError("reviewed frozen protocol required for main")
        if any(
            os.environ.get(name) != "1"
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        ):
            raise ValueError("main requires explicit BLAS1 environment")
    return _digest(p), module("protocol").source_registry()


def _save_pair(directory, stem, record, arrays, replace=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{stem}.npz"
    metadata = directory / f"{stem}.json"
    if not replace and (destination.exists() or metadata.exists()):
        raise FileExistsError(f"saved evidence already exists: {stem}")
    if any(np.asarray(a).dtype.hasobject for a in arrays.values()):
        raise ValueError("object arrays forbidden")
    scratch = destination.with_suffix(".npz.tmp")
    with scratch.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    saved = copy.deepcopy(record)
    saved["npz_digest"] = hashlib.sha256(scratch.read_bytes()).hexdigest()
    saved["array_registry"] = {
        key: {"shape": list(a.shape), "dtype": a.dtype.str} for key, a in arrays.items()
    }
    metadata_scratch = metadata.with_suffix(".json.tmp")
    metadata_scratch.write_text(
        json.dumps(_json(saved), ensure_ascii=False, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    scratch.replace(destination)
    metadata_scratch.replace(metadata)


def _load_pair(directory, stem):
    directory = Path(directory)
    saved = json.loads((directory / f"{stem}.json").read_text(encoding="utf-8"))
    archive = directory / f"{stem}.npz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != saved["npz_digest"]:
        raise ValueError("saved archive identity mismatch")
    with np.load(archive, allow_pickle=False) as bundle:
        arrays = {key: bundle[key].copy() for key in bundle.files}
    if set(arrays) != set(saved["array_registry"]):
        raise ValueError("saved array roster mismatch")
    for key, value in arrays.items():
        if value.dtype.hasobject or saved["array_registry"][key] != {
            "shape": list(value.shape),
            "dtype": value.dtype.str,
        }:
            raise ValueError("saved array schema mismatch")
    return saved, arrays


def load_result(output):
    """Load final original observations with pickle-disabled archive validation."""
    return _load_pair(output, "reference")


def serialization_receipt(output, record):
    """Read separate measured final-save cost; missing receipt means unknown."""
    path = Path(output) / "serialization_cost.json"
    if not path.exists():
        return {
            "pending": True,
            "seconds": None,
            "scope": "final save not measured after interruption",
        }
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (
        receipt["schema"] != "RB-F06-serialization-cost-v1"
        or receipt["reference_record_digest"] != _digest(record)
        or receipt["protocol_digest"] != record["protocol_digest"]
        or receipt["pending"]
        or not np.isfinite(receipt["seconds"])
        or receipt["seconds"] < 0
    ):
        raise ValueError("serialization receipt binding mismatch")
    return receipt


def _checkpoint_keys(dataset):
    keys = {
        dataset[k] for k in ("strikes_key", "quotes_key", "master_quotes_key", "master_noise_key")
    }
    for fit in dataset["fits"]:
        keys.update(fit["array_keys"].values())
        if fit.get("stability_jacobians_key"):
            keys.add(fit["stability_jacobians_key"])
    for field in ("holdout_truth_iv_key", "holdout_truth_prices_key"):
        if field in dataset:
            keys.add(dataset[field])
    return keys


def _checkpoint(output, dataset, arrays, binding):
    # Two alternating versions preserve a previous valid pair if interrupted
    # between the archive and JSON atomic replacements.
    began = perf_counter()
    dataset["checkpoint_revision"] = dataset.get("checkpoint_revision", 0) + 1
    saved = {"schema": "RB-F06-checkpoint-v1", "binding": binding, "dataset": dataset}
    subset = {key: arrays[key] for key in _checkpoint_keys(dataset)}
    _save_pair(
        Path(output) / "checkpoints",
        f"{dataset['dataset_id']}_{dataset['checkpoint_revision'] % 2}",
        saved,
        subset,
        replace=True,
    )
    dataset["checkpoint_seconds"] = dataset.get("checkpoint_seconds", 0.0) + perf_counter() - began


def _resume_dataset(output, dataset_id, binding):
    saved = []
    directory = Path(output) / "checkpoints"
    for slot in (0, 1):
        stem = f"{dataset_id}_{slot}"
        if not (directory / f"{stem}.json").exists():
            continue
        try:
            record, arrays = _load_pair(directory, stem)
        except (ValueError, FileNotFoundError, json.JSONDecodeError):
            continue
        if record["binding"] != binding:
            raise ValueError("checkpoint source/protocol/phase changed")
        saved.append((record["dataset"], arrays))
    return max(saved, key=lambda item: item[0]["checkpoint_revision"]) if saved else (None, {})


def _jacobian_calls(theta, h):
    count = 0
    for axis in range(3):
        if theta[2] == 0 and axis in (1, 2):
            continue
        delta = core.SCALE[axis] * h
        count += (
            2
            if core.LOWER[axis] <= theta[axis] - delta and theta[axis] + delta <= core.UPPER[axis]
            else 3
        )
    return count


def _extra_diagnostics(fit, p, strikes, phase, arrays, fit_id, unrestricted):
    if fit.get("theta") is None:
        return
    theta = fit["theta"]
    if phase != "pilot":
        began = perf_counter()
        holdout = p["forward"] * np.exp(p["holdout_log_moneyness"])
        fit["holdout_iv"] = core.sabr_vols(p["forward"], p["maturity"], p["beta"], theta, holdout)
        fit["holdout_prices"] = (
            module("reference_methods").black_calls(
                p["forward"], p["maturity"], holdout, fit["holdout_iv"]
            )
            * p["discount"]
        )
        fit["holdout_seconds"] = perf_counter() - began
        fit["holdout_iv_evaluations"] = len(holdout)
        fit["holdout_black_evaluations"] = len(holdout)
    if phase != "pilot" and unrestricted:
        began = perf_counter()
        jacobians, calls = [], 0
        for h in p["jacobian_steps_u"]:
            if h == fit["jacobian_step"]:
                jacobians.append(fit["scaled_jacobian"])
            else:
                jacobians.append(
                    core.scaled_jacobian(
                        p["forward"], p["maturity"], p["beta"], theta, strikes, h, p["noise_scale"]
                    )
                )
                calls += _jacobian_calls(theta, h)
        key = f"{fit_id}_stability_jacobians"
        arrays[key] = np.stack(jacobians)
        fit["stability_jacobians_key"] = key
        fit["numerical_stability"] = module("analytics").jacobian_stability(
            jacobians,
            p["rank_rtol"],
            p["jacobian_global_rtol"],
            p["jacobian_smallest_sv_relative_limit"],
        )
        fit["stability_seconds"] = perf_counter() - began
        fit["stability_iv_calls"] = calls
        fit["stability_scalar_iv_evaluations"] = calls * len(strikes)


def _fit_once(
    dataset,
    arrays,
    p,
    phase,
    output,
    binding,
    start_index,
    start,
    fixed,
    fit_id,
    kind,
    global_count,
):
    cached = next((fit for fit in dataset["fits"] if fit["fit_id"] == fit_id), None)
    if cached is not None:
        return cached
    if global_count() >= p["solver_call_cap"]:
        raise ValueError("solver call cap would be exceeded")
    began, cpu = perf_counter(), process_time()
    strikes, quotes = arrays[dataset["strikes_key"]], arrays[dataset["quotes_key"]]
    try:
        fit = core.fit_smile(
            p["forward"],
            p["maturity"],
            p["beta"],
            strikes,
            quotes,
            start,
            fixed=fixed,
            max_nfev=p["fit_max_nfev"] if kind == "unrestricted" else p["profile_max_nfev"],
            noise_scale=p["noise_scale"],
        )
        _extra_diagnostics(fit, p, strikes, phase, arrays, fit_id, kind == "unrestricted")
    except Exception as error:
        fit = {
            "success": False,
            "status": -999,
            "message": f"{type(error).__name__}: {error}",
            "q": None,
            "start": np.asarray(start),
            "fixed": fixed or {},
            "exception": type(error).__name__,
            "residual_calls": None,
            "diagnostic_calls": None,
            "scalar_iv_evaluations": None,
        }
    fit.update(
        fit_id=fit_id,
        kind=kind,
        start_index=start_index,
        attempt_seconds=perf_counter() - began,
        cpu_seconds=process_time() - cpu,
    )
    fit["solver_called"] = True
    packed = _pack_fit(fit, arrays, fit_id)
    dataset["fits"].append(packed)
    _checkpoint(output, dataset, arrays, binding)
    return packed


def _best_ids(fits):
    best = module("analytics").best_records(fits)
    return {name: record["fit_id"] if record else None for name, record in best.items()}


def _find_fit(dataset, fit_id):
    return next((f for f in dataset["fits"] if f["fit_id"] == fit_id), None)


def _profile_point(dataset, arrays, p, phase, output, binding, axis, value, global_count):
    existing = next(
        (
            point
            for point in dataset["profile_points"]
            if point["axis"] == axis and point["value"] == value
        ),
        None,
    )
    if existing:
        return existing
    point_id = f"{dataset['dataset_id']}_p{axis}_{float(value).hex()}"
    nuisance = [i for i in range(3) if i != axis]
    attempts = []
    for index, pair in enumerate(itertools.product(*(p["profile_starts"][i] for i in nuisance))):
        start = np.zeros(3)
        start[axis], start[nuisance] = value, pair
        fit = _fit_once(
            dataset,
            arrays,
            p,
            phase,
            output,
            binding,
            index,
            start,
            {axis: value},
            f"{point_id}_s{index}",
            "profile",
            global_count,
        )
        attempts.append(fit)
    best = _best_ids(attempts)
    chosen = _find_fit(dataset, best["converged"] or best["finite"])
    slice_q, slice_seconds = None, 0.0
    baseline = _find_fit(dataset, dataset["best_converged"] or dataset["best_finite"])
    if baseline:
        theta = unpack_fit(baseline, arrays)["theta"].copy()
        theta[axis] = value
        began = perf_counter()
        iv = core.sabr_vols(
            p["forward"], p["maturity"], p["beta"], theta, arrays[dataset["strikes_key"]]
        )
        slice_q = float(np.sum(((iv - arrays[dataset["quotes_key"]]) / p["noise_scale"]) ** 2))
        slice_seconds = perf_counter() - began
    point = {
        "point_id": point_id,
        "axis": axis,
        "value": float(value),
        "attempts": [a["fit_id"] for a in attempts],
        "best_finite": best["finite"],
        "best_converged": best["converged"],
        "q": chosen["q"] if chosen else None,
        "success": bool(chosen and chosen["success"]),
        "slice_q": slice_q,
        "slice_seconds": slice_seconds,
        "slice_iv_evaluations": len(dataset["indices"]) if baseline else 0,
    }
    dataset["profile_points"].append(point)
    _checkpoint(output, dataset, arrays, binding)
    return point


def _curve_axes(dataset, p, phase):
    if dataset.get("invalid_data") or (phase == "fixture" and not p["fixture"]["profiles"]):
        return []
    representative = dataset["rep"] == p["representative_noisy_rep"]
    if phase == "pilot":
        return (
            [2]
            if dataset["truth_index"] == 0 and dataset["group"] == "full" and representative
            else []
        )
    return [0, 1, 2] if representative else ([2] if dataset["rep"] == -1 else [])


def _curves(dataset, arrays, p, phase, output, binding, global_count):
    if phase == "fixture" and not p["fixture"]["profiles"]:
        return
    axes = _curve_axes(dataset, p, phase)
    baseline = _find_fit(dataset, dataset["best_converged"])
    for axis in axes:
        if any(curve["axis"] == axis for curve in dataset["curves"]):
            continue
        grid = (
            p["fixture"]["profile_grids"][axis] if phase == "fixture" else p["profile_grids"][axis]
        )
        values = list(grid)
        if baseline:
            values.append(float(unpack_fit(baseline, arrays)["theta"][axis]))
        points = [
            _profile_point(dataset, arrays, p, phase, output, binding, axis, value, global_count)
            for value in sorted(set(values))
        ]
        initial = [point["point_id"] for point in points]
        threshold = p["profile_threshold"] if dataset["rep"] >= 0 else p["noiseless_delta_q"]
        q0 = baseline["q"] if baseline else None
        per_bracket = (
            p["fixture"]["refinement_per_bracket"]
            if phase == "fixture"
            else p["profile_refinement_per_bracket"]
        )
        per_curve = (
            p["fixture"]["refinement_per_curve"]
            if phase == "fixture"
            else p["profile_refinement_per_curve"]
        )
        initial_segments = (
            module("analytics").profile_segments(
                points, q0, threshold, [p["bounds"][0][axis], p["bounds"][1][axis]]
            )
            if q0 is not None
            else None
        )
        brackets = []
        extra = 0
        for left, right in initial_segments["crossing_brackets"] if initial_segments else []:
            lo, hi, steps = left, right, []
            for _ in range(per_bracket):
                if extra >= per_curve:
                    break
                middle = (lo + hi) / 2
                point = _profile_point(
                    dataset, arrays, p, phase, output, binding, axis, middle, global_count
                )
                if point["point_id"] not in {v["point_id"] for v in points}:
                    points.append(point)
                    extra += 1
                steps.append(point["point_id"])
                if not point["success"] or point["q"] is None:
                    break
                low_point = next(v for v in points if v["value"] == lo)
                if (low_point["q"] - q0 <= threshold) == (point["q"] - q0 <= threshold):
                    lo = middle
                else:
                    hi = middle
            brackets.append(
                {
                    "initial": [left, right],
                    "final": [lo, hi],
                    "point_ids": steps,
                    "unresolved_interior": True,
                }
            )
        segments = (
            module("analytics").profile_segments(
                points, q0, threshold, [p["bounds"][0][axis], p["bounds"][1][axis]]
            )
            if q0 is not None
            else {"status": "no_converged_baseline", "guaranteed_full_support": False}
        )
        dataset["curves"].append(
            {
                "axis": axis,
                "initial_point_ids": initial,
                "point_ids": [v["point_id"] for v in sorted(points, key=lambda x: x["value"])],
                "refinement_brackets": brackets,
                "segments": segments,
                "threshold": threshold,
            }
        )
        _checkpoint(output, dataset, arrays, binding)
    if phase != "pilot" and dataset["rep"] >= 0:
        dataset["truth_points"] = [
            _profile_point(
                dataset,
                arrays,
                p,
                phase,
                output,
                binding,
                axis,
                p["truths"][dataset["truth_index"]]["theta"][axis],
                global_count,
            )["point_id"]
            for axis in range(3)
        ]


def _costs(datasets):
    fits = [fit for dataset in datasets for fit in dataset["fits"]]
    points = [point for dataset in datasets for point in dataset["profile_points"]]
    generations = [d["master_generation"] for d in datasets if d.get("master_generation")]

    def total(key):
        return sum(f.get(key) or 0 for f in fits)

    return {
        "solver_calls": sum(f.get("solver_called", True) for f in fits),
        "original_attempt_slots": len(fits),
        "unrestricted_calls": sum(
            f["kind"] == "unrestricted" and f.get("solver_called", True) for f in fits
        ),
        "profile_calls": sum(f["kind"] == "profile" and f.get("solver_called", True) for f in fits),
        "exceptions": sum(f.get("exception") is not None for f in fits),
        "evaluation_count_unknown": sum(f.get("residual_calls") is None for f in fits),
        "residual_calls": total("residual_calls"),
        "diagnostic_calls": total("diagnostic_calls"),
        "scalar_iv_evaluations": total("scalar_iv_evaluations"),
        "stability_scalar_iv_evaluations": total("stability_scalar_iv_evaluations"),
        "holdout_iv_evaluations": total("holdout_iv_evaluations"),
        "holdout_black_evaluations": total("holdout_black_evaluations"),
        "slice_iv_evaluations": sum(v["slice_iv_evaluations"] for v in points),
        "holdout_truth_iv_evaluations": sum(
            d.get("holdout_truth_iv_evaluations", 0) for d in datasets
        ),
        "holdout_truth_black_evaluations": sum(
            d.get("holdout_truth_black_evaluations", 0) for d in datasets
        ),
        "holdout_truth_seconds": sum(d.get("holdout_truth_seconds", 0) for d in datasets),
        "master_truth_iv_evaluations": sum(g["truth_iv_evaluations"] for g in generations),
        "noise_draws": sum(g["noise_draws"] for g in generations),
        "master_generation_seconds": sum(g["seconds"] for g in generations),
        "checkpoint_seconds": sum(d.get("checkpoint_seconds", 0.0) for d in datasets),
        "solver_seconds": total("solver_seconds"),
        "diagnostic_seconds": total("diagnostic_seconds"),
        "stability_seconds": total("stability_seconds"),
        "holdout_seconds": total("holdout_seconds"),
        "slice_seconds": sum(v["slice_seconds"] for v in points),
        "cpu_seconds": total("cpu_seconds"),
        "attempt_seconds": total("attempt_seconds"),
        "interpretation": "measured original work; exceptions retain unknown evaluation counts",
    }


def run_study(protocol, phase, output):
    """Run/restart reserved original slots; main is blocked until review/freeze."""
    p = copy.deepcopy(protocol)
    protocol_digest, sources = _binding(p, phase)
    binding = {"protocol_digest": protocol_digest, "source_registry": sources, "phase": phase}
    output = Path(output)
    if not (output / "reference.json").exists() and (output / "reference.npz").exists():
        scratch = output / "reference.json.tmp"
        if not scratch.exists():
            raise FileExistsError(
                "orphan original archive requires intact metadata; refusing replacement"
            )
        pending = json.loads(scratch.read_text(encoding="utf-8"))
        if {key: pending[key] for key in binding} != binding or pending[
            "npz_digest"
        ] != hashlib.sha256((output / "reference.npz").read_bytes()).hexdigest():
            raise ValueError("incomplete final pair binding mismatch")
        scratch.replace(output / "reference.json")
    if (output / "reference.json").exists():
        saved, arrays = load_result(output)
        if {key: saved[key] for key in binding} != binding:
            raise ValueError("completed source/protocol/phase changed")
        check_record(saved, arrays)
        return saved, arrays
    output.mkdir(parents=True, exist_ok=True)
    began, cpu = perf_counter(), process_time()
    arrays, datasets, masters = {}, [], {}
    phase_noise = "main" if phase == "main" else "pilot"
    master_strikes = p["forward"] * np.exp(p["log_moneyness"])
    roster = _roster(p, phase)
    for truth, group, rep, starts in roster:
        dataset_id = f"t{truth}_{group}_r{rep}"
        dataset, restored = _resume_dataset(output, dataset_id, binding)
        arrays.update(restored)
        master_id = f"{phase_noise}_t{truth}_r{rep}"
        master_noise_key, master_quotes_key = f"{master_id}_noise", f"{master_id}_quotes"
        if master_noise_key in restored:
            if master_id not in masters:
                masters[master_id] = (
                    restored[master_noise_key],
                    restored[master_quotes_key],
                    dataset.get("master_generation"),
                )
        newly_generated = master_id not in masters
        if master_id not in masters:
            generation_began = perf_counter()
            truth_iv = core.sabr_vols(
                p["forward"], p["maturity"], p["beta"], p["truths"][truth]["theta"], master_strikes
            )
            noise = (
                np.zeros(len(master_strikes))
                if rep == -1
                else module("protocol").noise_for(p, phase_noise, truth, rep)
            )
            generation = {
                "truth_iv_evaluations": len(master_strikes),
                "noise_draws": len(master_strikes) if rep >= 0 else 0,
                "seconds": perf_counter() - generation_began,
            }
            masters[master_id] = (noise, truth_iv + noise, generation)
        noise, quotes, generation = masters[master_id]
        arrays[master_noise_key], arrays[master_quotes_key] = noise.copy(), quotes.copy()
        if dataset is None:
            indices = p["groups"][group]
            dataset = {
                "dataset_id": dataset_id,
                "truth_index": truth,
                "group": group,
                "rep": rep,
                "indices": indices,
                "master_id": master_id,
                "master_noise_key": master_noise_key,
                "master_quotes_key": master_quotes_key,
                "strikes_key": f"{dataset_id}_strikes",
                "quotes_key": f"{dataset_id}_quotes",
                "fits": [],
                "profile_points": [],
                "curves": [],
                "truth_points": [],
                "best_finite": None,
                "best_converged": None,
                "complete": False,
                "master_generation": generation if newly_generated else None,
            }
            arrays[dataset["strikes_key"]], arrays[dataset["quotes_key"]] = (
                master_strikes[indices],
                quotes[indices],
            )
            if phase != "pilot":
                target_began = perf_counter()
                holdout = p["forward"] * np.exp(p["holdout_log_moneyness"])
                dataset["holdout_truth_iv_key"] = f"{dataset_id}_holdout_truth_iv"
                dataset["holdout_truth_prices_key"] = f"{dataset_id}_holdout_truth_prices"
                target_iv = core.sabr_vols(
                    p["forward"], p["maturity"], p["beta"], p["truths"][truth]["theta"], holdout
                )
                arrays[dataset["holdout_truth_iv_key"]] = target_iv
                arrays[dataset["holdout_truth_prices_key"]] = (
                    module("reference_methods").black_calls(
                        p["forward"], p["maturity"], holdout, target_iv
                    )
                    * p["discount"]
                )
                dataset.update(
                    holdout_truth_iv_evaluations=len(holdout),
                    holdout_truth_black_evaluations=len(holdout),
                    holdout_truth_seconds=perf_counter() - target_began,
                )
        datasets.append(dataset)
        if dataset["complete"]:
            continue

        def count():
            return sum(f.get("solver_called", True) for d in datasets for f in d["fits"])

        if not np.isfinite(quotes).all() or np.any(quotes <= 0):
            dataset.update(
                invalid_data=True,
                invalid_reason="nonpositive_or_nonfinite_master_quote",
                complete=True,
            )
            for start_index in starts:
                fit_id = f"{dataset_id}_u{start_index}"
                skipped = {
                    "fit_id": fit_id,
                    "kind": "unrestricted",
                    "start_index": start_index,
                    "start": np.asarray(p["starts"][start_index]),
                    "success": False,
                    "status": -998,
                    "message": "original quote slot invalid; no optimizer invoked",
                    "q": None,
                    "fixed": {},
                    "invalid_data": True,
                    "solver_called": False,
                    "residual_calls": 0,
                    "diagnostic_calls": 0,
                    "scalar_iv_evaluations": 0,
                    "seconds": 0.0,
                    "attempt_seconds": 0.0,
                    "cpu_seconds": 0.0,
                }
                dataset["fits"].append(_pack_fit(skipped, arrays, fit_id))
        else:
            for start_index in starts:
                _fit_once(
                    dataset,
                    arrays,
                    p,
                    phase,
                    output,
                    binding,
                    start_index,
                    p["starts"][start_index],
                    None,
                    f"{dataset_id}_u{start_index}",
                    "unrestricted",
                    count,
                )
            best = _best_ids([f for f in dataset["fits"] if f["kind"] == "unrestricted"])
            dataset["best_finite"], dataset["best_converged"] = best["finite"], best["converged"]
            _curves(dataset, arrays, p, phase, output, binding, count)
            dataset["complete"] = True
        _checkpoint(output, dataset, arrays, binding)
        print(
            f"{phase}: {sum(d['complete'] for d in datasets)}/{len(roster)} datasets; {count() if 'count' in locals() else 0} fits",
            flush=True,
        )
    record = {
        "schema": "RB-F06-study-v1",
        **binding,
        "protocol": p,
        "datasets": datasets,
        "complete": True,
        "teaching_acceptance": False,
        "costs": _costs(datasets),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "blas_threads": {
                name: os.environ.get(name)
                for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
            "invocation_seconds": perf_counter() - began,
            "invocation_cpu_seconds": process_time() - cpu,
            "cost_scope": "fit work sums survive resume; invocation includes checkpoint/I/O and setup for this invocation",
            "serialization_receipt": "serialization_cost.json",
            "serialization_pending": True,
        },
        "numerical_limits": {
            "rtol": 2e-6,
            "atol": 1e-8,
            "jacobian": "step-dependent Hagan approximation; tiny-positive nu needs uncertainty qualification",
        },
    }
    if hasattr(module("analytics"), "summarize"):
        record["summary"] = module("analytics").summarize(record, arrays)
    save_began = perf_counter()
    _save_pair(output, "reference", record, arrays)
    saved, arrays = load_result(output)
    receipt = {
        "schema": "RB-F06-serialization-cost-v1",
        "reference_record_digest": _digest(saved),
        "protocol_digest": saved["protocol_digest"],
        "seconds": perf_counter() - save_began,
        "pending": False,
        "scope": "final JSON/NPZ compression, transport hashing, writes and first load validation; receipt write excluded",
    }
    with (output / "serialization_cost.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, sort_keys=True, allow_nan=False)
    return saved, arrays


def _nested_equal(actual, expected, name):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"derived schema mismatch: {name}")
        for key in expected:
            _nested_equal(actual[key], expected[key], f"{name}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"derived roster mismatch: {name}")
        for index, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _nested_equal(a, b, f"{name}[{index}]")
    elif expected is None or isinstance(expected, (str, bool, int)):
        if actual != expected:
            raise ValueError(f"derived metadata mismatch: {name}")
    else:
        _equal(actual, expected, name)


def _check_fit(fit, dataset, arrays, p, phase):
    f = unpack_fit(fit, arrays)
    if f.get("invalid_data"):
        if (
            not dataset.get("invalid_data")
            or f["success"]
            or f["q"] is not None
            or f["solver_called"]
            or f["status"] != -998
        ):
            raise ValueError("invalid data slot promoted")
        return
    if f.get("exception"):
        if f["success"] or f["q"] is not None or f["status"] != -999:
            raise ValueError("exception was promoted to successful fit")
        return
    strikes, quotes = arrays[dataset["strikes_key"]], arrays[dataset["quotes_key"]]
    theta = f["theta"]
    if theta.shape != (3,) or np.any(theta < core.LOWER) or np.any(theta > core.UPPER):
        raise ValueError("fitted theta outside frozen box")
    for axis, value in f["fixed"].items():
        _equal(theta[axis], value, "fixed coordinate", rtol=0, atol=1e-13)
    iv = core.sabr_vols(p["forward"], p["maturity"], p["beta"], theta, strikes)
    _equal(f["iv"], iv, "IV")
    _equal(f["raw_residual"], iv - quotes, "raw residual")
    _equal(f["scaled_residual"], (iv - quotes) / p["noise_scale"], "scaled residual")
    _equal(f["q"], np.sum(((iv - quotes) / p["noise_scale"]) ** 2), "Q", rtol=1e-8, atol=1e-8)
    j = core.scaled_jacobian(
        p["forward"], p["maturity"], p["beta"], theta, strikes, f["jacobian_step"], p["noise_scale"]
    )
    _equal(f["scaled_jacobian"], j, "scaled J")
    _equal(f["theta_jacobian"], j * p["noise_scale"] / core.SCALE, "theta J")
    _equal(
        f["raw_jacobian"],
        j * p["noise_scale"] / core.SCALE / [p["forward"] ** (1 - p["beta"]), 1, 1],
        "raw J",
    )
    info = core.jacobian_diagnostics(j, p["rank_rtol"])
    _equal(f["singular_values"], info["singular_values"], "SVD values")
    if f["rank"] != info["rank"] or (f["condition"] is None) != (info["condition"] is None):
        raise ValueError("numerical rank/condition mismatch")
    if f["condition"] is not None:
        _equal(f["condition"], info["condition"], "condition")
    vectors = f["right_vectors"]
    _equal(vectors @ vectors.T, np.eye(3), "orthogonal right vectors")
    _equal(
        vectors.T @ np.diag(f["singular_values"] ** 2) @ vectors,
        j.T @ j,
        "SVD directions",
        atol=1e-5,
    )
    _equal(
        f["boundary_lower"],
        (theta - core.LOWER) / core.SCALE <= p["boundary_distance_u"],
        "lower boundary",
        rtol=0,
        atol=0,
    )
    _equal(
        f["boundary_upper"],
        (core.UPPER - theta) / core.SCALE <= p["boundary_distance_u"],
        "upper boundary",
        rtol=0,
        atol=0,
    )
    _equal(
        f["boundary_flags"],
        f["boundary_lower"] | f["boundary_upper"],
        "boundary flags",
        rtol=0,
        atol=0,
    )
    if (
        f["success"] != (f["status"] > 0)
        or f["nfev"] < 1
        or f["residual_calls"] < f["nfev"]
        or f["diagnostic_calls"] < 1
    ):
        raise ValueError("solver status/count mismatch")
    if f["scalar_iv_evaluations"] != len(strikes) * (f["residual_calls"] + f["diagnostic_calls"]):
        raise ValueError("price call count mismatch")
    for key in (
        "seconds",
        "solver_seconds",
        "diagnostic_seconds",
        "attempt_seconds",
        "cpu_seconds",
    ):
        if not np.isfinite(f[key]) or f[key] < 0:
            raise ValueError("invalid recorded timing")
    _equal(
        f["seconds"], f["solver_seconds"] + f["diagnostic_seconds"], "time components", atol=1e-10
    )
    if phase == "pilot":
        if any(key.startswith("holdout") for key in f) or "numerical_stability" in f:
            raise ValueError("pilot leaked held-out evaluation")
    else:
        holdout = p["forward"] * np.exp(p["holdout_log_moneyness"])
        h_iv = core.sabr_vols(p["forward"], p["maturity"], p["beta"], theta, holdout)
        _equal(f["holdout_iv"], h_iv, "holdout IV")
        _equal(
            f["holdout_prices"],
            module("reference_methods").black_calls(p["forward"], p["maturity"], holdout, h_iv)
            * p["discount"],
            "holdout Black",
        )
        if f["holdout_iv_evaluations"] != len(holdout) or f["holdout_black_evaluations"] != len(
            holdout
        ):
            raise ValueError("holdout call accounting mismatch")
        if f["kind"] == "unrestricted":
            js = arrays[f["stability_jacobians_key"]]
            expected_calls = 0
            for index, h in enumerate(p["jacobian_steps_u"]):
                expected = core.scaled_jacobian(
                    p["forward"], p["maturity"], p["beta"], theta, strikes, h, p["noise_scale"]
                )
                _equal(js[index], expected, "multi-step Jacobian")
                if h != f["jacobian_step"]:
                    expected_calls += _jacobian_calls(theta, h)
            if (
                f["stability_iv_calls"] != expected_calls
                or f["stability_scalar_iv_evaluations"] != len(strikes) * expected_calls
            ):
                raise ValueError("stability call accounting mismatch")
            _nested_equal(
                f["numerical_stability"],
                module("analytics").jacobian_stability(
                    js,
                    p["rank_rtol"],
                    p["jacobian_global_rtol"],
                    p["jacobian_smallest_sv_relative_limit"],
                ),
                "stability",
            )


def _check_profiles(dataset, arrays, p, phase):
    fits = {f["fit_id"]: f for f in dataset["fits"]}
    points = {v["point_id"]: v for v in dataset["profile_points"]}
    if len(points) != len(dataset["profile_points"]) or len(
        {(v["axis"], v["value"]) for v in points.values()}
    ) != len(points):
        raise ValueError("duplicate profile point recomputed")
    baseline = fits.get(dataset["best_converged"] or dataset["best_finite"])
    expected_axes = _curve_axes(dataset, p, phase)
    if [curve["axis"] for curve in dataset["curves"]] != expected_axes:
        raise ValueError("original curve roster changed")
    truth_required = (
        phase != "pilot"
        and dataset["rep"] >= 0
        and not dataset.get("invalid_data")
        and not (phase == "fixture" and not p["fixture"]["profiles"])
    )
    if len(dataset["truth_points"]) != (3 if truth_required else 0):
        raise ValueError("original truth-point roster changed")
    for point in points.values():
        attempts = [fits[fid] for fid in point["attempts"]]
        if len(attempts) != 4 or len(set(point["attempts"])) != 4:
            raise ValueError("profile nuisance roster changed")
        best = _best_ids(attempts)
        if best != {"finite": point["best_finite"], "converged": point["best_converged"]}:
            raise ValueError("profile best selection mismatch")
        selected = fits.get(best["converged"] or best["finite"])
        if point["q"] != (selected["q"] if selected else None) or point["success"] != bool(
            selected and selected["success"]
        ):
            raise ValueError("profile result mismatch")
        nuisance = [i for i in range(3) if i != point["axis"]]
        for index, pair in enumerate(
            itertools.product(*(p["profile_starts"][i] for i in nuisance))
        ):
            fit = unpack_fit(attempts[index], arrays)
            start = np.zeros(3)
            start[point["axis"]], start[nuisance] = point["value"], pair
            _equal(fit["start"], start, "profile start roster", rtol=0, atol=1e-13)
            if fit["fixed"] != {point["axis"]: point["value"]}:
                raise ValueError("profile fixed condition mismatch")
        if baseline:
            theta = unpack_fit(baseline, arrays)["theta"].copy()
            theta[point["axis"]] = point["value"]
            iv = core.sabr_vols(
                p["forward"], p["maturity"], p["beta"], theta, arrays[dataset["strikes_key"]]
            )
            _equal(
                point["slice_q"],
                np.sum(((iv - arrays[dataset["quotes_key"]]) / p["noise_scale"]) ** 2),
                "feasible slice Q",
            )
    for curve in dataset["curves"]:
        observed = [points[pid] for pid in curve["point_ids"]]
        baseline_fit = fits.get(dataset["best_converged"])
        grid = (
            p["fixture"]["profile_grids"][curve["axis"]]
            if phase == "fixture"
            else p["profile_grids"][curve["axis"]]
        )
        initial_values = list(grid)
        if baseline_fit:
            initial_values.append(float(unpack_fit(baseline_fit, arrays)["theta"][curve["axis"]]))
        actual_values = [points[pid]["value"] for pid in curve["initial_point_ids"]]
        _equal(actual_values, sorted(set(initial_values)), "initial curve grid", rtol=0, atol=1e-13)
        if baseline_fit:
            expected = module("analytics").profile_segments(
                observed,
                baseline_fit["q"],
                curve["threshold"],
                [p["bounds"][0][curve["axis"]], p["bounds"][1][curve["axis"]]],
            )
            _nested_equal(curve["segments"], expected, "profile segments")
            threshold = p["profile_threshold"] if dataset["rep"] >= 0 else p["noiseless_delta_q"]
            _equal(curve["threshold"], threshold, "curve threshold", rtol=0, atol=1e-13)
            initial = module("analytics").profile_segments(
                [points[pid] for pid in curve["initial_point_ids"]],
                baseline_fit["q"],
                threshold,
                [p["bounds"][0][curve["axis"]], p["bounds"][1][curve["axis"]]],
            )
            _nested_equal(
                [b["initial"] for b in curve["refinement_brackets"]],
                initial["crossing_brackets"],
                "initial crossing brackets",
            )
            refined_ids = set(curve["initial_point_ids"])
            per_bracket = p.get("fixture", {}).get(
                "refinement_per_bracket", p["profile_refinement_per_bracket"]
            )
            for bracket in curve["refinement_brackets"]:
                if not bracket["unresolved_interior"] or len(bracket["point_ids"]) > per_bracket:
                    raise ValueError("refinement bracket falsely resolved or over budget")
                lo, hi = bracket["initial"]
                for pid in bracket["point_ids"]:
                    point = points[pid]
                    _equal(point["value"], (lo + hi) / 2, "refinement midpoint", rtol=0, atol=1e-13)
                    refined_ids.add(pid)
                    if not point["success"] or point["q"] is None:
                        break
                    low = next(v for v in observed if v["value"] == lo)
                    if (low["q"] - baseline_fit["q"] <= threshold) == (
                        point["q"] - baseline_fit["q"] <= threshold
                    ):
                        lo = point["value"]
                    else:
                        hi = point["value"]
                _equal(
                    bracket["final"], [lo, hi], "refinement bracket endpoints", rtol=0, atol=1e-13
                )
            if set(curve["point_ids"]) != refined_ids:
                raise ValueError("refinement point ledger mismatch")
        extra = len(set(curve["point_ids"]) - set(curve["initial_point_ids"]))
        limit = p.get("fixture", {}).get("refinement_per_curve", p["profile_refinement_per_curve"])
        if extra > limit:
            raise ValueError("profile refinement budget exceeded")
    for axis, pid in enumerate(dataset["truth_points"]):
        point = points[pid]
        if (
            point["axis"] != axis
            or point["value"] != p["truths"][dataset["truth_index"]]["theta"][axis]
        ):
            raise ValueError("truth-point ledger changed")


def _fresh(record, arrays):
    p, phase = record["protocol"], record["phase"]
    results, noises = [], set()
    cases = p["fresh_cases"] if phase != "fixture" else [[0, "full", 0], [0, "sparse", 0]]
    for dataset in record["datasets"]:
        if dataset["rep"] >= 0 and dataset["master_id"] not in noises:
            expected = module("protocol").noise_for(
                p, "main" if phase == "main" else "pilot", dataset["truth_index"], dataset["rep"]
            )
            _equal(
                arrays[dataset["master_noise_key"]],
                expected,
                "fresh reserved noise",
                rtol=0,
                atol=1e-15,
            )
            noises.add(dataset["master_id"])
        if [dataset["truth_index"], dataset["group"], dataset["rep"]] not in cases:
            continue
        selected = [
            f
            for f in dataset["fits"]
            if f["kind"] == "unrestricted" and f["start_index"] in p["fresh_starts"]
        ]
        for point in dataset["profile_points"]:
            if (
                point["axis"] == 2
                and point["value"] == p["truths"][dataset["truth_index"]]["theta"][2]
            ):
                selected.extend(_find_fit(dataset, fid) for fid in point["attempts"][:1])
                break
        for saved in selected:
            if saved.get("exception"):
                continue
            original = unpack_fit(saved, arrays)
            replay = core.fit_smile(
                p["forward"],
                p["maturity"],
                p["beta"],
                arrays[dataset["strikes_key"]],
                arrays[dataset["quotes_key"]],
                original["start"],
                fixed=original["fixed"],
                max_nfev=p["fit_max_nfev"]
                if saved["kind"] == "unrestricted"
                else p["profile_max_nfev"],
                noise_scale=p["noise_scale"],
            )
            _equal(replay["q"], original["q"], "fresh fit Q", atol=1e-6)
            _equal(replay["iv"], original["iv"], "fresh fit IV", atol=1e-8)
            if replay["success"] != original["success"]:
                raise ValueError("fresh solver outcome changed")
            results.append(saved["fit_id"])
    return {
        "fit_ids": results,
        "noise_vectors": len(noises),
        "scope": "selected original fits; fresh work is not pooled with original evidence",
    }


def check_record(record, arrays, fresh=False):
    """Reprice saved numerical evidence; RNG/optimization are exclusive to fresh."""
    p, phase = record["protocol"], record["phase"]
    protocol_digest, sources = _binding(p, phase)
    if record["protocol_digest"] != protocol_digest or record["source_registry"] != sources:
        raise ValueError("saved source/protocol binding changed")
    if (
        record["schema"] != "RB-F06-study-v1"
        or not record["complete"]
        or record["teaching_acceptance"]
    ):
        raise ValueError("unfinished or falsely promoted study")
    expected = _roster(p, phase)
    identities = [(d["truth_index"], d["group"], d["rep"]) for d in record["datasets"]]
    if identities != [(t, g, r) for t, g, r, _ in expected]:
        raise ValueError("original dataset roster changed")
    fit_ids, master_noise = set(), {}
    for dataset, (_, _, _, starts) in zip(record["datasets"], expected, strict=True):
        truth, group, rep = dataset["truth_index"], dataset["group"], dataset["rep"]
        if (
            dataset["dataset_id"] != f"t{truth}_{group}_r{rep}"
            or dataset["indices"] != p["groups"][group]
            or not dataset["complete"]
        ):
            raise ValueError("dataset slot identity mismatch")
        strikes = p["forward"] * np.exp(p["log_moneyness"])
        truth_iv = core.sabr_vols(
            p["forward"], p["maturity"], p["beta"], p["truths"][truth]["theta"], strikes
        )
        noise = arrays[dataset["master_noise_key"]]
        if noise.shape != truth_iv.shape:
            raise ValueError("master noise shape changed")
        saved_master_quotes = arrays[dataset["master_quotes_key"]]
        actual_invalid = not np.isfinite(saved_master_quotes).all() or bool(
            np.any(saved_master_quotes <= 0)
        )
        if dataset.get("invalid_data", False) != actual_invalid:
            raise ValueError("saved invalid_data disagrees with actual master quotes")
        compare_quotes = _invalid_equal if actual_invalid else _equal
        if rep == -1:
            _equal(noise, np.zeros_like(noise), "noiseless vector", rtol=0, atol=1e-14)
        if dataset["master_id"] in master_noise:
            compare_quotes(
                noise,
                master_noise[dataset["master_id"]],
                "shared master noise",
                rtol=1e-12,
                atol=1e-14,
            )
        master_noise[dataset["master_id"]] = noise
        compare_quotes(saved_master_quotes, truth_iv + noise, "master quotes")
        _equal(arrays[dataset["strikes_key"]], strikes[dataset["indices"]], "group strikes")
        compare_quotes(
            arrays[dataset["quotes_key"]],
            (truth_iv + noise)[dataset["indices"]],
            "nested group quotes",
        )
        if phase == "pilot":
            if any(key.startswith("holdout") for key in dataset):
                raise ValueError("pilot accessed holdout truth")
        else:
            holdout = p["forward"] * np.exp(p["holdout_log_moneyness"])
            h_iv = core.sabr_vols(
                p["forward"], p["maturity"], p["beta"], p["truths"][truth]["theta"], holdout
            )
            _equal(arrays[dataset["holdout_truth_iv_key"]], h_iv, "holdout truth IV")
            _equal(
                arrays[dataset["holdout_truth_prices_key"]],
                module("reference_methods").black_calls(p["forward"], p["maturity"], holdout, h_iv)
                * p["discount"],
                "holdout truth price",
            )
        unrestricted = [f for f in dataset["fits"] if f["kind"] == "unrestricted"]
        if [f["start_index"] for f in unrestricted] != starts:
            raise ValueError("original start roster changed")
        best = _best_ids(unrestricted)
        if best != {"finite": dataset["best_finite"], "converged": dataset["best_converged"]}:
            raise ValueError("unrestricted selection mismatch")
        for fit in dataset["fits"]:
            if fit["fit_id"] in fit_ids:
                raise ValueError("original attempt duplicated")
            fit_ids.add(fit["fit_id"])
            if fit["kind"] == "unrestricted":
                _equal(
                    unpack_fit(fit, arrays)["start"],
                    p["starts"][fit["start_index"]],
                    "unrestricted start roster",
                    rtol=0,
                    atol=1e-13,
                )
            _check_fit(fit, dataset, arrays, p, phase)
        _check_profiles(dataset, arrays, p, phase)
    _nested_equal(record["costs"], _costs(record["datasets"]), "cost account")
    if record["costs"]["solver_calls"] > p["solver_call_cap"]:
        raise ValueError("solver budget exceeded")
    if "summary" in record:
        _nested_equal(record["summary"], module("analytics").summarize(record, arrays), "summary")
    result = {
        "passed": True,
        "dataset_slots": len(expected),
        "original_attempts": len(fit_ids),
        "fresh": bool(fresh),
        "scope": "saved Hagan-map/Black revaluation; not exact SABR validation",
    }
    if fresh:
        result["fresh_replay"] = _fresh(record, arrays)
    return result


def main(argv=None):
    """CLI for reserved study phases or a saved-only/fresh numerical check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["pilot", "main", "fixture"])
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        if args.phase or args.protocol or args.output:
            parser.error("--check cannot be combined with generation options")
        record, arrays = load_result(args.check)
        began = perf_counter()
        result = check_record(record, arrays, fresh=args.fresh)
        if args.fresh:
            receipt = {
                "schema": "RB-F06-fresh-check-v1",
                "reference_record_digest": _digest(record),
                "protocol_digest": record["protocol_digest"],
                "seconds": perf_counter() - began,
                "checks": result,
            }
            suffix = 1
            path = args.check / "fresh_check.json"
            while path.exists():
                suffix += 1
                path = args.check / f"fresh_check_{suffix:03d}.json"
            with path.open("x", encoding="utf-8") as handle:
                json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, allow_nan=False)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.fresh or not args.phase or not args.output:
        parser.error("generation requires --phase and --output; --fresh requires --check")
    p = (
        module("protocol").load_protocol(args.protocol)
        if args.protocol
        else (fixture_protocol() if args.phase == "fixture" else module("protocol").load_protocol())
    )
    record, _ = run_study(p, args.phase, args.output)
    print(
        f"{args.phase}: complete; {len(record['datasets'])} datasets, {record['costs']['solver_calls']} solver calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
