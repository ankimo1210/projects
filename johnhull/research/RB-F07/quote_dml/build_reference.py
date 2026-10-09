"""Controlled synthetic quote-DML protocol, grouped inputs and offline experiment.

The default replay path never imports a learner or torch. Learning is an
explicit offline action; every market is calibrated once for its eight rows.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import subprocess
import sys
from functools import cache
from pathlib import Path
from time import perf_counter

import numpy as np
from hullkit import _quote_dml_hedging as hedging
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parent


def load_protocol(path=HERE / "protocol.json"):
    """Read the frozen schema, quote units, supported curve and fit design."""
    config = json.loads(Path(path).read_text())
    curve, training = config["curve"], config["training"]
    fixed_training = {
        "modes": ["q_price", "theta_price", "theta_dml", "theta_quote_metric", "q_dml"],
        "sizes": [512, 2048],
        "seeds": [11, 29, 47],
        "hidden": [64, 64],
        "dtype": "float64",
        "device": "cpu",
        "threads": 1,
        "lr": 0.001,
        "batch": 256,
        "updates": 512,
        "budget_s": 120,
        "lambda": 1,
        "rms_floor": 1e-8,
    }
    if (
        config["schema_version"] != 1
        or curve["quote_unit"] != "rate_decimal"
        or curve["interpolation"] != "zero_linear"
        or curve["quote_kinds"] != list(teacher.QUOTE_KINDS)
        or curve["quote_times"] != [list(times) for times in teacher.QUOTE_TIMES]
        or curve["pillar_times"] != [0.5, 1, 2, 3, 5]
        or any(training.get(key) != value for key, value in fixed_training.items())
        or any(
            config["contract"].get(key) != value
            for key, value in {"strike": 100, "sigma": 0.2, "payout": 1}.items()
        )
        or config["sampling"]["contracts_per_market"] != 8
    ):
        raise ValueError("unsupported protocol schema, curve, units or fit design")
    return config


def make_dataset(protocol, split):
    """Draw disjoint market groups without silently replacing failed curves.

    Rate gradients are per annual decimal quote unit; rows are price payout
    one. Group IDs include the split, allowing market-cluster uncertainty.
    """
    split_id = {"train": 0, "validation": 1, "test": 2}[split]
    sampling, curve, contract = protocol["sampling"], protocol["curve"], protocol["contract"]
    markets, count = sampling["markets"][split], sampling["contracts_per_market"]
    rng = np.random.default_rng(np.random.SeedSequence([sampling["seed"], split_id]))
    n = markets * count
    data = {
        key: np.full(shape, np.nan)
        for key, shape in {
            "x_quote": (n, 7),
            "x_theta": (n, 7),
            "price": (n,),
            "g_quote": (n, 6),
            "g_theta": (n, 6),
            "A": (n, 5, 5),
            "a_quote": (n, 5),
            "discount": (n,),
            "integrated_rate": (n,),
            "rank": (n,),
            "amplification": (n,),
            "iterations": (n,),
            "scaled_residual": (n,),
        }.items()
    }
    data["market_id"] = np.repeat(split_id * 100000 + np.arange(markets), count)
    data["contract_id"] = np.tile(np.arange(count), markets)
    data["failure_reason"] = np.full(n, "", dtype="U512")
    data["calibration_count"] = np.array(markets)
    data["market_generation_s"] = np.zeros(markets)
    data["market_calibration_s"] = np.zeros(markets)
    for index in range(markets):
        curve_started = perf_counter()
        rows = slice(index * count, (index + 1) * count)
        q = np.asarray(curve["base_quotes"]) + rng.uniform(
            -curve["halfwidth"], curve["halfwidth"], 5
        )
        if split == "test":
            terms = np.asarray(sampling["test_contracts"], dtype=float)
        else:
            spot = rng.uniform(*contract["spot_bounds"], count)
            maturity = np.exp(rng.uniform(*np.log(contract["maturity_bounds"]), count))
            terms = np.column_stack([spot, maturity])
        data["x_quote"][rows] = np.column_stack([np.tile(q, (count, 1)), terms])
        try:
            calibration_started = perf_counter()
            market = teacher.prepare_market(q)
            data["market_calibration_s"][index] = perf_counter() - calibration_started
            calibration = market.calibration
            data["x_theta"][rows] = np.column_stack([np.tile(calibration.zeros, (count, 1)), terms])
            data["A"][rows] = market.dz_dq
            data["rank"][rows] = np.linalg.matrix_rank(calibration.jacobian)
            data["amplification"][rows] = calibration.amplification
            data["iterations"][rows] = calibration.iterations
            data["scaled_residual"][rows] = calibration.scaled_residual_norm
            for offset, (spot, maturity) in enumerate(terms):
                exact = teacher.analytic(
                    market, spot, maturity, strike=contract["strike"], sigma=contract["sigma"]
                )
                for key in (
                    "price",
                    "g_quote",
                    "g_theta",
                    "a_quote",
                    "discount",
                    "integrated_rate",
                ):
                    data[key][index * count + offset] = exact[key]
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
            data["failure_reason"][rows] = f"{type(error).__name__}: {error}"
        data["market_generation_s"][index] = perf_counter() - curve_started
    return data


@cache
def component(name):
    spec = importlib.util.spec_from_file_location(f"quote_dml_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_prediction(exported, q, spot, maturity, protocol, *, context=None, market=None):
    """Apply domain/calibration/bounds checks, preserving raw and safe results."""
    return component("policy").safe_prediction(
        exported, q, spot, maturity, protocol, context=context, market=market
    )


def _prediction(exported, dataset):
    replay = component("replay")
    if exported["kind"] == "ridge":
        return replay.ridge_predict(exported, dataset)
    x = dataset["x_theta" if str(exported["mode"]).startswith("theta") else "x_quote"]
    return replay.nn_predict(exported, x, dataset["A"])


def _export(arrays, model_id, exported):
    for key, value in exported.items():
        arrays[f"weights__{model_id}__{key}"] = np.asarray(value)


def _restore(arrays, model_id):
    prefix = f"weights__{model_id}__"
    result = {key[len(prefix) :]: value for key, value in arrays.items() if key.startswith(prefix)}
    for key in ("kind", "mode", "differential"):
        if key in result:
            result[key] = result[key].item()
    return result


def _dataset(arrays, name):
    prefix = f"{name}_"
    return {key[len(prefix) :]: value for key, value in arrays.items() if key.startswith(prefix)}


def shocks(protocol):
    """Fixed signed curve and stock shocks, with no time or coupon reset."""
    labels, changes, spots = ["zero"], [np.zeros(5)], [0.0]
    patterns = [(f"bucket{i}", np.eye(5)[i]) for i in range(5)]
    patterns += [
        ("parallel", np.ones(5)),
        ("steepener", np.asarray(protocol["shocks"]["steepener"])),
    ]
    for width in protocol["shocks"]["quote_bp"]:
        for name, direction in patterns:
            for sign in (-1, 1):
                labels.append(f"{name}_{sign * width:+}bp")
                changes.append(sign * width * 1e-4 * direction)
                spots.append(0.0)
    for sign in (-1, 1):
        labels.append(f"spot_{sign:+}pct")
        changes.append(np.zeros(5))
        spots.append(sign * protocol["shocks"]["spot_fraction"])
        for rate_sign in (-1, 1):
            labels.append(
                f"combined_{sign:+}pct_{rate_sign * protocol['shocks']['combined_quote_bp']:+}bp"
            )
            changes.append(np.full(5, rate_sign * protocol["shocks"]["combined_quote_bp"] * 1e-4))
            spots.append(sign * protocol["shocks"]["spot_fraction"])
    return np.asarray(labels), np.asarray(changes), np.asarray(spots)


def _fixed_contract_arrays(test, protocol):
    reference = component("reference_methods")
    labels, dq, ds = shocks(protocol)
    n, m = len(test["price"]), len(labels)
    result = {
        "shock_labels": labels,
        "shock_dq": dq,
        "shock_spot_fraction": ds,
        "contract_quotes": test["x_quote"][:, :5].copy(),
        "test_B": np.empty((n, 6, 6)),
        "held_base": np.empty((n, 6)),
        "shock_held": np.empty((n, m, 6)),
        "shock_price": np.empty((n, m)),
        "cost_rate_bp": np.asarray(protocol["costs"]["rate_halfspread_bp"]),
        "cost_stock_bp": np.asarray(protocol["costs"]["stock_halfspread_bp"]),
    }
    notional = protocol["costs"]["notional"]
    for group in np.unique(test["market_id"]):
        rows = np.flatnonzero(test["market_id"] == group)
        q = test["x_quote"][rows[0], :5]
        markets = [teacher.prepare_market(q + change) for change in dq]
        b = reference.held_risk(q, 100.0, q, notional=notional)
        for row in rows:
            spot, maturity = test["x_quote"][row, 5:]
            result["test_B"][row] = b
            result["held_base"][row] = reference.held_prices(q, spot, q, notional=notional)
            for j, shifted in enumerate(markets):
                shifted_spot = spot * (1 + ds[j])
                result["shock_price"][row, j] = teacher.analytic(shifted, shifted_spot, maturity)[
                    "price"
                ]
                result["shock_held"][row, j] = hedging.held_prices(
                    shifted, shifted_spot, q, notional=notional
                )
    result["reference_h"] = np.stack(
        [hedging.solve_hedge(b, g) for b, g in zip(result["test_B"], test["g_quote"], strict=True)]
    )
    result["reference_residual"] = (
        result["shock_price"]
        - test["price"][:, None]
        + np.einsum(
            "ni,nji->nj", result["reference_h"], result["shock_held"] - result["held_base"][:, None]
        )
    )
    return result


def _hedge_predictions(arrays, model_id, prediction, scale, protocol):
    prefix = f"pred__{model_id}__"
    for key in ("price", "g_quote"):
        arrays[prefix + key] = prediction[key]
    h = np.stack(
        [
            hedging.solve_hedge(b, g)
            for b, g in zip(arrays["test_B"], prediction["g_quote"], strict=True)
        ]
    )
    arrays[prefix + "h"] = h
    arrays[prefix + "risk_scale"] = scale
    arrays[prefix + "residual"] = (
        arrays["shock_price"]
        - arrays["test_price"][:, None]
        + np.einsum("ni,nji->nj", h, arrays["shock_held"] - arrays["held_base"][:, None])
    )
    stock = arrays["test_x_quote"][:, 5] * abs(h[:, 0]) * 1e-4
    rates = (
        np.sum(abs(h[:, 1:] * np.diagonal(arrays["test_B"], axis1=1, axis2=2)[:, 1:]), axis=1)
        * 1e-4
    )
    arrays[prefix + "cost"] = (
        rates[:, None, None] * arrays["cost_rate_bp"][None, :, None]
        + stock[:, None, None] * arrays["cost_stock_bp"][None, None, :]
    )


def _policy_arrays(arrays, test, protocol):
    q = np.asarray(protocol["curve"]["base_quotes"])
    cases = [(q, 100.0, 1.5, {})]
    for direction in np.eye(5):
        for sign in (-1, 1):
            cases.append(
                (q + sign * protocol["ood"]["quote_bp"] * 1e-4 * direction, 100.0, 1.5, {})
            )
    cases.append((np.array([-0.001, -0.002, 0.0, 0.001, 0.005]), 100.0, 1.5, {}))
    cases += [(q, spot, 1.5, {}) for spot in protocol["ood"]["spots"]]
    cases += [(q, 100.0, maturity, {}) for maturity in protocol["ood"]["maturities"]]
    cases += [
        (q, 100.0, 1.5, {"strike": protocol["ood"]["strike"]}),
        (q, 100.0, 1.5, {"sigma": protocol["ood"]["sigma"]}),
        (q, 100.0, 1.5, {"pillar_times": [0.5, 1, 2, 4, 5]}),
        (q, 100.0, 1.5, {"quote_times": [[0.5], [0.5, 1], [1, 2], [1, 2, 3], [1, 5]]}),
        (q, 100.0, 1.5, {"interpolation": "log_df_linear"}),
        (q, 0.0, 1.5, {}),
    ]
    arrays["ood_x_quote"] = np.asarray(
        [np.r_[quote, spot, maturity] for quote, spot, maturity, _ in cases]
    )
    arrays["ood_context"] = np.asarray(
        [json.dumps(context, sort_keys=True) for _, _, _, context in cases]
    )
    markets = {
        int(group): teacher.prepare_market(
            test["x_quote"][np.flatnonzero(test["market_id"] == group)[0], :5]
        )
        for group in np.unique(test["market_id"])
    }
    for model_id in arrays["model_ids"]:
        exported = _restore(arrays, str(model_id))
        for name, inputs, contexts, cached_markets in (
            (
                "safe",
                test["x_quote"],
                [{}] * len(test["price"]),
                [markets[int(group)] for group in test["market_id"]],
            ),
            (
                "ood",
                arrays["ood_x_quote"],
                [json.loads(item) for item in arrays["ood_context"]],
                [None] * len(cases),
            ),
        ):
            prefix = f"{name}__{model_id}__"
            statuses, reasons, fallbacks = [], [], []
            values = {
                f"{kind}_{field}": np.full(
                    (len(inputs), 6) if field == "g_quote" else (len(inputs),), np.nan
                )
                for kind in ("raw", "safe")
                for field in ("price", "g_quote")
            }
            for i, (x, context, market) in enumerate(
                zip(inputs, contexts, cached_markets, strict=True)
            ):
                result = safe_prediction(
                    exported, x[:5], *x[5:], protocol, context=context, market=market
                )
                statuses.append(result["status"])
                reasons.append(result["reason"])
                fallbacks.append(result["fallback"])
                for kind in ("raw", "safe"):
                    if result[kind] is not None:
                        for field in ("price", "g_quote"):
                            values[f"{kind}_{field}"][i] = result[kind][field]
            arrays.update({prefix + key: value for key, value in values.items()})
            arrays[prefix + "status"] = np.asarray(statuses)
            arrays[prefix + "reason"] = np.asarray(reasons)
            arrays[prefix + "fallback"] = np.asarray(fallbacks)


def run_experiment(protocol, *, smoke=False):
    """Run explicit offline fits; smoke preserves all modes but uses two updates.

    Validation is diagnostic. Neither validation nor test selects seeds,
    checkpoints, normalization, network settings or a preferred method.
    """
    import torch

    from deep_hedge_price import _quote_dml as learner

    effective = copy.deepcopy(protocol)
    if smoke:
        effective["sampling"]["markets"] = {"train": 4, "validation": 2, "test": 2}
        effective["training"]["sizes"] = [16, 32]
        effective["training"]["updates"] = 2
        effective["bootstrap"]["repeats"] = 20
    started = perf_counter()
    splits = {name: make_dataset(effective, name) for name in ("train", "validation", "test")}
    teacher_s = perf_counter() - started
    arrays = {
        f"{name}_{key}": value for name, data in splits.items() for key, value in data.items()
    }
    if any(np.any(data["failure_reason"]) for data in splits.values()):
        return {
            "schema_version": 1,
            "experiment": "smoke" if smoke else "main",
            "protocol": effective,
            "fits": [],
            "complete_fits": False,
            "failure_reason": "calibration failed before fitting",
            "teacher_s": teacher_s,
        }, arrays
    arrays.update(_fixed_contract_arrays(splits["test"], effective))
    fits, model_ids = [], []
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        for size in effective["training"]["sizes"]:
            train_teacher_s = float(
                np.sum(
                    splits["train"]["market_generation_s"][
                        : size // effective["sampling"]["contracts_per_market"]
                    ]
                )
            )
            train = {
                key: value[:size] if value.ndim else value for key, value in splits["train"].items()
            }
            scale = np.maximum(np.sqrt(np.mean(train["g_quote"] ** 2, axis=0)), 1e-8)
            for mode in effective["training"]["modes"]:
                for seed in effective["training"]["seeds"]:
                    model_id = f"{mode}_n{size}_s{seed}"
                    fit = learner.fit_nn(
                        train,
                        mode=mode,
                        seed=seed,
                        updates=effective["training"]["updates"],
                        budget_s=effective["training"]["budget_s"],
                    )
                    export_start = perf_counter()
                    exported = learner.export_nn(fit)
                    export_s = perf_counter() - export_start
                    _export(arrays, model_id, exported)
                    prediction = learner.predict_nn(
                        fit,
                        splits["test"]["x_theta" if mode.startswith("theta") else "x_quote"],
                        splits["test"]["A"],
                    )
                    _hedge_predictions(arrays, model_id, prediction, scale, effective)
                    validation = learner.predict_nn(
                        fit,
                        splits["validation"]["x_theta" if mode.startswith("theta") else "x_quote"],
                        splits["validation"]["A"],
                    )
                    arrays[f"validation_pred__{model_id}__price"] = validation["price"]
                    arrays[f"validation_pred__{model_id}__g_quote"] = validation["g_quote"]
                    fits.append(
                        {
                            "id": model_id,
                            "kind": "nn",
                            **fit.stats,
                            "export_s": export_s,
                            "train_teacher_s": train_teacher_s,
                            "offline_s": train_teacher_s + fit.stats["elapsed_s"] + export_s,
                        }
                    )
                    model_ids.append(model_id)
            for differential in (False, True):
                model_id = f"ridge_{'dml' if differential else 'price'}_n{size}"
                fit_start = perf_counter()
                exported = learner.fit_ridge(train, differential=differential)
                elapsed = perf_counter() - fit_start
                _export(arrays, model_id, exported)
                _hedge_predictions(
                    arrays,
                    model_id,
                    learner.predict_ridge(exported, splits["test"]),
                    scale,
                    effective,
                )
                fits.append(
                    {
                        "id": model_id,
                        "kind": "ridge",
                        "elapsed_s": elapsed,
                        "train_teacher_s": train_teacher_s,
                        "offline_s": train_teacher_s + elapsed,
                        "budget_failure": False,
                    }
                )
                model_ids.append(model_id)
    except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError) as error:
        arrays["model_ids"] = np.asarray(model_ids)
        return {
            "schema_version": 1,
            "experiment": "smoke" if smoke else "main",
            "protocol": effective,
            "fits": fits,
            "complete_fits": False,
            "failure_reason": f"fit {model_id}: {type(error).__name__}: {error}",
            "teacher_s": teacher_s,
        }, arrays
    finally:
        torch.set_num_threads(old_threads)
    arrays["model_ids"] = np.asarray(model_ids)
    _policy_arrays(arrays, splits["test"], effective)
    arrays.update(component("diagnostics").make_diagnostics(effective, smoke=smoke))
    record = {
        "schema_version": 1,
        "experiment": "smoke" if smoke else "main",
        "protocol": effective,
        "fits": fits,
        "teacher_s": teacher_s,
        "total_fit_s": sum(fit["elapsed_s"] for fit in fits),
        "complete_fits": not any(fit["budget_failure"] for fit in fits),
        "checks": {},
        "metrics": component("replay").metrics(arrays, effective),
    }
    return record, arrays


def _close(got, expected, *, label, atol=1e-10, rtol=1e-9):
    np.testing.assert_allclose(got, expected, atol=atol, rtol=rtol, err_msg=label)


def _check_loading(record, arrays):
    loading = record["loading"]
    assert loading["repeats"] == 100 and loading["warmup"] == 3, "loading protocol"
    identifiers = list(map(str, arrays["model_ids"]))
    assert set(loading["model_decode"]) == set(identifiers), "loading model roster"
    observations = {"loading__full_npz": loading["full_npz"]}
    observations.update(
        {
            f"loading__decode__{identifier}": loading["model_decode"][identifier]
            for identifier in identifiers
        }
    )
    assert {key for key in arrays if key.startswith("loading__")} == set(observations), (
        "loading raw registry"
    )
    for key, saved in observations.items():
        raw = arrays[key]
        assert raw.shape == (100,) and np.isfinite(raw).all() and np.all(raw >= 0), (
            "loading raw observations"
        )
        _close(saved["median_s"], np.median(raw), label="loading median")
        _close(saved["p95_s"], np.quantile(raw, 0.95), label="loading p95")


def check_record(record, arrays, *, fresh=True):
    """Recompute weights, risks, coupons, hedge cash flows and metrics without fit."""
    config, reference = record["protocol"], component("reference_methods")
    expected_protocol = load_protocol()
    if record["experiment"] == "smoke":
        expected_protocol["sampling"]["markets"] = {"train": 4, "validation": 2, "test": 2}
        expected_protocol["training"]["sizes"] = [16, 32]
        expected_protocol["training"]["updates"] = 2
        expected_protocol["bootstrap"]["repeats"] = 20
    assert config == expected_protocol, "fixed experiment protocol"
    assert not record.get("failure_reason"), "incomplete experiment: recorded failure"
    component("diagnostics").check_diagnostics(arrays, config)
    roster = []
    for size in config["training"]["sizes"]:
        roster += [
            f"{mode}_n{size}_s{seed}"
            for mode in config["training"]["modes"]
            for seed in config["training"]["seeds"]
        ]
        roster += [f"ridge_{kind}_n{size}" for kind in ("price", "dml")]
    np.testing.assert_array_equal(arrays["model_ids"], roster, err_msg="fixed model roster")
    assert [fit["id"] for fit in record["fits"]] == roster, "fit roster"
    for fit in record["fits"]:
        identifier = fit["id"]
        method, size_seed = identifier.rsplit("_n", 1)
        size = int(size_seed.split("_s")[0])
        kind = "ridge" if method.startswith("ridge_") else "nn"
        assert fit["kind"] == kind, "fit kind must match model ID"
        exported = _restore(arrays, identifier)
        assert exported["kind"] == kind, "fit/export kind must match model ID"
        times = ["elapsed_s", "train_teacher_s", "offline_s"]
        if kind == "nn":
            seed = int(size_seed.split("_s")[1])
            assert fit["mode"] == exported["mode"] == method, "fit mode must match model ID"
            assert fit["seed"] == seed, "fit seed must match model ID"
            assert fit["budget_s"] == config["training"]["budget_s"], "fixed fit budget"
            assert fit["requested_updates"] == config["training"]["updates"], "fit update protocol"
            assert 0 <= fit["updates"] <= fit["requested_updates"], "fit update count"
            assert fit["batch_size"] == min(config["training"]["batch"], size), "fit batch size"
            assert fit["batch_seed"] == seed + 104729, "fit batch seed"
            assert fit["threads"] == config["training"]["threads"], "fit thread protocol"
            times += ["setup_s", "training_s", "export_s", "overrun_s"]
            complete = (
                fit["updates"] == fit["requested_updates"] and fit["elapsed_s"] <= fit["budget_s"]
            )
            assert fit["budget_failure"] == (not complete), "fit budget status"
            _close(
                fit["overrun_s"],
                max(0.0, fit["elapsed_s"] - fit["budget_s"]),
                label="fit budget overrun",
            )
            assert fit["elapsed_s"] + 1e-10 >= fit["setup_s"] + fit["training_s"], (
                "fit elapsed time includes setup and training"
            )
        else:
            assert bool(exported["differential"]) == (method == "ridge_dml"), "fit ridge mode"
            assert fit["budget_failure"] is False, "fit ridge completion"
        assert all(np.isfinite(fit[key]) and fit[key] >= 0 for key in times), "fit times"
        _close(
            fit["offline_s"],
            fit["train_teacher_s"] + fit["elapsed_s"] + (fit["export_s"] if kind == "nn" else 0.0),
            label="fit offline time",
        )
    _close(
        record["total_fit_s"],
        sum(fit["elapsed_s"] for fit in record["fits"]),
        label="total fit time",
    )
    assert record["complete_fits"] == (not any(fit["budget_failure"] for fit in record["fits"])), (
        "complete fits status"
    )
    labels, dq, ds = shocks(config)
    np.testing.assert_array_equal(arrays["shock_labels"], labels, err_msg="shock protocol labels")
    _close(arrays["shock_dq"], dq, label="shock protocol quotes")
    _close(arrays["shock_spot_fraction"], ds, label="shock protocol spot")
    for kind in ("rate", "stock"):
        _close(
            arrays[f"cost_{kind}_bp"],
            config["costs"][f"{kind}_halfspread_bp"],
            label="fee protocol",
        )
    for name in ("train", "validation", "test"):
        data = _dataset(arrays, name)
        nmarket, count = (
            config["sampling"]["markets"][name],
            config["sampling"]["contracts_per_market"],
        )
        split_id = {"train": 0, "validation": 1, "test": 2}[name]
        np.testing.assert_array_equal(
            data["market_id"],
            np.repeat(split_id * 100000 + np.arange(nmarket), count),
            err_msg="market split IDs",
        )
        np.testing.assert_array_equal(
            data["contract_id"], np.tile(np.arange(count), nmarket), err_msg="contract group IDs"
        )
        assert data["calibration_count"] == nmarket, "calibration count"
        assert not np.any(data["failure_reason"]), "recorded calibration failure"
        assert np.isfinite(data["discount"]).all() and np.all(data["discount"] > 0), (
            "positive finite discount"
        )
        _close(data["discount"], np.exp(-data["integrated_rate"]), label="discount/rate identity")
    test = _dataset(arrays, "test")
    _close(arrays["contract_quotes"], test["x_quote"][:, :5], label="frozen contract coupon")
    for model_id in arrays["model_ids"]:
        model_id = str(model_id)
        exported = _restore(arrays, model_id)
        size = int(model_id.split("_n")[1].split("_s")[0])
        train = _dataset(arrays, "train")
        price = train["price"][:size]
        eval_scale = np.maximum(np.sqrt(np.mean(train["g_quote"][:size] ** 2, axis=0)), 1e-8)
        _close(arrays[f"pred__{model_id}__risk_scale"], eval_scale, label="evaluation train scale")
        if exported["kind"] == "nn":
            x = train["x_theta" if exported["mode"].startswith("theta") else "x_quote"][:size]
            features = np.column_stack([x[:, :5], np.log(x[:, 5] / 100), np.log(x[:, 6])])
            target_risk = train["g_theta" if exported["mode"] == "theta_dml" else "g_quote"][:size]
        else:
            x = train["x_quote"][:size]
            features = np.column_stack(
                [np.log(x[:, 5] / 100), train["integrated_rate"][:size], np.log(x[:, 6])]
            )
            target_risk = train["g_quote"][:size]
        scales = {
            "feature_mean": features.mean(axis=0),
            "feature_std": np.where(np.ptp(features, axis=0) > 0, features.std(axis=0), 1.0),
            "price_mean": price.mean(),
            "price_scale": max(float(price.std()), 1e-8),
            "risk_scale": np.maximum(np.sqrt(np.mean(target_risk**2, axis=0)), 1e-8),
        }
        for key, value in scales.items():
            _close(exported[key], value, label=f"train-only scale {key}")
        replayed = _prediction(exported, test)
        prefix = f"pred__{model_id}__"
        for key in ("price", "g_quote"):
            _close(arrays[prefix + key], replayed[key], label=f"weight replay {model_id} {key}")
        _close(
            arrays[prefix + "h"],
            np.linalg.solve(arrays["test_B"], -replayed["g_quote"][..., None])[..., 0],
            label="risk hedge solve",
        )
        residual = (
            arrays["shock_price"]
            - test["price"][:, None]
            + np.einsum(
                "ni,nji->nj",
                arrays[prefix + "h"],
                arrays["shock_held"] - arrays["held_base"][:, None],
            )
        )
        _close(arrays[prefix + "residual"], residual, label="held shock residual")
        costs = np.empty_like(arrays[prefix + "cost"])
        for row, h in enumerate(arrays[prefix + "h"]):
            for i, rate_bp in enumerate(arrays["cost_rate_bp"]):
                for j, stock_bp in enumerate(arrays["cost_stock_bp"]):
                    costs[row, i, j] = hedging.entry_cost(
                        h,
                        arrays["test_B"][row],
                        test["x_quote"][row, 5],
                        rate_halfspread_bp=rate_bp,
                        stock_halfspread_bp=stock_bp,
                    )
        _close(arrays[prefix + "cost"], costs, label="held entry fee")
        validation = _prediction(_restore(arrays, model_id), _dataset(arrays, "validation"))
        for key in ("price", "g_quote"):
            if _restore(arrays, model_id)["kind"] == "nn":
                _close(
                    arrays[f"validation_pred__{model_id}__{key}"],
                    validation[key],
                    label="validation replay",
                )
    _close(
        arrays["reference_h"],
        np.linalg.solve(arrays["test_B"], -test["g_quote"][..., None])[..., 0],
        label="reference risk solve",
    )
    reference_residual = (
        arrays["shock_price"]
        - test["price"][:, None]
        + np.einsum(
            "ni,nji->nj", arrays["reference_h"], arrays["shock_held"] - arrays["held_base"][:, None]
        )
    )
    _close(arrays["reference_residual"], reference_residual, label="reference curvature residual")
    np.testing.assert_allclose(
        arrays["reference_residual"][:, 0], 0.0, atol=1e-12, err_msg="zero shock"
    )
    if fresh:
        policy = {
            key: value.copy()
            for key, value in arrays.items()
            if not key.startswith(("safe__", "ood__"))
        }
        _policy_arrays(policy, test, config)
        for key, expected in policy.items():
            if key.startswith(("safe__", "ood__")):
                if expected.dtype.kind in "USb":
                    np.testing.assert_array_equal(arrays[key], expected, err_msg="policy replay")
                else:
                    _close(arrays[key], expected, label="policy replay")
    if "benchmark" in record:
        measured = record["benchmark"]
        expected_batches = (
            [1, 8, 16] if record["experiment"] == "smoke" else config["timing"]["batches"]
        )
        assert measured["settings"]["batches"] == expected_batches, "timing batch protocol"
        assert measured["settings"]["repeats"] == (
            3 if record["experiment"] == "smoke" else config["timing"]["repeats"]
        ), "timing repeat protocol"
        component("benchmark").check_measurement(
            measured, arrays, model_ids=arrays["model_ids"], protocol=config
        )
    for split in ("train", "validation", "test"):
        data = _dataset(arrays, split)
        if fresh:
            regenerated = make_dataset(config, split)
            for key in (
                "x_quote",
                "x_theta",
                "price",
                "g_quote",
                "g_theta",
                "A",
                "integrated_rate",
                "a_quote",
                "discount",
            ):
                _close(data[key], regenerated[key], label=f"dataset replay {split} {key}")
        if fresh:
            for row, x in enumerate(data["x_quote"]):
                exact = reference.digital_moments(x[:5], *x[5:])
                _close(
                    data["price"][row],
                    exact["price"],
                    label="independent price",
                    atol=1e-12,
                    rtol=1e-10,
                )
                _close(data["g_quote"][row], exact["g_quote"], label="independent risk")
    for row, x in enumerate(test["x_quote"]):
        q, spot, maturity = x[:5], x[5], x[6]
        coupon = arrays["contract_quotes"][row]
        _close(
            arrays["test_B"][row],
            reference.held_risk(q, spot, coupon, notional=config["costs"]["notional"]),
            label="independent held risk",
            atol=1e-6,
        )
        _close(
            arrays["held_base"][row],
            reference.held_prices(q, spot, coupon, notional=config["costs"]["notional"]),
            label="independent held prices",
            atol=1e-6,
        )
        if fresh:
            for j, (dq, ds) in enumerate(
                zip(arrays["shock_dq"], arrays["shock_spot_fraction"], strict=True)
            ):
                _close(
                    arrays["shock_price"][row, j],
                    reference.digital_price(q + dq, spot * (1 + ds), maturity),
                    label="independent shock price",
                    atol=1e-12,
                )
                _close(
                    arrays["shock_held"][row, j],
                    reference.held_prices(
                        q + dq, spot * (1 + ds), coupon, notional=config["costs"]["notional"]
                    ),
                    label="independent held shock",
                    atol=1e-6,
                )
    computed = component("replay").metrics(arrays, config)

    def compare(actual, expected):
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys(), "metric schema"
            for key in expected:
                compare(actual[key], expected[key])
        elif isinstance(expected, list):
            assert len(actual) == len(expected), "metric shape"
            for left, right in zip(actual, expected, strict=True):
                compare(left, right)
        elif isinstance(expected, (int, float)):
            _close(actual, expected, label="metric replay")
        else:
            assert actual == expected, "metric replay metadata"

    compare(record["metrics"], computed)
    if "loading" in record:
        _check_loading(record, arrays)
    if "costs" in record:
        compare(record["costs"], component("costs").cost_summary(record, arrays))


def save_result(directory, record, arrays):
    """Persist numerical arrays plus experiment metadata before acceptance checks."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    array_path = directory / "reference.npz"
    np.savez_compressed(array_path, **arrays)
    record["artifact"] = {
        "bytes": array_path.stat().st_size,
        "sha256": hashlib.sha256(array_path.read_bytes()).hexdigest(),
        "arrays": {
            key: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for key, value in arrays.items()
        },
    }
    (directory / "reference.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    if record["artifact"]["bytes"] > record["protocol"]["artifacts"]["max_git_bytes"]:
        store = HERE.parents[2] / "scripts/evidence_store.py"
        subprocess.run(
            [
                sys.executable,
                str(store),
                "put",
                "--project-root",
                str(directory),
                "--manifest-out",
                str(directory / "manifest.json"),
                "reference.npz",
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(store),
                "verify",
                str(directory / "manifest.json"),
                "--work",
                str(directory / "artifact-cache/restore-check" / record["artifact"]["sha256"][:16]),
            ],
            check=True,
        )


def load_result(directory):
    """Load declared numeric arrays only; object/pickle arrays are prohibited."""
    directory = Path(directory)
    record = json.loads((directory / "reference.json").read_text())
    array_path = directory / "reference.npz"
    if not array_path.exists() and (directory / "manifest.json").exists():
        store = HERE.parents[2] / "scripts/evidence_store.py"
        subprocess.run(
            [
                sys.executable,
                str(store),
                "restore",
                str(directory / "manifest.json"),
                "--dest",
                str(directory),
            ],
            check=True,
        )
    assert hashlib.sha256(array_path.read_bytes()).hexdigest() == record["artifact"]["sha256"], (
        "artifact integrity"
    )
    with np.load(array_path, allow_pickle=False) as source:
        arrays = dict(source)
    assert arrays.keys() == record["artifact"]["arrays"].keys(), "artifact array registry"
    for key, value in arrays.items():
        assert list(value.shape) == record["artifact"]["arrays"][key]["shape"], (
            f"artifact shape {key}"
        )
        assert str(value.dtype) == record["artifact"]["arrays"][key]["dtype"], (
            f"artifact dtype {key}"
        )
    return record, arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--smoke", action="store_true")
    actions.add_argument("--refresh", action="store_true")
    actions.add_argument("--check", action="store_true")
    actions.add_argument(
        "--measure", action="store_true", help="append timing to saved fits; never train"
    )
    actions.add_argument(
        "--measure-loading",
        action="store_true",
        help="measure warm-cache saved-bundle loading and summarize costs; never train",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.smoke and args.output is None:
        parser.error("--smoke requires a separate --output directory")
    output = args.output or HERE
    if args.measure:
        record, arrays = load_result(output)
        source_digest = hashlib.sha256((HERE / "benchmark.py").read_bytes()).hexdigest()
        benchmark, raw = component("benchmark").measure(
            record["protocol"], arrays, smoke=record["experiment"] == "smoke"
        )
        record["benchmark"] = benchmark
        record["timing_source"] = {"sha256": source_digest, "capture": "before_measure_call"}
        # A new measurement invalidates costs and loading of the old bundle.
        record.pop("costs", None)
        record.pop("loading", None)
        arrays = {key: value for key, value in arrays.items() if not key.startswith("loading__")}
        arrays.update(raw)
        save_result(output, record, arrays)
        print("PASS: timing saved; no training")
        return
    if args.measure_loading:
        record, arrays = load_result(output)
        loading, raw = component("measure_loading").measure(output)
        loading["input_npz"] = {key: record["artifact"][key] for key in ("sha256", "bytes")}
        record["loading"] = loading
        arrays.update(raw)
        _check_loading(record, arrays)
        record["costs"] = component("costs").cost_summary(record, arrays)
        save_result(output, record, arrays)
        print("PASS: loading and cost accounts saved; no training")
        return
    if args.check:
        record, arrays = load_result(output)
        check_record(record, arrays, fresh=True)
        print(f"PASS: {record['experiment']}, {len(arrays['model_ids'])} models; no training")
        return
    record, arrays = run_experiment(load_protocol(), smoke=args.smoke)
    record["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": importlib.metadata.version("scipy"),
        "torch": importlib.metadata.version("torch"),
        "synthetic": True,
    }
    sources = [
        "build_reference.py",
        "replay.py",
        "policy.py",
        "reference_methods.py",
        "diagnostics.py",
        "protocol.json",
    ]
    record["sources"] = {
        name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in sources
    }
    save_result(output, record, arrays)
    check_record(record, arrays, fresh=True)
    print(
        f"PASS: saved {record['experiment']} result, {len(arrays['model_ids'])} models, {record['artifact']['bytes']} bytes"
    )


if __name__ == "__main__":
    main()
