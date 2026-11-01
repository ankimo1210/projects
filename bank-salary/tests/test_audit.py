import csv
import tempfile
import unittest
from pathlib import Path

from bank_salary.audit import audit
from bank_salary.storage import Store
from test_storage import job


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "jobs.sqlite")
        self.run = self.store.start_run({"state": "NY"})
        self.store.record_listing(self.run, "JPM", ["42"], True)
        self.oid = self.store.save(self.run, job(), {"public": "original"})
        self.store.finish_run(self.run, "complete", {})
        self.store.export(self.run, self.root)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_checks_real_hashes_and_exported_amounts(self):
        result = audit(self.store, self.run, self.root)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["observations_checked"], 1)
        self.assertEqual(result["salary_csv_rows"], 1)

    def test_changed_compressed_original_fails_audit(self):
        with self.store.db:
            self.store.db.execute(
                "update observations set raw_zlib=? where id=?", (b"broken", self.oid)
            )
        result = audit(self.store, self.run, self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("source" in e for e in result["errors"]))

    def test_changed_csv_amount_fails_audit(self):
        path = self.root / "salary_ranges.csv"
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, list(reader)
        rows[0]["minimum"] = "999"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.assertFalse(audit(self.store, self.run, self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
