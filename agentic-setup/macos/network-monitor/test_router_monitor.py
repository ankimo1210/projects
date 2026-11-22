import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import router_monitor as monitor


def config():
    return {"schema": 1, "host": "192.168.11.1", "model": "WXR-5950AX12",
            "gateway_mac_sha256": "0" * 64, "public_key_sha256": "1" * 64,
            "privacy_key": "2" * 64}


class SafetyTests(unittest.TestCase):
    def test_unavailable_arp_requires_key_check_without_session_cookies(self):
        router = monitor.Router(config())
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'var modulus="' + b"a" * 512 + b'";'
        with (patch.object(monitor, "route_info", return_value={"ok": True, "gateway": config()["host"]}),
              patch.object(monitor, "gateway_mac_hash", side_effect=monitor.MonitorError("gateway_identity_unavailable")),
              patch.object(router.anonymous, "open", return_value=response),
              patch.object(router.opener, "open") as authenticated_request):
            with self.assertRaisesRegex(monitor.MonitorError, "router_key_changed"):
                router.guard()
            authenticated_request.assert_not_called()

    def test_setting_and_reboot_endpoints_are_refused_before_io(self):
        router = monitor.Router(config())
        with patch.object(router.opener, "open") as request:
            for path in ["/cgi-bin/cgi?req=set", "/cgi-bin/cgi?req=inp&res=reboot.html",
                         "/cgi-bin/cgi?req=fnc&fnc=%24{set_param(QOS)}"]:
                with self.assertRaises(monitor.MonitorError):
                    router.request(path, {})
            request.assert_not_called()

    def test_wrong_gateway_never_reads_credentials_or_contacts_router(self):
        router = monitor.Router(config())
        with (patch.object(monitor, "route_info", return_value={"ok": True, "gateway": "192.168.1.1"}),
              patch.object(router, "request") as request,
              patch.object(monitor.subprocess, "run") as command):
            with self.assertRaisesRegex(monitor.MonitorError, "different_network"):
                router.collect()
            request.assert_not_called()
            command.assert_not_called()

    def test_changed_router_identity_is_rejected(self):
        router = monitor.Router(config())
        with (patch.object(monitor, "route_info", return_value={"ok": True, "gateway": config()["host"]}),
              patch.object(monitor, "gateway_mac_hash", return_value="f" * 64),
              patch.object(router, "request") as request):
            with self.assertRaisesRegex(monitor.MonitorError, "different_router"):
                router.collect()
            request.assert_not_called()

    def test_changed_public_key_is_rejected_before_keychain_access(self):
        router = monitor.Router(config())
        with (patch.object(router, "guard"),
              patch.object(router, "json", return_value={"MODEL": "WXR-5950AX12"}),
              patch.object(router, "request", return_value='var modulus="' + "a" * 512 + '"; var exponent="65537";'),
              patch.object(monitor.subprocess, "run") as command):
            with self.assertRaisesRegex(monitor.MonitorError, "router_key_changed"):
                router.login()
            command.assert_not_called()

    def test_logs_remove_identifiers_and_credential_fields(self):
        router = monitor.Router(config())
        raw = "user aa:bb:cc:dd:ee:ff 43.235.1.2 192.168.11.20 Buffalo-A-TEST token=private password=secret"
        result = router.sanitize(raw)
        for text in ["aa:bb", "43.235", "192.168", "Buffalo-A", "private", "secret"]:
            self.assertNotIn(text, result)
        self.assertIn(router.device_id("aa:bb:cc:dd:ee:ff"), result)

    def test_failed_probe_never_records_raw_exception_or_auth_data(self):
        with tempfile.TemporaryDirectory() as directory:
            router = monitor.Router(config())
            with patch.object(router, "collect", side_effect=ValueError("password=do-not-record")):
                result = monitor.sample_once(router, Path(directory))
            self.assertEqual(result["error"], "ValueError")
            self.assertNotIn("do-not-record", (Path(directory) / "router-latest.json").read_text())

    def test_credential_backoff_prevents_frequent_logins(self):
        router = monitor.Router(config())
        router.next_login = float("inf")
        with patch.object(router, "guard") as guard:
            with self.assertRaisesRegex(monitor.MonitorError, "authentication_backoff"):
                router.login()
            guard.assert_not_called()


class TelemetryTests(unittest.TestCase):
    def test_repeated_router_log_snapshots_do_not_duplicate_events(self):
        import gzip
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = MagicMock()
            router.collect.return_value = {"router_reported_counters": {}}
            router.logs.return_value = [{"router_time": "2026/11/16 12:00:00", "category": "WIRED",
                                         "message": "test event", "id": "a" * 64}]
            with patch.object(monitor.time, "time", return_value=1794800000):
                first = monitor.sample_once(router, root)
            with patch.object(monitor.time, "time", return_value=1794800301):
                second = monitor.sample_once(router, root)
            self.assertEqual(first["new_log_entries"], 1)
            self.assertEqual(second["new_log_entries"], 0)
            path = next(root.glob("router-events-*.jsonl.gz"))
            with gzip.open(path, "rt") as handle:
                self.assertEqual(len(handle.readlines()), 1)

    def test_live_packet_html_format_and_missing_data(self):
        body = '<table><tr><th><span class="label_label_wan1_packet_main"></span></th><td>12</td><td>0</td><td>34</td><td>0</td></tr>'
        # These untranslated label IDs are from the actual vendor status page.
        for label in ["label_t13_packet_main", "label_t12_packet_main"]:
            body += '<tr><th><span class="' + label + '"></span></th><td>1</td><td>2</td><td>3</td><td>4</td></tr>'
        import html
        page = '<input id="packet_main_data" type="hidden" value="' + html.escape(body, quote=True) + '">'
        values = monitor.packet_counters(page)
        self.assertEqual(values["wan"]["rx_ok"], 34)
        self.assertEqual(values["wifi_5g"]["tx_error"], 2)
        with self.assertRaises(monitor.MonitorError):
            monitor.packet_counters("<html>login</html>")

    def test_reset_is_not_reported_as_negative_packet_loss(self):
        before = {"wan": {"tx_ok": 100, "rx_ok": 100, "tx_error": 1, "rx_error": 0}}
        after = {"wan": {"tx_ok": 3, "rx_ok": 4, "tx_error": 0, "rx_error": 0}}
        self.assertEqual(monitor.counter_changes(before, after)["wan"], {"reset_or_wrap": True})

    def test_rates_preserve_units_and_unknown_values(self):
        self.assertEqual(monitor.rates("3.9Mbps"), 3.9)
        self.assertEqual(monitor.rates("78.1Kbps"), 0.0781)
        self.assertIsNone(monitor.rates("unavailable"))


if __name__ == "__main__":
    unittest.main()
