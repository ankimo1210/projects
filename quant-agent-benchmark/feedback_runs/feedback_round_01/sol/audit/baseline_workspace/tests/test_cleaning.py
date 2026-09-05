from __future__ import annotations

import numpy as np
import pandas as pd

from quantcurve.cleaning import clean_market_data
from quantcurve.io import REQUIRED_COLUMNS
from quantcurve.modeling import huber_multipliers, robust_outlier_scores

from helpers import raw_row


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows).loc[:, REQUIRED_COLUMNS]


def test_missing_quote_uses_observable_midpoint() -> None:
    rows = [
        raw_row("A", "A", "deposit", 1.0, None, bid=1.9, ask=2.1),
        raw_row("B", "B", "deposit", 0.5, 2.0, bid=1.9, ask=2.1),
    ]
    result = clean_market_data(_frame(rows), "2026-01-15")
    assert np.isclose(result.usable.loc[result.usable.obs_id == "A", "normalized_quote"].iloc[0], 0.02)
    assert "midpoint" in result.audit.loc[result.audit.obs_id == "A", "reason"].iloc[0]


def test_duplicate_retains_newest_and_audits_loser() -> None:
    rows = [
        raw_row("OLD", "SAME", "deposit", 1.0, 2.0, bid=1.9, ask=2.1, timestamp="2026-01-15T14:00:00Z"),
        raw_row("NEW", "SAME", "deposit", 1.0, 2.0, bid=1.9, ask=2.1, timestamp="2026-01-15T15:00:00Z"),
    ]
    result = clean_market_data(_frame(rows), "2026-01-15")
    assert result.usable["obs_id"].tolist() == ["NEW"]
    assert result.audit.loc[result.audit.obs_id == "OLD", "action"].iloc[0] == "exclude"


def test_rate_and_bond_unit_conversion_and_bid_ask_inversion() -> None:
    rows = [
        raw_row("R1", "R1", "deposit", 0.5, 2.0, bid=1.9, ask=2.1),
        raw_row("R2", "R2", "deposit", 1.0, 0.02, bid=0.021, ask=0.019),
        raw_row("P1", "P1", "bond", 5.0, 1.02, bid=1.01, ask=1.03, coupon=0.02),
    ]
    result = clean_market_data(_frame(rows), "2026-01-15")
    values = result.usable.set_index("obs_id")["normalized_quote"]
    assert np.isclose(values["R1"], 0.02)
    assert np.isclose(values["R2"], 0.02)
    assert np.isclose(values["P1"], 102.0)
    assert "inversion" in result.audit.loc[result.audit.obs_id == "R2", "reason"].iloc[0]


def test_stale_and_low_liquidity_are_not_silently_dropped() -> None:
    rows = [raw_row("S", "S", "deposit", 1.0, 2.0, bid=1.9, ask=2.1, timestamp="2026-01-01T15:00:00Z", liquidity=0.1)]
    result = clean_market_data(_frame(rows), "2026-01-15")
    assert len(result.usable) == 1
    assert result.audit.iloc[0].action == "downweight"
    assert result.audit.iloc[0].weight < 0.2


def test_huber_outlier_and_coherent_tenor_treatment() -> None:
    assert np.allclose(huber_multipliers(np.array([0.0, 3.0, 6.0]), 3.0), [1.0, 1.0, 0.5])
    rows = pd.DataFrame(
        {
            "instrument_type": ["ois_swap"] * 3 + ["bond"],
            "maturity_years": [5.0, 5.0, 5.0, 8.0],
            "base_weight": [1.0, 1.0, 1.0, 1.0],
        }
    )
    scores = robust_outlier_scores(rows, np.array([20.0, 21.0, 40.0, 7.0]))
    assert np.allclose(scores[:3], [-1.0, 0.0, 19.0])
    assert scores[3] == 7.0
