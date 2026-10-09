"""Precision/teacher pilot for a *discretely* monitored up-and-out call.

This pilot freezes no main-study tolerance or training budget. It retains
quadrature refinements, independent PDE grids and IID teacher samples so that
the numerical summaries can be recomputed without trusting a saved PASS flag.
The full pilot is deliberately separate from the small smoke configuration.
"""

from __future__ import annotations

import importlib.util
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.special import ndtr


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Use the teacher in this checkout, even when a shared workspace venv has
# already imported the main checkout's public hullkit package.
teacher = _load_module(
    "discrete_barrier_pilot_teacher",
    Path(__file__).resolve().parents[3] / "hullkit/src/hullkit/_discrete_barrier_teachers.py",
)

_CONTRACT = {"strike": 100.0, "barrier": 120.0, "rate": 0.03, "volatility": 0.2}
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
_PRICES = {"raw_price", "conditioned_price", "oss_price"}
_UNBIASED = {
    "raw_price",
    "raw_delta",
    "conditioned_price",
    "conditioned_delta",
    "oss_price",
    "oss_delta",
}


def _references():
    return _load_module(
        "discrete_barrier_independent_reference", Path(__file__).with_name("reference_methods.py")
    )


def pilot_config(*, smoke=False):
    """Return explicit axes; the smoke result cannot count as a full pilot."""
    config = {
        "spots": [80.0, 100.0, 115.0, 119.0],
        "maturities": [0.25, 1.0, 2.0],
        "monitoring": 12,
        "gl_orders": [32, 64, 128, 256],
        "tail_sigma": [10.0, 12.0],
        "pde_space": [1200, 2400, 4800],
        "pde_time": [64, 128, 256],
        "pde_fixed_space": 4800,
        "pde_fixed_time": 128,
        "pde_domain": [1.0, 1.5, 2.0],
        "pde_base_domain": 1.5,
        "domain_dx": 0.000625,
        "barrier_phases": [0.0, 0.5],
        "bump_widths": [0.001, 0.0005],
        "mc_paths": 32768,
        "pilot_seed": 6017,
        "frequency_spots": [100.0, 119.0],
        "frequency_monitoring": [1, 4, 12, 48],
        "frequency_maturity": 1.0,
    }
    if smoke:
        config.update(
            spots=[100.0, 119.0],
            maturities=[0.25],
            gl_orders=[16, 32, 64],
            pde_space=[80, 160],
            pde_time=[4, 8],
            pde_fixed_space=160,
            pde_fixed_time=8,
            pde_domain=[1.0, 1.5],
            domain_dx=3.0 / 160,
            mc_paths=2048,
            frequency_spots=[100.0],
            frequency_monitoring=[1, 12],
        )
    return config


def _pde_settings(config):
    rows, groups = [], {}

    def add(group, values):
        indices = []
        for value in values:
            value = tuple(value)
            if value not in rows:
                rows.append(value)
            indices.append(rows.index(value))
        groups[group] = indices

    n, steps, width = config["pde_fixed_space"], config["pde_fixed_time"], config["pde_base_domain"]
    add("space", [(v, steps, width, 0.5) for v in config["pde_space"]])
    add("time", [(n, v, width, 0.5) for v in config["pde_time"]])
    # Keep dx fixed, rather than changing domain and spatial resolution together.
    add(
        "domain",
        [(2 * round(v / config["domain_dx"]), steps, v, 0.5) for v in config["pde_domain"]],
    )
    add("phase", [(n, steps, width, v) for v in config["barrier_phases"]])
    return np.asarray(rows, dtype=float), groups


def _pde_query(x_grid, continuation, spots, bumps):
    spline = CubicSpline(x_grid, continuation, extrapolate=False)
    price = spline(np.log(spots))
    differences = [
        (spline(np.log(spots + bump)) - spline(np.log(spots - bump))) / (2 * bump) for bump in bumps
    ]
    return np.column_stack((price, *differences, spline(np.log(spots), 1) / spots))


def _gl_cases(inputs, orders, tails, monitoring):
    values = np.empty((len(inputs), len(tails), len(orders), 3))
    bounds = np.empty_like(values)
    lower, mass = np.empty(values.shape[:-1]), np.empty(values.shape[:-1])
    for i, (spot, maturity) in enumerate(inputs):
        for j, tail in enumerate(tails):
            for k, order in enumerate(orders):
                result = teacher.markov_reference(
                    spot,
                    maturity,
                    monitoring=int(monitoring[i]),
                    order=int(order),
                    tail_sigma=tail,
                    **_CONTRACT,
                )
                values[i, j, k] = [result[v] for v in ("price", "delta", "naive_pw_mean")]
                bounds[i, j, k] = [
                    result[v]
                    for v in ("tail_probability_bound", "tail_price_bound", "tail_delta_bound")
                ]
                lower[i, j, k], mass[i, j, k] = result["log_lower"], result["row_mass_max"]
    return values, bounds, lower, mass


def _mc_cases(arrays, name, inputs, monitoring, normal_rng, uniform_rng, paths):
    for i, ((spot, maturity), monitors) in enumerate(zip(inputs, monitoring, strict=True)):
        prefix = f"{name}__{i}"
        z = normal_rng.standard_normal((paths, int(monitors)))
        # RNG draws almost surely avoid endpoints; an exact zero is replaced by
        # the closest interior float, retaining the actual uniforms afterwards.
        uniform = uniform_rng.uniform(size=z.shape)
        uniform = np.maximum(uniform, np.nextafter(0.0, 1.0))
        raw = teacher.samples(spot, maturity, z, **_CONTRACT)
        oss = teacher.one_step_survival(spot, maturity, uniform, **_CONTRACT)
        arrays[f"normal__{prefix}"] = z
        arrays[f"uniform__{prefix}"] = uniform
        arrays[f"survival__{prefix}"] = raw["survival"]
        arrays[f"oss_valid__{prefix}"] = oss["valid"]
        arrays[f"oss_weight__{prefix}"] = oss["survival_weight"]
        for flag in (
            "probability_underflow",
            "quantile_underflow",
            "weight_underflow",
            "numerical_failure",
        ):
            arrays[f"oss_{flag}__{prefix}"] = oss[flag]
        if monitors == 1:
            exact = teacher.one_step(spot, maturity, **_CONTRACT)
            conditioned_price = np.full(paths, exact["price"])
            conditioned_delta = np.full(paths, exact["delta"])
            conditioned_pw = conditioned_delta.copy()
        else:
            conditioned_price = raw["last_conditional"]
            conditioned_delta = raw["last_conditional_lrm"]
            conditioned_pw = raw["last_conditional_pw"]
        samples = (
            raw["payoff"],
            raw["lrm"],
            conditioned_price,
            conditioned_delta,
            raw["naive_pw"],
            conditioned_pw,
            oss["payoff"],
            oss["delta"],
        )
        for method, value in zip(_METHODS, samples, strict=True):
            arrays[f"samples__{prefix}__{method}"] = value


def run_pilot(*, smoke=False):
    """Compute a reproducible pilot, not the main DML study or its acceptance."""
    config, refs = pilot_config(smoke=smoke), _references()
    inputs = np.asarray([(s, t) for t in config["maturities"] for s in config["spots"]])
    monitoring = np.full(len(inputs), config["monitoring"], dtype=int)
    arrays = {
        "inputs": inputs,
        "monitoring": monitoring,
        "gl_orders": np.asarray(config["gl_orders"]),
        "tail_sigma": np.asarray(config["tail_sigma"]),
    }
    gl = _gl_cases(inputs, arrays["gl_orders"], arrays["tail_sigma"], monitoring)
    for key, value in zip(
        ("gl_values", "gl_tail_bounds", "gl_log_lower", "gl_row_mass_max"), gl, strict=True
    ):
        arrays[key] = value
    settings, groups = _pde_settings(config)
    arrays["pde_settings"] = settings
    arrays["pde_values"] = np.empty((len(inputs), len(settings), 4))
    arrays["pde_minimum_unclipped"] = np.empty((len(inputs), len(settings)))
    for ti, maturity in enumerate(config["maturities"]):
        indices = np.flatnonzero(inputs[:, 1] == maturity)
        for j, (space, steps, width, phase) in enumerate(settings):
            result = refs.pde_reference(
                inputs[indices, 0],
                maturity,
                monitors=config["monitoring"],
                space_nodes=int(space),
                steps_per_monitor=int(steps),
                log_half_width=width,
                barrier_phase=phase,
                bump=config["bump_widths"][0],
            )
            arrays[f"pde_x__{ti}__{j}"] = result["x_grid"]
            arrays[f"pde_grid__{ti}__{j}"] = result["continuation_grid"]
            arrays["pde_values"][indices, j] = _pde_query(
                result["x_grid"],
                result["continuation_grid"],
                inputs[indices, 0],
                config["bump_widths"],
            )
            arrays["pde_minimum_unclipped"][indices, j] = result["metadata"][
                "minimum_unclipped_value"
            ]
    arrays["m1_cdf"], arrays["m1_integral"] = np.empty((len(inputs), 3)), np.empty((len(inputs), 6))
    for i, (spot, maturity) in enumerate(inputs):
        cdf = teacher.one_step(spot, maturity, **_CONTRACT)
        density = refs.one_monitor_integral(spot, maturity, bump=config["bump_widths"][0])
        arrays["m1_cdf"][i] = [cdf[v] for v in ("price", "delta", "naive_pw_mean")]
        arrays["m1_integral"][i] = [
            density[v]
            for v in (
                "price",
                "delta",
                "delta_coarse",
                "quadrature_price_error",
                "quadrature_delta_error",
                "delta_bump_difference",
            )
        ]
    frequency = np.asarray(
        [
            (s, config["frequency_maturity"], m)
            for s in config["frequency_spots"]
            for m in config["frequency_monitoring"]
        ]
    )
    arrays["frequency_inputs"] = frequency
    frequency_gl = _gl_cases(
        frequency[:, :2], arrays["gl_orders"][-2:], arrays["tail_sigma"], frequency[:, 2]
    )
    for key, value in zip(
        (
            "frequency_gl_values",
            "frequency_tail_bounds",
            "frequency_log_lower",
            "frequency_row_mass_max",
        ),
        frequency_gl,
        strict=True,
    ):
        arrays[key] = value
    seeds = np.random.SeedSequence(config["pilot_seed"]).spawn(4)
    _mc_cases(
        arrays,
        "main",
        inputs,
        monitoring,
        np.random.default_rng(seeds[0]),
        np.random.default_rng(seeds[1]),
        config["mc_paths"],
    )
    _mc_cases(
        arrays,
        "frequency",
        frequency[:, :2],
        frequency[:, 2],
        np.random.default_rng(seeds[2]),
        np.random.default_rng(seeds[3]),
        config["mc_paths"],
    )
    record = {
        "schema": "rbf05-discrete-pilot-v1",
        "mode": "smoke" if smoke else "full_pilot",
        "eligible_for_main_freeze": not smoke,
        "main_precision_frozen": False,
        "contract": dict(
            _CONTRACT,
            dividend_yield=0.0,
            rebate=0.0,
            monitoring="0,T/m,...,T; S>=H knocks out",
            greek="spot Delta; K,H,T,m fixed",
        ),
        "config": config,
        "pde_groups": groups,
        "rng": {
            "entropy": config["pilot_seed"],
            "spawn_keys": [list(s.spawn_key) for s in seeds],
            "order": [
                "main normal",
                "main OSS uniform",
                "frequency normal",
                "frequency OSS uniform",
            ],
            "usage": "independent pilot streams; not main training/evaluation streams",
        },
        "array_shapes": {key: list(value.shape) for key, value in arrays.items()},
    }
    record["summary"] = _summary(arrays, config, groups)
    return record, arrays


def _difference(a, b):
    return {"price": float(abs(a[0] - b[0])), "delta": float(abs(a[1] - b[1]))}


def _mean_se(values):
    return {"mean": float(values.mean()), "se": float(values.std(ddof=1) / np.sqrt(values.size))}


def _mc_summary(arrays, name, inputs, monitoring, reference, errors):
    cases, controls = (
        [],
        {
            v: {"status": "biased_control", "outside_six_se_count": 0, "case_count": 0}
            for v in ("naive_pw", "last_conditional_pw")
        },
    )
    for i, ((spot, maturity), monitors) in enumerate(zip(inputs, monitoring, strict=True)):
        prefix = f"{name}__{i}"
        valid = arrays[f"oss_valid__{prefix}"]
        methods = {}
        for method in _METHODS:
            values = arrays[f"samples__{prefix}__{method}"]
            if monitors == 1 and method in (
                "conditioned_price",
                "conditioned_delta",
                "last_conditional_pw",
            ):
                # Exact conditioning integrates the sole increment completely.
                # A constant analytic value has no IID MC SE or 6-SE test.
                column = 0 if method == "conditioned_price" else 1
                result = {
                    "mean": float(values[0]),
                    "se": None,
                    "status": "analytic_reference",
                    "sampling_status": "not_MC",
                    "reference_comparison": None,
                    "abs_reference_difference": float(abs(values[0] - reference[i, column])),
                }
            elif method.startswith("oss_") and not valid.all():
                # Excluding unsupported paths would change the estimator.
                result = {
                    "mean": None,
                    "se": None,
                    "status": "unsupported_paths",
                    "reference_comparison": None,
                }
            else:
                result = _mean_se(values)
                column = 0 if method in _PRICES else 1
                difference = abs(result["mean"] - reference[i, column])
                tolerance = 6 * result["se"] + errors[i, column]
                result.update(
                    abs_reference_difference=float(difference),
                    six_se_plus_oracle_error=float(tolerance),
                    reference_comparison=bool(difference <= tolerance),
                )
                result.update(
                    zero_sample_se=bool(result["se"] == 0),
                    nonzero_sample_count=int(np.count_nonzero(values)),
                    sampling_status="zero_sample_variance" if result["se"] == 0 else "iid_samples",
                )
                result["status"] = "unbiased_teacher" if method in _UNBIASED else "biased_control"
                if method in controls and (method == "naive_pw" or monitors >= 2):
                    controls[method]["case_count"] += 1
                    controls[method]["outside_six_se_count"] += int(difference > tolerance)
            methods[method] = result
        cases.append(
            {
                "spot": float(spot),
                "maturity": float(maturity),
                "monitoring": int(monitors),
                "first_score_second_moment": float(
                    monitors / (spot**2 * _CONTRACT["volatility"] ** 2 * maturity)
                ),
                "methods": methods,
                "survival_count": int(np.count_nonzero(arrays[f"survival__{prefix}"])),
                "positive_payoff_count": int(
                    np.count_nonzero(arrays[f"samples__{prefix}__raw_price"] > 0)
                ),
                "oss_valid_count": int(np.count_nonzero(valid)),
                "oss_positive_payoff_count": int(
                    np.count_nonzero(valid & (arrays[f"samples__{prefix}__oss_price"] > 0))
                ),
                "oss_survival_probability_estimate": _mean_se(arrays[f"oss_weight__{prefix}"])
                if valid.all()
                else None,
                "oss_failures": {
                    flag: int(np.count_nonzero(arrays[f"oss_{flag}__{prefix}"]))
                    for flag in (
                        "probability_underflow",
                        "quantile_underflow",
                        "weight_underflow",
                        "numerical_failure",
                    )
                },
            }
        )
    return {
        "cases": cases,
        "negative_controls": controls,
        "standard_error": "IID path sample standard deviation, ddof=1, divided by sqrt(paths)",
        "comparison": "6 SE plus observed GL refinement difference and truncation bound; diagnostic, not confidence certification",
        "oss_survival": "mean proposal survival_weight estimates original-contract survival; proposal survival count is not used",
    }


def _summary(arrays, config, groups):
    inputs, gl, pde = arrays["inputs"], arrays["gl_values"], arrays["pde_values"]
    errors = np.abs(gl[:, -1, -1, :2] - gl[:, -1, -2, :2]) + arrays["gl_tail_bounds"][:, -1, -1, 1:]
    reference = gl[:, -1, -1, :2]
    refinements = []
    for i, (spot, maturity) in enumerate(inputs):
        row = {
            "spot": float(spot),
            "maturity": float(maturity),
            "gl_adjacent": [
                _difference(gl[i, -1, j], gl[i, -1, j + 1]) for j in range(gl.shape[2] - 1)
            ],
            "gl_tail_10_vs_12": _difference(gl[i, 0, -1], gl[i, -1, -1]),
            "pde_groups": {},
            "delta_bump_vs_spline": [],
        }
        orders = config["gl_orders"]
        if 64 in orders and 128 in orders and 256 in orders:
            row["gl64_vs128"] = _difference(
                gl[i, -1, orders.index(64)], gl[i, -1, orders.index(128)]
            )
            row["gl64_vs256"] = _difference(
                gl[i, -1, orders.index(64)], gl[i, -1, orders.index(256)]
            )
        for group, indices in groups.items():
            row["pde_groups"][group] = [
                {
                    "price": float(abs(pde[i, a, 0] - pde[i, b, 0])),
                    "delta": float(abs(pde[i, a, 2] - pde[i, b, 2])),
                }
                for a, b in pairwise(indices)
            ]
        fine = groups["time"][-1]
        row["independent_pde_vs_gl"] = _difference(pde[i, fine, [0, 2]], reference[i])
        for value in pde[i]:
            row["delta_bump_vs_spline"].append(
                {
                    "bump_001": float(abs(value[1] - value[3])),
                    "bump_0005": float(abs(value[2] - value[3])),
                    "bump_difference": float(abs(value[1] - value[2])),
                }
            )
        refinements.append(row)
    freeze_checks = {
        "gl64_vs128_and256": None,
        "pde_finest_vs_gl": all(
            r["independent_pde_vs_gl"]["price"] < 5e-4
            and r["independent_pde_vs_gl"]["delta"] < 2e-4
            for r in refinements
        ),
    }
    if all("gl64_vs128" in row for row in refinements):
        freeze_checks["gl64_vs128_and256"] = all(
            row[key]["price"] < 1e-7 and row[key]["delta"] < 1e-8
            for row in refinements
            for key in ("gl64_vs128", "gl64_vs256")
        )
    if config["mc_paths"] == 2048:
        freeze_checks = {key: None for key in freeze_checks}
    freq = arrays["frequency_inputs"]
    fgl = arrays["frequency_gl_values"]
    ferr = (
        np.abs(fgl[:, -1, -1, :2] - fgl[:, -1, -2, :2])
        + arrays["frequency_tail_bounds"][:, -1, -1, 1:]
    )
    return {
        "convergence": refinements,
        "precision_proposal": {
            "status": "requires_full_pilot_review_before_freeze",
            "checks": freeze_checks,
            "gl_price_tolerance": 1e-7,
            "gl_delta_tolerance": 1e-8,
            "pde_price_tolerance": 5e-4,
            "pde_delta_tolerance": 2e-4,
            "short_maturity_case_indices": np.flatnonzero(inputs[:, 1] == 0.25).tolist(),
        },
        "tail": {
            "max_probability_bound": float(arrays["gl_tail_bounds"][..., 0].max()),
            "max_price_bound": float(arrays["gl_tail_bounds"][..., 1].max()),
            "max_delta_bound": float(arrays["gl_tail_bounds"][..., 2].max()),
            "price_bound_method": "discounted payoff cap times lower-tail union probability",
            "delta_bound_method": "Cauchy-Schwarz with first-transition score",
            "scope": "truncation only; excludes quadrature/grid error",
        },
        "m1": {
            "max_price_difference": float(
                np.max(np.abs(arrays["m1_cdf"][:, 0] - arrays["m1_integral"][:, 0]))
            ),
            "max_delta_difference": float(
                np.max(np.abs(arrays["m1_cdf"][:, 1] - arrays["m1_integral"][:, 1]))
            ),
            "max_bump_difference": float(arrays["m1_integral"][:, 5].max()),
            "naive_pw_missing_boundary_term": (
                arrays["m1_cdf"][:, 2] - arrays["m1_cdf"][:, 1]
            ).tolist(),
        },
        "mc": _mc_summary(arrays, "main", inputs, arrays["monitoring"], reference, errors),
        "frequency": _mc_summary(
            arrays, "frequency", freq[:, :2], freq[:, 2], fgl[:, -1, -1, :2], ferr
        ),
        "pde_minimum_unclipped_value": float(arrays["pde_minimum_unclipped"].min()),
        "price_cap": (20.0 * np.exp(-0.03 * inputs[:, 1])).tolist(),
    }


def _close(actual, expected, name, *, atol=1e-11):
    if np.shape(actual) != np.shape(expected) or not np.allclose(
        actual, expected, rtol=1e-10, atol=atol, equal_nan=True
    ):
        raise ValueError(f"{name}: saved evidence differs from recomputation")


def _compare_summary(actual, expected, name="summary"):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{name}: summary keys differ")
        for key in expected:
            _compare_summary(actual[key], expected[key], f"{name}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{name}: summary length differs")
        for i, value in enumerate(expected):
            _compare_summary(actual[i], value, f"{name}[{i}]")
    elif isinstance(expected, float):
        _close(actual, expected, name)
    elif actual != expected:
        raise ValueError(f"{name}: saved summary differs from recomputation")


def _check_tails(inputs, monitoring, lower, saved):
    rate, sigma = _CONTRACT["rate"], _CONTRACT["volatility"]
    for i, ((spot, maturity), monitors) in enumerate(zip(inputs, monitoring, strict=True)):
        times = np.linspace(0, maturity, int(monitors) + 1)[1:]
        scores = (lower[i, ..., None] - np.log(spot) - (rate - sigma**2 / 2) * times) / (
            sigma * np.sqrt(times)
        )
        probability = np.minimum(1, ndtr(scores).sum(axis=-1))
        cap, width = 20 * np.exp(-rate * maturity), sigma * np.sqrt(maturity / monitors)
        expected = np.stack(
            (probability, cap * probability, cap * np.sqrt(probability) / (spot * width)), axis=-1
        )
        # Tail probabilities are much smaller than the price/Greek absolute
        # comparison tolerance. Relative comparison prevents zeroing a bound.
        _close(saved[i], expected, "tail probability/price/Delta units", atol=0)


def check_pilot(record, arrays, *, fresh=False):
    """Recompute from retained evidence; optional fresh calculations replay RNGs.

    Precision checks may fail legitimately in a pilot; that is a recorded
    finding, not a reason to replace a tolerance with a saved success flag.
    This function rejects inconsistent/missing evidence and returns newly
    computed diagnostics. Fresh mode also reruns the numerical references and
    path teachers without fitting any model.
    """
    if record.get("schema") != "rbf05-discrete-pilot-v1" or record.get("mode") not in (
        "smoke",
        "full_pilot",
    ):
        raise ValueError("unknown pilot schema or mode")
    smoke = record["mode"] == "smoke"
    config = pilot_config(smoke=smoke)
    if (
        record.get("config") != config
        or record.get("eligible_for_main_freeze") != (not smoke)
        or record.get("main_precision_frozen") is not False
    ):
        raise ValueError("pilot axes/freeze status differ from fixed protocol")
    expected_contract = dict(
        _CONTRACT,
        dividend_yield=0.0,
        rebate=0.0,
        monitoring="0,T/m,...,T; S>=H knocks out",
        greek="spot Delta; K,H,T,m fixed",
    )
    if record.get("contract") != expected_contract:
        raise ValueError("saved contract differs from fixed discrete-monitoring contract")
    rng = record.get("rng", {})
    if rng.get("entropy") != config["pilot_seed"] or rng.get("spawn_keys") != [[0], [1], [2], [3]]:
        raise ValueError("pilot RNG provenance differs from independent stream protocol")
    if set(arrays) != set(record.get("array_shapes", {})):
        raise ValueError("missing or unexpected pilot arrays")
    for name, value in arrays.items():
        value = np.asarray(value)
        if list(value.shape) != record["array_shapes"][name]:
            raise ValueError(f"{name}: shape mismatch")
        if not np.isfinite(value).all():
            if name.startswith("samples__") and name.endswith(("__oss_price", "__oss_delta")):
                prefix = name.removeprefix("samples__").rsplit("__", 1)[0]
                valid = arrays[f"oss_valid__{prefix}"]
                if not np.isfinite(value[valid]).all() or not np.isnan(value[~valid]).all():
                    raise ValueError(f"{name}: invalid finite/unsupported OSS evidence")
            else:
                raise ValueError(f"{name}: finite evidence required")
    expected_inputs = np.asarray([(s, t) for t in config["maturities"] for s in config["spots"]])
    _close(arrays["inputs"], expected_inputs, "inputs")
    _close(arrays["monitoring"], np.full(len(expected_inputs), 12), "monitoring")
    _close(arrays["gl_orders"], config["gl_orders"], "GL orders")
    _close(arrays["tail_sigma"], config["tail_sigma"], "tail sigma")
    settings, groups = _pde_settings(config)
    _close(arrays["pde_settings"], settings, "PDE settings")
    if record.get("pde_groups") != groups:
        raise ValueError("PDE convergence groups differ")
    for ti, maturity in enumerate(config["maturities"]):
        indices = np.flatnonzero(arrays["inputs"][:, 1] == maturity)
        for j in range(len(settings)):
            value = _pde_query(
                arrays[f"pde_x__{ti}__{j}"],
                arrays[f"pde_grid__{ti}__{j}"],
                arrays["inputs"][indices, 0],
                config["bump_widths"],
            )
            _close(arrays["pde_values"][indices, j], value, "PDE price/bump/spline")
    _check_tails(
        arrays["inputs"], arrays["monitoring"], arrays["gl_log_lower"], arrays["gl_tail_bounds"]
    )
    frequency = arrays["frequency_inputs"]
    expected_frequency = np.asarray(
        [
            (s, config["frequency_maturity"], m)
            for s in config["frequency_spots"]
            for m in config["frequency_monitoring"]
        ]
    )
    _close(frequency, expected_frequency, "frequency axes")
    _check_tails(
        frequency[:, :2],
        frequency[:, 2],
        arrays["frequency_log_lower"],
        arrays["frequency_tail_bounds"],
    )
    seeds = np.random.SeedSequence(config["pilot_seed"]).spawn(4)
    for cohort, _inputs, monitoring, normal_seed, uniform_seed in (
        ("main", arrays["inputs"], arrays["monitoring"], seeds[0], seeds[1]),
        ("frequency", frequency[:, :2], frequency[:, 2], seeds[2], seeds[3]),
    ):
        normal_rng, uniform_rng = (
            np.random.default_rng(normal_seed),
            np.random.default_rng(uniform_seed),
        )
        for i, monitors in enumerate(monitoring):
            shape = config["mc_paths"], int(monitors)
            normal = normal_rng.standard_normal(shape)
            uniform = np.maximum(uniform_rng.uniform(size=shape), np.nextafter(0.0, 1.0))
            _close(arrays[f"normal__{cohort}__{i}"], normal, "independent normal stream draws")
            _close(
                arrays[f"uniform__{cohort}__{i}"], uniform, "independent OSS uniform stream draws"
            )
    for cohort, inputs, monitoring in (
        ("main", arrays["inputs"], arrays["monitoring"]),
        ("frequency", frequency[:, :2], frequency[:, 2]),
    ):
        for i, ((spot, maturity), monitors) in enumerate(zip(inputs, monitoring, strict=True)):
            prefix, size = f"{cohort}__{i}", config["mc_paths"]
            z, u = arrays[f"normal__{prefix}"], arrays[f"uniform__{prefix}"]
            if (
                z.shape != (size, int(monitors))
                or u.shape != z.shape
                or np.any((u <= 0) | (u >= 1))
            ):
                raise ValueError(
                    "teacher draws must have fixed path/monitor axes and interior uniforms"
                )
            for method in _METHODS:
                if arrays[f"samples__{prefix}__{method}"].shape != (size,):
                    raise ValueError("teacher samples must have one value per IID path")
            raw = teacher.samples(spot, maturity, z, **_CONTRACT)
            oss = teacher.one_step_survival(spot, maturity, u, **_CONTRACT)
            _close(arrays[f"survival__{prefix}"], raw["survival"], "raw survival")
            _close(arrays[f"samples__{prefix}__raw_price"], raw["payoff"], "raw price samples")
            _close(arrays[f"samples__{prefix}__raw_delta"], raw["lrm"], "raw score Delta samples")
            _close(arrays[f"samples__{prefix}__naive_pw"], raw["naive_pw"], "naive PW samples")
            if monitors == 1:
                exact = teacher.one_step(spot, maturity, **_CONTRACT)
                conditioned = [np.full(size, exact[v]) for v in ("price", "delta", "delta")]
            else:
                conditioned = [
                    raw[v]
                    for v in ("last_conditional", "last_conditional_lrm", "last_conditional_pw")
                ]
            for method, expected in zip(
                ("conditioned_price", "conditioned_delta", "last_conditional_pw"),
                conditioned,
                strict=True,
            ):
                _close(arrays[f"samples__{prefix}__{method}"], expected, f"{method} path samples")
            for method, key in (("oss_price", "payoff"), ("oss_delta", "delta")):
                _close(arrays[f"samples__{prefix}__{method}"], oss[key], f"{method} path samples")
            _close(arrays[f"oss_valid__{prefix}"], oss["valid"], "OSS valid support")
            _close(
                arrays[f"oss_weight__{prefix}"],
                oss["survival_weight"],
                "OSS survival probability weight",
            )
            for flag in (
                "probability_underflow",
                "quantile_underflow",
                "weight_underflow",
                "numerical_failure",
            ):
                _close(arrays[f"oss_{flag}__{prefix}"], oss[flag], f"OSS {flag}")
    summary = _summary(arrays, config, groups)
    _compare_summary(record.get("summary"), summary)
    if fresh:
        replay_record, replay_arrays = run_pilot(smoke=smoke)
        if set(replay_arrays) != set(arrays):
            raise ValueError("fresh pilot array schema differs")
        for key in arrays:
            _close(arrays[key], replay_arrays[key], f"fresh {key}")
        _compare_summary(record["summary"], replay_record["summary"])
    return summary
