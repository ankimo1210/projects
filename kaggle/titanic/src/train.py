"""Titanic survival prediction.

Compares a gender-rule baseline, logistic regression, random forest, and
HistGradientBoosting with stratified 5-fold CV (accuracy = competition metric),
then fits the best model on the full training set and writes submission.csv.

Usage (from ~/Documents/projects):
    uv run python kaggle/titanic/src/train.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_DIR = Path(__file__).resolve().parents[1] / "titanic"
OUT_PATH = Path(__file__).resolve().parents[1] / "submission.csv"
SEED = 42

TITLE_MAP = {
    "Mr": "Mr", "Mrs": "Mrs", "Miss": "Miss", "Master": "Master",
    "Ms": "Miss", "Mlle": "Miss", "Mme": "Mrs",
    "Dr": "Rare", "Rev": "Rare", "Col": "Rare", "Major": "Rare",
    "Capt": "Rare", "Sir": "Rare", "Lady": "Rare", "Don": "Rare",
    "Dona": "Rare", "Countess": "Rare", "Jonkheer": "Rare",
}

NUM_COLS = ["Age", "Fare", "SibSp", "Parch", "FamilySize", "TicketGroup"]
CAT_COLS = ["Pclass", "Sex", "Embarked", "Title", "IsAlone", "HasCabin"]


def build_features(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    both = pd.concat([train.drop(columns=["Survived"]), test], ignore_index=True)
    # Ticket group size uses train+test jointly (no labels involved)
    ticket_counts = both["Ticket"].value_counts()

    def transform(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        title = out["Name"].str.extract(r",\s*([^.]*)\.", expand=False).str.strip()
        out["Title"] = title.map(TITLE_MAP).fillna("Rare")
        out["FamilySize"] = out["SibSp"] + out["Parch"] + 1
        out["IsAlone"] = (out["FamilySize"] == 1).astype(int)
        out["TicketGroup"] = out["Ticket"].map(ticket_counts).clip(upper=8)
        out["HasCabin"] = out["Cabin"].notna().astype(int)
        out["Embarked"] = out["Embarked"].fillna("S")  # mode; only 2 missing
        return out[NUM_COLS + CAT_COLS]

    return transform(train), transform(test)


def make_pipeline(model) -> Pipeline:
    scale = isinstance(model, LogisticRegression)
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))
    pre = ColumnTransformer([
        ("num", Pipeline(num_steps), NUM_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
    ])
    return Pipeline([("pre", pre), ("model", model)])


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    y = train["Survived"]
    X_train, X_test = build_features(train, test)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    # Baseline: predict survival iff female
    baseline_pred = (train["Sex"] == "female").astype(int)
    baseline_acc = (baseline_pred == y).mean()
    print(f"baseline (sex rule)         : {baseline_acc:.4f}")

    models = {
        "logistic_regression": LogisticRegression(max_iter=2000, C=1.0),
        "random_forest": RandomForestClassifier(
            n_estimators=500, min_samples_leaf=3, random_state=SEED, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.06, max_iter=400,
            l2_regularization=1.0, random_state=SEED,
        ),
    }

    results = {}
    for name, model in models.items():
        scores = cross_val_score(make_pipeline(model), X_train, y, cv=cv, scoring="accuracy")
        results[name] = (scores.mean(), scores.std())
        print(f"{name:<28}: {scores.mean():.4f} +/- {scores.std():.4f}")

    best_name = max(results, key=lambda k: results[k][0])
    assert results[best_name][0] > baseline_acc, "best model does not beat the sex-rule baseline"
    print(f"\nbest model: {best_name} (CV {results[best_name][0]:.4f})")

    pipe = make_pipeline(models[best_name])
    pipe.fit(X_train, y)
    pred = pipe.predict(X_test)

    sub = pd.DataFrame({"PassengerId": test["PassengerId"], "Survived": pred})
    sub.to_csv(OUT_PATH, index=False)
    print(f"predicted survival rate on test: {pred.mean():.4f}")
    print(f"wrote {OUT_PATH} ({len(sub)} rows)")


if __name__ == "__main__":
    main()
