"""Page-resumable archival acquisition with explicit incomplete-history states."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta

import duckdb

from health.archive import Archive
from health.archive_index import ArchiveIndex
from health.auth import AuthError
from health.client import ApiError, RateLimited, RequestBudget, RequestCapExceeded
from health.source_catalog import (
    RequestSpec,
    SourceSpec,
    build_request,
    source_points,
    with_page_token,
)


@dataclass
class ArchiveReport:
    requests_made: int = 0
    remaining: int = 0
    failures: list[dict] = field(default_factory=list)
    stopped_reason: str | None = None
    retry_after_s: int | None = None


class ArchiveEngine:
    def __init__(
        self,
        client,
        archive: Archive,
        index: ArchiveIndex,
        sources,
        today: date | None = None,
        *,
        history_start: date | None = None,
        granted_scopes: set[str] | None = None,
    ):
        self.client, self.archive, self.index = client, archive, index
        self.sources = {source.key: source for source in sources}
        self.today = today or date.today()
        self.history_start = history_start
        self.granted_scopes = granted_scopes
        for source in sources:
            index.register(source)
        # Detail work discovered by an earlier process is part of the durable queue.
        for key, metadata in index.con.execute(
            "SELECT stream_id, metadata FROM archive_sources"
        ).fetchall():
            if ".resource." in key:
                self.sources[key] = SourceSpec(**json.loads(metadata))

    def _initial(self, source: SourceSpec) -> dict:
        if source.preferred_method == "dailyRollUp":
            start = self.today - timedelta(days=min(source.max_range_days or 7, 7) - 1)
            if self.history_start:
                start = self.history_start
            end = min(
                self.today + timedelta(days=1), start + timedelta(days=source.max_range_days or 7)
            )
            request = build_request(source, start=start, end=end)
            return {
                **asdict(request),
                "range_start": start.isoformat(),
                "range_end": end.isoformat(),
                "history_verified": False,
                "bounded_history": bool(self.history_start),
            }
        request = build_request(source, allow_unverified_unbounded=True)
        verified = source.unbounded_verified or source.filter_kind == "none"
        return {
            **asdict(request),
            "history_verified": verified,
            "range_start": None,
            "range_end": None,
        }

    def _prepare(self, source: SourceSpec, *, rescan: bool) -> bool:
        work = self.index.work(source.key)
        if source.detail_parent and ".resource." not in source.key:
            return False
        if source.availability != "candidate":
            attempt = self.index.start(source.key, {}, source.representation)
            self.index.finish(
                attempt,
                "unsupported" if source.availability == "unsupported" else "unknown_history",
                "No verified readonly retrieval method is available",
            )
            return False
        if self.granted_scopes is not None and not set(source.readonly_scopes).issubset(
            self.granted_scopes
        ):
            attempt = self.index.start(source.key, {}, source.representation)
            self.index.finish(
                attempt,
                "permission_denied",
                "Required readonly scope has not been granted",
                http_status=403,
            )
            return False
        if work and work["state"] in {"partial", "rate_limited", "storage_error"} and not rescan:
            return True
        if (
            work
            and work["completed_on"] == self.today
            and work["state"] in {"complete", "empty", "unknown_history"}
            and not rescan
        ):
            return False
        if source.detail_parent:
            if not work:
                return False
            request = work["request"]
        else:
            request = self._initial(source)
        self.index.start(source.key, request, source.representation)
        return True

    def _capture(self, attempt: str):
        def capture(body: bytes, status: int) -> None:
            ref = self.archive.put(body)
            self.index.record_page(attempt, self.index.page_count(attempt), ref, status)

        return capture

    def _details(self, parent: SourceSpec, points: list[dict], attempt: str) -> list[str]:
        added = []
        children = [
            s
            for s in list(self.sources.values())
            if s.detail_parent == parent.key
            and ".resource." not in s.key
            and s.availability == "candidate"
        ]
        for child in children:
            for point in points:
                name = point.get("name") or point.get("dataPointName")
                if not isinstance(name, str):
                    self.index.record_detail_failure(attempt, child.key)
                    continue
                try:
                    request = build_request(child, resource_name=name)
                except ValueError:
                    self.index.record_detail_failure(attempt, child.key)
                    continue  # Never turn an untrusted API resource name into an arbitrary URL.
                key = child.key + ".resource." + hashlib.sha256(name.encode()).hexdigest()[:24]
                if key in self.sources and self.index.work(key) is not None:
                    continue
                dynamic = replace(child, key=key)
                self.index.enqueue_detail(
                    dynamic,
                    {
                        **asdict(request),
                        "history_verified": True,
                        "parent_stream": parent.key,
                        "resource_name": name,
                    },
                )
                # An unsuccessful commit must not make rediscovery skip this resource.
                self.sources[key] = dynamic
                added.append(key)
        return added

    def sync(self, budget: RequestBudget, *, rescan: bool = False) -> ArchiveReport:
        report = ArchiveReport()
        used_at_start = budget.used
        ready: set[str] = set()
        for source in list(self.sources.values()):
            try:
                if self._prepare(source, rescan=rescan):
                    ready.add(source.key)
            except ValueError:
                attempt = self.index.start(source.key, {}, source.representation)
                self.index.finish(
                    attempt, "unknown_history", "A verified request or history boundary is missing"
                )
        while ready:
            key = min(ready, key=lambda k: (self.index.work(k)["next_visit"], k))
            source, work = self.sources[key], self.index.work(key)
            attempt, info = work["attempt_id"], work["request"]
            request = RequestSpec(**{k: info.get(k) for k in ("method", "path", "params", "body")})
            try:
                request = with_page_token(request, work["page_token"])
                payload = self.client.request_page(request, budget, capture=self._capture(attempt))
                points = source_points(source, payload)
                seq = self.index.page_count(attempt) - 1
                if seq < 0:
                    raise ValueError("transport did not capture the response")
                self.index.set_points(attempt, seq, len(points))
                token = payload.get("nextPageToken")
                if token is not None and not isinstance(token, str):
                    raise ValueError("invalid continuation token")
                if not token:
                    self.index.confirm_terminal(attempt, next_page_token=token)
                ready.update(self._details(source, points, attempt))
                if token:
                    self.index.save_cursor(key, info, token, attempt)
                elif (
                    source.preferred_method == "dailyRollUp"
                    and info.get("bounded_history")
                    and date.fromisoformat(info["range_end"]) <= self.today
                ):
                    self.index.finish(
                        attempt, "complete" if self.index.point_count(attempt) else "empty"
                    )
                    start = date.fromisoformat(info["range_end"])
                    end = min(
                        self.today + timedelta(days=1),
                        start + timedelta(days=source.max_range_days or 7),
                    )
                    next_request = build_request(source, start=start, end=end)
                    self.index.start(
                        key,
                        {
                            **asdict(next_request),
                            "range_start": start.isoformat(),
                            "range_end": end.isoformat(),
                            "history_verified": False,
                            "bounded_history": True,
                        },
                        source.representation,
                    )
                else:
                    verified = info.get("history_verified", False)
                    status = "complete" if self.index.point_count(attempt) else "empty"
                    reason = None
                    if not verified:
                        status = "unknown_history"
                        reason = "Requested data was saved; coverage before the verified range remains unknown"
                    self.index.finish(
                        attempt, status, reason, history_complete=verified, completed_on=self.today
                    )
                    ready.remove(key)
            except RequestCapExceeded:
                report.stopped_reason = "request_cap"
                break
            except RateLimited as exc:
                self.index.finish(
                    attempt,
                    "rate_limited",
                    "Google Health rate limit; retry later",
                    http_status=429,
                )
                report.stopped_reason, report.retry_after_s = "rate_limited", exc.retry_after_s
                break
            except AuthError:
                self.index.finish(attempt, "failed", "Authorization expired; run health auth")
                report.stopped_reason = "authorization"
                break
            except ApiError as exc:
                status = "permission_denied" if exc.status_code == 403 else "failed"
                self.index.finish(
                    attempt,
                    status,
                    f"Google Health request failed (HTTP {exc.status_code})",
                    http_status=exc.status_code,
                )
                ready.remove(key)
            except (OSError, duckdb.Error):
                # A full disk may also prevent writing the failure row. Previously
                # committed objects/cursors remain valid; report the stop in memory.
                try:
                    self.index.finish(
                        attempt,
                        "storage_error",
                        "Local storage write failed; free capacity and resume",
                    )
                except (OSError, duckdb.Error):
                    pass
                report.stopped_reason = "storage_error"
                break
            except ValueError:
                self.index.finish(
                    attempt, "failed", "Invalid response, request, or repeated continuation token"
                )
                ready.remove(key)
        rows = self.index.coverage()
        report.requests_made = budget.used - used_at_start
        report.failures = [
            r for r in rows if r["status"] not in {"complete", "empty", "partial", "pending"}
        ]
        report.remaining = sum(r["status"] not in {"complete", "empty"} for r in rows)
        return report
