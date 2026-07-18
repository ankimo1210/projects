"""Build vol 19--25 references from the tested implementation APIs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

try:
    from .frontier_acceptance import evaluate_acceptance
except ImportError:  # direct script execution
    from frontier_acceptance import evaluate_acceptance

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "johnhull"
VOLUMES = PROJECT / "volumes"
RELEASE = json.loads((PROJECT / "release_manifest.json").read_text(encoding="utf-8"))

FILES = {
    19: ("19_inverse_surfaces", "metrics.json", "surfaces.npz"),
    20: ("20_surface_dynamics", "metrics.json", "forecast_paths.npz"),
    21: ("21_spx_vix", "metrics.json", "joint_surface.npz"),
    22: ("22_zero_dte", "metrics.json", "intraday_slices.npz"),
    23: ("23_rfr_post_libor", "metrics.json", "rfr_scenarios.npz"),
    24: ("24_crypto_market_structure", "metrics.json", "stress_paths.npz"),
    25: ("25_climate_energy", "metrics.json", "scenarios.npz"),
}

UNITS_BY_VOLUME: dict[int, dict[str, str]] = {
    21: {
        "strike": "synthetic index points",
        "maturity": "years",
        "spx_target": "decimal implied volatility",
        "spx_pdv": "decimal implied volatility",
        "spx_afv": "decimal implied volatility",
        "spx_rough_heston": "decimal implied volatility",
        "spx_quintic_ou": "decimal implied volatility",
        "vix_maturity": "years",
        "vix_target": "VIX index points",
        "vix_pdv": "VIX index points",
        "vix_option_target": "synthetic monetary units",
        "vix_option_pdv": "synthetic monetary units",
        "variance_term_target": "annualized variance",
        "variance_term_pdv": "annualized variance",
        "spx_model_grid": "decimal implied volatility",
        "vix_model_grid": "VIX index points",
        "vix_option_model_grid": "discounted index-point option price",
        "variance_term_model_grid": "annualized variance",
        "model_names": "label",
        "spx_rmse": "decimal implied volatility",
        "vix_rmse": "VIX index points",
        "vix_option_rmse": "synthetic monetary units",
        "variance_rmse": "annualized variance",
        "joint_loss": "dimensionless weighted loss",
        "surrogate_features": "normalized features",
        "teacher_price": "synthetic monetary units",
        "teacher_standard_error": "discounted index-point option price",
        "surrogate_price": "synthetic monetary units",
        "teacher_delta": "price per normalized scale",
        "teacher_gamma": "price per normalized scale squared",
        "surrogate_delta": "price per normalized scale",
        "surrogate_gamma": "price per normalized scale squared",
        "ood_flag": "boolean",
        "ood_radius": "normalized Euclidean distance",
        "ood_error": "synthetic monetary units",
        "batch_size": "rows",
        "nested_mc_ms": "milliseconds median",
        "surrogate_ms": "milliseconds median",
    },
    22: {
        "minute": "trading minutes",
        "variance_weight": "normalized variance weight",
        "variance_clock": "cumulative variance fraction",
        "event_jump_intensity": "jump intensity per session",
        "non_event_jump_intensity": "jump intensity per session",
        "scheduled_variance": "variance",
        "event_mask": "boolean",
        "time_of_day": "label",
        "seconds_to_settlement": "seconds",
        "teacher_price": "synthetic monetary units",
        "baseline_price": "synthetic monetary units",
        "teacher_standard_error": "synthetic monetary units",
        "delta": "price per underlying unit",
        "gamma": "price per underlying unit squared",
        "baseline_delta": "price per underlying unit",
        "adjacent_expiry_minutes": "trading minutes",
        "total_variance": "total variance",
        "model_total_variance": "total variance",
        "forward_variance": "forward variance",
        "tod_names": "label",
        "price_mae": "synthetic monetary units",
        "greek_mae": "price per underlying unit",
        "event_split_names": "label",
        "event_price_rmse": "synthetic monetary units",
        "event_greek_rmse": "price per underlying unit",
    },
    23: {
        "convention_names": "label",
        "convention_rate": "annualized decimal rate",
        "convention_accumulation": "accrual factor",
        "convention_day_count": "days",
        "convention_observation_ordinal": "days",
        "coupon_names": "label",
        "coupon_cashflow": "synthetic monetary units",
        "curve_names": "label",
        "curve_discount_factor": "discount factor",
        "curve_forward_rate": "annualized decimal rate",
        "basis_spread_bp": "basis points",
        "policy_scenario_names": "label",
        "policy_date_ordinal": "days",
        "policy_rate_path": "annualized decimal rate",
        "collateral_currency_names": "label",
        "collateral_currency_pv": "synthetic monetary units",
        "collateral_shift_bp": "basis points",
        "day": "index",
        "daily_rate": "decimal rate",
        "day_count": "year fraction",
        "discrete_accrual": "accrual factor",
        "continuous_accrual": "accrual factor",
        "maturity": "years",
        "discount_factor": "discount factor",
        "forward_rate": "decimal rate",
        "futures_forward_bp": "basis points",
        "strike": "decimal rate",
        "normal_iv": "decimal normal volatility",
        "shifted_sabr_iv": "decimal normal volatility",
        "free_boundary_sabr_iv": "decimal normal volatility",
        "teacher_maturity": "years",
        "bachelier_price": "rate-option price units",
        "quadrature_price": "rate-option price units",
        "shifted_sabr_price": "rate-option price units",
        "free_boundary_sabr_price": "rate-option price units",
        "shifted_teacher_price": "rate-option price units",
        "shifted_teacher_standard_error": "rate-option price units",
        "hagan_price": "rate-option price units",
        "teacher_price": "rate-option price units",
        "teacher_standard_error": "rate-option price units",
        "hagan_error_bp": "basis points",
        "hedge_names": "label",
        "hedge_rmse": "rate-option price units",
        "option_price_change": "rate-option price units",
        "forward_change": "decimal rate",
        "sticky_hedge_error": "rate-option price units",
        "bartlett_hedge_error": "rate-option price units",
        "hedge_teacher_standard_error": "rate-option price units",
        "policy_jump_bp": "basis points",
        "collateral_pv": "synthetic monetary units",
    },
    24: {
        "contract_names": "label",
        "contract_settlement_price": "synthetic USD per asset",
        "contract_pnl_long": "contract settlement units",
        "contract_pnl_short": "contract settlement units",
        "step": "index",
        "elapsed_hours": "hours",
        "index_price": "synthetic USD per asset",
        "mark_price": "synthetic USD per asset",
        "last_price": "synthetic USD per asset",
        "mark_index_basis": "dimensionless price ratio",
        "funding_rate": "decimal rate",
        "funding_rate_cap": "decimal rate per settlement interval",
        "funding_settled_intervals": "count",
        "funding_long_cashflow": "synthetic monetary units",
        "funding_short_cashflow": "synthetic monetary units",
        "funding_venue_cashflow": "synthetic monetary units",
        "funding_conservation_error": "synthetic monetary units",
        "funding_cashflow": "synthetic monetary units",
        "equity": "synthetic monetary units",
        "liability": "synthetic monetary units",
        "initial_margin_requirement": "synthetic monetary units",
        "maintenance_margin_requirement": "synthetic monetary units",
        "bankruptcy_price": "synthetic USD per asset",
        "liquidation_price": "synthetic USD per asset",
        "insurance_fund": "synthetic monetary units",
        "insurance_used": "synthetic monetary units",
        "adl_notional": "synthetic monetary units",
        "socialized_loss": "synthetic monetary units",
        "uncovered_loss": "synthetic monetary units",
        "liquidation_conservation_error": "synthetic monetary units",
        "liquidation_method_names": "label",
        "liquidation_execution_price": "synthetic USD per asset",
        "liquidation_method_equity": "synthetic monetary units",
        "liquidation_method_auction_recovery": "synthetic monetary units",
        "liquidation_method_insurance_used": "synthetic monetary units",
        "liquidation_method_adl_used": "synthetic monetary units",
        "liquidation_method_socialized_loss": "synthetic monetary units",
        "liquidation_method_uncovered_loss": "synthetic monetary units",
        "liquidation_method_conservation_error": "synthetic monetary units",
        "rebalanced_value": "synthetic monetary units",
        "lp_value": "synthetic monetary units",
        "lvr": "synthetic monetary units",
        "fee_income": "synthetic monetary units",
        "dynamic_fee_income": "synthetic monetary units",
        "fixed_fee_net_lvr": "token-Y value",
        "dynamic_fee_net_lvr": "token-Y value",
        "fixed_fee_gross_lvr": "token-Y value",
        "dynamic_fee_gross_lvr": "token-Y value",
        "concentrated_lp_value": "token-Y value",
        "concentrated_lvr": "token-Y value",
        "cpmm_swap_identity_error": "token amount identity residual",
        "cpmm_invariant_gain": "reserve product",
        "amm_identity_error": "synthetic monetary units",
        "oracle_age": "seconds",
        "oracle_stale": "boolean",
        "oracle_dislocated": "boolean",
        "oracle_shocked_mark": "synthetic USD per asset",
        "oracle_latent_index": "synthetic USD per asset",
        "oracle_observed_dislocation": "dimensionless price ratio",
        "oracle_latent_dislocation": "dimensionless price ratio",
        "liquidation_loss": "synthetic monetary units",
    },
    25: {
        "strike": "synthetic carbon price units",
        "carbon_model_names": "label",
        "carbon_model_price": "synthetic monetary units",
        "carbon_model_standard_error": "synthetic monetary units",
        "carbon_black76_price": "synthetic monetary units",
        "carbon_gbm_price": "synthetic monetary units",
        "carbon_gbm_standard_error": "synthetic monetary units",
        "carbon_heston_price": "synthetic monetary units",
        "carbon_heston_standard_error": "synthetic monetary units",
        "carbon_jump_price": "synthetic monetary units",
        "carbon_jump_standard_error": "synthetic monetary units",
        "carbon_gbm_iv": "decimal volatility",
        "carbon_heston_iv": "decimal volatility",
        "carbon_jump_iv": "decimal volatility",
        "risk_premium_names": "label",
        "premium_sensitivity": "synthetic monetary units",
        "day": "index",
        "temperature_seasonal": "degrees Celsius",
        "temperature_ou": "degrees Celsius",
        "temperature_fou": "degrees Celsius",
        "temperature_model_names": "label",
        "temperature_path_std": "degrees Celsius",
        "temperature_lag1_autocorrelation": "dimensionless correlation",
        "degree_day_mean": "degree-days",
        "degree_day_std": "degree-days",
        "premium_principle_names": "label",
        "weather_premium": "synthetic monetary units",
        "station_distance_km": "kilometres",
        "basis_rmse": "weather payoff units",
        "basis_residual": "weather payoff units",
        "basis_hedge_ratio": "dimensionless hedge ratio",
        "basis_variance_reduction": "dimensionless fraction",
        "ppa_fixed": "synthetic monetary units",
        "ppa_pay_as_produced": "synthetic monetary units",
        "ppa_floor_collar": "synthetic monetary units",
        "risk_names": "label",
        "cvar95": "synthetic monetary units",
        "cash_flow_at_risk": "synthetic monetary units",
        "unhedged_cash_flow_std": "synthetic monetary units",
        "expected_hedged_cash_flow": "synthetic monetary units",
        "hedge_residual": "synthetic monetary units",
        "ppa_fair_value": "synthetic monetary units",
        "ppa_volume_risk": "synthetic monetary units",
        "ppa_shape_risk": "synthetic monetary units",
        "ppa_profile_risk": "synthetic monetary units",
        "hedge_ratio": "dimensionless hedge ratio",
        "hedge_ratio_residual": "synthetic monetary units",
    },
}


def _stable_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write sorted arrays with fixed ZIP metadata for byte-stable artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            value = np.asarray(arrays[name])
            if value.dtype.kind == "O":
                raise ValueError(f"object dtype is forbidden in release artifact: {name}")
            if value.dtype.kind in "biufc" and not np.all(np.isfinite(value)):
                raise ValueError(f"non-finite release values: {name}")
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, value, allow_pickle=False)
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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _benchmark_contract(volume: int, arrays: dict[str, np.ndarray]) -> dict[str, object]:
    if volume != 21:
        return {"schema_version": 1, "nondeterministic_fields": []}
    sources = [
        PROJECT / "hullkit/src/hullkit/frontier_reference.py",
        PROJECT / "hullkit/src/hullkit/spx_vix.py",
    ]
    return {
        "schema_version": 1,
        "sources": {str(source.relative_to(ROOT)): _digest(source) for source in sources},
        "batch_size": np.asarray(arrays["batch_size"]).tolist(),
        "timing_method": "perf_counter_ns warm-cache median of 5",
        "nondeterministic_fields": [
            "nested_mc_ms",
            "surrogate_ms",
            "metrics.surrogate_speedup_1024",
        ],
    }


def _preserve_vol21_timing_reference(
    output: Path,
    metrics: dict[str, Any],
    arrays: dict[str, np.ndarray],
    benchmark: dict[str, object],
) -> None:
    """Keep the committed benchmark sample stable unless refresh is explicit."""
    json_path = output / "metrics.json"
    npz_path = output / "joint_surface.npz"
    if not json_path.exists() or not npz_path.exists():
        return
    previous = json.loads(json_path.read_text(encoding="utf-8"))
    if (
        previous.get("generated_by") != "johnhull/scripts/build_frontier_artifacts.py"
        or previous.get("generator_api") != "hullkit.frontier_reference.build_frontier_reference"
        or previous.get("benchmark") != benchmark
    ):
        return
    with np.load(npz_path, allow_pickle=False) as archive:
        if "batch_size" not in archive.files or not np.array_equal(
            archive["batch_size"], arrays["batch_size"]
        ):
            return
        for name in ("nested_mc_ms", "surrogate_ms"):
            if name not in archive.files or archive[name].shape != arrays[name].shape:
                raise ValueError(f"committed volume 21 timing schema changed for {name}")
            arrays[name] = archive[name].copy()
    metrics["surrogate_speedup_1024"] = previous["metrics"]["surrogate_speedup_1024"]


def _array_schema(
    volume: int,
    arrays: dict[str, np.ndarray],
    semantic_schema: dict[str, dict[str, object]] | None,
) -> dict[str, dict[str, object]]:
    if volume in {19, 20}:
        if semantic_schema is None:
            raise ValueError(f"volume {volume} implementation omitted its array schema")
        units = {name: str(spec["unit"]) for name, spec in semantic_schema.items()}
    else:
        units = UNITS_BY_VOLUME[volume]
    missing = set(arrays) - set(units)
    stale = set(units) - set(arrays)
    if missing or stale:
        raise ValueError(
            f"volume {volume} unit schema mismatch: missing={sorted(missing)}, stale={sorted(stale)}"
        )
    return {
        name: {
            "shape": list(np.asarray(value).shape),
            "dtype": str(np.asarray(value).dtype),
            "unit": units[name],
        }
        for name, value in sorted(arrays.items())
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _implementation_reference(
    volume: int,
) -> tuple[int, int, dict[str, Any], dict[str, np.ndarray]]:
    """Normalize the two project APIs without changing either public contract."""
    if volume in {19, 20}:
        from deep_hedge_price.frontier_reference import build_frontier_reference
    else:
        from hullkit.frontier_reference import build_frontier_reference

    reference = build_frontier_reference(volume)
    if volume in {19, 20}:
        metrics, arrays = reference
        return int(metrics["volume"]), int(metrics["seed"]), metrics, arrays
    return reference.volume, reference.seed, reference.metrics, reference.arrays


def build_volume(
    volume: int,
    *,
    refresh_timing: bool = False,
    output_root: Path | None = None,
) -> tuple[Path, Path]:
    """Build one reference directly from the corresponding semantic API."""
    if volume not in FILES:
        raise ValueError(f"volume must be one of {sorted(FILES)}")
    slug, json_name, npz_name = FILES[volume]
    item = next(row for row in RELEASE["volumes"] if row["number"] == volume)
    reference_volume, reference_seed, raw_metrics, raw_arrays = _implementation_reference(volume)
    arrays = {name: np.asarray(value) for name, value in raw_arrays.items()}
    metrics = _jsonable(raw_metrics)
    if reference_volume != volume:
        raise ValueError(f"implementation returned volume {reference_volume}, expected {volume}")
    output = (VOLUMES if output_root is None else output_root) / slug / "reference"
    benchmark = _benchmark_contract(volume, arrays)
    if volume == 21 and not refresh_timing:
        _preserve_vol21_timing_reference(output, metrics, arrays, benchmark)
    output.mkdir(parents=True, exist_ok=True)
    npz_path = output / npz_name
    json_path = output / json_name
    with tempfile.TemporaryDirectory(prefix=".frontier-", dir=output) as temporary:
        temporary_dir = Path(temporary)
        temporary_npz = temporary_dir / npz_name
        temporary_json = temporary_dir / json_name
        _stable_npz(temporary_npz, arrays)
        _verify_written_npz(temporary_npz, arrays)
        payload = {
            "schema_version": 1,
            "volume": volume,
            "generated_by": "johnhull/scripts/build_frontier_artifacts.py",
            "generator_api": (
                "deep_hedge_price.frontier_reference.build_frontier_reference"
                if volume in {19, 20}
                else "hullkit.frontier_reference.build_frontier_reference"
            ),
            "data_policy": "synthetic-offline",
            "artifact_role": "implementation-derived, identity-tested teaching reference",
            "benchmark": benchmark,
            "benchmark_policy": (
                "volume 21 preserves its committed perf_counter sample; pass --refresh-timing "
                "to measure again"
                if volume == 21
                else "no nondeterministic benchmark fields"
            ),
            "seed": reference_seed,
            "metrics": metrics,
            "acceptance": evaluate_acceptance(volume, metrics, arrays),
            "semantic_sources": item["semantic_sources"],
            "semantic_tests": item["semantic_tests"],
            "companions": {npz_name: _digest(temporary_npz)},
            "companion_schemas": {
                npz_name: _array_schema(volume, arrays, raw_metrics.get("array_schema"))
            },
            "limitations": metrics.get(
                "limitations",
                ["Synthetic results are not evidence of market forecasting power."],
            ),
        }
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
        temporary_npz.replace(npz_path)
        temporary_json.replace(json_path)
    return json_path, npz_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume", type=int, choices=sorted(FILES))
    parser.add_argument(
        "--refresh-timing",
        action="store_true",
        help="remeasure the non-deterministic volume 21 benchmark sample",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="optional volume root for non-mutating verification builds",
    )
    args = parser.parse_args(argv)
    volumes = [args.volume] if args.volume else sorted(FILES)
    for volume in volumes:
        json_path, npz_path = build_volume(
            volume,
            refresh_timing=args.refresh_timing,
            output_root=args.output_root,
        )
        try:
            display_json = json_path.relative_to(ROOT)
            display_npz = npz_path.relative_to(ROOT)
        except ValueError:
            display_json, display_npz = json_path, npz_path
        print(f"Built vol {volume}: {display_json} + {display_npz}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
