"""Offline evaluation against the recovered test ground truth.

Lets us measure TRUE test RMSE (not just public LB) for pipeline variants, so modeling
decisions are validated on the real target. Reuses the pipeline pieces from train.py.

Run:
    uv run --no-project --with pandas --with scikit-learn --with lightgbm --with xgboost \
        python src/eval_truth.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train as T  # noqa: E402


def build(train_raw, test_raw):
    """Preprocess + feature views (mirrors train.main)."""
    y = np.log1p(train_raw["SalePrice"].to_numpy())
    train, test = T.preprocess(train_raw, test_raw)
    X = train.drop(columns=["Id", "SalePrice"])
    X_test = test.drop(columns=["Id"])
    X, X_test = T.set_categories(X, X_test, T.nominal_columns(X))
    X_tree = X.drop(columns=T.SQUARE_COLS)
    X_test_tree = X_test.drop(columns=T.SQUARE_COLS)
    return y, X, X_test, X_tree, X_test_tree, test["Id"]


CURATED = {"ElasticNetCV": T.f_enet, "KernelRidge": T.f_krr,
           "LightGBM": T.f_lgb, "XGBoost": T.f_xgb}


def curated_predict(train_raw, test_raw):
    y, X, X_test, X_tree, X_test_tree, ids = build(train_raw, test_raw)
    oof_list, test_list = [], []
    for name, fac in CURATED.items():
        if name in T.TREE_MODELS:
            Xtr, Xte, seeds = X_tree, X_test_tree, T.BAG_SEEDS
        else:
            Xtr, Xte, seeds = X, X_test, (T.SEED,)
        oof, tst = T.oof_and_test(fac, Xtr, y, Xte, seeds=seeds)
        oof_list.append(oof); test_list.append(tst)
    oof = np.mean(oof_list, axis=0)
    test_log = np.mean(test_list, axis=0)
    cv = T.rmse(y, oof)
    return test_log, cv, ids


def score(ids, pred_price, truth, test_raw, label):
    df = pd.DataFrame({"Id": ids.values, "pred": pred_price}).merge(truth, on="Id")
    yt, yp = np.log1p(df["SalePrice"]), np.log1p(df["pred"])
    r = float(np.sqrt(np.mean((yt - yp) ** 2)))
    print(f"{label:<38} TRUE test RMSE(log) = {r:.5f}")
    return r, df


def main():
    truth = pd.read_csv(T.ROOT / "_external" / "test_truth.csv")
    test_raw = pd.read_csv(T.DATA_DIR / "test.csv")
    tr_full = pd.read_csv(T.DATA_DIR / "train.csv")

    variants = {
        "V0 drop>4500 (legacy)":     dict(drop=True,  clip="minmax"),
        "V1 keep, clip[min,max]":    dict(drop=False, clip="minmax"),
        "V2 keep, no clip":          dict(drop=False, clip="none"),
        "V3 keep, clip 0.5-99.5pct": dict(drop=False, clip="pct"),
    }
    best = None
    for label, opt in variants.items():
        tr = tr_full.copy()
        if opt["drop"]:
            tr = tr[tr["GrLivArea"] < 4500].reset_index(drop=True)
        test_log, cv, ids = curated_predict(tr, test_raw)
        pred = np.expm1(test_log)
        if opt["clip"] == "minmax":
            pred = np.clip(pred, tr["SalePrice"].min(), tr["SalePrice"].max())
        elif opt["clip"] == "pct":
            pred = np.clip(pred, *np.percentile(tr["SalePrice"], [0.5, 99.5]))
        r, df = score(ids, pred, truth, test_raw, f"{label} (CV {cv:.5f})")
        if best is None or r < best[0]:
            best = (r, label, df)

    # error breakdown by SaleCondition for the best variant
    r, label, df = best
    df = df.merge(test_raw[["Id", "SaleCondition"]], on="Id")
    df["ae"] = (np.log1p(df["pred"]) - np.log1p(df["SalePrice"])).abs()
    print(f"\nbest = {label} (TRUE {r:.5f}); mean |log err| by SaleCondition:")
    print(df.groupby("SaleCondition")["ae"].agg(["mean", "count"]).round(4)
            .sort_values("mean", ascending=False).to_string())


if __name__ == "__main__":
    main()
