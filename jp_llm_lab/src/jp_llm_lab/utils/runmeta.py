"""Run metadata for reproducibility (spec §3.2).

Every training run saves: git state, package versions, environment report,
timestamps. Note: this session leaves work uncommitted, so `git_dirty=True`
is expected and recorded honestly rather than hidden.
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from datetime import UTC, datetime

from .env import collect_env_report
from .io import repo_root

_TRACKED_PACKAGES = ["torch", "numpy", "matplotlib", "plotly", "jinja2", "pyyaml", "pandas"]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo_root(), capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except OSError:
        return None


def collect_run_metadata(extra: dict | None = None) -> dict:
    status = _git("status", "--porcelain")
    meta = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("branch", "--show-current"),
        "git_dirty": bool(status) if status is not None else None,
        "python": sys.version.split()[0],
        "argv": sys.argv,
        "packages": {},
        "env": collect_env_report().__dict__,
    }
    for pkg in _TRACKED_PACKAGES:
        try:
            meta["packages"][pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            meta["packages"][pkg] = None
    if extra:
        meta.update(extra)
    return meta
