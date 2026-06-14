"""Train the Titanic survival pipeline and persist it for serving.

Run from the project directory:

    PYTHONPATH=src python -m serve.train          # writes serve/model.joblib
"""

from __future__ import annotations

from pathlib import Path

from ml_textbook import datasets, pipelines, preprocessing
from ml_textbook.models import get_logistic_regression

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"

# Columns the service expects, in the order the pipeline was trained on.
FEATURE_COLUMNS = ["pclass", "sex", "age", "sibsp", "parch", "fare", "embarked"]


def train_pipeline(seed: int = 0):
    """Fit the preprocessing+model pipeline on the synthetic Titanic data."""
    X, y = datasets.make_titanic_like_dataset(n=900, seed=seed)
    numeric, categorical = preprocessing.split_feature_types(X)
    pipe = pipelines.make_full_pipeline(numeric, categorical, get_logistic_regression())
    return pipe.fit(X, y)


def main(path: str | Path = DEFAULT_MODEL_PATH) -> None:
    pipe = train_pipeline()
    pipelines.save_pipeline(pipe, str(path))
    print(f"saved model to {path}")


if __name__ == "__main__":
    main()
