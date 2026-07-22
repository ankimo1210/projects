"""Published Google Health data types and locally stored series inventory."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from health.endpoints import CATALOG, KNOWN_DATA_TYPES, Metric
from health.store import Store

PUBLISHED_COLUMNS = [
    "data_type",
    "label",
    "scope",
    "implemented",
    "metrics",
    "methods",
]
STORED_COLUMNS = [
    "metric",
    "data_type",
    "series",
    "storage",
    "n",
    "first_date",
    "last_date",
    "last_synced",
    "status",
    "n_raw_pages",
    "raw_first_range",
    "raw_last_range",
]


def build_inventory(
    store: Store,
    catalog: Sequence[Metric] = CATALOG,
    known_data_types: dict[str, tuple[str, str]] = KNOWN_DATA_TYPES,
) -> pd.DataFrame:
    """Return every published data type, whether or not the app implements it."""

    del store  # kept in the interface so both inventory builders share a caller
    by_type: dict[str, list[Metric]] = {}
    for metric in catalog:
        by_type.setdefault(metric.data_type, []).append(metric)

    rows = []
    for data_type, (label, scope) in known_data_types.items():
        implementations = by_type.get(data_type, [])
        rows.append(
            {
                "data_type": data_type,
                "label": label,
                "scope": scope,
                "implemented": bool(implementations),
                "metrics": ", ".join(item.name for item in implementations),
                "methods": ", ".join(dict.fromkeys(item.method for item in implementations)),
            }
        )
    return pd.DataFrame(rows, columns=PUBLISHED_COLUMNS).sort_values("data_type", ignore_index=True)


def build_series_inventory(store: Store, catalog: Sequence[Metric] = CATALOG) -> pd.DataFrame:
    """Return one row per typed local series, plus the sleep-session table."""

    daily = _indexed(store.series_stats(), "metric")
    intraday = _indexed(store.intraday_stats(), "metric")
    raw = _indexed(store.raw_stats(), "metric")
    states = _indexed(store.sync_states(), "metric")
    sleep = store.sleep_stats()

    rows = []
    for metric in catalog:
        stats = daily if metric.full_history else intraday
        storage = "daily" if metric.full_history else "intraday"
        for series in metric.series_names:
            rows.append(_series_row(metric, series, storage, stats, raw, states))
        if metric.name == "sleep":
            sleep_row = _series_row(metric, "sleep_sessions", "sleep", {}, raw, states)
            if not sleep.empty:
                sleep_row.update(
                    n=int(sleep.iloc[0]["n"]),
                    first_date=sleep.iloc[0]["first_date"],
                    last_date=sleep.iloc[0]["last_date"],
                )
            rows.append(sleep_row)

    return pd.DataFrame(rows, columns=STORED_COLUMNS).sort_values(
        ["metric", "storage", "series"], ignore_index=True
    )


def _indexed(frame: pd.DataFrame, column: str):
    return {} if frame.empty else frame.set_index(column)


def _value(indexed, key: str, column: str, default=None):
    if isinstance(indexed, dict) or key not in indexed.index:
        return default
    return indexed.loc[key, column]


def _series_row(metric, series, storage, stats, raw, states):
    return {
        "metric": metric.name,
        "data_type": metric.data_type,
        "series": series,
        "storage": storage,
        "n": int(_value(stats, series, "n", 0)),
        "first_date": _value(stats, series, "first_date"),
        "last_date": _value(stats, series, "last_date"),
        "last_synced": _value(states, metric.name, "last_synced_date"),
        "status": _value(states, metric.name, "status"),
        "n_raw_pages": int(_value(raw, metric.name, "n_pages", 0)),
        "raw_first_range": _value(raw, metric.name, "first_range_start"),
        "raw_last_range": _value(raw, metric.name, "last_range_end"),
    }
