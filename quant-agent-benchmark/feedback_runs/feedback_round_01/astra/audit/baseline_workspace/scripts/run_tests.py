"""Run and count a real pytest invocation, including failed attempts."""
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
summary_path = root / "benchmark_summary.json"
summary = json.loads(summary_path.read_text())
number = summary["test_runs"] + 1
summary["test_runs"] = summary["test_suite_runs"] = number
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
xml_path = root / "logs" / f"test_run_{number}.xml"
started = time.time()
command = [sys.executable, "-m", "pytest", "-q", f"--junitxml={xml_path}", *sys.argv[1:]]
result = subprocess.run(command, cwd=root, text=True, capture_output=True)
log = result.stdout + result.stderr
(root / "logs" / f"test_run_{number}.log").write_text(log)
print(log, end="")
passed = failed = skipped = 0
if xml_path.exists():
    cases = ET.parse(xml_path).getroot().findall(".//testcase")
    for case in cases:
        if case.find("failure") is not None or case.find("error") is not None:
            failed += 1
        elif case.find("skipped") is not None:
            skipped += 1
        else:
            passed += 1
record = {"run": number, "returncode": result.returncode, "passed": passed, "failed": failed,
          "skipped": skipped, "duration_seconds": time.time() - started, "command": command[2:]}
(root / "logs" / f"test_run_{number}.json").write_text(json.dumps(record, indent=2) + "\n")
summary = json.loads(summary_path.read_text())
summary["failed_test_runs"] += int(result.returncode != 0)
summary["failed_test_suite_runs"] = summary["failed_test_runs"]
summary["tests_passed"] = summary["final_tests_passed"] = passed
summary["tests_failed"] = summary["final_tests_failed"] = failed
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
raise SystemExit(result.returncode)
