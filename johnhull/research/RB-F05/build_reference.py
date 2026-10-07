"""Generate RB-F05 digital experiments; --check reuses weights, never trains."""

import argparse
import json
import platform
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _digital_teachers as teacher
from scipy.integrate import quad
from scipy.interpolate import CubicHermiteSpline
from scipy.special import ndtr

HERE = Path(__file__).resolve().parent
RATE, VOL, STRIKE = 0.03, 0.2, 100.0
METHODS = ["lrm", "conditional", "crn", "ramp", "pathwise"]
SEEDS = [11, 29, 47]


def exact(inputs):
    """Vectorized closed-form reference, independently cross-checked in tests."""
    s, t = np.asarray(inputs).T
    d = (np.log(s / STRIKE) + (RATE - VOL**2 / 2) * t) / (VOL * np.sqrt(t))
    price = np.exp(-RATE * t) * ndtr(d)
    delta = np.exp(-RATE * t - d * d / 2) / (s * VOL * np.sqrt(2 * np.pi * t))
    return np.column_stack([price, delta])


def integrated(inputs):
    """Compute price/delta by independent Gaussian tail integration."""

    def density(z):
        return np.exp(-z * z / 2) / np.sqrt(2 * np.pi)

    output = []
    for s, t in inputs:
        a = (np.log(STRIKE / s) - (RATE - VOL**2 / 2) * t) / (VOL * np.sqrt(t))
        p = quad(density, a, np.inf, epsabs=1e-12)[0] * np.exp(-RATE * t)
        d = quad(lambda z: z * density(z), a, np.inf, epsabs=1e-12)[0]
        output.append([p, d * np.exp(-RATE * t) / (s * VOL * np.sqrt(t))])
    return np.array(output)


def metrics(prediction, target):
    """Derive physical price/delta RMSE and 99th-percentile/max absolute errors."""
    prediction, target = np.asarray(prediction), np.asarray(target)
    if prediction.shape != target.shape or prediction.ndim != 2 or prediction.shape[1] != 2:
        raise ValueError("matching price/delta rows required")
    error = prediction - target
    if not np.all(np.isfinite(error)) or len(error) == 0:
        raise ValueError("finite nonempty error rows required")
    result = {}
    for i, name in enumerate(["price", "delta"]):
        result[name + "_rmse"] = float(np.sqrt(np.mean(error[:, i] ** 2)))
        result[name + "_p99_abs"] = float(np.quantile(np.abs(error[:, i]), 0.99))
        result[name + "_max_abs"] = float(np.max(np.abs(error[:, i])))
    return result


def diagnostic(seed, paths):
    """Generate independent scenario streams and mean/SE arrays for all teachers."""
    inputs = np.array([[s, t] for t in [0.05, 1 / 3, 2] for s in [95, 100, 105]])
    z = np.random.default_rng(seed).standard_normal((len(inputs), paths))
    values = teacher.samples(inputs[:, 0], STRIKE, RATE, VOL, inputs[:, 1], z, ramp_width=8)
    pairs = {
        "lrm": ("payoff", "lrm"),
        "conditional": ("conditional_price", "conditional_delta"),
        "crn": ("payoff", "crn_bump"),
        "ramp": ("ramp_price", "ramp_delta"),
        "pathwise": ("payoff", "pathwise"),
    }
    arrays = {"inputs": inputs, "target": exact(inputs)}
    for name, keys in pairs.items():
        summary = [teacher.summarize(values[key]) for key in keys]
        arrays[name + "_mean"] = np.column_stack([row[0] for row in summary])
        arrays[name + "_se"] = np.column_stack([row[1] for row in summary])
    return arrays


def _close(left, right, label, *, atol=2e-11):
    assert np.allclose(left, right, rtol=2e-9, atol=atol), label


def _numeric_record(record, expected, label):
    for key, value in expected.items():
        _close(record[key], value, label + ":" + key)


def numpy_prediction(arrays, name, inputs):
    """Independently run saved network weights and chain-rule spot derivative."""
    prefix = name + "_weight_"
    mean, std = arrays[prefix + "mean"], arrays[prefix + "std"]
    z = (np.column_stack([inputs[:, 0], np.log(inputs[:, 1])]) - mean) / std
    w1, w2, w3 = [arrays[prefix + layer + ".weight"] for layer in ["first", "second", "last"]]
    b1, b2, b3 = [arrays[prefix + layer + ".bias"] for layer in ["first", "second", "last"]]
    h1 = np.tanh(z @ w1.T + b1)
    h2 = np.tanh(h1 @ w2.T + b2)
    probability = 1 / (1 + np.exp(-(h2 @ w3.T + b3).ravel()))
    g1 = (1 - h1 * h1) * w1[:, 0] / std[0]
    g2 = (g1 @ w2.T) * (1 - h2 * h2)
    price = np.exp(-RATE * inputs[:, 1]) * probability
    delta = price * (1 - probability) * (g2 @ w3.T).ravel()
    return np.column_stack([price, delta])


def inside(inputs):
    """Declared input domain, fixed before training; not inferred from test errors."""
    s, t = inputs.T
    return (s >= 80) & (s <= 120) & (t >= 0.05) & (t <= 2)


def interpolator():
    """Hermite price/Greek interpolation in spot, linear interpolation in log T."""
    spots = np.linspace(80, 120, 33)
    times = np.geomspace(0.05, 2, 17)
    surfaces = []
    for t in times:
        rows = exact(np.column_stack([spots, np.full_like(spots, t)]))
        surfaces.append(CubicHermiteSpline(spots, rows[:, 0], rows[:, 1]))

    def evaluate(inputs):
        s, t = inputs.T
        index = np.clip(np.searchsorted(times, t) - 1, 0, len(times) - 2)
        ratio = (np.log(t) - np.log(times[index])) / (
            np.log(times[index + 1]) - np.log(times[index])
        )
        result = np.empty((len(inputs), 2))
        for i in np.unique(index):
            mask = index == i
            for derivative in [0, 1]:
                result[mask, derivative] = (1 - ratio[mask]) * surfaces[i](
                    s[mask], nu=derivative
                ) + ratio[mask] * surfaces[i + 1](s[mask], nu=derivative)
        return result

    return evaluate


def adoption(runs, baselines):
    """Compute paired-seed quality and speed decisions without seed selection."""
    paired = []
    for seed in SEEDS:
        a = next(r for r in runs if r["seed"] == seed and not r["dml"])
        b = next(r for r in runs if r["seed"] == seed and r["dml"])
        paired.append(
            {
                "seed": seed,
                "price_not_materially_worse": b["test"]["price_rmse"]
                <= 1.10 * a["test"]["price_rmse"],
                "delta_improves": b["test"]["delta_rmse"] < a["test"]["delta_rmse"],
            }
        )
    fastest = min(baselines, key=lambda b: b["online_s_per_query"])
    recover = []
    for run in runs:
        saving = fastest["online_s_per_query"] - run["online_s_per_query"]
        recover.append(
            {
                "name": run["name"],
                "queries": run["offline_s"] / saving if saving > 0 else None,
                "reason": "positive timing denominator"
                if saving > 0
                else "nonpositive timing denominator",
            }
        )
    return {
        "paired_quality": paired,
        "dml_quality_all_seeds": all(
            p["price_not_materially_worse"] and p["delta_improves"] for p in paired
        ),
        "fastest_comparator": fastest["name"],
        "cost_recovery": recover,
        "standard_speed_adoption": all(
            r["queries"] is not None for r in recover if r["name"].startswith("dml_")
        ),
    }


def check_record(data, arrays, *, fresh):
    """Recompute split, targets, predictions, metrics, cost totals and decisions."""
    ids = [arrays[s + "_id"].tolist() for s in ["train", "validation", "test"]]
    assert len({item for group in ids for item in group}) == sum(map(len, ids)), (
        "scenario ID leakage"
    )
    for split in ["train", "validation", "test"]:
        x = arrays[split + "_inputs"]
        _close(arrays[split + "_target"], exact(x), "reference:" + split)
    # Feature normalization must use the training split only.
    features = np.column_stack([arrays["train_inputs"][:, 0], np.log(arrays["train_inputs"][:, 1])])
    for run in data["runs"]:
        name = run["name"]
        _close(arrays[name + "_weight_mean"], features.mean(axis=0), "train mean")
        _close(arrays[name + "_weight_std"], features.std(axis=0), "train std")
        for split in ["validation", "test"]:
            prediction = numpy_prediction(arrays, name, arrays[split + "_inputs"])
            _close(arrays[name + "_" + split], prediction, "saved weights:" + name + split)
            if split == "test":
                _close(arrays[name + "_prediction"], prediction, "test prediction alias")
            _close(
                arrays[name + "_" + split + "_error"],
                prediction - arrays[split + "_target"],
                "error array:" + name,
            )
            _numeric_record(
                run[split], metrics(prediction, arrays[split + "_target"]), "metrics:" + name
            )
        expected_offline = (
            run["teacher_s"]
            + run["training_s"]
            + run["verification_s"]
            + data["common_initialization_s"]
        )
        _close(run["offline_s"], expected_offline, "offline cost sum")
        _close(
            run["total_at_1000_s"],
            run["offline_s"] + 1000 * run["online_s_per_query"],
            "full deployment cost",
        )
        _close(
            run["overrun_s"],
            max(0.0, run["teacher_s"] + run["training_s"] + data["common_initialization_s"] - 8),
            "budget overrun",
        )
        assert (
            run["online_s_per_query"] > 0
            and min(run[k] for k in ["teacher_s", "training_s", "verification_s"]) >= 0
        ), "negative cost"
        predictions = arrays[name + "_prediction"]
        assert np.all(predictions[:, 0] >= 0) and np.all(
            predictions[:, 0] <= np.exp(-RATE * arrays["test_inputs"][:, 1]) + 2e-12
        ), "digital price bounds"
        served = numpy_prediction(arrays, name, arrays["served_inputs"])
        served[~inside(arrays["served_inputs"])] = exact(
            arrays["served_inputs"][~inside(arrays["served_inputs"])]
        )
        _close(arrays[name + "_served"], served, "OOD fallback")
    for baseline in data["baselines"]:
        _close(
            baseline["offline_s"],
            baseline["setup_s"] + baseline["verification_s"],
            "baseline offline sum",
        )
        _numeric_record(
            baseline["test"],
            metrics(arrays[baseline["name"] + "_prediction"], arrays["test_target"]),
            "baseline metrics",
        )
        _close(
            baseline["total_at_1000_s"],
            baseline["offline_s"] + 1000 * baseline["online_s_per_query"],
            "baseline total cost",
        )
    assert data["adoption"] == adoption(data["runs"], data["baselines"]), "adoption from evidence"
    _close(arrays["diagnostic_target"], exact(arrays["diagnostic_inputs"]), "diagnostic targets")
    for method in ["lrm", "conditional"]:
        assert np.all(
            np.abs(arrays["diagnostic_" + method + "_mean"] - arrays["diagnostic_target"])
            <= 6 * arrays["diagnostic_" + method + "_se"] + 2e-12
        ), "unbiased teacher 6SE"
    assert np.allclose(arrays["diagnostic_pathwise_mean"][:, 1], 0), "zero negative control"
    if fresh:
        _close(
            integrated(arrays["test_inputs"]),
            arrays["test_target"],
            "independent density integration",
        )
        regenerated = diagnostic(1107, 65_536)
        for key, value in regenerated.items():
            _close(arrays["diagnostic_" + key], value, "regenerated teacher:" + key)
        z = np.random.default_rng(4017).standard_normal((512, 2048))
        x = arrays["train_inputs"]
        samples = teacher.samples(x[:, 0], STRIKE, RATE, VOL, x[:, 1], z)
        for field, key in [("price", "payoff"), ("delta", "lrm")]:
            mean, se = teacher.summarize(samples[key])
            _close(arrays["train_" + field], mean, "fresh training teacher")
            _close(arrays["train_" + field + "_se"], se, "fresh training teacher SE")
        _close(
            arrays["integral_prediction"], integrated(arrays["test_inputs"]), "integral baseline"
        )
        _close(
            arrays["hermite_prediction"], interpolator()(arrays["test_inputs"]), "Hermite baseline"
        )


def _timed_per_query(function, inputs, repeats=20):
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        function(inputs)
        samples.append((perf_counter() - start) / len(inputs))
    return float(np.median(samples))


def baseline_experiment(arrays):
    """Measure complete baseline setup, validation and served price/Greek cost."""
    baselines = []
    for name in ["analytic", "integral", "hermite"]:
        start = perf_counter()
        function = (
            interpolator() if name == "hermite" else (exact if name == "analytic" else integrated)
        )
        setup_s = perf_counter() - start if name == "hermite" else 0.0
        start = perf_counter()
        arrays[name + "_prediction"] = function(arrays["test_inputs"])
        score = metrics(arrays[name + "_prediction"], arrays["test_target"])

        def serve(inputs, function=function):
            mask = inside(inputs)
            output = np.empty((len(inputs), 2))
            output[mask] = function(inputs[mask])
            output[~mask] = exact(inputs[~mask])
            return output

        cost = _timed_per_query(
            serve, arrays["served_inputs"], repeats=3 if name == "integral" else 20
        )
        verify_s = perf_counter() - start
        baselines.append(
            {
                "name": name,
                "test": score,
                "setup_s": setup_s,
                "verification_s": verify_s,
                "offline_s": setup_s + verify_s,
                "online_s_per_query": cost,
                "total_at_1000_s": setup_s + verify_s + 1000 * cost,
            }
        )
    return baselines


def generate():
    """Run the fixed pilot and all six CPU fits; retain all arrays and negative results."""
    import torch

    from deep_hedge_price import _digital_dml as learner

    arrays, data = (
        {},
        {
            "version": 1,
            "contract": "GBM digital call payout=1, no dividends",
            "seeds": SEEDS,
            "budget_s": 8,
            "teacher_paths_per_scenario": 2048,
            "teacher_stream": 4017,
            "diagnostic_stream": 1107,
            "network": "2x32 tanh, bounded sigmoid; CPU float64, full batch Adam lr=.003",
            "pilot": {
                "seed": 6017,
                "paths": 32768,
                "multiplier": 6,
                "reference_abs_tolerance": 2e-12,
            },
        },
    )
    # Pilot and tolerances are fixed before the main experiment or any fit.
    pilot = diagnostic(6017, 32768)
    for method in ["lrm", "conditional"]:
        assert np.all(
            np.abs(pilot[method + "_mean"] - pilot["target"]) <= 6 * pilot[method + "_se"] + 2e-12
        ), "fixed pilot"
    for key, value in diagnostic(1107, 65_536).items():
        arrays["diagnostic_" + key] = value
    for split, count, stream in [("train", 512, 3017), ("validation", 128, 3029)]:
        rng = np.random.default_rng(stream)
        x = np.column_stack(
            [rng.uniform(80, 120, count), np.exp(rng.uniform(np.log(0.05), np.log(2), count))]
        )
        arrays[split + "_inputs"] = x
        arrays[split + "_id"] = np.array([f"{split}:{i:04d}" for i in range(count)])
        arrays[split + "_target"] = exact(x)
    spots, times = np.linspace(80, 120, 25), np.array([0.05, 0.075, 0.1, 0.2, 1 / 3, 0.5, 1, 2])
    arrays["test_inputs"] = np.array([[s, t] for t in times for s in spots])
    arrays["test_id"] = np.array([f"test:{i:04d}" for i in range(len(arrays["test_inputs"]))])
    arrays["test_target"] = exact(arrays["test_inputs"])
    arrays["served_inputs"] = np.vstack(
        [arrays["test_inputs"], [[70, 0.02], [130, 0.1], [100, 3], [100, 0.01]]]
    )
    data["grid"] = {"spots": spots.tolist(), "times": times.tolist()}
    data["streams"] = {
        "train_scenarios": 3017,
        "validation_scenarios": 3029,
        "train_paths": 4017,
        "pilot_paths": 6017,
        "diagnostic_paths": 1107,
    }
    start = perf_counter()
    z = np.random.default_rng(4017).standard_normal((512, 2048))
    x = arrays["train_inputs"]
    values = teacher.samples(x[:, 0], STRIKE, RATE, VOL, x[:, 1], z)
    for field, key in [("price", "payoff"), ("delta", "lrm")]:
        arrays["train_" + field], arrays["train_" + field + "_se"] = teacher.summarize(values[key])
    teacher_s = perf_counter() - start
    # Warm up the same engine once; charge it to every standalone deployment.
    start = perf_counter()
    learner.train(
        x[:16],
        arrays["train_price"][:16],
        arrays["train_delta"][:16],
        seed=701,
        dml=True,
        budget_s=5,
        max_updates=1,
    )
    data["common_initialization_s"] = perf_counter() - start
    assert teacher_s + data["common_initialization_s"] < 7, "CPU setup consumed fit budget"
    runs = []
    for seed in SEEDS:
        for differential in [False, True] if seed != 29 else [True, False]:
            name = ("dml_" if differential else "price_") + str(seed)
            print("Training", name, flush=True)
            fit = learner.train(
                x,
                arrays["train_price"],
                arrays["train_delta"],
                seed=seed,
                dml=differential,
                budget_s=8 - data["common_initialization_s"],
                teacher_s=teacher_s,
            )
            run = {"name": name, **fit.stats}
            start = perf_counter()
            for split in ["validation", "test"]:
                prediction = np.column_stack(learner.predict(fit, arrays[split + "_inputs"]))
                arrays[name + "_" + split] = prediction
                arrays[name + "_" + split + "_error"] = prediction - arrays[split + "_target"]
                run[split] = metrics(prediction, arrays[split + "_target"])
            arrays[name + "_prediction"] = arrays[name + "_test"].copy()
            for key, value in fit.model.state_dict().items():
                arrays[name + "_weight_" + key] = value.detach().numpy().copy()

            def serve(inputs, fit=fit):
                mask = inside(inputs)
                output = np.empty((len(inputs), 2))
                if np.any(mask):
                    output[mask] = np.column_stack(learner.predict(fit, inputs[mask]))
                if np.any(~mask):
                    output[~mask] = exact(inputs[~mask])
                return output

            arrays[name + "_served"] = serve(arrays["served_inputs"])
            run["online_s_per_query"] = _timed_per_query(serve, arrays["served_inputs"])
            run["verification_s"] = perf_counter() - start
            run["offline_s"] = (
                teacher_s
                + run["training_s"]
                + run["verification_s"]
                + data["common_initialization_s"]
            )
            run["overrun_s"] = max(
                0.0, teacher_s + run["training_s"] + data["common_initialization_s"] - 8
            )
            run["total_at_1000_s"] = run["offline_s"] + 1000 * run["online_s_per_query"]
            runs.append(run)
    data["runs"] = runs
    baselines = baseline_experiment(arrays)
    data["baselines"] = baselines
    data["adoption"] = adoption(runs, baselines)
    data["hardware"] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "threads": 1,
        "device": "cpu",
        "timing": "observed perf_counter; not a portable performance gate",
    }
    data["teacher_generation_s"] = teacher_s
    check_record(data, arrays, fresh=True)
    np.savez_compressed(HERE / "reference.npz", **arrays)
    (HERE / "reference.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("RB-F05 generated; all independent numerical/array checks PASS", flush=True)


def main():
    """Generate or validate cached evidence without rerunning expensive learning."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        data = json.loads((HERE / "reference.json").read_text())
        with np.load(HERE / "reference.npz", allow_pickle=False) as source:
            arrays = {key: source[key] for key in source.files}
        check_record(data, arrays, fresh=True)
        print("RB-F05 cached + fresh independent checks PASS")
    else:
        generate()


if __name__ == "__main__":
    main()
