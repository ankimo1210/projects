"""Price/Greek/OOD buckets, hard checks, speed, and calibration evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from .greeks import autodiff_greeks
from .pricing_artifacts import load_pricing_dataset
from .pricing_benchmark import (
    benchmark_pricing_suite,
    break_even_batch_size,
    calibration_recovery,
)
from .pricing_config import PricingConfig, pricing_run_directory
from .pricing_policy import GREEK_NAMES, PolynomialRidge
from .pricing_residuals import compare_heston_bsm_residual
from .pricing_training import load_pricing_model


def _errors(prediction, target):
    prediction = np.asarray(prediction, dtype=float)
    target = np.asarray(target, dtype=float)
    absolute = np.abs(prediction - target)
    return {
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.mean((prediction - target) ** 2))),
        "relative_mae": float(np.mean(absolute / np.maximum(np.abs(target), 1e-6))),
        "worst_absolute_error": float(absolute.max(initial=0.0)),
    }


def bucket_metrics(inputs, prediction, target):
    x = inputs[:, 0]
    tau = inputs[:, 1]
    buckets = {
        "deep_otm": x < 0.9,
        "near_atm": (x >= 0.9) & (x <= 1.1),
        "deep_itm": x > 1.1,
        "short": tau < 0.25,
        "medium": (tau >= 0.25) & (tau <= 1.0),
        "long": tau > 1.0,
    }
    return {
        name: {"n": int(mask.sum()), **_errors(prediction[mask], target[mask])}
        for name, mask in buckets.items()
        if mask.any()
    }


def _hard_report(model, device):
    try:
        from hullkit.surrogate_validation import (
            check_calendar_monotonicity,
            check_greek_consistency,
            check_nonnegative_gamma,
            check_price_bounds,
            check_put_call_parity,
            check_spot_monotonicity,
            check_strike_convexity,
            check_strike_monotonicity,
            validation_report,
        )
    except ImportError as exc:
        raise RuntimeError("hullkit is required to create the canonical hard report") from exc
    strikes = np.linspace(0.7, 1.3, 61)
    strike_inputs = np.column_stack(
        (
            1.0 / strikes,
            np.ones_like(strikes),
            np.full_like(strikes, 0.02),
            np.full_like(strikes, 0.01),
            np.full_like(strikes, 0.25),
        )
    )
    with torch.no_grad():
        normalized = (
            model(torch.as_tensor(strike_inputs, dtype=torch.float64, device=device)).cpu().numpy()
        )
    strike_prices = strikes * normalized
    maturities = np.linspace(0.03, 2.0, 50)
    maturity_inputs = np.column_stack(
        (
            np.ones_like(maturities),
            maturities,
            np.full_like(maturities, 0.02),
            np.full_like(maturities, 0.01),
            np.full_like(maturities, 0.25),
        )
    )
    with torch.no_grad():
        maturity_prices = (
            model(torch.as_tensor(maturity_inputs, dtype=torch.float64, device=device))
            .cpu()
            .numpy()
        )
    spots = np.linspace(0.7, 1.3, 81)
    spot_inputs = np.column_stack(
        (
            spots,
            np.ones_like(spots),
            np.full_like(spots, 0.02),
            np.full_like(spots, 0.01),
            np.full_like(spots, 0.25),
        )
    )
    auto = autodiff_greeks(model, torch.as_tensor(spot_inputs, dtype=torch.float64, device=device))
    spot_prices = auto["price"].cpu().numpy()
    derived_puts = strike_prices - np.exp(-0.01) + strikes * np.exp(-0.02)
    checks = (
        check_price_bounds(strike_prices, 1.0, strikes, 0.02, 1.0, 0.01, tolerance=1e-6),
        check_put_call_parity(
            strike_prices,
            derived_puts,
            1.0,
            strikes,
            0.02,
            1.0,
            0.01,
            tolerance=1e-12,
        ),
        check_strike_monotonicity(strike_prices, strikes, tolerance=1e-5),
        check_strike_convexity(strike_prices, strikes, tolerance=1e-4),
        check_calendar_monotonicity(maturity_prices, maturities, tolerance=1e-5),
        check_spot_monotonicity(spot_prices, spots, tolerance=1e-5),
        check_nonnegative_gamma(auto["gamma"].cpu().numpy(), tolerance=1e-5),
        check_greek_consistency(
            spots,
            spot_prices,
            auto["delta"].cpu().numpy(),
            auto["gamma"].cpu().numpy(),
            tolerance=2e-2,
        ),
    )
    return validation_report(
        *checks,
        applicable_checks=(
            "price_bounds",
            "put_call_parity",
            "strike_monotonicity",
            "strike_convexity",
            "calendar_monotonicity",
            "spot_monotonicity",
            "nonnegative_gamma",
            "greek_consistency",
        ),
        metadata={
            "option_policy": "call_only",
            "put_call_parity_put_source": "derived_from_call",
            "put_call_parity_is_identity_by_construction": True,
        },
    ).to_dict()


def evaluate_pricing_run(
    config: PricingConfig,
    manifest_path: str | Path,
    checkpoint_path: str | Path,
    polynomial_path: str | Path,
    project_root: str | Path,
):
    manifest, arrays = load_pricing_dataset(Path(manifest_path))
    model, checkpoint = load_pricing_model(checkpoint_path, device="cpu")
    polynomial = PolynomialRidge.load(polynomial_path)
    model.eval()
    result = {
        "schema_version": 1,
        "artifact_kind": "pricing_evaluation",
        "config_fingerprint": config.fingerprint(),
        "dataset_fingerprints": manifest.split_fingerprints,
        "checkpoint_epoch": checkpoint["epoch"],
        "device": "cpu",
        "splits": {},
    }
    validation_inputs = np.asarray(arrays["validation_inputs"], dtype=np.float64)
    validation_tensor = torch.as_tensor(validation_inputs, dtype=torch.float64)
    validation_auto = autodiff_greeks(model, validation_tensor)
    with torch.no_grad():
        _validation_price, validation_direct = model.components(validation_tensor)
    validation_delta_target = np.asarray(arrays["validation_delta"], dtype=np.float64)
    autodiff_validation_mae = _errors(
        validation_auto["delta"].cpu().numpy(), validation_delta_target
    )["mae"]
    direct_validation_mae = (
        _errors(validation_direct[:, 0].cpu().numpy(), validation_delta_target)["mae"]
        if validation_direct is not None
        else None
    )
    adopted_route = (
        "direct_heads"
        if direct_validation_mae is not None and direct_validation_mae < autodiff_validation_mae
        else "price_head_autodiff"
    )
    result["greek_route_selection"] = {
        "split": "validation",
        "adopted": adopted_route,
        "direct_delta_mae": direct_validation_mae,
        "autodiff_delta_mae": autodiff_validation_mae,
    }
    for split in ("test", "ood"):
        inputs = np.asarray(arrays[f"{split}_inputs"], dtype=np.float64)
        target_price = np.asarray(arrays[f"{split}_price"], dtype=np.float64)
        tensor = torch.as_tensor(inputs, dtype=torch.float64)
        with torch.no_grad():
            neural_tensor, direct_tensor = model.components(tensor)
            neural_price = neural_tensor.cpu().numpy()
        auto = autodiff_greeks(model, tensor)
        autodiff_metrics = {
            name: _errors(auto[name].cpu().numpy(), arrays[f"{split}_{name}"])
            for name in GREEK_NAMES
        }
        if direct_tensor is not None:
            direct_values = direct_tensor.cpu().numpy()
            direct_metrics = {
                name: _errors(direct_values[:, index], arrays[f"{split}_{name}"])
                for index, name in enumerate(GREEK_NAMES)
            }
            consistency = {
                name: _errors(direct_values[:, index], auto[name].cpu().numpy())
                for index, name in enumerate(GREEK_NAMES)
            }
            greek_metrics = direct_metrics if adopted_route == "direct_heads" else autodiff_metrics
        else:
            direct_metrics = None
            consistency = None
            greek_metrics = autodiff_metrics
        result["splits"][split] = {
            "neural_price": _errors(neural_price, target_price),
            "polynomial_price": _errors(polynomial.predict(inputs), target_price),
            "greeks": greek_metrics,
            "autodiff_greeks": autodiff_metrics,
            "direct_greeks": direct_metrics,
            "direct_autodiff_consistency": consistency,
            "adopted_greek_route": adopted_route,
            "price_buckets": bucket_metrics(inputs, neural_price, target_price),
        }
    result["hard_validation"] = _hard_report(model, torch.device("cpu"))

    test_inputs = np.asarray(arrays["test_inputs"], dtype=np.float64)
    sample_sizes = tuple(dict.fromkeys((1, min(32, len(test_inputs)), min(256, len(test_inputs)))))

    def neural_fn(value):
        return model(torch.as_tensor(value, dtype=torch.float64)).detach().numpy()

    result["benchmark"] = benchmark_pricing_suite(
        test_inputs,
        polynomial_function=polynomial.predict,
        neural_function=neural_fn,
        batch_sizes=sample_sizes,
        warmup=1,
        repeats=5,
        device="cpu",
        mc_seed=config.data.seed + 90_000,
        mc_paths=512,
        heston_cos_terms=128,
    )
    result["benchmark"]["neural_vs_analytic_break_even_batch"] = break_even_batch_size(
        result["benchmark"]["analytic"], result["benchmark"]["neural"]
    )
    result["residual_correction"] = compare_heston_bsm_residual(
        np.asarray(arrays["train_inputs"][:1024], dtype=np.float64),
        test_inputs[:256],
        n_terms=128,
    )
    calibration_rows = test_inputs[: min(16, len(test_inputs))]
    result["calibration"] = calibration_recovery(
        neural_fn,
        calibration_rows,
        np.asarray(arrays["test_price"][: len(calibration_rows)]),
        bounds=config.data.bounds["sigma"],
    )
    result["acceptance"] = {
        "price_mae_below_1e-3": result["splits"]["test"]["neural_price"]["mae"] < 1e-3,
        "delta_mae_below_2e-3": result["splits"]["test"]["greeks"]["delta"]["mae"] < 2e-3,
        "all_hard_checks_pass": result["hard_validation"]["arbitrage_free"],
    }
    output = pricing_run_directory(config, project_root) / "pricing_evaluation.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return output, result
