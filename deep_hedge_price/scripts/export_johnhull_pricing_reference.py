"""Export the validated Phase 2 quick run as stable johnhull JSON/NPZ."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import torch

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from johnhull.scripts.frontier_acceptance import evaluate_acceptance

from deep_hedge_price.greeks import autodiff_greeks
from deep_hedge_price.pricing_artifacts import load_pricing_dataset
from deep_hedge_price.pricing_config import load_pricing_config, pricing_run_directory
from deep_hedge_price.pricing_data import black_scholes_labels
from deep_hedge_price.pricing_training import load_pricing_model

ROOT = WORKSPACE_ROOT
RELEASE = json.loads((ROOT / "johnhull/release_manifest.json").read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue(), compress_type=zipfile.ZIP_DEFLATED)


def _verify_written_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != set(arrays):
            raise ValueError(f"written NPZ names differ: {path}")
        for name, expected in arrays.items():
            if not np.array_equal(archive[name], expected):
                raise ValueError(f"written NPZ values differ: {path}:{name}")


def _teacher_diagnostics() -> tuple[dict[str, float], dict[str, float], dict[str, np.ndarray]]:
    from hullkit import bsm
    from hullkit.surrogate_data import mc_black_scholes_call_estimates

    references = {
        "price": bsm.call_price(100, 100, 0.02, 0.2, 1.0, 0.01),
        "delta": bsm.call_delta(100, 100, 0.02, 0.2, 1.0, 0.01),
        "vega": bsm.vega(100, 100, 0.02, 0.2, 1.0, 0.01),
    }
    intervals = [
        mc_black_scholes_call_estimates(
            100,
            100,
            0.02,
            1.0,
            0.2,
            q=0.01,
            n_paths=8_000,
            seed=seed,
        )
        for seed in range(20)
    ]
    coverage = {
        name: float(
            np.mean(
                [
                    getattr(row, name).ci_lower <= reference <= getattr(row, name).ci_upper
                    for row in intervals
                ]
            )
        )
        for name, reference in references.items()
    }
    small = mc_black_scholes_call_estimates(100, 105, 0.02, 1.0, 0.3, n_paths=10_000, seed=4)
    large = mc_black_scholes_call_estimates(100, 105, 0.02, 1.0, 0.3, n_paths=40_000, seed=4)
    se_ratio = {
        name: getattr(large, name).standard_error / getattr(small, name).standard_error
        for name in references
    }
    # The raw intervals and standard errors let the acceptance gate recompute
    # the coverage and the 4x-path ratio instead of reading them back.
    evidence = {
        "teacher_estimand_names": np.asarray(tuple(references)),
        "teacher_reference": np.asarray(tuple(references.values())),
        "teacher_ci_lower": np.asarray(
            [[getattr(row, name).ci_lower for name in references] for row in intervals]
        ),
        "teacher_ci_upper": np.asarray(
            [[getattr(row, name).ci_upper for name in references] for row in intervals]
        ),
        "teacher_se_4x_paths": np.asarray(
            [[getattr(row, name).standard_error for name in references] for row in (small, large)]
        ),
    }
    return coverage, se_ratio, evidence


def _row_keys(rows: np.ndarray) -> np.ndarray:
    """First 64 bits of each row's SHA-256, the digest the split manifest uses."""
    value = np.ascontiguousarray(rows)
    return np.asarray(
        [
            int.from_bytes(hashlib.sha256(row.tobytes(order="C")).digest()[:8], "little")
            for row in value
        ],
        dtype=np.uint64,
    )


def _array_schema(arrays: dict[str, np.ndarray]) -> dict[str, dict[str, object]]:
    units = {
        "moneyness": "S/K",
        "maturity": "years",
        "truth_price": "C/K",
        "neural_price": "C/K",
        "price_error": "absolute C/K error",
        "delta_error": "absolute d(C/K)/d(S/K) error",
        "gamma_error": "absolute d2(C/K)/d(S/K)2 error",
        "check_names": "hard-check identifier",
        "violations_unconstrained": "count averaged across 3 seeds",
        "violations_constrained": "count",
        "batch_size": "rows",
        "analytic_us": "microseconds median",
        "mlp_us": "microseconds median",
        "test_price_abs_error": "absolute C/K error per test row",
        "test_delta_abs_error": "absolute delta error per test row",
        "ood_price_abs_error": "absolute C/K error per OOD row",
        "ood_delta_abs_error": "absolute delta error per OOD row",
        "split_row_key_train": "first 64 bits of the row SHA-256",
        "split_row_key_validation": "first 64 bits of the row SHA-256",
        "split_row_key_test": "first 64 bits of the row SHA-256",
        "split_row_key_ood": "first 64 bits of the row SHA-256",
        "teacher_estimand_names": "estimand identifier",
        "teacher_reference": "analytic BSM price, delta and vega",
        "teacher_ci_lower": "95% MC interval lower bound per seed",
        "teacher_ci_upper": "95% MC interval upper bound per seed",
        "teacher_se_4x_paths": "MC standard error at 10k and 40k paths",
    }
    return {
        name: {
            "shape": list(np.asarray(value).shape),
            "dtype": str(np.asarray(value).dtype),
            "unit": units[name],
        }
        for name, value in sorted(arrays.items())
    }


def export(config_path: Path, output_dir: Path, ablation_path: Path) -> tuple[Path, Path]:
    config = load_pricing_config(config_path)
    run = pricing_run_directory(config, ROOT / "deep_hedge_price")
    manifest_path = run / "pricing_dataset.json"
    checkpoint_path = run / "pricing_best.pt"
    evaluation_path = run / "pricing_evaluation.json"
    missing = [
        path
        for path in (manifest_path, checkpoint_path, evaluation_path, ablation_path)
        if not path.exists()
    ]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"missing validated pricing inputs: {names}; run pricing-demo and pricing-ablation first"
        )
    manifest, dataset = load_pricing_dataset(manifest_path)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    ablation = json.loads(ablation_path.read_text(encoding="utf-8"))
    if evaluation["config_fingerprint"] != config.fingerprint():
        raise ValueError("evaluation/config fingerprint mismatch")
    if not all(evaluation["acceptance"].values()):
        raise ValueError("main pricing acceptance must pass before export")
    if ablation["config_fingerprint"] != config.fingerprint():
        raise ValueError("ablation/config fingerprint mismatch")

    model, checkpoint = load_pricing_model(checkpoint_path, device="cpu")
    moneyness = np.linspace(0.65, 1.35, 29)
    maturity = np.linspace(0.03, 2.0, 21)
    xx, tt = np.meshgrid(moneyness, maturity)
    inputs = np.column_stack(
        (
            xx.ravel(),
            tt.ravel(),
            np.full(xx.size, 0.02),
            np.full(xx.size, 0.01),
            np.full(xx.size, 0.20),
        )
    )
    targets = black_scholes_labels(inputs)
    tensor = torch.as_tensor(inputs, dtype=torch.float64)
    autodiff = autodiff_greeks(model, tensor)
    with torch.no_grad():
        price, direct = model.components(tensor)
    route = evaluation["greek_route_selection"]["adopted"]
    if route == "direct_heads" and direct is not None:
        delta = direct[:, 0].numpy()
        gamma = direct[:, 1].numpy()
    else:
        delta = autodiff["delta"].numpy()
        gamma = autodiff["gamma"].numpy()

    hard_validation = evaluation["hard_validation"]
    check_names = hard_validation["applicable_checks"]
    if not hard_validation.get("check_set_complete"):
        raise ValueError("main evaluation hard-check set is incomplete")
    unconstrained_checks = ablation["variants"]["price_only"]["aggregate"]["hard_validation"][
        "checks"
    ]
    constrained_checks = {row["name"]: row for row in hard_validation["checks"]}
    if set(unconstrained_checks) != set(check_names) or set(constrained_checks) != set(check_names):
        raise ValueError("main evaluation and ablation must report every applicable hard check")
    benchmark = evaluation["benchmark"]
    arrays = {
        "moneyness": moneyness,
        "maturity": maturity,
        "truth_price": targets["price"].reshape(xx.shape),
        "neural_price": price.numpy().reshape(xx.shape),
        "price_error": np.abs(price.numpy() - targets["price"]).reshape(xx.shape),
        "delta_error": np.mean(
            np.abs(delta.reshape(xx.shape) - targets["delta"].reshape(xx.shape)), axis=0
        ),
        "gamma_error": np.mean(
            np.abs(gamma.reshape(xx.shape) - targets["gamma"].reshape(xx.shape)), axis=0
        ),
        "check_names": np.asarray(check_names),
        "violations_unconstrained": np.asarray(
            [unconstrained_checks[name]["n_violations"]["mean"] for name in check_names]
        ),
        "violations_constrained": np.asarray(
            [constrained_checks[name]["n_violations"] for name in check_names], dtype=np.int64
        ),
        "batch_size": np.asarray([row["batch_size"] for row in benchmark["analytic"]]),
        "analytic_us": 1_000 * np.asarray([row["median_ms"] for row in benchmark["analytic"]]),
        "mlp_us": 1_000 * np.asarray([row["median_ms"] for row in benchmark["neural"]]),
    }
    # Per-row split errors, re-evaluated with the evaluation's adopted Greek
    # route, so the gate recomputes the MAEs instead of trusting the JSON.
    for split in ("test", "ood"):
        split_inputs = torch.as_tensor(
            np.asarray(dataset[f"{split}_inputs"], dtype=np.float64), dtype=torch.float64
        )
        with torch.no_grad():
            split_price, split_direct = model.components(split_inputs)
        if route == "direct_heads" and split_direct is not None:
            split_delta = split_direct[:, 0].numpy()
        else:
            split_delta = autodiff_greeks(model, split_inputs)["delta"].numpy()
        price_error = np.abs(
            split_price.numpy() - np.asarray(dataset[f"{split}_price"], dtype=np.float64)
        )
        delta_error = np.abs(split_delta - np.asarray(dataset[f"{split}_delta"], dtype=np.float64))
        reported = evaluation["splits"][split]
        if not (
            np.isclose(price_error.mean(), reported["neural_price"]["mae"], rtol=1e-12, atol=0.0)
            and np.isclose(
                delta_error.mean(), reported["greeks"]["delta"]["mae"], rtol=1e-12, atol=0.0
            )
        ):
            raise ValueError(f"{split} per-row errors do not reproduce the evaluation MAE")
        arrays[f"{split}_price_abs_error"] = price_error
        arrays[f"{split}_delta_abs_error"] = delta_error
    for split in ("train", "validation", "test", "ood"):
        arrays[f"split_row_key_{split}"] = _row_keys(dataset[f"{split}_inputs"])
    output_dir.mkdir(parents=True, exist_ok=True)
    arrays_path = output_dir / "pricing_slices.npz"
    coverage, se_ratio, teacher_evidence = _teacher_diagnostics()
    arrays.update(teacher_evidence)
    test = evaluation["splits"]["test"]
    ood = evaluation["splits"]["ood"]
    metrics = {
        "price_mae_normalized": test["neural_price"]["mae"],
        "delta_mae": test["greeks"]["delta"]["mae"],
        "ood_price_mae_normalized": ood["neural_price"]["mae"],
        "ood_price_worst_absolute_error": ood["neural_price"]["worst_absolute_error"],
        "ood_delta_mae": ood["greeks"]["delta"]["mae"],
        "split_overlap_count": manifest.overlap_count,
        "hard_violation_rate": float(
            np.mean([row["violation_rate"] for row in evaluation["hard_validation"]["checks"]])
        ),
        "break_even_batch": benchmark["neural_vs_analytic_break_even_batch"],
        "teacher_ci_coverage_20_seeds": coverage["price"],
        "teacher_ci_coverage_20_seeds_by_estimand": coverage,
        "teacher_se_ratio_4x_paths": se_ratio["price"],
        "teacher_se_ratio_4x_paths_by_estimand": se_ratio,
        "dml_improved_a_greek_without_price_degradation": ablation["conclusions"][
            "variant_comparison"
        ]["differential_ml"]["improves_a_greek_without_material_price_degradation"],
        "soft_penalty_improved_hard_checks": ablation["conclusions"]["penalty_comparison"][
            "positive_penalty_improves_hard_checks_without_material_price_degradation"
        ],
        "heston_bsm_residual_mae": evaluation["residual_correction"]["bsm_residual_mae"],
        "heston_raw_price_mae": evaluation["residual_correction"]["raw_price_mae"],
    }
    payload = {
        "schema_version": 1,
        "volume": 18,
        "generated_by": "deep_hedge_price/scripts/export_johnhull_pricing_reference.py",
        "data_policy": "synthetic-offline",
        "artifact_role": "validated Phase 2 quick-run reference for artifact-only teaching",
        "semantic_sources": next(
            item["semantic_sources"] for item in RELEASE["volumes"] if item["number"] == 18
        ),
        "semantic_tests": next(
            item["semantic_tests"] for item in RELEASE["volumes"] if item["number"] == 18
        ),
        "metrics": metrics,
        "acceptance": evaluate_acceptance(18, metrics, arrays),
        "engine_evidence": {
            "config_fingerprint": config.fingerprint(),
            "dataset_split_fingerprints": manifest.split_fingerprints,
            "checkpoint_epoch": checkpoint["epoch"],
            "greek_route": route,
            "acceptance": evaluation["acceptance"],
            "ablation_sha256": _sha256(ablation_path),
        },
        "companions": {},
        "companion_schemas": {arrays_path.name: _array_schema(arrays)},
        "limitations": [
            "Synthetic Black-Scholes accuracy is not evidence of market forecasting power.",
            "The OOD shell remains a stress diagnostic and is not an acceptance claim.",
            "The 512-path Monte-Carlo benchmark is a latency workload, not a precision result.",
            "The small ablation may fail absolute main-run thresholds and is used only for relative comparison.",
        ],
    }
    json_path = output_dir / "pricing_metrics.json"
    with tempfile.TemporaryDirectory(prefix=".pricing-reference-", dir=output_dir) as temporary:
        temporary_dir = Path(temporary)
        temporary_arrays = temporary_dir / arrays_path.name
        temporary_json = temporary_dir / json_path.name
        _stable_npz(temporary_arrays, arrays)
        _verify_written_npz(temporary_arrays, arrays)
        payload["companions"] = {arrays_path.name: _sha256(temporary_arrays)}
        temporary_json.write_text(
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_arrays.replace(arrays_path)
        temporary_json.replace(json_path)
    return json_path, arrays_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "johnhull/volumes/18_ml_surrogates/reference",
    )
    parser.add_argument(
        "--ablation",
        type=Path,
        default=ROOT / "deep_hedge_price/reports/pricing_ablation_quick.json",
    )
    args = parser.parse_args()
    json_path, arrays_path = export(args.config, args.output_dir, args.ablation)
    print(f"Exported {json_path.relative_to(ROOT)} and {arrays_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
