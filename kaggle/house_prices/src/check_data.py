"""Data quality check for the House Prices competition.

Run:
    uv run --no-project --with pandas --with scikit-learn python src/check_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "house-prices-advanced-regression-techniques"

# Columns where NA means "feature absent" per data_description.txt
NA_MEANS_NONE = [
    "Alley", "BsmtQual", "BsmtCond", "BsmtExposure", "BsmtFinType1", "BsmtFinType2",
    "FireplaceQu", "GarageType", "GarageFinish", "GarageQual", "GarageCond",
    "PoolQC", "Fence", "MiscFeature", "MasVnrType",
]


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")

    print(f"train: {train.shape}, test: {test.shape}")
    print(f"duplicate Ids: train={train['Id'].duplicated().sum()}, test={test['Id'].duplicated().sum()}")
    print(f"train/test Id overlap: {len(set(train['Id']) & set(test['Id']))}")

    print("\n--- SalePrice ---")
    sp = train["SalePrice"]
    print(sp.describe().round(0).to_string())
    print(f"skew={sp.skew():.2f}  log1p skew={np.log1p(sp).skew():.2f}")

    print("\n--- Missing values (columns with any NA, % of rows) ---")
    rows = []
    for col in train.columns.drop(["Id", "SalePrice"]):
        tr_na = train[col].isna().mean() * 100
        te_na = test[col].isna().mean() * 100
        if tr_na > 0 or te_na > 0:
            kind = "absent-feature" if col in NA_MEANS_NONE else "true-missing"
            rows.append((col, str(train[col].dtype), round(tr_na, 1), round(te_na, 1), kind))
    miss = pd.DataFrame(rows, columns=["col", "dtype", "train_na%", "test_na%", "NA meaning"])
    print(miss.sort_values("train_na%", ascending=False).to_string(index=False))

    print("\n--- Category levels present only in test (unseen at fit time) ---")
    cat_cols = train.select_dtypes(include="object").columns
    for col in cat_cols:
        extra = set(test[col].dropna()) - set(train[col].dropna())
        if extra:
            print(f"{col}: {sorted(extra)}")

    print("\n--- GrLivArea outliers (large area, low price) ---")
    out = train[train["GrLivArea"] > 4000][["Id", "GrLivArea", "OverallQual", "SalePrice"]]
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
