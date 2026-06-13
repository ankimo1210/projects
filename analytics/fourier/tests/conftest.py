"""Make ``fourier_book`` importable when this project is not (yet) installed.

The package lives under ``src/``. Until the project is added to the uv workspace
and installed, prepend ``src/`` to ``sys.path`` so the tests (and notebooks run
from here) can ``import fourier_book`` directly. Harmless once installed.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
