"""Acceptance probe helpers that persist raw pages without touching DuckDB."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from health.auth import AuthError
from health.client import ApiError, RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric, PayloadError, response_points
from health.privacy import ensure_private_dir
from health.source_catalog import SourceSpec, build_request, source_points, with_page_token

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
    _write_private_bytes(
        path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _write_private_bytes(path: Path, body: bytes) -> None:
    """Atomic private write; raw paths are unique for each probe run."""
    ensure_private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".probe-")
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_source_probe(
    client,
    output_dir: Path,
    sources: Sequence[SourceSpec],
    today: date | None = None,
    max_requests: int = 200,
    *,
    report: Callable[[str], None] | None = None,
) -> dict:
    """Audit narrow independent ranges without touching a database.

    Every wire response, including errors and each 401, is stored before JSON
    parsing. A per-run body directory preserves earlier runs. Time-series
    history remains unknown even when all tested ranges are empty. ECG probes
    are lower-bound-only queries, bounded by the physical request budget.
    Failures stop only their source except auth/429/cap/storage failures.
    """
    if type(max_requests) is not int or max_requests < 0:
        raise ValueError("max_requests must be a nonnegative integer")
    sources = tuple(sources)
    if len({s.key for s in sources}) != len(sources):
        raise ValueError("duplicate source keys")
    today = today or date.today()
    output_dir = Path(output_dir)
    ensure_private_dir(output_dir)
    run_id = uuid.uuid4().hex
    run_dir = output_dir / "runs" / run_id
    ensure_private_dir(output_dir / "runs")
    ensure_private_dir(run_dir)
    budget = RequestBudget(max_requests)
    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "run_id": run_id,
        "requests_made": 0,
        "max_requests": max_requests,
        "stopped_reason": None,
        "sources": {},
    }
    queue = deque()
    failed = set()
    details: dict[str, list[SourceSpec]] = {}
    seen_names: dict[str, set[str]] = {}

    def save_manifest():
        manifest["requests_made"] = budget.used
        _write_private_json(run_dir / "manifest.json", manifest)
        _write_private_json(output_dir / "manifest.json", manifest)

    def enqueue(source, label, start=None, end=None, resource_name=None):
        request = build_request(source, start=start, end=end, resource_name=resource_name)
        query = {
            "label": label,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "request": asdict(request),
            "status": "pending",
            "next_page_token": None,
            "page_count": 0,
            "data_point_count": 0,
        }
        manifest["sources"][source.key]["requests"].append(query)
        queue.append((source, query, request, set()))

    # Initialize every entry before the first possible auth/cap/rate failure.
    for source in sources:
        status = (
            "pending"
            if source.availability == "candidate"
            else "unsupported"
            if source.availability == "unsupported"
            else "unknown_history"
        )
        manifest["sources"][source.key] = {
            "status": status,
            "data_type": source.data_type,
            "method": source.preferred_method,
            "representation": source.representation,
            "history_status": "not_applicable"
            if source.representation in {"metadata", "reference"}
            else "unknown_history",
            "reason": "awaiting_observed_resource_name" if source.detail_parent else None,
            "error_status": None,
            "page_count": 0,
            "data_point_count": 0,
            "top_level_keys": [],
            "requests": [],
            "responses": [],
        }
        if source.availability != "candidate":
            continue
        if source.detail_parent:
            details.setdefault(source.detail_parent, []).append(source)
            seen_names[source.key] = set()

    try:
        five_years_ago = today.replace(year=today.year - 5)
    except ValueError:  # leap day: preserve a real calendar boundary
        five_years_ago = today.replace(year=today.year - 5, day=28)
    ranges = [
        ("recent", today),
        ("older_than_30_days", today - timedelta(days=31)),
        ("older_than_5_years", five_years_ago - timedelta(days=1)),
    ]
    for source in sources:
        if source.availability != "candidate" or source.detail_parent:
            continue
        try:
            if source.filter_kind == "none":
                enqueue(source, "snapshot")
            else:
                for label, start in ranges:
                    end = None if source.filter_kind == "ecg_start" else start + timedelta(days=1)
                    enqueue(source, label, start, end)
        except ValueError:
            manifest["sources"][source.key].update(
                status="failed", reason="invalid_request_contract"
            )
            failed.add(source.key)
    save_manifest()

    while queue:
        source, query, request, tokens = queue.popleft()
        entry = manifest["sources"][source.key]
        if source.key in failed:
            continue
        if budget.used >= budget.limit:
            manifest["stopped_reason"] = "request_cap"
            break

        def capture(
            body: bytes,
            status_code: int,
            *,
            source=source,
            entry=entry,
            query=query,
            request=request,
        ):
            relative = (
                Path("runs") / run_id / source.key / f"response-{len(entry['responses']):05d}.bin"
            )
            _write_private_bytes(output_dir / relative, body)
            entry["responses"].append(
                {
                    "path": relative.as_posix(),
                    "status_code": status_code,
                    "byte_count": len(body),
                    "query": query["label"],
                    "request": asdict(request),
                }
            )
            entry["page_count"] += 1

        try:
            payload = client.request_page(request, budget, capture=capture)
            points = source_points(source, payload)
            token = payload.get("nextPageToken")
            if token is not None and not isinstance(token, str):
                raise ValueError("invalid_page_token")
            query["page_count"] += 1
            query["data_point_count"] += len(points)
            entry["data_point_count"] += len(points)
            entry["top_level_keys"] = sorted(set(entry["top_level_keys"]) | payload.keys())
            query["next_page_token"] = token or None
            if token:
                if token in tokens:
                    raise ValueError("repeated_page_token")
                tokens.add(token)
                query["status"] = "partial"
                queue.append((source, query, with_page_token(request, token), tokens))
            else:
                query["status"] = "complete" if query["data_point_count"] else "empty"
            for detail in details.get(source.key, []):
                for point in points:
                    name = point.get("name")
                    if not isinstance(name, str) or name in seen_names[detail.key]:
                        continue
                    seen_names[detail.key].add(name)
                    try:
                        enqueue(detail, "detail", resource_name=name)
                    except ValueError:
                        manifest["sources"][detail.key].update(
                            status="failed", reason="invalid_resource_name"
                        )
                        failed.add(detail.key)
            entry["status"] = "partial"
        except RateLimited as exc:
            entry.update(
                status="rate_limited",
                reason="http_429",
                error_status=429,
                retry_after_s=exc.retry_after_s,
            )
            query["status"] = "rate_limited"
            manifest["stopped_reason"] = "rate_limited"
        except RequestCapExceeded:
            entry.update(status="partial", reason="request_cap")
            query["status"] = "partial"
            manifest["stopped_reason"] = "request_cap"
        except AuthError:
            entry.update(status="failed", reason="auth_error")
            query["status"] = "failed"
            manifest["stopped_reason"] = "auth_error"
        except OSError:
            entry.update(status="storage_error", reason="storage_error")
            query["status"] = "storage_error"
            manifest["stopped_reason"] = "storage_error"
        except (ApiError, ValueError) as exc:
            code = getattr(exc, "status_code", None)
            # Never propagate upstream messages/body content into summaries.
            reason = (
                f"http_{code}"
                if isinstance(exc, ApiError)
                else "repeated_page_token"
                if str(exc) == "repeated_page_token"
                else "invalid_response"
            )
            entry.update(
                status="permission_denied" if code == 403 else "failed",
                reason=reason,
                error_status=code,
            )
            query["status"] = entry["status"]
            failed.add(source.key)
        save_manifest()
        if manifest["stopped_reason"]:
            break

    for source in sources:
        entry = manifest["sources"][source.key]
        queries = entry["requests"]
        if entry["status"] in {"pending", "partial"}:
            if queries and all(q["status"] in {"complete", "empty"} for q in queries):
                entry["status"] = "ok" if entry["data_point_count"] else "empty"
                entry["reason"] = None
            elif entry["responses"]:
                entry["status"] = "partial"
        if report:
            report(
                f"{source.key}: {entry['status']} ({entry['page_count']} responses, {entry['data_point_count']} points)"
            )
    save_manifest()
    return manifest
