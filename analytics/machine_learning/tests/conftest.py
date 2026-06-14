"""Make ``ml_textbook`` importable when this project is not (yet) installed.

The package lives under ``src/``. Until the project is added to the uv workspace
and installed, prepend ``src/`` to ``sys.path`` so the tests (and notebooks run
from here) can ``import ml_textbook`` directly. Harmless once installed.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
# src/ for ``import ml_textbook``; project root for ``import serve`` (the app
# layer, which is not part of the installable package).
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
