"""Project paths. Everything caches under the repo ``data/`` tree by default.

Override the data root with the ``QUANTKIT_DATA_DIR`` environment variable (useful for
tests, which point it at a tmp dir).
"""

from __future__ import annotations

import os
from pathlib import Path

# .../investment-research-platform/src/quantkit/utils/paths.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "configs"


def data_root() -> Path:
    env = os.environ.get("QUANTKIT_DATA_DIR")
    return Path(env) if env else REPO_ROOT / "data"


# Sub-stores (see README): raw downloads, normalized/latest-vintage, point-in-time.
def raw_dir() -> Path:
    return data_root() / "raw"


def interim_dir() -> Path:
    return data_root() / "interim"


def processed_dir() -> Path:
    return data_root() / "processed"


def point_in_time_dir() -> Path:
    return data_root() / "point_in_time"


def external_dir() -> Path:
    return data_root() / "external"


def ensure_dirs() -> None:
    for d in (raw_dir(), interim_dir(), processed_dir(), point_in_time_dir(), external_dir()):
        d.mkdir(parents=True, exist_ok=True)
