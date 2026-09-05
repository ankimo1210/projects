"""User-provided final-summary workflow, with audited sources and strict loads.

Corrections: Sol's actual path; software_engineering_reproducibility key;
transcript token recovery; separate self-report and measured timing/tests.
Missing/failed evaluations are errors, never silently converted to empty dicts.
"""
from datetime import datetime, timezone
import csv
import json
import importlib.metadata
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / "matched"
DEST = ROOT / "evaluations"
PATHS = {"astra": "results/astra", "sol": "output/sol", "opus": "results/opus", "fable": "results/fable"}
CATEGORY_KEYS = {
    "numerical": "numerical_correctness", "model_quality": "quantitative_model_quality",
    "robustness": "hidden_scenario_robustness", "software_engineering": "software_engineering_reproducibility",
    "data_quality": "data_quality_handling", "report": "report_completeness", "completion": "completion_integrity",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_counts(result):
    counts = {}
    text = result["stdout"] + result["stderr"]
    for kind in ("passed", "failed", "error", "skipped"):
        matches = re.findall(rf"(\d+) {kind}s?\b", text)
        counts[kind] = int(matches[-1]) if matches else 0
    assert sum(counts.values()) > 0, "No test count found; inspect pytest log"
    return counts


def main():
    audit = load(RUN / "evaluation_audit.json")
    assert audit["original_candidates_unchanged"] and audit.get("completed_utc")
    pytest = load(RUN / "pytest_verification.json")
    with (RUN / "runtime_tokens.csv").open(encoding="utf-8-sig", newline="") as f:
        usage = {r["model"]: r for r in csv.DictReader(f)}
    evaluations, rows = {}, []
    for model, candidate in PATHS.items():
        score = load(RUN / f"{model}_score.json")
        summary = load(ROOT / candidate / "benchmark_summary.json")
        # Status is optional in the original summary contract (Sol omits it).
        # Completed log-turn markers were separately checked during recovery.
        assert summary.get("finish_time") and summary.get("status") in (None, "COMPLETED")
        assert abs(sum(score["category_scores"].values()) - score["total_score"]) < 1e-6
        t = test_counts(pytest[model])
        u = usage[model]
        row = {
            "model": model, "score": score["total_score"], "candidate_path": candidate,
            "reported_status": summary.get("status"),
            "wall_time_sec": summary.get("wall_time_seconds"),
            "work_time_min": float(u["work_minutes"]),
            "work_span_min": float(u["work_span_minutes"]),
            "between_work_turn_idle_min": float(u["between_work_turn_idle_minutes"]),
            "corrective_iterations": summary.get("corrective_iterations"),
            "tests_passed": summary.get("final_tests_passed", summary.get("tests_passed")),
            "tests_failed": summary.get("final_tests_failed", summary.get("tests_failed")),
            "verified_tests_passed": t["passed"], "verified_tests_failed": t["failed"],
            "verified_test_errors": t["error"], "pytest_exit_code": pytest[model]["returncode"],
            "input_tokens": int(u["input_total"]), "uncached_input_tokens": int(u["uncached_input"]),
            "cached_input_tokens": int(u["cache_read_input"]),
            "cache_creation_input_tokens": int(u["cache_creation_input"]),
            "output_tokens": int(u["output_total"]), "reasoning_tokens": int(u["output_reasoning"]),
            "total_tokens": int(u["total_tokens"]), "session_total_tokens": int(u["session_total_tokens"]),
            "reported_usd_cost": summary.get("reported_usd_cost"),
            "hidden_checks_passed": len(score["hidden_tests"]["passed"]),
            "hidden_checks_failed": len(score["hidden_tests"]["failed"]),
            "failed_check_ids": score["failed_test_identifiers"],
            **{alias: score["category_scores"][key] for alias, key in CATEGORY_KEYS.items()},
        }
        assert row["input_tokens"] + row["output_tokens"] == row["total_tokens"]
        assert row["uncached_input_tokens"] + row["cached_input_tokens"] + row["cache_creation_input_tokens"] == row["input_tokens"]
        rows.append(row)
        evaluations[model] = score
    rows.sort(key=lambda row: -row["score"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    DEST.mkdir(exist_ok=True)
    for filename in [f"{m}.json" for m in PATHS] + ["combined_summary.json", "combined_summary.csv", "methodology.json"]:
        assert not (DEST / filename).exists(), f"Refusing to overwrite {filename}"
    for model, score in evaluations.items():
        (DEST / f"{model}.json").write_text(json.dumps(score, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (DEST / "combined_summary.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (DEST / "combined_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()} for row in rows)
    methodology = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "user_script": "/Users/ankimo1210/.codex/attachments/a922796c-21dd-4200-9134-00860a8961ac/pasted-text.txt",
        "scorer": str(ROOT / "tools/evaluate_candidate.py"),
        "adapter": str(HERE / "evaluate_compatible.py"),
        "audit": str(RUN / "evaluation_audit.json"), "usage_audit": str(RUN / "usage_audit.json"),
        "test_verification": str(RUN / "pytest_verification.json"),
        "python": sys.version,
        "installed_distributions": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "definitions": {
            "score": "Original rubric /100; only required risk columns passed to avoid optional-column join collision. No weights/thresholds changed.",
            "wall_time_sec": "Candidate self-reported elapsed time; timing boundaries differ between candidates.",
            "work_time_min": "Logged main and resume user-turn wall time. Includes tools and compaction; excludes setup, follow-ups, inter-turn idle.",
            "total_tokens": "Logged selected work-turn input (including cache) + output; reasoning is part of output, not additional.",
            "session_total_tokens": "All API usage in the named session, including setup and follow-ups.",
            "tests_passed": "Candidate self-report; verified_tests_passed is independent full pytest rerun.",
            "missing_cost": "Unknown, not zero; no prices or costs estimated.",
        },
        "caveats": [
            "Each model ran once. Scores measure this rubric, not universal model capability.",
            "Opus work turns 1+2 included. Earlier 69.9-minute /29,457,223-token value was incomplete.",
            "Sol evaluated from output/sol; specified results/sol directory remains empty. No automatic relocation performed.",
            "Astra report checker recognizes only 2/9 English keywords despite Japanese headings covering the requested subjects.",
            "All 30 Astra other-directory warnings match its own results/astra path, not another model; no score override applied.",
            "Opus README and Fable benchmark_summary other-directory warnings also refer to their own respective result directories. These hits are not evidence of another model's output being read.",
            "Original rubric uses unittest discovery, which misses some pytest tests. Full pytest result is reported separately.",
            "Shared older numerical environment had warning-induced test failures. Final scores and tests use isolated recorded numerical versions.",
        ],
    }
    (DEST / "methodology.json").write_text(json.dumps(methodology, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
