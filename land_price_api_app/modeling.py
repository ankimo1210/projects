"""
modeling.py
公示地価データに対する簡易線形モデルの学習・推論。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import db
from config import PROCESSED_DIR

MODEL_PATH = PROCESSED_DIR / "valuation_model_public_notice.json"

FEATURE_COLUMNS = [
    "area_sqm",
    "life_convenience_score",
    "family_score",
    "negative_facility_score",
    "terrain_caution_score",
    "elevation_m",
    "nearest_water_m",
]


def prepare_public_notice_training_data(conn, year: int | None = None, limit: int = 20000) -> pd.DataFrame:
    where = []
    params: list[Any] = []
    if year is not None:
        where.append("lp.year = ?")
        params.append(year)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    query = f"""
        SELECT
            lp.point_id,
            lp.year,
            lp.price_yen_per_sqm,
            lp.area_sqm,
            lf.life_convenience_score,
            lf.family_score,
            lf.negative_facility_score,
            lf.terrain_caution_score,
            lf.elevation_m,
            lf.nearest_water_m
        FROM land_prices_public_notice lp
        JOIN public_notice_location_features plf
          ON lp.point_id = plf.point_id AND lp.year = plf.year
        JOIN location_features lf
          ON plf.location_key = lf.location_key
        {where_sql}
        LIMIT {int(limit)}
    """
    df = conn.execute(query, params).df()
    df = df.dropna(subset=["price_yen_per_sqm"])
    return df


def fit_linear_public_notice_model(df: pd.DataFrame) -> dict[str, Any]:
    train = df.copy()
    for col in FEATURE_COLUMNS:
        if col not in train.columns:
            train[col] = 0.0
    train[FEATURE_COLUMNS] = train[FEATURE_COLUMNS].fillna(0.0)
    train = train[(train["price_yen_per_sqm"] > 0)]
    if train.empty:
        raise ValueError("training data is empty")

    X = train[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = np.log(train["price_yen_per_sqm"].to_numpy(dtype=float))
    X = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)

    pred = X @ coef
    rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
    model = {
        "model_name": "linear_public_notice_v1",
        "feature_columns": FEATURE_COLUMNS,
        "intercept": float(coef[0]),
        "coefficients": {name: float(value) for name, value in zip(FEATURE_COLUMNS, coef[1:])},
        "rmse_log": rmse,
        "row_count": int(len(train)),
    }
    return model


def save_model(model: dict[str, Any], path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_model(path: Path = MODEL_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def predict_listing_fair_value(model: dict[str, Any], snapshot_row: dict[str, Any], feature_row: dict[str, Any]) -> float | None:
    unit_area_sqm = snapshot_row.get("unit_area_sqm")
    if unit_area_sqm is None or float(unit_area_sqm) <= 0:
        return None
    x = [1.0]
    for col in model["feature_columns"]:
        if col in snapshot_row:
            value = snapshot_row.get(col)
        else:
            value = feature_row.get(col)
        try:
            x.append(float(value) if value is not None else 0.0)
        except (TypeError, ValueError):
            x.append(0.0)
    intercept = float(model["intercept"])
    coefs = model["coefficients"]
    log_unit = intercept + sum(xi * float(coefs[name]) for xi, name in zip(x[1:], model["feature_columns"]))
    unit_price = float(np.exp(log_unit))
    return unit_price * float(unit_area_sqm)
