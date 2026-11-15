import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import network_monitor as monitor
import speed_monitor as speed


def route():
    return {"ok": True, "gateway": "192.168.1.1", "interface": "en0"}


def successful(direction, size):
    return {"ok": True, "expected_bytes": size, "transferred_bytes": size,
            "seconds": 0.1, "mbps": 160 if direction == "download" else 80}


class SpeedTests(unittest.TestCase):
    def setUp(self):
        self.context = patch.object(speed, "execution_context", return_value={"darwin_background": False, "nice": 0})
        self.context.start()
        self.addCleanup(self.context.stop)

    def test_validated_bytes_and_time_determine_mbps(self):
        response = subprocess.CompletedProcess([], 0, json.dumps({
            "http_code": 200, "size_download": 2_000_000, "time_total": 0.08}).encode(), b"")
        with patch.object(speed.subprocess, "run", return_value=response):
            result = speed.transfer("download", 2_000_000)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mbps"], 200)

    def test_partial_timeout_is_not_a_valid_speed_or_zero(self):
        response = subprocess.CompletedProcess([], 28, json.dumps({
            "http_code": 200, "size_download": 100_000, "time_total": 8}).encode(), b"")
        with patch.object(speed.subprocess, "run", return_value=response):
            result = speed.transfer("download", 2_000_000)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["mbps"])

    def test_relative_drop_needs_comparable_history(self):
        old = {"method": speed.METHOD, "route": route(), "download": successful("download", speed.DOWNLOAD_BYTES),
               "upload": successful("upload", speed.UPLOAD_BYTES)}
        current = json.loads(json.dumps(old))
        current["download"]["mbps"] = 10
        self.assertEqual(speed.compare_reference(current, [old] * 3)[0], "below_recent_baseline")
        self.assertEqual(speed.compare_reference(current, [old] * 2)[0], "measured")
        changed = json.loads(json.dumps(current))
        changed["route"]["gateway"] = "192.168.2.1"
        self.assertEqual(speed.compare_reference(changed, [old] * 3)[1], {})

    def test_cadence_prevents_extra_transfers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "speed-latest.json").write_text(json.dumps({"epoch": 1000, "method": speed.METHOD}))
            with patch.object(speed.time, "time", return_value=1010), patch.object(speed, "transfer") as transfer:
                self.assertEqual(speed.run_once(root)["skipped"], "minimum_interval")
                transfer.assert_not_called()

    def test_budget_is_reserved_before_transfer_and_blocks_excess(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(speed, "route_info", return_value=route()), patch.object(speed, "transfer", side_effect=successful):
                row = speed.run_once(root, force=True)
            budget = json.loads((root / "speed-budget.json").read_text())
            self.assertEqual(budget["reserved_bytes"], speed.DOWNLOAD_BYTES + speed.UPLOAD_BYTES)
            budget["reserved_bytes"] = speed.DAILY_BUDGET
            (root / "speed-budget.json").write_text(json.dumps(budget))
            with patch.object(speed, "route_info", return_value=route()), patch.object(speed, "transfer") as transfer:
                self.assertEqual(speed.run_once(root, force=True)["condition"], "skipped_daily_budget")
                transfer.assert_not_called()

    def test_speed_job_does_not_wait_for_connectivity_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with monitor.lock(root), patch.object(speed, "route_info", return_value=route()), patch.object(speed, "transfer", side_effect=successful):
                self.assertEqual(speed.run_once(root)["condition"], "measured")

    def test_report_includes_speed_without_breaking_connectivity_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(speed, "route_info", return_value=route()), patch.object(speed, "transfer", side_effect=successful):
                speed.run_once(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                monitor.report(root, 24)
            report = json.loads(output.getvalue())
            self.assertEqual(report["samples"], 0)
            self.assertEqual(report["throughput"]["samples"], 1)
            self.assertEqual(report["throughput"]["upload_mbps"]["median"], 80)

    def test_load_overlap_does_not_persist_after_a_crashed_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "speed-active.json").write_text(json.dumps({"started_epoch": 1000, "ended_epoch": None}))
            self.assertTrue(monitor.speed_test_overlap(root, 1002, 1003))
            self.assertFalse(monitor.speed_test_overlap(root, 1040, 1041))

    def test_background_network_throttling_is_not_reported_as_line_speed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(speed, "route_info", return_value=route()), patch.object(speed, "execution_context", return_value={"darwin_background": True}), patch.object(speed, "transfer") as transfer:
                row = speed.run_once(root)
            self.assertEqual(row["condition"], "invalid_background_execution")
            transfer.assert_not_called()

    def test_measurement_methods_are_not_mixed_in_baseline(self):
        old = {"method": "old_background_method", "route": route(),
               "download": successful("download", speed.DOWNLOAD_BYTES),
               "upload": successful("upload", speed.UPLOAD_BYTES)}
        row = {**old, "method": speed.METHOD}
        self.assertEqual(speed.compare_reference(row, [old] * 5)[1], {})


if __name__ == "__main__":
    unittest.main()
