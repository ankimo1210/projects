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


# -- numeric / date / time coercion helpers ------------------------------------
# Many contract fields are JSON strings (countSum, beatsPerMinute, minutesAsleep,
# ...) and some are JSON numbers (kcalSum, weightGramsAvg, ...); these helpers
# accept either.


def _to_float(value: object) -> float:
    """Coerce a JSON number or numeric string to float."""
    return float(value)  # type: ignore[arg-type]


def _to_int(value: object) -> int:
    """Coerce a JSON number or numeric string to int, via float so both
    integer-valued strings ("80") and numbers (80 or 80.0) work."""
    return int(float(value))  # type: ignore[arg-type]


def _google_date(d: dict) -> date:
    """Google `Date` {year, month, day} -> stdlib date."""
    return date(d["year"], d["month"], d["day"])


def _civil_to_datetime(civil: dict) -> datetime:
    """CivilDateTime {date, time} -> naive local datetime. `time` subfields
    default to 0 when absent (e.g. local midnight is often `{"time": {}}`)."""
    d = civil["date"]
    t = civil.get("time") or {}
    return datetime(
        d["year"],
        d["month"],
        d["day"],
        t.get("hours", 0),
        t.get("minutes", 0),
        t.get("seconds", 0),
        t.get("nanos", 0) // 1000,
    )


def _duration_seconds(text: str) -> float:
    """Protobuf `Duration` JSON string, e.g. "32400s" -> 32400.0 seconds."""
    return float(text[:-1]) if text.endswith("s") else float(text)


def _physical_to_local_datetime(physical_time: str, utc_offset: str) -> datetime:
    """RFC3339 UTC instant + a UTC-offset duration -> naive local datetime."""
    utc_dt = datetime.fromisoformat(physical_time.replace("Z", "+00:00"))
    local_dt = utc_dt + timedelta(seconds=_duration_seconds(utc_offset))
    return local_dt.replace(tzinfo=None)


def _local_datetime(
    civil: dict | None,
    physical_time: str | None,
    utc_offset: str | None,
    metric_name: str,
    field: str,
) -> datetime:
    """Prefer CivilDateTime; fall back to physicalTime + utcOffset when civil
    is absent. Neither present means the row can't be placed -- PayloadError."""
    if civil and "date" in civil:
        return _civil_to_datetime(civil)
    if physical_time and utc_offset:
        return _physical_to_local_datetime(physical_time, utc_offset)
    raise PayloadError(metric_name, f"missing {field} (no civil time, no physical time/offset)")


def _metric(name: str) -> Metric:
    """Look up this module's own CATALOG entry by name. Parsers use this to
    get the Metric object response_points() needs (.method / .name); resolved
    lazily at call time -- CATALOG is only fully built after this module's
    top-level code finishes running, which is always true by the time any
    parser is actually invoked."""
    return next(m for m in CATALOG if m.name == name)


# -- rollup parsers -------------------------------------------------------------
# Shared engine: a rollupDataPoint's `civilStartTime.date` places the row and
# is required (PayloadError if missing/malformed); the metric's own value
# field is an optional measurement -- absent means that day has no reading
# for it, so `build` returns None for that series and the row is skipped.


def _rollup_daily_rows(
    pages: Sequence[dict],
    metric_name: str,
    build: Callable[[dict], list[tuple[str, float | None]]],
) -> tuple[DailyRow, ...]:
    metric = _metric(metric_name)
    seen: set[tuple[str, date]] = set()
    out: list[DailyRow] = []
    for page in pages:
        for point in response_points(metric, page):
            civil_start = point.get("civilStartTime")
            if not civil_start or "date" not in civil_start:
                raise PayloadError(metric_name, "rollupDataPoint missing civilStartTime.date")
            d = _google_date(civil_start["date"])
            for series_name, value in build(point):
                if value is None:
                    continue
                key = (series_name, d)
                if key in seen:
                    raise PayloadError(metric_name, f"duplicate ({series_name}, {d})")
                seen.add(key)
                out.append((series_name, d, value))
    return tuple(out)


def parse_steps_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        obj = point.get("steps") or {}
        value = _to_float(obj["countSum"]) if "countSum" in obj else None
        return [("steps", value)]

    return ParsedRows(daily=_rollup_daily_rows(pages, "steps", build))


def parse_distance_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        obj = point.get("distance") or {}
        value = _to_float(obj["millimetersSum"]) / 1_000_000 if "millimetersSum" in obj else None
        return [("distance_km", value)]

    return ParsedRows(daily=_rollup_daily_rows(pages, "distance", build))


def parse_calories_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        obj = point.get("totalCalories") or {}
        value = _to_float(obj["kcalSum"]) if "kcalSum" in obj else None
        return [("calories", value)]

    return ParsedRows(daily=_rollup_daily_rows(pages, "calories", build))


_ACTIVITY_LEVEL_SERIES = {
    "LIGHT": "minutes_lightly_active",
    "MODERATE": "minutes_fairly_active",
    "VIGOROUS": "minutes_very_active",
}


def parse_active_minutes_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        levels = (point.get("activeMinutes") or {}).get("activeMinutesRollupByActivityLevel") or []
        out: list[tuple[str, float | None]] = []
        for entry in levels:
            series = _ACTIVITY_LEVEL_SERIES.get(entry.get("activityLevel"))
            if series is None or "activeMinutesSum" not in entry:
                continue
            out.append((series, _to_float(entry["activeMinutesSum"])))
        return out

    return ParsedRows(daily=_rollup_daily_rows(pages, "active_minutes", build))


def parse_weight_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        obj = point.get("weight") or {}
        value = _to_float(obj["weightGramsAvg"]) / 1000 if "weightGramsAvg" in obj else None
        return [("weight_kg", value)]

    return ParsedRows(daily=_rollup_daily_rows(pages, "weight", build))


def parse_body_fat_rollup(pages: Sequence[dict]) -> ParsedRows:
    def build(point: dict) -> list[tuple[str, float | None]]:
        obj = point.get("bodyFat") or {}
        value = _to_float(obj["bodyFatPercentageAvg"]) if "bodyFatPercentageAvg" in obj else None
        return [("fat_pct", value)]

    return ParsedRows(daily=_rollup_daily_rows(pages, "body_fat", build))


# -- daily reconcile parsers ------------------------------------------------------
# Shared engine: a dataPoint missing this metric's own union field (outer_key)
# doesn't concern this parser and is skipped silently (not an error). Once
# that field is present, its own `date` is required to place the row
# (PayloadError if absent); the value fields `build` inspects are optional
# measurements that skip only their own series row.


def _reconcile_daily_rows(
    pages: Sequence[dict],
    metric_name: str,
    outer_key: str,
    build: Callable[[dict], list[tuple[str, float | None]]],
) -> tuple[DailyRow, ...]:
    metric = _metric(metric_name)
    seen: set[tuple[str, date]] = set()
    out: list[DailyRow] = []
    for page in pages:
        for point in response_points(metric, page):
            obj = point.get(outer_key)
            if obj is None:
                continue
            if "date" not in obj:
                raise PayloadError(metric_name, f"{outer_key} missing date")
            d = _google_date(obj["date"])
            for series_name, value in build(obj):
                if value is None:
                    continue
                key = (series_name, d)
                if key in seen:
                    raise PayloadError(metric_name, f"duplicate ({series_name}, {d})")
                seen.add(key)
                out.append((series_name, d, value))
    return tuple(out)


def parse_resting_hr_reconcile(pages: Sequence[dict]) -> ParsedRows:
    def build(obj: dict) -> list[tuple[str, float | None]]:
        value = _to_float(obj["beatsPerMinute"]) if "beatsPerMinute" in obj else None
        return [("resting_hr", value)]

    return ParsedRows(
        daily=_reconcile_daily_rows(pages, "resting_hr", "dailyRestingHeartRate", build)
    )


def parse_hrv_reconcile(pages: Sequence[dict]) -> ParsedRows:
    def build(obj: dict) -> list[tuple[str, float | None]]:
        avg = (
            _to_float(obj["averageHeartRateVariabilityMilliseconds"])
            if "averageHeartRateVariabilityMilliseconds" in obj
            else None
        )
        deep_key = "deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds"
        deep = _to_float(obj[deep_key]) if deep_key in obj else None
        return [("hrv_rmssd", avg), ("hrv_deep_rmssd", deep)]

    return ParsedRows(daily=_reconcile_daily_rows(pages, "hrv", "dailyHeartRateVariability", build))


def parse_spo2_reconcile(pages: Sequence[dict]) -> ParsedRows:
    def build(obj: dict) -> list[tuple[str, float | None]]:
        return [
            (
                "spo2_avg",
                _to_float(obj["averagePercentage"]) if "averagePercentage" in obj else None,
            ),
            (
                "spo2_lower_bound",
                _to_float(obj["lowerBoundPercentage"]) if "lowerBoundPercentage" in obj else None,
            ),
            (
                "spo2_upper_bound",
                _to_float(obj["upperBoundPercentage"]) if "upperBoundPercentage" in obj else None,
            ),
        ]

    return ParsedRows(daily=_reconcile_daily_rows(pages, "spo2", "dailyOxygenSaturation", build))


def parse_temp_skin_reconcile(pages: Sequence[dict]) -> ParsedRows:
    def build(obj: dict) -> list[tuple[str, float | None]]:
        # baseline missing -> skip the row entirely; relativeNightlyStddev30dCelsius
        # is a different statistic and is never used as a substitute.
        if "baselineTemperatureCelsius" not in obj or "nightlyTemperatureCelsius" not in obj:
            return [("temp_skin_relative", None)]
        value = _to_float(obj["nightlyTemperatureCelsius"]) - _to_float(
            obj["baselineTemperatureCelsius"]
        )
        return [("temp_skin_relative", value)]

    return ParsedRows(
        daily=_reconcile_daily_rows(pages, "temp_skin", "dailySleepTemperatureDerivations", build)
    )


def parse_br_reconcile(pages: Sequence[dict]) -> ParsedRows:
    def build(obj: dict) -> list[tuple[str, float | None]]:
        value = _to_float(obj["breathsPerMinute"]) if "breathsPerMinute" in obj else None
        return [("breathing_rate", value)]

    return ParsedRows(daily=_reconcile_daily_rows(pages, "br", "dailyRespiratoryRate", build))


# -- sleep parser -----------------------------------------------------------------

_SLEEP_ROW_KEYS = (
    "provider_id",
    "date",
    "start_ts",
    "end_ts",
    "minutes_asleep",
    "minutes_deep",
    "minutes_light",
    "minutes_rem",
    "minutes_wake",
    "efficiency",
    "is_main",
)


def parse_sleep_reconcile(pages: Sequence[dict]) -> ParsedRows:
    metric = _metric("sleep")
    entries: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for page in pages:
        for point in response_points(metric, page):
            provider_id = point.get("dataPointName")
            if not provider_id:
                raise PayloadError(metric.name, "sleep dataPoint missing dataPointName")
            if provider_id in seen_ids:
                raise PayloadError(metric.name, f"duplicate sleep provider_id: {provider_id}")
            seen_ids.add(provider_id)

            sleep = point.get("sleep")
            if sleep is None:
                raise PayloadError(metric.name, f"{provider_id}: missing sleep")
            interval = sleep.get("interval") or {}
            start_ts = _local_datetime(
                interval.get("civilStartTime"),
                interval.get("startTime"),
                interval.get("startUtcOffset"),
                metric.name,
                f"{provider_id}: interval.civilStartTime/startTime",
            )
            end_ts = _local_datetime(
                interval.get("civilEndTime"),
                interval.get("endTime"),
                interval.get("endUtcOffset"),
                metric.name,
                f"{provider_id}: interval.civilEndTime/endTime",
            )

            summary = sleep.get("summary") or {}
            if "minutesAsleep" not in summary:
                raise PayloadError(metric.name, f"{provider_id}: missing summary.minutesAsleep")
            minutes_asleep = _to_int(summary["minutesAsleep"])

            stages_summary = summary.get("stagesSummary") or []
            stage_minutes = {"DEEP": 0, "LIGHT": 0, "REM": 0, "AWAKE": 0}
            for stage in stages_summary:
                stage_type = stage.get("type")
                if stage_type in stage_minutes:
                    stage_minutes[stage_type] += _to_int(stage.get("minutes", 0))
            if stages_summary:
                # STAGES sleep: wake minutes come from the AWAKE stage bucket.
                minutes_wake = stage_minutes["AWAKE"]
            else:
                # Classic sleep has no stagesSummary at all -- fall back to
                # summary.minutesAwake. Deep/light/rem stay 0 (not a blocker).
                minutes_wake = _to_int(summary["minutesAwake"]) if "minutesAwake" in summary else 0

            minutes_in_period = summary.get("minutesInSleepPeriod")
            denom = _to_int(minutes_in_period) if minutes_in_period not in (None, "") else 0
            efficiency = round(minutes_asleep / denom * 100) if denom else 0

            nap = bool((sleep.get("metadata") or {}).get("nap", False))
            entries.append(
                {
                    "provider_id": provider_id,
                    "date": end_ts.date(),
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "minutes_asleep": minutes_asleep,
                    "minutes_deep": stage_minutes["DEEP"],
                    "minutes_light": stage_minutes["LIGHT"],
                    "minutes_rem": stage_minutes["REM"],
                    "minutes_wake": minutes_wake,
                    "efficiency": efficiency,
                    "_nap": nap,
                }
            )

    # Main-session selection is resolved across the whole call: group by wake
    # date, prefer the longest non-nap session; if every session that date is
    # a nap, the longest session overall is main.
    by_date: dict[date, list[dict[str, object]]] = {}
    for entry in entries:
        by_date.setdefault(entry["date"], []).append(entry)  # type: ignore[arg-type]
    for group in by_date.values():
        non_nap = [e for e in group if not e["_nap"]]
        candidates = non_nap or group
        main = max(candidates, key=lambda e: e["minutes_asleep"])
        for e in group:
            e["is_main"] = e is main

    # Daily series alongside the sessions (catalog: sleep -> sleep_minutes +
    # sleep_sessions): total asleep minutes per wake date, naps included.
    daily = tuple(
        ("sleep_minutes", d, float(sum(e["minutes_asleep"] for e in group)))  # type: ignore[misc]
        for d, group in sorted(by_date.items())
    )
    rows = tuple({k: e[k] for k in _SLEEP_ROW_KEYS} for e in entries)
    return ParsedRows(daily=daily, sleep=rows)


# -- intraday parsers ---------------------------------------------------------------
# A dataPoint missing this metric's own field (heartRate / steps) doesn't
# concern this parser and is skipped silently. Once present, its sample/
# interval start time is required to place the row (PayloadError if it can't
# be resolved via civil time or the physical-time/offset fallback); the
# actual bpm/count value is an optional measurement that skips only its row.


def parse_intraday_hr_reconcile(pages: Sequence[dict]) -> ParsedRows:
    metric = _metric("intraday_hr")
    series_name = metric.series_names[0]
    seen: set[datetime] = set()
    out: list[IntradayRow] = []
    for page in pages:
        for point in response_points(metric, page):
            hr = point.get("heartRate")
            if hr is None:
                continue
            sample_time = hr.get("sampleTime") or {}
            ts = _local_datetime(
                sample_time.get("civilTime"),
                sample_time.get("physicalTime"),
                sample_time.get("utcOffset"),
                metric.name,
                "heartRate.sampleTime",
            )
            if "beatsPerMinute" not in hr:
                continue
            if ts in seen:
                raise PayloadError(metric.name, f"duplicate hr timestamp: {ts}")
            seen.add(ts)
            out.append((series_name, ts, _to_float(hr["beatsPerMinute"])))
    return ParsedRows(intraday=tuple(out))


def parse_intraday_steps_reconcile(pages: Sequence[dict]) -> ParsedRows:
    metric = _metric("intraday_steps")
    series_name = metric.series_names[0]
    seen: set[datetime] = set()
    out: list[IntradayRow] = []
    for page in pages:
        for point in response_points(metric, page):
            steps = point.get("steps")
            if steps is None:
                continue
            interval = steps.get("interval") or {}
            ts = _local_datetime(
                interval.get("civilStartTime"),
                interval.get("startTime"),
                interval.get("startUtcOffset"),
                metric.name,
                "steps.interval.civilStartTime",
            )
            if "count" not in steps:
                continue
            if ts in seen:
                raise PayloadError(metric.name, f"duplicate steps timestamp: {ts}")
            seen.add(ts)
            out.append((series_name, ts, _to_float(steps["count"])))
    return ParsedRows(intraday=tuple(out))


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
