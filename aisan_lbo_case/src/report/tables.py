from __future__ import annotations

from typing import Any

import pandas as pd

from src.utils.formatting import fmt_jpy_mn, fmt_multiple, fmt_pct


def format_case_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in df.to_dict("records"):
        rows.append(
            {
                "scenario": row["scenario"],
                "premium": fmt_pct(row["premium"], 0),
                "offer_price": f"JPY {row['offer_price']:,.0f}",
                "entry_ev": fmt_jpy_mn(row["headline_enterprise_value"]),
                "entry_ev_ebitda": fmt_multiple(row["entry_ev_ebitda"]),
                "new_debt": fmt_jpy_mn(row["new_debt"]),
                "debt_to_ebitda": fmt_multiple(row["entry_debt_to_ebitda"]),
                "exit_ebitda": fmt_jpy_mn(row["exit_ebitda"]),
                "exit_multiple": fmt_multiple(row["exit_multiple"]),
                "moic": fmt_multiple(row["moic"]),
                "irr": fmt_pct(row["irr"]),
            }
        )
    return rows


def records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)
    return df.astype(object).where(pd.notna(df), "n/a").to_dict("records")
