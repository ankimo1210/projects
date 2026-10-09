"""Discrete-barrier research runner; checking saved artifacts never fits a NN.

Main fitting requires the frozen protocol and a independently checked full
pilot. Diagnostic streams, train scenarios/paths and validation scenarios/paths
are separate. Only noisy train labels determine normalization or optimization.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
_MODULES = {}
_EXPORT_FIELDS = (
    "kind",
    "dml",
    "feature_mean",
    "feature_std",
    "price_mean",
    "price_scale",
    "delta_scale",
    "layer0_weight",
    "layer0_bias",
    "layer1_weight",
    "layer1_bias",
    "layer2_weight",
    "layer2_bias",
)
_METHODS = (
    "raw_price",
    "raw_delta",
    "conditioned_price",
    "conditioned_delta",
    "naive_pw",
    "last_conditional_pw",
    "oss_price",
    "oss_delta",
)
_FLAG_NAMES = (
    "probability_underflow",
    "quantile_underflow",
    "weight_underflow",
    "numerical_failure",
)


def _module(name, path=None):
    if name not in _MODULES:
        path = path or HERE / (name + ".py")
        spec = importlib.util.spec_from_file_location("rbf05_runner_" + name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _MODULES[name] = module
    return _MODULES[name]


def _learner():
    # Lazy: a shared venv may have imported another checkout's package already.
    return _module("learner", ROOT / "deep_hedge_price/src/deep_hedge_price/_barrier_dml.py")


def _initialize_framework():
    """Measure shared CPU/Adam lazy initialization, without fitting a network.

    The zero scalar has zero gradient. CPU RNG/default-device context is
    restored, and the measured expense is separate from every fit's cap.
    """
    start = perf_counter()
    torch = _learner().torch
    with torch.device("cpu"), torch.random.fork_rng(devices=[]):
        parameter = torch.nn.Parameter(torch.zeros((), dtype=torch.float64, device="cpu"))
        optimizer = torch.optim.Adam([parameter], lr=0.003)
        parameter.square().backward()
        optimizer.step()
    return perf_counter() - start


def _teacher():
    return _module("teacher", HERE.parents[2] / "hullkit/src/hullkit/_discrete_barrier_teachers.py")


def protocol():
    return json.loads((HERE / "protocol.json").read_text())


def _check_protocol(p):
    canonical = protocol()
    for key in (
        "schema",
        "study",
        "contract",
        "domain",
        "splits",
        "reference",
        "pilot",
        "diagnostic",
        "learning",
        "interpolation",
        "timing",
        "quality",
    ):
        if p.get(key) != canonical.get(key):
            raise ValueError(f"fixed protocol differs: {key}")


def _effective(p, smoke):
    return {
        "train": 16 if smoke else p["splits"]["train"],
        "validation": 8 if smoke else p["splits"]["validation"],
        "test_spots": 4 if smoke else p["splits"]["test_spots"],
        "test_times": [0.25, 1.0, 2.0] if smoke else p["splits"]["test_times"],
        "paths": 256 if smoke else p["splits"]["paths_per_scenario"],
        "updates": 2 if smoke else p["learning"]["updates"],
        "grid_spots": 5 if smoke else p["interpolation"]["spots"],
        "grid_times": 4 if smoke else p["interpolation"]["times"],
        "diagnostic_paths": 256 if smoke else p["diagnostic"]["paths"],
    }


def _contract(p):
    return {key: p["contract"][key] for key in ("strike", "barrier", "rate", "volatility")}


def _row_seeds(stream, rows):
    return np.asarray(
        [child.generate_state(1)[0] for child in np.random.SeedSequence(stream).spawn(rows)],
        dtype=np.uint64,
    )


def _scenarios(p, split, rows):
    rng = np.random.default_rng(p["splits"][split + "_scenarios"])
    s = rng.uniform(*p["domain"]["spot"], rows)
    t = np.exp(rng.uniform(*np.log(p["domain"]["maturity"]), rows))
    return np.column_stack((s, t))


def _test_inputs(p, e):
    return np.asarray(
        [
            (s, t)
            for t in e["test_times"]
            for s in np.linspace(*p["domain"]["spot"], e["test_spots"])
        ]
    )


def oracle(x, order=128, tail_sigma=12, verify=False):
    """Markov reference with same-call T setup sharing; failed checks stay NaN.

    Verification compares independent quadrature refinements, including the
    separate truncation bounds. It does not replace a failed numerical result
    with a fabricated zero or an unchecked larger-order value.
    """
    values, _, _ = _oracle_details(x, order=order, tail_sigma=tail_sigma, verify=verify)
    return values


def _oracle_details(x, *, order=128, tail_sigma=12, verify=True):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError("physical [spot,maturity] rows required")
    teacher, p = _teacher(), protocol()
    values, errors, checked = (
        np.full((len(x), 2), np.nan),
        np.full((len(x), 2), np.nan),
        np.zeros(len(x), dtype=bool),
    )
    valid = np.isfinite(x).all(axis=1) & np.all(x > 0, axis=1)
    if np.any(valid):
        result = teacher.markov_batch(
            x[valid],
            monitoring=p["contract"]["positive_monitoring"],
            order=order,
            tail_sigma=tail_sigma,
            check_order=max(order * 2, p["reference"]["check_order"]) if verify else None,
            **_contract(p),
        )
        value = np.column_stack((result["price"].ravel(), result["delta"].ravel()))
        bound = result["tail_bounds"][:, 1:]
        if verify:
            refinement = result["refinement"]
            error = np.column_stack(
                (refinement["price"].ravel(), refinement["delta"].ravel())
            ) + np.maximum(bound, refinement["tail_bounds"][:, 1:])
            good = (
                np.isfinite(value).all(axis=1)
                & (error[:, 0] <= p["reference"]["quadrature_price_tolerance"])
                & (error[:, 1] <= p["reference"]["quadrature_delta_tolerance"])
            )
            values[valid] = np.where(good[:, None], value, np.nan)
            errors[valid], checked[valid] = error, good
        else:
            values[valid], errors[valid] = value, bound
        # The t0 contract rule is exact; its ordinary Delta remains undefined
        # at contact even when a quadrature refinement cannot compare NaNs.
        knock = valid & (x[:, 0] >= p["contract"]["barrier"])
        values[knock], errors[knock] = 0, 0
        contact = knock & (x[:, 0] == p["contract"]["barrier"])
        values[contact, 1] = np.nan
        checked[knock] = ~contact[knock]
    return values, errors, checked


def mc_labels(x, stream, paths):
    """Noisy last-step conditional price + first-transition LRM, per-row seed.

    This function never substitutes analytic/reference labels. Its counts are
    original simulated survival and positive terminal payoff, respectively.
    """
    x = np.asarray(x, dtype=float)
    if (
        x.ndim != 2
        or x.shape[1] != 2
        or not np.isfinite(x).all()
        or np.any(x <= 0)
        or int(paths) != paths
        or paths < 2
    ):
        raise ValueError("finite positive physical inputs and at least two paths required")
    p, teacher = protocol(), _teacher()
    seeds, labels, se = _row_seeds(stream, len(x)), np.empty((len(x), 2)), np.empty((len(x), 2))
    survival, positive = np.empty(len(x), dtype=int), np.empty(len(x), dtype=int)
    for i, ((s, t), seed) in enumerate(zip(x, seeds, strict=True)):
        z = np.random.default_rng(seed).standard_normal(
            (int(paths), p["contract"]["positive_monitoring"])
        )
        sample = teacher.samples(s, t, z, **_contract(p))
        for j, key in enumerate(("last_conditional", "last_conditional_lrm")):
            summary = teacher.summarize(sample[key])
            labels[i, j], se[i, j] = summary["mean"], summary["se"]
        survival[i], positive[i] = (
            np.count_nonzero(sample["survival"]),
            np.count_nonzero(sample["payoff"] > 0),
        )
    return labels, se, seeds, survival, positive


def _diagnostic_inputs(p, smoke):
    inputs = [(s, t, 12) for t in p["pilot"]["times"] for s in p["pilot"]["spots"]]
    inputs += [(s, 1.0, m) for s in (100.0, 119.0) for m in p["diagnostic"]["monitoring"]]
    if smoke:
        inputs = [(100.0, 0.25, 12), (119.0, 0.25, 12), (100.0, 1.0, 1), (100.0, 1.0, 12)]
    return np.asarray(inputs)


def _diagnostic_seeds(p, rows):
    seed_streams = np.random.SeedSequence(p["diagnostic"]["seed"]).spawn(2)
    return np.column_stack(
        [
            np.asarray([c.generate_state(1)[0] for c in s.spawn(rows)], dtype=np.uint64)
            for s in seed_streams
        ]
    )


def _diagnostic(p, smoke):
    """Compact independent diagnostic; fresh checking regenerates actual paths."""
    teacher, inputs = _teacher(), _diagnostic_inputs(p, smoke)
    count = 256 if smoke else p["diagnostic"]["paths"]
    seeds = _diagnostic_seeds(p, len(inputs))
    stats, counts, flags = (
        np.full((len(inputs), 8, 2), np.nan),
        np.empty((len(inputs), 5), dtype=int),
        np.empty((len(inputs), 4), dtype=int),
    )
    reference, error = np.empty((len(inputs), 2)), np.empty((len(inputs), 2))
    for i, ((s, t, m), (normal_seed, uniform_seed)) in enumerate(zip(inputs, seeds, strict=True)):
        z = np.random.default_rng(normal_seed).standard_normal((count, int(m)))
        u = np.maximum(
            np.random.default_rng(uniform_seed).uniform(size=z.shape), np.nextafter(0.0, 1.0)
        )
        raw, oss = (
            teacher.samples(s, t, z, **_contract(p)),
            teacher.one_step_survival(s, t, u, **_contract(p)),
        )
        if m == 1:
            exact = teacher.one_step(s, t, **_contract(p))
            conditional = [np.full(count, exact[k]) for k in ("price", "delta", "delta")]
        else:
            conditional = [
                raw[k] for k in ("last_conditional", "last_conditional_lrm", "last_conditional_pw")
            ]
        samples = [
            raw["payoff"],
            raw["lrm"],
            conditional[0],
            conditional[1],
            raw["naive_pw"],
            conditional[2],
            oss["payoff"],
            oss["delta"],
        ]
        for j, sample in enumerate(samples):
            if m == 1 and j in (2, 3, 5):
                stats[i, j, 0] = sample[0]  # analytic, no MC standard error
            elif np.isfinite(sample).all():
                summary = teacher.summarize(sample)
                stats[i, j] = summary["mean"], summary["se"]
        counts[i] = [
            np.count_nonzero(raw["survival"]),
            np.count_nonzero(raw["payoff"] > 0),
            np.count_nonzero(oss["valid"]),
            oss["positive_payoff_count"],
            np.count_nonzero(~oss["valid"]),
        ]
        flags[i] = [np.count_nonzero(oss[k]) for k in _FLAG_NAMES]
        low = teacher.markov_reference(
            s,
            t,
            monitoring=int(m),
            order=p["reference"]["order"],
            tail_sigma=p["reference"]["tail_sigma"],
            **_contract(p),
        )
        high = teacher.markov_reference(
            s,
            t,
            monitoring=int(m),
            order=p["reference"]["check_order"],
            tail_sigma=p["reference"]["tail_sigma"],
            **_contract(p),
        )
        reference[i] = low["price"], low["delta"]
        error[i] = np.abs(reference[i] - [high["price"], high["delta"]]) + np.asarray(
            [low["tail_price_bound"], low["tail_delta_bound"]]
        )
    return {
        "diagnostic.inputs": inputs,
        "diagnostic.path_seed": seeds,
        "diagnostic.statistics": stats,
        "diagnostic.counts": counts,
        "diagnostic.flags": flags,
        "diagnostic.reference": reference,
        "diagnostic.reference_error": error,
    }


def _diagnostic_summary(arrays, p):
    cases = []
    for i, (s, t, m) in enumerate(arrays["diagnostic.inputs"]):
        methods = {}
        for j, method in enumerate(_METHODS):
            mean, se = arrays["diagnostic.statistics"][i, j]
            analytic = m == 1 and j in (2, 3, 5)
            column = 0 if j in (0, 2, 6) else 1
            supported = np.isfinite(mean) and (analytic or np.isfinite(se))
            difference = (
                abs(mean - arrays["diagnostic.reference"][i, column]) if supported else None
            )
            tolerance = (
                6 * se + arrays["diagnostic.reference_error"][i, column]
                if supported and not analytic
                else None
            )
            methods[method] = {
                "mean": float(mean) if np.isfinite(mean) else None,
                "se": float(se) if np.isfinite(se) else None,
                "status": "analytic_reference"
                if analytic
                else ("biased_control" if j in (4, 5) else "unbiased_teacher"),
                "sampling_status": "not_MC"
                if analytic
                else (
                    "unsupported_paths"
                    if not supported
                    else ("zero_sample_variance" if se == 0 else "iid_samples")
                ),
                "abs_reference_difference": float(difference) if difference is not None else None,
                "six_se_plus_oracle_error": float(tolerance) if tolerance is not None else None,
                "reference_comparison": bool(difference <= tolerance)
                if tolerance is not None
                else None,
            }
        counts = arrays["diagnostic.counts"][i]
        cases.append(
            {
                "spot": float(s),
                "maturity": float(t),
                "monitoring": int(m),
                "methods": methods,
                "survival_count": int(counts[0]),
                "positive_payoff_count": int(counts[1]),
                "oss_valid_count": int(counts[2]),
                "oss_positive_payoff_count": int(counts[3]),
                "oss_failure_count": int(counts[4]),
                "oss_flags": dict(
                    zip(_FLAG_NAMES, map(int, arrays["diagnostic.flags"][i]), strict=True)
                ),
                "first_score_second_moment": float(
                    m / (s**2 * p["contract"]["volatility"] ** 2 * t)
                ),
            }
        )
    return {
        "seed": p["diagnostic"]["seed"],
        "cases": cases,
        "methods": list(_METHODS),
        "fresh_regeneration_required": True,
        "independence": "separate diagnostic normal/uniform row streams; no diagnostic labels used for fitting",
        "standard_error": "IID sample variance ddof=1; analytic m1 entries have no MC SE",
    }


def _check_diagnostic(arrays, p, smoke):
    inputs, paths = _diagnostic_inputs(p, smoke), 256 if smoke else p["diagnostic"]["paths"]
    _close(arrays["diagnostic.inputs"], inputs, "fixed diagnostic cases")
    _close(
        arrays["diagnostic.path_seed"],
        _diagnostic_seeds(p, len(inputs)),
        "independent diagnostic row path seeds",
    )
    stats, counts, flags = (
        arrays["diagnostic.statistics"],
        arrays["diagnostic.counts"],
        arrays["diagnostic.flags"],
    )
    if (
        stats.shape != (len(inputs), 8, 2)
        or counts.shape != (len(inputs), 5)
        or flags.shape != (len(inputs), 4)
    ):
        raise ValueError("diagnostic shapes differ")
    if (
        np.any((counts < 0) | (counts > paths))
        or np.any(counts != np.floor(counts))
        or np.any((flags < 0) | (flags > paths))
        or np.any(flags != np.floor(flags))
    ):
        raise ValueError("diagnostic counts/flags must be bounded path counts")
    if (
        np.any(counts[:, 1] > counts[:, 0])
        or np.any(counts[:, 3] > counts[:, 2])
        or np.any(counts[:, 2] + counts[:, 4] != paths)
    ):
        raise ValueError("diagnostic survival/positive/support counts differ")
    if np.any(flags.max(axis=1) > counts[:, 4]) or np.any(flags.sum(axis=1) < counts[:, 4]):
        raise ValueError("diagnostic unsupported paths require explicit flags")
    for i, (s, t, m) in enumerate(inputs):
        for j in range(8):
            mean, se = stats[i, j]
            analytic = m == 1 and j in (2, 3, 5)
            unsupported = j >= 6 and counts[i, 4] > 0
            if analytic:
                if not np.isfinite(mean) or not np.isnan(se):
                    raise ValueError("analytic diagnostic conditioning has no MC SE")
            elif unsupported:
                if not np.isnan([mean, se]).all():
                    raise ValueError("unsupported OSS samples must not be filtered")
            elif not np.isfinite([mean, se]).all() or se < 0:
                raise ValueError("finite diagnostic mean/nonnegative SE required")
        teacher = _teacher()
        low = teacher.markov_reference(
            s,
            t,
            monitoring=int(m),
            order=p["reference"]["order"],
            tail_sigma=p["reference"]["tail_sigma"],
            **_contract(p),
        )
        high = teacher.markov_reference(
            s,
            t,
            monitoring=int(m),
            order=p["reference"]["check_order"],
            tail_sigma=p["reference"]["tail_sigma"],
            **_contract(p),
        )
        reference = np.asarray([low["price"], low["delta"]])
        error = np.abs(reference - [high["price"], high["delta"]]) + np.asarray(
            [low["tail_price_bound"], low["tail_delta_bound"]]
        )
        _close(arrays["diagnostic.reference"][i], reference, "diagnostic oracle")
        _close(
            arrays["diagnostic.reference_error"][i], error, "diagnostic refinement/truncation error"
        )


def _normalization(x, labels):
    features = np.column_stack((x[:, 0], np.log(x[:, 1])))
    return {
        "feature_mean": features.mean(axis=0),
        "feature_std": np.where(np.ptp(features, axis=0) > 0, features.std(axis=0), 1),
        "price_mean": labels[:, 0].mean(),
        "price_scale": max(labels[:, 0].std(), 1e-8),
        "delta_scale": max(np.sqrt(np.mean(labels[:, 1] ** 2)), 1e-8),
    }


def _export(arrays, model_id):
    result = {field: arrays[f"weight.{model_id}.{field}"] for field in _EXPORT_FIELDS}
    for key in ("kind", "dml", "price_mean", "price_scale", "delta_scale"):
        result[key] = result[key].item()
    return result


def _surface(arrays):
    grid = arrays["interpolation.reference"]
    return _module("replay").HermiteSurface(
        arrays["interpolation.spots"], arrays["interpolation.times"], grid[:, :, 0], grid[:, :, 1]
    )


def _safe_inputs():
    return np.asarray(
        [
            [100, 1],
            [70, 0.1],
            [119.5, 0.25],
            [120, 1],
            [121, 1],
            [-1, 1],
            [100, 0],
            [np.nan, 1],
            [100, 3],
        ],
        dtype=float,
    )


def _boundary_inputs():
    return np.asarray(
        [(s, t) for t in (0.25, 1.0, 2.0) for s in (119.0, 119.9, 119.999, 120.0, 120.001)]
    )


def _adoption(record):
    rows = []
    for seed in record["protocol"]["learning"]["seeds"]:
        price = record["models"][f"price_s{seed}"]["test"]
        dml = record["models"][f"dml_s{seed}"]["test"]
        ratio_p = (
            dml["price_rmse"] / price["price_rmse"] if price["price_rmse"] > 0 else float("inf")
        )
        ratio_d = (
            dml["delta_rmse"] / price["delta_rmse"] if price["delta_rmse"] > 0 else float("inf")
        )
        rows.append(
            {
                "seed": seed,
                "price_rmse_ratio": ratio_p,
                "delta_rmse_ratio": ratio_d,
                "quality_pass": bool(ratio_p <= 1.1 and ratio_d < 1),
                "dml_vs_hermite_price_rmse": dml["price_rmse"]
                / record["interpolation"]["test"]["price_rmse"],
                "dml_vs_hermite_delta_rmse": dml["delta_rmse"]
                / record["interpolation"]["test"]["delta_rmse"],
            }
        )
    return {
        "paired": rows,
        "all_seed_quality_pass": all(row["quality_pass"] for row in rows),
        "standard_speed_adopted": False,
        "timing_and_full_cost": (
            "measured; see benchmark/costs and explicit unmeasured boundary"
            if "benchmark" in record and "costs" in record
            else "pending; no automatic benchmark"
        ),
        "interpretation": "paired NN quality and strong Hermite accuracy tradeoff retained; accuracy alone does not establish full-cost speed advantage",
    }


def _pilot_gate(pilot_record, pilot_arrays):
    summary = _module("pilot").check_pilot(pilot_record, pilot_arrays)
    if pilot_record["mode"] != "full_pilot" or not all(
        v is True for v in summary["precision_proposal"]["checks"].values()
    ):
        raise ValueError("full independent pilot precision checks required")
    for case in summary["mc"]["cases"]:
        for method in (
            "raw_price",
            "raw_delta",
            "conditioned_price",
            "conditioned_delta",
            "oss_price",
            "oss_delta",
        ):
            if case["methods"][method]["reference_comparison"] is not True:
                raise ValueError(f"pilot MC gate failed: {method}")
    return summary


def _load_pilot():
    if not (HERE / "pilot.json").exists():
        raise ValueError("external pilot record/arrays or restored pilot files required")
    return _module("artifacts").load_bundle(HERE, stem="pilot")


def _provenance():
    paths = [
        Path(__file__),
        HERE / "protocol.json",
        HERE / "pilot.py",
        HERE / "replay.py",
        HERE / "reference_methods.py",
        HERE.parents[2] / "hullkit/src/hullkit/_discrete_barrier_teachers.py",
        ROOT / "deep_hedge_price/src/deep_hedge_price/_barrier_dml.py",
    ]
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def run_experiment(p, smoke=False, pilot_record=None, pilot_arrays=None):
    """Execute once; failed phases/fits remain in a saveable partial record."""
    _check_protocol(p)
    pilot_summary = None
    if not smoke:
        if p.get("state") != "frozen":
            raise ValueError("main protocol must be frozen before fitting")
        if pilot_record is None or pilot_arrays is None:
            pilot_record, pilot_arrays = _load_pilot()
        pilot_summary = _pilot_gate(pilot_record, pilot_arrays)
    replay, e = _module("replay"), _effective(p, smoke)
    record = {
        "schema": "rbf05-discrete-research-v1",
        "mode": "smoke" if smoke else "main",
        "protocol": copy.deepcopy(p),
        "effective": e,
        "status": "incomplete",
        "failures": [],
        "models": {},
        "source_digests": _provenance(),
        "source_digest_role": "provenance only; numeric evidence is replayed with tolerances",
        "pilot_summary": pilot_summary,
        "pilot_manifest": "pilot_manifest.json" if not smoke else None,
        "teacher": {
            "method": "last_conditional + first-transition score",
            "train_only_scales": True,
        },
        "canonical_gate": "fresh MC/diagnostic regeneration plus independent PDE test-grid comparison required",
    }
    arrays = {}
    phase = "datasets"
    try:
        for split in ("train", "validation"):
            x = _scenarios(p, split, e[split])
            arrays[split + ".inputs"] = x
            start = perf_counter()
            result = mc_labels(x, p["splits"][split + "_paths"], e["paths"])
            elapsed = perf_counter() - start
            record["teacher"][split + "_generation_s"] = elapsed
            for name, value in zip(
                ("labels", "label_se", "path_seed", "survival_count", "positive_count"),
                result,
                strict=True,
            ):
                arrays[split + "." + name] = value
        arrays["test.inputs"] = _test_inputs(p, e)
        for split in ("train", "validation", "test"):
            value, error, good = _oracle_details(arrays[split + ".inputs"])
            (
                arrays[split + ".reference"],
                arrays[split + ".reference_error"],
                arrays[split + ".reference_checked"],
            ) = value, error, good
            if not good.all():
                raise ArithmeticError(f"{split} oracle refinement failed")
            arrays[f"prediction.oracle.{split}"] = value.copy()
        record["baselines"] = {
            "oracle": {
                split: replay.metrics(arrays[split + ".reference"], arrays[split + ".reference"])
                for split in ("validation", "test")
            }
        }
        arrays["boundary.inputs"] = _boundary_inputs()
        arrays["boundary.reference"] = oracle(arrays["boundary.inputs"], verify=True)
        phase = "diagnostics"
        arrays.update(_diagnostic(p, smoke))
        record["diagnostic"] = _diagnostic_summary(arrays, p)
        phase = "interpolation"
        spots, times = (
            np.linspace(*p["domain"]["spot"], e["grid_spots"]),
            np.geomspace(*p["domain"]["maturity"], e["grid_times"]),
        )
        knots = np.asarray([(s, t) for t in times for s in spots])
        start = perf_counter()
        grid, error, good = _oracle_details(knots)
        if not good.all():
            raise ArithmeticError("interpolation oracle refinement failed")
        arrays["interpolation.spots"], arrays["interpolation.times"] = spots, times
        arrays["interpolation.reference"] = grid.reshape(len(times), len(spots), 2)
        arrays["interpolation.reference_error"] = error.reshape(len(times), len(spots), 2)
        surface = _surface(arrays)
        record["interpolation"] = {"gridsetup_s": perf_counter() - start}
        for split in ("validation", "test"):
            arrays[f"prediction.hermite.{split}"] = surface(arrays[split + ".inputs"])
            record["interpolation"][split] = replay.metrics(
                arrays[f"prediction.hermite.{split}"], arrays[split + ".reference"]
            )
        phase = "common_initialization"
        record["common_initialization_s"] = _initialize_framework()
        record["common_initialization"] = {
            "operation": "zero CPU float64 scalar parameter + Adam + one zero-gradient step",
            "scope": "one shared initialization before six NN fits; no network fit",
            "standalone_allocation": "once per model, outside fit elapsed/cap",
            "rng": "CPU fork_rng(devices=[]); caller state restored",
        }
        phase = "fitting"
        learner = _learner()
        model_ids = [
            f"{mode}_s{seed}" for mode in p["learning"]["modes"] for seed in p["learning"]["seeds"]
        ]
        arrays["model_ids"] = np.asarray(model_ids)
        for mode in p["learning"]["modes"]:
            for seed in p["learning"]["seeds"]:
                model_id = f"{mode}_s{seed}"
                try:
                    labels = arrays["train.labels"]
                    fit = learner.train(
                        arrays["train.inputs"],
                        labels[:, 0],
                        labels[:, 1],
                        seed=seed,
                        dml=mode == "dml",
                        updates=e["updates"],
                        budget_s=p["learning"]["budget_s"],
                    )
                    start = perf_counter()
                    exported = learner.export(fit)
                    export_s = perf_counter() - start
                    for field in _EXPORT_FIELDS:
                        arrays[f"weight.{model_id}.{field}"] = np.asarray(exported[field])
                    record["models"][model_id] = dict(
                        fit.stats,
                        train_teacher_s=record["teacher"]["train_generation_s"],
                        common_initialization_s=record["common_initialization_s"],
                        export_s=export_s,
                        offline_s=record["teacher"]["train_generation_s"]
                        + fit.stats["elapsed_s"]
                        + export_s
                        + record["common_initialization_s"],
                    )
                    for split in ("validation", "test"):
                        native = np.column_stack(learner.predict(fit, arrays[split + ".inputs"]))
                        independent = replay.predict_nn(exported, arrays[split + ".inputs"])
                        _close(native, independent, "learner vs NumPy replay")
                        arrays[f"prediction.{model_id}.{split}"] = native
                        record["models"][model_id][split] = replay.metrics(
                            native, arrays[split + ".reference"]
                        )
                    if fit.stats["budget_failure"]:
                        record["failures"].append(
                            {
                                "phase": "fit",
                                "model_id": model_id,
                                "reason": "budget_failure",
                                "stats": fit.stats,
                            }
                        )
                except Exception as exc:
                    record["failures"].append(
                        {
                            "phase": "fit",
                            "model_id": model_id,
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
        if record["failures"]:
            return record, arrays
        phase = "safe_policy"
        arrays["safe.inputs"] = _safe_inputs()
        for model_id in [*model_ids, "hermite", "oracle"]:
            approximation = (
                (lambda x: oracle(x, verify=True))
                if model_id == "oracle"
                else (
                    surface
                    if model_id == "hermite"
                    else lambda x, mid=model_id: replay.predict_nn(_export(arrays, mid), x)
                )
            )
            served = replay.serve(
                approximation, arrays["safe.inputs"], lambda x: oracle(x, verify=True)
            )
            arrays[f"safe.{model_id}.prediction"], arrays[f"safe.{model_id}.status"] = (
                served["prediction"],
                served["status"],
            )
            served_test = replay.serve(
                approximation, arrays["test.inputs"], lambda x: oracle(x, verify=True)
            )
            arrays[f"prediction.{model_id}.safe"], arrays[f"routing.{model_id}.safe"] = (
                served_test["prediction"],
                served_test["status"],
            )
            metadata = (
                record["interpolation"]
                if model_id == "hermite"
                else (
                    record["baselines"]["oracle"]
                    if model_id == "oracle"
                    else record["models"][model_id]
                )
            )
            metadata["test_raw"] = metadata["test"].copy()
            metadata["test_safe"] = replay.metrics(
                served_test["prediction"], arrays["test.reference"]
            )
        unsupported = replay.serve(
            surface,
            np.asarray([[100.0, 1.0]]),
            lambda x: oracle(x, verify=True),
            contract={"barrier": 121.0},
        )
        arrays["safe.unsupported.prediction"], arrays["safe.unsupported.status"] = (
            unsupported["prediction"],
            unsupported["status"],
        )
        record["adoption"] = _adoption(record)
        arrays["adoption.paired"] = np.asarray(
            [
                [
                    r["seed"],
                    r["price_rmse_ratio"],
                    r["delta_rmse_ratio"],
                    r["quality_pass"],
                    r["dml_vs_hermite_price_rmse"],
                    r["dml_vs_hermite_delta_rmse"],
                ]
                for r in record["adoption"]["paired"]
            ]
        )
        record["status"] = "complete"
    except Exception as exc:
        record["failures"].append({"phase": phase, "reason": f"{type(exc).__name__}: {exc}"})
    return record, arrays


def _close(actual, expected, name):
    aa, bb = np.asarray(actual), np.asarray(expected)
    if aa.dtype.kind in "biu" and bb.dtype.kind in "biu":
        if not np.array_equal(aa, bb):
            raise ValueError(f"{name}: discrete IDs/counts differ")
        return
    if np.shape(actual) != np.shape(expected) or not np.allclose(
        actual, expected, rtol=1e-9, atol=1e-10, equal_nan=True
    ):
        raise ValueError(f"{name}: evidence differs from recomputation")


def _compare(actual, expected, name):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{name}: keys differ")
        for key in expected:
            _compare(actual[key], expected[key], name + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{name}: length differs")
        for i, value in enumerate(expected):
            _compare(actual[i], value, f"{name}[{i}]")
    elif isinstance(expected, float):
        _close(actual, expected, name)
    elif actual != expected:
        raise ValueError(f"{name}: metadata differs")


def check_record(record, arrays, *, fresh=False, pilot_record=None, pilot_arrays=None):
    """Torch-free saved-weight checking; fresh replay also checks MC and PDE."""
    if (
        record.get("schema") != "rbf05-discrete-research-v1"
        or record.get("status") != "complete"
        or record.get("failures")
    ):
        raise ValueError("incomplete or unknown research record")
    p, replay = record["protocol"], _module("replay")
    _check_protocol(p)
    if record.get("mode") not in ("smoke", "main"):
        raise ValueError("unknown experiment mode")
    smoke, e = record["mode"] == "smoke", _effective(p, record["mode"] == "smoke")
    if record.get("effective") != e:
        raise ValueError("effective protocol differs")
    if not smoke:
        if p.get("state") != "frozen":
            raise ValueError("main protocol is not frozen")
        if pilot_record is None or pilot_arrays is None:
            pilot_record, pilot_arrays = _load_pilot()
        _compare(record["pilot_summary"], _pilot_gate(pilot_record, pilot_arrays), "pilot summary")
    for split in ("train", "validation"):
        expected = _scenarios(p, split, e[split])
        _close(arrays[split + ".inputs"], expected, split + " scenarios")
        _close(
            arrays[split + ".path_seed"],
            _row_seeds(p["splits"][split + "_paths"], e[split]),
            split + " row path seeds",
        )
        if (
            arrays[split + ".labels"].shape != expected.shape
            or arrays[split + ".label_se"].shape != expected.shape
            or not np.isfinite(arrays[split + ".labels"]).all()
            or not np.isfinite(arrays[split + ".label_se"]).all()
            or np.any(arrays[split + ".label_se"] < 0)
        ):
            raise ValueError("finite aligned labels and nonnegative SE required")
        for key in ("survival_count", "positive_count"):
            count = arrays[split + "." + key]
            if (
                count.shape != (e[split],)
                or np.any((count < 0) | (count > e["paths"]))
                or np.any(count != np.floor(count))
            ):
                raise ValueError("invalid teacher counts")
        if np.any(arrays[split + ".positive_count"] > arrays[split + ".survival_count"]):
            raise ValueError("positive payoff count exceeds survival count")
        if fresh:
            result = mc_labels(expected, p["splits"][split + "_paths"], e["paths"])
            for key, value in zip(
                ("labels", "label_se", "path_seed", "survival_count", "positive_count"),
                result,
                strict=True,
            ):
                _close(arrays[split + "." + key], value, "fresh " + split + " " + key)
    _close(arrays["test.inputs"], _test_inputs(p, e), "fixed test grid")
    expected_ids = [
        f"{mode}_s{seed}" for mode in p["learning"]["modes"] for seed in p["learning"]["seeds"]
    ]
    if arrays["model_ids"].tolist() != expected_ids or set(record["models"]) != set(expected_ids):
        raise ValueError("fixed six-model roster differs")
    scale = _normalization(arrays["train.inputs"], arrays["train.labels"])
    common = record.get("common_initialization_s", -1)
    if not np.isfinite(common) or common <= 0:
        raise ValueError("positive common framework initialization cost required")
    for model_id in expected_ids:
        model, stats = _export(arrays, model_id), record["models"][model_id]
        mode, seed = model_id.split("_s")
        for key, expected in scale.items():
            _close(model[key], expected, "train-only " + key)
        if model["kind"] != "barrier_nn" or model["dml"] != (mode == "dml"):
            raise ValueError("NN kind or mode mismatch")
        for j, shape in enumerate(((32, 2), (32, 32), (1, 32))):
            if np.shape(model[f"layer{j}_weight"]) != shape or np.shape(
                model[f"layer{j}_bias"]
            ) != (shape[0],):
                raise ValueError("fixed NN architecture differs")
        expected_stats = {
            "seed": int(seed),
            "dml": mode == "dml",
            "updates": e["updates"],
            "requested_updates": e["updates"],
            "batch_size": min(128, e["train"]),
            "batch_seed": int(seed) + 104729,
            "threads": 1,
            "learning_rate": 0.003,
            "delta_weight": 1.0 if mode == "dml" else 0.0,
            "budget_s": p["learning"]["budget_s"],
            "budget_failure": False,
        }
        for key, expected in expected_stats.items():
            if stats.get(key) != expected:
                raise ValueError("fit budget/updates/seed metadata differs: " + key)
        for key in (
            "setup_s",
            "training_s",
            "elapsed_s",
            "export_s",
            "train_teacher_s",
            "common_initialization_s",
            "offline_s",
            "overrun_s",
        ):
            if not np.isfinite(stats[key]) or stats[key] < 0:
                raise ValueError("nonnegative finite costs required")
        if (
            stats["elapsed_s"] > stats["budget_s"]
            or stats["elapsed_s"] + 1e-8 < stats["setup_s"] + stats["training_s"]
        ):
            raise ValueError("fit cap or elapsed accounting mismatch")
        _close(
            stats["train_teacher_s"],
            record["teacher"]["train_generation_s"],
            "shared train teacher cost",
        )
        _close(
            stats["common_initialization_s"],
            common,
            "common framework initialization cost allocation",
        )
        _close(
            stats["offline_s"],
            stats["train_teacher_s"] + stats["elapsed_s"] + stats["export_s"] + common,
            "offline teacher+fit+export+common cost",
        )
        for key in (
            "initial_price_loss",
            "initial_delta_loss",
            "initial_loss",
            "final_price_loss",
            "final_delta_loss",
            "final_loss",
        ):
            if not np.isfinite(stats[key]) or stats[key] < 0:
                raise ValueError("nonnegative finite fit losses required")
        _close(
            stats["initial_loss"],
            stats["initial_price_loss"] + stats["initial_delta_loss"],
            "initial objective accounting",
        )
        train_prediction = replay.predict_nn(model, arrays["train.inputs"])
        price_loss = np.mean(
            ((train_prediction[:, 0] - arrays["train.labels"][:, 0]) / scale["price_scale"]) ** 2
        )
        delta_loss = (
            np.mean(
                ((train_prediction[:, 1] - arrays["train.labels"][:, 1]) / scale["delta_scale"])
                ** 2
            )
            if mode == "dml"
            else 0.0
        )
        _close(stats["final_price_loss"], price_loss, "replayed final price loss")
        _close(stats["final_delta_loss"], delta_loss, "replayed final Delta loss")
        _close(stats["final_loss"], price_loss + delta_loss, "replayed final objective")
        for split in ("validation", "test"):
            prediction = replay.predict_nn(model, arrays[split + ".inputs"])
            _close(
                arrays[f"prediction.{model_id}.{split}"],
                prediction,
                "saved NumPy replay prediction",
            )
            _compare(
                stats[split],
                replay.metrics(prediction, arrays[split + ".reference"]),
                split + " metrics",
            )
    spots, times = (
        np.linspace(*p["domain"]["spot"], e["grid_spots"]),
        np.geomspace(*p["domain"]["maturity"], e["grid_times"]),
    )
    _close(arrays["interpolation.spots"], spots, "Hermite spot knots")
    _close(arrays["interpolation.times"], times, "Hermite time knots")
    surface = _surface(arrays)
    if (
        not np.isfinite(record["interpolation"]["gridsetup_s"])
        or record["interpolation"]["gridsetup_s"] < 0
    ):
        raise ValueError("invalid interpolation setup cost")
    for split in ("train", "validation", "test"):
        value, error, good = _oracle_details(arrays[split + ".inputs"])
        _close(arrays[split + ".reference"], value, "checked " + split + " oracle")
        _close(arrays[split + ".reference_error"], error, "oracle convergence error")
        _close(arrays[split + ".reference_checked"], good, "oracle convergence flags")
        if not good.all():
            raise ValueError("reference convergence failed")
        _close(arrays[f"prediction.oracle.{split}"], value, "oracle baseline prediction")
        if split != "train":
            prediction = surface(arrays[split + ".inputs"])
            _close(arrays[f"prediction.hermite.{split}"], prediction, "Hermite prediction")
            _compare(
                record["interpolation"][split], replay.metrics(prediction, value), "Hermite metrics"
            )
            _compare(
                record["baselines"]["oracle"][split],
                replay.metrics(value, value),
                "oracle baseline metrics",
            )
    knots = np.asarray([(s, t) for t in times for s in spots])
    grid, error, good = _oracle_details(knots)
    _close(
        arrays["interpolation.reference"],
        grid.reshape(len(times), len(spots), 2),
        "GL interpolation knots",
    )
    _close(
        arrays["interpolation.reference_error"],
        error.reshape(len(times), len(spots), 2),
        "GL interpolation convergence",
    )
    if not good.all():
        raise ValueError("Hermite reference convergence failed")
    _close(arrays["safe.inputs"], _safe_inputs(), "fixed safe probes")
    _close(arrays["boundary.inputs"], _boundary_inputs(), "fixed boundary contract probes")
    _close(
        arrays["boundary.reference"],
        oracle(arrays["boundary.inputs"], verify=True),
        "boundary continuation/contact oracle",
    )
    for model_id in [*expected_ids, "hermite", "oracle"]:
        approximation = (
            (lambda x: oracle(x, verify=True))
            if model_id == "oracle"
            else (
                surface
                if model_id == "hermite"
                else lambda x, mid=model_id: replay.predict_nn(_export(arrays, mid), x)
            )
        )
        served = replay.serve(
            approximation, arrays["safe.inputs"], lambda x: oracle(x, verify=True)
        )
        _close(
            arrays[f"safe.{model_id}.prediction"], served["prediction"], "safe returned price/Delta"
        )
        if arrays[f"safe.{model_id}.status"].tolist() != served["status"].tolist():
            raise ValueError("safe probe routing differs")
        served_test = replay.serve(
            approximation, arrays["test.inputs"], lambda x: oracle(x, verify=True)
        )
        _close(
            arrays[f"prediction.{model_id}.safe"],
            served_test["prediction"],
            "safe test predictions",
        )
        if arrays[f"routing.{model_id}.safe"].tolist() != served_test["status"].tolist():
            raise ValueError("safe test routing differs")
        metadata = (
            record["interpolation"]
            if model_id == "hermite"
            else (
                record["baselines"]["oracle"]
                if model_id == "oracle"
                else record["models"][model_id]
            )
        )
        _compare(metadata["test_raw"], metadata["test"], "raw metrics alias")
        _compare(
            metadata["test_safe"],
            replay.metrics(served_test["prediction"], arrays["test.reference"]),
            "safe test metrics",
        )
    if (
        arrays["safe.unsupported.status"].tolist() != ["unsupported"]
        or not np.isnan(arrays["safe.unsupported.prediction"]).all()
    ):
        raise ValueError("unsupported contract must fail explicitly")
    _check_diagnostic(arrays, p, smoke)
    _compare(record["diagnostic"], _diagnostic_summary(arrays, p), "diagnostic means/SE/counts")
    if fresh:
        for key, value in _diagnostic(p, smoke).items():
            _close(arrays[key], value, "fresh " + key)
        if not smoke:
            refs = _module("reference_methods")
            test = arrays["test.inputs"]
            independent = np.empty_like(arrays["test.reference"])
            for t in np.unique(test[:, 1]):
                mask = test[:, 1] == t
                result = refs.pde_reference(
                    test[mask, 0],
                    t,
                    monitors=p["contract"]["positive_monitoring"],
                    space_nodes=p["reference"]["pde_space"],
                    steps_per_monitor=p["reference"]["pde_steps"],
                    log_half_width=p["reference"]["pde_half_width"],
                    barrier_phase=p["reference"]["pde_phase"],
                    bump=0.0005,
                )
                independent[mask] = np.column_stack((result["price"], result["delta"]))
            difference = np.abs(independent - arrays["test.reference"])
            if np.any(difference[:, 0] > p["reference"]["price_tolerance"]) or np.any(
                difference[:, 1] > p["reference"]["delta_tolerance"]
            ):
                raise ValueError("independent PDE test-grid tolerance failed")
    adoption = _adoption(record)
    _compare(record["adoption"], adoption, "paired quality/adoption")
    paired = np.asarray(
        [
            [
                r["seed"],
                r["price_rmse_ratio"],
                r["delta_rmse_ratio"],
                r["quality_pass"],
                r["dml_vs_hermite_price_rmse"],
                r["dml_vs_hermite_delta_rmse"],
            ]
            for r in adoption["paired"]
        ]
    )
    _close(arrays["adoption.paired"], paired, "adoption evidence")
    return {
        "mode": record["mode"],
        "models": len(expected_ids),
        "fresh": bool(fresh),
        "adoption": adoption,
    }


def save_result(output, record, arrays):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "reference.npz", **arrays)
    saved = copy.deepcopy(record)
    # Retain a failed computation even if the subsequent storage boundary fails.
    (output / "reference.json").write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
    saved["artifact"] = _module("artifacts").store_large(output, stem="reference")
    saved["artifact"]["arrays"] = {
        key: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in arrays.items()
    }
    (output / "reference.json").write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
    return output / "reference.json", output / "reference.npz"


def load_result(output):
    record, arrays = _module("artifacts").load_bundle(output, stem="reference")
    registry = {
        key: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in arrays.items()
    }
    if record.get("artifact", {}).get("arrays") != registry:
        raise ValueError("artifact array registry differs")
    return record, arrays


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args(argv)
    if args.refresh:
        record, arrays = run_experiment(protocol(), smoke=args.smoke)
        save_result(args.output, record, arrays)
        if record["status"] != "complete":
            print(json.dumps({"status": record["status"], "failures": record["failures"]}))
            return 1
    elif not args.check:
        parser.error("choose --refresh or --check")
    if args.check or args.fresh:
        record, arrays = load_result(args.output)
        print(json.dumps(check_record(record, arrays, fresh=args.fresh)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
