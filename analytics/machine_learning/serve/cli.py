"""CLI: predict survival for one passenger.

    PYTHONPATH=src python -m serve.cli --pclass 1 --sex female --fare 100 --embarked C
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ml_textbook.pipelines import load_pipeline

from .train import DEFAULT_MODEL_PATH, FEATURE_COLUMNS, train_pipeline

NUMERIC = ["pclass", "age", "sibsp", "parch", "fare"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Predict Titanic survival for one passenger.")
    ap.add_argument("--pclass", type=int, required=True, choices=[1, 2, 3])
    ap.add_argument("--sex", required=True, choices=["male", "female"])
    ap.add_argument("--age", type=float, default=None)
    ap.add_argument("--sibsp", type=int, default=0)
    ap.add_argument("--parch", type=int, default=0)
    ap.add_argument("--fare", type=float, required=True)
    ap.add_argument("--embarked", default=None, choices=["S", "C", "Q", None])
    args = ap.parse_args(argv)

    path = Path(DEFAULT_MODEL_PATH)
    model = load_pipeline(str(path)) if path.exists() else train_pipeline()
    df = pd.DataFrame([{k: getattr(args, k) for k in FEATURE_COLUMNS}])
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    proba = float(model.predict_proba(df)[0, 1])
    print(json.dumps({"survived": int(proba >= 0.5), "probability": round(proba, 4)}))


if __name__ == "__main__":
    main()
