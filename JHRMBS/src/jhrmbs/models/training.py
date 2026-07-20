from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from jhrmbs.artifacts import read_table, write_table
from jhrmbs.config import AppConfig
from jhrmbs.exceptions import ModelError
from jhrmbs.metrics import psj_cpr, smm_to_cpr
from jhrmbs.models.fractional_logit import FractionalLogitModel
from jhrmbs.paths import DataPaths
from jhrmbs.util import atomic_write_json, read_json, timestamp_id, utc_now

LOGGER = logging.getLogger("jhrmbs.models.training")

MODEL_SPECS: dict[str, tuple[str, ...]] = {
    "seasoning": ("seasoning_ratio",),
    "rate": ("seasoning_ratio", "rate_feature_pct"),
    "full": (
        "seasoning_ratio",
        "rate_feature_pct",
        "burnout_lag1",
        "month_sin",
        "month_cos",
        "vintage_year_numeric",
        "housing_starts_yoy_pct",
        "m3_yoy_pct",
    ),
}


@dataclass(frozen=True)
class Split:
    name: str
    train_mask: pd.Series
    test_mask: pd.Series
    description: str


def make_splits(frame: pd.DataFrame, config: AppConfig) -> list[Split]:
    months = sorted(pd.Timestamp(month) for month in frame["payment_month"].dropna().unique())
    if len(months) <= config.models.time_test_months:
        raise ModelError("not enough distinct months for the configured time holdout")
    time_cutoff = months[-config.models.time_test_months]
    time_train = frame["payment_month"] < time_cutoff
    time_test = frame["payment_month"] >= time_cutoff

    maximum_vintage = int(frame["vintage_year"].max())
    vintage_cutoff = maximum_vintage - config.models.vintage_test_years + 1
    vintage_train = frame["vintage_year"] < vintage_cutoff
    vintage_test = frame["vintage_year"] >= vintage_cutoff
    return [
        Split(
            "time",
            time_train,
            time_test,
            f"train before {time_cutoff:%Y-%m}; test from {time_cutoff:%Y-%m}",
        ),
        Split(
            "vintage",
            vintage_train,
            vintage_test,
            f"train vintages before {vintage_cutoff}; test vintages {vintage_cutoff}+",
        ),
    ]


def select_champion(metrics: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Select a fitted model by cross-split rank, then mean and worst RMSE.

    Fixed PSJ remains a benchmark but cannot be selected as the fitted forecast
    model because it has no serialized estimator.
    """
    candidates = metrics[metrics["model"].isin(MODEL_SPECS)].copy()
    if candidates.empty:
        raise ModelError("no fitted-model metrics are available for champion selection")
    split_count = int(candidates["split"].nunique())
    candidates["split_rank"] = candidates.groupby("split")["weighted_rmse_cpr_pct"].rank(
        method="min"
    )
    selection = candidates.groupby("model", as_index=False).agg(
        evaluated_splits=("split", "nunique"),
        mean_split_rank=("split_rank", "mean"),
        mean_weighted_rmse_cpr_pct=("weighted_rmse_cpr_pct", "mean"),
        worst_weighted_rmse_cpr_pct=("weighted_rmse_cpr_pct", "max"),
    )
    selection = (
        selection[selection["evaluated_splits"] == split_count]
        .sort_values(
            [
                "mean_split_rank",
                "mean_weighted_rmse_cpr_pct",
                "worst_weighted_rmse_cpr_pct",
                "model",
            ]
        )
        .reset_index(drop=True)
    )
    if selection.empty:
        raise ModelError("no model was evaluated on every configured split")
    selection.insert(0, "selection_rank", range(1, len(selection) + 1))
    return str(selection.loc[0, "model"]), selection


def _weighted_metrics(
    target: np.ndarray, prediction: np.ndarray, weights: np.ndarray
) -> dict[str, float]:
    error = prediction - target
    normalized_weight = weights / weights.sum()
    return {
        "mae_cpr_pct": float(np.mean(np.abs(error))),
        "rmse_cpr_pct": float(np.sqrt(np.mean(error**2))),
        "weighted_mae_cpr_pct": float(np.sum(normalized_weight * np.abs(error))),
        "weighted_rmse_cpr_pct": float(np.sqrt(np.sum(normalized_weight * error**2))),
    }


def _cashflow_metrics(test: pd.DataFrame, predicted_smm: np.ndarray) -> dict[str, float]:
    working = test.copy()
    working["predicted_smm"] = predicted_smm
    scheduled_balance = working["face_amount_jpy"] * working["scheduled_surviving_factor"]
    beginning_balance = working["face_amount_jpy"] * working["factor_lag1"]
    scheduled_principal = (beginning_balance - scheduled_balance).clip(lower=0.0)
    predicted_principal = scheduled_principal + scheduled_balance * working["predicted_smm"]
    actual_principal = (
        working["face_amount_jpy"] * (working["factor_lag1"] - working["actual_factor"])
    ).clip(lower=0.0)
    working["predicted_principal"] = predicted_principal
    working["actual_principal"] = actual_principal

    cumulative_errors: list[float] = []
    wal_errors: list[float] = []
    for _, issue in working.groupby("issue_id"):
        issue = issue.sort_values("payment_month")
        opening = float(issue["face_amount_jpy"].iloc[0] * issue["factor_lag1"].iloc[0])
        if opening <= 0:
            continue
        cumulative_errors.append(
            abs(float(issue["predicted_principal"].sum() - issue["actual_principal"].sum()))
            / opening
            * 100.0
        )
        first_month = pd.Timestamp(issue["payment_month"].min())
        times = (issue["payment_month"] - first_month).dt.days.to_numpy(float) / 365.25 + 1.0 / 12.0
        actual = issue["actual_principal"].to_numpy(float)
        predicted = issue["predicted_principal"].to_numpy(float)
        if actual.sum() > 0.0 and predicted.sum() > 0.0:
            actual_wal = float(times @ actual / actual.sum())
            predicted_wal = float(times @ predicted / predicted.sum())
            wal_errors.append(abs(predicted_wal - actual_wal))
    return {
        "cashflow_cumulative_principal_mae_pct": float(np.mean(cumulative_errors))
        if cumulative_errors
        else float("nan"),
        "truncated_wal_mae_years": float(np.mean(wal_errors)) if wal_errors else float("nan"),
    }


def _evaluate_one(
    test: pd.DataFrame,
    predicted_smm: np.ndarray,
) -> dict[str, float]:
    target_cpr_pct = np.asarray(smm_to_cpr(test["target_smm"].to_numpy(float))) * 100.0
    predicted_cpr_pct = np.asarray(smm_to_cpr(predicted_smm)) * 100.0
    weights = test["exposure_jpy"].to_numpy(float)
    metrics = _weighted_metrics(target_cpr_pct, predicted_cpr_pct, weights)
    metrics.update(_cashflow_metrics(test, predicted_smm))
    return metrics


def ensure_rate_definition_coverage(frame: pd.DataFrame, rate_feature_mode: str) -> None:
    """Require one mortgage-rate definition to cover at least 90% of training rows.

    Rows with a missing rate or a missing definition count against coverage, so a
    mixture of series definitions can never silently share one coefficient.
    """
    if rate_feature_mode != "mortgage_rate" or frame.empty:
        return
    definitions = (
        frame["mortgage_rate_definition"]
        if "mortgage_rate_definition" in frame.columns
        else pd.Series(index=frame.index, dtype=object)
    )
    valued = frame["rate_feature_pct"].notna() & definitions.notna()
    counts = definitions[valued].value_counts()
    coverage = float(counts.iloc[0]) / float(len(frame)) if not counts.empty else 0.0
    if coverage < 0.90:
        dominant = str(counts.index[0]) if not counts.empty else "none"
        raise ModelError(
            "mortgage_rate mode requires one mortgage-rate definition to cover at least "
            f"90% of training rows; best coverage={coverage:.1%} ({dominant})"
        )


def _training_frame(config: AppConfig) -> pd.DataFrame:
    path = DataPaths(config.data_root).features / "model_features.parquet"
    frame = read_table(path)
    eligible = (
        frame["target_smm"].notna()
        & frame["exposure_jpy"].notna()
        & (frame["exposure_jpy"] > 0.0)
        & (frame["series_type"] == "monthly")
    )
    result = frame[eligible].sort_values(["payment_month", "issue_id"]).reset_index(drop=True)
    ensure_rate_definition_coverage(result, config.features.rate_feature_mode)
    if len(result) < config.models.minimum_train_rows:
        raise ModelError(
            f"学習可能行が不足しています: {len(result)} < {config.models.minimum_train_rows}"
        )
    return result


def train_models(config: AppConfig) -> Path:
    frame = _training_frame(config)
    paths = DataPaths(config.data_root)
    run_id = timestamp_id()
    run_directory = paths.models / run_id
    model_directory = run_directory / "models"
    model_directory.mkdir(parents=True, exist_ok=False)
    np.random.seed(config.models.random_seed)

    metric_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    splits = make_splits(frame, config)
    for split in splits:
        train = frame[split.train_mask].copy()
        test = frame[split.test_mask].copy()
        if len(train) < config.models.minimum_train_rows or test.empty:
            raise ModelError(
                f"split {split.name} is too small: train={len(train)} test={len(test)}"
            )
        for model_name in ("fixed_psj", *MODEL_SPECS):
            if model_name == "fixed_psj":
                predicted_cpr = psj_cpr(
                    test["prediction_wala_months"].to_numpy(float),
                    config.models.fixed_psj_terminal_cpr_pct / 100.0,
                    seasoning_months=config.features.psj_seasoning_months,
                )
                predicted_smm = np.asarray(
                    1.0 - np.power(1.0 - np.asarray(predicted_cpr), 1.0 / 12.0)
                )
            else:
                model = FractionalLogitModel(
                    feature_names=MODEL_SPECS[model_name],
                    l2_penalty=config.models.l2_penalty,
                ).fit(
                    train,
                    train["target_smm"],
                    sample_weight=train["exposure_jpy"],
                )
                predicted_smm = model.predict_smm(test)
            metrics = _evaluate_one(test, predicted_smm)
            metric_rows.append(
                {
                    "split": split.name,
                    "split_description": split.description,
                    "model": model_name,
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "test_issues": int(test["issue_id"].nunique()),
                    "rate_proxy_share": float(test["rate_feature_is_proxy"].mean()),
                    **metrics,
                }
            )
            audit = test[
                ["issue_id", "payment_month", "target_smm", "exposure_jpy", "actual_factor"]
            ].copy()
            audit["predicted_smm"] = predicted_smm
            audit["split"] = split.name
            audit["model"] = model_name
            prediction_frames.append(audit)

    final_models: dict[str, dict[str, Any]] = {}
    for model_name, feature_names in MODEL_SPECS.items():
        model = FractionalLogitModel(
            feature_names=feature_names,
            l2_penalty=config.models.l2_penalty,
        ).fit(frame, frame["target_smm"], sample_weight=frame["exposure_jpy"])
        model_path = model_directory / f"{model_name}.json"
        metadata = {
            "run_id": run_id,
            "model_name": model_name,
            "target": "monthly voluntary SMM in decimal units",
            "training_start": str(frame["payment_month"].min().date()),
            "training_end": str(frame["payment_month"].max().date()),
            "training_issues": int(frame["issue_id"].nunique()),
            "feature_timing": "pool state and public macro inputs lagged by one month",
        }
        model.save(model_path, metadata=metadata)
        final_models[model_name] = {"path": str(model_path), "features": list(feature_names)}

    metrics_frame = pd.DataFrame(metric_rows).sort_values(["split", "weighted_rmse_cpr_pct"])
    champion_model, selection = select_champion(metrics_frame)
    write_table(metrics_frame, run_directory / "metrics.parquet")
    write_table(selection, run_directory / "model_selection.parquet")
    write_table(
        pd.concat(prediction_frames, ignore_index=True), run_directory / "oos_predictions.parquet"
    )
    feature_metadata = read_json(paths.features / "model_features.metadata.json", {})
    run_metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": utc_now().isoformat(),
        "random_seed": config.models.random_seed,
        "model_configuration": asdict(config.models),
        "feature_configuration": asdict(config.features),
        "fixed_psj_terminal_cpr_pct": config.models.fixed_psj_terminal_cpr_pct,
        "champion_model": champion_model,
        "champion_rule": (
            "lowest mean within-split weighted-RMSE rank; ties by mean RMSE, "
            "worst-split RMSE, then model name"
        ),
        "training_rows": len(frame),
        "training_issues": int(frame["issue_id"].nunique()),
        "feature_artifact_sha256": feature_metadata.get("sha256")
        if isinstance(feature_metadata, dict)
        else None,
        "splits": [{"name": split.name, "description": split.description} for split in splits],
        "models": final_models,
        "limitations": [
            (
                "rate_feature_pct has one definition per run; default jgb_proxy is not a "
                "borrower refinancing rate"
            ),
            "truncated WAL is measured only over the observed OOS window",
            "pool-level model does not identify borrower-level competing risks",
        ],
    }
    atomic_write_json(run_directory / "run.json", run_metadata)
    atomic_write_json(
        paths.models / "latest_run.json",
        {"run_id": run_id, "run_path": str(run_directory.relative_to(config.data_root))},
    )
    LOGGER.info("trained run %s rows=%d", run_id, len(frame))
    return run_directory


def resolve_run_directory(config: AppConfig, run_id: str | None = None) -> Path:
    paths = DataPaths(config.data_root)
    if run_id:
        directory = paths.models / run_id
    else:
        pointer = read_json(paths.models / "latest_run.json", {})
        if not isinstance(pointer, dict) or not pointer.get("run_path"):
            raise ModelError("学習済みrunがありません。先に jhrmbs train を実行してください。")
        directory = config.data_root / str(pointer["run_path"])
    if not (directory / "run.json").is_file():
        raise ModelError(f"invalid model run: {directory}")
    return directory


def load_model(
    config: AppConfig, model_name: str = "full", run_id: str | None = None
) -> FractionalLogitModel:
    selected = resolve_model_name(config, model_name, run_id)
    return FractionalLogitModel.load(
        resolve_run_directory(config, run_id) / "models" / f"{selected}.json"
    )


def resolve_model_name(
    config: AppConfig, model_name: str = "champion", run_id: str | None = None
) -> str:
    if model_name != "champion":
        if model_name not in MODEL_SPECS:
            raise ModelError(f"unknown fitted model: {model_name}")
        return model_name
    run = read_json(resolve_run_directory(config, run_id) / "run.json", {})
    selected = run.get("champion_model") if isinstance(run, dict) else None
    if selected not in MODEL_SPECS:
        raise ModelError("model run does not contain a valid champion_model")
    return str(selected)
