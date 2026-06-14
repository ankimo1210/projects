"""FastAPI inference service for the Titanic survival pipeline.

Run from the project directory:

    PYTHONPATH=src uvicorn serve.app:app --reload
    # then POST to http://127.0.0.1:8000/predict  (see /docs)

The pipeline ingests *raw* passenger fields (missing age / categories allowed) —
all preprocessing happens inside the saved ``Pipeline``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from ml_textbook.pipelines import load_pipeline

from .train import DEFAULT_MODEL_PATH, FEATURE_COLUMNS, train_pipeline

NUMERIC = ["pclass", "age", "sibsp", "parch", "fare"]


class Passenger(BaseModel):
    """One raw passenger record (age / embarked may be missing)."""

    pclass: int = Field(..., ge=1, le=3, description="ticket class 1/2/3")
    sex: str = Field(..., description="'male' or 'female'")
    age: float | None = None
    sibsp: int = 0
    parch: int = 0
    fare: float = Field(..., ge=0)
    embarked: str | None = None


class Prediction(BaseModel):
    survived: int
    probability: float


def _load_or_train():
    path = Path(DEFAULT_MODEL_PATH)
    return load_pipeline(str(path)) if path.exists() else train_pipeline()


def _to_frame(passenger: Passenger) -> pd.DataFrame:
    df = pd.DataFrame([passenger.model_dump()])[FEATURE_COLUMNS]
    # Force numeric dtype so a missing age (None) becomes NaN for the imputer.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def create_app(model=None) -> FastAPI:
    """Build the app. Pass ``model`` to inject a pre-fit pipeline (used in tests)."""
    app = FastAPI(title="ml-textbook — Titanic survival service", version="0.1.0")
    state = {"model": model if model is not None else _load_or_train()}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/predict", response_model=Prediction)
    def predict(passenger: Passenger) -> Prediction:
        proba = float(state["model"].predict_proba(_to_frame(passenger))[0, 1])
        return Prediction(survived=int(proba >= 0.5), probability=round(proba, 4))

    return app


app = create_app()
