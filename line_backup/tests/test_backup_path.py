import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestCandidateDirs(unittest.TestCase):
    """Test that backup candidate paths are built correctly from env vars."""

    def _get_candidates(self, env_overrides: dict) -> list[Path]:
        with patch.dict(os.environ, env_overrides, clear=False):
            with patch("platform.system", return_value="Windows"):
                from importlib import reload

                import line_backup_exporter.backup_locator as mod

                reload(mod)
                return mod._candidate_dirs()

    def test_appdata_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates = self._get_candidates({"APPDATA": tmp})
            paths_str = [str(p) for p in candidates]
            self.assertTrue(any("Apple Computer" in p and "MobileSync" in p for p in paths_str))

    def test_userprofile_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates = self._get_candidates({"USERPROFILE": tmp})
            paths_str = [str(p) for p in candidates]
            self.assertTrue(any("Apple" in p and "MobileSync" in p for p in paths_str))

    def test_glob_wildcard_resolved(self):
        """AppleInc.iTunes_* glob is resolved via actual directory."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create a fake UWP package directory
            fake_pkg = (
                Path(tmp)
                / "Packages"
                / "AppleInc.iTunes_abc123"
                / "LocalCache"
                / "Roaming"
                / "Apple Computer"
                / "MobileSync"
                / "Backup"
            )
            fake_pkg.mkdir(parents=True)

            candidates = self._get_candidates({"LOCALAPPDATA": tmp})
            resolved = [p.resolve() for p in candidates if p.exists()]
            self.assertIn(fake_pkg.resolve(), resolved)


if __name__ == "__main__":
    unittest.main()
