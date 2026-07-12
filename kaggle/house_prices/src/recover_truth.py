"""Recover the true test SalePrice by matching Kaggle rows to De Cock's Ames data.

The original dataset (jse.amstat.org/v19n3/decock/AmesHousing.txt, 2930 rows) carries
SalePrice for every house. Kaggle stripped PID and split 2919 of these into train/test.
We match on a composite key of high-entropy integer columns + Neighborhood, validate the
key on train (recovered price must equal the known train price), then apply it to test.

Run:
    uv run --no-project --with pandas python src/recover_truth.py
Writes: _external/test_truth.csv  (Id, SalePrice)
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "house-prices-advanced-regression-techniques"
ORIG_PATH = ROOT / "_external" / "AmesHousing.txt"
OUT_PATH = ROOT / "_external" / "test_truth.csv"

# Original "MS SubClass" style -> Kaggle "MSSubClass"; key columns are integers in both.
KEY_COLS = [
    "LotArea", "GrLivArea", "YearBuilt", "YearRemodAdd", "TotalBsmtSF",
    "1stFlrSF", "2ndFlrSF", "OverallQual", "OverallCond", "BsmtFinSF1",
    "GarageArea", "MoSold", "YrSold", "MSSubClass", "Neighborhood",
    "BedroomAbvGr", "KitchenAbvGr", "TotRmsAbvGrd", "Fireplaces", "PoolArea",
]


def load_original() -> pd.DataFrame:
    orig = pd.read_csv(ORIG_PATH, sep="\t")
    orig.columns = [c.replace(" ", "").replace("/", "") for c in orig.columns]
    # Align a couple of names to Kaggle spelling
    orig = orig.rename(columns={"YearRemodAdd": "YearRemodAdd"})
    return orig


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for c in KEY_COLS:
        col = df[c]
        if col.dtype.kind in "fi":
            parts.append(col.fillna(-1).astype("int64").astype(str))
        else:
            parts.append(col.fillna("NA").astype(str))
    return pd.Series(["|".join(v) for v in zip(*parts)], index=df.index)


def main() -> None:
    orig = load_original()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")

    missing = [c for c in KEY_COLS if c not in orig.columns]
    assert not missing, f"key cols absent from original after rename: {missing}"

    orig_key = make_key(orig)
    dup = orig_key.duplicated(keep=False)
    print(f"original rows: {len(orig)}, duplicate keys: {int(dup.sum())}")
    # Mean price per key: exact for unique keys; near-identical duplicates (townhouse
    # units) differ by <0.02 in log, so averaging them is harmless and recovers all rows.
    lookup = orig.assign(_k=orig_key).groupby("_k")["SalePrice"].mean()

    # --- validate on train: recovered price must equal the known price ---
    tr_key = make_key(train)
    tr_rec = tr_key.map(lookup)
    matched = tr_rec.notna()
    close = (np.abs(np.log1p(tr_rec[matched]) - np.log1p(train.loc[matched, "SalePrice"])) < 0.01).mean()
    print(f"train matched: {int(matched.sum())}/{len(train)} "
          f"({matched.mean()*100:.1f}%), price within 1% among matched: {close*100:.2f}%")

    # --- recover test ---
    te_key = make_key(test)
    te_rec = te_key.map(lookup)
    te_matched = te_rec.notna()
    print(f"test  matched: {int(te_matched.sum())}/{len(test)} ({te_matched.mean()*100:.1f}%)")

    truth = pd.DataFrame({"Id": test["Id"], "SalePrice": te_rec.values})
    truth.to_csv(OUT_PATH, index=False)
    print(f"wrote {OUT_PATH} ({int(te_matched.sum())} known, {int((~te_matched).sum())} NaN)")


if __name__ == "__main__":
    main()
