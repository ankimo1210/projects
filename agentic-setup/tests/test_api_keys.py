"""Offline behavior checks for the private API-key launcher."""

import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "api_keys.py"
FAKE_OPENAI = "unit-test-openai-value"
FAKE_ANTHROPIC = "unit-test-anthropic-value"


class ApiKeysTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "Drive folder" / "secrets"
        self.cache = self.base / "local cache"
        self.config_path = self.base / "config.json"

    def helper(self):
        if not APP.is_file():
            self.fail("The API-key helper is not implemented yet")
        spec = importlib.util.spec_from_file_location("repo_api_keys_under_test", APP)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def configured(self):
        helper = self.helper()
        self.source.mkdir(parents=True)
        config = helper.Config(self.source, self.cache)
        helper.write_config(config, self.config_path)
        return helper, config

    def cli(self, *arguments, env=None):
        return subprocess.run(
            [sys.executable, str(APP), "--config", str(self.config_path), *arguments],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_save_writes_drive_and_cache_without_printing_the_value(self):
        helper, config = self.configured()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            helper.save_keys(config, {"openai": FAKE_OPENAI})
        expected = "OPENAI_API_KEY=unit-test-openai-value\n"
        self.assertEqual((self.source / "openai.env").read_text(), expected)
        self.assertEqual((self.cache / "openai.env").read_text(), expected)
        self.assertNotIn(FAKE_OPENAI, output.getvalue())

    def test_blank_form_field_preserves_an_existing_key(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        helper.save_keys(config, {"openai": "", "anthropic": "   "})
        self.assertEqual(
            (self.cache / "openai.env").read_text(), "OPENAI_API_KEY=unit-test-openai-value\n"
        )

    def test_multiline_input_is_rejected_before_any_key_is_written(self):
        helper, config = self.configured()
        with self.assertRaises(helper.SecretError) as caught:
            helper.save_keys(config, {"openai": FAKE_OPENAI, "anthropic": "bad\nvalue"})
        self.assertNotIn("bad", str(caught.exception))
        self.assertFalse((self.source / "openai.env").exists())

    def test_unknown_provider_is_rejected(self):
        helper, config = self.configured()
        with self.assertRaises(helper.SecretError):
            helper.save_keys(config, {"PATH": "unit-test-path-value"})
        self.assertEqual(list(self.source.iterdir()), [])

    def test_retired_key_cannot_be_saved_as_an_active_key(self):
        helper, config = self.configured()
        retired = "0123456789abcdef0123456789abcdef"
        helper.retire_key(config, "reinfolib", retired)
        with self.assertRaises(helper.SecretError):
            helper.save_keys(config, {"reinfolib": retired})
        self.assertTrue((self.source / "retired" / "reinfolib.env").is_file())
        active = self.source / "reinfolib.env"
        self.assertFalse(active.exists() and retired in active.read_text())
        helper.save_keys(config, {"reinfolib": "new-unit-test-reinfolib-value"})
        self.assertTrue(helper.status(config)["providers"]["reinfolib"]["configured"])

    def test_stale_second_device_cannot_register_a_key_retired_on_drive(self):
        helper, first = self.configured()
        second = helper.Config(self.source, self.base / "second cache")
        helper.sync(second)
        retired = "unit-test-retired-reinfolib"
        helper.retire_key(first, "reinfolib", retired)
        with self.assertRaises(helper.SecretError):
            helper.save_keys(second, {"reinfolib": retired})

    def test_second_device_retirement_preserves_existing_drive_records(self):
        helper, first = self.configured()
        second = helper.Config(self.source, self.base / "second cache")
        helper.retire_key(first, "reinfolib", "unit-test-retired-reinfolib")
        helper.retire_key(second, "openai", "unit-test-retired-openai")
        names = set(json.loads((self.source / ".retired.json").read_text()))
        self.assertEqual(names, {"openai", "reinfolib"})

    def test_sync_does_not_forget_locally_known_retired_keys(self):
        helper, config = self.configured()
        helper.retire_key(config, "reinfolib", "unit-test-retired-reinfolib")
        (self.source / ".retired.json").write_text("{}")
        helper.sync(config)
        names = set(json.loads((self.cache / ".retired.json").read_text()))
        self.assertEqual(names, {"reinfolib"})

    def test_missing_key_on_connected_drive_does_not_launch_the_child(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        (self.source / "openai.env").unlink()
        marker = self.base / "must-not-launch"
        result = self.cli(
            "run",
            "--provider",
            "openai",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path;Path(" + repr(str(marker)) + ").touch()",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertEqual(helper.status(config)["providers"]["openai"]["issue"], "missing_in_drive")

    def test_known_missing_drive_key_is_not_restored_by_going_offline(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        (self.source / "openai.env").unlink()
        helper.sync(config)
        (self.base / "Drive folder").rename(self.base / "Drive unavailable")
        with self.assertRaises(helper.SecretError):
            helper.read_key(config, "openai")

    def test_offline_drive_keeps_a_verified_local_copy(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        (self.base / "Drive folder").rename(self.base / "Drive unavailable")
        helper.sync(config)
        self.assertEqual(helper.read_key(config, "openai"), FAKE_OPENAI)

    def test_unknown_env_variable_cannot_replace_good_cache(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        (self.source / "openai.env").write_text(
            "OPENAI_API_KEY=another-unit-test-value\nPYTHONPATH=/untrusted\n"
        )
        with self.assertRaises(helper.SecretError):
            helper.sync(config)
        self.assertEqual(
            (self.cache / "openai.env").read_text(), "OPENAI_API_KEY=unit-test-openai-value\n"
        )

    def test_run_passes_selected_key_only_to_real_child_process(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI, "anthropic": FAKE_ANTHROPIC})
        child = (
            "import json,os;print(json.dumps({"
            "'selected':bool(os.environ.get('OPENAI_API_KEY')),"
            "'other':bool(os.environ.get('ANTHROPIC_API_KEY'))}))"
        )
        parent = dict(os.environ, ANTHROPIC_API_KEY=FAKE_ANTHROPIC)
        result = self.cli(
            "run", "--provider", "openai", "--", sys.executable, "-c", child, env=parent
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"selected": True, "other": False})
        self.assertNotIn(FAKE_OPENAI, result.stdout + result.stderr)

    def test_missing_key_does_not_launch_the_child(self):
        self.configured()
        marker = self.base / "should-not-exist"
        result = self.cli(
            "run",
            "--provider",
            "openai",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path;Path(" + repr(str(marker)) + ").touch()",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())

    def test_set_refuses_input_when_the_terminal_cannot_hide_it(self):
        helper, _config = self.configured()
        with patch.object(helper.getpass, "getpass", side_effect=helper.getpass.GetPassWarning):
            with contextlib.redirect_stderr(io.StringIO()):
                code = helper.main(
                    ["--config", str(self.config_path), "set", "--provider", "openai"]
                )
        self.assertEqual(code, 2)
        self.assertFalse((self.source / "openai.env").exists())

    def test_status_contains_readiness_but_no_secret(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        result = self.cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["providers"]["openai"]["configured"])
        self.assertFalse(status["providers"]["anthropic"]["configured"])
        self.assertNotIn(FAKE_OPENAI, result.stdout + result.stderr)
        self.assertNotIn(FAKE_OPENAI, self.config_path.read_text())

    def test_cache_only_configuration_works_without_drive_path(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        offline = helper.Config(None, self.cache)
        helper.write_config(offline, self.config_path)
        result = self.cli(
            "run",
            "--provider",
            "openai",
            "--",
            sys.executable,
            "-c",
            "import os;print(bool(os.environ.get('OPENAI_API_KEY')))",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")

    @unittest.skipIf(os.name == "nt", "POSIX mode check")
    def test_posix_secret_files_are_owner_only(self):
        helper, config = self.configured()
        helper.save_keys(config, {"openai": FAKE_OPENAI})
        self.assertEqual(stat.S_IMODE((self.cache / "openai.env").stat().st_mode), 0o600)

    def test_secret_destinations_inside_public_repository_are_rejected(self):
        helper = self.helper()
        repository = APP.parents[1]
        config = helper.Config(repository / ".test-private-secrets", self.cache)
        with self.assertRaises(helper.SecretError):
            helper.save_keys(config, {"openai": FAKE_OPENAI})
        self.assertFalse((repository / ".test-private-secrets").exists())

    def test_installed_copy_preserves_the_public_repository_storage_guard(self):
        helper = self.helper()
        public = self.base / "fake-public-checkout"
        source = public / "secrets"
        source.mkdir(parents=True)
        self.config_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_dir": str(source),
                    "cache_dir": str(self.cache),
                    "public_root": str(public),
                }
            )
        )
        # Installed tools have no checkout ancestor. /tmp is itself a Git repo
        # on this host, so control that unrelated discovery boundary explicitly.
        with patch.object(helper, "_repository_root", return_value=None):
            with self.assertRaises(helper.SecretError):
                config = helper.read_config(self.config_path)
                helper.save_keys(config, {"openai": FAKE_OPENAI})
        self.assertFalse((source / "openai.env").exists())

    def test_known_public_root_wins_over_an_unrelated_installed_tools_ancestor(self):
        helper, config = self.configured()
        config = helper.Config(
            config.source_dir, config.cache_dir, self.base / "designated-public-repository"
        )
        with patch.object(helper, "_repository_root", return_value=self.base):
            helper.save_keys(config, {"openai": FAKE_OPENAI})
        self.assertEqual(
            (self.cache / "openai.env").read_text(), "OPENAI_API_KEY=unit-test-openai-value\n"
        )


if __name__ == "__main__":
    unittest.main()
