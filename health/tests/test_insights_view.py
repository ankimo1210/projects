from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from common import clip_days  # noqa: E402
from health.analytics import rolling_baseline_z  # noqa: E402
from views import insights_view  # noqa: E402


def test_clipped_baseline_uses_history_outside_the_display_window():
    """`_clipped_baseline` must compute the z-score on the full history and
    clip afterward. Computing on an already-clipped 30-day frame (the bug)
    starves `rolling_baseline_z`'s own 30-day window of prior observations
    for the oldest third of that same window, even though 40 days of real
    history exist just outside it."""
    df = pd.DataFrame(
        {
            "date": [date(2026, 1, 1) + timedelta(days=i) for i in range(40)],
            "resting_hr": [60.0 + i for i in range(40)],
        }
    )

    fixed = insights_view._clipped_baseline(df, "resting_hr", 30)

    # What the old, buggy order would have produced: clip first, then score.
    buggy_input = clip_days(df, 30)
    buggy = rolling_baseline_z(buggy_input[["date", "resting_hr"]], "resting_hr").dropna(
        subset=["z"]
    )

    assert len(fixed) == 30  # every day of the display window gets a z-score
    assert len(buggy) == 20  # the bug leaves the oldest 10 of those 30 days NaN
    assert fixed["date"].min() == date(2026, 1, 11)
    assert buggy["date"].min() == date(2026, 1, 21)


def test_clipped_baseline_returns_empty_when_history_is_too_thin():
    df = pd.DataFrame(
        {
            "date": [date(2026, 1, 1) + timedelta(days=i) for i in range(3)],
            "resting_hr": [60.0, 61.0, 59.0],
        }
    )

    scored = insights_view._clipped_baseline(df, "resting_hr", 30)

    assert scored.empty
