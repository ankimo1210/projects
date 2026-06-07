from __future__ import annotations

import pandas as pd

from src.utils.sources import CONFIG_DIR, PROJECT_ROOT, load_yaml


def build_segments() -> pd.DataFrame:
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    segment_cfg = assumptions["segments"]
    df = pd.DataFrame(segment_cfg["rows"])
    df["public_ebit_margin"] = df["public_ebit"] / df["public_revenue"]
    df["mobility_dx_ebit_margin"] = df["mobility_dx_ebit"] / df["mobility_dx_revenue"]
    df["other_ebit_margin"] = df["other_ebit"] / df["other_revenue"]
    df["source_id"] = segment_cfg["source_id"]
    df["source_type"] = segment_cfg["source_type"]
    return df


def main() -> None:
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    build_segments().to_csv(out_dir / "segment_financials.csv", index=False)


if __name__ == "__main__":
    main()
