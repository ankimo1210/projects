from __future__ import annotations

import pandas as pd

from src.utils.sources import PROJECT_ROOT


SHAREHOLDERS = [
    {"shareholder": "Kiyohisa Kato", "shares": 554400, "ownership_pct": 0.0999},
    {"shareholder": "Mitsubishi Electric Corporation", "shares": 350000, "ownership_pct": 0.0630},
    {"shareholder": "KDDI Corporation", "shares": 280000, "ownership_pct": 0.0504},
    {"shareholder": "Treasury shares", "shares": 268816, "ownership_pct": 0.0484},
    {"shareholder": "AT Co., Ltd.", "shares": 254000, "ownership_pct": 0.0457},
    {"shareholder": "Kaoru Sasaki", "shares": 200000, "ownership_pct": 0.0360},
    {"shareholder": "Kazuhisa Ando", "shares": 120000, "ownership_pct": 0.0216},
    {"shareholder": "Masato Kagami", "shares": 103000, "ownership_pct": 0.0185},
    {"shareholder": "TimeTicket Inc.", "shares": 101000, "ownership_pct": 0.0182},
    {"shareholder": "Jun Kato", "shares": 84316, "ownership_pct": 0.0151},
]


def build_shareholders() -> pd.DataFrame:
    df = pd.DataFrame(SHAREHOLDERS)
    df["source_id"] = "official_stock_status"
    df["source_type"] = "sourced"
    return df


def main() -> None:
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    build_shareholders().to_csv(out_dir / "shareholders.csv", index=False)


if __name__ == "__main__":
    main()
