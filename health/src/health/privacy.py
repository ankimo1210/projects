"""Filesystem privacy helpers for the app's own data directories."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


def ensure_private_dir(path: Path) -> None:
    """Create `path` if needed and narrow it to owner-only.

    The chmod applies only to a directory this call created. Callers can be
    pointed at a location the app does not own -- `/tmp` for a demo database,
    a user-chosen export directory -- where re-permissioning someone else's
    directory would be a side effect well beyond protecting health data, and
    where the chmod fails outright on a sticky directory like /tmp. Narrowing
    is therefore best-effort on creation, while the files themselves are
    always written 0600 by their own writers.
    """
    created = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if created:
        with contextlib.suppress(OSError):
            os.chmod(path, 0o700)
