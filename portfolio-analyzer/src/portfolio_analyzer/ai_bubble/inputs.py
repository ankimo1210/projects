"""Long-format financial rows: point-in-time selection and a quality audit.

Every row says when it became knowable (``available_at``). Selection keeps, for
each issuer / metric / period / accounting basis, the latest version known at
``as_of``, so a restatement enters only after its own filing. Gaps stay gaps: a
row without a value must give its reason as ``quality = "missing:<reason>"``.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

REQUIRED_FIELDS = (
    "issuer_id",
    "metric",
    "value",
    "unit",
    "period_start",
    "period_end",
    "published_at",
    "available_at",
    "retrieved_at",
    "source_url",
    "document_id",
    "accounting_basis",
    "quality",
)
_KEY = ("issuer_id", "metric", "period_start", "period_end", "accounting_basis")
_TIMESTAMPS = ("published_at", "available_at", "retrieved_at")
MISSING = "missing:"


def parse_utc(value: Any, label: str) -> datetime:
    """An ISO timestamp that names its offset, as UTC."""
    try:
        when = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO timestamp with a timezone") from exc
    if when.utcoffset() is None:
        raise ValueError(f"{label} needs a timezone")
    return when.astimezone(UTC)


def _require(row: dict[str, Any]) -> None:
    absent = [field for field in REQUIRED_FIELDS if field not in row]
    if absent:
        raise ValueError(f"row lacks required field(s): {', '.join(absent)}")


def select_as_of(rows: list[dict[str, Any]], as_of_utc: str) -> list[dict[str, Any]]:
    """The version of each fact that was available at ``as_of_utc``."""
    cutoff = parse_utc(as_of_utc, "as_of_utc")
    latest: dict[tuple[Any, ...], tuple[datetime, dict[str, Any]]] = {}
    for row in rows:
        _require(row)
        available = parse_utc(row["available_at"], "available_at")
        if available > cutoff:
            continue
        key = tuple(row[k] for k in _KEY)
        held = latest.get(key)
        if held is None or available > held[0]:
            latest[key] = (available, row)
        elif available == held[0]:
            if row["value"] != held[1]["value"]:
                raise ValueError(f"conflicting values at the same available_at for {key}")
            if str(row["document_id"]) < str(held[1]["document_id"]):
                latest[key] = (available, row)
    return [
        row for _, row in sorted(latest.values(), key=lambda kv: tuple(str(kv[1][k]) for k in _KEY))
    ]


def _problem(row: dict[str, Any]) -> str | None:
    absent = [field for field in REQUIRED_FIELDS if field not in row]
    if absent:
        return f"missing field(s): {', '.join(absent)}"
    stamps = {}
    for field in _TIMESTAMPS:
        try:
            stamps[field] = parse_utc(row[field], field)
        except ValueError as exc:
            return str(exc)
    if stamps["available_at"] < stamps["published_at"]:
        return "available before published"
    if not str(row["unit"] or "").strip():
        return "unit missing"
    value, quality = row["value"], str(row["quality"] or "")
    if value is None:
        if not quality.startswith(MISSING) or not quality[len(MISSING) :].strip():
            return "value missing without a reason"
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "value is not a finite number"
    if quality.startswith(MISSING):
        return "value present but quality says missing"
    return None


def audit_inputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Errors (rows unusable as given) and explained gaps, kept apart."""
    errors: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        reason = _problem(row)
        if reason:
            errors.append({"index": index, "reason": reason})
        elif row["value"] is None:
            missing.append(
                {
                    "issuer_id": row["issuer_id"],
                    "metric": row["metric"],
                    "period_end": row["period_end"],
                    "reason": str(row["quality"])[len(MISSING) :],
                }
            )
    return {
        "ok": not errors,
        "errors": errors,
        "missing": missing,
        "issuers": sorted({str(r["issuer_id"]) for r in rows if r.get("issuer_id")}),
        "sources": sorted({str(r["source_url"]) for r in rows if r.get("source_url")}),
    }


def reconcile(
    rows: list[dict[str, Any]], references: list[dict[str, Any]], as_of_utc: str
) -> list[dict[str, Any]]:
    """Check values copied from an original document against the as-of rows.

    A reference gives issuer, metric, period, the printed value in the row's
    unit and ``rounding`` (the printed precision, e.g. 1e6 for "in millions").
    It matches when the parsed value is within half of that precision. A
    reference may name ``accounting_basis`` when several bases cover a period.
    """
    selected = select_as_of(rows, as_of_utc)
    out = []
    for reference in references:
        hits = [
            r
            for r in selected
            if all(
                r[k] == reference[k] for k in ("issuer_id", "metric", "period_start", "period_end")
            )
            and reference.get("accounting_basis", r["accounting_basis"]) == r["accounting_basis"]
        ]
        result = {**reference, "parsed": None, "difference": None, "match": False}
        if not hits:
            result["reason"] = "no row"
        elif len(hits) > 1:
            result["reason"] = "several accounting bases; name one"
        elif hits[0]["value"] is None:
            result["reason"] = f"row is a gap ({hits[0]['quality']})"
        else:
            hit = hits[0]
            difference = hit["value"] - float(reference["value"])
            result.update(
                parsed=hit["value"],
                difference=difference,
                match=abs(difference) <= float(reference["rounding"]) / 2,
                document_id=hit["document_id"],
                row_source_url=hit["source_url"],
            )
        out.append(result)
    return out
