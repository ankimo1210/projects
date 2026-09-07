"""Pure, finite JSON analytics shared by the static dashboard's seven pages."""

from __future__ import annotations

import math
import warnings

import pandas as pd

from health.analytics import (
    calendar_rolling_mean,
    coverage_calendar,
    lagged_correlation,
    rolling_baseline_z,
    social_jetlag_hours,
)

PERIODS = (30, 90, 180, 365, None)
BASELINE_METRICS = ("resting_hr", "hrv_rmssd", "temp_skin_relative")
PAIRS = (
    ("sleep_minutes", "resting_hr"),
    ("sleep_minutes", "hrv_rmssd"),
    ("steps", "sleep_minutes"),
)


def _number(value) -> float | None:
    return float(value) if pd.notna(value) and math.isfinite(float(value)) else None


def _date(value) -> str | None:
    return None if pd.isna(value) else pd.Timestamp(value).date().isoformat()


def clip_calendar(frame, days, *, end, date_col="date") -> pd.DataFrame:
    """Copy a sorted inclusive calendar interval, using an explicit common end."""
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days < 1):
        raise ValueError("days must be a positive integer or None")
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    dates = pd.to_datetime(result[date_col])
    last = pd.Timestamp(end).normalize()
    selected = dates < last + pd.Timedelta(days=1)
    if days is not None:
        selected &= dates >= last - pd.Timedelta(days=days - 1)
    result[date_col] = dates
    return result.loc[selected].sort_values(date_col, kind="stable").reset_index(drop=True)


def _moving(frame: pd.DataFrame, metric: str) -> list[dict]:
    if frame.empty or metric not in frame:
        return []
    means = calendar_rolling_mean(frame, metric)
    return [
        {"date": _date(day), "value": _number(mean)}
        for day, mean in zip(frame["date"], means, strict=True)
    ]


def build_analytics(daily: pd.DataFrame, sleep: pd.DataFrame) -> dict:
    """Calculate on saved history; only correlations/coverage are period-specific.

    Input frames are never mutated. Missing and non-finite observations cannot
    contribute to statistics. Baselines and averages remain on the full history
    so narrowing a browser window cannot erase its preceding observations.
    """
    work = daily.copy().replace([float("inf"), -float("inf")], float("nan"))
    if "date" not in work:
        work["date"] = pd.Series(dtype="datetime64[ns]")
    work["date"] = pd.to_datetime(work["date"])
    work = work.sort_values("date", kind="stable").reset_index(drop=True)
    metrics = sorted(column for column in work if column != "date")
    baselines = {}
    for metric in BASELINE_METRICS:
        baselines[metric] = []
        if metric in work:
            scored = rolling_baseline_z(work, metric)
            baselines[metric] = [
                {
                    "date": _date(row["date"]),
                    "value": _number(row[metric]),
                    **{key: _number(row[key]) for key in ("baseline", "sd", "z")},
                }
                for row in scored.to_dict("records")
            ]

    sleep_work = sleep.copy().replace([float("inf"), -float("inf")], float("nan"))
    if not sleep_work.empty:
        sleep_work["date"] = pd.to_datetime(sleep_work["date"])
        sleep_work = sleep_work.sort_values("date", kind="stable")
    main = sleep_work
    if "is_main" in main:
        main = main.loc[main["is_main"].eq(True)].copy()
    moving = {
        "steps": _moving(work, "steps"),
        "sleep_main_minutes": _moving(main, "minutes_asleep"),
    }

    first = work["date"].min()
    end = work["date"].max()
    periods = {}
    for days in PERIODS:
        key = "all" if days is None else str(days)
        start = first if days is None or pd.isna(end) else end - pd.Timedelta(days=days - 1)
        clipped = clip_calendar(work, days, end=end)
        correlations = []
        for x, y in PAIRS:
            pair = clipped.reindex(columns=["date", x, y])
            # scipy warns for a constant series; the explicit null reason below
            # is the public result for that case, not a console warning.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                table = lagged_correlation(pair, x, y)
            for row in table.to_dict("records"):
                value = _number(row["spearman"])
                correlations.append(
                    {
                        "x": x,
                        "y": y,
                        "lag": int(row["lag"]),
                        "n": int(row["n"]),
                        "spearman": value,
                        "reason": "insufficient_pairs"
                        if row["n"] < 20
                        else ("constant_series" if value is None else None),
                    }
                )
        coverage = {}
        for metric in metrics:
            coverage[metric] = (
                []
                if pd.isna(end)
                else [
                    {"date": _date(row["date"]), "has_data": bool(row["has_data"])}
                    for row in coverage_calendar(clipped, metric, start, end).to_dict("records")
                ]
            )
        periods[key] = {
            "startDate": _date(start),
            "endDate": _date(end),
            "correlations": correlations,
            "coverage": coverage,
        }

    jetlag = social_jetlag_hours(sleep_work)
    return {
        "baselines": baselines,
        "movingAverages": moving,
        "periods": periods,
        "socialJetlag": {
            "hours": _number(jetlag),
            "scope": "all_saved_sleep",
            "firstDate": None if sleep_work.empty else _date(sleep_work["date"].min()),
            "lastDate": None if sleep_work.empty else _date(sleep_work["date"].max()),
        },
    }
