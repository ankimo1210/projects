"""Build the user-requested standalone HTML from a read-only salary snapshot."""

import argparse
import hashlib
import html
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bank_salary.classification import VERSION as CLASSIFICATION_VERSION
from bank_salary.classification import classify_job

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent


def load_snapshot(db_path, run_id=None):
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        if run_id is None:
            run_id = db.execute(
                "SELECT MAX(id) FROM runs WHERE finished_at IS NOT NULL"
            ).fetchone()[0]
        run = db.execute(
            "SELECT started_at,finished_at,status,report_json FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise ValueError(f"Unknown run {run_id}")
        if not run[1]:
            raise ValueError("The collection run is still running")
        query = (
            "SELECT j.company,j.requisition_id,r.observation_id,r.checked_at,r.error,r.listing_json,o.job_json "
            "FROM run_jobs r JOIN jobs j ON j.id=r.job_id LEFT JOIN observations o ON o.id=r.observation_id "
            "WHERE r.run_id=? ORDER BY j.company,j.requisition_id"
        )
        jobs = []
        for company, req, oid, checked, error, listing_json, encoded in db.execute(
            query, (run_id,)
        ):
            raw = json.loads(encoded or listing_json)
            ranges = []
            if oid is not None:
                cur = db.execute(
                    "SELECT minimum,maximum,currency,period,region,pay_type,evidence,parse_status FROM salary_ranges WHERE observation_id=? ORDER BY id",
                    (oid,),
                )
                keys = [c[0] for c in cur.description]
                ranges = [dict(zip(keys, row, strict=True)) for row in cur]
            status = (
                "detail_failed"
                if oid is None
                else "review"
                if error or any(r["parse_status"] == "review" for r in ranges)
                else "extracted"
                if ranges
                else "missing"
            )
            jobs.append(
                {
                    "id": f"{company}:{req}",
                    "company": company,
                    "req": req,
                    "title": raw.get("title", ""),
                    "department": raw.get("department", ""),
                    "classification": classify_job(raw),
                    "public_category": raw.get("job_level", ""),
                    "locations": raw.get("locations", []),
                    "employment_type": raw.get("employment_type", ""),
                    "posted": raw.get("posted_at", ""),
                    "checked": checked or "",
                    "url": raw.get("url", ""),
                    "source": raw.get("source", ""),
                    "status": status,
                    "ranges": ranges,
                }
            )
        report = json.loads(run[3])
        sources = []
        for label, data in report.get("sources", {}).items():
            note = (
                "対象一覧は前後で一致"
                if data.get("complete") and data.get("after_details", {}).get("complete")
                else "件数または一覧の完全性を未確認"
            )
            if label == "MS:workday":
                note = "対象一覧を取得。後続ページのtotal省略は先頭ページで照合"
            if label == "MS:eightfold":
                note = "表示総数と一意IDが不一致。NY該当分のみ補完"
            sources.append(
                {
                    "label": label,
                    "expected": data.get("expected"),
                    "unique": data.get("raw_unique"),
                    "note": note,
                }
            )

        def jst(value):
            return (
                datetime.fromisoformat(value)
                .astimezone(ZoneInfo("Asia/Tokyo"))
                .strftime("%Y-%m-%d %H:%M:%S")
            )

        snapshot = {
            "meta": {
                "run_id": run_id,
                "date": jst(run[0])[:10],
                "started": jst(run[0]),
                "finished": jst(run[1]),
                "status": run[2],
                "sources": sources,
                "limitations": report.get("limitations", []),
                "classification_version": CLASSIFICATION_VERSION,
            },
            "jobs": jobs,
        }
        encoded = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        snapshot["meta"]["snapshot_sha256"] = hashlib.sha256(encoded).hexdigest()
        return snapshot
    finally:
        db.close()


def build_report(db_path, output, run_id=None):
    source = Path(db_path).resolve()
    target = Path(output)
    if target.resolve() == source or (target.exists() and target.samefile(source)):
        raise ValueError(
            "HTML output must not overwrite the input SQLite database or an alias of it"
        )
    snapshot = load_snapshot(db_path, run_id)
    assets = PROJECT / "report"
    template = (assets / "template.html").read_text(encoding="utf-8")
    data = (
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    replacements = {
        "__TOKENS__": (WORKSPACE / "docs/templates/claude-report/tokens.css").read_text(
            encoding="utf-8"
        ),
        "__CSS__": (assets / "report.css").read_text(encoding="utf-8"),
        "__JS__": (assets / "report.js").read_text(encoding="utf-8"),
        "__DATA__": data,
        "__DATE__": html.escape(snapshot["meta"]["date"]),
        "__RUN__": str(snapshot["meta"]["run_id"]),
        "__START__": snapshot["meta"]["started"],
        "__END__": snapshot["meta"]["finished"],
        "__RUNSTATE__": html.escape(snapshot["meta"]["status"]),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template, encoding="utf-8")
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the standalone NY bank salary HTML report without modifying the database."
    )
    parser.add_argument(
        "--database", type=Path, default=WORKSPACE / "_data/bank-salary/jobs.sqlite"
    )
    parser.add_argument("--output", type=Path, default=WORKSPACE / "_data/bank-salary/report.html")
    parser.add_argument("--run-id", type=int)
    args = parser.parse_args(argv)
    snapshot = build_report(args.database, args.output, args.run_id)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "jobs": len(snapshot["jobs"]),
                "run_id": snapshot["meta"]["run_id"],
                "snapshot_sha256": snapshot["meta"]["snapshot_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
