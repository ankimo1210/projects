"""Independent output checks against retained source bytes and SQLite rows."""

import csv
import hashlib
import json
import math
import re
import zlib
from collections import Counter
from pathlib import Path

from .storage import utcnow


def audit(store, run_id, directory):
    errors = []
    structural = store.validate(run_id)
    if not structural["integrity_ok"]:
        errors.append("SQLite integrity or foreign keys failed")
    observations = store.db.execute(
        "SELECT DISTINCT o.id,o.content_hash,o.job_json,o.raw_sha256,o.raw_zlib "
        "FROM observations o JOIN run_jobs r ON r.observation_id=o.id WHERE r.run_id=?",
        (run_id,),
    ).fetchall()
    for oid, content_hash, encoded, raw_hash, compressed in observations:
        if hashlib.sha256(encoded.encode()).hexdigest() != content_hash:
            errors.append(f"observation {oid}: normalized content hash mismatch")
        try:
            raw = zlib.decompress(compressed)
            json.loads(raw)
            if hashlib.sha256(raw).hexdigest() != raw_hash:
                errors.append(f"observation {oid}: source hash mismatch")
        except (ValueError, zlib.error, UnicodeDecodeError) as exc:
            errors.append(f"observation {oid}: invalid source bytes: {exc}")
        job = json.loads(encoded)
        source_texts = [job.get("description", "")]
        labelled_fields = []
        for field in job.get("salary_fields") or []:
            if not isinstance(field, dict):
                continue
            value = field.get("Value")
            if value is not None:
                source_texts.append(str(value))
                labelled_fields.append(
                    (field.get("Prompt") or "").strip() + ": " + str(value).strip()
                )
        for low, high, evidence, status in store.db.execute(
            "SELECT minimum,maximum,evidence,parse_status FROM salary_ranges WHERE observation_id=?",
            (oid,),
        ):
            if not any(evidence in text for text in source_texts) and not all(
                part in labelled_fields for part in evidence.split("; ")
            ):
                errors.append(f"observation {oid}: salary evidence is absent from retained source")
            values = []
            for token in re.findall(r"\d+(?:,\d+)*(?:\.\d+)?[Kk]?", evidence):
                values.append(
                    float(token.rstrip("Kk").replace(",", ""))
                    * (1000 if token.lower().endswith("k") else 1)
                )
            if low not in values or high not in values:
                errors.append(f"observation {oid}: amounts do not appear in source evidence")
            if (
                not math.isfinite(low)
                or not math.isfinite(high)
                or (status == "parsed" and not 0 < low <= high)
            ):
                errors.append(f"observation {oid}: invalid accepted salary range")
    expected_jobs = Counter(
        (company, req, str(oid or ""))
        for company, req, oid in store.db.execute(
            "SELECT j.company,j.requisition_id,r.observation_id FROM run_jobs r JOIN jobs j ON j.id=r.job_id WHERE r.run_id=?",
            (run_id,),
        )
    )
    keys = [
        "company",
        "requisition_id",
        "observation_id",
        "minimum",
        "maximum",
        "currency",
        "period",
        "region",
        "pay_type",
        "parse_status",
    ]
    expected_salaries = Counter(
        (*row[:2], str(row[2]), *row[3:])
        for row in store.db.execute(
            "SELECT j.company,j.requisition_id,r.observation_id,s.minimum,s.maximum,s.currency,s.period,s.region,s.pay_type,s.parse_status "
            "FROM run_jobs r JOIN jobs j ON j.id=r.job_id JOIN salary_ranges s ON s.observation_id=r.observation_id WHERE r.run_id=?",
            (run_id,),
        )
    )
    actual_jobs, actual_salaries = Counter(), Counter()
    try:
        with (Path(directory) / "jobs.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                actual_jobs[(row["company"], row["requisition_id"], row["observation_id"])] += 1
                if int(row["run_id"]) != run_id:
                    errors.append("jobs.csv contains a different run")
        with (Path(directory) / "salary_ranges.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                row["minimum"], row["maximum"] = float(row["minimum"]), float(row["maximum"])
                actual_salaries[tuple(row[k] for k in keys)] += 1
                if int(row["run_id"]) != run_id:
                    errors.append("salary_ranges.csv contains a different run")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"CSV read failed: {exc}")
    if actual_jobs != expected_jobs:
        errors.append("jobs.csv membership/count differs from the selected SQLite run")
    if actual_salaries != expected_salaries:
        errors.append("salary_ranges.csv membership/amounts/units differ from SQLite")
    return {
        "run_id": run_id,
        "checked_at_utc": utcnow(),
        "ok": not errors,
        "observations_checked": len(observations),
        "jobs_csv_rows": sum(actual_jobs.values()),
        "salary_csv_rows": sum(actual_salaries.values()),
        "error_count": len(errors),
        "errors": errors[:30],
        "checks": [
            "SQLite integrity and foreign keys",
            "normalized content SHA-256",
            "compressed source JSON SHA-256",
            "salary evidence and amounts in retained sources",
            "accepted range bounds",
            "CSV membership, run IDs, counts, amounts and units",
        ],
    }
