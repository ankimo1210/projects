"""Run from source and promote the current report; no prior output is required."""
from pathlib import Path
import shutil
from quantcurve.workflow import run_workflow

root=Path(__file__).resolve().parents[1]
result=run_workflow(root/'data/market_observations.csv',root/'outputs','2026-01-15')
(root/'reports').mkdir(exist_ok=True)
shutil.copyfile(root/'outputs/reports/research_report.html',root/'reports/research_report.html')
print(result)
