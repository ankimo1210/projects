from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from common import calendar_rolling_mean  # noqa: E402


def test_calendar_rolling_mean_uses_days_not_observation_count():
    frame = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-07", "2026-07-08"],
            "steps": [10.0, 70.0, 80.0],
        }
    )

    result = calendar_rolling_mean(frame, "steps")

    assert result.tolist() == [10.0, 40.0, 75.0]


def test_calendar_rolling_mean_preserves_original_row_order():
    frame = pd.DataFrame(
        {
            "date": ["2026-07-08", "2026-07-01", "2026-07-07"],
            "sleep": [80.0, 10.0, 70.0],
        },
        index=[8, 1, 7],
    )

    result = calendar_rolling_mean(frame, "sleep")

    assert result.index.tolist() == [8, 1, 7]
    assert result.tolist() == [75.0, 10.0, 40.0]


def test_calendar_rolling_mean_rejects_non_positive_window():
    with pytest.raises(ValueError, match="positive"):
        calendar_rolling_mean(pd.DataFrame(), "steps", days=0)
