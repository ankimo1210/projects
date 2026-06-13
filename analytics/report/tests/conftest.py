"""Make ``report_builder`` importable when pytest collects this tree.

The report package is not a uv workspace member (it only orchestrates the three
book packages), so we add its directory to sys.path here.
"""

import sys
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1]
if str(REPORT_DIR) not in sys.path:
    sys.path.insert(0, str(REPORT_DIR))
