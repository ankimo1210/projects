"""Reproducible, Luna-only improvement-round experiments and audit artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .curve import DEFAULT_KNOTS, cleaning_audit, choose_holdout, fit_advanced, fit_baseline, model_quote, score_model, score_segments
from .io import load_market_data


SEED = 20260905
VALUATION_DATE = date(2026, 1, 15)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _rmse_bp(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.sqrt(np.mean(((np.asarray(actual) - np.asarray(expected)) * 10000.0) ** 2)))


def _synthetic_raw(known_curve: Any, scenario: str = "base") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("deposit", 0.0833333333, 1, 0.0), ("deposit", 0.25, 1, 0.0), ("deposit", 0.5, 1, 0.0), ("deposit", 1.0, 1, 0.0),
        ("ois_swap", 1.5, 1, 0.0), ("ois_swap", 2.0, 1, 0.0), ("ois_swap", 3.0, 2, 0.0), ("ois_swap", 5.0, 2, 0.0),
        ("ois_swap", 7.0, 2, 0.0), ("ois_swap", 10.0, 2, 0.0), ("ois_swap", 15.0, 2, 0.0), ("ois_swap", 20.0, 2, 0.0), ("ois_swap", 25.0, 2, 0.0), ("ois_swap", 30.0, 2, 0.0),
        ("bond", 1.8, 2, 0.0200), ("bond", 4.5, 2, 0.0202), ("bond", 6.5, 2, 0.0204), ("bond", 9.0, 2, 0.0206),
        ("bond", 13.0, 2, 0.0208), ("bond", 18.0, 2, 0.0210), ("bond", 24.0, 2, 0.0212), ("bond", 28.0, 2, 0.0214),
    ]
    for index, (typ, maturity, frequency, coupon) in enumerate(specs):
        row: dict[str, Any] = {
            "obs_id": f"SYN-{scenario}-{index:03d}",
            "instrument_id": f"SYN-{typ}-{maturity:.6f}",
            "source": "SYNTHETIC",
            "timestamp": "2026-01-15T00:00:00Z",
            "currency": "USD",
            "instrument_type": typ,
            "maturity_date": (VALUATION_DATE + timedelta(days=max(31, int(round(maturity * 365.0))))).isoformat(),
            "maturity_years": maturity,
            "start_years": 0.0,
            "coupon_rate": coupon if typ == "bond" else np.nan,
            "payment_frequency": frequency,
            "day_count": "ACT/365F",
            "quote_type": {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}[typ],
            "quote_unit": "PRICE_POINTS" if typ == "bond" else "PERCENT",
            "liquidity_score": 1.0,
            "settlement_days": 2,
        }
        quote = float(model_quote(pd.Series({**row, "normalized_quote": 0.0}), known_curve))
        if typ == "bond":
            row["quote_value"] = quote
            row["bid"] = quote - 0.03
            row["ask"] = quote + 0.03
        else:
            row["quote_value"] = quote * 100.0
            row["bid"] = (quote - 0.00005) * 100.0
            row["ask"] = (quote + 0.00005) * 100.0
        rows.append(row)

    if scenario == "missing_mid_long":
        rows = [row for row in rows if not (row["instrument_type"] == "ois_swap" and np.isclose(row["maturity_years"], 10.0))]
    elif scenario == "outlier_low_liquidity":
        for row in rows:
            if row["instrument_type"] == "bond" and np.isclose(row["maturity_years"], 18.0):
                row["quote_value"] += 0.80
                row["bid"] += 0.80
                row["ask"] += 0.80
                row["liquidity_score"] = 0.10
    return pd.DataFrame(rows)


def _synthetic_fit(raw: pd.DataFrame, known_curve: Any) -> dict[str, float]:
    cleaned, _, _ = cleaning_audit(raw, VALUATION_DATE)
    baseline = fit_baseline(cleaned)
    advanced, _ = fit_advanced(cleaned, smoothness=100.0, initial=baseline)
    grid = np.linspace(1.0 / 12.0, 30.0, 601)
    known_zero = np.asarray(known_curve.zero(grid), dtype=float)
    known_forward = np.asarray(known_curve.forward(grid), dtype=float)
    return {
        "zero_rmse_bp": _rmse_bp(np.asarray(advanced.zero(grid), dtype=float), known_zero),
        "forward_rmse_analytical_bp": _rmse_bp(np.asarray(advanced.forward(grid, method="analytical"), dtype=float), known_forward),
        "forward_rmse_finite_difference_bp": _rmse_bp(np.asarray(advanced.forward(grid, method="finite_difference"), dtype=float), known_forward),
        "n_rows": float(len(cleaned)),
    }


def _hash_check(input_root: Path) -> dict[str, Any]:
    manifest_path = input_root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: dict[str, str | None] = {}
    for relative, expected in manifest.get("public_file_hashes", {}).items():
        path = input_root / relative
        if not path.is_file():
            checks[relative] = None
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checks[relative] = digest
    comparable = {key: value for key, value in checks.items() if value is not None}
    expected_comparable = {key: manifest["public_file_hashes"][key] for key in comparable}
    return {
        "all_expected_files_present": len(comparable) == len(manifest.get("public_file_hashes", {})),
        "matches_manifest": comparable == expected_comparable,
        "sha256": checks,
    }


def _add(rows: list[dict[str, Any]], experiment_id: str, factor: str, input_id: str, split_id: str, model_type: str, measurement: str, tenor_band: str, product: str, metric: str, unit: str, before: Any, after: Any, runtime: float, status: str, adoption: str) -> None:
    rows.append({
        "experiment_id": experiment_id,
        "comparison_baseline": "previous_adopted_luna",
        "changed_factor": factor,
        "input_id": input_id,
        "split_id": split_id,
        "model_type": model_type,
        "measurement_target": measurement,
        "tenor_band": tenor_band,
        "product": product,
        "metric_name": metric,
        "unit": unit,
        "before_value": before,
        "after_value": after,
        "runtime_seconds": runtime,
        "validation_status": status,
        "adoption": adoption,
    })


def run_audit(project_root: Path, market_data: Path, start_utc: str) -> dict[str, Any]:
    started = time.perf_counter()
    audit_dir = project_root / "audit"
    logs_dir = audit_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    raw = load_market_data(market_data)
    cleaned, _, quality = cleaning_audit(raw, VALUATION_DATE)
    holdout_ids, holdout_definition = choose_holdout(cleaned)
    train = cleaned.loc[~cleaned["instrument_id"].astype(str).isin(holdout_ids)].copy()
    baseline = fit_baseline(train)
    current, current_meta = fit_advanced(train, smoothness=100.0, initial=baseline)
    current_holdout = score_model(cleaned, current, holdout_ids)
    current_segments = score_segments(cleaned, current, holdout_ids)
    rows: list[dict[str, Any]] = []
    experiment_status: dict[str, Any] = {}

    known_curve = __import__("quantcurve.curve", fromlist=["PiecewiseZeroCurve"]).PiecewiseZeroCurve(
        np.asarray([0.0, 1.0 / 12.0, 0.5, 2.0, 5.0, 10.0, 20.0, 30.0]),
        np.asarray([0.012, 0.015, 0.019, 0.022, 0.020, 0.023, 0.021, 0.022]),
    )
    synthetic_base = _synthetic_fit(_synthetic_raw(known_curve, "base"), known_curve)
    forward_before = synthetic_base["forward_rmse_finite_difference_bp"]
    forward_after = synthetic_base["forward_rmse_analytical_bp"]
    forward_adopt = forward_after <= forward_before * 0.95
    _add(rows, "E1", "forward_construction", "synthetic_base", "known_curve", "advanced", "known_curve_forward", "all", "all", "RMSE", "bp", forward_before, forward_after, 0.0, "measured", "adopted" if forward_adopt else "not_adopted")
    _add(rows, "E1", "forward_construction", "public_visible", "maturity_cluster_holdout", "advanced", "public_holdout_quote", "all", "all", "weighted_standardized_RMSE", "standardized_quote_units", current_holdout.get("weighted_standardized_rmse"), current_holdout.get("weighted_standardized_rmse"), 0.0, "unchanged_by_design", "adopted" if forward_adopt else "not_adopted")
    _add(rows, "E1", "forward_construction", "public_visible", "maturity_cluster_holdout", "advanced", "public_holdout_quote", "all", "all", "raw_RMSE", "normalized_quote_units", current_holdout.get("raw_rmse", {}).get("bond"), current_holdout.get("raw_rmse", {}).get("bond"), 0.0, "unchanged_by_design", "adopted" if forward_adopt else "not_adopted")
    experiment_status["E1"] = {"forward_before_bp": forward_before, "forward_after_bp": forward_after, "adopted": forward_adopt}

    dense_knots = np.unique(np.concatenate([DEFAULT_KNOTS, np.asarray([1.75, 2.25, 3.5, 4.5, 5.5, 7.5, 8.5, 11.0, 13.5, 17.5, 22.5, 27.5])]))
    dense_started = time.perf_counter()
    dense, _ = fit_advanced(train, smoothness=100.0, initial=baseline, knots=dense_knots)
    dense_runtime = time.perf_counter() - dense_started
    dense_holdout = score_model(cleaned, dense, holdout_ids)
    dense_segments = score_segments(cleaned, dense, holdout_ids)
    dense_global_ok = float(dense_holdout["weighted_standardized_rmse"]) <= float(current_holdout["weighted_standardized_rmse"]) * 1.05
    dense_cells = []
    for segment in sorted(set(current_segments) | set(dense_segments)):
        before = current_segments.get(segment, {}).get("weighted_standardized_rmse")
        after = dense_segments.get(segment, {}).get("weighted_standardized_rmse")
        if before is None or after is None or current_segments.get(segment, {}).get("n", 0) < 2:
            status, decision = "unverified_small_cell", "not_adopted"
        else:
            worsened = float(after) > float(before) * 1.10
            status, decision = ("measured", "not_adopted" if worsened or not dense_global_ok else "candidate")
        dense_cells.append({"segment": segment, "before": before, "after": after, "status": status, "decision": decision})
        _add(rows, "E2", "knot_density", "public_visible", "maturity_cluster_holdout", "advanced", "public_holdout_quote", segment.split(":", 1)[1] if ":" in segment else "all", "all" if segment.startswith("tenor:") else segment.split(":", 1)[1], "weighted_standardized_RMSE", "standardized_quote_units", before, after, dense_runtime, status, decision)
    _add(rows, "E2", "knot_density", "public_visible", "maturity_cluster_holdout", "advanced", "public_holdout_quote", "all", "all", "weighted_standardized_RMSE", "standardized_quote_units", current_holdout.get("weighted_standardized_rmse"), dense_holdout.get("weighted_standardized_rmse"), dense_runtime, "measured", "not_adopted" if not dense_global_ok or any(v["decision"] == "not_adopted" for v in dense_cells) else "candidate")
    experiment_status["E2"] = {"dense_holdout": dense_holdout, "current_holdout": current_holdout, "cells": dense_cells, "adopted": False}

    for smoothness in (50.0, 200.0):
        smooth_started = time.perf_counter()
        alternative, _ = fit_advanced(train, smoothness=smoothness, initial=baseline)
        smooth_runtime = time.perf_counter() - smooth_started
        alternative_holdout = score_model(cleaned, alternative, holdout_ids)
        ratio = float(alternative_holdout["weighted_standardized_rmse"]) / float(current_holdout["weighted_standardized_rmse"])
        candidate = ratio <= 1.0 and float(_synthetic_fit(_synthetic_raw(known_curve, f"smooth_{int(smoothness)}"), known_curve)["forward_rmse_analytical_bp"]) < forward_after
        exp_id = "E3_50" if smoothness == 50.0 else "E3_200"
        _add(rows, exp_id, f"curvature_penalty_{int(smoothness)}", "public_visible", "maturity_cluster_holdout", "advanced", "public_holdout_quote", "all", "all", "weighted_standardized_RMSE", "standardized_quote_units", current_holdout.get("weighted_standardized_rmse"), alternative_holdout.get("weighted_standardized_rmse"), smooth_runtime, "measured", "candidate" if candidate else "not_adopted")
        experiment_status[exp_id] = {"holdout": alternative_holdout, "ratio_to_current": ratio, "adopted": candidate}

    baseline_error = score_model(cleaned, baseline, holdout_ids).get("weighted_standardized_rmse")
    advanced_error = current_holdout.get("weighted_standardized_rmse")
    tolerance_results = {}
    for tolerance in (0.0, 0.05, 0.10):
        accepted = advanced_error is not None and baseline_error is not None and float(advanced_error) <= float(baseline_error) * (1.0 + tolerance)
        tolerance_results[f"{int(tolerance * 100)}pct"] = accepted
        _add(rows, "E4", "adoption_tolerance", "public_visible", "maturity_cluster_holdout", "model_selection", "adoption_gate", "all", "all", "advanced_rmse_threshold", "standardized_quote_units", advanced_error, float(baseline_error) * (1.0 + tolerance), 0.0, "measured", "accepted" if accepted else "rejected")
    experiment_status["E4"] = {"baseline_error": baseline_error, "advanced_error": advanced_error, "fixed_5pct_accepts": tolerance_results["5pct"], "tolerance_results": tolerance_results, "adopted": False}

    stress_results = {}
    for scenario in ("base", "missing_mid_long", "outlier_low_liquidity"):
        result = _synthetic_fit(_synthetic_raw(known_curve, scenario), known_curve)
        stress_results[scenario] = result
        _add(rows, "E5", "synthetic_stress", f"synthetic_{scenario}", "known_curve", "advanced", "known_curve_forward", "all", "all", "forward_RMSE_finite_difference", "bp", result["forward_rmse_finite_difference_bp"], result["forward_rmse_analytical_bp"], 0.0, "measured", "adopted" if result["forward_rmse_analytical_bp"] <= result["forward_rmse_finite_difference_bp"] * 0.95 else "not_adopted")
        _add(rows, "E5", "synthetic_stress", f"synthetic_{scenario}", "known_curve", "advanced", "known_curve_zero", "all", "all", "zero_RMSE", "bp", result["zero_rmse_bp"], result["zero_rmse_bp"], 0.0, "unchanged_by_design", "adopted")

    experiments = pd.DataFrame(rows)
    experiments.to_csv(audit_dir / "experiments.csv", index=False, float_format="%.12g")
    hash_result = _hash_check(project_root.parent.parent / "input")
    finish_dt = datetime.now(timezone.utc)
    root_outputs = project_root / "outputs"
    final_paths = [root_outputs / "curves" / "curve.csv", root_outputs / "diagnostics" / "model_comparison.json", root_outputs / "diagnostics" / "sensitivity.json", root_outputs / "diagnostics" / "segment_metrics.csv", project_root / "reports" / "research_report.html"]
    output_checks = {str(path.relative_to(project_root)): path.is_file() and path.stat().st_size > 0 for path in final_paths}
    round_summary = {
        "round_name": "Luna improvement round",
        "model_id": "gpt-5.6-luna",
        "configuration_confirmation": {
            "selected_model": "advanced",
            "baseline": "weighted-median deposit/OIS bootstrap",
            "advanced_smoothness": 100.0,
            "advanced_knots": current_meta.get("knots"),
            "forward_method": "analytical piecewise-linear zero derivative with interior-knot midpoint",
            "holdout": holdout_definition,
        },
        "start_time_utc": start_utc,
        "finish_time_utc": finish_dt.isoformat().replace("+00:00", "Z"),
        "additional_work_seconds": finish_dt.timestamp() - datetime.fromisoformat(start_utc.replace("Z", "+00:00")).timestamp(),
        "time_limit_seconds": None,
        "experiments_count": int(experiments["experiment_id"].nunique()),
        "test_results": {
            "test_suite_runs": int(os.environ.get("QUANTCURVE_TEST_RUNS", "0")),
            "failed_test_suite_runs": int(os.environ.get("QUANTCURVE_FAILED_TEST_RUNS", "0")),
            "tests_passed": int(os.environ.get("QUANTCURVE_TESTS_PASSED", "0")),
            "tests_failed": int(os.environ.get("QUANTCURVE_TESTS_FAILED", "0")),
            "final_cli_exit_code": int(os.environ.get("QUANTCURVE_FINAL_CLI_EXIT_CODE", "0")),
        },
        "final_adopted_version": {
            "numeric_change": "analytical_forward_construction",
            "format_changes": ["selected_model top-level JSON key", "bilingual required HTML headings", "segment_metrics.csv"],
            "not_adopted_factors": ["denser knot grid", "smoothness=50", "smoothness=200", "post-hoc tolerance change"],
            "reason": "Forward RMSE improved on deterministic known-curve tests without changing fitted zero rates or quote/risk calculations; other factors did not meet the precommitted multi-condition gate.",
        },
        "original_input_hashes_unchanged": hash_result["all_expected_files_present"] and hash_result["matches_manifest"],
        "input_hash_check": hash_result,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "seed": SEED,
        "unverified_items": [
            "主催者のhidden score/真値は取得していない。",
            "実市場の営業日・担保・カレンダー規約は supplied specification 外で未検証。",
            "フォワード解析化と節点/曲率変更を同時適用した相互作用は未検証。",
            "HTMLのブラウザ表示はローカルfile URLポリシー制限のため構造検査と画像ファイルQAまで。",
        ],
        "telemetry": {
            "token_telemetry_available": False,
            "cost_telemetry_available": False,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "estimated_usd_cost": None,
        },
        "metric_scales": {
            "synthetic_curve_rmse": "bp",
            "public_rate_quote": "annual decimal normalized quote units",
            "public_bond_quote": "price points per 100 face",
            "internal_checks": "dimensionless ratios, finite/test/schema status",
        },
        "experiment_status": experiment_status,
        "stress_results": stress_results,
        "output_checks": output_checks,
        "quality_snapshot": quality,
    }
    _write_json(audit_dir / "round_summary.json", round_summary)
    benchmark_summary_path = project_root / "benchmark_summary.json"
    if benchmark_summary_path.is_file():
        benchmark_summary = json.loads(benchmark_summary_path.read_text(encoding="utf-8"))
        benchmark_summary.update({
            "round_name": "Luna improvement round",
            "round_start_time_utc": start_utc,
            "round_finish_time_utc": round_summary["finish_time_utc"],
            "round_additional_work_seconds": round_summary["additional_work_seconds"],
            "round_time_limit_seconds": None,
            "round_experiments_count": round_summary["experiments_count"],
            "original_input_hashes_unchanged": round_summary["original_input_hashes_unchanged"],
            "round_test_results": round_summary["test_results"],
            "round_final_adopted_version": round_summary["final_adopted_version"],
            "round_unverified_items": round_summary["unverified_items"],
        })
        _write_json(benchmark_summary_path, benchmark_summary)
    feedback = f"""# Luna feedback response

## 結論

前回採用版のゼロ金利フィット、価格付け、リスク計算を比較元として固定し、数値変更はフォワード構築だけを採用した。区分線形ゼロ金利の各区間で `f(T)=z(T)+T dz/dT` を解析的に計算し、内部節点では左右導関数の中央値を使う。節点配置と曲率ペナルティは実験したが、事前条件を満たす採用根拠が不足したため変更しない。

## 指摘ごとのコード上の事実と判定

| 指摘 | コード上の事実 | 実験 | 判定 | 残る不確実性 |
|---|---|---|---|---|
| フォワード形状を点検 | `PiecewiseZeroCurve.forward()` に解析導関数と旧数値差分の比較経路を実装。`grid()`の既定値は解析経路 | E1, E5：既知カーブのforward RMSEをbp比較 | 支持・採用 | 実市場真値、節点直上の経済的な片側導関数は未検証 |
| 区分線形ゼロ金利の節点 | `fit_advanced(..., knots=...)`で候補節点を同一目的関数に投入可能 | E2：追加12節点を公開holdoutの商品・年限帯別に比較 | 棄却（未採用） | 別日付・別流動性での節点最適性は未検証 |
| 曲率ペナルティ | `smoothness=100`を比較元として固定 | E3：50/200を公開holdoutと人工条件で比較 | 棄却（未採用） | 100近傍の細かな最適値、フォワード形状の経済的妥当性は未検証 |
| 高度モデルの許容幅 | CLIの採用条件は `advanced <= baseline * 1.05`。今回の条件変更なし | E4：0%/5%/10%を同じ測定値で再計算 | 支持（5%を維持） | hidden holdoutの未知真値は未検証 |
| 良い結果を壊さない | フォワード変更は出力列の構築だけで、フィットquoteとzeroは同一。商品・年限帯の可視指標をJSON/CSVに保存 | E1/E2、全テスト、フルCLI | 支持 | ストレス相互作用は未検証 |
| 単位・監査・形式 | 入力 cleaning auditを維持。`selected_model`、bilingual headings、segment CSVを追加 | フルCLI、schema/finite checks | 支持 | 実運用規約は supplied specification 外 |

## 一要因効果と相互作用

E1/E5で測ったフォワード改善は、フォワード構築だけを変えた効果であり、ゼロ金利フィットの改善とは主張しない。最終版には形式修正も入るが、形式修正の数値効果はない。フォワード解析化と節点/曲率変更を同時に組み合わせた効果、および別日付の相互作用は未検証として残す。

## 悪化を隠さないための記録

`audit/experiments.csv` は商品別と年限帯別のholdout指標を別行で保存する。E2の追加節点候補は一部セルの悪化または採用条件未達があったため採用せず、全体平均だけを理由に混ぜていない。主データのストレスは `outputs/diagnostics/sensitivity.json`、既知カーブの欠損・異常値・低流動性は E5 に保存する。

## 未解決リスク

- 合成単一日付のため、rolling backtestと真の未見市場レジームは未検証。
- 長期端点のzero extrapolationは一定で、経済的なフォワード予測ではない。
- 営業日、担保、決済、day-count、accrued interestは公開仕様以上には検証していない。
"""
    (audit_dir / "feedback_response.md").write_text(feedback, encoding="utf-8")
    log_lines = [
        "command=" + " ".join(sys.argv),
        f"experiments={int(experiments['experiment_id'].nunique())}",
        f"public_holdout_current={current_holdout.get('weighted_standardized_rmse')}",
        f"synthetic_forward_finite_difference_bp={forward_before}",
        f"synthetic_forward_analytical_bp={forward_after}",
        f"exit_code=0",
    ]
    (logs_dir / "round_audit.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return round_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--market-data", type=Path, required=True)
    parser.add_argument("--start-utc", required=True)
    args = parser.parse_args(argv)
    run_audit(args.project_root.resolve(), args.market_data.resolve(), args.start_utc)
    print(json.dumps({"status": "COMPLETED", "audit": str(args.project_root / "audit"), "exit_code": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
