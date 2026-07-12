"""Titanic v3: gender rule + travel-group survival + class-based child rule.

Improvements over wcg.py, grounded in data semantics:
  - Groups are connected components linking passengers who share an exact
    Ticket (captures nannies/servants/companions with different surnames)
    or share (Surname, Pclass) (family split across tickets, while avoiding
    collisions between same-surname families in different classes).
  - Boys (title "Master") in 1st/2nd class always survive: "women and
    children first" was fully honored there (12/12 in train).

Rules (default = gender rule):
  - female whose group's labeled women/boys ALL died  -> 0
  - Master whose group's labeled women/boys ALL lived -> 1
  - Master in Pclass 1 or 2                           -> 1
  - rule A: 3rd-class female, embarked S, solo ticket -> 0 (train: 41% survive)
  - rule B: 3rd-class female, embarked S, ticket group of 4+ -> 0 (train: 8%)
  Rules A/B are demographic priors and apply only when the passenger's group
  has no labeled surviving woman/boy (group evidence outranks the prior; e.g.
  the Dean family's infant boy survived in train, so its women stay "live").

Outputs submission_v3.csv (group rules only) and submission_v4.csv (+A+B).

Validation: 5-fold out-of-fold; group *labels* come from training folds only
(group structure uses no labels). Variants are compared on identical folds.

Usage (from ~/Documents/projects):
    uv run python kaggle/titanic/src/wcg2.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

DATA_DIR = Path(__file__).resolve().parents[1] / "titanic"
OUT_PATH = Path(__file__).resolve().parents[1] / "submission_v3.csv"
SEED = 42


def add_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Title"] = out["Name"].str.extract(r",\s*([^.]*)\.", expand=False).str.strip()
    out["Surname"] = out["Name"].str.extract(r"^([^,]*),", expand=False).str.strip()
    out["IsWomanOrBoy"] = (out["Sex"] == "female") | (out["Title"] == "Master")
    return out


def union_find_groups(both: pd.DataFrame) -> pd.Series:
    """Connected components over shared Ticket or shared (Surname, Pclass)."""
    parent = list(range(len(both)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for key in [both["Ticket"], both["Surname"] + "|" + both["Pclass"].astype(str)]:
        for idx in both.groupby(key.values).indices.values():
            for k in idx[1:]:
                union(int(idx[0]), int(k))

    return pd.Series([find(i) for i in range(len(both))], index=both.index)


def group_rates(labeled: pd.DataFrame) -> pd.Series:
    wcb = labeled[labeled["IsWomanOrBoy"]]
    return wcb.groupby("Group")["Survived"].mean()


def predict(df: pd.DataFrame, rates: pd.Series, p3s_rules: bool,
            master_class_rule: bool = True) -> np.ndarray:
    pred = (df["Sex"] == "female").astype(int).to_numpy().copy()
    rate = df["Group"].map(rates)
    is_female = (df["Sex"] == "female").to_numpy()
    is_master = (df["Title"] == "Master").to_numpy()
    pred[is_female & (rate == 0.0).to_numpy()] = 0
    pred[is_master & (rate == 1.0).to_numpy()] = 1
    if master_class_rule:
        pred[is_master & df["Pclass"].isin([1, 2]).to_numpy()] = 1
    if p3s_rules:
        p3f_s = (is_female & (df["Pclass"] == 3).to_numpy()
                 & (df["Embarked"] == "S").to_numpy())
        # demographic prior must not override group survival evidence
        p3f_s &= ~(rate > 0).fillna(False).to_numpy()
        pred[p3f_s & (df["TicketSize"] == 1).to_numpy()] = 0  # rule A
        pred[p3f_s & (df["TicketSize"] >= 4).to_numpy()] = 0  # rule B
    return pred


def oof_accuracy(train: pd.DataFrame, y: np.ndarray, p3s_rules: bool,
                 master_class_rule: bool = True) -> float:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof = np.empty(len(train), dtype=int)
    for tr_idx, va_idx in cv.split(train, y):
        rates = group_rates(train.iloc[tr_idx])
        oof[va_idx] = predict(train.iloc[va_idx], rates, p3s_rules, master_class_rule)
    return float((oof == y).mean())


def main() -> None:
    train = add_keys(pd.read_csv(DATA_DIR / "train.csv"))
    test = add_keys(pd.read_csv(DATA_DIR / "test.csv"))
    y = train["Survived"].to_numpy()

    both = pd.concat([train.drop(columns=["Survived"]), test], ignore_index=True)
    groups = union_find_groups(both)
    both["TicketSize"] = both.groupby("Ticket")["Name"].transform("size")
    train["Group"] = groups.iloc[: len(train)].values
    test["Group"] = groups.iloc[len(train):].values
    train["TicketSize"] = both["TicketSize"].iloc[: len(train)].values
    test["TicketSize"] = both["TicketSize"].iloc[len(train):].values

    # Also evaluate the old surname-only grouping on identical folds
    train_sn = train.assign(Group=train["Surname"])
    print(f"OOF surname groups (=v2)          : {oof_accuracy(train_sn, y, False, False):.4f}")
    print(f"OOF v3 (components + master-class): {oof_accuracy(train, y, False):.4f}")
    print(f"OOF v4 (v3 + P3-S female rules)   : {oof_accuracy(train, y, True):.4f}")

    rates = group_rates(train)
    gender_pred = (test["Sex"] == "female").astype(int).to_numpy()
    for name, p3s in [("submission_v3.csv", False), ("submission_v4.csv", True)]:
        pred = predict(test, rates, p3s_rules=p3s)
        sub = pd.DataFrame({"PassengerId": test["PassengerId"], "Survived": pred})
        out = Path(__file__).resolve().parents[1] / name
        sub.to_csv(out, index=False)
        print(f"\n{name}: {int((pred != gender_pred).sum())} flips vs gender rule, "
              f"survival rate {pred.mean():.4f}")

    flips = test.loc[pred != gender_pred, ["Name", "Pclass", "Sex", "Title", "TicketSize"]].copy()
    flips["NewPred"] = pred[pred != gender_pred]
    print("\nv4 flips vs gender rule:")
    print(flips.to_string(index=False))


if __name__ == "__main__":
    main()
