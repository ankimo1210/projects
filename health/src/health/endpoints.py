"""Google Health API v4 metric catalog: request/response contracts, chunking, parser stubs.

Contract source of truth: `.superpowers/sdd/health-google-api-contracts.md`
(extracted verbatim from the v4 discovery document). `CivilDateTime` never
carries a UTC offset; `dailyRollUp` ranges are closed-open; `reconcile`
filters use the full snake_case data-type path, never a bare field name.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DAILY_ROLLUP = "daily_rollup"
RECONCILE = "reconcile"

DailyRow = tuple[str, date, float]
IntradayRow = tuple[str, datetime, float]
SleepRow = dict[str, object]


class PayloadError(ValueError):
    """A response's repeated field exists but is not a list."""

    def __init__(self, metric: str, detail: str):
        self.metric = metric
        self.detail = detail
        super().__init__(f"{metric}: {detail}")


@dataclass(frozen=True)
class ParsedRows:
    daily: tuple[DailyRow, ...] = ()
    sleep: tuple[SleepRow, ...] = ()
    intraday: tuple[IntradayRow, ...] = ()


@dataclass(frozen=True)
class Metric:
    name: str
    data_type: str
    method: str  # DAILY_ROLLUP or RECONCILE
    max_range_days: int
    scope: str
    full_history: bool  # False: backfill only trailing 30 days (intraday)
    series_names: tuple[str, ...]
    parse_pages: Callable[[Sequence[dict]], ParsedRows]
    page_size: int = 1000
    filter_path: str | None = None  # reconcile only; None for dailyRollUp


# -- request / response contract helpers -------------------------------------


def civil_midnight(d: date) -> dict[str, object]:
    """A CivilDateTime at local midnight: {date, time}, never a UTC offset."""
    return {
        "date": {"year": d.year, "month": d.month, "day": d.day},
        "time": {},
    }


def daily_rollup_body(start: date, end: date) -> dict[str, object]:
    """DailyRollUpDataPointsRequest body. `end` is inclusive on our side but
    the API range is closed-open, so the wire end is `end + 1 day`."""
    return {
        "range": {
            "start": civil_midnight(start),
            "end": civil_midnight(end + timedelta(days=1)),
        },
        "windowSizeDays": 1,
    }


def closed_open_filter(path: str, start: date, end: date) -> str:
    """reconcile/list filter expression over a full snake_case data-type path,
    e.g. `daily_resting_heart_rate.date`. `end` is inclusive on our side; the
    wire filter is closed-open so the upper bound is `end + 1 day`."""
    stop = end + timedelta(days=1)
    return f'{path} >= "{start}" AND {path} < "{stop}"'


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    """Split [start, end] into contiguous, non-overlapping <= max_days chunks."""
    if max_days < 1:
        raise ValueError(f"max_days must be >= 1, got {max_days}")
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=max_days - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def response_points(metric: Metric, page: dict) -> list[dict]:
    """Read the repeated data-point field for one response page.

    dailyRollUp pages carry `rollupDataPoints`; reconcile pages carry
    `dataPoints`. A missing key is treated as an empty page (protobuf JSON
    omits empty repeated fields); a present-but-non-list value means the
    payload is malformed and raises PayloadError.
    """
    key = "rollupDataPoints" if metric.method == DAILY_ROLLUP else "dataPoints"
    if key not in page:
        return []
    value = page[key]
    if not isinstance(value, list):
        raise PayloadError(metric.name, f"{key!r} is not a list: {type(value).__name__}")
    return value


# -- parsers (stubs; completed in Task 5) -------------------------------------
# Each metric gets its own named callable so the catalog never references a
# shared placeholder. None of these are exercised by this task's contract
# tests -- they exist only to satisfy Metric.parse_pages' type.


def parse_steps_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_steps_rollup: implemented in Task 5")


def parse_distance_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_distance_rollup: implemented in Task 5")


def parse_calories_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_calories_rollup: implemented in Task 5")


def parse_active_minutes_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_active_minutes_rollup: implemented in Task 5")


def parse_weight_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_weight_rollup: implemented in Task 5")


def parse_body_fat_rollup(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_body_fat_rollup: implemented in Task 5")


def parse_resting_hr_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_resting_hr_reconcile: implemented in Task 5")


def parse_hrv_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_hrv_reconcile: implemented in Task 5")


def parse_spo2_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_spo2_reconcile: implemented in Task 5")


def parse_temp_skin_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_temp_skin_reconcile: implemented in Task 5")


def parse_br_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_br_reconcile: implemented in Task 5")


def parse_sleep_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_sleep_reconcile: implemented in Task 5")


def parse_intraday_hr_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_intraday_hr_reconcile: implemented in Task 5")


def parse_intraday_steps_reconcile(pages: Sequence[dict]) -> ParsedRows:
    raise NotImplementedError("parse_intraday_steps_reconcile: implemented in Task 5")


# -- 14-entry metric catalog ---------------------------------------------------

CATALOG: list[Metric] = [
    Metric(
        "steps",
        "steps",
        DAILY_ROLLUP,
        90,
        "activity_and_fitness",
        True,
        ("steps",),
        parse_steps_rollup,
    ),
    Metric(
        "distance",
        "distance",
        DAILY_ROLLUP,
        90,
        "activity_and_fitness",
        True,
        ("distance_km",),
        parse_distance_rollup,
    ),
    Metric(
        "calories",
        "total-calories",
        DAILY_ROLLUP,
        14,
        "activity_and_fitness",
        True,
        ("calories",),
        parse_calories_rollup,
    ),
    Metric(
        "active_minutes",
        "active-minutes",
        DAILY_ROLLUP,
        14,
        "activity_and_fitness",
        True,
        ("minutes_lightly_active", "minutes_fairly_active", "minutes_very_active"),
        parse_active_minutes_rollup,
    ),
    Metric(
        "weight",
        "weight",
        DAILY_ROLLUP,
        90,
        "health_metrics_and_measurements",
        True,
        ("weight_kg",),
        parse_weight_rollup,
    ),
    Metric(
        "body_fat",
        "body-fat",
        DAILY_ROLLUP,
        90,
        "health_metrics_and_measurements",
        True,
        ("fat_pct",),
        parse_body_fat_rollup,
    ),
    Metric(
        "resting_hr",
        "daily-resting-heart-rate",
        RECONCILE,
        90,
        "health_metrics_and_measurements",
        True,
        ("resting_hr",),
        parse_resting_hr_reconcile,
        filter_path="daily_resting_heart_rate.date",
    ),
    Metric(
        "hrv",
        "daily-heart-rate-variability",
        RECONCILE,
        90,
        "health_metrics_and_measurements",
        True,
        ("hrv_rmssd", "hrv_deep_rmssd"),
        parse_hrv_reconcile,
        filter_path="daily_heart_rate_variability.date",
    ),
    Metric(
        "spo2",
        "daily-oxygen-saturation",
        RECONCILE,
        90,
        "health_metrics_and_measurements",
        True,
        ("spo2_avg", "spo2_lower_bound", "spo2_upper_bound"),
        parse_spo2_reconcile,
        filter_path="daily_oxygen_saturation.date",
    ),
    Metric(
        "temp_skin",
        "daily-sleep-temperature-derivations",
        RECONCILE,
        90,
        "health_metrics_and_measurements",
        True,
        ("temp_skin_relative",),
        parse_temp_skin_reconcile,
        filter_path="daily_sleep_temperature_derivations.date",
    ),
    Metric(
        "br",
        "daily-respiratory-rate",
        RECONCILE,
        90,
        "health_metrics_and_measurements",
        True,
        ("breathing_rate",),
        parse_br_reconcile,
        filter_path="daily_respiratory_rate.date",
    ),
    Metric(
        "sleep",
        "sleep",
        RECONCILE,
        90,
        "sleep",
        True,
        ("sleep_minutes",),
        parse_sleep_reconcile,
        page_size=25,
        filter_path="sleep.interval.civil_end_time",
    ),
    Metric(
        "intraday_hr",
        "heart-rate",
        RECONCILE,
        1,
        "health_metrics_and_measurements",
        False,
        ("hr",),
        parse_intraday_hr_reconcile,
        filter_path="heart_rate.sample_time.civil_time",
    ),
    Metric(
        "intraday_steps",
        "steps",
        RECONCILE,
        1,
        "activity_and_fitness",
        False,
        ("steps",),
        parse_intraday_steps_reconcile,
        filter_path="steps.interval.civil_start_time",
    ),
]


# -- published Google Health data types (superset of CATALOG) -----------------
# id -> (label, scope). Ids and shapes come from the ReconciledDataPoint union
# in the contracts file (plus `total-calories`, rollup-only). Not every
# published data type is implemented; CATALOG's data types are a subset.
# `scope` is one of the 3 OAuth scopes actually requested by auth.py
# (activity_and_fitness / health_metrics_and_measurements / sleep) so the
# inventory page can point a 403 back at the scope to (re)grant.

KNOWN_DATA_TYPES: dict[str, tuple[str, str]] = {
    "steps": ("Steps", "activity_and_fitness"),
    "distance": ("Distance", "activity_and_fitness"),
    "total-calories": ("Total calories", "activity_and_fitness"),
    "active-minutes": ("Active minutes", "activity_and_fitness"),
    "active-energy-burned": ("Active energy burned", "activity_and_fitness"),
    "active-zone-minutes": ("Active zone minutes", "activity_and_fitness"),
    "activity-level": ("Activity level", "activity_and_fitness"),
    "altitude": ("Altitude", "activity_and_fitness"),
    "basal-energy-burned": ("Basal energy burned", "activity_and_fitness"),
    "exercise": ("Exercise session", "activity_and_fitness"),
    "floors": ("Floors climbed", "activity_and_fitness"),
    "sedentary-period": ("Sedentary period", "activity_and_fitness"),
    "swim-lengths-data": ("Swim lengths", "activity_and_fitness"),
    "time-in-heart-rate-zone": ("Time in heart rate zone", "activity_and_fitness"),
    "daily-vo2-max": ("Daily VO2 max", "activity_and_fitness"),
    "run-vo2-max": ("Run VO2 max", "activity_and_fitness"),
    "vo2-max": ("VO2 max", "activity_and_fitness"),
    "weight": ("Weight", "health_metrics_and_measurements"),
    "body-fat": ("Body fat percentage", "health_metrics_and_measurements"),
    "height": ("Height", "health_metrics_and_measurements"),
    "heart-rate": ("Heart rate", "health_metrics_and_measurements"),
    "heart-rate-variability": (
        "Heart rate variability (sample)",
        "health_metrics_and_measurements",
    ),
    "daily-resting-heart-rate": (
        "Daily resting heart rate",
        "health_metrics_and_measurements",
    ),
    "daily-heart-rate-variability": (
        "Daily heart rate variability",
        "health_metrics_and_measurements",
    ),
    "daily-heart-rate-zones": ("Daily heart rate zones", "health_metrics_and_measurements"),
    "daily-oxygen-saturation": (
        "Daily oxygen saturation",
        "health_metrics_and_measurements",
    ),
    "oxygen-saturation": ("Oxygen saturation (sample)", "health_metrics_and_measurements"),
    "daily-sleep-temperature-derivations": (
        "Daily sleep temperature derivation",
        "health_metrics_and_measurements",
    ),
    "core-body-temperature": ("Core body temperature", "health_metrics_and_measurements"),
    "daily-respiratory-rate": ("Daily respiratory rate", "health_metrics_and_measurements"),
    "respiratory-rate-sleep-summary": (
        "Respiratory rate sleep summary",
        "health_metrics_and_measurements",
    ),
    "blood-glucose": ("Blood glucose", "health_metrics_and_measurements"),
    "nutrition-log": ("Nutrition log", "health_metrics_and_measurements"),
    "hydration-log": ("Hydration log", "health_metrics_and_measurements"),
    "sleep": ("Sleep session", "sleep"),
}
