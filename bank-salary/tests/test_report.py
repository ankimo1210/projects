import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bank_salary.report import build_report, load_snapshot
from bank_salary.storage import Store
from test_storage import job


class ReportTests(unittest.TestCase):
    def test_input_database_cannot_be_overwritten_through_output_or_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "jobs.sqlite"
            store = Store(db)
            run = store.start_run({"state": "NY"})
            store.save(run, job(), {"source": "official"})
            store.finish_run(run, "complete", {})
            store.close()
            symbolic = root / "symbolic.sqlite"
            symbolic.symlink_to(db)
            hard = root / "hard.sqlite"
            hard.hardlink_to(db)
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            for target in [db, symbolic, hard]:
                with self.assertRaises(ValueError):
                    build_report(db, target, run)
                self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)

    def test_build_is_read_only_and_embeds_the_requested_run_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "jobs.sqlite"
            store = Store(db)
            run = store.start_run({"state": "NY"})
            data = job(title="Equity Trading Software Engineer </script><img src=x>")
            store.record_listing(run, "JPM", ["42"], True)
            store.save(run, data, {"source": "official"})
            store.finish_run(run, "complete", {})
            store.close()
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            snapshot = load_snapshot(db, run)
            self.assertEqual(snapshot["jobs"][0]["ranges"][0]["minimum"], 100000)
            self.assertEqual(len(snapshot["jobs"]), 1)
            classification = snapshot["jobs"][0]["classification"]
            self.assertEqual(classification["department"]["label"], "Technology")
            self.assertEqual(classification["subdepartment"]["label"], "株式・デリバティブ技術")
            self.assertEqual(classification["occupation"]["label"], "エンジニア・開発")
            self.assertEqual(classification["occupation"]["basis"], "タイトル")
            self.assertIn("classification_version", snapshot["meta"])
            out = root / "report.html"
            build_report(db, out, run)
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)
            html = out.read_text(encoding="utf-8")
            self.assertNotIn("</script><img src=x>", html)
            self.assertIn("\\u003c/script", html)
            self.assertIn("BankSalaryReport", html)
            self.assertGreater(len(html), 20000)


if __name__ == "__main__":
    unittest.main()
