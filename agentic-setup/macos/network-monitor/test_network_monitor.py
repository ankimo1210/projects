import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import network_monitor as monitor


def healthy():
    return {"at": "2026-11-15T08:00:00+09:00", "epoch": 1000, "boot": "boot1",
            "route": {"ok": True, "interface": "en0", "gateway": "192.168.1.1"},
            "wifi": {"channel": 100, "width_mhz": 160},
            "ping": {name: {"ok": True, "sent": 2, "received": 2}
                     for name in ["gateway", "cloudflare", "google"]},
            "https": {name: {"ok": True, "code": 0, "status": 200, "total_ms": 20}
                      for name in ["apple", "anthropic", "openai", "ip"]}}


class ClassificationTests(unittest.TestCase):
    def test_icmp_loss_does_not_mean_internet_outage(self):
        sample = healthy()
        sample["ping"]["gateway"] = {"ok": False, "sent": 2, "received": 0}
        self.assertEqual(monitor.classify(sample), "probe_loss_only")

    def test_unauthenticated_http_response_proves_transport(self):
        sample = healthy()
        sample["https"]["anthropic"]["status"] = 404
        sample["https"]["openai"]["status"] = 401
        self.assertEqual(monitor.classify(sample), "healthy")

    def test_dns_failure_with_working_ip_https(self):
        sample = healthy()
        for name in ["apple", "anthropic"]:
            sample["https"][name] = {"ok": False, "code": 6}
        self.assertEqual(monitor.classify(sample), "dns_issue_suspected")

    def test_multiple_https_failures_with_healthy_lan(self):
        sample = healthy()
        for name in ["apple", "ip"]:
            sample["https"][name] = {"ok": False, "code": 28}
        self.assertEqual(monitor.classify(sample), "upstream_issue_suspected")

    def test_single_destination_failure_is_distinct(self):
        sample = healthy()
        sample["https"]["anthropic"] = {"ok": False, "code": 28}
        self.assertEqual(monitor.classify(sample), "single_destination_issue")

    def test_ipv4_only_issue_does_not_mark_total_outage(self):
        sample = healthy()
        sample["ipv6_https"] = {"ok": True}
        for name in ["apple", "ip"]:
            sample["https"][name] = {"ok": False, "code": 28}
        self.assertEqual(monitor.classify(sample), "ipv4_path_issue_suspected")

    def test_no_default_route(self):
        sample = healthy()
        sample["route"] = {"ok": False}
        self.assertEqual(monitor.classify(sample), "no_default_route")


class RecordingTests(unittest.TestCase):
    def test_prior_https_failure_is_rechecked_even_when_ping_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = healthy()
            previous.update(condition="single_destination_issue", last_full_epoch=1000)
            (root / "latest.json").write_text(json.dumps(previous))
            with (patch.object(monitor.time, "time", return_value=1015),
                  patch.object(monitor, "command", return_value={"text": "boot1"}),
                  patch.object(monitor, "route_info", return_value=previous["route"]),
                  patch.object(monitor, "ping", return_value={"ok": True, "sent": 2, "received": 2}),
                  patch.object(monitor, "wifi_info", return_value=previous["wifi"]),
                  patch.object(monitor, "network_details", return_value={"dns_servers": [], "ipv6_available": False}),
                  patch.object(monitor, "dns", return_value={"ok": True}),
                  patch.object(monitor, "https", return_value={"ok": True, "status": 200}) as web):
                sample = monitor.sample_once(root)
            self.assertTrue(sample["full"])
            self.assertEqual(web.call_count, 4)
            self.assertEqual(sample["condition"], "healthy")

    def test_sleep_gap_and_channel_change_are_separate_from_outage(self):
        previous = healthy()
        previous["condition"] = "healthy"
        sample = copy.deepcopy(previous)
        sample["epoch"] += 600
        sample["wifi"]["channel"] = 36
        events = monitor.transition_events(previous, sample)
        self.assertEqual({e["kind"] for e in events}, {"observation_gap", "wifi_channel_changed"})

    def test_reboot_gap_is_identified(self):
        previous = healthy()
        previous["condition"] = "healthy"
        sample = copy.deepcopy(previous)
        sample["boot"] = "boot2"
        events = monitor.transition_events(previous, sample)
        self.assertTrue(any(e.get("reason") == "boot_changed" for e in events))

    def test_compressed_append_preserves_all_prior_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples.jsonl.gz"
            monitor.append_log(path, {"n": 1})
            first_bytes = path.read_bytes()
            monitor.append_log(path, {"n": 2})
            self.assertTrue(path.read_bytes().startswith(first_bytes))
            with gzip.open(path, "rt") as handle:
                self.assertEqual([json.loads(line) for line in handle], [{"n": 1}, {"n": 2}])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_state_stops_before_probing_or_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "latest.json"
            state.write_text("invalid json")
            with patch.object(monitor, "route_info") as route:
                with self.assertRaises(json.JSONDecodeError):
                    monitor.sample_once(root)
                route.assert_not_called()
            self.assertEqual(state.read_text(), "invalid json")

    def test_overlapping_job_does_not_probe_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with monitor.lock(root):
                with patch.object(monitor, "route_info") as route:
                    self.assertIn("skipped", monitor.sample_once(root))
                    route.assert_not_called()
            self.assertFalse((root / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
