"""Check likely API credentials without echoing their values."""

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().parents[1] / "check_api_secrets.py"


class SecretGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        spec = importlib.util.spec_from_file_location("check_api_secrets", GUARD_PATH)
        self.guard = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.guard
        spec.loader.exec_module(self.guard)

    def check(self, name, text):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = self.guard.main([str(path)])
        return code, output.getvalue()

    def test_known_provider_keys_are_blocked_without_echoing_the_value(self):
        for prefix in ("sk-proj-", "sk-ant-api03-"):
            with self.subTest(provider=prefix):
                value = prefix + "a" * 40
                code, output = self.check("source.py", 'KEY = "' + value + '"\n')
                self.assertEqual(code, 1)
                self.assertNotIn(value, output)

    def test_reinfolib_literal_is_blocked_inside_a_notebook(self):
        import json

        value = "0123456789abcdef" * 2
        source = 'REINFOLIB_API_KEY = "' + value + '"\n'
        code, output = self.check("book.ipynb", json.dumps({"source": [source]}))
        self.assertEqual(code, 1)
        self.assertNotIn(value, output)

    def test_real_env_files_are_blocked_even_in_outputs(self):
        for name in ("outputs/.env", "outputs/.env.production", "outputs/openai.env"):
            with self.subTest(name=name):
                code, _ = self.check(name, "OPENAI_API_KEY=\n")
                self.assertEqual(code, 1)

    def test_empty_example_and_environment_lookup_are_allowed(self):
        self.assertEqual(self.check(".env.example", "OPENAI_API_KEY=\n")[0], 0)
        code, _ = self.check(
            "source.py", 'REINFOLIB_API_KEY = os.environ.get("REINFOLIB_API_KEY", "")\n'
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
