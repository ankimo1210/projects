from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.sources import CONFIG_DIR, PROJECT_ROOT, load_yaml


def build_historical_financials() -> pd.DataFrame:
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    rows = assumptions["historical_financials"]["rows"]
    d_and_a_pct = assumptions["projection_defaults"]["d_and_a_pct_revenue"]
    df = pd.DataFrame(rows)
    df["d_and_a_estimated"] = (df["revenue"] * d_and_a_pct).round(1)
    df["ebitda_estimated"] = (df["ebit"] + df["d_and_a_estimated"]).round(1)
    df["ebit_margin"] = df["ebit"] / df["revenue"]
    df["ebitda_margin_estimated"] = df["ebitda_estimated"] / df["revenue"]
    df["fcf_conversion_to_ebitda"] = df["free_cf"] / df["ebitda_estimated"]
    df["source_type"] = assumptions["historical_financials"]["source_type"]
    df["source_ids"] = ";".join(assumptions["historical_financials"]["source_ids"])
    return df


def build_management_forecast() -> pd.DataFrame:
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    row = assumptions["management_forecast"].copy()
    d_and_a_pct = assumptions["projection_defaults"]["d_and_a_pct_revenue"]
    row["d_and_a_estimated"] = round(row["revenue"] * d_and_a_pct, 1)
    row["ebitda_estimated"] = round(row["ebit"] + row["d_and_a_estimated"], 1)
    row["ebit_margin"] = row["ebit"] / row["revenue"]
    row["ebitda_margin_estimated"] = row["ebitda_estimated"] / row["revenue"]
    return pd.DataFrame([row])


def build_assumption_audit() -> pd.DataFrame:
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    rows: list[dict[str, object]] = []
    for section_name, section in assumptions.items():
        if isinstance(section, dict):
            source_id = section.get("source_id")
            source_type = section.get("source_type")
            if source_id or source_type:
                rows.append(
                    {
                        "section": section_name,
                        "source_type": source_type or "mixed",
                        "source_id": source_id or ";".join(section.get("source_ids", [])),
                        "note": section.get("note", ""),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    build_historical_financials().to_csv(out_dir / "historical_financials.csv", index=False)
    build_management_forecast().to_csv(out_dir / "management_forecast.csv", index=False)
    build_assumption_audit().to_csv(out_dir / "assumption_audit.csv", index=False)


if __name__ == "__main__":
    main()
