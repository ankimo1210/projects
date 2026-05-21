"""
train_valuation_model.py
公示地価 + 付与済み location_features から簡易線形モデルを学習して保存する。
"""
from __future__ import annotations

import argparse

import db
from modeling import fit_linear_public_notice_model, prepare_public_notice_training_data, save_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--limit", type=int, default=20000)
    args = parser.parse_args()

    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    df = prepare_public_notice_training_data(conn, year=args.year, limit=args.limit)
    model = fit_linear_public_notice_model(df)
    path = save_model(model)
    conn.close()
    print({"saved_to": str(path), "rows": model["row_count"], "rmse_log": model["rmse_log"]})


if __name__ == "__main__":
    main()
