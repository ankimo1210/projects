"""Make ``stats_textbook`` importable before the project is pip-installed.

The package lives under ``src/``. Prepending it to ``sys.path`` keeps the
tests (and notebooks launched from this directory) working in a bare
checkout. Harmless once the project is installed into the workspace venv.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
