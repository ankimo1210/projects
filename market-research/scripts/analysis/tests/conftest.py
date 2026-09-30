"""Run the stand-alone research scripts from the workspace pytest command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
