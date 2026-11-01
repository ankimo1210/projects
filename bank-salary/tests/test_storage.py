import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bank_salary.storage import Store


def job(amount=100000, title="Analyst"):
    return {
        "company": "JPM",
        "requisition_id": "42",
        "title": title,
        "department": "Markets",
        "job_level": "",
        "locations": ["New York, NY, US"],
        "employment_type": "Full time",
        "posted_at": "2026-10-30",
        "url": "https://example.com/job/42",
        "source": "oracle",
        "description": "Public job description.",
        "salary_fields": [
            {"Prompt": "Base Pay/Salary", "Value": f"New York,NY ${amount}-${amount + 10000}"}
        ],
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "jobs.sqlite")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def run_with_job(self, data):
        run = self.store.start_run({"state": "NY"})
        self.store.record_listing(run, "JPM", ["42"], True)
        observation = self.store.save(run, data, {"raw": data})
        self.store.finish_run(run, "complete", {})
        return run, observation

    def test_same_content_reuses_observation_and_new_run_records_it(self):
        r1, o1 = self.run_with_job(job())
        r2, o2 = self.run_with_job(job())
        self.assertNotEqual(r1, r2)
        self.assertEqual(o1, o2)
        self.assertEqual(self.store.db.execute("select count(*) from run_jobs").fetchone()[0], 2)

    def test_salary_change_preserves_history(self):
        _, first = self.run_with_job(job())
        _, second = self.run_with_job(job(120000))
        self.assertNotEqual(first, second)
        self.assertEqual(
            self.store.db.execute("select minimum from salary_ranges order by id").fetchall(),
            [(100000.0,), (120000.0,)],
        )

    def test_incomplete_scan_and_changed_scope_do_not_imply_absence(self):
        self.run_with_job(job())
        run = self.store.start_run({"state": "NY"})
        self.store.record_listing(run, "JPM", [], False)
        self.assertEqual(self.store.presence(run, "JPM", "42"), "unverified")
        other = self.store.start_run({"state": "NJ"})
        self.store.record_listing(other, "JPM", [], True)
        self.assertEqual(self.store.presence(other, "JPM", "42"), "unverified")
        complete = self.store.start_run({"state": "NY"})
        self.store.record_listing(complete, "JPM", [], True)
        self.assertEqual(self.store.presence(complete, "JPM", "42"), "not_listed_in_complete_scan")

    def test_failed_detail_is_exported_without_old_salary(self):
        self.run_with_job(job())
        run = self.store.start_run({"state": "NY"})
        self.store.record_listing(run, "JPM", ["42"], False)
        self.store.record_error(run, "JPM", "42", "HTTP 503")
        self.store.export(run, Path(self.temp.name))
        with (Path(self.temp.name) / "jobs.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["salary_status"], "detail_failed")
        with (Path(self.temp.name) / "salary_ranges.csv").open(
            encoding="utf-8-sig", newline=""
        ) as f:
            self.assertEqual(list(csv.DictReader(f)), [])

    def test_export_uses_requested_run_and_escapes_spreadsheet_formulas(self):
        old, _ = self.run_with_job(job(100000, "=bad()"))
        self.run_with_job(job(120000))
        self.store.export(old, Path(self.temp.name))
        with (Path(self.temp.name) / "salary_ranges.csv").open(
            encoding="utf-8-sig", newline=""
        ) as f:
            row = next(csv.DictReader(f))
        self.assertEqual(float(row["minimum"]), 100000)
        self.assertTrue(row["title"].startswith("'="))
        self.assertTrue(self.store.validate(old)["integrity_ok"])
        raw = self.store.db.execute("select job_json from observations order by id").fetchone()[0]
        self.assertEqual(json.loads(raw)["title"], "=bad()")

    def test_parser_failure_keeps_raw_observation_and_marks_review(self):
        run = self.store.start_run({"state": "NY"})
        self.store.record_listing(run, "JPM", ["42"], False)
        with patch(
            "bank_salary.storage.extract_salary", side_effect=ValueError("bad salary schema")
        ):
            oid = self.store.save(run, job(), {"raw": "kept"})
        self.assertIsNotNone(oid)
        base, salaries = next(self.store.rows(run))
        self.assertEqual(base["salary_status"], "review")
        self.assertIn("bad salary schema", base["detail_error"])
        self.assertEqual(salaries, [])

    def test_same_run_error_does_not_export_previous_successful_salary(self):
        run, _ = self.run_with_job(job())
        self.store.record_error(run, "JPM", "42", "HTTP 503")
        base, salaries = next(self.store.rows(run))
        self.assertEqual(base["salary_status"], "detail_failed")
        self.assertEqual(salaries, [])

    def test_unknown_run_export_keeps_existing_files(self):
        root = Path(self.temp.name)
        target = root / "jobs.csv"
        target.write_text("keep me", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.export(999, root)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_reparse_preserves_observations_and_raw_hash(self):
        run, oid = self.run_with_job(job())
        original = self.store.db.execute(
            "select raw_sha256,raw_zlib from observations where id=?", (oid,)
        ).fetchone()
        with self.store.db:
            self.store.db.execute("delete from salary_ranges where observation_id=?", (oid,))
        self.store.reparse(run)
        self.assertEqual(next(self.store.rows(run))[1][0]["minimum"], 100000)
        current = self.store.db.execute(
            "select raw_sha256,raw_zlib from observations where id=?", (oid,)
        ).fetchone()
        self.assertEqual(original, current)


if __name__ == "__main__":
    unittest.main()
