import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from line_backup_exporter.safety import (
    ensure_within_directory,
    redact_text,
    safe_filename,
    unique_path,
)


class TestEnsureWithinDirectory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = Path(self.tmp)

    def test_valid_child(self):
        child = self.base / "sub" / "file.txt"
        child.parent.mkdir(parents=True)
        child.touch()
        result = ensure_within_directory(self.base, child)
        self.assertEqual(result, child.resolve())

    def test_traversal_raises(self):
        evil = self.base / ".." / "etc" / "passwd"
        with self.assertRaises(ValueError):
            ensure_within_directory(self.base, evil)

    def test_same_dir_ok(self):
        result = ensure_within_directory(self.base, self.base)
        self.assertEqual(result, self.base.resolve())


class TestSafeFilename(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(safe_filename("hello_world.sqlite"), "hello_world.sqlite")

    def test_special_chars(self):
        result = safe_filename("foo/bar:baz")
        self.assertNotIn("/", result)
        self.assertNotIn(":", result)

    def test_empty(self):
        self.assertEqual(safe_filename(""), "unnamed")

    def test_reserved_name(self):
        result = safe_filename("CON.sqlite")
        self.assertTrue(result.startswith("_"))

    def test_leading_dot(self):
        result = safe_filename(".hidden")
        self.assertFalse(result.startswith("."))

    def test_long_name(self):
        long_name = "a" * 300
        self.assertLessEqual(len(safe_filename(long_name)), 200)


class TestRedactText(unittest.TestCase):
    def test_short_passthrough(self):
        self.assertEqual(redact_text("hello"), "hello")

    def test_long_truncated(self):
        long = "x" * 100
        result = redact_text(long, max_len=80)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 83)

    def test_none(self):
        self.assertEqual(redact_text(None), "")

    def test_newlines_collapsed(self):
        result = redact_text("a\nb\rc")
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)


class TestUniquePath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_no_conflict(self):
        p = Path(self.tmp) / "file.txt"
        self.assertEqual(unique_path(p), p)

    def test_conflict_adds_suffix(self):
        p = Path(self.tmp) / "file.txt"
        p.touch()
        result = unique_path(p)
        self.assertNotEqual(result, p)
        self.assertIn("(1)", result.name)

    def test_multiple_conflicts(self):
        p = Path(self.tmp) / "file.txt"
        p.touch()
        p1 = Path(self.tmp) / "file (1).txt"
        p1.touch()
        result = unique_path(p)
        self.assertIn("(2)", result.name)


if __name__ == "__main__":
    unittest.main()
