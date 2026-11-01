"""Versioned observations and explicit run membership; no inferred hiring end dates."""

import csv
import hashlib
import json
import sqlite3
import zlib
from datetime import UTC, datetime
from pathlib import Path

from .parsing import extract_salary


def utcnow():
    return datetime.now(UTC).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
 config_json TEXT NOT NULL, status TEXT NOT NULL, report_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS jobs (
 id INTEGER PRIMARY KEY, company TEXT NOT NULL, requisition_id TEXT NOT NULL,
 first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, UNIQUE(company,requisition_id)
);
CREATE TABLE IF NOT EXISTS observations (
 id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
 content_hash TEXT NOT NULL, observed_at TEXT NOT NULL, job_json TEXT NOT NULL,
 raw_sha256 TEXT NOT NULL, raw_zlib BLOB NOT NULL, UNIQUE(job_id,content_hash)
);
CREATE TABLE IF NOT EXISTS run_jobs (
 run_id INTEGER NOT NULL REFERENCES runs(id), job_id INTEGER NOT NULL REFERENCES jobs(id),
 observation_id INTEGER REFERENCES observations(id), checked_at TEXT, error TEXT,
 listing_json TEXT NOT NULL DEFAULT '{}', PRIMARY KEY(run_id,job_id)
);
CREATE TABLE IF NOT EXISTS coverage (
 run_id INTEGER NOT NULL REFERENCES runs(id), company TEXT NOT NULL,
 complete INTEGER NOT NULL, PRIMARY KEY(run_id,company)
);
CREATE TABLE IF NOT EXISTS salary_ranges (
 id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL REFERENCES observations(id),
 minimum REAL NOT NULL, maximum REAL NOT NULL, currency TEXT NOT NULL,
 period TEXT NOT NULL, region TEXT NOT NULL, pay_type TEXT NOT NULL,
 evidence TEXT NOT NULL, parse_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_salary_observation ON salary_ranges(observation_id);
CREATE INDEX IF NOT EXISTS ix_observation_job ON observations(job_id);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def start_run(self, config):
        with self.db:
            return self.db.execute(
                "INSERT INTO runs(started_at,config_json,status) VALUES(?,?,?)",
                (utcnow(), canonical(config), "running"),
            ).lastrowid

    def _job_id(self, company, requisition_id):
        stamp = utcnow()
        self.db.execute(
            "INSERT INTO jobs(company,requisition_id,first_seen,last_seen) VALUES(?,?,?,?) "
            "ON CONFLICT(company,requisition_id) DO UPDATE SET last_seen=excluded.last_seen",
            (company, str(requisition_id), stamp, stamp),
        )
        return self.db.execute(
            "SELECT id FROM jobs WHERE company=? AND requisition_id=?",
            (company, str(requisition_id)),
        ).fetchone()[0]

    def record_listing(self, run_id, company, ids, complete):
        """ids can be a list of IDs or a mapping of ID to the public listing payload."""
        with self.db:
            for req in ids:
                jid = self._job_id(company, req)
                listing = ids[req] if isinstance(ids, dict) else {}
                self.db.execute(
                    "INSERT INTO run_jobs(run_id,job_id,listing_json) VALUES(?,?,?) "
                    "ON CONFLICT(run_id,job_id) DO UPDATE SET listing_json=excluded.listing_json",
                    (run_id, jid, canonical(listing)),
                )
            self.db.execute(
                "INSERT OR REPLACE INTO coverage VALUES(?,?,?)", (run_id, company, int(complete))
            )

    def record_error(self, run_id, company, requisition_id, message):
        with self.db:
            jid = self._job_id(company, requisition_id)
            self.db.execute(
                "INSERT INTO run_jobs(run_id,job_id,checked_at,error) VALUES(?,?,?,?) "
                "ON CONFLICT(run_id,job_id) DO UPDATE SET observation_id=NULL,checked_at=excluded.checked_at,error=excluded.error",
                (run_id, jid, utcnow(), str(message)),
            )

    def save(self, run_id, job, payload):
        encoded = canonical(job)
        content_hash = hashlib.sha256(encoded.encode()).hexdigest()
        raw = canonical(payload).encode()
        stamp = utcnow()
        parse_error = None
        try:
            parsed = extract_salary(
                job["company"], job["description"], job.get("salary_fields", [])
            )
        except Exception as exc:
            parsed = []
            parse_error = f"salary_parse_error: {type(exc).__name__}: {exc}"
        with self.db:
            jid = self._job_id(job["company"], job["requisition_id"])
            row = self.db.execute(
                "SELECT id FROM observations WHERE job_id=? AND content_hash=?", (jid, content_hash)
            ).fetchone()
            if row:
                oid = row[0]
            else:
                oid = self.db.execute(
                    "INSERT INTO observations(job_id,content_hash,observed_at,job_json,raw_sha256,raw_zlib) VALUES(?,?,?,?,?,?)",
                    (
                        jid,
                        content_hash,
                        stamp,
                        encoded,
                        hashlib.sha256(raw).hexdigest(),
                        zlib.compress(raw, 6),
                    ),
                ).lastrowid
                for salary in parsed:
                    self.db.execute(
                        "INSERT INTO salary_ranges(observation_id,minimum,maximum,currency,period,region,pay_type,evidence,parse_status) VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            oid,
                            *(
                                salary[k]
                                for k in (
                                    "minimum",
                                    "maximum",
                                    "currency",
                                    "period",
                                    "region",
                                    "pay_type",
                                    "evidence",
                                    "parse_status",
                                )
                            ),
                        ),
                    )
            self.db.execute(
                "INSERT INTO run_jobs(run_id,job_id,observation_id,checked_at,error) VALUES(?,?,?,?,?) "
                "ON CONFLICT(run_id,job_id) DO UPDATE SET observation_id=excluded.observation_id,checked_at=excluded.checked_at,error=excluded.error",
                (run_id, jid, oid, stamp, parse_error),
            )
        return oid

    def finish_run(self, run_id, status, report):
        with self.db:
            self.db.execute(
                "UPDATE runs SET status=?,finished_at=?,report_json=? WHERE id=?",
                (status, utcnow(), canonical(report), run_id),
            )

    def presence(self, run_id, company, requisition_id):
        present = self.db.execute(
            "SELECT r.observation_id FROM run_jobs r JOIN jobs j ON j.id=r.job_id WHERE r.run_id=? AND j.company=? AND j.requisition_id=?",
            (run_id, company, str(requisition_id)),
        ).fetchone()
        if present:
            return "observed" if present[0] is not None else "detail_failed"
        coverage = self.db.execute(
            "SELECT complete FROM coverage WHERE run_id=? AND company=?", (run_id, company)
        ).fetchone()
        old = self.db.execute(
            "SELECT 1 FROM run_jobs r JOIN jobs j ON j.id=r.job_id JOIN runs old ON old.id=r.run_id "
            "JOIN runs current ON current.id=? WHERE old.config_json=current.config_json AND old.id<current.id "
            "AND j.company=? AND j.requisition_id=? LIMIT 1",
            (run_id, company, str(requisition_id)),
        ).fetchone()
        return "not_listed_in_complete_scan" if coverage and coverage[0] and old else "unverified"

    def latest_run(self):
        row = self.db.execute("SELECT MAX(id) FROM runs").fetchone()
        if not row or row[0] is None:
            raise ValueError("No collection runs exist")
        return row[0]

    def rows(self, run_id):
        query = (
            "SELECT j.company,j.requisition_id,r.observation_id,r.checked_at,r.error,r.listing_json,o.job_json,o.content_hash "
            "FROM run_jobs r JOIN jobs j ON j.id=r.job_id LEFT JOIN observations o ON o.id=r.observation_id "
            "WHERE r.run_id=? ORDER BY j.company,j.requisition_id"
        )
        for (
            company,
            req,
            oid,
            checked,
            error,
            listing_json,
            job_json,
            content_hash,
        ) in self.db.execute(query, (run_id,)):
            job = json.loads(job_json or listing_json)
            salaries = []
            if oid is not None:
                cursor = self.db.execute(
                    "SELECT minimum,maximum,currency,period,region,pay_type,evidence,parse_status FROM salary_ranges WHERE observation_id=? ORDER BY id",
                    (oid,),
                )
                keys = [c[0] for c in cursor.description]
                salaries = [dict(zip(keys, row, strict=True)) for row in cursor]
            status = (
                "detail_failed"
                if oid is None
                else (
                    "review"
                    if error or any(s["parse_status"] == "review" for s in salaries)
                    else ("extracted" if salaries else "not_disclosed_or_unparsed")
                )
            )
            base = {
                "run_id": run_id,
                "company": company,
                "requisition_id": req,
                "title": job.get("title", ""),
                "department": job.get("department", ""),
                "job_level": job.get("job_level", ""),
                "locations": " | ".join(job.get("locations", [])),
                "employment_type": job.get("employment_type", ""),
                "posted_at": job.get("posted_at", ""),
                "url": job.get("url", ""),
                "source": job.get("source", ""),
                "salary_status": status,
                "range_count": len(salaries),
                "checked_at_utc": checked or "",
                "observation_id": oid or "",
                "content_hash": content_hash or "",
                "detail_error": error or "",
            }
            yield base, salaries

    def export(self, run_id, directory):
        if not self.db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
            raise ValueError(f"Unknown run {run_id}")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        job_fields = [
            "run_id",
            "company",
            "requisition_id",
            "title",
            "department",
            "job_level",
            "locations",
            "employment_type",
            "posted_at",
            "url",
            "source",
            "salary_status",
            "range_count",
            "checked_at_utc",
            "observation_id",
            "content_hash",
            "detail_error",
        ]
        pay_fields = [
            *job_fields,
            "minimum",
            "maximum",
            "currency",
            "period",
            "region",
            "pay_type",
            "evidence",
            "parse_status",
        ]

        def safe(row):
            return {
                k: "'" + v
                if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@"))
                else v
                for k, v in row.items()
            }

        with (
            (directory / "jobs.csv").open("w", encoding="utf-8-sig", newline="") as jf,
            (directory / "salary_ranges.csv").open("w", encoding="utf-8-sig", newline="") as sf,
        ):
            jw, sw = (
                csv.DictWriter(jf, fieldnames=job_fields),
                csv.DictWriter(sf, fieldnames=pay_fields),
            )
            jw.writeheader()
            sw.writeheader()
            for base, salaries in self.rows(run_id):
                jw.writerow(safe(base))
                for salary in salaries:
                    sw.writerow(safe({**base, **salary}))

    def validate(self, run_id):
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = self.db.execute("PRAGMA foreign_key_check").fetchall()
        stats = {}
        for base, salaries in self.rows(run_id):
            group = stats.setdefault(
                base["company"],
                {
                    "jobs": 0,
                    "detail_failed": 0,
                    "with_salary": 0,
                    "without_salary": 0,
                    "review": 0,
                    "ranges": 0,
                    "period_unspecified": 0,
                },
            )
            group["jobs"] += 1
            if base["salary_status"] == "detail_failed":
                group["detail_failed"] += 1
            elif salaries:
                group["with_salary"] += 1
            else:
                group["without_salary"] += 1
            group["review"] += int(base["salary_status"] == "review")
            group["ranges"] += len(salaries)
            group["period_unspecified"] += sum(s["period"] == "unspecified" for s in salaries)
        run = self.db.execute(
            "SELECT started_at,finished_at,status,config_json,report_json FROM runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if run is None:
            raise ValueError(f"Unknown run {run_id}")
        return {
            "run_id": run_id,
            "started_at_utc": run[0],
            "finished_at_utc": run[1],
            "status": run[2],
            "config": json.loads(run[3]),
            "collection": json.loads(run[4]),
            "integrity_ok": integrity == "ok" and not foreign_keys,
            "foreign_key_errors": foreign_keys,
            "companies": stats,
        }

    def reparse(self, run_id):
        """Rebuild derived salary rows; immutable observations and source bytes stay intact."""
        self.validate(run_id)
        observations = self.db.execute(
            "SELECT DISTINCT o.id,o.job_json FROM observations o JOIN run_jobs r ON r.observation_id=o.id WHERE r.run_id=?",
            (run_id,),
        ).fetchall()
        with self.db:
            for oid, encoded in observations:
                job = json.loads(encoded)
                error = None
                try:
                    parsed = extract_salary(
                        job["company"], job["description"], job.get("salary_fields", [])
                    )
                except Exception as exc:
                    parsed = []
                    error = f"salary_parse_error: {type(exc).__name__}: {exc}"
                self.db.execute("DELETE FROM salary_ranges WHERE observation_id=?", (oid,))
                for salary in parsed:
                    self.db.execute(
                        "INSERT INTO salary_ranges(observation_id,minimum,maximum,currency,period,region,pay_type,evidence,parse_status) VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            oid,
                            *(
                                salary[k]
                                for k in (
                                    "minimum",
                                    "maximum",
                                    "currency",
                                    "period",
                                    "region",
                                    "pay_type",
                                    "evidence",
                                    "parse_status",
                                )
                            ),
                        ),
                    )
                self.db.execute(
                    "UPDATE run_jobs SET error=? WHERE observation_id=? AND (error IS NULL OR error LIKE ?)",
                    (error, oid, "salary_parse_error:%"),
                )
            report = json.loads(
                self.db.execute("SELECT report_json FROM runs WHERE id=?", (run_id,)).fetchone()[0]
            )
            report.setdefault("derivations", []).append(
                {
                    "reparsed_at_utc": utcnow(),
                    "observations": len(observations),
                    "extractor_sha256": hashlib.sha256(
                        Path(__file__).with_name("parsing.py").read_bytes()
                    ).hexdigest(),
                }
            )
            self.db.execute("UPDATE runs SET report_json=? WHERE id=?", (canonical(report), run_id))
        return len(observations)
