from __future__ import annotations

import json
import sys
import tempfile
import unittest
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_email import build_outputs, load_report  # noqa: E402
from check_email import inspect_email  # noqa: E402
from send_email import send_via_smtp  # noqa: E402


class InteractiveEmailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = load_report(PROJECT_ROOT / "sample-report.json")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def build(self) -> dict[str, Path]:
        return build_outputs(
            self.report,
            self.output_dir,
            "reports@example.com",
            "reader@example.net",
        )

    def test_builds_all_outputs(self) -> None:
        outputs = self.build()
        self.assertEqual({"eml", "amp", "html", "text", "browser"}, outputs.keys())
        self.assertTrue(all(path.is_file() for path in outputs.values()))

    def test_mime_order_and_amp_checks(self) -> None:
        eml = self.build()["eml"]
        self.assertEqual([], inspect_email(eml))
        message = BytesParser(policy=policy.default).parsebytes(eml.read_bytes())
        self.assertEqual(
            ["text/plain", "text/x-amp-html", "text/html"],
            [part.get_content_type() for part in message.iter_parts()],
        )

    def test_every_metric_is_interactive(self) -> None:
        amp = self.build()["amp"].read_text(encoding="utf-8")
        for metric in self.report["metrics"]:
            self.assertIn(f"metric: '{metric['id']}'", amp)
            self.assertIn(f"metric != '{metric['id']}'", amp)

    def test_browser_preview_contains_same_data(self) -> None:
        browser = self.build()["browser"].read_text(encoding="utf-8")
        for metric in self.report["metrics"]:
            self.assertIn(json.dumps(metric["id"]), browser)
            self.assertIn(metric["headline"], browser)

    def test_rejects_same_sender_and_recipient(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be different"):
            build_outputs(
                self.report,
                self.output_dir,
                "same@example.com",
                "same@example.com",
            )

    def test_rejects_non_https_dashboard(self) -> None:
        bad_data = dict(self.report, dashboard_url="http://example.com/report")
        path = self.output_dir / "bad.json"
        path.write_text(json.dumps(bad_data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            load_report(path)

    @patch("send_email.smtplib.SMTP")
    def test_smtp_sender_uses_starttls(self, smtp_class: MagicMock) -> None:
        smtp = smtp_class.return_value.__enter__.return_value
        message = EmailMessage()
        message.set_content("test")

        send_via_smtp(
            message,
            host="smtp.example.com",
            port=587,
            username="reporter@example.com",
            password="secret",
            from_address="reporter@example.com",
            to_address="reader@example.net",
            use_ssl=False,
        )

        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
        self.assertEqual(2, smtp.ehlo.call_count)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("reporter@example.com", "secret")
        smtp.send_message.assert_called_once_with(
            message,
            from_addr="reporter@example.com",
            to_addrs=["reader@example.net"],
        )

    @patch("send_email.smtplib.SMTP_SSL")
    def test_smtp_sender_supports_implicit_tls(self, smtp_class: MagicMock) -> None:
        smtp = smtp_class.return_value.__enter__.return_value
        message = EmailMessage()
        message.set_content("test")

        send_via_smtp(
            message,
            host="smtp.example.com",
            port=465,
            username=None,
            password=None,
            from_address="reporter@example.com",
            to_address="reader@example.net",
            use_ssl=True,
        )

        self.assertIn("context", smtp_class.call_args.kwargs)
        smtp.starttls.assert_not_called()
        smtp.login.assert_not_called()
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
