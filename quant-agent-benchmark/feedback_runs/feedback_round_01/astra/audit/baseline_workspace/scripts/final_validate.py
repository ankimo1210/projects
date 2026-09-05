"""Compare clean installed-package and source CLI runs, then promote outputs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
work = Path(tempfile.mkdtemp(prefix="final-validation-", dir=root / "tmp"))
results = []
for name, isolated in (("installed", True), ("source", False)):
    destination = work / name
    command = [sys.executable, *(["-I"] if isolated else []), "-m", "quantcurve.cli", "run",
               "--market-data", str(root / "data" / "market_observations.csv"),
               "--output-dir", str(destination), "--valuation-date", "2026-01-15"]
    start = time.time()
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, env=os.environ.copy())
    result = {"mode": name, "returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
              "duration_seconds": time.time() - start}
    results.append(result)
    (root / "logs" / f"final_{name}_workflow.json").write_text(json.dumps(result, indent=2) + "\n")
    if process.returncode:
        raise RuntimeError(f"{name} clean CLI failed: {process.stderr}")


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


first = hashes(work / "installed")
second = hashes(work / "source")
if first != second:
    raise RuntimeError("installed/source clean workflow artifacts are not byte-identical")
import_check = subprocess.run([sys.executable, "-I", "-c",
    "import json,quantcurve; print(json.dumps({'module_file':quantcurve.__file__}))"],
    cwd=work, text=True, capture_output=True, check=True)
import_path = json.loads(import_check.stdout)["module_file"]
if ".venv" not in import_path:
    raise RuntimeError("isolated import did not resolve to the fresh installed package")

validated = {}
for relative in ("curves/curve.csv", "diagnostics/repricing.csv", "diagnostics/risk.csv"):
    frame = pd.read_csv(work / "installed" / relative)
    if not np.isfinite(frame.select_dtypes("number").to_numpy()).all():
        raise RuntimeError(f"nonfinite numerical output: {relative}")
    validated[relative] = {"rows": len(frame), "columns": len(frame.columns), "finite_numeric": True}
for p in (work / "installed" / "diagnostics").glob("*.json"):
    json.loads(p.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"nonfinite JSON {value}")))
grid = pd.read_csv(work / "installed" / "curves" / "curve.csv")
assert (grid.discount_factor > 0).all()
assert len(grid) >= 361 and grid.maturity_years.iloc[0] <= 1 / 12 and grid.maturity_years.iloc[-1] >= 30
source_hash = hashlib.sha256((root / "data" / "market_observations.csv").read_bytes()).hexdigest()
assert source_hash == json.loads((root / "data" / "provenance.json").read_text())["manifest_sha256"]

shutil.copytree(work / "installed", root / "outputs", dirs_exist_ok=True)
shutil.copy2(root / "outputs" / "reports" / "research_report.html", root / "reports" / "research_report.html")
assert hashes(root / "outputs") == first
record = {"all_passed": True, "fresh_directories": True, "installed_package_import": str(Path(import_path).relative_to(root)),
          "installed_and_source_byte_identical": True, "output_hashes": first, "numerical_inspection": validated,
          "input_copy_matches_supplied_manifest": True,
          "selected_result": json.loads(results[0]["stdout"])}
(root / "logs" / "final_validation.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k:v for k,v in record.items() if k != "output_hashes"},indent=2))
