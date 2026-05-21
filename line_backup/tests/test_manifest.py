import plistlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from line_backup_exporter.manifest import (
    check_encrypted,
    iter_line_files,
    open_manifest,
    prioritize,
)


def _make_manifest_db(path: Path, rows: list[tuple]) -> None:
    """Create a minimal Manifest.db with given (fileID, domain, relativePath, flags, file) rows."""
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE Files (
            fileID TEXT,
            domain TEXT,
            relativePath TEXT,
            flags INTEGER,
            file INTEGER
        )
    """)
    conn.executemany("INSERT INTO Files VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def _make_plist(path: Path, encrypted: bool) -> None:
    data = {"IsEncrypted": encrypted, "Version": 12}
    with path.open("wb") as f:
        plistlib.dump(data, f)


class TestCheckEncrypted(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_not_encrypted(self):
        _make_plist(self.tmp / "Manifest.plist", False)
        self.assertFalse(check_encrypted(self.tmp))

    def test_encrypted(self):
        _make_plist(self.tmp / "Manifest.plist", True)
        self.assertTrue(check_encrypted(self.tmp))

    def test_no_plist(self):
        self.assertFalse(check_encrypted(self.tmp))


class TestIterLineFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        rows = [
            (
                "aabbcc",
                "AppDomainGroup-jp.naver.line",
                "Library/Application Support/Line.sqlite",
                1,
                0,
            ),
            ("ddeeff", "AppDomain-com.apple.mobilenotes", "Documents/notes.sqlite", 1, 0),
            ("112233", "AppDomain-com.example.other", "Caches/data.db", 1, 0),
        ]
        _make_manifest_db(self.tmp / "Manifest.db", rows)

    def test_only_line_entries(self):
        conn = open_manifest(self.tmp)
        entries = list(iter_line_files(conn))
        conn.close()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].file_id, "aabbcc")

    def test_file_entry_fields(self):
        conn = open_manifest(self.tmp)
        entries = list(iter_line_files(conn))
        conn.close()
        e = entries[0]
        self.assertEqual(e.domain, "AppDomainGroup-jp.naver.line")
        self.assertIn("Line.sqlite", e.relative_path)


class TestPrioritize(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        rows = [
            ("aa", "AppDomainGroup-jp.naver.line", "Library/chat/Talk.sqlite", 1, 0),
            ("bb", "AppDomainGroup-jp.naver.line", "Library/Line.sqlite", 1, 0),
            ("cc", "AppDomainGroup-jp.naver.line", "Library/image/cache", 1, 0),
        ]
        _make_manifest_db(self.tmp / "Manifest.db", rows)

    def test_line_sqlite_is_top(self):
        conn = open_manifest(self.tmp)
        entries = list(iter_line_files(conn))
        conn.close()
        ranked = prioritize(entries)
        # Line.sqlite or Talk.sqlite should be ranked highly
        top_paths = [e.relative_path for e in ranked[:2]]
        self.assertTrue(any("Line.sqlite" in p or "Talk.sqlite" in p for p in top_paths))


if __name__ == "__main__":
    unittest.main()
