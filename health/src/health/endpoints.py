"""Fitbit metric catalog: endpoint definitions, range chunking, payload parsers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

API = "https://api.fitbit.com"


@dataclass(frozen=True)
class ParsedRows:
    daily: Any = ()      # [(metric, "YYYY-MM-DD", value)]
    sleep: Any = ()      # [dict] matching sleep_sessions columns
    intraday: Any = ()   # [(metric, "YYYY-MM-DD HH:MM:SS", value)]


@dataclass(frozen=True)
class Metric:
    name: str
    path: str            # contains {start}/{end} (kind="range") or {date} (kind="per_day")
    kind: str
    max_range_days: int
    scope: str
    full_history: bool   # False: backfill only trailing 30 days
    parse: Callable[[Any], ParsedRows] = field(repr=False)


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=max_days - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def _series_parser(key: str, metric: str) -> Callable[[Any], ParsedRows]:
    def parse(payload: Any) -> ParsedRows:
        rows = [(metric, e["dateTime"], float(e["value"])) for e in payload.get(key, [])]
        return ParsedRows(daily=rows)
    return parse


_ZONES = {"Out of Range": "out_of_range", "Fat Burn": "fat_burn",
          "Cardio": "cardio", "Peak": "peak"}


def _parse_heart(payload: Any) -> ParsedRows:
    rows = []
    for e in payload.get("activities-heart", []):
        d, v = e["dateTime"], e.get("value") or {}
        if "restingHeartRate" in v:
            rows.append(("resting_hr", d, float(v["restingHeartRate"])))
        for z in v.get("heartRateZones", []):
            slug = _ZONES.get(z.get("name"))
            if slug and "minutes" in z:
                rows.append((f"hr_zone_{slug}_min", d, float(z["minutes"])))
    return ParsedRows(daily=rows)


def _parse_sleep(payload: Any) -> ParsedRows:
    daily, sessions = [], []
    for s in payload.get("sleep", []):
        summary = (s.get("levels") or {}).get("summary") or {}

        def mins(k: str) -> int:
            return int((summary.get(k) or {}).get("minutes", 0))

        sessions.append({
            "log_id": s["logId"], "date": s["dateOfSleep"],
            "start_ts": s["startTime"].replace("T", " ")[:19],
            "end_ts": s["endTime"].replace("T", " ")[:19],
            "minutes_asleep": int(s.get("minutesAsleep", 0)),
            "minutes_deep": mins("deep"), "minutes_light": mins("light"),
            "minutes_rem": mins("rem"), "minutes_wake": mins("wake"),
            "efficiency": int(s.get("efficiency", 0)),
            "is_main": bool(s.get("isMainSleep", False)),
        })
        if s.get("isMainSleep", False):
            daily.append(("sleep_minutes", s["dateOfSleep"], float(s.get("minutesAsleep", 0))))
    return ParsedRows(daily=daily, sleep=sessions)


def _parse_weight(payload: Any) -> ParsedRows:
    rows = []
    for e in payload.get("weight", []):
        rows.append(("weight_kg", e["date"], float(e["weight"])))
        if "fat" in e:
            rows.append(("fat_pct", e["date"], float(e["fat"])))
    return ParsedRows(daily=rows)


def _value_fields_parser(key: str | None, fields: dict[str, str]) -> Callable[[Any], ParsedRows]:
    """Parser for hrv/spo2/temp/br shapes: entries with dateTime + value{...}.

    key=None means the payload itself is the entry list (spo2).
    fields maps response field -> our metric name.
    """
    def parse(payload: Any) -> ParsedRows:
        entries = payload if key is None else payload.get(key, [])
        rows = []
        for e in entries:
            v = e.get("value") or {}
            for src, metric in fields.items():
                if v.get(src) is not None:
                    rows.append((metric, e["dateTime"], float(v[src])))
        return ParsedRows(daily=rows)
    return parse


def _intraday_parser(summary_key: str, dataset_key: str, metric: str) -> Callable[[Any], ParsedRows]:
    def parse(payload: Any) -> ParsedRows:
        summary = payload.get(summary_key, [])
        if not summary:
            return ParsedRows()
        d = summary[0]["dateTime"]
        rows = [(metric, f"{d} {e['time']}", float(e["value"]))
                for e in payload.get(dataset_key, {}).get("dataset", [])]
        return ParsedRows(intraday=rows)
    return parse


CATALOG: list[Metric] = [
    Metric("steps", "/1/user/-/activities/steps/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-steps", "steps")),
    Metric("distance", "/1/user/-/activities/distance/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-distance", "distance_km")),
    Metric("calories", "/1/user/-/activities/calories/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-calories", "calories")),
    Metric("minutes_very_active", "/1/user/-/activities/minutesVeryActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesVeryActive", "minutes_very_active")),
    Metric("minutes_fairly_active", "/1/user/-/activities/minutesFairlyActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesFairlyActive", "minutes_fairly_active")),
    Metric("minutes_lightly_active", "/1/user/-/activities/minutesLightlyActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesLightlyActive", "minutes_lightly_active")),
    Metric("heart", "/1/user/-/activities/heart/date/{start}/{end}.json",
           "range", 365, "heartrate", True, _parse_heart),
    Metric("sleep", "/1.2/user/-/sleep/date/{start}/{end}.json",
           "range", 100, "sleep", True, _parse_sleep),
    Metric("weight", "/1/user/-/body/log/weight/date/{start}/{end}.json",
           "range", 31, "weight", True, _parse_weight),
    Metric("hrv", "/1/user/-/hrv/date/{start}/{end}.json",
           "range", 30, "heartrate", True,
           _value_fields_parser("hrv", {"dailyRmssd": "hrv_rmssd", "deepRmssd": "hrv_deep_rmssd"})),
    Metric("spo2", "/1/user/-/spo2/date/{start}/{end}.json",
           "range", 30, "oxygen_saturation", True,
           _value_fields_parser(None, {"avg": "spo2_avg", "min": "spo2_min", "max": "spo2_max"})),
    Metric("temp_skin", "/1/user/-/temp/skin/date/{start}/{end}.json",
           "range", 30, "temperature", True,
           _value_fields_parser("tempSkin", {"nightlyRelative": "temp_skin_relative"})),
    Metric("br", "/1/user/-/br/date/{start}/{end}.json",
           "range", 30, "respiratory_rate", True,
           _value_fields_parser("br", {"breathingRate": "breathing_rate"})),
    Metric("intraday_hr", "/1/user/-/activities/heart/date/{date}/1d/1min.json",
           "per_day", 1, "heartrate", False,
           _intraday_parser("activities-heart", "activities-heart-intraday", "hr")),
    Metric("intraday_steps", "/1/user/-/activities/steps/date/{date}/1d/1min.json",
           "per_day", 1, "activity", False,
           _intraday_parser("activities-steps", "activities-steps-intraday", "steps")),
]
