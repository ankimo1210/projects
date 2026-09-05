"""Extend the immutable final audit to seven candidates without editing them.

Existing evaluations are reused only if candidate and evaluator hashes still
match the earlier completed snapshot. Usage is freshly recovered for all seven.
Run using the existing .venv-matched/bin/python; no installations are performed.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "expanded-7-models"
OLD = HERE / "matched"
sys.path.insert(0, str(HERE))
import recheck_final as prior
import summarize_results as summary_helpers
import evaluate_compatible as adapter
recovery = prior.recovery

PATHS = {**prior.CANDIDATES, "terra": "/Users/ankimo1210/Documents/terra",
         "luna": "output/luna", "sonnet": "output/sonnet"}
LABEL_PATHS = {**PATHS, "terra": "Documents/terra（ベンチマーク外）"}
WORK = {**prior.WORK_TURNS, "terra": [2], "luna": [1], "sonnet": [3]}
SOURCES = {**recovery.SOURCES,
    "terra": {"title": "Model Test Terra", "provider": "codex", "primary_turn": 2,
              "turn_labels": ["指示・出力先確認", "ベンチマーク本実行"],
              "path": "/Users/ankimo1210/.codex/sessions/2026/09/05/rollout-2026-09-05T14-21-53-01a07004-1fe7-78b0-9748-781853ea2fcf.jsonl"},
    "luna": {"title": "Model Test Luna", "provider": "codex", "primary_turn": 1,
             "turn_labels": ["ベンチマーク本実行"],
             "path": "/Users/ankimo1210/.codex/sessions/2026/09/05/rollout-2026-09-05T14-22-55-01a07005-1021-7e33-b054-de2d6123f020.jsonl"},
    "sonnet": {"title": "model-test-sonnet", "provider": "claude", "primary_turn": 3,
               "turn_labels": ["初回入力（API応答なし）", "指示入力（API応答なし）", "ベンチマーク本実行"],
               "path": "/Users/ankimo1210/.claude/projects/-Users-ankimo1210-Documents-projects/c4769567-9626-48f5-b87b-dadd7d1ba01f.jsonl"},
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recover_all():
    runtime, turn_rows, api_rows, audits = [], [], [], {}
    for model, config in SOURCES.items():
        before = recovery.digest(config["path"])
        parser = recovery.parse_codex if config["provider"] == "codex" else recovery.parse_claude
        turns, api, calls, audit = parser(config)
        assert before == recovery.digest(config["path"]), f"{model}: source log changed during recovery"
        audits[model] = dict(audit, source_path=config["path"], source_sha256=before)
        for turn in turns:
            children = [a for a in api if a["turn_number"] == turn["turn_number"]]
            completed = turn["status"] in ("task_complete", "turn_duration", "turn_aborted")
            # No completion event and no response is not a measured zero-second
            # completed turn. Preserve this as null outside selected work.
            minutes = recovery.elapsed(turn["start_utc"], turn["end_utc"]) / 60 if completed else None
            turn_rows.append(dict(model=model, turn_number=turn["turn_number"],
                label="ベンチマーク再開" if model == "opus" and turn["turn_number"] == 2 else turn["label"],
                selected_work_turn=turn["turn_number"] in WORK[model],
                start_jst=recovery.local(turn["start_utc"]), end_jst=recovery.local(turn["end_utc"]) if completed else None,
                status=turn["status"], minutes=minutes, api_responses=len(children), **recovery.aggregate(children)))
        selected = [t for t in turn_rows if t["model"] == model and t["selected_work_turn"]]
        assert len(selected) == len(WORK[model])
        assert all(t["status"] in ("task_complete", "turn_duration") for t in selected)
        selected_api = [a for a in api if a["turn_number"] in WORK[model]]
        assert recovery.aggregate(selected) == recovery.aggregate(selected_api)
        candidate = load(ROOT / PATHS[model] / "benchmark_summary.json")
        minutes = sum(t["minutes"] for t in selected)
        span = recovery.elapsed(selected[0]["start_jst"], selected[-1]["end_jst"]) / 60
        model_ids = sorted({a["model_id"] for a in selected_api if a.get("model_id")})
        efforts = sorted({a["reasoning_effort"] for a in selected_api if a.get("reasoning_effort")})
        assert len(model_ids) == 1, f"{model}: mixed or absent model ID {model_ids}"
        assert len(efforts) == 1, f"{model}: mixed or absent effort {efforts}"
        runtime.append(dict(model=model, model_id=model_ids[0], reasoning_effort=efforts[0],
            session_name=config["title"], candidate_path=LABEL_PATHS[model], work_turns=WORK[model],
            work_minutes=minutes, work_span_minutes=span, between_work_turn_idle_minutes=max(0, span-minutes),
            start_jst=selected[0]["start_jst"], finish_jst=selected[-1]["end_jst"],
            work_api_responses=len(selected_api), session_api_responses=len(api),
            session_total_tokens=recovery.aggregate(api)["total_tokens"],
            self_reported_wall_minutes=float(candidate["wall_time_seconds"])/60,
            **recovery.aggregate(selected_api)))
        for a in api:
            api_rows.append({"model": model, "selected_work_turn": a["turn_number"] in WORK[model],
                **{k: v for k, v in a.items() if k != "call_ids"}})
        save(f"{model}_metadata.json", {"model_name": model_ids[0], "reasoning_effort": efforts[0],
             "wall_time_seconds": minutes*60, "timing_definition": "Selected work-turn wall time; tools included, setup and inter-turn idle excluded."})
        print(f"USAGE {model}: {minutes:.4f} min; {recovery.aggregate(selected_api)['total_tokens']:,} tokens; {len(selected_api)} responses", flush=True)
    assert len(runtime) == 7 and len(turn_rows) >= 20
    assert sum(t["selected_work_turn"] for t in turn_rows) == 8
    recovery.write_csv(OUT / "runtime_tokens.csv", runtime)
    recovery.write_csv(OUT / "user_turns.csv", turn_rows)
    recovery.write_csv(OUT / "api_responses.csv", api_rows)
    save("usage_audit.json", audits)
    return runtime


def score_and_test(model):
    print(f"EVALUATE {model}", flush=True)
    command = [sys.executable, str(HERE / "evaluate_compatible.py"), str(ROOT / PATHS[model]),
               "--metadata", str(OUT / f"{model}_metadata.json"), "--json-out", str(OUT / f"{model}_score.json")]
    with (OUT / f"{model}_evaluator.log").open("w") as log:
        proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    if proc.returncode:
        raise RuntimeError(f"{model}: evaluator failed ({proc.returncode}); preserved log")
    score = load(OUT / f"{model}_score.json")
    assert abs(sum(score["category_scores"].values()) - score["total_score"]) < 1e-6
    with tempfile.TemporaryDirectory(prefix=f"quant-seven-tests-{model}-") as temp:
        project = Path(temp) / "candidate"
        shutil.copytree(ROOT / PATHS[model], project,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "outputs", "fresh_outputs", "build"))
        test_command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        start = datetime.now(timezone.utc).isoformat()
        test = adapter.scoring.run_command(test_command, project, timeout=300)
        test.update(started_utc=start, command=test_command, candidate=PATHS[model])
    (OUT / f"{model}_pytest.log").write_text(test["stdout"] + "\n" + test["stderr"], encoding="utf-8")
    print(f"RESULT {model}: {score['total_score']}; pytest exit {test['returncode']}; {test['stdout'].splitlines()[-1:]}", flush=True)
    return model, score, test


def main():
    OUT.mkdir(exist_ok=True)
    if (OUT / "evaluation_audit.json").exists():
        unfinished = load(OUT / "evaluation_audit.json")
        assert "--resume" in sys.argv and not unfinished.get("completed_utc"), "Completed snapshot is immutable"
    old = load(OLD / "evaluation_audit.json")
    hashes = {m: prior.candidate_hashes(ROOT / path) for m, path in PATHS.items()}
    if (OUT / "evaluation_audit.json").exists():
        assert hashes == unfinished["candidate_before"], "Candidate changed since interrupted audit; start a new snapshot"
    scoring_unchanged = all(recovery.digest(ROOT / p) == old[key] for p, key in [
        ("evaluator/scoring.py", "scoring_sha256"), ("tools/evaluate_candidate.py", "wrapper_sha256"),
        ("analysis/final-review-20260905/evaluate_compatible.py", "adapter_sha256")])
    reused = [m for m in prior.CANDIDATES if scoring_unchanged and hashes[m] == old["candidate_before"][m]]
    audit = {"started_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "packages": {n: importlib.metadata.version(n) for n in ["numpy", "pandas", "scipy", "matplotlib", "pytest"]},
        "manifest_before": prior.manifest_check(), "candidate_before": hashes, "candidate_locations": PATHS,
        "scoring_sha256": recovery.digest(ROOT / "evaluator/scoring.py"),
        "wrapper_sha256": recovery.digest(ROOT / "tools/evaluate_candidate.py"),
        "adapter_sha256": recovery.digest(HERE / "evaluate_compatible.py"), "compatibility_adapter": True,
        "reused_evaluations": {m: {"source": str(OLD / f"{m}_score.json"), "sha256": recovery.digest(OLD / f"{m}_score.json"),
                                   "reason": "Candidate and evaluator hashes unchanged", "evaluated_at": old["completed_utc"]} for m in reused},
        "fresh_evaluations": [m for m in PATHS if m not in reused],
        "caveats": ["Terra remains at its actual external directory; not moved.",
                    "Sonnet T1/T2 had no recorded API response or completion; time is null, not zero.",
                    "All seven logs re-read and deduplicated; prior scores/test results reused only on exact candidate/evaluator hash matches.",
                    "Candidate tests may fail; report failures without editing candidates or changing rubric."]}
    save("evaluation_audit.json", audit)
    runtime = recover_all()
    scores, tests = {}, {}
    previous_tests = load(OLD / "pytest_verification.json")
    for m in reused:
        scores[m] = load(OLD / f"{m}_score.json")
        tests[m] = previous_tests[m]
        save(f"{m}_score.json", scores[m])
        print(f"REUSE {m}: candidate/evaluator hashes match", flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(score_and_test, m) for m in PATHS if m not in reused]
        for future in as_completed(futures):
            m, score, test = future.result()
            scores[m], tests[m] = score, test
            save("pytest_verification.json", tests)
    audit["manifest_after"] = prior.manifest_check()
    audit["original_candidates_unchanged"] = hashes == {m: prior.candidate_hashes(ROOT / p) for m, p in PATHS.items()}
    assert audit["original_candidates_unchanged"]
    assert all(recovery.digest(c["path"]) == load(OUT / "usage_audit.json")[m]["source_sha256"] for m, c in SOURCES.items())
    audit["completed_utc"] = datetime.now(timezone.utc).isoformat()
    save("evaluation_audit.json", audit)
    save("pytest_verification.json", tests)
    rows = []
    for u in runtime:
        m = u["model"]
        score, candidate = scores[m], load(ROOT / PATHS[m] / "benchmark_summary.json")
        counts = summary_helpers.test_counts(tests[m])
        row = dict(model=m, model_id=u["model_id"], reasoning_effort=u["reasoning_effort"], score=score["total_score"],
            candidate_path=LABEL_PATHS[m], reported_status=candidate.get("status"), wall_time_sec=candidate.get("wall_time_seconds"),
            work_time_min=u["work_minutes"], work_span_min=u["work_span_minutes"], between_work_turn_idle_min=u["between_work_turn_idle_minutes"],
            corrective_iterations=candidate.get("corrective_iterations"), tests_passed=candidate.get("final_tests_passed", candidate.get("tests_passed")),
            tests_failed=candidate.get("final_tests_failed", candidate.get("tests_failed")), verified_tests_passed=counts["passed"],
            verified_tests_failed=counts["failed"], verified_test_errors=counts["error"], verified_tests_skipped=counts["skipped"],
            pytest_exit_code=tests[m]["returncode"], input_tokens=u["input_total"], uncached_input_tokens=u["uncached_input"],
            cached_input_tokens=u["cache_read_input"], cache_creation_input_tokens=u["cache_creation_input"],
            output_tokens=u["output_total"], reasoning_tokens=u["output_reasoning"], total_tokens=u["total_tokens"], session_total_tokens=u["session_total_tokens"],
            reported_usd_cost=candidate.get("reported_usd_cost"), hidden_checks_passed=len(score["hidden_tests"]["passed"]),
            hidden_checks_failed=len(score["hidden_tests"]["failed"]), failed_check_ids=score["failed_test_identifiers"],
            evaluation_reused=m in reused, **{alias: score["category_scores"][key] for alias, key in summary_helpers.CATEGORY_KEYS.items()})
        assert row["input_tokens"] + row["output_tokens"] == row["total_tokens"]
        rows.append(row)
    rows.sort(key=lambda r: -r["score"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    save("combined_summary.json", rows)
    recovery.write_csv(OUT / "combined_summary.csv", rows)
    print("FINAL", json.dumps([{k: r[k] for k in ["model", "score", "work_time_min", "total_tokens", "verified_tests_passed", "verified_tests_failed", "verified_test_errors"]} for r in rows]), flush=True)


if __name__ == "__main__":
    main()
