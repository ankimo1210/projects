"""Where the project keeps its inputs and its outputs.

Its own module so that `finance` and `datasets` can both use it without one
importing the other — they are peers, and a cycle between them was the first
thing that broke when the financial series were added.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = _ROOT / "_data"
RESULTS_DIR = _ROOT / "reports"
