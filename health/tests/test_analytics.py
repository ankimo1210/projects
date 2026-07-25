from datetime import date, timedelta

import pandas as pd
import pytest
from health.analytics import calendar_rolling_mean, lagged_correlation, rolling_baseline_z


def _daily(values, start=date(2026, 1, 1)):
    return pd.DataFrame(
        {"date": [start + timedelta(days=i) for i in range(len(values))], "value": values}
    )


def test_baseline_uses_only_prior_days():
    df = _daily([10.0] * 20 + [40.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    last = out.iloc[-1]
    assert last["baseline"] == pytest.approx(10.0)  # the spike is not in its own baseline
    assert last["value"] == 40.0


def test_days_without_enough_history_get_no_z():
    df = _daily([10.0, 11.0, 12.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert out["z"].isna().all()


def test_zero_variance_history_yields_no_z_instead_of_infinity():
    df = _daily([10.0] * 15 + [12.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert pd.isna(out.iloc[-1]["z"])


def test_z_is_positive_for_a_value_above_its_baseline():
    df = _daily([10.0, 11.0, 9.0, 10.5, 9.5] * 3 + [20.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert out.iloc[-1]["z"] > 3


def test_lagged_correlation_matches_by_calendar_date_not_row_position():
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(40)]
    sleep = [float(i % 7) for i in range(40)]
    df = pd.DataFrame({"date": days, "sleep": sleep, "hr": [0.0] * 40})
    # hr on day d+1 mirrors sleep on day d, with day 5 missing entirely.
    df["hr"] = [0.0, *sleep[:-1]]
    df = df.drop(index=5).reset_index(drop=True)

    out = lagged_correlation(df, "sleep", "hr", lags=(0, 1), min_pairs=5)

    lag1 = out[out["lag"] == 1].iloc[0]
    lag0 = out[out["lag"] == 0].iloc[0]
    assert lag1["spearman"] > 0.95
    assert lag1["spearman"] > lag0["spearman"]
    assert lag1["n"] < len(df)  # the missing day drops its pairs instead of shifting them


def test_lagged_correlation_reports_nan_below_min_pairs():
    df = _daily([1.0, 2.0, 3.0]).rename(columns={"value": "x"})
    df["y"] = [3.0, 2.0, 1.0]

    out = lagged_correlation(df, "x", "y", lags=(0,), min_pairs=20)

    assert pd.isna(out.iloc[0]["spearman"])
    assert out.iloc[0]["n"] == 3


def test_calendar_rolling_mean_ignores_missing_days():
    df = pd.DataFrame(
        {
            "date": [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 20)],
            "value": [10.0, 20.0, 5.0],
        }
    )

    out = calendar_rolling_mean(df, "value", days=7)

    assert out.tolist() == [10.0, 15.0, 5.0]


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
