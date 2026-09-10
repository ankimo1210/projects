"""Audited read-only sources and pure request builders, separate from projections.

Date arguments are closed-open civil dates. A missing range is never evidence
of all-history semantics. Catalog JSON is bundled, not fetched at runtime.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class RequestSpec:
    method: str
    path: str
    params: dict = field(default_factory=dict)
    body: dict | None = None


@dataclass(frozen=True)
class SourceSpec:
    key: str
    data_type: str
    label: str
    path: str
    methods: tuple[str, ...]
    preferred_method: str | None
    readonly_scopes: tuple[str, ...]
    filter_kind: str
    filter_field: str | None
    page_size: int
    max_range_days: int | None
    unbounded_verified: bool
    representation: str
    availability: str
    evidence_url: str
    checked_at: str
    response_key: str | None = "dataPoints"
    detail_parent: str | None = None
    range_evidence_url: str | None = None
    notes: str = ""


_READ_METHODS = {
    "list",
    "get",
    "reconcile",
    "dailyRollUp",
    "rollUp",
    "getProfile",
    "getIdentity",
    "getSettings",
    "getIrnProfile",
    "exportExerciseTcx",
}
_FILTER_KINDS = {"none", "civil_interval", "civil_sample", "daily", "sleep_end", "ecg_start"}
_SCOPE = re.compile(r"https://www\.googleapis\.com/auth/googlehealth\.[a-z_]+\.readonly\Z")


def load_sources(path: Path | None = None) -> tuple[SourceSpec, ...]:
    """Load validated bundled sources; an optional fixture path is useful for audits."""
    document = json.loads(
        (path or files("health").joinpath("source_catalog.json")).read_text(encoding="utf-8")
    )
    if not isinstance(document, list):
        raise ValueError("source catalog must be a list")
    result = []
    keys = set()
    for row in document:
        if not isinstance(row, dict):
            raise ValueError("source must be an object")
        row = dict(row)
        for name in ("methods", "readonly_scopes"):
            if not isinstance(row.get(name), list) or not all(
                isinstance(x, str) for x in row[name]
            ):
                raise ValueError(f"{name} must be a list of strings")
            row[name] = tuple(row[name])
        try:
            source = SourceSpec(**row)
        except TypeError as exc:
            raise ValueError("invalid source fields") from exc
        if not re.fullmatch(r"[a-zA-Z0-9_-]+(?:[.:][a-zA-Z0-9_-]+)*", source.key):
            raise ValueError("invalid source key")
        if source.key in keys:
            raise ValueError(f"duplicate source key: {source.key}")
        keys.add(source.key)
        if any(not _SCOPE.fullmatch(s) for s in source.readonly_scopes):
            raise ValueError("only Google Health readonly scopes are allowed")
        if source.availability not in {"candidate", "unsupported", "unverified"}:
            raise ValueError("invalid availability")
        if source.filter_kind not in _FILTER_KINDS:
            raise ValueError("invalid filter kind")
        if source.representation not in {
            "source",
            "reconciled",
            "aggregate",
            "reference",
            "metadata",
        }:
            raise ValueError("invalid representation")
        if source.preferred_method is not None and (
            source.preferred_method not in _READ_METHODS
            or source.preferred_method not in source.methods
        ):
            raise ValueError("preferred_method must be a documented read method")
        if source.availability == "candidate" and (
            source.preferred_method is None or not source.readonly_scopes
        ):
            raise ValueError("candidate requires a read method and readonly scopes")
        if type(source.page_size) is not int or not 1 <= source.page_size <= 10000:
            raise ValueError("invalid page_size")
        if source.max_range_days is not None and (
            type(source.max_range_days) is not int or source.max_range_days <= 0
        ):
            raise ValueError("invalid max_range_days")
        if type(source.unbounded_verified) is not bool:
            raise ValueError("invalid unbounded_verified")
        if not source.path.startswith("/v4/users/") or any(
            x in source.path for x in ("..", "?", "#", "%", "\\")
        ):
            raise ValueError("invalid resource path")
        for url in (source.evidence_url, source.range_evidence_url):
            if url is not None and not url.startswith("https://developers.google.com/health/"):
                raise ValueError("evidence must refer to official Google Health documentation")
        date.fromisoformat(source.checked_at)
        result.append(source)
    for source in result:
        if source.detail_parent is not None and source.detail_parent not in keys:
            raise ValueError("unknown detail_parent")
    return tuple(result)


def validate_request(request: RequestSpec) -> None:
    """Reject write operations and ambiguous URL/path interpretation before auth."""
    path = request.path
    if not re.fullmatch(
        r"/v4/users/[A-Za-z0-9-]+/(?:[A-Za-z0-9-]+/)*[A-Za-z0-9-]+(?::[A-Za-z]+)?", path
    ):
        raise ValueError("request must use a fixed v4 user resource path")
    if request.method not in {"GET", "POST"}:
        raise ValueError("only read requests are allowed")
    if request.method == "POST" and not re.fullmatch(
        r"/v4/users/[A-Za-z0-9-]+/dataTypes/[a-z0-9-]+/dataPoints:(?:dailyRollUp|rollUp)", path
    ):
        raise ValueError("POST is only allowed for read-only rollups")
    if request.method == "GET" and request.body is not None:
        raise ValueError("GET request body must be empty")
    if not isinstance(request.params, dict) or (
        request.body is not None and not isinstance(request.body, dict)
    ):
        raise ValueError("request params/body must be objects")


def build_request(
    source: SourceSpec,
    *,
    start: date | None = None,
    end: date | None = None,
    page_token: str | None = None,
    resource_name: str | None = None,
    allow_unverified_unbounded: bool = False,
) -> RequestSpec:
    """Build one request; start inclusive, end exclusive, never infer history.

    ECG supports only a UTC lower bound (date means UTC midnight); end is
    rejected. Detail resources require an observed, type-matching resource name.
    max_range_days=None means no documented maximum, not a history guarantee.
    """
    if source.availability != "candidate" or source.preferred_method is None:
        raise ValueError(f"unavailable source: {source.key}")
    if (
        source.preferred_method not in _READ_METHODS
        or source.preferred_method not in source.methods
    ):
        raise ValueError("undocumented read method")
    path = source.path
    params: dict = {}
    body = None
    method = "GET"
    if source.detail_parent:
        if not resource_name:
            raise ValueError("detail request requires resource_name")
        # List responses may carry the system user ID rather than the me alias.
        template = re.escape(path.removeprefix("/v4/")).replace(
            "users/me/", r"users/[A-Za-z0-9-]+/"
        )
        template = template.replace(r"\{dataPoint\}", r"[A-Za-z0-9-]+").replace(
            r"\{pairedDevice\}", r"[A-Za-z0-9-]+"
        )
        if not re.fullmatch(template, resource_name):
            raise ValueError("resource_name does not match this detail source")
        path = "/v4/" + resource_name
    elif resource_name is not None:
        raise ValueError("resource_name is only valid for detail sources")
    for value in (start, end):
        if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
            raise ValueError("range boundaries must be dates")
    if source.filter_kind == "none":
        if start is not None or end is not None:
            raise ValueError("resource does not accept a date range")
    elif start is None and end is None:
        if source.preferred_method not in {"list", "reconcile"}:
            raise ValueError("rollup requires a date range")
        if not source.unbounded_verified and not allow_unverified_unbounded:
            raise ValueError("unbounded history semantics are unverified; supply a range")
    elif source.filter_kind == "ecg_start":
        if end is not None:
            raise ValueError("ECG does not support an upper bound")
        if start is None:
            raise ValueError("ECG requires a start date")
        params["filter"] = f'{source.filter_field} >= "{start.isoformat()}T00:00:00Z"'
    else:
        if start is None or end is None or end <= start:
            raise ValueError("range requires start < end")
        if source.max_range_days is not None and (end - start).days > source.max_range_days:
            raise ValueError("range exceeds documented maximum")
        if source.preferred_method == "dailyRollUp":

            def civil(d):
                return {"date": {"year": d.year, "month": d.month, "day": d.day}, "time": {}}

            body = {
                "range": {"start": civil(start), "end": civil(end)},
                "windowSizeDays": 1,
            }
            # The 2026-09-07 integration accepts the default page size but
            # rejects explicit 1000 for these daily rollups. Keep pagination.
            method = "POST"
        else:
            if not source.filter_field:
                raise ValueError("source has no verified filter field")
            params["filter"] = (
                f'{source.filter_field} >= "{start.isoformat()}" AND {source.filter_field} < "{end.isoformat()}"'
            )
    if source.preferred_method in {"list", "reconcile"}:
        params["pageSize"] = source.page_size
    request = RequestSpec(method, path, params, body)
    if page_token is not None:
        if source.preferred_method not in {"list", "reconcile", "dailyRollUp"}:
            raise ValueError("resource does not support pagination")
        request = with_page_token(request, page_token)
    validate_request(request)
    return request


def with_page_token(request: RequestSpec, token: str | None) -> RequestSpec:
    """Return an independent request, changing only the pagination token."""
    if token is not None and (not isinstance(token, str) or not token):
        raise ValueError("page token must be a nonempty string or None")
    params = dict(request.params)
    body = json.loads(json.dumps(request.body)) if request.body is not None else None
    target = body if request.method == "POST" else params
    if target is None:
        raise ValueError("paged POST requires a body")
    target.pop("pageToken", None)
    if token is not None:
        target["pageToken"] = token
    return replace(request, params=params, body=body)


def source_points(source: SourceSpec, payload: dict) -> list[dict]:
    """Validate the envelope, preserving every point and unknown attribute.

    Proto JSON can omit an empty repeated field. An explicit null/wrong type
    is invalid. A singleton get response is itself one resource.
    """
    if not isinstance(payload, dict):
        raise ValueError("response must be an object")
    if source.response_key is None:
        return [payload]
    points = payload.get(source.response_key, [])
    if not isinstance(points, list) or not all(isinstance(p, dict) for p in points):
        raise ValueError(f"{source.response_key} must be a list of objects")
    return points
