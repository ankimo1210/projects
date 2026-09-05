from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from synthetic import synthetic_frame  # noqa: E402


@pytest.fixture(scope="session")
def clean_frame():
    return synthetic_frame(noise_bp=0.0)


@pytest.fixture(scope="session")
def noisy_frame():
    return synthetic_frame(noise_bp=0.3, seed=7)
