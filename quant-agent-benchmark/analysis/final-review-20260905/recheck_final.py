"""Re-evaluate final submissions with the existing, unchanged owner evaluator.

Preserves original candidate files and previous session-token analysis. Evaluator
execution time is not benchmark-agent work time. Resume turns count as work;
idle gaps are recorded separately. Requires the previous recovery module.
"""
from __future__ import annotations

import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
MATCHED = "--matched" in sys.argv
COMPATIBLE = "--compatible" in sys.argv or MATCHED
OUT = SCRIPT_DIR / "matched" if MATCHED else (SCRIPT_DIR / "compatible" if COMPATIBLE else SCRIPT_DIR)
sys.path.insert(0, str(ROOT / "analysis/session-tokens-20260905"))
import recover_tokens as recovery

CANDIDATES = {"astra": "results/astra", "sol": "output/sol",
              "opus": "results/opus", "fable": "results/fable"}
WORK_TURNS = {"astra": [4], "sol": [2], "opus": [1, 2], "fable": [1]}


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def candidate_hashes(path):
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "tmp", "build"}
    return {str(p.relative_to(path)): recovery.digest(p) for p in sorted(path.rglob("*"))
            if p.is_file() and not ignored.intersection(p.relative_to(path).parts)}


def manifest_check():
    verified = {}
    for part, key in (("input", "public_file_hashes"), ("evaluator", "evaluator_file_hashes")):
        manifest = json.loads((ROOT / part / "MANIFEST.json").read_text())
        mismatches = [rel for rel, expected in manifest[key].items()
                      if recovery.digest(ROOT / part / rel) != expected]
        assert not mismatches, (part, mismatches)
        verified[part] = {"files_verified": len(manifest[key]), "mismatches": mismatches}
    return verified


def recover_usage():
    summaries, turn_rows, audits = [], [], {}
    for model, config in recovery.SOURCES.items():
        before = recovery.digest(config["path"])
        parser = recovery.parse_codex if config["provider"] == "codex" else recovery.parse_claude
        turns, api, calls, audit = parser(config)
        assert recovery.digest(config["path"]) == before, "Session changed while reading"
        audits[model] = dict(audit, source_path=config["path"], source_sha256=before)
        for turn in turns:
            children = [a for a in api if a["turn_number"] == turn["turn_number"]]
            turn_rows.append(dict(model=model, turn_number=turn["turn_number"],
                                  label=("ベンチマーク再開" if model == "opus" and turn["turn_number"] == 2 else turn["label"]),
                                  selected_work_turn=turn["turn_number"] in WORK_TURNS[model],
                                  start_jst=recovery.local(turn["start_utc"]),
                                  end_jst=recovery.local(turn["end_utc"]), status=turn["status"],
                                  minutes=recovery.elapsed(turn["start_utc"], turn["end_utc"])/60,
                                  api_responses=len(children), **recovery.aggregate(children)))
        selected = [t for t in turn_rows if t["model"] == model and t["selected_work_turn"]]
        assert len(selected) == len(WORK_TURNS[model])
        assert all(t["status"] in ("task_complete", "turn_duration") for t in selected)
        selected_api = [a for a in api if a["turn_number"] in WORK_TURNS[model]]
        assert recovery.aggregate(selected) == recovery.aggregate(selected_api)
        summary_json = json.loads((ROOT / CANDIDATES[model] / "benchmark_summary.json").read_text())
        work_minutes = sum(t["minutes"] for t in selected)
        span_minutes = recovery.elapsed(selected[0]["start_jst"], selected[-1]["end_jst"])/60
        summary = dict(model=model, session_name=config["title"], candidate_path=CANDIDATES[model],
                       work_turns=WORK_TURNS[model], work_minutes=work_minutes,
                       work_span_minutes=span_minutes, between_work_turn_idle_minutes=span_minutes-work_minutes,
                       start_jst=selected[0]["start_jst"], finish_jst=selected[-1]["end_jst"],
                       work_api_responses=len(selected_api), session_api_responses=len(api),
                       session_total_tokens=recovery.aggregate(api)["total_tokens"],
                       self_reported_wall_minutes=float(summary_json["wall_time_seconds"])/60,
                       **recovery.aggregate(selected_api))
        summaries.append(summary)
        metadata = {"model_name": model, "reasoning_effort": "xhigh",
                    "wall_time_seconds": work_minutes * 60,
                    "timing_definition": "Sum of selected benchmark/resume user-turn wall times; tools included; inter-turn idle excluded."}
        save(f"{model}_metadata.json", metadata)
    recovery.write_csv(OUT / "runtime_tokens.csv", summaries)
    recovery.write_csv(OUT / "user_turns.csv", turn_rows)
    save("usage_audit.json", audits)
    return summaries


def evaluate(model):
    entrypoint = SCRIPT_DIR / "evaluate_compatible.py" if COMPATIBLE else ROOT / "tools/evaluate_candidate.py"
    command = [sys.executable, str(entrypoint),
               str(ROOT / CANDIDATES[model]), "--metadata", str(OUT / f"{model}_metadata.json"),
               "--json-out", str(OUT / f"{model}_score.json")]
    print(f"START {model}: owner evaluator; compatibility adapter={COMPATIBLE}", flush=True)
    with (OUT / f"{model}_evaluator.log").open("w") as log:
        proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    if proc.returncode:
        raise RuntimeError(f"{model}: evaluator exit {proc.returncode}; inspect log")
    result = json.loads((OUT / f"{model}_score.json").read_text())
    assert abs(sum(result["category_scores"].values()) - result["total_score"]) < 1e-6
    print(f"DONE {model}: {result['total_score']}/100; {len(result['failed_test_identifiers'])} failed checks", flush=True)
    return model, result


def main():
    # This directory is a snapshot. Do not overwrite an earlier evaluation.
    OUT.mkdir(exist_ok=True)
    assert not list(OUT.glob("*_score.json")), "Score snapshot exists; use a new output directory"
    audit = {"started_utc": datetime.now(timezone.utc).isoformat(),
             "python": sys.version, "python_executable": sys.executable,
             "packages": {n: importlib.metadata.version(n) for n in ("numpy", "pandas", "scipy", "matplotlib", "pytest")},
             "manifest_before": manifest_check(),
             "scoring_sha256": recovery.digest(ROOT / "evaluator/scoring.py"),
             "wrapper_sha256": recovery.digest(ROOT / "tools/evaluate_candidate.py"),
             "compatibility_adapter": COMPATIBLE,
             "adapter_sha256": recovery.digest(SCRIPT_DIR / "evaluate_compatible.py") if COMPATIBLE else None,
             "candidate_before": {m: candidate_hashes(ROOT / p) for m, p in CANDIDATES.items()},
             "caveats": ["Sol evaluated at output/sol; results/sol is empty.",
                         "Opus resumed at 12:50 JST; both work turns included, idle gap separate.",
                         "Post-generation empty-results test is inapplicable after submissions.",
                         "Evaluators run concurrently; their durations are not agent work times."]}
    usage = recover_usage()
    save("evaluation_audit.json", audit)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(evaluate, m) for m in CANDIDATES]
        for future in concurrent.futures.as_completed(futures):
            model, result = future.result()
            results[model] = result
    audit["manifest_after"] = manifest_check()
    after = {m: candidate_hashes(ROOT / p) for m, p in CANDIDATES.items()}
    audit["original_candidates_unchanged"] = after == audit["candidate_before"]
    assert audit["original_candidates_unchanged"]
    audit["completed_utc"] = datetime.now(timezone.utc).isoformat()
    save("evaluation_audit.json", audit)
    joined = []
    for u in usage:
        result = results[u["model"]]
        joined.append(dict(u, score=result["total_score"], **result["category_scores"],
                           passed_checks=len(result["hidden_tests"]["passed"]),
                           failed_checks=len(result["hidden_tests"]["failed"]),
                           score_per_work_minute=result["total_score"]/u["work_minutes"],
                           warnings=result["warnings"]))
    recovery.write_csv(OUT / "comparison.csv", sorted(joined, key=lambda r: -r["score"]))
    print("VALIDATED: manifests and original candidates unchanged; score sums and usage totals reconcile.", flush=True)


if __name__ == "__main__":
    main()
