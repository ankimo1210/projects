"""Acceptance probe helpers that persist raw pages without touching DuckDB."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

from health.auth import AuthError
from health.client import ApiError, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric, PayloadError, response_points

PROBE_REQUEST_LIMIT_PER_METRIC = 1000


def probe_range(metric: Metric, today: date) -> tuple[date, date]:
    """Use a deliberately narrow range for an acceptance probe."""

    if metric.method == DAILY_ROLLUP:
        return today - timedelta(days=6), today
    if metric.full_history:
        return today - timedelta(days=29), today
    return today, today


def run_probe(
    client,
    output_dir: Path,
    catalog: Sequence[Metric] = CATALOG,
    today: date | None = None,
    report: Callable[[str], None] | None = None,
) -> dict:
    """Probe catalog entries independently and persist pages plus a manifest.

    API and payload errors are isolated to one metric. Auth errors stop the
    run because every subsequent request would fail for the same reason.
    """

    today = today or date.today()
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "metrics": {},
    }

    for metric in catalog:
        start, end = probe_range(metric, today)
        entry = _manifest_entry(metric, start, end)
        try:
            budget = RequestBudget(PROBE_REQUEST_LIMIT_PER_METRIC)
            if metric.method == DAILY_ROLLUP:
                pages = [client.daily_rollup(metric, start, end, budget)]
            else:
                pages = list(client.iter_reconciled(metric, start, end, budget))

            point_count = sum(len(response_points(metric, page)) for page in pages)
            metric_dir = output_dir / metric.name
            metric_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(metric_dir, 0o700)
            for index, page in enumerate(pages):
                _write_private_json(metric_dir / f"page-{index:03d}.json", page)

            entry.update(
                status="ok" if point_count else "empty",
                page_count=len(pages),
                data_point_count=point_count,
                top_level_keys=sorted({key for page in pages for key in page.keys()}),
            )
        except AuthError as exc:
            entry.update(status="error", error_message=str(exc))
            manifest["metrics"][metric.name] = entry
            _write_private_json(output_dir / "manifest.json", manifest)
            raise
        except (ApiError, PayloadError, RequestCapExceeded) as exc:
            entry.update(
                status="error",
                error_status=getattr(exc, "status_code", None),
                error_message=str(exc),
            )

        manifest["metrics"][metric.name] = entry
        if report:
            report(
                f"{metric.name}: {entry['status']} "
                f"({entry['page_count']} pages, {entry['data_point_count']} points)"
            )

    _write_private_json(output_dir / "manifest.json", manifest)
    return manifest


def _manifest_entry(metric: Metric, start: date, end: date) -> dict:
    return {
        "status": "pending",
        "data_type": metric.data_type,
        "method": metric.method,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "page_count": 0,
        "data_point_count": 0,
        "top_level_keys": [],
        "error_status": None,
        "error_message": None,
    }


def _write_private_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.chmod(path, 0o600)
