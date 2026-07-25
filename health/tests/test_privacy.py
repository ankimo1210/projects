import os
import stat

from health.privacy import ensure_private_dir


def test_creates_and_narrows_a_new_directory(tmp_path):
    target = tmp_path / "brand-new"

    ensure_private_dir(target)

    assert target.is_dir()
    assert stat.S_IMODE(target.stat().st_mode) == 0o700


def test_creates_missing_parents_too(tmp_path):
    target = tmp_path / "a" / "b" / "c"

    ensure_private_dir(target)

    assert target.is_dir()
    assert stat.S_IMODE(target.stat().st_mode) == 0o700


def test_does_not_reperm_a_preexisting_directory(tmp_path):
    """A directory this call did not create -- /tmp for a demo database, a
    user's home directory, a pre-existing export target -- must be left
    exactly as it was found. Re-permissioning it would be a side effect well
    beyond protecting health data, and would fail outright on a directory
    like /tmp where chmod is not permitted."""
    target = tmp_path / "already-here"
    target.mkdir(mode=0o755)
    os.chmod(target, 0o755)  # mkdir's mode is filtered by umask; force it

    ensure_private_dir(target)

    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_chmod_failure_on_a_freshly_created_directory_is_swallowed(tmp_path, monkeypatch):
    """Narrowing a brand-new directory is best-effort: a sticky or
    otherwise-unchmoddable location (the real-world trigger for this fix)
    must not turn directory creation itself into a crash."""

    def raise_eperm(_path, _mode):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "chmod", raise_eperm)
    target = tmp_path / "sticky"

    ensure_private_dir(target)  # must not raise

    assert target.is_dir()
