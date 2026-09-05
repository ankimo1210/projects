"""Run the unchanged supplied data and promote the self-contained report."""
from pathlib import Path
import shutil

from quantcurve.workflow import run_workflow

root = Path(__file__).resolve().parents[1]
result = run_workflow(root / "data" / "market_observations.csv", root / "outputs", "2026-01-15")
shutil.copy2(root / "outputs" / "reports" / "research_report.html", root / "reports" / "research_report.html")
print(result)
