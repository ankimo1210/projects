"""Supplement the rubric's unittest discovery with each full pytest suite.

Runs against temporary copies; does not change rubric scores or submissions.
"""
import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from evaluate_compatible import ROOT, scoring

OUT = Path(__file__).resolve().parent
if "--matched" in sys.argv:
    OUT = OUT / "matched"
CANDIDATES = {"astra": "results/astra", "sol": "output/sol",
              "opus": "results/opus", "fable": "results/fable"}


def run(model):
    with tempfile.TemporaryDirectory(prefix=f"quant-final-tests-{model}-") as temp:
        project = Path(temp) / "candidate"
        shutil.copytree(ROOT / CANDIDATES[model], project,
                        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "outputs"))
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        start = datetime.now(timezone.utc).isoformat()
        result = scoring.run_command(command, project, timeout=300)
        (OUT / f"{model}_pytest.log").write_text(result["stdout"] + "\n" + result["stderr"], encoding="utf-8")
        result["started_utc"] = start
        result["command"] = command
        result["candidate"] = CANDIDATES[model]
        print(f"{model}: exit={result['returncode']}; {result['stdout'].splitlines()[-1:]}", flush=True)
        return model, result


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    assert not (OUT / "pytest_verification.json").exists(), "Existing verification snapshot"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        result = dict(pool.map(run, CANDIDATES))
    (OUT / "pytest_verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
