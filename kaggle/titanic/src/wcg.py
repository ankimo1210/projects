"""Titanic: gender rule + woman-child-group (WCG) survival model.

Default prediction is the gender rule (female -> 1, male -> 0). It is
overridden only where the training data gives strong group evidence:
  - a female whose surname group's women/boys ALL died in train -> 0
  - a boy (title "Master") whose surname group's women/boys ALL survived -> 1

Group statistics are computed from women/boys only. Validation uses 5-fold
out-of-fold evaluation where group stats come from the training folds alone.

Usage (from ~/Documents/projects):
    uv run python kaggle/titanic/src/wcg.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

DATA_DIR = Path(__file__).resolve().parents[1] / "titanic"
OUT_PATH = Path(__file__).resolve().parents[1] / "submission_wcg.csv"
SEED = 42


def add_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Title"] = out["Name"].str.extract(r",\s*([^.]*)\.", expand=False).str.strip()
    out["Surname"] = out["Name"].str.extract(r"^([^,]*),", expand=False).str.strip()
    out["IsWomanOrBoy"] = (out["Sex"] == "female") | (out["Title"] == "Master")
    return out


def group_rates(labeled: pd.DataFrame) -> pd.Series:
    """Survival rate per surname among women/boys with known labels."""
    wcb = labeled[labeled["IsWomanOrBoy"]]
    return wcb.groupby("Surname")["Survived"].mean()


def predict(df: pd.DataFrame, rates: pd.Series) -> np.ndarray:
    pred = (df["Sex"] == "female").astype(int).to_numpy().copy()
    rate = df["Surname"].map(rates)  # NaN if group has no labeled women/boys
    pred[(df["Sex"] == "female").to_numpy() & (rate == 0.0).to_numpy()] = 0
    pred[(df["Title"] == "Master").to_numpy() & (rate == 1.0).to_numpy()] = 1
    return pred


def main() -> None:
    train = add_keys(pd.read_csv(DATA_DIR / "train.csv"))
    test = add_keys(pd.read_csv(DATA_DIR / "test.csv"))
    y = train["Survived"].to_numpy()

    # Out-of-fold validation: group stats from training folds only
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof = np.empty(len(train), dtype=int)
    for tr_idx, va_idx in cv.split(train, y):
        rates = group_rates(train.iloc[tr_idx])
        oof[va_idx] = predict(train.iloc[va_idx], rates)
    gender_acc = ((train["Sex"] == "female").astype(int) == y).mean()
    oof_acc = (oof == y).mean()
    print(f"gender rule (train)     : {gender_acc:.4f}")
    print(f"WCG out-of-fold accuracy: {oof_acc:.4f}")

    # Final prediction: group stats from all of train
    rates = group_rates(train)
    pred = predict(test, rates)

    gender_pred = (test["Sex"] == "female").astype(int).to_numpy()
    flips = test[pred != gender_pred][["Name", "Sex", "Title", "Surname"]]
    print(f"\nflips vs gender rule: {len(flips)}")
    print(flips.to_string(index=False))

    sub = pd.DataFrame({"PassengerId": test["PassengerId"], "Survived": pred})
    sub.to_csv(OUT_PATH, index=False)
    print(f"\npredicted survival rate on test: {pred.mean():.4f}")
    print(f"wrote {OUT_PATH} ({len(sub)} rows)")


if __name__ == "__main__":
    main()
